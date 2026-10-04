"""
Modul Pencarian Spasial / Geocoding Asinkron
Menggunakan library 'geopy' dengan fallback HTTP request yang dijalankan
dalam QThread agar antarmuka desktop tetap responsif tanpa lag.
"""

from PyQt6.QtCore import QThread, pyqtSignal


class GeocodingWorker(QThread):
    """
    Worker thread untuk mencari koordinat geografis berdasarkan nama tempat/alamat.
    """
    searchCompleted = pyqtSignal(float, float, str)  # lat, lng, formatted_address
    searchFailed = pyqtSignal(str)                   # error message

    def __init__(self, query: str, parent=None):
        super().__init__(parent)
        self.query = query.strip()

    def run(self):
        if not self.query:
            self.searchFailed.emit("Masukkan nama wilayah atau alamat yang valid.")
            return

        try:
            # Gunakan geopy jika tersedia
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent="ftth_network_planner_v1")
            location = geolocator.geocode(self.query, timeout=10)

            if location:
                self.searchCompleted.emit(
                    float(location.latitude),
                    float(location.longitude),
                    location.address
                )
            else:
                self.searchFailed.emit(f"Lokasi '{self.query}' tidak ditemukan.")

        except ImportError:
            # Fallback jika geopy belum terpasang: Gunakan urllib standar Python
            self._fallback_http_search()
        except Exception as e:
            # Coba fallback jika geopy mengalami kendala koneksi atau rate limit
            try:
                self._fallback_http_search()
            except Exception:
                self.searchFailed.emit(f"Gagal melakukan pencarian: {str(e)}")

    def _fallback_http_search(self):
        """Fallback pencarian menggunakan urllib bawaan Python ke Nominatim OSM."""
        import json
        import urllib.parse
        import urllib.request

        encoded_query = urllib.parse.quote(self.query)
        url = f"https://nominatim.openstreetmap.org/search?q={encoded_query}&format=json&limit=1"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "FTTHPlannerDesktop/1.0 (GIS Survey Tool)"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data and len(data) > 0:
                result = data[0]
                lat = float(result["lat"])
                lon = float(result["lon"])
                address = result.get("display_name", self.query)
                self.searchCompleted.emit(lat, lon, address)
            else:
                self.searchFailed.emit(f"Wilayah '{self.query}' tidak ditemukan.")
