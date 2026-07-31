"""Add pairing section to all locale common.json files.
Uses {{variable}} format for i18next interpolation.
"""
import json
import os

pairing_tr = {
    "title": "Cihaz Eşleştirme",
    "qrTitle": "QR Kod ile Bağlan",
    "qrDescription": "Android uygulamasından QR kodu okutarak cihazını eşleştir.",
    "qrLoading": "Yükleniyor...",
    "qrError": "QR kod yüklenemedi",
    "serverLabel": "Sunucu: ",
    "refreshQr": "Kodu Yenile",
    "manualTitle": "Manuel Eşleştirme Kodu",
    "manualDescription": "QR kodu okutamıyorsan bu kodu Android uygulamasına elle girebilirsin:",
    "copyButton": "Kopyala",
    "copiedButton": "Kopyalandı!",
    "codeExpiry": "Yeni kod almak için kodu yenile butonuna tıklayın.",
    "devicesTitle": "Bağlı Cihazlar",
    "devicesLoading": "Yükleniyor...",
    "devicesLoadError": "Cihaz listesi yüklenemedi",
    "devicesEmpty": "Henüz eşleştirilmiş cihaz yok.",
    "deviceNameHeader": "Cihaz Adı",
    "devicePairingDate": "Pair Tarihi",
    "deviceStatusHeader": "Durum",
    "deviceLastSyncHeader": "Son Senkronizasyon",
    "deviceActionsHeader": "İşlem",
    "statusConnected": "Bağlı",
    "statusDisconnected": "Bağlı Değil",
    "unknownDevice": "Bilinmeyen Cihaz",
    "revokeButton": "Bağlantıyı Kes",
    "revokeConfirm": "\"{{name}}\" cihazının bağlantısını kesmek istediğine emin misin?",
    "revokeFailed": "Bağlantı kesilemedi: {{message}}",
    "revokeError": "Bağlantı kesilirken hata oluştu.",
    "unknownError": "Bilinmeyen hata",
    "copiedPrefix": "✅ ",
    "copyPrefix": "📋 ",
}

pairing_en = {
    "title": "Device Pairing",
    "qrTitle": "Connect via QR Code",
    "qrDescription": "Pair your device by scanning the QR code from the Android app.",
    "qrLoading": "Loading...",
    "qrError": "Failed to load QR code",
    "serverLabel": "Server: ",
    "refreshQr": "Refresh Code",
    "manualTitle": "Manual Pairing Code",
    "manualDescription": "If you can\u2019t scan the QR code, enter this code manually in the Android app:",
    "copyButton": "Copy",
    "copiedButton": "Copied!",
    "codeExpiry": "Click the refresh code button to get a new code.",
    "devicesTitle": "Paired Devices",
    "devicesLoading": "Loading...",
    "devicesLoadError": "Failed to load device list",
    "devicesEmpty": "No paired devices yet.",
    "deviceNameHeader": "Device Name",
    "devicePairingDate": "Pair Date",
    "deviceStatusHeader": "Status",
    "deviceLastSyncHeader": "Last Sync",
    "deviceActionsHeader": "Actions",
    "statusConnected": "Connected",
    "statusDisconnected": "Disconnected",
    "unknownDevice": "Unknown Device",
    "revokeButton": "Disconnect",
    "revokeConfirm": "Are you sure you want to disconnect \"{{name}}\"?",
    "revokeFailed": "Disconnect failed: {{message}}",
    "revokeError": "An error occurred while disconnecting.",
    "unknownError": "Unknown error",
    "copiedPrefix": "✅ ",
    "copyPrefix": "📋 ",
}

# Use absolute path based on script location
locales_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "static", "locales")
locales_dir = os.path.normpath(locales_dir)
count = 0
for lang_dir in sorted(os.listdir(locales_dir)):
    filepath = os.path.join(locales_dir, lang_dir, "common.json")
    if not os.path.isfile(filepath):
        continue
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["pairing"] = pairing_tr if lang_dir == "tr" else pairing_en
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    count += 1

print(f"Updated {count} locale files with pairing section (i18next {{}} interpolation)")