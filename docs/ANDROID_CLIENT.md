# Nunti Go — Android Client

Setup & usage guide for the Nunti Go Android app.

## Overview

Nunti Go is the **offline-first** mobile companion for the Nunti web application running in your home lab. It stores articles locally on your device so you can read them **without an internet connection**, and automatically syncs your reading progress back to the web app when you are on the same network again.

## Requirements

- **Flutter SDK 3.24+** (e.g. `C:\Users\sence\Personal-Projects\flutter`)
- **Android SDK**: API 26+ (Android 8.0+)
- **Web app**: nunti running on your network

## Setup (Flutter)

```bash
# Navigate to the project
cd android_client

# Install dependencies
flutter pub get

# Build & run on your device / emulator
flutter run
```

## First-Time Pairing

1. Open the `/pairing` page in the web app (e.g. `http://192.168.1.100:8000/pairing`)
2. Note the **QR code** or the **6-digit pairing code** shown on the page
3. Open the Android app
4. Enter the server address and pairing code, tap **"Devam Et" (Continue)**
   - If you scan the QR code, the server URL and pairing code are filled automatically and pairing starts immediately
5. When pairing completes you are taken to the home screen and the first sync starts automatically

> **Note:** Nunti Go keeps the code shown in the web UI and the code used by the device in sync.
> The `register` request sends the code produced on the web (`pairing_code` field) to the server,
> and the device is paired with that code. This eliminates any mismatch between the QR/manual code
> and the server-side code.

## Network Configuration

- **Cleartext HTTP**: The app allows plain `http://` connections (`usesCleartextTraffic="true"`) so it can pair and sync with a LAN server directly by IP (e.g. `http://192.168.1.100:8000`).
- **Firebase/ML telemetry**: All automatic telemetry collection (Analytics, Crashlytics, Performance, ML Kit) is **disabled** in the app manifest. No data leaves your device.

## Automatic Sync

- When the web app scheduler fetches and translates new articles, paired Android devices receive a `sync_trigger` message over **WebSocket**
- On receipt, the app calls `syncNow()` and downloads new articles into the local **SQLite** database
- The user gets a **"N yeni makale hazır"** local notification (`NotificationService`)
- Opening a story detail marks it as read locally and pushes the read status to the server via WebSocket `read_status` and the `sync/read-status` REST endpoint
- If the device is off the network, previously downloaded articles can be read offline
- If the device is revoked from the web UI (`revoked` message), the app clears pairing and returns to the pairing screen

## Font Size Setting

- The **Yazı Boyutu (Font Size)** slider in Settings (13–22 pt) is fully functional.
- The selected value is baked into the app `TextTheme` and applied to:
  - Story list cards (`story_card.dart`)
  - Story detail title, content, comments summary, and meta chips (`story_detail_screen.dart`)
  - AppBar title
- No hard-coded font sizes remain on those screens — everything is theme-driven.

## Factory Reset / Re-Pairing

Can be triggered in two ways:

1. **From the Android app**: Settings > **"Yeniden EÅŸleÅŸtir"** (with confirmation dialog)
2. **From the web app**: Pairing page > "Revoke" on the device list

In both cases:
- The WebSocket connection is closed
- Pairing data (token, server URL, device ID) is cleared
- The user is returned to the pairing screen
- They can pair again by scanning a fresh QR code

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/devices/register` | Device registration + pairing code (`pairing_code` is optional) |
| POST | `/api/devices/confirm` | Pairing confirmation + JWT token |
| GET | `/api/devices/list` | List paired devices |
| GET | `/api/devices/qr-code` | Base64 QR code |
| GET | `/api/devices/sync?token=...` | Sync data (new stories since last id) |
| POST | `/api/devices/sync/read-status` | Push read status |
| DELETE | `/api/devices/{id}/revoke` | Revoke a device |
| POST | `/api/devices/{id}/reset` | Factory reset |
| WS | `/api/devices/ws/{id}?token=...` | WebSocket (sync_trigger, revoked, ping/pong) |

## Architecture (Current State)

```
android_client/lib/
├── main.dart                     # App entry point, DI / provider wiring
├── app.dart                      # MaterialApp, splash → pairing → shell flow
├── config/theme.dart             # Light/dark theme (Material 3, blue seed); font-size scaled TextTheme
├── models/                       # Data models
│   ├── story.dart                # Story (fromMap/toMap, bool/int tolerant _asBool)
│   ├── device.dart               # DeviceInfo
│   └── app_settings.dart         # App settings model
├── services/                     # Business logic layer
│   ├── api_service.dart          # Dio HTTP client (register/confirm/sync/read-status/reset; URL normalized)
│   ├── database_service.dart     # SQLite (sqflite) — upsert/get/mark-read/clear/last-id
│   ├── websocket_service.dart    # WebSocket — 30s ping, sync_trigger, revoked, read_status (wss/ws via UrlHelper)
│   ├── discovery_service.dart    # LAN server discovery (manual URL entry is the primary path)
│   ├── pairing_service.dart      # Pairing flow (QR data parsing, dual storage, stored-device-id)
│   ├── sync_service.dart         # Sync orchestration (REST + WS)
│   ├── notification_service.dart # flutter_local_notifications (new stories, sync status)
│   └── settings_service.dart     # SharedPreferences (theme, language, font, pairing fallback)
├── providers/                    # State management (ChangeNotifier)
│   ├── story_provider.dart       # Story list (load/refresh/mark-as-read)
│   ├── sync_provider.dart        # Sync status, WS listening, revoked handling, lastSyncError
│   └── settings_provider.dart    # Theme/language/font settings (persisted; setter methods)
├── screens/                      # UI screens
│   ├── splash_screen.dart        # Logo + loading
│   ├── pairing_screen.dart       # QR scan + manual entry + server discovery
│   ├── home_screen.dart          # Offline story list (pull-to-refresh, empty/error states; settings top-right)
│   ├── story_detail_screen.dart  # Content, translation, comments analysis, original link; theme-driven fonts
│   └── settings_screen.dart      # Theme, language, font size, re-pair
├── widgets/                      # Reusable widgets
│   ├── story_card.dart           # Story card (read indicator, TR badge, score; theme-driven fonts)
│   └── sync_indicator.dart       # Connection status icon
└── utils/
    ├── constants.dart            # App name, version, SyncStatus enum
    ├── url_helper.dart           # URL normalization (:0 port fix), http→ws / https→wss conversion
    └── date_formatter.dart       # Relative date formatting (min/hour/day)
```

## Notes / Known Fixes

- **`:0` port fix**: The server now sanitizes `PUBLIC_URL` when it contains an invalid `:0` port (`_public_server_url()` in `app/api/routes/devices.py`); the client also normalizes URLs via `UrlHelper` (used by both REST and WebSocket paths).
- **Boolean/Integer tolerance**: `Story.fromMap` accepts both server JSON booleans (`true`/`false`) and SQLite integers (`0`/`1`) for flag fields (fixes `type 'bool' is not a subtype of type 'int?'` crashes).
- **WebSocket support**: Server requires `uvicorn[standard]` and `websockets` (added to `pyproject.toml`) for WebSocket upgrade support.
- **No bottom navigation**: The app intentionally has no bottom nav bar; Settings lives in the top-right app-bar action.