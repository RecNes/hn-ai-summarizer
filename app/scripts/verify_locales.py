"""Verify all locale files are valid UTF-8 JSON."""
import json
import os
import glob

all_ok = True
for path in sorted(glob.glob("app/static/locales/*/common.json")):
    lang = os.path.basename(os.path.dirname(path))
    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
        print(f"OK:   {lang}")
    except Exception as e:
        print(f"FAIL: {lang} - {e}")
        all_ok = False

print()
print("ALL OK" if all_ok else "SOME FAILED")