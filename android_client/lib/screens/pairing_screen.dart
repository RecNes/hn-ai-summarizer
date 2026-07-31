import 'dart:async';

import 'package:flutter/material.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart';

import '../providers/sync_provider.dart';
import '../services/discovery_service.dart';
import '../services/pairing_service.dart';

/// Device pairing screen — QR scan + manual entry + server discovery.
class PairingScreen extends StatefulWidget {
  final PairingService pairingService;
  final DiscoveryService discoveryService;

  const PairingScreen({
    super.key,
    required this.pairingService,
    required this.discoveryService,
  });

  @override
  State<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends State<PairingScreen> {
  // ── Controllers (created once, disposed properly) ──
  final _codeController = TextEditingController();
  final _serverController = TextEditingController();
  final _deviceNameController = TextEditingController();
  final MobileScannerController _cameraController = MobileScannerController();

  // ── State ───────────────────────────────
  String _deviceName = '';
  bool _isProcessing = false;
  String? _errorMessage;
  bool _qrProcessed = false;

  @override
  void initState() {
    super.initState();
    _initDeviceName();
  }

  @override
  void dispose() {
    _codeController.dispose();
    _serverController.dispose();
    _deviceNameController.dispose();
    _cameraController.dispose();
    super.dispose();
  }

  Future<void> _initDeviceName() async {
    try {
      final deviceInfo = await DeviceInfoPlugin().androidInfo;
      final name = '${deviceInfo.brand} ${deviceInfo.model}'.trim();
      if (mounted) {
        setState(() {
          _deviceName = name;
          _deviceNameController.text = name;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _deviceName = 'Android Cihaz');
      }
    }
  }

  // ── QR detection ────────────────────────

  void _onQrDetected(BarcodeCapture capture) {
    if (_qrProcessed || _isProcessing) return;
    final barcode = capture.barcodes.firstOrNull;
    if (barcode?.rawValue == null) return;

    final raw = barcode!.rawValue!;
    final data = widget.pairingService.extractPairingData(raw);
    if (data == null) return;

    _qrProcessed = true;

    // Auto-fill fields
    _serverController.text = data['server_url'] ?? '';
    if (data['pairing_code'] != null) {
      _codeController.text = data['pairing_code']!;
    }

    // Auto-trigger pairing
    _startPairing();
  }

  // ── Server discovery modal ──────────────

  Future<void> _onServerFieldTap() async {
    // Show discovery modal
    showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => _ServerDiscoverySheet(
        discoveryService: widget.discoveryService,
      ),
    ).then((selectedUrl) {
      if (selectedUrl != null && selectedUrl.isNotEmpty) {
        _serverController.text = selectedUrl;
      }
    });
  }

  // ── Pairing flow ────────────────────────

  Future<void> _startPairing() async {
    final code = _codeController.text.trim();
    final serverUrl = _serverController.text.trim();

    if (code.isEmpty || serverUrl.isEmpty) {
      setState(() => _errorMessage = 'Lütfen eşleştirme kodu ve sunucu adresini girin.');
      return;
    }

    setState(() {
      _isProcessing = true;
      _errorMessage = null;
    });

    try {
      final deviceId = const Uuid().v4();
      final deviceName = _deviceName.isNotEmpty ? _deviceName : 'Android Cihaz';

      // Step 1: Register device on server with the web-visible pairing code.
      // The server uses this code so the web UI code and device code match.
      final pairingCode = await widget.pairingService.initiatePairing(
        serverUrl,
        deviceName,
        deviceId,
        pairingCode: code,
      );

      // Step 2: Confirm pairing with the same code
      final device = await widget.pairingService.confirmPairing(deviceId, pairingCode);

      // Success — save & notify
      await widget.pairingService.savePairing(device);

      if (mounted) {
        await context.read<SyncProvider>().setPaired(true);
      }
    } catch (e) {
      final serverName = Uri.tryParse(serverUrl)?.host ?? serverUrl;
      if (mounted) {
        setState(() {
          _isProcessing = false;
          _qrProcessed = false;
          _errorMessage = '"$serverName" sunucusu ile eşleşme başarısız';
        });
      }
    }
  }

  // ── Build ───────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Cihaz Eşleştirme')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // ── QR Vizör ──────────────────
              _buildQrViewer(),
              const SizedBox(height: 16),

              // ── Device Name Input ─────────
              TextField(
                controller: _deviceNameController,
                decoration: const InputDecoration(
                  labelText: 'Cihaz Adı',
                  hintText: 'Cihazına bir isim ver',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.phone_android),
                ),
                enabled: !_isProcessing,
                onChanged: (v) => _deviceName = v,
              ),
              const SizedBox(height: 12),

