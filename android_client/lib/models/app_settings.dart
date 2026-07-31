import 'package:flutter/material.dart';

/// Application settings model.
class AppSettings {
  final String uiLanguage;
  final ThemeMode themeMode;
  final double fontSize;
  final String fontFamily;

  const AppSettings({
    this.uiLanguage = 'en',
    this.themeMode = ThemeMode.system,
    this.fontSize = 16.0,
    this.fontFamily = 'Inter',
  });
}