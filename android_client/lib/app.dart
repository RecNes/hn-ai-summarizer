import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';

import 'config/theme.dart';
import 'l10n/app_localizations.dart';
import 'providers/settings_provider.dart';
import 'providers/sync_provider.dart';
import 'screens/home_screen.dart';
import 'screens/pairing_screen.dart';
import 'screens/splash_screen.dart';
import 'services/discovery_service.dart';
import 'services/pairing_service.dart';

class NuntiGoApp extends StatelessWidget {
  const NuntiGoApp({super.key});

  @override
  Widget build(BuildContext context) {
    // Rebuild whole app when locale changes.
    return Consumer<AppLocalizations>(
      builder: (context, l10n, _) {
        return Consumer<SettingsProvider>(
          builder: (context, settings, _) {
            return MaterialApp(
              title: 'Nunti Go',
              debugShowCheckedModeBanner: false,
              locale: Locale(l10n.currentLanguage),
              supportedLocales: const [
                Locale('ar'), Locale('bn'), Locale('cs'), Locale('de'),
                Locale('en'), Locale('es'), Locale('fa'), Locale('hi'),
                Locale('it'), Locale('ja'), Locale('ko'), Locale('nl'),
                Locale('pl'), Locale('pt'), Locale('ru'), Locale('tr'),
                Locale('uk'), Locale('zh', 'CN'), Locale('zh', 'TW'),
              ],
              localizationsDelegates: const [
                GlobalMaterialLocalizations.delegate,
                GlobalWidgetsLocalizations.delegate,
                GlobalCupertinoLocalizations.delegate,
              ],
              theme: AppTheme.lightTheme(settings.fontSize),
              darkTheme: AppTheme.darkTheme(settings.fontSize),
              themeMode: settings.themeMode,
              home: const _AppEntry(),
            );
          },
        );
      },
    );
  }
}

/// Top-level widget managing splash → main app transition.
class _AppEntry extends StatefulWidget {
  const _AppEntry();

  @override
  State<_AppEntry> createState() => _AppEntryState();
}

class _AppEntryState extends State<_AppEntry> {
  bool _showSplash = true;

  @override
  void initState() {
    super.initState();
    // Use post-frame callback to avoid build-time state changes
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkToken();
    });
  }

  Future<void> _checkToken() async {
    final syncProvider = context.read<SyncProvider>();
    await syncProvider.checkStoredToken();
  }

  void _onSplashFinished() {
    setState(() => _showSplash = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_showSplash) {
      final settings = context.watch<SettingsProvider>();
      return SplashScreen(
        onFinished: _onSplashFinished,
        uiLanguage: settings.uiLanguage,
      );
    }

    final syncProvider = context.watch<SyncProvider>();

    // Still checking token — show blank / loader
    if (syncProvider.isChecking) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    // Pairing not done → pairing screen
    if (!syncProvider.isPaired) {
      return PairingScreen(
        pairingService: context.read<PairingService>(),
        discoveryService: context.read<DiscoveryService>(),
      );
    }

    // Paired → main app
    return const AppShell();
  }
}

class AppShell extends StatelessWidget {
  const AppShell({super.key});

  @override
  Widget build(BuildContext context) {
    // Bottom nav kaldırıldı — Settings ikonu HomeScreen'in AppBar'ında
    return const HomeScreen();
  }
}
