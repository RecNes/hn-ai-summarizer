import 'package:flutter/material.dart';

import '../services/settings_service.dart';

/// Manages application-wide settings.
class SettingsProvider extends ChangeNotifier {
  final SettingsService _settingsService;

  String _uiLanguage = 'en';
  ThemeMode _themeMode = ThemeMode.system;
  double _fontSize = 16.0;

  SettingsProvider(this._settingsService);

  String get uiLanguage => _uiLanguage;
  ThemeMode get themeMode => _themeMode;
  double get fontSize => _fontSize;

  Future<void> load() async {
    _uiLanguage = await _settingsService.getUiLanguage();
    final themeStr = await _settingsService.getThemeMode();
    _themeMode = _parseThemeMode(themeStr);
    _fontSize = await _settingsService.getFontSize();
    notifyListeners();
  }

  /// Set UI language (persisted).
  Future<void> setUiLanguage(String lang) async {
    if (lang == _uiLanguage) return;
    _uiLanguage = lang;
    await _settingsService.setUiLanguage(lang);
    notifyListeners();
  }

  /// Set theme mode (persisted).
  Future<void> setThemeMode(ThemeMode mode) async {
    if (mode == _themeMode) return;
    _themeMode = mode;
    await _settingsService.setThemeMode(_serializeThemeMode(mode));
    notifyListeners();
  }

  /// Set base font size (persisted).
  Future<void> setFontSize(double size) async {
    if (size == _fontSize) return;
    _fontSize = size;
    await _settingsService.setFontSize(size);
    notifyListeners();
  }

  ThemeMode _parseThemeMode(String mode) {
    switch (mode) {
      case 'light':
        return ThemeMode.light;
      case 'dark':
        return ThemeMode.dark;
      default:
        return ThemeMode.system;
    }
  }

  String _serializeThemeMode(ThemeMode mode) {
    switch (mode) {
      case ThemeMode.light:
        return 'light';
      case ThemeMode.dark:
        return 'dark';
      case ThemeMode.system:
        return 'system';
    }
  }
}