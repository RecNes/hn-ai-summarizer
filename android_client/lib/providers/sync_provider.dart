import 'dart:async';

import 'package:flutter/foundation.dart';

import '../services/sync_service.dart';
import '../services/pairing_service.dart';
import '../services/api_service.dart';
import '../services/notification_service.dart';
import '../utils/constants.dart';

/// Manages sync state and pairing status.
class SyncProvider extends ChangeNotifier {
  final SyncService _syncService;
  final PairingService _pairingService;
  final NotificationService _notificationService;
  final ApiService apiService;

  SyncStatus _status = SyncStatus.idle;
  bool _isPaired = false;
  bool _isChecking = true;
  StreamSubscription? _wsSubscription;

  SyncProvider(
    this._syncService,
    this._pairingService,
    this._notificationService, {
    required this.apiService,
  });

  SyncStatus get status => _status;
  bool get isPaired => _isPaired;
  bool get isChecking => _isChecking;

  /// Check if device has stored token → verify with server → mark paired or clear.
  Future<void> checkStoredToken() async {
    _isChecking = true;
    notifyListeners();

    try {
      final hasToken = await _pairingService.hasStoredToken();

      if (!hasToken) {
        _isPaired = false;
        _isChecking = false;
        notifyListeners();
        return;
      }

      // Token exists — verify with server
      final token = await _pairingService.getStoredToken();
      final serverUrl = await _pairingService.getStoredServerUrl();

      if (token == null || serverUrl == null) {
        await _pairingService.clearPairing();
        _isPaired = false;
        _isChecking = false;
        notifyListeners();
        return;
      }

      // Try to verify token with server
      apiService.updateBaseUrl(serverUrl);
      final isValid = await apiService.verifyToken(token);

      if (isValid) {
        _isPaired = true;
        unawaited(_connectWebSocket());
      } else {
        // Token invalid (revoked/expired) → clear local data
        await _pairingService.clearPairing();
        _isPaired = false;
      }
    } catch (_) {
      // Network error or server unreachable → assume paired if token exists
      // Will be re-verified on next app launch when network is available
      final hasToken = await _pairingService.hasStoredToken();
      _isPaired = hasToken;
    }

    _isChecking = false;
    notifyListeners();
  }

  /// Mark device as paired (called after successful pairing).
  Future<void> setPaired(bool paired) async {
    _isPaired = paired;
    notifyListeners();

    if (paired) {
      unawaited(_connectWebSocket());
      unawaited(syncNow());
    } else {
      await _syncService.disconnectWebSocket();
    }
  }

  /// Perform a full sync: pull new stories, push read status, notify.
  /// Returns number of new stories synced, or -1 on failure.
  Future<int> syncNow() async {
    _status = SyncStatus.syncing;
    notifyListeners();

    try {
      final newCount = await _syncService.syncStories();

      // Notify about new stories
      if (newCount > 0) {
        await _notificationService.showNewStoriesNotification(newCount);
      }

      _status = SyncStatus.idle;
      notifyListeners();
      return newCount;
    } catch (_) {
      _status = SyncStatus.error;
      notifyListeners();
      return -1;
    }
  }

  /// Push read status to server (best-effort).
  Future<void> pushReadStatus(List<int> storyIds) async {
    if (storyIds.isEmpty) return;

    try {
      await _syncService.syncReadStatus(storyIds);
    } catch (_) {
      // Best-effort — will be re-synced on next full sync
    }
  }

  Future<void> _connectWebSocket() async {
    await _syncService.connectWebSocket();

    // Listen for incoming WS messages
    _wsSubscription?.cancel();
    _wsSubscription = _syncService.websocketService.messages.listen((msg) {
      final type = msg['type'];
      if (type == 'sync_trigger') {
        unawaited(syncNow());
      } else if (type == 'revoked') {
        // Device was revoked from web app → clear pairing
        unawaited(_handleRevoked());
      }
    });
  }

  Future<void> _handleRevoked() async {
    await _pairingService.clearPairing();
    _isPaired = false;
    notifyListeners();
  }

  /// Clear all pairing data (used from settings).
  Future<void> clearPairing() async {
    await _syncService.disconnectWebSocket();
    await _pairingService.clearPairing();
    _isPaired = false;
    notifyListeners();
  }

  @override
  void dispose() {
    _wsSubscription?.cancel();
    super.dispose();
  }
}