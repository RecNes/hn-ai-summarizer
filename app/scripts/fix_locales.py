"""Fix locale files that are encoded as ISO-8859-1 instead of UTF-8.

Run: python -m app.scripts.fix_locales
"""
import os
import glob

BROKEN_LANGS = ["de", "es", "fr", "ja", "pt"]

for lang in BROKEN_LANGS:
    path = os.path.join("app", "static", "locales", lang, "common.json")
    if not os.path.exists(path):
        print(f"SKIP: {lang} - file not found")
        continue

    with open(path, "rb") as f:
        raw = f.read()

    # Decode as ISO-8859-1, re-encode as UTF-8
    try:
        text = raw.decode("iso-8859-1")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"OK:   {lang} - ISO-8859-1 -> UTF-8  ({len(raw)} bytes -> {len(text.encode('utf-8'))} bytes)")
    except Exception as e:
        print(f"ERR:  {lang} - {e}")