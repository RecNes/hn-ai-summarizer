import '../models/story.dart';
import 'api_service.dart';
import 'database_service.dart';
import 'pairing_service.dart';
import 'websocket_service.dart';
import 'settings_service.dart';

/// Orchestrates data synchronization between server and local DB.
class SyncService {
  final ApiService apiService;
  final DatabaseService databaseService;
  final PairingService pairingService;
  final WebSocketService websocketService;
  final SettingsService settingsService;

  SyncService({
    required this.apiService,
    required this.databaseService,
    required this.pairingService,
    required this.websocketService,
    required this.settingsService,
  });

  /// Pull new stories from the server and upsert into local DB.
  /// Returns number of new stories synced.
  Future<int> syncStories() async {
    final token = await pairingService.getStoredToken();
    if (token == null || token.isEmpty) return 0;

    final lastStoryId = await databaseService.getLastStoryId();

    final result = await apiService.syncData(
      token: token,
      lastSyncedStoryId: lastStoryId,
    );

    final rawStories = result['new_stories'] as List<dynamic>? ?? [];
    if (rawStories.isEmpty) return 0;

    // Convert server story maps to Story models
    final stories = rawStories.map((raw) {
      final map = Map<String, dynamic>.from(raw as Map);
      return Story.fromMap(map);
    }).toList();

    await databaseService.upsertStories(stories);
    return stories.length;
  }

  /// Push read status updates to the server.
  /// Returns number of stories the server acknowledged.
  Future<int> syncReadStatus(List<int> storyIds) async {
    if (storyIds.isEmpty) return 0;

    final token = await pairingService.getStoredToken();
    if (token == null || token.isEmpty) return 0;

    final result = await apiService.syncReadStatus(
      token: token,
      readStoryIds: storyIds,
    );
    return (result['updated_stories'] as int?) ?? 0;
  }

  /// Connect the WebSocket for real-time updates.
  Future<void> connectWebSocket() async {
    final token = await pairingService.getStoredToken();
    final serverUrl = await pairingService.getStoredServerUrl();
    final deviceId = await pairingService.getStoredDeviceId();

    if (token == null || serverUrl == null || deviceId == null) return;

    await websocketService.connect(
      serverUrl: serverUrl,
      deviceId: deviceId,
      token: token,
    );
  }

  /// Disconnect the WebSocket.
  Future<void> disconnectWebSocket() async {
    await websocketService.disconnect();
  }
}
