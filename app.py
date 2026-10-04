"""
TopoFiberix - FTTH Network Designer (Streamlit Edition)
Aplikasi Web GIS Interaktif untuk Perencanaan, Routing Kabel, Audit Quality Control,
Impor Multi-Format (KML, KMZ, CSV, XLSX), dan Ekspor Google Earth (KML).
Didesain secara murni menggunakan Streamlit, Folium, dan Pandas (bebas Uvicorn/FastAPI).
"""

import io
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

# Import modul domain geospasial & FTTH dari ftth_planner
from ftth_planner.models import (
    FTTHNode,
    FTTHNodeType,
    CableSegment,
    CableType,
    KMLExporter,
)
from ftth_planner.distance import (
    calculate_geodesic_distance,
    calculate_cable_length_with_slack,
    fetch_osrm_road_route,
    interpolate_geodesic_point,
    split_road_polyline_into_spans,
)
from ftth_planner.importer import FTTHDataImporter, DataImportError

# ==============================================================================
# 1. KONFIGURASI HALAMAN STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="TopoFiberix - Network Designer",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tampilan modern light theme
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div.stButton > button {
        border-radius: 6px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. INISIALISASI SESSION STATE
# ==============================================================================
if "nodes" not in st.session_state:
    st.session_state.nodes: Dict[str, FTTHNode] = {}

if "cables" not in st.session_state:
    st.session_state.cables: Dict[str, CableSegment] = {}

if "center_lat" not in st.session_state:
    st.session_state.center_lat = -6.2592
if "center_lon" not in st.session_state:
    st.session_state.center_lon = 106.8145
if "zoom_level" not in st.session_state:
    st.session_state.zoom_level = 15

if "max_span" not in st.session_state:
    st.session_state.max_span = 120.0
if "min_span" not in st.session_state:
    st.session_state.min_span = 25.0
if "slack_pct" not in st.session_state:
    st.session_state.slack_pct = 10.0

if "clicked_lat" not in st.session_state:
    st.session_state.clicked_lat = None
if "clicked_lon" not in st.session_state:
    st.session_state.clicked_lon = None


# Helper untuk mengonversi NodeType ke warna marker Folium
def get_node_marker_color(infra_type: FTTHNodeType) -> str:
    color_map = {
        FTTHNodeType.ODC: "blue",
        FTTHNodeType.ODP: "purple",
        FTTHNodeType.POLE: "green",
        FTTHNodeType.CLOSURE: "orange",
        FTTHNodeType.HANDHOLE: "darkblue",
        FTTHNodeType.DROP_NODE: "cadetblue",
        FTTHNodeType.ONT: "red",
    }
    return color_map.get(infra_type, "blue")


# Helper untuk mengonversi NodeType ke ikon Folium
def get_node_icon_name(infra_type: FTTHNodeType) -> str:
    icon_map = {
        FTTHNodeType.ODC: "server",
        FTTHNodeType.ODP: "share-alt",
        FTTHNodeType.POLE: "flag",
        FTTHNodeType.CLOSURE: "wrench",
        FTTHNodeType.HANDHOLE: "inbox",
        FTTHNodeType.DROP_NODE: "circle",
        FTTHNodeType.ONT: "home",
    }
    return icon_map.get(infra_type, "info-sign")


# Helper memuat data contoh (Kemang, Jakarta Selatan)
def load_sample_kemang_data():
    st.session_state.nodes.clear()
    st.session_state.cables.clear()

    odc = FTTHNode(
        id="ODC-KMG-01",
        name="ODC Sentral Kemang",
        latitude=-6.2592,
        longitude=106.8145,
        infra_type=FTTHNodeType.ODC,
        capacity="288 Core"
    )
    odp1 = FTTHNode(
        id="ODP-KMG-01",
        name="ODP Cluster Kemang 1",
        latitude=-6.2615,
        longitude=106.8170,
        infra_type=FTTHNodeType.ODP,
        capacity="1:8 Splitter"
    )
    odp2 = FTTHNode(
        id="ODP-KMG-02",
        name="ODP Cluster Kemang 2",
        latitude=-6.2570,
        longitude=106.8120,
        infra_type=FTTHNodeType.ODP,
        capacity="1:16 Splitter"
    )
    st.session_state.nodes[odc.id] = odc
    st.session_state.nodes[odp1.id] = odp1
    st.session_state.nodes[odp2.id] = odp2

    # Tambahkan rute kabel OSRM / Geodesik
    route_coords1 = fetch_osrm_road_route((-6.2592, 106.8145), (-6.2615, 106.8170))
    span1 = calculate_geodesic_distance((-6.2592, 106.8145), (-6.2615, 106.8170))
    real_len1 = span1 * 1.10

    c1 = CableSegment(
        id="CABLE-ODC-ODP-01",
        source_node_id="ODC-KMG-01",
        target_node_id="ODP-KMG-01",
        cable_type=CableType.FEEDER,
        span_distance_m=span1,
        total_length_m=real_len1,
        slack_percentage=10.0,
        route_polyline=route_coords1
    )

    route_coords2 = fetch_osrm_road_route((-6.2592, 106.8145), (-6.2570, 106.8120))
    span2 = calculate_geodesic_distance((-6.2592, 106.8145), (-6.2570, 106.8120))
    real_len2 = span2 * 1.10

    c2 = CableSegment(
        id="CABLE-ODC-ODP-02",
        source_node_id="ODC-KMG-01",
        target_node_id="ODP-KMG-02",
        cable_type=CableType.DISTRIBUTION,
        span_distance_m=span2,
        total_length_m=real_len2,
        slack_percentage=10.0,
        route_polyline=route_coords2
    )

    st.session_state.cables[c1.id] = c1
    st.session_state.cables[c2.id] = c2

    st.session_state.center_lat = -6.2592
    st.session_state.center_lon = 106.8145
    st.session_state.zoom_level = 15


# ==============================================================================
# 3. SIDEBAR / PANEL KONTROL
# ==============================================================================
with st.sidebar:
    st.title("📡 TopoFiberix")
    st.caption("FTTH Network Designer & GIS Survey Module")
    st.divider()

    # --- SECTION 1: SEARCH & LOCATION ---
    st.subheader("🔍 Pencarian Wilayah")
    search_query = st.text_input("Cari Kota / Jalan / Landmark:", placeholder="Contoh: Kemang, Jakarta")
    if st.button("Cari Lokasi", use_container_width=True):
        if search_query.strip():
            try:
                geolocator = Nominatim(user_agent="topofiberix_streamlit_app")
                location = geolocator.geocode(search_query)
                if location:
                    st.session_state.center_lat = location.latitude
                    st.session_state.center_lon = location.longitude
                    st.session_state.zoom_level = 15
                    st.success(f"Ditemukan: {location.address[:40]}...")
                else:
                    st.error("Lokasi tidak ditemukan. Coba kata kunci lain.")
            except Exception as e:
                st.error(f"Gagal geocoding: {str(e)}")

    st.divider()

    # --- SECTION 2: PARAMETER DESAIN ---
    st.subheader("⚙️ Parameter Desain")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.session_state.max_span = st.number_input(
            "Max Span (m):", min_value=30.0, max_value=300.0, value=st.session_state.max_span, step=5.0
        )
    with col_p2:
        st.session_state.min_span = st.number_input(
            "Min Span (m):", min_value=5.0, max_value=100.0, value=st.session_state.min_span, step=5.0
        )

    st.session_state.slack_pct = st.slider(
        "Cadangan Slack Kabel (%):", min_value=0.0, max_value=50.0, value=st.session_state.slack_pct, step=1.0
    )

    st.divider()

    # --- SECTION 3: TAMBAH SIMPUL (NODES) ---
    st.subheader("📌 Tambah Simpul Baru")
    node_type_str = st.selectbox(
        "Jenis Infrastruktur:",
        [t.value for t in FTTHNodeType],
        index=0
    )
    # Temukan enum FTTHNodeType
    selected_node_type = next((t for t in FTTHNodeType if t.value == node_type_str), FTTHNodeType.ODP)

    # Otomatisasi penomoran ID
    existing_type_count = sum(1 for n in st.session_state.nodes.values() if n.infra_type == selected_node_type)
    default_node_id = f"{selected_node_type.short_code}-{existing_type_count + 1:02d}"

    node_id_input = st.text_input("ID Simpul:", value=default_node_id)
    node_name_input = st.text_input("Nama / Label Simpul:", value=f"{selected_node_type.short_code} Point {existing_type_count + 1}")

    col_lat, col_lon = st.columns(2)
    with col_lat:
        default_lat = st.session_state.clicked_lat if st.session_state.clicked_lat else st.session_state.center_lat
        input_lat = st.number_input("Latitude:", value=float(default_lat), format="%.6f")
    with col_lon:
        default_lon = st.session_state.clicked_lon if st.session_state.clicked_lon else st.session_state.center_lon
        input_lon = st.number_input("Longitude:", value=float(default_lon), format="%.6f")

    if st.button("➕ Tambahkan Simpul", use_container_width=True):
        if not node_id_input.strip():
            st.error("ID Simpul tidak boleh kosong.")
        else:
            new_node = FTTHNode(
                id=node_id_input.strip(),
                name=node_name_input.strip(),
                latitude=input_lat,
                longitude=input_lon,
                infra_type=selected_node_type,
            )
            st.session_state.nodes[new_node.id] = new_node
            st.session_state.center_lat = input_lat
            st.session_state.center_lon = input_lon
            st.success(f"Simpul {new_node.id} berhasil ditambahkan!")
            st.rerun()

    st.divider()

    # --- SECTION 4: ROUTING & PENARIKAN KABEL ---
    st.subheader("🔗 Penarikan & Routing Kabel")
    node_ids = list(st.session_state.nodes.keys())

    if len(node_ids) < 2:
        st.info("Tambahkan minimal 2 simpul untuk melakukan penarikan kabel.")
    else:
        src_id = st.selectbox("Simpul Asal (Source):", node_ids, index=0)
        tgt_id = st.selectbox("Simpul Tujuan (Target):", node_ids, index=min(1, len(node_ids) - 1))

        routing_mode = st.radio("Mode Routing:", ["Road-Snapped (Jalan Raya)", "Straight (Garis Lurus)"], index=0)
        auto_poles = st.checkbox("Generasi Tiang Otomatis (Jika Over Span)", value=True)

        if st.button("🔌 Tarik Kabel & Routing", use_container_width=True):
            if src_id == tgt_id:
                st.error("Simpul Asal dan Tujuan tidak boleh sama.")
            else:
                src_node = st.session_state.nodes[src_id]
                tgt_node = st.session_state.nodes[tgt_id]

                p1 = (src_node.latitude, src_node.longitude)
                p2 = (tgt_node.latitude, tgt_node.longitude)

                if "Road-Snapped" in routing_mode:
                    route_poly = fetch_osrm_road_route(p1, p2)
                else:
                    route_poly = [p1, p2]

                span_dist = calculate_geodesic_distance(p1, p2)
                total_len = span_dist * (1.0 + st.session_state.slack_pct / 100.0)

                cable_id = f"CABLE-{src_id}-{tgt_id}"
                new_cable = CableSegment(
                    id=cable_id,
                    source_node_id=src_id,
                    target_node_id=tgt_id,
                    cable_type=CableType.DISTRIBUTION,
                    span_distance_m=span_dist,
                    total_length_m=total_len,
                    slack_percentage=st.session_state.slack_pct,
                    route_polyline=route_poly,
                )
                st.session_state.cables[cable_id] = new_cable

                # Generasi tiang otomatis jika span > max_span
                poles_added = 0
                if auto_poles and span_dist > st.session_state.max_span:
                    spans = split_road_polyline_into_spans(route_poly, st.session_state.max_span)
                    for idx, pt in enumerate(spans[1:-1], 1):
                        pole_id = f"POLE-{src_id}-{tgt_id}-{idx:02d}"
                        if pole_id not in st.session_state.nodes:
                            st.session_state.nodes[pole_id] = FTTHNode(
                                id=pole_id,
                                name=f"Tiang Sisipan {idx}",
                                latitude=pt[0],
                                longitude=pt[1],
                                infra_type=FTTHNodeType.POLE,
                            )
                            poles_added += 1

                msg = f"Kabel {cable_id} ({total_len:.1f}m) berhasil ditarik!"
                if poles_added > 0:
                    msg += f" Ditambahkan {poles_added} tiang perantara."
                st.success(msg)
                st.rerun()

    st.divider()

    # --- SECTION 5: IMPOR MULTI-FORMAT ---
    st.subheader("📥 Impor File (KML/KMZ/CSV/XLSX)")
    uploaded_file = st.file_uploader(
        "Pilih file geospasial / survey:",
        type=["kml", "kmz", "csv", "xlsx", "xls"],
        help="Mendukung KML, KMZ, CSV, dan Excel dengan pencocokan kolom otomatis."
    )
    import_mode = st.radio("Mode Impor:", ["Gabungkan (Merge)", "Gantikan (Replace)"], index=0)

    if uploaded_file is not None:
        if st.button("🚀 Proses Impor File", use_container_width=True):
            try:
                content = uploaded_file.read()
                filename = uploaded_file.name

                res = FTTHDataImporter.import_from_bytes(content, filename)

                if "Gantikan" in import_mode:
                    st.session_state.nodes.clear()
                    st.session_state.cables.clear()

                added_n = 0
                for n in res.nodes:
                    if n.id not in st.session_state.nodes:
                        st.session_state.nodes[n.id] = n
                        added_n += 1

                added_c = 0
                for c in res.cables:
                    if c.id not in st.session_state.cables:
                        st.session_state.cables[c.id] = c
                        added_c += 1

                if res.nodes:
                    st.session_state.center_lat = res.nodes[0].latitude
                    st.session_state.center_lon = res.nodes[0].longitude

                st.success(f"Impor Berhasil! Ditambahkan {added_n} titik & {added_c} rute kabel.")
                if res.warnings:
                    for w in res.warnings[:3]:
                        st.warning(w)
                st.rerun()
            except Exception as e:
                st.error(f"Gagal memproses file: {str(e)}")

    if st.button("📂 Muat Data Sampel Kemang", use_container_width=True):
        load_sample_kemang_data()
        st.success("Data sampel Kemang berhasil dimuat!")
        st.rerun()

    st.divider()

    # --- SECTION 6: EKSPOR DATA ---
    st.subheader("🚀 Ekspor Google Earth (KML)")
    if st.session_state.nodes:
        kml_string = KMLExporter.export_to_string(
            nodes=list(st.session_state.nodes.values()),
            cables=list(st.session_state.cables.values()),
            document_name="TopoFiberix Network Plan"
        )
        st.download_button(
            label="🌍 Unduh File KML",
            data=kml_string,
            file_name="TopoFiberix_Network_Plan.kml",
            mime="application/vnd.google-earth.kml+xml",
            use_container_width=True
        )


# ==============================================================================
# 4. AREA UTAMA (MAIN PANEL TABS)
# ==============================================================================
tab_map, tab_qc, tab_data = st.tabs(["🗺️ Peta Interaktif GIS", "🔍 Quality Control & Audit", "📋 Tabel Data & Manajer"])

# --- TAB 1: PETA INTERAKTIF FOLIUM ---
with tab_map:
    st.subheader("🗺️ Viewport Spasial Jaringan FTTH")

    # Inisialisasi peta Folium
    m = folium.Map(
        location=[st.session_state.center_lat, st.session_state.center_lon],
        zoom_start=st.session_state.zoom_level,
        tiles="OpenStreetMap"
    )

    # Tambahkan Tile Layer Tambahan (Satelit & CartoDB)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="🛰️ Citra Satelit (Esri)"
    ).add_to(m)

    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{y}/{x}{r}.png",
        attr="CartoDB Dark",
        name="🌙 Dark Mode"
    ).add_to(m)

    # Render Cable Polyline
    for c in st.session_state.cables.values():
        if c.route_polyline:
            color = "#0D6EFD" if c.cable_type == CableType.FEEDER else "#0EA5E9"
            folium.PolyLine(
                locations=c.route_polyline,
                color=color,
                weight=4,
                opacity=0.85,
                popup=f"<b>Kabel: {c.id}</b><br>Jarak Span: {c.span_distance_m:.1f} m<br>Total Riil: {c.total_length_m:.1f} m (Slack {c.slack_percentage}%)"
            ).add_to(m)

    # Render Node Markers
    for n in st.session_state.nodes.values():
        color = get_node_marker_color(n.infra_type)
        icon_name = get_node_icon_name(n.infra_type)

        popup_html = f"""
        <div style="font-family: sans-serif; font-size: 12px;">
            <b>ID:</b> {n.id}<br>
            <b>Nama:</b> {n.name}<br>
            <b>Tipe:</b> {n.infra_type.value}<br>
            <b>Kapasitas:</b> {n.capacity}<br>
            <b>Koordinat:</b> {n.latitude:.6f}, {n.longitude:.6f}
        </div>
        """

        folium.Marker(
            location=[n.latitude, n.longitude],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{n.id} - {n.name}",
            icon=folium.Icon(color=color, icon=icon_name, prefix="fa")
        ).add_to(m)

    folium.LayerControl().add_to(m)

    # Display Map via streamlit-folium
    map_data = st_folium(m, width="100%", height=620)

    # Inspeksi klik peta untuk auto-fill koordinat
    if map_data and map_data.get("last_clicked"):
        click_lat = map_data["last_clicked"]["lat"]
        click_lon = map_data["last_clicked"]["lng"]
        st.session_state.clicked_lat = click_lat
        st.session_state.clicked_lon = click_lon
        st.info(f"📍 Koordinat terpilih dari peta: Lat: {click_lat:.6f}, Lon: {click_lon:.6f}. Koordinat otomatis terisi di form sidebar!")

