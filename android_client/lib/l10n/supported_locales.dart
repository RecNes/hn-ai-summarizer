/// Supported UI languages for Nunti Go.
/// Codes match the WebApp locale folder names under app/static/locales/.
class SupportedLocale {
  final String code;
  final String name;

  const SupportedLocale(this.code, this.name);

  static const List<SupportedLocale> all = [
    SupportedLocale('ar', 'العربية'),
    SupportedLocale('bn', 'বাংলা'),
    SupportedLocale('cs', 'Čeština'),
    SupportedLocale('de', 'Deutsch'),
    SupportedLocale('en', 'English'),
    SupportedLocale('es', 'Español'),
    SupportedLocale('fa', 'فارسی'),
    SupportedLocale('hi', 'हिन्दी'),
    SupportedLocale('it', 'Italiano'),
    SupportedLocale('ja', '日本語'),
    SupportedLocale('ko', '한국어'),
    SupportedLocale('nl', 'Nederlands'),
    SupportedLocale('pl', 'Polski'),
    SupportedLocale('pt', 'Português'),
    SupportedLocale('ru', 'Русский'),
    SupportedLocale('tr', 'Türkçe'),
    SupportedLocale('uk', 'Українська'),
    SupportedLocale('zh-CN', '简体中文'),
    SupportedLocale('zh-TW', '繁體中文'),
  ];

  /// Default and fallback language.
  static const String defaultCode = 'en';

  /// RTL languages.
  static bool isRtl(String code) => code == 'ar' || code == 'fa';

  static String? displayName(String code) {
    for (final loc in all) {
      if (loc.code == code) return loc.name;
    }
    return null;
  }
}