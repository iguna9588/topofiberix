"""
Modul Widget Peta Leaflet.js Berbasis PyQt6 WebEngine (Modul 1 & Modul 2)
Menyediakan integrasi peta interaktif GIS, visualisasi marker infrastruktur FTTH,
visualisasi rute bentangan kabel (Polyline), dan jembatan komunikasi dua arah
JavaScript -> Python yang 100% andal dan cepat (Direct Console Bridge + QWebChannel).
"""

import json
from typing import Optional
from PyQt6.QtCore import QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView

from .models import CableSegment, FTTHNode
from .web_bridge import MapBridge


# Template HTML + CSS + JS Mandiri untuk Leaflet
LEAFLET_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>FTTH GIS Interactive Map</title>
  
  <!-- Leaflet CSS & JS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

  <style>
    html, body, #map {
      height: 100%;
      width: 100%;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: #1a1e24;
    }

    /* Custom Leaflet Controls */
    .leaflet-control-layers {
      border-radius: 8px !important;
      box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
      border: 1px solid #e2e8f0 !important;
      background: rgba(255, 255, 255, 0.95) !important;
      color: #1e293b !important;
      backdrop-filter: blur(8px);
    }
    .leaflet-control-layers-base label {
      cursor: pointer;
      padding: 4px 0;
      font-size: 12px;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    /* Custom Pulsing Click Pointer */
    .temp-click-pin {
      background-color: #0284c7;
      border: 3px solid #ffffff;
      border-radius: 50%;
      width: 18px;
      height: 18px;
      box-shadow: 0 0 12px rgba(2, 132, 199, 0.8);
      animation: pulse-glow 1.4s infinite;
    }
    @keyframes pulse-glow {
      0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(2, 132, 199, 0.8); }
      70% { transform: scale(1.1); box-shadow: 0 0 0 14px rgba(2, 132, 199, 0); }
      100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(2, 132, 199, 0); }
    }

    .temp-pin-tooltip {
      background: rgba(15, 23, 42, 0.92) !important;
      border: 1px solid #0284c7 !important;
      color: #38bdf8 !important;
      font-weight: bold !important;
      font-size: 11px !important;
      border-radius: 6px !important;
      padding: 4px 8px !important;
      box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
    }

    /* Custom FTTH Node Badge Marker */
    .ftth-marker-badge {
      display: flex;
      align-items: center;
      justify-content: center;
      color: #ffffff;
      font-weight: 700;
      font-size: 11px;
      border-radius: 6px;
      border: 2px solid #ffffff;
      box-shadow: 0 3px 8px rgba(0, 0, 0, 0.25);
      cursor: pointer;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      white-space: nowrap;
      padding: 0 6px;
      height: 24px;
      min-width: 32px;
    }
    .ftth-marker-badge:hover {
      transform: translateY(-3px) scale(1.08);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.35);
    }
    .ftth-marker-badge.selected-node {
      border: 2px solid #f59e0b !important;
      box-shadow: 0 0 16px #f59e0b !important;
      animation: bounce 0.6s infinite alternate;
    }
    @keyframes bounce {
      from { transform: translateY(0); }
      to { transform: translateY(-6px); }
    }

    /* Tooltip Jalur Kabel */
    .cable-tooltip {
      background: rgba(15, 23, 42, 0.92) !important;
      border: 1px solid #0284c7 !important;
      color: #38bdf8 !important;
      font-weight: bold !important;
      font-size: 11px !important;
      border-radius: 6px !important;
      padding: 3px 8px !important;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25) !important;
    }

    /* Custom Leaflet Popup */
    .leaflet-popup-content-wrapper {
      background: #ffffff;
      color: #1e293b;
      border-radius: 10px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
      border: 1px solid #e2e8f0;
    }
    .leaflet-popup-tip {
      background: #ffffff;
    }
    .popup-title {
      font-size: 13px;
      font-weight: 700;
      color: #0284c7;
      margin-bottom: 6px;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 4px;
    }
    .popup-row {
      font-size: 12px;
      margin: 3px 0;
      display: flex;
      justify-content: space-between;
      gap: 12px;
    }
    .popup-label {
      color: #64748b;
    }
    .popup-value {
      font-weight: 600;
      color: #0f172a;
    }
  </style>
