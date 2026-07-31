import 'package:flutter/material.dart';

/// Centralized theme configuration.
class AppTheme {
  AppTheme._();

  static ThemeData lightTheme(double fontSize) => _buildTheme(
        brightness: Brightness.light,
        fontSize: fontSize,
      );

  static ThemeData darkTheme(double fontSize) => _buildTheme(
        brightness: Brightness.dark,
        fontSize: fontSize,
      );

  static ThemeData _buildTheme({
    required Brightness brightness,
    required double fontSize,
  }) {
    final isDark = brightness == Brightness.dark;

    return ThemeData(
      brightness: brightness,
      useMaterial3: true,
      colorSchemeSeed: const Color(0xFF2196F3),
      scaffoldBackgroundColor:
          isDark ? const Color(0xFF121212) : const Color(0xFFF5F5F5),
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: 0,
        backgroundColor:
            isDark ? const Color(0xFF1E1E1E) : const Color(0xFF2196F3),
        foregroundColor: Colors.white,
      ),
      cardTheme: CardThemeData(
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }
}