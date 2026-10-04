"""
Modul Panel Routing Kabel, Kalkulasi Jarak, dan Generator Tiang Otomatis (Modul 2)
Mendukung Road-Snapped Routing berbasis OpenStreetMap (OSRM API) sehingga jalur kabel
dan penempatan tiang baru otomatis melengkung presisi mengikuti kontur jalan raya,
menghindari perlintasan menembus rumah atau gedung warga.
"""

from typing import Dict, List, Optional, Tuple
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .distance import (
    calculate_cable_length_with_slack,
    calculate_geodesic_distance,
    calculate_pole_distribution,
    fetch_osrm_road_route,
    interpolate_geodesic_point,
    split_road_polyline_into_spans,
)
from .models import CableSegment, CableType, FTTHNode, FTTHNodeType


class RoadRouteWorker(QThread):
    """Worker thread untuk mengambil rute kontur jalan dari OSRM secara asinkron."""
    routeCalculated = pyqtSignal(float, list)  # total_distance_m, path_coordinates
    routeFailed = pyqtSignal(str)

    def __init__(self, point_a: Tuple[float, float], point_b: Tuple[float, float], parent=None):
        super().__init__(parent)
        self.point_a = point_a
        self.point_b = point_b

    def run(self):
        try:
            dist, path = fetch_osrm_road_route(self.point_a, self.point_b, timeout_sec=8)
            self.routeCalculated.emit(dist, path)
        except Exception as e:
            self.routeFailed.emit(str(e))


