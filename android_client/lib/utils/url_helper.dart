/// URL normalizasyon yardımcıları.
///
/// Proxy / ters-proxy kurulumlarında `PUBLIC_URL` bazen `:0` portu ile
/// üretilebilir (örn. `https://domain:0`). Bu helper geçersiz portu
/// temizler ve WebSocket URL'lerini doğru scheme ile üretir.
class UrlHelper {
  UrlHelper._();

  /// Geçersiz `:0` portunu temizleyip normalleştirilmiş URL döndürür.
  ///
  /// `https://domain:0/path` → `https://domain/path`
  /// `http://host:0` → `http://host`
  static String normalizeBaseUrl(String url) {
    final cleaned = url.trim().replaceAll(RegExp(r'/+$'), '');
    final uri = Uri.tryParse(cleaned);
    if (uri == null) return cleaned;

    if (uri.port == 0) {
      // Port 0 geçersiz — portu kaldır (https→443, http→80 varsayılır)
      final builder = Uri(
        scheme: uri.scheme,
        host: uri.host,
        port: null,
        path: uri.path,
        query: uri.query,
        fragment: uri.fragment,
      );
      return builder.toString().replaceAll(RegExp(r'/+$'), '');
    }

    return cleaned;
  }

  /// HTTP(S) URL'sini WebSocket URL'sine çevirir.
  ///
  /// `https://domain` → `wss://domain`
  /// `http://host:8000` → `ws://host:8000`
  static String toWebSocketUrl(String baseUrl) {
    final normalized = normalizeBaseUrl(baseUrl);

    if (normalized.startsWith('https://')) {
      return 'wss://${normalized.substring(8)}';
    }
    if (normalized.startsWith('http://')) {
      return 'ws://${normalized.substring(7)}';
    }
    // Zaten ws/wss — aynen döndür
    return normalized;
  }
}