# --- TAB 2: QUALITY CONTROL & AUDIT ---
with tab_qc:
    st.subheader("🔍 Audit Kelayakan Quality Control Jaringan")

    total_nodes = len(st.session_state.nodes)
    total_cables = len(st.session_state.cables)
    total_poles = sum(1 for n in st.session_state.nodes.values() if n.infra_type == FTTHNodeType.POLE)
    total_odc = sum(1 for n in st.session_state.nodes.values() if n.infra_type == FTTHNodeType.ODC)
    total_odp = sum(1 for n in st.session_state.nodes.values() if n.infra_type == FTTHNodeType.ODP)
    total_real_m = sum(c.total_length_m for c in st.session_state.cables.values())

    over_span_count = 0
    findings = []

    if total_nodes == 0:
        findings.append({
            "Severity": "❌ CRITICAL",
            "Category": "Integritas Data",
            "Target": "N/A",
            "Value": "0 Titik",
            "Description": "Belum ada simpul infrastruktur yang didaftarkan pada proyek.",
            "Recommendation": "Tambahkan titik ODC, ODP, atau Tiang melalui sidebar atau impor file."
        })
    else:
        for n in st.session_state.nodes.values():
            if not n.name.strip():
                findings.append({
                    "Severity": "⚠️ WARNING",
                    "Category": "Atribut Simpul",
                    "Target": n.id,
                    "Value": "Nama Kosong",
                    "Description": f"Simpul {n.id} belum memiliki label nama deskriptif.",
                    "Recommendation": "Lengkapi nama titik agar mudah diidentifikasi di lapangan."
                })

        for c in st.session_state.cables.values():
            if c.span_distance_m > st.session_state.max_span:
                over_span_count += 1
                severity = "❌ CRITICAL" if c.span_distance_m > (st.session_state.max_span * 1.35) else "⚠️ WARNING"
                findings.append({
                    "Severity": severity,
                    "Category": "Span Tiang",
                    "Target": f"{c.source_node_id} ➔ {c.target_node_id}",
                    "Value": f"{c.span_distance_m:.1f} m (Max: {st.session_state.max_span:.0f} m)",
                    "Description": f"Bentangan kabel melebihi batas maksimal {st.session_state.max_span:.0f}m.",
                    "Recommendation": "Gunakan fitur Generasi Tiang Otomatis untuk menyisipkan tiang perantara."
                })

    # Display KPI Cards
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    with col_k1:
        st.metric("Total Simpul", f"{total_nodes} Titik", f"{total_odc} ODC | {total_odp} ODP")
    with col_k2:
        st.metric("Total Tiang (Poles)", f"{total_poles} Unit", "Tiang Perantara & Jalur")
    with col_k3:
        if total_real_m >= 1000:
            st.metric("Total Kabel Riil", f"{total_real_m/1000.0:.2f} km", f"{total_cables} Rute Kabel")
        else:
            st.metric("Total Kabel Riil", f"{total_real_m:.1f} m", f"{total_cables} Rute Kabel")
    with col_k4:
        st.metric("Pelanggaran Span", f"{over_span_count} Segmen", f"Batas Max: {st.session_state.max_span:.0f} m")

    st.divider()

    # Status Banner
    has_critical = any(f["Severity"].startswith("❌") for f in findings)
    has_warning = any(f["Severity"].startswith("⚠️") for f in findings)

    if has_critical:
        st.error("❌ **DESAIN DITOLAK (CRITICAL ERROR):** Ditemukan galat kritis pada data geospasial atau bentangan kabel.")
    elif has_warning:
        st.warning("⚠️ **DESAIN PERLU DITINJAU (WARNING):** Terdapat beberapa bentangan kabel melebihi batas toleransi.")
    else:
        st.success("✅ **DESAIN MEMENUHI STANDAR TEKNIS:** Seluruh simpul dan bentangan kabel dalam kondisi ideal.")

    st.subheader(f"📋 Rincian Temuan Audit ({len(findings)} Item)")
    if findings:
        df_qc = pd.DataFrame(findings)
        st.dataframe(df_qc, use_container_width=True, hide_index=True)
    else:
        st.info("Tidak ada catatan temuan. Desain jaringan 100% bebas galat!")

