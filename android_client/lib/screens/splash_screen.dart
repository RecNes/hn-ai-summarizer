import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../utils/constants.dart';

/// Splash screen shown on app startup.
/// Displays logo, app name, localized description, loader, and version.
class SplashScreen extends StatefulWidget {
  final VoidCallback onFinished;
  final String uiLanguage;

  const SplashScreen({
    super.key,
    required this.onFinished,
    required this.uiLanguage,
  });

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  String _description = '';

  @override
  void initState() {
    super.initState();
    _loadLocale();
    // Navigate after 5 seconds
    Future.delayed(const Duration(seconds: 5), widget.onFinished);
  }

  Future<void> _loadLocale() async {
    try {
      final lang = widget.uiLanguage;
      String data;
      try {
        data = await rootBundle.loadString('assets/locales/$lang.json');
      } catch (_) {
        data = await rootBundle.loadString('assets/locales/en.json');
      }
      final json = jsonDecode(data) as Map<String, dynamic>;
      final splash = json['splash'] as Map<String, dynamic>;
      setState(() {
        _description = splash['description'] as String? ?? '';
      });
    } catch (_) {
      setState(() {
        _description = 'Take your daily AI-summarized\narticles offline with you';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Image.asset('assets/logo.png', width: 120, height: 120),
              const SizedBox(height: 32),
              Text(
                AppConstants.appName,
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  color: isDark ? Colors.white : const Color(0xFF212121),
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                _description,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 14,
                  color: isDark ? Colors.grey[400] : Colors.grey[600],
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 48),
              SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    isDark ? Colors.grey[400]! : const Color(0xFF2196F3),
                  ),
                ),
              ),
              const SizedBox(height: 48),
              Text(
                'v${AppConstants.version}',
                style: TextStyle(
                  fontSize: 12,
                  color: isDark ? Colors.grey[600] : Colors.grey[400],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}