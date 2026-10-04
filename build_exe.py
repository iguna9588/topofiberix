#!/usr/bin/env python3
"""
Skrip Otomatisasi Build Executable Windows (.exe) untuk Topofiberix
Menginstal PyInstaller jika belum tersedia dan mengompilasi proyek
menjadi Topofiberix.exe mandiri dengan icon FTTH Network.
"""

import os
import sys
import subprocess

def run_command(cmd, desc):
    print(f"\n🚀 {desc}...")
    print(f"Menjalankan: {cmd}")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        print(f"❌ Gagal saat: {desc}")
        sys.exit(res.returncode)
    print(f"✅ Selesai: {desc}")

def main():
    print("=" * 65)
    print("      TOPOFIBERIX - NETWORK DESIGNER (.EXE) BUILDER")
    print("=" * 65)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    icon_path = os.path.join(base_dir, "topofiberix.ico")
    if not os.path.exists(icon_path):
        print(f"❌ File icon tidak ditemukan: {icon_path}")
        sys.exit(1)

    print(f"🎨 Icon aplikasi terdeteksi: {icon_path}")

    # 1. Pastikan PyInstaller terpasang
    try:
        import PyInstaller
        print("📦 PyInstaller sudah terpasang.")
    except ImportError:
        print("📦 Menginstal PyInstaller ke lingkungan virtual...")
        run_command(f'"{sys.executable}" -m pip install pyinstaller', "Instalasi PyInstaller")

    # 2. Jalankan Build menggunakan topofiberix.spec
    spec_file = os.path.join(base_dir, "topofiberix.spec")
    if os.path.exists(spec_file):
        cmd = f'"{sys.executable}" -m PyInstaller --clean --noconfirm "{spec_file}"'
    else:
        cmd = (
            f'"{sys.executable}" -m PyInstaller --clean --noconfirm '
            f'--name Topofiberix --windowed --icon="{icon_path}" '
            f'--add-data "ftth_planner/assets/*;ftth_planner/assets" main.py'
        )

    run_command(cmd, "Kompilasi Topofiberix.exe dengan PyInstaller")

    exe_path = os.path.join(base_dir, "dist", "Topofiberix", "Topofiberix.exe")
    single_exe_path = os.path.join(base_dir, "dist", "Topofiberix.exe")

    target = single_exe_path if os.path.exists(single_exe_path) else exe_path
    print("\n" + "=" * 65)
    print("🎉 BUILD BERHASIL!")
    print(f"Lokasi Executable: {target}")
    print("Icon FTTH Network telah tertanam pada file .exe dan taskbar.")
    print("=" * 65)

if __name__ == "__main__":
    main()
