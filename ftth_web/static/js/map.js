/**
 * FTTH Network Planner - Leaflet Map Manager Module
 */

class FTTHMapManager {
  constructor(containerId, onCoordSelected) {
    this.containerId = containerId;
    this.onCoordSelected = onCoordSelected;
    this.map = null;
    this.markers = new Map();
    this.cables = new Map();
    this.tempMarker = null;

    this.initMap();
  }

  initMap() {
    // Pusat peta awal: Jakarta (-6.2088, 106.8456)
    this.map = L.map(this.containerId, {
      zoomControl: false
    }).setView([-6.2088, 106.8456], 13);

    // Kontrol Zoom di sudut kanan atas
    L.control.zoom({ position: 'topright' }).addTo(this.map);

    // Base Layer: OpenStreetMap Standard
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors | FTTH Planner'
    }).addTo(this.map);

    // Event Listener Klik pada Peta
    this.map.on('click', (e) => {
      const lat = e.latlng.lat;
      const lng = e.latlng.lng;

      this.showTempMarker(lat, lng);

      if (typeof this.onCoordSelected === 'function') {
        this.onCoordSelected(lat, lng);
      }
    });

    // Event Listener Pergerakan Kursor
    this.map.on('mousemove', (e) => {
      const el = document.getElementById('status-coords');
      if (el) {
        el.innerText = `📍 Lat: ${e.latlng.lat.toFixed(6)} | Lng: ${e.latlng.lng.toFixed(6)}`;
      }
    });
  }

  showTempMarker(lat, lng) {
    if (this.tempMarker) {
      this.tempMarker.setLatLng([lat, lng]);
    } else {
      const tempIcon = L.divIcon({
        className: 'temp-pin',
        html: `<div style="background:#0EA5E9;width:14px;height:14px;border:2px solid #FFF;border-radius:50%;box-shadow:0 0 8px rgba(14,165,233,0.8);animation:pulse 1.5s infinite;"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7]
      });
      this.tempMarker = L.marker([lat, lng], { icon: tempIcon, zIndexOffset: 1000 }).addTo(this.map);
    }
  }

  getIconForType(infraType, label) {
    let color = '#0EA5E9';
    let symbol = 'ODP';

    const t = (infraType || '').toUpperCase();
    if (t.includes('ODC')) {
      color = '#EF4444';
      symbol = 'ODC';
    } else if (t.includes('POLE') || t.includes('TIANG')) {
      color = '#F59E0B';
      symbol = 'P';
    } else if (t.includes('CLOSURE')) {
      color = '#8B5CF6';
      symbol = 'JC';
    }

    return L.divIcon({
      className: 'custom-ftth-marker',
      html: `
        <div style="
          background: ${color};
          color: white;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 10px;
          font-weight: 700;
          border: 2px solid white;
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
          white-space: nowrap;
          text-align: center;
          display: inline-block;
          transform: translate(-50%, -100%);
        ">
          ${label || symbol}
        </div>
      `,
      iconSize: [0, 0]
    });
  }

  addOrUpdateMarker(node) {
    const latLng = [node.latitude, node.longitude];
    const icon = this.getIconForType(node.infra_type, node.id);

    if (this.markers.has(node.id)) {
      const m = this.markers.get(node.id);
      m.setLatLng(latLng);
      m.setIcon(icon);
      m.bindPopup(`<b>${node.id}</b><br>${node.name}<br><i>${node.infra_type}</i>`);
    } else {
      const m = L.marker(latLng, { icon: icon }).addTo(this.map);
      m.bindPopup(`<b>${node.id}</b><br>${node.name}<br><i>${node.infra_type}</i>`);
      m.on('click', () => {
        if (window.ftthApp) {
          window.ftthApp.selectNodeRow(node.id);
        }
      });
      this.markers.set(node.id, m);
    }
  }

  removeMarker(nodeId) {
    if (this.markers.has(nodeId)) {
      this.map.removeLayer(this.markers.get(nodeId));
      this.markers.delete(nodeId);
    }
  }

  clearMarkers() {
    this.markers.forEach(m => this.map.removeLayer(m));
    this.markers.clear();
    if (this.tempMarker) {
      this.map.removeLayer(this.tempMarker);
      this.tempMarker = null;
    }
  }

  addOrUpdateCable(cable) {
    const coords = (cable.path_coordinates && cable.path_coordinates.length > 0)
      ? cable.path_coordinates
      : [[cable.source_lat, cable.source_lng], [cable.target_lat, cable.target_lng]];

    let strokeColor = '#3B82F6';
    let weight = 4;
    const t = (cable.cable_type || '').toUpperCase();
    if (t.includes('FEEDER')) {
      strokeColor = '#DC2626';
      weight = 5;
    } else if (t.includes('DROP')) {
      strokeColor = '#10B981';
      weight = 3;
    }

    if (this.cables.has(cable.id)) {
      const poly = this.cables.get(cable.id);
      poly.setLatLngs(coords);
      poly.setStyle({ color: strokeColor, weight: weight });
    } else {
      const poly = L.polyline(coords, {
        color: strokeColor,
        weight: weight,
        opacity: 0.85,
        smoothFactor: 1
      }).addTo(this.map);

      poly.bindTooltip(
        `<b>${cable.id}</b>: ${cable.source_node_id} ➔ ${cable.target_node_id} (${cable.total_length_m.toFixed(1)} m)`,
        { sticky: true }
      );

      this.cables.set(cable.id, poly);
    }
  }

  removeCable(cableId) {
    if (this.cables.has(cableId)) {
      this.map.removeLayer(this.cables.get(cableId));
      this.cables.delete(cableId);
    }
  }

  clearCables() {
    this.cables.forEach(poly => this.map.removeLayer(poly));
    this.cables.clear();
  }

  fitAllBounds() {
    const latLngs = [];
    this.markers.forEach(m => latLngs.push(m.getLatLng()));
    this.cables.forEach(poly => {
      poly.getLatLngs().forEach(pt => latLngs.push(pt));
    });

    if (latLngs.length > 0) {
      const bounds = L.latLngBounds(latLngs);
      this.map.fitBounds(bounds, { padding: [50, 50], maxZoom: 17 });
    }
  }

  flyTo(lat, lng, zoom = 16) {
    this.map.flyTo([lat, lng], zoom, { duration: 1.2 });
  }
}
