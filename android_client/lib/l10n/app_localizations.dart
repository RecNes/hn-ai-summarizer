import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import 'supported_locales.dart';

/// Central localization service for Nunti Go.
/// Loads JSON assets (assets/locales/{lang}.json) and provides
/// key-based lookups with automatic English fallback.
class AppLocalizations extends ChangeNotifier {
  AppLocalizations._();

  static final AppLocalizations instance = AppLocalizations._();

  Map<String, String> _strings = {};
  Map<String, String> _enStrings = {};
  String _currentLanguage = SupportedLocale.defaultCode;
  bool _loaded = false;

  String get currentLanguage => _currentLanguage;
  bool get isLoaded => _loaded;
  bool get isRtl => SupportedLocale.isRtl(_currentLanguage);

  /// Load (or reload) the given language. Falls back to English on error.
  Future<void> load(String lang) async {
    if (_enStrings.isEmpty) {
      _enStrings = await _loadJson(SupportedLocale.defaultCode);
    }

    var target = lang;
    if (target.isEmpty) target = SupportedLocale.defaultCode;

    try {
      _strings = await _loadJson(target);
    } catch (_) {
      _strings = _enStrings;
      target = SupportedLocale.defaultCode;
    }

    _currentLanguage = target;
    _loaded = true;
    notifyListeners();
  }

  /// Translate a key. Supports {{placeholder}} replacement via [args].
  /// Falls back to English, then to a raw key marker.
  String t(String key, {Map<String, dynamic>? args}) {
    final String value = _strings[key] ?? _enStrings[key] ?? '<$key>';

    if (args != null && args.isNotEmpty) {
      return args.entries.fold(
        value,
        (acc, entry) => acc.replaceAll('{{${entry.key}}}', '${entry.value}'),
      );
    }
    return value;
  }

  Future<Map<String, String>> _loadJson(String lang) async {
    final data = await rootBundle.loadString('assets/locales/$lang.json');
    final decoded = jsonDecode(data) as Map<String, dynamic>;
    return decoded.map((key, value) => MapEntry(key, value.toString()));
  }
}