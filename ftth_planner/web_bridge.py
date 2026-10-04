"""
Modul Bridge Komunikasi Dua Arah JavaScript - PyQt6 (QWebChannel)
Menghubungkan event peta Leaflet.js dengan komponen logika Python di desktop app.
"""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class MapBridge(QObject):
    """
    Objek perantara yang diekspos ke lingkungan JavaScript di Leaflet.
    Menyediakan sinyal dan slot untuk pertukaran data secara asinkron.
    """
    # Sinyal yang dipancarkan saat pengguna mengklik peta (mengirimkan lat, lng)
    mapClicked = pyqtSignal(float, float)

    # Sinyal saat kursor bergerak di atas peta (mengirimkan lat, lng untuk status bar)
    mouseMoved = pyqtSignal(float, float)

    # Sinyal saat peta Leaflet telah selesai dimuat sepenuhnya
    mapInitialized = pyqtSignal()

    # Sinyal saat marker pada peta diklik oleh pengguna
    markerClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    @pyqtSlot(float, float)
    def on_map_clicked(self, lat: float, lng: float):
        """
        Dipanggil dari JavaScript saat event 'click' pada Leaflet peta terjadi.
        """
        self.mapClicked.emit(lat, lng)

    @pyqtSlot(float, float)
    def on_mouse_moved(self, lat: float, lng: float):
        """
        Dipanggil dari JavaScript saat kursor digerakkan di atas peta.
        """
        self.mouseMoved.emit(lat, lng)

    @pyqtSlot()
    def on_map_ready(self):
        """
        Dipanggil dari JavaScript saat Leaflet map dan QWebChannel siap digunakan.
        """
        self.mapInitialized.emit()

    @pyqtSlot(str)
    def on_marker_clicked(self, node_id: str):
        """
        Dipanggil saat suatu marker FTTH yang ada diklik di peta.
        """
        self.markerClicked.emit(node_id)
