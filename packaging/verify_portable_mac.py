"""Validate the portable Mac .app artifact and its executable permissions."""
import plistlib
import sys
import zipfile
from pathlib import Path

archive = Path(sys.argv[1])
with zipfile.ZipFile(archive) as z:
    names = z.namelist()
    prefix = "Deathwish Digitizer 2 Test.app/Contents/"
    executable = prefix + "MacOS/Deathwish Digitizer 2 Test"
    assert executable in names, "Missing Mac app launcher"
    assert prefix + "Info.plist" in names, "Missing Info.plist"
    assert prefix + "Resources/mac_app.py" in names, "Missing GUI"
    assert prefix + "Resources/digitizer/image.py" in names, "Missing vector tracing"
    assert prefix + "Resources/digitizer/export.py" in names, "Missing PES exporter"
    assert prefix + "Resources/requirements-mac.txt" in names, "Missing dependencies"
    assert z.getinfo(executable).external_attr >> 16 & 0o111, "Launcher not executable"
    plist = plistlib.loads(z.read(prefix + "Info.plist"))
    assert plist["CFBundleExecutable"] == "Deathwish Digitizer 2 Test"
    launcher = z.read(executable).decode("utf-8")
    assert "python" in launcher and "pip install" in launcher
    print(f"Portable Mac app verified: {len(names)} files, launcher executable")