              // ── Pairing Code Input ────────
              TextField(
                controller: _codeController,
                decoration: const InputDecoration(
                  labelText: 'Eşleştirme Kodu',
                  hintText: '6 haneli kodu girin',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.key),
                ),
                keyboardType: TextInputType.number,
                maxLength: 6,
                enabled: !_isProcessing,
              ),
              const SizedBox(height: 12),

              // ── Server URL Input ──────────
              TextField(
                controller: _serverController,
                decoration: const InputDecoration(
                  labelText: 'Sunucu Adresi',
                  hintText: 'https://... veya dokunup ağda ara',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.dns),
                ),
                keyboardType: TextInputType.url,
                enabled: !_isProcessing,
                onTap: _onServerFieldTap,
              ),
              const SizedBox(height: 16),

              // ── Error message ─────────────
              if (_errorMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.error_outline, color: Colors.red.shade700, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: TextStyle(color: Colors.red.shade700, fontSize: 13),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // ── Continue button / Loader ──
              if (_isProcessing)
                const Center(
                  child: Column(
                    children: [
                      CircularProgressIndicator(),
                      SizedBox(height: 12),
                      Text('Eşleştirme yapılıyor...'),
                    ],
                  ),
                )
              else
                ElevatedButton.icon(
                  onPressed: _startPairing,
                  icon: const Icon(Icons.arrow_forward),
                  label: const Text('Devam Et'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    textStyle: const TextStyle(fontSize: 16),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  // ── QR Viewer Widget ────────────────────

  Widget _buildQrViewer() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: SizedBox(
        height: 220,
        child: MobileScanner(
          controller: _cameraController,
          onDetect: _onQrDetected,
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// Server Discovery Bottom Sheet
// ═══════════════════════════════════════════

class _ServerDiscoverySheet extends StatefulWidget {
  final DiscoveryService discoveryService;

  const _ServerDiscoverySheet({required this.discoveryService});

  @override
  State<_ServerDiscoverySheet> createState() => _ServerDiscoverySheetState();
}

class _ServerDiscoverySheetState extends State<_ServerDiscoverySheet> {
  bool _searching = true;
  List<String> _servers = [];

  @override
  void initState() {
    super.initState();
    _search();
  }

  Future<void> _search() async {
    try {
      final servers = await widget.discoveryService.discoverServers();
      if (mounted) {
        setState(() {
          _servers = servers;
          _searching = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _searching = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Ağda Sunucu Ara',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          if (_searching)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Column(
                  children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 12),
                    Text('Sunucular aranıyor...'),
                  ],
                ),
              ),
            )
          else if (_servers.isEmpty)
            Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  Icon(Icons.search_off, size: 40, color: Colors.grey[400]),
                  const SizedBox(height: 8),
                  Text('Hiç sunucu bulunamadı.\nAdresi elle girebilirsiniz.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.grey[600]),
                  ),
                ],
              ),
            )
          else ...[
            const Text('Bulunan sunucular:'),
            const SizedBox(height: 8),
            ..._servers.map((url) => ListTile(
              leading: const Icon(Icons.dns),
              title: Text(url),
              onTap: () => Navigator.pop(context, url),
            )),
          ],
          const SizedBox(height: 16),
          OutlinedButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Kapat'),
          ),
        ],
      ),
    );
  }
}