</head>
<body>
  <div id="map"></div>

  <script>
    var map;
    var bridge = null;
    var tempMarker = null;
    var nodeMarkers = {};    // node_id -> L.marker
    var cablePolylines = {}; // cable_id -> L.polyline

    // Fungsi komunikasi handal JS -> Python
    function sendToPython(action, data) {
      // 1. Console Bridge (100% bekerja di semua versi PyQt6 tanpa dependensi luar)
      if (action === 'MAP_CLICK') {
        console.log("FTTH_BRIDGE:MAP_CLICK:" + data.lat + ":" + data.lng);
      } else if (action === 'MOUSE_MOVE') {
        console.log("FTTH_BRIDGE:MOUSE_MOVE:" + data.lat + ":" + data.lng);
      } else if (action === 'MARKER_CLICK') {
        console.log("FTTH_BRIDGE:MARKER_CLICK:" + data.id);
      } else if (action === 'MAP_READY') {
        console.log("FTTH_BRIDGE:MAP_READY:1");
      }

      // 2. QWebChannel jika aktif
      if (window.bridge) {
        try {
          if (action === 'MAP_CLICK' && bridge.on_map_clicked) bridge.on_map_clicked(data.lat, data.lng);
          else if (action === 'MOUSE_MOVE' && bridge.on_mouse_moved) bridge.on_mouse_moved(data.lat, data.lng);
          else if (action === 'MARKER_CLICK' && bridge.on_marker_clicked) bridge.on_marker_clicked(data.id);
          else if (action === 'MAP_READY' && bridge.on_map_ready) bridge.on_map_ready();
        } catch(err) {
          console.error("Bridge call error:", err);
        }
      }
    }

    // Inisialisasi Peta Leaflet
    function initMap() {
      var osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
      });

      var satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye'
      });

      var darkLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        attribution: '&copy; CARTO'
      });

      map = L.map('map', {
        center: [-6.2088, 106.8456],
        zoom: 14,
        layers: [osmLayer],
        zoomControl: true
      });

      var baseMaps = {
        "🗺️ Peta Jalan (OSM)": osmLayer,
        "🛰️ Satelit (Esri World)": satelliteLayer,
        "🌙 Peta Gelap (CartoDB)": darkLayer
      };

      L.control.layers(baseMaps, null, { position: 'topright' }).addTo(map);

      // Event Klik Peta
      map.on('click', function(e) {
        var lat = e.latlng.lat;
        var lng = e.latlng.lng;
        setTemporaryPin(lat, lng);
        sendToPython('MAP_CLICK', { lat: lat, lng: lng });
      });

      // Event Mouse Move
      var lastMoveTime = 0;
      map.on('mousemove', function(e) {
        var now = Date.now();
        if (now - lastMoveTime > 80) {
          lastMoveTime = now;
          sendToPython('MOUSE_MOVE', { lat: e.latlng.lat, lng: e.latlng.lng });
        }
      });

      sendToPython('MAP_READY', {});
    }

    // Menampilkan penanda sementara yang dipilih
    function setTemporaryPin(lat, lng) {
      if (tempMarker) {
        map.removeLayer(tempMarker);
      }
      var pulseIcon = L.divIcon({
        className: 'temp-click-pin-wrapper',
        html: '<div class="temp-click-pin"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 9]
      });
      tempMarker = L.marker([lat, lng], { icon: pulseIcon }).addTo(map);
      tempMarker.bindTooltip("📍 " + lat.toFixed(6) + ", " + lng.toFixed(6), {
        permanent: true,
        direction: "top",
        offset: [0, -10],
        className: "temp-pin-tooltip"
      }).openTooltip();
    }

    function removeTemporaryPin() {
      if (tempMarker) {
        map.removeLayer(tempMarker);
        tempMarker = null;
      }
    }

    function flyToLocation(lat, lng, zoomLevel) {
      var zoom = zoomLevel || 17;
      map.flyTo([lat, lng], zoom, {
        animate: true,
        duration: 1.2
      });
      setTemporaryPin(lat, lng);
    }

    // --- MANAJEMEN SIMPUL (NODES) ---

    function addOrUpdateNode(node) {
      if (nodeMarkers[node.id]) {
        map.removeLayer(nodeMarkers[node.id]);
      }

      var badgeHtml = '<div class="ftth-marker-badge" style="background-color: ' + node.color + ';">' + 
                      node.infra_code + ' ' + node.name + '</div>';

      var customIcon = L.divIcon({
        className: 'custom-ftth-icon',
        html: badgeHtml,
        iconSize: [80, 24],
        iconAnchor: [40, 12],
        popupAnchor: [0, -14]
      });

      var marker = L.marker([node.latitude, node.longitude], { icon: customIcon }).addTo(map);

      var popupContent = '<div class="popup-title">' + node.name + ' [' + node.id + ']</div>' +
        '<div class="popup-row"><span class="popup-label">Tipe:</span><span class="popup-value">' + node.infra_type + '</span></div>' +
        '<div class="popup-row"><span class="popup-label">Kapasitas:</span><span class="popup-value">' + node.capacity + '</span></div>' +
        '<div class="popup-row"><span class="popup-label">Koordinat:</span><span class="popup-value">' + node.latitude.toFixed(6) + ', ' + node.longitude.toFixed(6) + '</span></div>' +
        '<div class="popup-row"><span class="popup-label">Catatan:</span><span class="popup-value">' + (node.notes || '-') + '</span></div>';

      marker.bindPopup(popupContent);

      marker.on('click', function() {
        sendToPython('MARKER_CLICK', { id: node.id });
      });

      nodeMarkers[node.id] = marker;
      removeTemporaryPin();
    }

    function removeNode(nodeId) {
      if (nodeMarkers[nodeId]) {
        map.removeLayer(nodeMarkers[nodeId]);
        delete nodeMarkers[nodeId];
      }
    }

    function clearAllNodes() {
      for (var id in nodeMarkers) {
        map.removeLayer(nodeMarkers[id]);
      }
      nodeMarkers = {};
      removeTemporaryPin();
    }

    function highlightNode(nodeId) {
      for (var id in nodeMarkers) {
        var el = nodeMarkers[id].getElement();
        if (el) {
          var badge = el.querySelector('.ftth-marker-badge');
          if (badge) {
            if (id === nodeId) {
              badge.classList.add('selected-node');
              nodeMarkers[id].openPopup();
              map.panTo(nodeMarkers[id].getLatLng());
            } else {
              badge.classList.remove('selected-node');
            }
          }
        }
      }
    }

    // --- MANAJEMEN RUTE KABEL (POLYLINE ROUTING) ---

    function addOrUpdateCable(cable) {
      if (cablePolylines[cable.id]) {
        map.removeLayer(cablePolylines[cable.id]);
      }

      var latlngs = [];
      if (cable.path_coordinates && cable.path_coordinates.length > 1) {
        latlngs = cable.path_coordinates;
      } else {
        latlngs = [
          [cable.source_lat, cable.source_lng],
          [cable.target_lat, cable.target_lng]
        ];
      }

      var polyline = L.polyline(latlngs, {
        color: cable.color,
        weight: 4,
        opacity: 0.9,
        lineCap: 'round',
        lineJoin: 'round'
      }).addTo(map);

      polyline.bindTooltip(cable.name + ' (' + cable.total_length_m.toFixed(1) + ' m)', {
        permanent: false,
        direction: 'center',
        className: 'cable-tooltip'
      });

      var popupHtml = '<div class="popup-title">🔗 ' + cable.name + ' [' + cable.id + ']</div>' +
        '<div class="popup-row"><span class="popup-label">Tipe:</span><span class="popup-value">' + cable.cable_type + '</span></div>' +
        '<div class="popup-row"><span class="popup-label">Kapasitas:</span><span class="popup-value">' + cable.core_count + '</span></div>' +
        '<div class="popup-row"><span class="popup-label">Asal:</span><span class="popup-value">' + cable.source_node_name + '</span></div>' +
        '<div class="popup-row"><span class="popup-label">Tujuan:</span><span class="popup-value">' + cable.target_node_name + '</span></div>' +
        '<div class="popup-row"><span class="popup-label">Jarak Span:</span><span class="popup-value">' + cable.span_distance_m.toFixed(2) + ' m</span></div>' +
        '<div class="popup-row"><span class="popup-label">Slack (' + cable.slack_percent.toFixed(0) + '%):</span><span class="popup-value">' + (cable.span_distance_m * cable.slack_percent / 100).toFixed(2) + ' m</span></div>' +
        '<div class="popup-row" style="border-top:1px solid rgba(255,255,255,0.2); padding-top:4px; margin-top:4px;"><span class="popup-label" style="color:#00adb5; font-weight:bold;">Panjang Riil:</span><span class="popup-value" style="color:#38ef7d; font-size:13px;">' + cable.total_length_m.toFixed(2) + ' m</span></div>';

      polyline.bindPopup(popupHtml);

      polyline._defaultColor = cable.color;
      polyline._defaultWeight = 4;

      cablePolylines[cable.id] = polyline;
    }

    function removeCable(cableId) {
      if (cablePolylines[cableId]) {
        map.removeLayer(cablePolylines[cableId]);
        delete cablePolylines[cableId];
      }
    }

    function clearAllCables() {
      for (var id in cablePolylines) {
        map.removeLayer(cablePolylines[id]);
      }
      cablePolylines = {};
    }

    function highlightCable(cableId) {
      for (var id in cablePolylines) {
        var poly = cablePolylines[id];
        if (id === cableId) {
          poly.setStyle({ color: '#ffeb3b', weight: 7, opacity: 1.0 });
          poly.openPopup();
          map.fitBounds(poly.getBounds(), { padding: [40, 40] });
        } else {
          poly.setStyle({ color: poly._defaultColor || '#3498db', weight: poly._defaultWeight || 4, opacity: 0.75 });
        }
      }
    }

    function fitAllBounds() {
      var points = [];
      for (var id in nodeMarkers) {
        points.push(nodeMarkers[id].getLatLng());
      }
      for (var cid in cablePolylines) {
        var latlngs = cablePolylines[cid].getLatLngs();
        for (var i = 0; i < latlngs.length; i++) {
          points.push(latlngs[i]);
        }
      }
      if (points.length > 0) {
        var bounds = L.latLngBounds(points);
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 17 });
      }
    }

    window.onload = function() {
      initMap();
    };
  </script>
