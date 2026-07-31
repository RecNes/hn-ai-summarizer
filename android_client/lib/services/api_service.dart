import 'package:dio/dio.dart';

import '../utils/url_helper.dart';

/// REST API client for communicating with the HN Reader server.
class ApiService {
  final Dio _dio = Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 30),
    headers: {'Content-Type': 'application/json'},
  ));

  /// Update base URL (used after server discovery).
  /// URL, geçersiz `:0` portundan temizlenerek saklanır.
  void updateBaseUrl(String url) {
    _dio.options.baseUrl = UrlHelper.normalizeBaseUrl(url);
  }

  /// Get current base URL.
  String? get baseUrl => _dio.options.baseUrl;

  /// Register a new device, get pairing code back.
  ///
  /// If [pairingCode] is provided (e.g. from a web UI QR code), the server
  /// uses that code instead of generating a new one, so the web-visible
  /// code and the device-side code stay in sync.
  Future<Map<String, dynamic>> registerDevice(
    String deviceName,
    String deviceId, {
    String deviceType = 'android',
    String? pairingCode,
  }) async {
    final res = await _dio.post('/api/devices/register', data: {
      'device_name': deviceName,
      'device_id': deviceId,
      'device_type': deviceType,
      if (pairingCode != null && pairingCode.isNotEmpty)
        'pairing_code': pairingCode,
    });
    return res.data as Map<String, dynamic>;
  }

  /// Confirm pairing with code, get JWT token back.
  Future<Map<String, dynamic>> confirmPairing(
    String deviceId,
    String pairingCode,
  ) async {
    final res = await _dio.post('/api/devices/confirm', data: {
      'device_id': deviceId,
      'pairing_code': pairingCode,
    });
    return res.data as Map<String, dynamic>;
  }

  /// Verify a stored token is still valid on the server.
  Future<bool> verifyToken(String token) async {
    try {
      final res = await _dio.get('/api/devices/verify', queryParameters: {
        'token': token,
      });
      return res.data?['valid'] == true;
    } on DioException {
      return false;
    }
  }

  /// Fetch QR code data (base64 PNG + server_url).
  Future<Map<String, dynamic>> getQrCode() async {
    final res = await _dio.get('/api/devices/qr-code', queryParameters: {
      't': DateTime.now().millisecondsSinceEpoch,
    });
    return res.data as Map<String, dynamic>;
  }

  /// Full sync: fetch new stories and preferences since [lastSyncedStoryId].
  ///
  /// Requires a valid device [token].
  Future<Map<String, dynamic>> syncData({
    required String token,
    required int lastSyncedStoryId,
  }) async {
    final res = await _dio.get(
      '/api/devices/sync',
      queryParameters: {
        'token': token,
        'last_synced_story_id': lastSyncedStoryId,
      },
    );
    return res.data as Map<String, dynamic>;
  }

  /// Push read status updates to the server.
  Future<Map<String, dynamic>> syncReadStatus({
    required String token,
    required List<int> readStoryIds,
  }) async {
    final res = await _dio.post(
      '/api/devices/sync/read-status',
      queryParameters: {'token': token},
      data: {
        'read_story_ids': readStoryIds,
      },
    );
    return res.data as Map<String, dynamic>;
  }

  /// Factory reset: tell server to clear pairing data for this device.
  Future<void> resetDevice({
    required String deviceId,
    required String token,
  }) async {
    await _dio.post(
      '/api/devices/$deviceId/reset',
      queryParameters: {'token': token},
    );
  }
}