# --- TAB 3: TABEL DATA & MANAJER ---
with tab_data:
    st.subheader("📋 Manajemen Data Simpul & Kabel")

    col_t1, col_t2 = st.columns(2)

    with col_t1:
        st.markdown("##### 📌 Tabel Simpul Infrastruktur")
        if st.session_state.nodes:
            node_data = [
                {
                    "ID": n.id,
                    "Nama": n.name,
                    "Tipe": n.infra_type.short_code,
                    "Latitude": n.latitude,
                    "Longitude": n.longitude,
                    "Kapasitas": n.capacity,
                }
                for n in st.session_state.nodes.values()
            ]
            st.dataframe(pd.DataFrame(node_data), use_container_width=True, hide_index=True)

            if st.button("🗑️ Hapus Seluruh Simpul", type="secondary"):
                st.session_state.nodes.clear()
                st.session_state.cables.clear()
                st.success("Seluruh simpul dan kabel berhasil dibersihkan.")
                st.rerun()
        else:
            st.caption("Belum ada data simpul.")

    with col_t2:
        st.markdown("##### 🔗 Tabel Jalur Kabel")
        if st.session_state.cables:
            cable_data = [
                {
                    "ID": c.id,
                    "Asal": c.source_node_id,
                    "Tujuan": c.target_node_id,
                    "Span (m)": f"{c.span_distance_m:.1f}",
                    "Slack (%)": f"{c.slack_percentage:.0f}%",
                    "Total Riil (m)": f"{c.total_length_m:.1f}",
                }
                for c in st.session_state.cables.values()
            ]
            st.dataframe(pd.DataFrame(cable_data), use_container_width=True, hide_index=True)

            if st.button("🗑️ Hapus Seluruh Rute Kabel", type="secondary"):
                st.session_state.cables.clear()
                st.success("Seluruh rute kabel berhasil dibersihkan.")
                st.rerun()
        else:
            st.caption("Belum ada data kabel.")
