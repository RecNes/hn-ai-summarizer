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

    // Base typography from Flutter's defaults, then scale all sizes
    // relative to the user-selected font size (13..22).
    final baseTheme = isDark ? ThemeData.dark() : ThemeData.light();
    final baseText = baseTheme.textTheme;

    final textTheme = baseText.copyWith(
      // Large title (e.g. detail screen title)
      headlineMedium: baseText.headlineMedium?.copyWith(
        fontSize: fontSize + 8,
        fontWeight: FontWeight.w700,
      ),
      // Screen / section titles
      titleLarge: baseText.titleLarge?.copyWith(fontSize: fontSize + 6),
      titleMedium: baseText.titleMedium?.copyWith(
        fontSize: fontSize + 4,
        fontWeight: FontWeight.w600,
      ),
      titleSmall: baseText.titleSmall?.copyWith(fontSize: fontSize + 2),
      // Regular body text (story cards, content)
      bodyLarge: baseText.bodyLarge?.copyWith(fontSize: fontSize + 1),
      bodyMedium: baseText.bodyMedium?.copyWith(fontSize: fontSize),
      // Small / meta text
      bodySmall: baseText.bodySmall?.copyWith(fontSize: fontSize - 2),
      labelLarge: baseText.labelLarge?.copyWith(fontSize: fontSize),
      labelSmall: baseText.labelSmall?.copyWith(fontSize: fontSize - 3),
    );

    return ThemeData(
      brightness: brightness,
      useMaterial3: true,
      colorSchemeSeed: const Color(0xFF2196F3),
      textTheme: textTheme,
      scaffoldBackgroundColor:
          isDark ? const Color(0xFF121212) : const Color(0xFFF5F5F5),
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: 0,
        backgroundColor:
            isDark ? const Color(0xFF1E1E1E) : const Color(0xFF2196F3),
        foregroundColor: Colors.white,
        titleTextStyle: TextStyle(
          fontSize: fontSize + 4,
          fontWeight: FontWeight.w600,
          color: Colors.white,
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }
}