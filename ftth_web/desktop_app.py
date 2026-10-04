"""
Modul Pembungkus Desktop Mandiri (Standalone Desktop App) menggunakan PyWebView
Menjalankan server FastAPI lokal di background thread dan menampilkan antarmuka
melalui jendela desktop native (Windows WebView2 / macOS WebKit / Linux WebKitGTK).
"""

import sys
import threading
import time
import socket
import uvicorn
import webview


def find_free_port() -> int:
    """Mencari port TCP kosong di localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class DesktopAPI:
    """API Bridge Python yang dapat dipanggil langsung dari JavaScript web."""
    def __init__(self, window=None):
        self.window = window

    def set_window(self, window):
        self.window = window

    def select_file_dialog(self):
        """Membuka dialog file native OS untuk memilih file proyek."""
        if not self.window:
            return None
        file_types = ('FTTH Project Files (*.ftth;*.json)', 'All files (*.*)')
        result = self.window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        if result and len(result) > 0:
            return result[0]
        return None

    def save_file_dialog(self, default_filename="Proyek_FTTH.ftth"):
        """Membuka dialog file native OS untuk menyimpan file proyek."""
        if not self.window:
            return None
        file_types = ('FTTH Project (*.ftth)', 'JSON Files (*.json)', 'All files (*.*)')
        result = self.window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=default_filename,
            file_types=file_types
        )
        return result


def start_server(host: str, port: int):
    """Menjalankan server FastAPI via Uvicorn di thread terpisah."""
    from .backend.app import app
    uvicorn.run(app, host=host, port=port, log_level="warning")


def launch_desktop():
    """Fungsi utama untuk meluncurkan aplikasi desktop berbasis webview."""
    host = "127.0.0.1"
    port = find_free_port()

    # 1. Jalankan FastAPI server di background thread
    server_thread = threading.Thread(target=start_server, args=(host, port), daemon=True)
    server_thread.start()

    # Beri jeda 0.5 detik agar server siap
    time.sleep(0.5)

    api = DesktopAPI()
    url = f"http://{host}:{port}/"

    # 2. Buat Jendela Native Desktop
    window = webview.create_window(
        title="TopoFiberix - Network Designer",
        url=url,
        width=1320,
        height=820,
        min_size=(980, 620),
        js_api=api,
        text_select=True
    )
    api.set_window(window)

    # 3. Mulai loop GUI desktop
    webview.start(debug=False)


if __name__ == "__main__":
    launch_desktop()
