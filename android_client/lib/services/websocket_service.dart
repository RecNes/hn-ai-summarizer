import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../utils/url_helper.dart';

/// WebSocket client for real-time communication with the server.
///
/// Connects to `/api/devices/ws/{deviceId}?token={token}`.
/// Handles keepalive pings and incoming messages.
class WebSocketService {
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  Timer? _pingTimer;

  bool _connected = false;

  /// Message stream for incoming server messages (e.g. sync_trigger, revoked).
  final _messageController = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get messages => _messageController.stream;

  bool get isConnected => _connected;

  /// Connect to the server WebSocket endpoint.
  Future<void> connect({
    required String serverUrl,
    required String deviceId,
    required String token,
  }) async {
    await disconnect();

    final wsBase = UrlHelper.toWebSocketUrl(serverUrl);
    final wsUrl = '$wsBase/api/devices/ws/$deviceId?token=$token';

    try {
      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));

      _subscription = _channel!.stream.listen(
        _onMessage,
        onDone: _onDisconnected,
        onError: (Object _) => _onDisconnected(),
      );

      _connected = true;

      // Keepalive ping every 30s
      _pingTimer = Timer.periodic(const Duration(seconds: 30), (_) {
        _send({'type': 'ping'});
      });
    } catch (_) {
      _connected = false;
    }
  }

  /// Disconnect and clean up resources.
  Future<void> disconnect() async {
    _pingTimer?.cancel();
    _pingTimer = null;

    await _subscription?.cancel();
    _subscription = null;

    await _channel?.sink.close();
    _channel = null;

    _connected = false;
  }

  /// Send a raw JSON message through the socket.
  void _send(Map<String, dynamic> data) {
    if (!_connected || _channel == null) return;
    try {
      _channel!.sink.add(jsonEncode(data));
    } catch (_) {
      // Ignore send errors — will surface via onDone
    }
  }

  /// Send a ping message.
  void ping() => _send({'type': 'ping'});

  /// Notify the server that stories were read.
  void sendReadStatus(List<int> storyIds) {
    if (storyIds.isEmpty) return;
    _send({
      'type': 'read_status',
      'read_story_ids': storyIds,
    });
  }

  /// Request a full sync trigger from the server.
  void requestSync() {
    _send({
      'type': 'sync_request',
      'timestamp': DateTime.now().toIso8601String(),
    });
  }

  void _onMessage(dynamic raw) {
    try {
      final decoded = jsonDecode(raw as String) as Map<String, dynamic>;
      if (decoded['type'] == 'pong') return; // keepalive response
      _messageController.add(decoded);
    } catch (_) {
      // Ignore malformed messages
    }
  }

  void _onDisconnected() {
    final wasConnected = _connected;
    _connected = false;
    if (wasConnected) {
      _messageController.add({'type': 'disconnected'});
    }
  }

  void dispose() {
    _messageController.close();
    disconnect();
  }
}