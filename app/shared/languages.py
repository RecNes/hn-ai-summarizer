"""Paylaşılan dil listesi ve dil çözümleyici.

Bu dosya hem backend hem de frontend tarafından kullanılan tek kaynak dil listesidir.
Frontend, bu listeyi /api/settings/ endpoint'inden JSON olarak alır.
"""

LANGUAGES = [
    {"code": "en", "english_name": "English", "native_name": "English"},
    {"code": "tr", "english_name": "Turkish", "native_name": "Türkçe"},
    {"code": "de", "english_name": "German", "native_name": "Deutsch"},
    {"code": "fr", "english_name": "French", "native_name": "Français"},
    {"code": "es", "english_name": "Spanish", "native_name": "Español"},
    {"code": "it", "english_name": "Italian", "native_name": "Italiano"},
    {"code": "pt", "english_name": "Portuguese", "native_name": "Português"},
    {"code": "ru", "english_name": "Russian", "native_name": "Русский"},
    {"code": "uk", "english_name": "Ukrainian", "native_name": "Українська"},
    {"code": "pl", "english_name": "Polish", "native_name": "Polski"},
    {"code": "nl", "english_name": "Dutch", "native_name": "Nederlands"},
    {"code": "cs", "english_name": "Czech", "native_name": "Čeština"},
    {"code": "ar", "english_name": "Arabic", "native_name": "العربية"},
    {"code": "fa", "english_name": "Persian", "native_name": "فارسی"},
    {"code": "hi", "english_name": "Hindi", "native_name": "हिन्दी"},
    {"code": "bn", "english_name": "Bengali", "native_name": "বাংলা"},
    {"code": "zh-CN", "english_name": "Chinese (Simplified)", "native_name": "中文 (Simplified)"},
    {"code": "zh-TW", "english_name": "Chinese (Traditional)", "native_name": "中文 (Traditional)"},
    {"code": "ja", "english_name": "Japanese", "native_name": "日本語"},
    {"code": "ko", "english_name": "Korean", "native_name": "한국어"},
]


def get_languages():
    """Dil listesini döndürür."""
    return LANGUAGES


class TranslationLanguageResolver:
    """Dil kodunu AI prompt'unda kullanılacak okunabilir isme çevirir.

    Örnek: "ja" → "Japanese", "tr" → "Turkish"
    """

    @staticmethod
    def get_language_name(code: str) -> str:
        """Verilen dil kodunun İngilizce ismini döndürür."""
        for lang in LANGUAGES:
            if lang["code"] == code:
                return lang["english_name"]
        return "English"  # fallback

    @staticmethod
    def get_native_name(code: str) -> str:
        """Verilen dil kodunun yerel ismini döndürür."""
        for lang in LANGUAGES:
            if lang["code"] == code:
                return lang["native_name"]
        return "English"