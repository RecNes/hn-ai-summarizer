import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Local notification service for new story alerts.
class NotificationService {
  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();

  bool _initialized = false;

  bool get isInitialized => _initialized;

  /// Initialize the notification plugin and request permissions.
  Future<void> initialize() async {
    if (_initialized) return;

    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const settings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _plugin.initialize(settings);
    _initialized = true;
  }

  /// Show a notification that new stories are available.
  Future<void> showNewStoriesNotification(int count) async {
    if (!_initialized) return;
    if (count <= 0) return;

    await _plugin.show(
      1,
      'Yeni Makaleler',
      count == 1
          ? '1 yeni makale seni bekliyor.'
          : '$count yeni makale seni bekliyor.',
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'new_stories',
          'Yeni Makaleler',
          channelDescription: 'Sunucudan yeni makale geldiğinde bildir',
          importance: Importance.high,
          priority: Priority.high,
        ),
        iOS: DarwinNotificationDetails(),
      ),
    );
  }

  /// Show a generic sync status notification.
  Future<void> showSyncNotification(String message) async {
    if (!_initialized) return;

    await _plugin.show(
      2,
      'Senkronizasyon',
      message,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'sync_status',
          'Senkronizasyon',
          channelDescription: 'Senkronizasyon durumu bildirimleri',
          importance: Importance.defaultImportance,
          priority: Priority.defaultPriority,
        ),
        iOS: DarwinNotificationDetails(),
      ),
    );
  }
}