class FTTHRoutingWidget(QWidget):
    """
    Widget antarmuka untuk perhitungan jarak spasial, Road-Snapped Routing OSRM,
    manajemen rute kabel, dan Automatic Route Spacing & Pole Generator.
    """
    cableAdded = pyqtSignal(CableSegment)
    cableDeleted = pyqtSignal(str)
    allCablesCleared = pyqtSignal()
    cableSelected = pyqtSignal(str)

    # Sinyal batch saat generator otomatis membuat tiang dan rute kabel
    polesBatchGenerated = pyqtSignal(list)   # List[FTTHNode]
    cablesBatchGenerated = pyqtSignal(list)  # List[CableSegment]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes_dict: Dict[str, FTTHNode] = {}
        self.cables_dict: Dict[str, CableSegment] = {}
        self.cable_counter = 1
        self.pole_counter = 1

        # State rute aktif (koordinat kontur rute saat ini)
        self.current_route_path: List[Tuple[float, float]] = []
        self.current_route_distance: float = 0.0
        self.route_worker: Optional[RoadRouteWorker] = None

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)

        # -------------------------------------------------------------
        # 1. GROUPBOX: Form Pemilihan Titik Asal, Tujuan & Mode Routing
        # -------------------------------------------------------------
        form_group = QGroupBox("📏 Form Rute Kabel dan Titik Acuan")
        form_layout = QVBoxLayout(form_group)
        form_layout.setSpacing(10)

        # Mode Routing (Road-Snapped vs Garis Lurus)
        mode_container = QVBoxLayout()
        mode_container.setSpacing(4)
        lbl_mode = QLabel("Metode Routing Jalur:")
        lbl_mode.setStyleSheet("font-weight: 600; color: #334155;")
        self.combo_routing_mode = QComboBox()
        self.combo_routing_mode.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_routing_mode.setMinimumContentsLength(10)
        self.combo_routing_mode.addItem("🛣️  Ikuti Kontur Jalan (OSRM Road-Snapped)", "road")
        self.combo_routing_mode.addItem("📏  Garis Lurus (Aerial / Direct Line)", "straight")
        self.combo_routing_mode.currentIndexChanged.connect(self._recalculate_distance)
        mode_container.addWidget(lbl_mode)
        mode_container.addWidget(self.combo_routing_mode)
        form_layout.addLayout(mode_container)

        # Titik Asal (Source) & Titik Tujuan (Destination)
        node_grid = QGridLayout()
        node_grid.setHorizontalSpacing(10)
        node_grid.setVerticalSpacing(4)

        lbl_src = QLabel("Titik Asal (Source):")
        lbl_src.setStyleSheet("font-weight: 600; color: #334155;")
        self.combo_source = QComboBox()
        self.combo_source.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_source.setMinimumContentsLength(6)
        self.combo_source.currentIndexChanged.connect(self._recalculate_distance)

        lbl_dst = QLabel("Titik Tujuan (Dest):")
        lbl_dst.setStyleSheet("font-weight: 600; color: #334155;")
        self.combo_dest = QComboBox()
        self.combo_dest.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_dest.setMinimumContentsLength(6)
        self.combo_dest.currentIndexChanged.connect(self._recalculate_distance)

        node_grid.addWidget(lbl_src, 0, 0)
        node_grid.addWidget(lbl_dst, 0, 1)
        node_grid.addWidget(self.combo_source, 1, 0)
        node_grid.addWidget(self.combo_dest, 1, 1)
        form_layout.addLayout(node_grid)

        # Tipe Kabel & Core
        cable_meta_grid = QGridLayout()
        cable_meta_grid.setHorizontalSpacing(10)
        cable_meta_grid.setVerticalSpacing(4)

        lbl_type = QLabel("Jenis Kabel:")
        lbl_type.setStyleSheet("font-weight: 600; color: #334155;")
        self.combo_cable_type = QComboBox()
        self.combo_cable_type.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_cable_type.setMinimumContentsLength(8)
        for c_type in CableType:
            self.combo_cable_type.addItem(c_type.value, c_type)
        self.combo_cable_type.currentIndexChanged.connect(self._on_cable_type_changed)

        lbl_core = QLabel("Kapasitas Core:")
        lbl_core.setStyleSheet("font-weight: 600; color: #334155;")
        self.combo_core = QComboBox()
        self.combo_core.setEditable(True)
        self.combo_core.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_core.setMinimumContentsLength(6)
        self._update_core_presets(self.combo_cable_type.currentData())

        cable_meta_grid.addWidget(lbl_type, 0, 0)
        cable_meta_grid.addWidget(lbl_core, 0, 1)
        cable_meta_grid.addWidget(self.combo_cable_type, 1, 0)
        cable_meta_grid.addWidget(self.combo_core, 1, 1)
        cable_meta_grid.setColumnStretch(0, 3)
        cable_meta_grid.setColumnStretch(1, 2)
        form_layout.addLayout(cable_meta_grid)

        # Pengaturan Persentase Slack / Cadangan Kabel
        slack_container = QHBoxLayout()
        lbl_slack = QLabel("Cadangan Kabel (Slack):")
        lbl_slack.setStyleSheet("font-weight: 600; color: #334155;")
        self.spin_slack = QDoubleSpinBox()
        self.spin_slack.setRange(0.0, 100.0)
        self.spin_slack.setSingleStep(1.0)
        self.spin_slack.setValue(10.0)  # Default 10%
        self.spin_slack.setDecimals(1)
        self.spin_slack.setSuffix(" %")
        self.spin_slack.setFixedWidth(115)
        self.spin_slack.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_slack.valueChanged.connect(self._update_calculation_labels)

        slack_container.addWidget(lbl_slack)
        slack_container.addStretch()
        slack_container.addWidget(self.spin_slack)
        form_layout.addLayout(slack_container)

        # Box Hasil Metrik Jarak Real-Time (Sleek Modern Card)
        calc_box = QFrame()
        calc_box.setObjectName("calcBox")
        calc_box_layout = QVBoxLayout(calc_box)
        calc_box_layout.setContentsMargins(12, 12, 12, 12)
        calc_box_layout.setSpacing(6)

        header_calc = QLabel("HASIL KALKULASI PANJANG KABEL")
        header_calc.setStyleSheet("font-size: 11px; font-weight: bold; color: #0284c7; letter-spacing: 0.5px;")
        calc_box_layout.addWidget(header_calc)

        row1 = QHBoxLayout()
        self.lbl_span_title = QLabel("Jarak Bentangan (Jalan):")
        self.lbl_span_title.setStyleSheet("color: #64748b; font-size: 12px;")
        self.lbl_span_distance = QLabel("0.00 m")
        self.lbl_span_distance.setStyleSheet("color: #0f172a; font-weight: 700; font-size: 13px; padding-right: 4px;")
        self.lbl_span_distance.setAlignment(Qt.AlignmentFlag.AlignRight)
        row1.addWidget(self.lbl_span_title)
        row1.addWidget(self.lbl_span_distance)
        calc_box_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.lbl_slack_title = QLabel("Cadangan Slack (+10%):")
        self.lbl_slack_title.setStyleSheet("color: #64748b; font-size: 12px;")
        self.lbl_slack_meter = QLabel("0.00 m")
        self.lbl_slack_meter.setStyleSheet("color: #0284c7; font-weight: 700; font-size: 13px; padding-right: 4px;")
        self.lbl_slack_meter.setAlignment(Qt.AlignmentFlag.AlignRight)
        row2.addWidget(self.lbl_slack_title)
        row2.addWidget(self.lbl_slack_meter)
        calc_box_layout.addLayout(row2)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #e2e8f0; max-height: 1px; margin: 3px 0;")
        calc_box_layout.addWidget(divider)

        row3 = QHBoxLayout()
        lbl_tot_title = QLabel("TOTAL KABEL RIIL:")
        lbl_tot_title.setStyleSheet("color: #059669; font-size: 12px; font-weight: bold;")
        self.lbl_total_cable = QLabel("0.00 m")
        self.lbl_total_cable.setStyleSheet("color: #059669; font-size: 15px; font-weight: bold; padding-right: 4px;")
        self.lbl_total_cable.setAlignment(Qt.AlignmentFlag.AlignRight)
        row3.addWidget(lbl_tot_title)
        row3.addWidget(self.lbl_total_cable)
        calc_box_layout.addLayout(row3)

        form_layout.addWidget(calc_box)

        # Tombol Manual Satu Rute Langsung
        self.btn_save_direct_cable = QPushButton("➕  Hubungkan 1 Jalur Mengikuti Jalan")
        self.btn_save_direct_cable.setObjectName("btnSaveNode")
        self.btn_save_direct_cable.setMinimumHeight(38)
        self.btn_save_direct_cable.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_direct_cable.clicked.connect(self._handle_save_direct_cable)
        form_layout.addWidget(self.btn_save_direct_cable)

        layout.addWidget(form_group)

        # -------------------------------------------------------------
        # 2. GROUPBOX: Automatic Route Spacing & Pole Generator
        # -------------------------------------------------------------
        auto_group = QGroupBox("⚡ Generator Tiang dan Rute Otomatis")
        auto_layout = QVBoxLayout(auto_group)
        auto_layout.setSpacing(10)

        info_auto = QLabel(
            "Menempatkan tiang perantara (POLE) di sepanjang kontur jalan raya secara presisi "
            "berdasarkan interval bentangan maksimal (cth: setiap 100 meter bahu jalan)."
        )
        info_auto.setWordWrap(True)
        info_auto.setStyleSheet("color: #64748b; font-size: 11px; line-height: 1.4;")
        auto_layout.addWidget(info_auto)

        # Jarak Maksimal Antar Tiang (Span Limit)
        span_ctrl_layout = QHBoxLayout()
        lbl_max_span = QLabel("Jarak Rentang Antar Tiang:")
        lbl_max_span.setStyleSheet("font-weight: 600; color: #334155;")
        self.spin_max_span = QDoubleSpinBox()
        self.spin_max_span.setRange(20.0, 500.0)
        self.spin_max_span.setValue(100.0)  # Default 100 meter
        self.spin_max_span.setSingleStep(10.0)
        self.spin_max_span.setDecimals(0)
        self.spin_max_span.setSuffix(" m")
        self.spin_max_span.setFixedWidth(115)
        self.spin_max_span.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_max_span.valueChanged.connect(self._update_calculation_labels)
        span_ctrl_layout.addWidget(lbl_max_span)
        span_ctrl_layout.addStretch()
        span_ctrl_layout.addWidget(self.spin_max_span)
        auto_layout.addLayout(span_ctrl_layout)

        # Prefix Kode Tiang & Spesifikasi
        pole_cfg_grid = QGridLayout()
        pole_cfg_grid.setHorizontalSpacing(10)
        pole_cfg_grid.setVerticalSpacing(4)

        lbl_p_prefix = QLabel("Prefix Kode Tiang:")
        lbl_p_prefix.setStyleSheet("font-weight: 600; color: #334155;")
        self.input_pole_prefix = QLineEdit()
        self.input_pole_prefix.setText("POLE")
        self.input_pole_prefix.setPlaceholderText("cth: POLE")

        lbl_p_spec = QLabel("Spesifikasi Tiang:")
        lbl_p_spec.setStyleSheet("font-weight: 600; color: #334155;")
        self.combo_pole_spec = QComboBox()
        self.combo_pole_spec.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_pole_spec.setMinimumContentsLength(8)
        self.combo_pole_spec.addItems([
            "Tiang Besi 7M (Bahu Jalan Standar)",
            "Tiang Besi 9M (Crossing Jalan)",
            "Tiang Beton 9M (Heavy Duty)",
            "Tiang Eksisting / Telkom"
        ])

        pole_cfg_grid.addWidget(lbl_p_prefix, 0, 0)
        pole_cfg_grid.addWidget(lbl_p_spec, 0, 1)
        pole_cfg_grid.addWidget(self.input_pole_prefix, 1, 0)
        pole_cfg_grid.addWidget(self.combo_pole_spec, 1, 1)
        pole_cfg_grid.setColumnStretch(0, 2)
        pole_cfg_grid.setColumnStretch(1, 3)
        auto_layout.addLayout(pole_cfg_grid)

        # Kotak Preview Estimasi Generator
        self.preview_auto_box = QFrame()
        self.preview_auto_box.setObjectName("previewAutoBox")
        preview_layout = QVBoxLayout(self.preview_auto_box)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_layout.setSpacing(4)

        self.lbl_preview_generator = QLabel("Pilih Titik Asal dan Titik Tujuan untuk simulasi tiang.")
        self.lbl_preview_generator.setWordWrap(True)
        self.lbl_preview_generator.setStyleSheet("color: #7c3aed; font-size: 11px; font-weight: 600;")
        preview_layout.addWidget(self.lbl_preview_generator)

        auto_layout.addWidget(self.preview_auto_box)

        # Tombol Eksekusi Generator
        self.btn_auto_generate = QPushButton("⚡  Generate Tiang & Jalur Kabel Sepanjang Jalan")
        self.btn_auto_generate.setObjectName("btnGeneratePoles")
        self.btn_auto_generate.setMinimumHeight(38)
        self.btn_auto_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_auto_generate.clicked.connect(self._handle_auto_generate_poles)
        auto_layout.addWidget(self.btn_auto_generate)

        layout.addWidget(auto_group)

        # -------------------------------------------------------------
        # 3. GROUPBOX: Tabel Rute Kabel Tersimpan
        # -------------------------------------------------------------
        table_group = QGroupBox("📋 Daftar Jalur Kabel (Routing)")
        table_layout = QVBoxLayout(table_group)
        table_layout.setSpacing(8)

        # Baris Header Tabel & Opsi Pilih Semua
        top_cable_layout = QHBoxLayout()
        self.lbl_cable_summary = QLabel("Total: 0 Rute | 0.00 m Panjang Riil")
        self.lbl_cable_summary.setStyleSheet("font-weight: bold; color: #0284c7;")

        self.chk_select_all_cables = QCheckBox("Pilih Semua")
        self.chk_select_all_cables.setStyleSheet("color: #64748b; font-size: 11px;")
        self.chk_select_all_cables.stateChanged.connect(self._on_toggle_all_cables)

        top_cable_layout.addWidget(self.lbl_cable_summary)
        top_cable_layout.addStretch()
        top_cable_layout.addWidget(self.chk_select_all_cables)
        table_layout.addLayout(top_cable_layout)

        self.table_cables = QTableWidget(0, 4)
        self.table_cables.setHorizontalHeaderLabels(["✓", "ID", "Rute", "Panjang"])
        self.table_cables.setColumnWidth(0, 32)
        self.table_cables.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table_cables.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_cables.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_cables.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_cables.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_cables.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_cables.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table_cables.setFixedHeight(180)
        table_layout.addWidget(self.table_cables)

        # Tombol Aksi Tabel
        table_btn_layout = QHBoxLayout()
        self.btn_delete_cable = QPushButton("🗑️ Hapus Terpilih")
        self.btn_delete_cable.clicked.connect(self._handle_delete_cable)

        self.btn_clear_cables = QPushButton("🧹 Kosongkan")
        self.btn_clear_cables.clicked.connect(self._handle_clear_cables)

        table_btn_layout.addWidget(self.btn_delete_cable)
        table_btn_layout.addWidget(self.btn_clear_cables)
        table_layout.addLayout(table_btn_layout)

        layout.addWidget(table_group)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    # -------------------------------------------------------------
    # SINKRONISASI DATA DARI MODUL 1
    # -------------------------------------------------------------

    def update_nodes(self, nodes_dict: Dict[str, FTTHNode]):
        """Memperbarui daftar simpul di dropdown saat ada simpul baru dari Modul 1."""
        self.nodes_dict = nodes_dict

        current_src_id = self.combo_source.currentData()
        current_dst_id = self.combo_dest.currentData()

        self.combo_source.blockSignals(True)
        self.combo_dest.blockSignals(True)

        self.combo_source.clear()
        self.combo_dest.clear()

        self.combo_source.addItem("-- Pilih Titik Asal --", None)
        self.combo_dest.addItem("-- Pilih Titik Tujuan --", None)

        for node_id, node in nodes_dict.items():
            label = f"{node.id} ({node.name})"
            self.combo_source.addItem(label, node_id)
            self.combo_dest.addItem(label, node_id)

        if current_src_id:
            idx = self.combo_source.findData(current_src_id)
            if idx != -1:
                self.combo_source.setCurrentIndex(idx)

        if current_dst_id:
            idx = self.combo_dest.findData(current_dst_id)
            if idx != -1:
                self.combo_dest.setCurrentIndex(idx)

        self.combo_source.blockSignals(False)
        self.combo_dest.blockSignals(False)

        self._recalculate_distance()

    def _on_cable_type_changed(self):
        cable_type: CableType = self.combo_cable_type.currentData()
        self._update_core_presets(cable_type)

    def _update_core_presets(self, cable_type: CableType):
        self.combo_core.clear()
        if cable_type == CableType.FEEDER:
            self.combo_core.addItems(["96 Core", "144 Core", "288 Core", "48 Core"])
        elif cable_type == CableType.DISTRIBUTION:
            self.combo_core.addItems(["24 Core", "48 Core", "12 Core", "72 Core"])
        elif cable_type == CableType.DROP:
            self.combo_core.addItems(["1 Core Drop Cable", "2 Core Drop Cable"])
        else:
            self.combo_core.addItems(["24 Core", "Kustom"])

    # -------------------------------------------------------------
    # KALKULASI JALUR KABEL (ROAD-SNAPPED vs STRAIGHT LINE)
    # -------------------------------------------------------------

    def _recalculate_distance(self):
        """Memicu pengambilan rute jalan atau garis lurus saat pilihan berubah."""
        src_id = self.combo_source.currentData()
        dst_id = self.combo_dest.currentData()

        if not src_id or not dst_id or src_id == dst_id:
            self.current_route_path = []
            self.current_route_distance = 0.0
            if hasattr(self, 'lbl_span_title'):
                self.lbl_span_title.setText("Jarak Bentangan:")
            self.lbl_span_distance.setText("0.00 m")
            if hasattr(self, 'lbl_slack_title'):
                self.lbl_slack_title.setText(f"Cadangan Slack (+{self.spin_slack.value():.0f}%):")
            self.lbl_slack_meter.setText("0.00 m")
            self.lbl_total_cable.setText("0.00 m")
            self.lbl_preview_generator.setText("Pilih Titik Asal dan Titik Tujuan untuk simulasi rute.")
            return

        src_node = self.nodes_dict.get(src_id)
        dst_node = self.nodes_dict.get(dst_id)

        if not src_node or not dst_node:
            return

        pt_a = (src_node.latitude, src_node.longitude)
        pt_b = (dst_node.latitude, dst_node.longitude)

        mode = self.combo_routing_mode.currentData()

        if mode == "straight":
            # Mode Garis Lurus Tradisional
            dist = calculate_geodesic_distance(pt_a, pt_b)
            self.current_route_distance = dist
            self.current_route_path = [pt_a, pt_b]
            self._update_calculation_labels()
        else:
            # Mode Ikuti Jalur Jalan Raya (OSRM Road-Snapped)
            if hasattr(self, 'lbl_span_title'):
                self.lbl_span_title.setText("Jarak Bentangan:")
            self.lbl_span_distance.setText("⏳ Mengambil rute OSRM...")
            self.lbl_preview_generator.setText("⏳ Sedang mengambil kontur rute jalan raya dari OpenStreetMap...")

            if self.route_worker and self.route_worker.isRunning():
                self.route_worker.terminate()

            self.route_worker = RoadRouteWorker(pt_a, pt_b, self)
            self.route_worker.routeCalculated.connect(self._on_road_route_calculated)
            self.route_worker.routeFailed.connect(self._on_road_route_failed)
            self.route_worker.start()

    def _on_road_route_calculated(self, distance_m: float, path_coords: list):
        """Dipanggil saat rute kontur jalan OSRM berhasil diperoleh."""
        self.current_route_distance = distance_m
        self.current_route_path = path_coords
        self._update_calculation_labels()

    def _on_road_route_failed(self, error_msg: str):
        """Fallback ke garis lurus jika rute jalan gagal diambil."""
        src_id = self.combo_source.currentData()
        dst_id = self.combo_dest.currentData()
        src_node = self.nodes_dict.get(src_id)
        dst_node = self.nodes_dict.get(dst_id)
        if src_node and dst_node:
            pt_a = (src_node.latitude, src_node.longitude)
            pt_b = (dst_node.latitude, dst_node.longitude)
            dist = calculate_geodesic_distance(pt_a, pt_b)
            self.current_route_distance = dist
            self.current_route_path = [pt_a, pt_b]
            self._update_calculation_labels()

    def _update_calculation_labels(self):
        """Memperbarui teks metrik jarak dan estimasi generator tiang otomatis."""
        if not self.current_route_path or self.current_route_distance <= 0:
            return

        span_m = self.current_route_distance
        slack_pct = self.spin_slack.value()
        slack_m = span_m * (slack_pct / 100.0)
        total_m = calculate_cable_length_with_slack(span_m, slack_pct)

        mode = self.combo_routing_mode.currentData()
        mode_label = "Jalan Raya" if mode == "road" else "Garis Lurus"

        if hasattr(self, 'lbl_span_title'):
            self.lbl_span_title.setText(f"Jarak Bentang ({mode_label}):")
        self.lbl_span_distance.setText(f"{span_m:.2f} m")

        if hasattr(self, 'lbl_slack_title'):
            self.lbl_slack_title.setText(f"Cadangan Slack (+{slack_pct:.0f}%):")
        self.lbl_slack_meter.setText(f"{slack_m:.2f} m")

        self.lbl_total_cable.setText(f"{total_m:.2f} m")


        # Update Simulasi Generator Tiang Otomatis
        max_span = self.spin_max_span.value()
        num_spans, span_len = calculate_pole_distribution(span_m, max_span)
        num_poles = num_spans - 1

        if num_poles > 0:
            prefix = self.input_pole_prefix.text().strip() or "POLE"
            start_num = self.pole_counter
            end_num = self.pole_counter + num_poles - 1
            road_note = "mengikuti kontur kelokan jalan" if mode == "road" else "garis lurus"
            preview_text = (
                f"<b>Estimasi Rute ({mode_label}):</b> Jarak Total <b>{span_m:.1f} m</b><br>"
                f"• Dibagi menjadi <b>{num_spans} rentang kabel</b> (rata-rata <b>{span_len:.1f} m</b>/span) {road_note}<br>"
                f"• Akan membuat <b>{num_poles} Tiang Baru</b> ({prefix}-{start_num:02d} s/d {prefix}-{end_num:02d}) di bahu jalan<br>"
                f"• Total kabel riil (+{slack_pct:.0f}% slack): <b>{total_m:.1f} meter</b>"
            )
        else:
            preview_text = (
                f"Jarak total ({span_m:.1f} m) lebih pendek dari rentang batas ({max_span:.1f} m).<br>"
                f"Tidak diperlukan tiang perantara tambahan (hanya 1 bentangan langsung)."
            )

        self.lbl_preview_generator.setText(preview_text)

    # -------------------------------------------------------------
    # AKSI 1: SIMPAN SATU RUTE KABEL MENGIKUTI JALAN
    # -------------------------------------------------------------

    def _handle_save_direct_cable(self):
        src_id = self.combo_source.currentData()
        dst_id = self.combo_dest.currentData()

        if not src_id or not dst_id or src_id == dst_id:
            QMessageBox.warning(self, "Peringatan", "Pilih Titik Asal dan Titik Tujuan yang berbeda.")
            return

        src_node = self.nodes_dict.get(src_id)
        dst_node = self.nodes_dict.get(dst_id)

        if not self.current_route_path:
            self._recalculate_distance()

        span_m = self.current_route_distance
        slack_pct = self.spin_slack.value()
        total_m = calculate_cable_length_with_slack(span_m, slack_pct)

        cable_type: CableType = self.combo_cable_type.currentData()
        core_count = self.combo_core.currentText()
        mode = self.combo_routing_mode.currentData()

        cable_id = f"{cable_type.short_code}-{self.cable_counter:03d}"
        cable_name = f"{src_node.id} ➔ {dst_node.id}"
        notes = "Rute jalan raya (OSRM)" if mode == "road" else "Rute garis lurus"

        cable = CableSegment(
            id=cable_id,
            name=cable_name,
            cable_type=cable_type,
            source_node_id=src_node.id,
            source_node_name=src_node.name,
            source_lat=src_node.latitude,
            source_lng=src_node.longitude,
            target_node_id=dst_node.id,
            target_node_name=dst_node.name,
            target_lat=dst_node.latitude,
            target_lng=dst_node.longitude,
            span_distance_m=span_m,
            slack_percent=slack_pct,
            total_length_m=total_m,
            core_count=core_count,
            path_coordinates=list(self.current_route_path),
            notes=notes
        )

        self.cables_dict[cable.id] = cable
        self.cable_counter += 1

        self._refresh_cable_table()
        self.cableAdded.emit(cable)

    # -------------------------------------------------------------
    # AKSI 2: AUTOMATIC ROUTE SPACING & POLE GENERATOR (ROAD-SNAPPED)
    # -------------------------------------------------------------

    def _handle_auto_generate_poles(self):
        """
        Mengeksekusi penempatan tiang otomatis di sepanjang jalur jalan raya (Road-Snapped)
        dan menghubungkan segmen kabel yang melengkung rapi mengikuti jalan.
        """
        src_id = self.combo_source.currentData()
        dst_id = self.combo_dest.currentData()

        if not src_id or not dst_id or src_id == dst_id:
            QMessageBox.warning(self, "Peringatan", "Silakan pilih Titik Asal dan Titik Tujuan yang berbeda.")
            return

        src_node = self.nodes_dict.get(src_id)
        dst_node = self.nodes_dict.get(dst_id)

        if not self.current_route_path or self.current_route_distance <= 0:
            QMessageBox.warning(self, "Peringatan", "Sedang menghitung jalur jalan. Silakan tunggu sebentar.")
            return

        total_distance = self.current_route_distance
        max_span = self.spin_max_span.value()
        num_spans, span_len = calculate_pole_distribution(total_distance, max_span)
        num_intermediate_poles = num_spans - 1

        prefix = self.input_pole_prefix.text().strip() or "POLE"
        pole_spec = self.combo_pole_spec.currentText()
        cable_type: CableType = self.combo_cable_type.currentData()
        core_count = self.combo_core.currentText()
        slack_pct = self.spin_slack.value()
        mode = self.combo_routing_mode.currentData()
        mode_str = "Jalan Raya (OSRM)" if mode == "road" else "Garis Lurus"

        # Konfirmasi ke pengguna
        confirm_msg = (
            f"Sistem akan menempatkan tiang dan jalur kabel:\n\n"
            f"• Mode: {mode_str}\n"
            f"• Titik Asal: {src_node.name} [{src_node.id}]\n"
            f"• Titik Tujuan: {dst_node.name} [{dst_node.id}]\n"
            f"• Jarak Bentangan: {total_distance:.2f} meter\n"
            f"• Batas Maksimal Rentang: {max_span:.1f} meter\n"
            f"• Jumlah Rentang: {num_spans} span (@ {span_len:.2f} m)\n"
            f"• Jumlah Tiang Perantara: {num_intermediate_poles} tiang\n\n"
            f"Lanjutkan pembuatan tiang dan rute kabel di sepanjang jalan?"
        )
        confirm = QMessageBox.question(
            self,
            "Konfirmasi Generator Tiang",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        # 1. Hitung Posisi Tiang & Potong Polyline Jalan Menjadi Sub-Rute
        if mode == "road" and len(self.current_route_path) > 2:
            pole_coords, sub_polylines = split_road_polyline_into_spans(self.current_route_path, num_spans)
        else:
            # Fallback jika mode garis lurus
            pt_a = (src_node.latitude, src_node.longitude)
            pt_b = (dst_node.latitude, dst_node.longitude)
            pole_coords = [
                interpolate_geodesic_point(pt_a, pt_b, i / float(num_spans))
                for i in range(1, num_spans)
            ]
            all_pts = [pt_a] + pole_coords + [pt_b]
            sub_polylines = [
                [all_pts[k], all_pts[k+1]] for k in range(num_spans)
            ]

        # 2. Buat Objek FTTHNode untuk Setiap Tiang Perantara Baru
        new_poles: List[FTTHNode] = []
        for i, (p_lat, p_lng) in enumerate(pole_coords, start=1):
            pole_id = f"{prefix}-{self.pole_counter:02d}"
            pole_name = f"Tiang {self.pole_counter:02d} ({src_node.id}➔{dst_node.id})"
            self.pole_counter += 1

            distance_along = i * span_len
            pole_node = FTTHNode(
                id=pole_id,
                name=pole_name,
                infra_type=FTTHNodeType.POLE,
                latitude=p_lat,
                longitude=p_lng,
                capacity=pole_spec,
                notes=f"Auto-generated di bahu jalan: {distance_along:.1f}m dari {src_node.id}"
            )
            new_poles.append(pole_node)

        # 3. Buat Rangkaian Seluruh Titik: [Asal, Pole1, Pole2, ..., Tujuan]
        route_chain: List[FTTHNode] = [src_node] + new_poles + [dst_node]

        # 4. Hubungkan Menjadi Segmen Kabel yang Melengkung Mengikuti Jalan
        new_cables: List[CableSegment] = []
        for j in range(len(route_chain) - 1):
            seg_src = route_chain[j]
            seg_dst = route_chain[j + 1]
            seg_path = sub_polylines[j] if j < len(sub_polylines) else [
                (seg_src.latitude, seg_src.longitude),
                (seg_dst.latitude, seg_dst.longitude)
            ]

            # Hitung jarak bentangan jalan riil untuk segmen ini
            seg_span_m = 0.0
            for v in range(len(seg_path) - 1):
                seg_span_m += calculate_geodesic_distance(seg_path[v], seg_path[v + 1])

            seg_total_m = calculate_cable_length_with_slack(seg_span_m, slack_pct)

            cbl_id = f"{cable_type.short_code}-{self.cable_counter:03d}"
            self.cable_counter += 1

            cable = CableSegment(
                id=cbl_id,
                name=f"{seg_src.id} ➔ {seg_dst.id}",
                cable_type=cable_type,
                source_node_id=seg_src.id,
                source_node_name=seg_src.name,
                source_lat=seg_src.latitude,
                source_lng=seg_src.longitude,
                target_node_id=seg_dst.id,
                target_node_name=seg_dst.name,
                target_lat=seg_dst.latitude,
                target_lng=seg_dst.longitude,
                span_distance_m=seg_span_m,
                slack_percent=slack_pct,
                total_length_m=seg_total_m,
                core_count=core_count,
                path_coordinates=seg_path,  # Menyimpan seluruh kontur jalan untuk segmen ini!
                notes=f"Segmen {j+1}/{len(route_chain)-1} kontur jalan ({src_node.id}-{dst_node.id})"
            )
            new_cables.append(cable)
            self.cables_dict[cable.id] = cable

        # 5. Pancarkan Sinyal Batch
        if new_poles:
            self.polesBatchGenerated.emit(new_poles)

        if new_cables:
            self._refresh_cable_table()
            self.cablesBatchGenerated.emit(new_cables)

        total_cable_meters = sum(c.total_length_m for c in new_cables)
        success_msg = (
            f"✅ Sukses men-generate jalur kabel & tiang di sepanjang jalan!\n\n"
            f"• Mode: {mode_str}\n"
            f"• Tiang Perantara Dibuat: {len(new_poles)} titik tiang di bahu jalan\n"
            f"• Segmen Kabel Dihubungkan: {len(new_cables)} segmen melengkung rapi\n"
            f"• Total Panjang Kabel (+{slack_pct:.0f}% slack): {total_cable_meters:.2f} meter\n\n"
            f"Seluruh tiang dan garis kabel jalan telah tampil di peta dan siap diekspor ke Google Earth KML."
        )
        QMessageBox.information(self, "Generator Jalan Berhasil", success_msg)

    # -------------------------------------------------------------
    # OPERASI TABEL KABEL
    # -------------------------------------------------------------

    def _on_toggle_all_cables(self, state):
        """Mencentang atau membatalkan centang pada seluruh rute kabel di tabel."""
        is_checked = (state == Qt.CheckState.Checked.value or state == 2)
        self.table_cables.blockSignals(True)
        for row in range(self.table_cables.rowCount()):
            chk_item = self.table_cables.item(row, 0)
            if chk_item:
                chk_item.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
        self.table_cables.blockSignals(False)

    def _refresh_cable_table(self):
        self.table_cables.blockSignals(True)
        self.table_cables.setRowCount(len(self.cables_dict))

        total_accumulated_length = 0.0

        for row, cable in enumerate(self.cables_dict.values()):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            chk_item.setCheckState(Qt.CheckState.Unchecked)

            id_item = QTableWidgetItem(cable.id)
            route_item = QTableWidgetItem(f"{cable.source_node_id} ➔ {cable.target_node_id}")
            len_item = QTableWidgetItem(f"{cable.total_length_m:.1f} m")

            id_item.setForeground(QColor(cable.cable_type.color_hex))
            font = self.font()
            font.setBold(True)
            id_item.setFont(font)

            self.table_cables.setItem(row, 0, chk_item)
            self.table_cables.setItem(row, 1, id_item)
            self.table_cables.setItem(row, 2, route_item)
            self.table_cables.setItem(row, 3, len_item)

            total_accumulated_length += cable.total_length_m

        self.table_cables.blockSignals(False)
        self.lbl_cable_summary.setText(
            f"Total: {len(self.cables_dict)} Rute | {total_accumulated_length:.1f} m Panjang Riil"
        )
        if hasattr(self, 'chk_select_all_cables'):
            self.chk_select_all_cables.blockSignals(True)
            self.chk_select_all_cables.setChecked(False)
            self.chk_select_all_cables.blockSignals(False)

    def _on_table_selection_changed(self):
        selected_rows = self.table_cables.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            cable_id_item = self.table_cables.item(row, 1)  # Kolom 1 adalah ID
            if cable_id_item:
                cable_id = cable_id_item.text()
                self.cableSelected.emit(cable_id)

    def _handle_delete_cable(self):
        # 1. Kumpulkan seluruh ID rute kabel yang tercentang di kolom 0
        checked_ids = []
        for row in range(self.table_cables.rowCount()):
            chk_item = self.table_cables.item(row, 0)
            id_item = self.table_cables.item(row, 1)
            if chk_item and id_item and chk_item.checkState() == Qt.CheckState.Checked:
                checked_ids.append(id_item.text())

        # 2. Jika tidak ada yang dicentang, cek baris yang sedang aktif disorot
        if not checked_ids:
            selected_rows = self.table_cables.selectionModel().selectedRows()
            if selected_rows:
                row = selected_rows[0].row()
                id_item = self.table_cables.item(row, 1)
                if id_item:
                    checked_ids.append(id_item.text())

        if not checked_ids:
            QMessageBox.information(
                self,
                "Pilih Rute",
                "Silakan centang (☑) rute kabel pada kolom pertama yang ingin Anda hapus."
            )
            return

        confirm_msg = (
            f"Apakah Anda yakin ingin menghapus {len(checked_ids)} rute kabel terpilih?"
            if len(checked_ids) > 1
            else f"Apakah Anda yakin ingin menghapus rute kabel {checked_ids[0]}?"
        )
        confirm = QMessageBox.question(
            self,
            "Konfirmasi Hapus Rute",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            for cable_id in checked_ids:
                if cable_id in self.cables_dict:
                    del self.cables_dict[cable_id]
                    self.cableDeleted.emit(cable_id)
            self._refresh_cable_table()

    def _handle_clear_cables(self):
        if not self.cables_dict:
            return

        confirm = QMessageBox.question(
            self,
            "Konfirmasi",
            "Apakah Anda yakin ingin menghapus semua rute kabel?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            self.cables_dict.clear()
            self._refresh_cable_table()
            self.allCablesCleared.emit()

    def set_cables_data(self, cables: Dict[str, CableSegment]):
        """Memuat kamus rute kabel dari file proyek dan memperbarui antarmuka tabel."""
        self.cables_dict = dict(cables)
        self._refresh_cable_table()

    def clear_all_cables(self):
        """Menghapus seluruh data kabel programmatically tanpa prompt konfirmasi."""
        self.cables_dict.clear()
        self._refresh_cable_table()
