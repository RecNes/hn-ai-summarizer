import 'package:shared_preferences/shared_preferences.dart';

/// Manages app preferences via SharedPreferences.
class SettingsService {
  Future<String> getUiLanguage() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('ui_language') ?? 'en';
  }

  Future<void> setUiLanguage(String lang) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('ui_language', lang);
  }

  Future<String> getThemeMode() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('theme_mode') ?? 'system';
  }

  Future<void> setThemeMode(String mode) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('theme_mode', mode);
  }

  Future<double> getFontSize() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getDouble('font_size') ?? 16.0;
  }

  Future<void> setFontSize(double size) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble('font_size', size);
  }

  // ── Pairing data fallback storage ─────────

  /// Get a pairing-related value from shared preferences.
  Future<String?> getPairingValue(String key) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('pairing_$key');
  }

  /// Set a pairing-related value in shared preferences.
  Future<void> setPairingValue(String key, String value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('pairing_$key', value);
  }

  /// Remove a pairing-related value from shared preferences.
  Future<void> removePairingValue(String key) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('pairing_$key');
  }
}
