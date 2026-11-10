"""Assemble a macOS .app launcher on Linux, without PyInstaller or Mac runners.

This is a bootstrap app, NOT a fully self-contained native executable.
It uses a local Tk-capable Python and installs Python packages on first launch.
"""
from pathlib import Path
import os
import plistlib
import shutil
import stat
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "Deathwish Digitizer 2 Test"
APP = Path(tempfile.mkdtemp(prefix="deathwish-mac-")) / (APP_NAME + ".app")
CONTENTS = APP / "Contents"
MACOS = CONTENTS / "MacOS"
RESOURCES = CONTENTS / "Resources"
MACOS.mkdir(parents=True)
RESOURCES.mkdir(parents=True)

plist = {
    "CFBundleName": APP_NAME,
    "CFBundleDisplayName": APP_NAME,
    "CFBundleIdentifier": "com.deathwishpaintball.digitizer2.test",
    "CFBundleExecutable": APP_NAME,
    "CFBundlePackageType": "APPL",
    "CFBundleVersion": "0.2.0",
    "CFBundleShortVersionString": "0.2.0",
    "LSMinimumSystemVersion": "12.0",
    "NSHighResolutionCapable": True,
}
with (CONTENTS / "Info.plist").open("wb") as stream:
    plistlib.dump(plist, stream)

launcher = r'''#!/bin/bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RESOURCES="$APP_DIR/Contents/Resources"
DATA_DIR="$HOME/Library/Application Support/Deathwish Digitizer 2 Test"
LOG_FILE="$DATA_DIR/launch.log"
mkdir -p "$DATA_DIR"

alert() {
  /usr/bin/osascript -e 'display dialog "'"$1"'" buttons {"OK"} default button "OK" with title "Deathwish Digitizer 2"' >/dev/null 2>&1 || true
}
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    candidate_path="$(command -v "$candidate")"
    if "$candidate_path" -c 'import sys, tkinter; assert sys.version_info >= (3, 10)' >/dev/null 2>&1; then
      PYTHON="$candidate_path"
      break
    fi
  fi
done
if [ -z "$PYTHON" ]; then
  alert "This test app needs Python 3.10 or newer with Tkinter. Install Python 3.11 or 3.12 from python.org (which includes Tkinter), then reopen the app."
  exit 1
fi
VENV="$DATA_DIR/venv"
READY="$VENV/.deathwish-ready"
if [ ! -f "$READY" ] || [ "$(cat "$READY" 2>/dev/null)" != "$PYTHON|geometry-v2" ]; then
  alert "First launch will install the embroidery libraries into your user account. This needs internet and may take a minute. Click OK to continue."
  if ! "$PYTHON" -m venv "$VENV" >>"$LOG_FILE" 2>&1; then
    alert "Could not create Python environment. Details: $LOG_FILE"
    exit 1
  fi
  if ! "$VENV/bin/python" -m pip install --disable-pip-version-check -r "$RESOURCES/requirements-mac.txt" >>"$LOG_FILE" 2>&1; then
    alert "Could not install libraries. Check your internet connection. Details: $LOG_FILE"
    exit 1
  fi
  printf '%s' "$PYTHON|geometry-v2" > "$READY"
fi
cd "$RESOURCES"
if ! "$VENV/bin/python" "$RESOURCES/mac_app.py" >>"$LOG_FILE" 2>&1; then
  alert "Digitizer stopped unexpectedly. Details: $LOG_FILE"
  exit 1
fi
'''
executable = MACOS / APP_NAME
executable.write_text(launcher, encoding="utf-8")
executable.chmod(0o755)

for filename in ("mac_app.py", "requirements-mac.txt"):
    shutil.copy2(ROOT / filename, RESOURCES / filename)
shutil.copytree(ROOT / "digitizer", RESOURCES / "digitizer",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

output = ROOT / "Deathwish-Digitizer-2-Mac-Test.zip"
with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=8) as archive:
    for path in sorted(APP.rglob("*")):
        if not path.is_file():
            continue
        entry = zipfile.ZipInfo(str(path.relative_to(APP.parent)))
        entry.create_system = 3
        entry.external_attr = (stat.S_IFREG | (0o755 if path == executable else 0o644)) << 16
        entry.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(entry, path.read_bytes())
print(f"Created {output} ({output.stat().st_size} bytes)")
