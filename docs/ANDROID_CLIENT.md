# Android Client — Kurulum ve Kullanım Kılavuzu

## Genel Bakış

HN Reader Android istemcisi, home lab'ınızdaki web uygulamasıyla otomatik olarak senkronize olan offline-first bir mobil uygulamadır. 
Makaleleri yerel olarak depolar, internet bağlantısı olmadan okumanızı sağlar ve aynı ağa döndüğünüzde okunma durumlarınızı otomatik olarak web uygulamasına aktarır.

## Gereksinimler

- **Flutter SDK 3.24+**: `C:\Users\sence\Personal-Projects\flutter`
- **Android SDK**: API 21+ (Android 5.0+)
- **Web App**: hn-reader web uygulamasının aynı ağda çalışıyor olması

## Kurulum (Flutter)

```bash
# Proje dizinine git
cd android_client

# Bağımlılıkları yükle
flutter pub get

# Android cihaza/emülatöre yükle
flutter run
```

## İlk Eşleştirme (Pairing)

1. Web uygulamasında `/pairing` sayfasına git (örn: `http://192.168.1.100:8000/pairing`)
2. Sayfada görünen **QR kodu** veya **6 haneli kodu** not al
3. Android uygulamasını aç
4. Sunucu adresini ve eşleştirme kodunu girip "Devam Et"e tıkla — QR okutulursa kod ve sunucu adresi otomatik doldurulur, eşleştirme otomatik başlar
5. Eşleşme tamamlandığında ana ekrana yönlendirileceksin ve ilk senkronizasyon otomatik başlar

> **Not:** HNS Take Away, web UI'da gösterilen kodla cihazdaki kodu birebir eşleştirir.
> `register` isteğinde `pairing_code` alanı ile web'de üretilen kod sunucuya iletilir
> ve cihaz bu kodla eşleştirilir. Böylece QR/manuel girilen kod ile sunucudaki kod arasındaki
> uyumsuzluk sorunu ortadan kalkar.

## Otomatik Senkronizasyon

- Web uygulaması scheduler ile yeni makaleleri çekip çevirdiğinde, bağlı Android cihazlara WebSocket üzerinden `sync_trigger` bildirimi gider
- Android cihaz bu bildirimi alınca `syncNow()` tetiklenir ve yeni makaleleri yerel SQLite veritabanına indirir
- Kullanıcıya "N yeni makale hazır" yerel bildirimi gelir (`NotificationService`)
- Okunan makaleler (detay ekranı açıldığında) WebSocket `read_status` mesajı ve `sync/read-status` REST çağrısıyla sunucuya iletilir
- Aynı ağda olmadığında daha önce indirilmiş makaleler offline okunabilir
- Eşleştirilmiş cihaz web arayüzünden iptal edilirse (`revoked` mesajı) cihaz eşleştirmeyi kaldırıp pairing ekranına döner

## Factory Reset (Yeniden Bağlanma)

İki şekilde tetiklenebilir:

1. **Android uygulamasından**: Ayarlar > "Yeniden Eşleştir" (onay dialog'u ile)
2. **Web uygulamasından**: Pairing sayfası > Cihaz listesinden "Bağlantıyı Kes"

Her iki durumda da:
- WebSocket bağlantısı kapatılır
- Eşleştirme bilgisi (token, sunucu, cihaz kimliği) temizlenir
- Kullanıcı pairing ekranına yönlendirilir
- Sıfırdan QR kod okutarak yeniden bağlanabilir

## API Referansı

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| POST | `/api/devices/register` | Cihaz kaydı + pairing kodu (`pairing_code` opsiyoneldir) |
| POST | `/api/devices/confirm` | Pairing onayı + JWT token |
| GET | `/api/devices/list` | Eşleşmiş cihaz listesi |
| GET | `/api/devices/qr-code` | Base64 QR kod |
| GET | `/api/devices/sync?token=...` | Senkronizasyon verisi |
| POST | `/api/devices/sync/read-status` | Okunma durumu |
| DELETE | `/api/devices/{id}/revoke` | Bağlantı koparma |
| POST | `/api/devices/{id}/reset` | Factory reset |
| WS | `/api/devices/ws/{id}?token=...` | WebSocket |

## Mimari (Mevcut Durum)

```
android_client/lib/
├── main.dart                   # Uygulama giriş noktası, DI (provider wiring)
├── app.dart                    # MaterialApp, splash → pairing → shell akışı
├── config/theme.dart           # Light/dark tema (Material 3, mavi seed)
├── models/                     # Veri modelleri
│   ├── story.dart              # Story (fromMap, toMap)
│   ├── device.dart             # DeviceInfo
│   └── app_settings.dart       # Uygulama ayarları modeli
├── services/                   # İş mantığı katmanı
│   ├── api_service.dart        # Dio HTTP client (register/confirm/sync/read-status/reset)
│   ├── database_service.dart   # SQLite (sqflite) — upsert/get/mark-read/clear
│   ├── websocket_service.dart  # WebSocket — ping 30s, read_status, sync_request, revoked
│   ├── discovery_service.dart  # Ağ keşfi (istersen elle URL girilir)
│   ├── pairing_service.dart    # Pairing akışı (QR data çözümleme, dual storage)
│   ├── sync_service.dart       # Senkronizasyon orkestrasyonu (REST + WS)
│   ├── notification_service.dart # flutter_local_notifications (yeni makale, sync)
│   └── settings_service.dart   # SharedPreferences (tema, dil, font, pairing fallback)
├── providers/                  # State management (ChangeNotifier)
│   ├── story_provider.dart     # Makale listesi (load/refresh/mark-as-read)
│   ├── sync_provider.dart      # Sync durumu, WS dinleme, revoked handling
│   └── settings_provider.dart  # Tema/dil/font ayarları (persisted)
├── screens/                    # UI ekranları
│   ├── splash_screen.dart      # Logo + gecikme
│   ├── pairing_screen.dart     # QR okuma + manuel giriş + sunucu arama
│   ├── home_screen.dart        # Offline makale listesi (refresh, boş/hata durumları)
│   ├── story_detail_screen.dart # İçerik, çeviri, yorum analizi, orijinal link
│   └── settings_screen.dart    # Tema, dil, font, yeniden eşleştir
├── widgets/                    # Yeniden kullanılabilir widget'lar
│   ├── story_card.dart         # Makale kartı (read indicator, TR rozeti, puan)
│   └── sync_indicator.dart     # Bağlantı durumu ikonu
└── utils/
    ├── constants.dart          # Uygulama adı, versiyon, SyncStatus enum
    └── date_formatter.dart     # Göreli tarih formatlama (dk/saat/gün)