# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec Configuration for Topofiberix
Mengompilasi aplikasi Topofiberix menjadi file .exe mandiri (standalone Windows binary)
dengan icon kustom FTTH Network, modul PyQt6, dan seluruh aset pendukung.
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Aset dan file data pendukung
added_files = [
    ('ftth_planner/assets/*', 'ftth_planner/assets'),
    ('topofiberix.ico', '.'),
    ('topofiberix.png', '.'),
]

# Hidden imports yang mungkin diperlukan PyQt6 dan library pendukung
hidden_imports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtNetwork',
    'openpyxl',
    'pandas',
    'xml.etree.ElementTree',
    'zipfile',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Topofiberix',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI mode tanpa jendela command prompt hitam di background
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='topofiberix.ico',  # Icon aplikasi untuk file .exe dan taskbar
)
