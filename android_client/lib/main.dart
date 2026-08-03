import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:provider/provider.dart';

import 'app.dart';
import 'l10n/app_localizations.dart';
import 'providers/settings_provider.dart';
import 'providers/story_provider.dart';
import 'providers/sync_provider.dart';
import 'services/api_service.dart';
import 'services/database_service.dart';
import 'services/pairing_service.dart';
import 'services/settings_service.dart';
import 'services/sync_service.dart';
import 'services/discovery_service.dart';
import 'services/websocket_service.dart';
import 'services/notification_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final secureStorage = FlutterSecureStorage();
  final settingsService = SettingsService();
  final databaseService = DatabaseService();
  await databaseService.initialize();

  final apiService = ApiService();
  final pairingService = PairingService(
    apiService: apiService,
    secureStorage: secureStorage,
    settingsService: settingsService,
  );
  final wsService = WebSocketService();
  final discoveryService = DiscoveryService();
  final notificationService = NotificationService();
  await notificationService.initialize();

  final syncService = SyncService(
    apiService: apiService,
    databaseService: databaseService,
    pairingService: pairingService,
    websocketService: wsService,
    settingsService: settingsService,
  );

  final settingsProvider = SettingsProvider(settingsService);
  await settingsProvider.load();

  // Initialize localization with the stored (or default English) language.
  await AppLocalizations.instance.load(settingsProvider.uiLanguage);

  final storyProvider = StoryProvider(databaseService);
  final syncProvider = SyncProvider(
    syncService,
    pairingService,
    notificationService,
    apiService: apiService,
  );

  runApp(
    MultiProvider(
      providers: [
        Provider.value(value: apiService),
        Provider.value(value: pairingService),
        Provider.value(value: discoveryService),
        // Expose the localization service as a provider so widgets can rebuild on locale change.
        ChangeNotifierProvider.value(value: AppLocalizations.instance),
        ChangeNotifierProvider(create: (_) => settingsProvider),
        ChangeNotifierProvider(create: (_) => storyProvider),
        ChangeNotifierProvider(create: (_) => syncProvider),
      ],
      child: const NuntiGoApp(),
    ),
  );
}