</body>
</html>
"""


class MapWebEnginePage(QWebEnginePage):
    """
    Subclass QWebEnginePage kustom yang mengintersepsi pesan jembatan JavaScript
    secara instan dan sinkron di thread utama PyQt6.
    """
    def __init__(self, bridge: MapBridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge

    def javaScriptConsoleMessage(self, level, message: str, line_number: int, source_id: str):
        """Menangkap pesan konsol berpola 'FTTH_BRIDGE:...' dan memicu sinyal PyQt6."""
        if message.startswith("FTTH_BRIDGE:"):
            try:
                parts = message.split(":")
                action = parts[1]
                if action == "MAP_CLICK":
                    lat = float(parts[2])
                    lng = float(parts[3])
                    self.bridge.mapClicked.emit(lat, lng)
                elif action == "MOUSE_MOVE":
                    lat = float(parts[2])
                    lng = float(parts[3])
                    self.bridge.mouseMoved.emit(lat, lng)
                elif action == "MARKER_CLICK":
                    node_id = parts[2]
                    self.bridge.markerClicked.emit(node_id)
                elif action == "MAP_READY":
                    self.bridge.mapInitialized.emit()
            except Exception as e:
                print(f"[MapWebEnginePage] Error parsing bridge message: {e}")
            return

        super().javaScriptConsoleMessage(level, message, line_number, source_id)


class LeafletMapWidget(QWebEngineView):
    """
    Komponen View PyQt6 yang membungkus antarmuka peta Leaflet.js
    dan mengelola instruksi JavaScript ke DOM (Marker Simpul & Polyline Kabel).
    """
    def __init__(self, bridge: MapBridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.is_ready = False

        # Pasang Custom WebEngine Page dengan Console Bridge yang 100% andal
        self.custom_page = MapWebEnginePage(self.bridge, self)
        self.setPage(self.custom_page)

        # Pasang QWebChannel sebagai jalur sekunder/paralel
        self.web_channel = QWebChannel(self.page())
        self.web_channel.registerObject("mapBridge", self.bridge)
        self.page().setWebChannel(self.web_channel)

        self.bridge.mapInitialized.connect(self._on_map_initialized)
        self.setHtml(LEAFLET_HTML_TEMPLATE, QUrl("https://unpkg.com/"))

    def _on_map_initialized(self):
        self.is_ready = True

    def fly_to(self, lat: float, lng: float, zoom: int = 17):
        script = f"flyToLocation({lat}, {lng}, {zoom});"
        self.page().runJavaScript(script)

    # Simpul (Nodes)
    def add_or_update_marker(self, node: FTTHNode):
        node_json = json.dumps(node.to_dict())
        script = f"addOrUpdateNode({node_json});"
        self.page().runJavaScript(script)

    def remove_marker(self, node_id: str):
        script = f"removeNode('{node_id}');"
        self.page().runJavaScript(script)

    def clear_markers(self):
        self.page().runJavaScript("clearAllNodes();")

    def highlight_marker(self, node_id: str):
        script = f"highlightNode('{node_id}');"
        self.page().runJavaScript(script)

    # Rute Kabel (Cables - Modul 2)
    def add_or_update_cable(self, cable: CableSegment):
        cable_json = json.dumps(cable.to_dict())
        script = f"addOrUpdateCable({cable_json});"
        self.page().runJavaScript(script)

    def remove_cable(self, cable_id: str):
        script = f"removeCable('{cable_id}');"
        self.page().runJavaScript(script)

    def clear_cables(self):
        self.page().runJavaScript("clearAllCables();")

    def highlight_cable(self, cable_id: str):
        script = f"highlightCable('{cable_id}');"
        self.page().runJavaScript(script)

    def fit_all_bounds(self):
        """Menyesuaikan zoom dan posisi peta agar mencakup seluruh simpul dan kabel."""
        self.page().runJavaScript("fitAllBounds();")
