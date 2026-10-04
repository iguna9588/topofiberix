/**
 * FTTH Network Planner - Web Client Application Logic
 */

class FTTHWebApp {
  constructor() {
    this.nodes = new Map();
    this.cables = new Map();
    this.counter = 1;
    this.poleCounter = 1;
    this.cableCounter = 1;
    this.projectName = "Proyek_FTTH_Baru";

    this.mapManager = new FTTHMapManager('map', (lat, lng) => {
      this.onMapCoordSelected(lat, lng);
    });

    this.initEventListeners();
    this.autoGenerateId();
  }

  initEventListeners() {
    // 1. Tab Switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        btn.classList.add('active');
        const targetId = btn.getAttribute('data-tab');
        document.getElementById(targetId).classList.add('active');

        if (targetId === 'tab-review') {
          this.runAuditQC();
        }
      });
    });

    // 2. Simpan Titik Simpul
    document.getElementById('btn-save-node').addEventListener('click', () => this.handleSaveNode());
    document.getElementById('btn-reset-form').addEventListener('click', () => this.resetNodeForm());
    document.getElementById('btn-delete-node').addEventListener('click', () => this.handleDeleteSelectedNode());

    // 3. Routing Form
    document.getElementById('combo-src-node').addEventListener('change', () => this.recalculateRoutePreview());
    document.getElementById('combo-dst-node').addEventListener('change', () => this.recalculateRoutePreview());
    document.getElementById('combo-routing-mode').addEventListener('change', () => this.recalculateRoutePreview());
    document.getElementById('input-slack').addEventListener('input', () => this.updateSlackPreview());
    document.getElementById('btn-add-cable').addEventListener('click', () => this.handleAddCable());
    document.getElementById('btn-auto-poles').addEventListener('click', () => this.handleAutoGeneratePoles());
    document.getElementById('btn-delete-cable').addEventListener('click', () => this.handleDeleteSelectedCable());

    // 4. Project Operations
    document.getElementById('btn-new-proj').addEventListener('click', () => this.handleNewProject());
    document.getElementById('btn-open-proj').addEventListener('click', () => document.getElementById('file-import-input').click());
    document.getElementById('file-import-input').addEventListener('change', (e) => this.handleFileImport(e));
    document.getElementById('btn-save-proj').addEventListener('click', () => this.handleSaveProject());
    document.getElementById('btn-export-kml').addEventListener('click', () => this.handleExportKML());

    // 5. Pencarian Lokasi (Geocoding)
    const searchInput = document.getElementById('input-search-map');
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.handleSearchLocation(searchInput.value.trim());
    });
  }

  onMapCoordSelected(lat, lng) {
    document.getElementById('input-node-lat').value = lat.toFixed(6);
    document.getElementById('input-node-lng').value = lng.toFixed(6);
    this.setStatus(`Titik koordinat dipilih: ${lat.toFixed(6)}, ${lng.toFixed(6)}`);
  }

  setStatus(msg) {
    const el = document.getElementById('status-msg');
    if (el) el.innerText = msg;
  }

  autoGenerateId() {
    const type = document.getElementById('combo-node-type').value;
    let prefix = "ODP";
    if (type.includes("ODC")) prefix = "ODC";
    else if (type.includes("POLE") || type.includes("Tiang")) prefix = "POLE";
    else if (type.includes("Closure")) prefix = "CLOS";

    const idInput = document.getElementById('input-node-id');
    if (idInput && !idInput.dataset.manual) {
      idInput.value = `${prefix}-${String(this.counter).padStart(2, '0')}`;
    }
  }

  handleSaveNode() {
    const id = document.getElementById('input-node-id').value.trim();
    const name = document.getElementById('input-node-name').value.trim() || id;
    const type = document.getElementById('combo-node-type').value;
    const lat = parseFloat(document.getElementById('input-node-lat').value);
    const lng = parseFloat(document.getElementById('input-node-lng').value);
    const cap = document.getElementById('input-node-cap').value.trim();
    const notes = document.getElementById('input-node-notes').value.trim();

    if (!id || isNaN(lat) || isNaN(lng)) {
      alert("Harap lengkapi ID Simpul dan klik peta untuk mengisi Latitude & Longitude!");
      return;
    }

    const isNew = !this.nodes.has(id);
    const node = { id, name, infra_type: type, latitude: lat, longitude: lng, capacity: cap, notes };

    this.nodes.set(id, node);
    this.mapManager.addOrUpdateMarker(node);
    this.refreshNodeTable();
    this.updateDropdownNodes();

    if (isNew) {
      this.counter++;
    }

    this.resetNodeForm();
    this.setStatus(`Simpul ${id} berhasil disimpan.`);
  }

  resetNodeForm() {
    document.getElementById('input-node-id').dataset.manual = "";
    document.getElementById('input-node-name').value = "";
    document.getElementById('input-node-lat').value = "";
    document.getElementById('input-node-lng').value = "";
    document.getElementById('input-node-notes').value = "";
    document.getElementById('btn-save-node').innerText = "➕ Simpan Titik Simpul";
    this.autoGenerateId();
  }

  refreshNodeTable() {
    const tbody = document.getElementById('tbody-nodes');
    tbody.innerHTML = '';

    this.nodes.forEach(node => {
      const tr = document.createElement('tr');
      tr.setAttribute('data-id', node.id);

      let badgeClass = 'badge-odp';
      if (node.infra_type.includes('ODC')) badgeClass = 'badge-odc';
      else if (node.infra_type.includes('POLE') || node.infra_type.includes('Tiang')) badgeClass = 'badge-pole';
      else if (node.infra_type.includes('Closure')) badgeClass = 'badge-closure';

      tr.innerHTML = `
        <td><input type="checkbox" class="chk-node" value="${node.id}"></td>
        <td><b>${node.id}</b></td>
        <td><span class="badge ${badgeClass}">${node.infra_type}</span></td>
        <td>${node.name}</td>
      `;

      tr.addEventListener('click', (e) => {
        if (e.target.tagName !== 'INPUT') {
          this.loadNodeToForm(node);
        }
      });

      tbody.appendChild(tr);
    });

    document.getElementById('lbl-total-nodes').innerText = `${this.nodes.size} Titik`;
  }

  loadNodeToForm(node) {
    document.getElementById('input-node-id').value = node.id;
    document.getElementById('input-node-name').value = node.name;
    document.getElementById('combo-node-type').value = node.infra_type;
    document.getElementById('input-node-lat').value = node.latitude;
    document.getElementById('input-node-lng').value = node.longitude;
    document.getElementById('input-node-cap').value = node.capacity || "";
    document.getElementById('input-node-notes').value = node.notes || "";
    document.getElementById('btn-save-node').innerText = "💾 Perbarui Titik Simpul";
    this.mapManager.flyTo(node.latitude, node.longitude);
  }

  selectNodeRow(nodeId) {
    if (this.nodes.has(nodeId)) {
      this.loadNodeToForm(this.nodes.get(nodeId));
    }
  }

  handleDeleteSelectedNode() {
    const chks = document.querySelectorAll('.chk-node:checked');
    if (chks.length === 0) {
      alert("Centang titik simpul yang ingin dihapus pada tabel!");
      return;
    }

    if (!confirm(`Hapus ${chks.length} titik simpul terpilih?`)) return;

    chks.forEach(chk => {
      const id = chk.value;
      this.nodes.delete(id);
      this.mapManager.removeMarker(id);
    });

    this.refreshNodeTable();
    this.updateDropdownNodes();
    this.setStatus(`${chks.length} simpul telah dihapus.`);
  }

  updateDropdownNodes() {
    const src = document.getElementById('combo-src-node');
    const dst = document.getElementById('combo-dst-node');
    const curSrc = src.value;
    const curDst = dst.value;

    src.innerHTML = '<option value="">-- Pilih Titik Asal --</option>';
    dst.innerHTML = '<option value="">-- Pilih Titik Tujuan --</option>';

    this.nodes.forEach(node => {
      const opt1 = new Option(`${node.id} (${node.name})`, node.id);
      const opt2 = new Option(`${node.id} (${node.name})`, node.id);
      src.add(opt1);
      dst.add(opt2);
    });

    if (this.nodes.has(curSrc)) src.value = curSrc;
    if (this.nodes.has(curDst)) dst.value = curDst;
  }

  async recalculateRoutePreview() {
    const srcId = document.getElementById('combo-src-node').value;
    const dstId = document.getElementById('combo-dst-node').value;
    const mode = document.getElementById('combo-routing-mode').value;

    if (!srcId || !dstId || srcId === dstId) {
      document.getElementById('val-span-dist').innerText = "0.0 m";
      document.getElementById('val-total-cable').innerText = "0.0 m";
      this.activeRouteCoords = [];
      this.activeRouteDistance = 0;
      return;
    }

    const nSrc = this.nodes.get(srcId);
    const nDst = this.nodes.get(dstId);

    try {
      this.setStatus(`Menghitung rute ${mode.toUpperCase()} dari ${srcId} ke ${dstId}...`);
      const resp = await fetch('/api/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_lat: nSrc.latitude,
          source_lng: nSrc.longitude,
          target_lat: nDst.latitude,
          target_lng: nDst.longitude,
          mode: mode
        })
      });

      const data = await resp.json();
      this.activeRouteDistance = data.distance_m;
      this.activeRouteCoords = data.path_coordinates;

      document.getElementById('val-span-dist').innerText = `${data.distance_m.toFixed(1)} m`;
      this.updateSlackPreview();
      this.setStatus(`Rute berhasil dikalkulasi: ${data.distance_m.toFixed(1)} m (${data.mode_used})`);
    } catch (e) {
      console.error(e);
      this.setStatus(`Gagal kalkulasi rute: ${e.message}`);
    }
  }

  updateSlackPreview() {
    const slackPct = parseFloat(document.getElementById('input-slack').value) || 0;
    const span = this.activeRouteDistance || 0;
    const total = span * (1 + slackPct / 100);
    document.getElementById('val-total-cable').innerText = `${total.toFixed(1)} m`;
  }

  handleAddCable() {
    const srcId = document.getElementById('combo-src-node').value;
    const dstId = document.getElementById('combo-dst-node').value;
    if (!srcId || !dstId || srcId === dstId || !this.activeRouteDistance) {
      alert("Pilih Titik Asal dan Tujuan yang berbeda serta pastikan rute terhitung!");
      return;
    }

    const nSrc = this.nodes.get(srcId);
    const nDst = this.nodes.get(dstId);
    const slackPct = parseFloat(document.getElementById('input-slack').value) || 10;
    const totalM = this.activeRouteDistance * (1 + slackPct / 100);
    const cableType = document.getElementById('combo-cable-type').value;

    const cableId = `CAB-${String(this.cableCounter).padStart(3, '0')}`;
    this.cableCounter++;

    const cable = {
      id: cableId,
      name: `Kabel ${srcId} ke ${dstId}`,
      cable_type: cableType,
      source_node_id: srcId,
      source_node_name: nSrc.name,
      source_lat: nSrc.latitude,
      source_lng: nSrc.longitude,
      target_node_id: dstId,
      target_node_name: nDst.name,
      target_lat: nDst.latitude,
      target_lng: nDst.longitude,
      span_distance_m: round(this.activeRouteDistance, 2),
      slack_percent: slackPct,
      total_length_m: round(totalM, 2),
      core_count: "24 Core",
      path_coordinates: this.activeRouteCoords
    };

    this.cables.set(cableId, cable);
    this.mapManager.addOrUpdateCable(cable);
    this.refreshCableTable();
    this.setStatus(`Rute kabel ${cableId} berhasil ditambahkan (${totalM.toFixed(1)} m).`);
  }

  async handleAutoGeneratePoles() {
    const srcId = document.getElementById('combo-src-node').value;
    const dstId = document.getElementById('combo-dst-node').value;
    if (!srcId || !dstId || !this.activeRouteDistance) {
      alert("Pilih Titik Asal dan Tujuan terlebih dahulu!");
      return;
    }

    const spacing = parseFloat(document.getElementById('input-spacing').value) || 80;
    const slackPct = parseFloat(document.getElementById('input-slack').value) || 10;
    const nSrc = this.nodes.get(srcId);
    const nDst = this.nodes.get(dstId);

    try {
      this.setStatus(`Menjalankan generator tiang otomatis per ${spacing}m...`);
      const resp = await fetch('/api/generate-poles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_node_id: srcId,
          source_node_name: nSrc.name,
          source_lat: nSrc.latitude,
          source_lng: nSrc.longitude,
          target_node_id: dstId,
          target_node_name: nDst.name,
          target_lat: nDst.latitude,
          target_lng: nDst.longitude,
          spacing_m: spacing,
          slack_percent: slackPct,
          path_coordinates: this.activeRouteCoords || [],
          start_pole_num: this.poleCounter,
          start_cable_num: this.cableCounter
        })
      });

      const res = await resp.json();
      res.generated_poles.forEach(p => {
        this.nodes.set(p.id, p);
        this.mapManager.addOrUpdateMarker(p);
      });
      res.generated_cables.forEach(c => {
        this.cables.set(c.id, c);
        this.mapManager.addOrUpdateCable(c);
      });

      this.poleCounter += res.generated_poles.length;
      this.cableCounter += res.generated_cables.length;

      this.refreshNodeTable();
      this.refreshCableTable();
      this.updateDropdownNodes();
      this.mapManager.fitAllBounds();
      this.setStatus(`Selesai: Dibuat ${res.generated_poles.length} tiang baru & ${res.generated_cables.length} rute bentangan kabel.`);
    } catch (e) {
      console.error(e);
      alert("Gagal membagi rute: " + e.message);
    }
  }

  refreshCableTable() {
    const tbody = document.getElementById('tbody-cables');
    tbody.innerHTML = '';
    let totalLen = 0;

    this.cables.forEach(c => {
      totalLen += c.total_length_m;
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><input type="checkbox" class="chk-cable" value="${c.id}"></td>
        <td><b>${c.id}</b></td>
        <td>${c.source_node_id} ➔ ${c.target_node_id}</td>
        <td>${c.total_length_m.toFixed(1)} m</td>
      `;
      tbody.appendChild(tr);
    });

    document.getElementById('lbl-total-cables').innerText = `${this.cables.size} Rute (${totalLen.toFixed(1)} m)`;
  }

  handleDeleteSelectedCable() {
    const chks = document.querySelectorAll('.chk-cable:checked');
    if (chks.length === 0) {
      alert("Centang rute kabel yang ingin dihapus!");
      return;
    }

    if (!confirm(`Hapus ${chks.length} rute kabel terpilih?`)) return;

    chks.forEach(chk => {
      const id = chk.value;
      this.cables.delete(id);
      this.mapManager.removeCable(id);
    });

    this.refreshCableTable();
    this.setStatus(`${chks.length} rute kabel telah dihapus.`);
  }

  async runAuditQC() {
    const nodesList = Array.from(this.nodes.values());
    const cablesList = Array.from(this.cables.values());

    try {
      const resp = await fetch('/api/review-audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nodes: nodesList,
          cables: cablesList,
          max_span_m: 120.0,
          min_span_m: 25.0
        })
      });

      const audit = await resp.json();
      document.getElementById('metric-total-cable').innerText = `${audit.total_real_cable_m.toFixed(1)} m`;
      document.getElementById('metric-total-poles').innerText = `${audit.total_poles} Tiang`;
      document.getElementById('metric-total-odp').innerText = `${audit.total_odp} ODP`;
      document.getElementById('metric-audit-status').innerText = audit.is_export_ready ? "Lolos (Ready)" : "Catatan QC";

      const tbody = document.getElementById('tbody-audit-findings');
      tbody.innerHTML = '';

      if (audit.findings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#059669;padding:12px;">✅ Seluruh parameter jarak dan topologi lulus audit QC.</td></tr>';
      } else {
        audit.findings.forEach(f => {
          const tr = document.createElement('tr');
          const badgeClass = f.severity === 'CRITICAL' ? 'badge-crit' : (f.severity === 'WARNING' ? 'badge-warn' : 'badge-pass');
          tr.innerHTML = `
            <td><span class="badge ${badgeClass}">${f.severity}</span></td>
            <td><b>${f.target_id}</b></td>
            <td>${f.description}</td>
            <td>${f.recommendation}</td>
          `;
          tbody.appendChild(tr);
        });
      }
    } catch (e) {
      console.error(e);
    }
  }

  async handleSearchLocation(q) {
    if (!q) return;
    this.setStatus(`Mencari wilayah '${q}'...`);
    try {
      const resp = await fetch(`/api/geocode?q=${encodeURIComponent(q)}`);
      const data = await resp.json();
      if (data.results && data.results.length > 0) {
        const item = data.results[0];
        const lat = parseFloat(item.lat);
        const lon = parseFloat(item.lon);
        this.mapManager.flyTo(lat, lon, 16);
        this.onMapCoordSelected(lat, lon);
        this.setStatus(`Wilayah ditemukan: ${item.display_name}`);
      } else {
        alert("Wilayah tidak ditemukan.");
      }
    } catch (e) {
      console.error(e);
    }
  }

  handleNewProject() {
    if (this.nodes.size > 0 && !confirm("Buat proyek baru? Data yang belum disimpan akan hilang.")) {
      return;
    }
    this.nodes.clear();
    this.cables.clear();
    this.counter = 1;
    this.poleCounter = 1;
    this.cableCounter = 1;
    this.mapManager.clearMarkers();
    this.mapManager.clearCables();
    this.refreshNodeTable();
    this.refreshCableTable();
    this.updateDropdownNodes();
    this.resetNodeForm();
    this.setStatus("✨ Proyek baru dibuat.");
  }

  async handleSaveProject() {
    const payload = {
      project_name: this.projectName,
      nodes: Array.from(this.nodes.values()),
      cables: Array.from(this.cables.values()),
      settings: {
        routing_mode: document.getElementById('combo-routing-mode').value,
        auto_pole_spacing_m: parseFloat(document.getElementById('input-spacing').value),
        slack_percentage: parseFloat(document.getElementById('input-slack').value)
      }
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${this.projectName}.ftth`;
    a.click();
    URL.revokeObjectURL(url);
    this.setStatus(`💾 Proyek disimpan sebagai ${this.projectName}.ftth`);
  }

  handleFileImport(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result);
        this.loadProjectFromJSON(data, file.name);
      } catch (err) {
        alert("File proyek rusak atau format tidak valid: " + err.message);
      }
    };
    reader.readAsText(file);
    event.target.value = '';
  }

  loadProjectFromJSON(data, filename) {
    this.nodes.clear();
    this.cables.clear();
    this.mapManager.clearMarkers();
    this.mapManager.clearCables();

    this.projectName = data.project_name || filename.replace(/\.[^/.]+$/, "");

    let maxNodeNum = 0;
    let maxPoleNum = 0;
    let maxCabNum = 0;

    (data.nodes || []).forEach(n => {
      this.nodes.set(n.id, n);
      this.mapManager.addOrUpdateMarker(n);

      const m = n.id.match(/\d+/g);
      if (m) {
        const val = parseInt(m[m.length - 1]);
        if (n.id.includes("POLE")) {
          if (val > maxPoleNum) maxPoleNum = val;
        } else {
          if (val > maxNodeNum) maxNodeNum = val;
        }
      }
    });

    (data.cables || []).forEach(c => {
      this.cables.set(c.id, c);
      this.mapManager.addOrUpdateCable(c);

      const m = c.id.match(/\d+/g);
      if (m) {
        const val = parseInt(m[m.length - 1]);
        if (val > maxCabNum) maxCabNum = val;
      }
    });

    this.counter = maxNodeNum + 1;
    this.poleCounter = maxPoleNum + 1;
    this.cableCounter = maxCabNum + 1;

    this.refreshNodeTable();
    this.refreshCableTable();
    this.updateDropdownNodes();
    this.resetNodeForm();
    this.mapManager.fitAllBounds();
    this.setStatus(`📂 Proyek '${this.projectName}' berhasil dimuat (${this.nodes.size} simpul, ${this.cables.size} kabel).`);
  }

  async handleExportKML() {
    if (this.nodes.size === 0) {
      alert("Belum ada data titik infrastruktur untuk diekspor!");
      return;
    }

    const payload = {
      project_name: this.projectName,
      nodes: Array.from(this.nodes.values()),
      cables: Array.from(this.cables.values()),
      settings: {}
    };

    try {
      this.setStatus("Mengekspor KML...");
      const resp = await fetch('/api/export-kml', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) throw new Error("Gagal generate KML dari server");

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${this.projectName}.kml`;
      a.click();
      URL.revokeObjectURL(url);
      this.setStatus(`🌍 File KML ${this.projectName}.kml berhasil diunduh!`);
    } catch (e) {
      console.error(e);
      alert("Gagal ekspor KML: " + e.message);
    }
  }
}

function round(val, dec) {
  return Number(Math.round(val + 'e' + dec) + 'e-' + dec);
}

// Inisialisasi saat DOM siap
window.addEventListener('DOMContentLoaded', () => {
  window.ftthApp = new FTTHWebApp();
});
