# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []

# PACKAGING FIX (project-verification pass): the original spec only
# collected customtkinter's assets. insightface, onnxruntime, ultralytics,
# and cv2 all ship non-Python files (model config JSON/YAML, native shared
# libraries, ONNX Runtime DLLs) that PyInstaller's default import scanner
# does not discover on its own — omitting them here does not fail at build
# time, only later at runtime on a clean machine with a confusing
# ModuleNotFoundError/DLL-load error. This is a build-configuration change
# only; nothing about how the app behaves is touched.
for pkg in ("customtkinter", "insightface", "onnxruntime", "ultralytics", "cv2"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

datas.append(("yolov8n.pt", "."))

# Bundle the app icon file so python code can load it at runtime
import os
if os.path.exists("app_icon.ico"):
    datas.append(("app_icon.ico", "."))

# NOTE: InsightFace's buffalo_l model weights are downloaded to the user's
# home directory (~/.insightface/models) on first run, not bundled into the
# .exe. The teacher's machine therefore needs an internet connection the
# very first time KinderSort runs so InsightFace can fetch them; after that
# first run it is fully offline as documented in the guidebook. If fully
# offline-from-first-run is required, pre-download the buffalo_l model
# folder and add it here via `datas.append(("path/to/buffalo_l", "models/buffalo_l"))`.


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='KinderSort',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico' if os.path.exists('app_icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='KinderSort',
)

