import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from ftth_web.desktop_app import launch_desktop

if __name__ == "__main__":
    print("=" * 60)
    print("Memulai TopoFiberix - Network Designer (Desktop Edition)")
    print("Membuka antarmuka jendela desktop native via PyWebView...")
    print("=" * 60)
    launch_desktop()
