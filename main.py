#!/usr/bin/env python3
"""
Topofiberix - FTTH Network Planner
Aplikasi desktop modern untuk perencanaan, pemetaan topologi, dan survey spasial jaringan fiber optik.
"""

import os
import sys
import ctypes
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from ftth_planner.main_window import FTTHMainWindow
from ftth_planner.styles import apply_theme


def main():
    # Pastikan taskbar Windows menampilkan icon aplikasi kustom (bukan icon default python)
    try:
        myappid = "topofiberix.network.designer.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    # Optimasi rendering grafis dan font resolusi tinggi (High-DPI)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("TopoFiberix - Network Designer")
    # Biarkan kosong agar Qt di Windows tidak menambahkan suffix displayName yang berulang pada title bar
    app.setApplicationDisplayName("")
    app.setOrganizationName("TopoFiberix")

    # Muat Icon Aplikasi FTTH Network
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "ftth_planner", "assets")
    ico_path = os.path.join(assets_dir, "topofiberix.ico")
    png_path = os.path.join(assets_dir, "topofiberix.png")

    app_icon = None
    if os.path.exists(ico_path):
        app_icon = QIcon(ico_path)
    elif os.path.exists(png_path):
        app_icon = QIcon(png_path)

    if app_icon:
        app.setWindowIcon(app_icon)

    # Terapkan gaya modern light theme secara global pada aplikasi
    apply_theme(app, "light")

    # Inisialisasi dan tampilkan jendela utama
    window = FTTHMainWindow()
    if app_icon:
        window.setWindowIcon(app_icon)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

