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

# Code generation (Drift için)
flutter pub run build_runner build --delete-conflicting-outputs

# Android cihaza/emülatöre yükle
flutter run
```

## İlk Eşleştirme (Pairing)

1. Web uygulamasında `/pairing` sayfasına git (örn: `http://192.168.1.100:8000/pairing`)
2. Sayfada görünen **QR kodu** veya **6 haneli kodu** not al
3. Android uygulamasını aç
4. Sunucu adresini ve eşleştirme kodunu girip "Bağlan"a tıkla
5. Eşleşme tamamlandığında ana ekrana yönlendirileceksin

## Otomatik Senkronizasyon

- Web uygulaması scheduler ile yeni makaleleri çekip çevirdiğinde, bağlı Android cihazlara otomatik bildirim gider
- Android cihaz bu bildirimi alınca yeni makaleleri yerel veritabanına indirir
- Kullanıcıya "N yeni makale hazır" bildirimi gelir
- Aynı ağda olmadığında daha önce indirilmiş makaleler offline okunabilir

## Factory Reset (Yeniden Bağlanma)

İki şekilde tetiklenebilir:

1. **Android uygulamasından**: Ayarlar > "Bağlantıyı Kes ve Sıfırla"
2. **Web uygulamasından**: Pairing sayfası > Cihaz listesinden "Bağlantıyı Kes"

Her iki durumda da:
- Tüm yerel makaleler silinir
- Eşleştirme bilgisi kaldırılır
- Kullanıcı pairing ekranına yönlendirilir
- Sıfırdan QR kod okutarak yeniden bağlanabilir

## API Referansı

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| POST | `/api/devices/register` | Cihaz kaydı + pairing kodu |
| POST | `/api/devices/confirm` | Pairing onayı + JWT token |
| GET | `/api/devices/list` | Eşleşmiş cihaz listesi |
| GET | `/api/devices/qr-code` | Base64 QR kod |
| GET | `/api/devices/sync?token=...` | Senkronizasyon verisi |
| POST | `/api/devices/sync/read-status` | Okunma durumu |
| DELETE | `/api/devices/{id}/revoke` | Bağlantı koparma |
| POST | `/api/devices/{id}/reset` | Factory reset |
| WS | `/api/devices/ws/{id}?token=...` | WebSocket |

## Mimari

```
android_client/lib/
├── main.dart                   # Uygulama giriş noktası, DI
├── app.dart                    # MaterialApp, routing, tema
├── config/theme.dart           # Light/dark tema tanımları
├── models/                     # Veri modelleri
│   ├── story.dart              # Story modeli (fromJson, toJson, copyWith)
│   ├── device.dart             # DeviceInfo modeli
│   ├── sync_state.dart         # SyncState enum + model
│   └── app_settings.dart       # Tema, dil, font ayarları
├── services/                   # İş mantığı katmanı
│   ├── api_service.dart        # Dio HTTP client
│   ├── database_service.dart   # SQLite (sqflite)
│   ├── websocket_service.dart  # WebSocket yönetimi
│   ├── discovery_service.dart  # Ağ keşfi
│   ├── pairing_service.dart    # Pairing akışı
│   ├── sync_service.dart       # Senkronizasyon orkestrasyonu
│   ├── notification_service.dart # Yerel bildirimler
│   └── settings_service.dart   # SharedPreferences
├── providers/                  # State management (ChangeNotifier)
│   ├── story_provider.dart     # Makale listesi
│   ├── sync_provider.dart      # Sync durumu
│   └── settings_provider.dart  # Uygulama ayarları
├── screens/                    # UI ekranları
│   ├── pairing_screen.dart     # Bağlantı ekranı
│   ├── home_screen.dart        # Makale listesi
│   ├── story_detail_screen.dart # Makale detayı
│   └── settings_screen.dart    # Ayarlar
├── widgets/                    # Yeniden kullanılabilir widget'lar
│   ├── story_card.dart         # Makale kartı
│   └── sync_indicator.dart     # Bağlantı durumu ikonu
└── utils/
    ├── constants.dart          # API endpoint, storage key sabitleri
    └── date_formatter.dart     # Tarih formatlama