import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../models/device.dart';
import 'api_service.dart';
import 'settings_service.dart';

/// Manages device pairing with the Nunti server.
/// Uses dual-storage: flutter_secure_storage (primary) + shared_preferences (fallback).
class PairingService {
  final ApiService apiService;
  final FlutterSecureStorage secureStorage;
  final SettingsService settingsService;

  PairingService({
    required this.apiService,
    required this.secureStorage,
    required this.settingsService,
  });

  // â”€â”€ Storage keys â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  static const _keyAuthToken = 'auth_token';
  static const _keyServerUrl = 'server_url';
  static const _keyDeviceId = 'device_id';
  static const _keyDeviceName = 'device_name';

  // â”€â”€ Token check (dual read) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  /// Check if device has a stored pairing token.
  Future<bool> hasStoredToken() async {
    final token = await _readSecureOrPref(_keyAuthToken);
    return token != null && token.isNotEmpty;
  }

  Future<String?> getStoredToken() async {
    return await _readSecureOrPref(_keyAuthToken);
  }

  Future<String?> getStoredServerUrl() async {
    return await _readSecureOrPref(_keyServerUrl);
  }

  Future<String?> getStoredDeviceId() async {
    return await _readSecureOrPref(_keyDeviceId);
  }

  /// Read from secure storage first, fall back to shared preferences.
  Future<String?> _readSecureOrPref(String key) async {
    try {
      final secure = await secureStorage.read(key: key);
      if (secure != null && secure.isNotEmpty) return secure;

      // Fallback: shared_preferences
      final pref = await settingsService.getPairingValue(key);
      return pref;
    } catch (_) {
      return null;
    }
  }

  // â”€â”€ QR code parsing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  /// Extract pairing data from QR code content.
  Map<String, String?>? extractPairingData(String qrData) {
    try {
      final json = jsonDecode(qrData) as Map<String, dynamic>;
      return {
        'server_url': json['server_url'] as String?,
        'register_endpoint': json['register_endpoint'] as String?,
        'pairing_code': json['pairing_code'] as String?,
      };
    } catch (_) {
      return null;
    }
  }

  // â”€â”€ Pairing flow â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  /// Register device on server, returns pairing code.
  ///
  /// If [pairingCode] is provided (e.g. from a QR code), the server uses
  /// that code so the web-visible code and device code stay in sync.
  Future<String> initiatePairing(
    String serverUrl,
    String deviceName,
    String deviceId, {
    String? pairingCode,
  }) async {
    apiService.updateBaseUrl(serverUrl);
    final result = await apiService.registerDevice(
      deviceName,
      deviceId,
      deviceType: 'android',
      pairingCode: pairingCode,
    );
    return result['pairing_code'] as String? ?? '';
  }

  /// Confirm pairing, returns device info with JWT token.
  Future<DeviceInfo> confirmPairing(
    String deviceId,
    String pairingCode,
  ) async {
    final result = await apiService.confirmPairing(deviceId, pairingCode);
    return DeviceInfo(
      deviceId: result['device_id'] as String? ?? deviceId,
      deviceName: result['device_name'] as String? ?? 'Unknown Device',
      authToken: result['auth_token'] as String?,
      isPaired: true,
      serverUrl: apiService.baseUrl,
    );
  }

  // â”€â”€ Token persistence (dual write) â”€â”€â”€â”€â”€â”€â”€â”€â”€

  /// Save pairing result to both secure storage AND shared preferences.
  Future<void> savePairing(DeviceInfo device) async {
    if (device.authToken != null) {
      await _writeDual(_keyAuthToken, device.authToken!);
    }
    if (device.serverUrl != null) {
      await _writeDual(_keyServerUrl, device.serverUrl!);
    }
    await _writeDual(_keyDeviceId, device.deviceId);
    await _writeDual(_keyDeviceName, device.deviceName);
  }

  /// Clear all pairing data from both storages.
  Future<void> clearPairing() async {
    for (final key in [_keyAuthToken, _keyServerUrl, _keyDeviceId, _keyDeviceName]) {
      await secureStorage.delete(key: key);
      await settingsService.removePairingValue(key);
    }
  }

  /// Write to both secure storage and shared preferences.
  Future<void> _writeDual(String key, String value) async {
    await secureStorage.write(key: key, value: value);
    await settingsService.setPairingValue(key, value);
  }
}