# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

base_dir = Path('.').resolve()
src_dir = base_dir / 'catword'
datas = []
for name in ('preference.ini', 'themes.ini', 'fonts.ini'):
    p = src_dir / name
    if p.exists():
        datas.append((str(p), '.'))

icon_file = None
for candidate in (
    src_dir / 'assets' / 'app_icon' / 'app.png',
    src_dir / 'assets' / 'app_icon' / 'app.ico',
):
    if candidate.exists():
        datas.append((str(candidate), str(Path('assets') / 'app_icon')))
        if icon_file is None:
            icon_file = candidate

a = Analysis(
    [str(src_dir / 'W2R.py')],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'qtpy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='W2R_Cattoon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(icon_file) if icon_file is not None else None,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='W2R_Cattoon',
)
