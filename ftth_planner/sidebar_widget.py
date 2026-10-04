"""
Modul Panel Samping (Sidebar) FTTH Network Planner (Modul 1 & Modul 2)
Mengintegrasikan Tab Manajemen Simpul (Node) dan Tab Routing Kabel (Routing),
serta pemicu ekspor gabungan (Titik + Jalur Garis) ke Google Earth KML.
"""

import re
from typing import Dict, List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDoubleValidator, QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .models import CableSegment, FTTHNode, FTTHNodeType, KMLExporter
from .review_widget import FTTHReviewWidget
from .routing_widget import FTTHRoutingWidget


class FTTHSidebarWidget(QWidget):
    """
    Panel sisi samping yang mengorganisasikan modul FTTH dengan sistem Tab:
    - Tab 1: Manajemen Simpul / Titik (Modul 1)
    - Tab 2: Kalkulasi Routing Kabel & Jarak (Modul 2)
    - Footer: Ekspor Terpadu ke Google Earth (KML Placemarks + LineStrings)
    """
    # Sinyal Simpul (Nodes)
    nodeAdded = pyqtSignal(FTTHNode)
    nodeDeleted = pyqtSignal(str)
    allNodesCleared = pyqtSignal()
    nodeSelected = pyqtSignal(str)

    # Sinyal Kabel (Routing - Modul 2)
    cableAdded = pyqtSignal(CableSegment)
    cableDeleted = pyqtSignal(str)
    allCablesCleared = pyqtSignal()
    cableSelected = pyqtSignal(str)

    # Sinyal Proyek
    newProjectRequested = pyqtSignal()
    openProjectRequested = pyqtSignal()
    saveProjectRequested = pyqtSignal()
    importRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes: Dict[str, FTTHNode] = {}
        self.counter = 1

        self.setMinimumWidth(400)
        self.setMaximumWidth(580)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(8)

        # Tab Widget Utama
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)

        # TAB 1: Simpul / Nodes (Modul 1)
        node_tab_widget = self._create_node_tab()
        self.tab_widget.addTab(node_tab_widget, "📌 Titik Simpul")

        # TAB 2: Routing Jalur Kabel (Modul 2)
        self.routing_widget = FTTHRoutingWidget(self)
        self.routing_widget.cableAdded.connect(self.cableAdded)
        self.routing_widget.cableDeleted.connect(self.cableDeleted)
        self.routing_widget.allCablesCleared.connect(self.allCablesCleared)
        self.routing_widget.cableSelected.connect(self.cableSelected)
        self.routing_widget.polesBatchGenerated.connect(self._handle_batch_poles)
        self.routing_widget.cablesBatchGenerated.connect(self._handle_batch_cables)
        self.tab_widget.addTab(self.routing_widget, "🔗 Jalur Kabel")

        # TAB 3: Review Desain & Quality Control (QC)
        self.review_widget = FTTHReviewWidget(self)
        self.review_widget.validationStatusChanged.connect(self._on_validation_status_changed)
        self.review_widget.requestExport.connect(self._handle_export_kml)
        self.review_widget.itemSelected.connect(self.nodeSelected)
        self.tab_widget.addTab(self.review_widget, "🔍 Review Desain")

        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # Sinkronisasi kabel otomatis ke modul review QC
        self.routing_widget.cableAdded.connect(lambda _: self._sync_review_data())
        self.routing_widget.cableDeleted.connect(lambda _: self._sync_review_data())
        self.routing_widget.allCablesCleared.connect(self._sync_review_data)

        main_layout.addWidget(self.tab_widget, 1)

        # FOOTER: Ekspor Terintegrasi ke Google Earth Pro (KML)
        export_box = self._create_export_footer()
        main_layout.addWidget(export_box)

        self._auto_generate_id()

    def _create_node_tab(self) -> QWidget:
        """Membuat konten Tab 1: Form Input Simpul dan Tabel Simpul."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)

        # Form Input Titik FTTH
        form_group = QGroupBox("📌 Form Titik Infrastruktur")
        form_layout = QVBoxLayout(form_group)
        form_layout.setSpacing(8)

        lbl_id = QLabel("Kode / ID Simpul:")
        self.input_id = QLineEdit()
        self.input_id.setPlaceholderText("cth: ODP-KBY-01")
        form_layout.addWidget(lbl_id)
        form_layout.addWidget(self.input_id)

        lbl_name = QLabel("Nama / Label Titik:")
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("cth: ODP Jl. Kemang Timur No. 12")
        form_layout.addWidget(lbl_name)
        form_layout.addWidget(self.input_name)

        lbl_type = QLabel("Jenis Infrastruktur:")
        self.combo_type = QComboBox()
        for node_type in FTTHNodeType:
            self.combo_type.addItem(node_type.value, node_type)
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        form_layout.addWidget(lbl_type)
        form_layout.addWidget(self.combo_type)

        lbl_cap = QLabel("Kapasitas / Spesifikasi:")
        self.combo_capacity = QComboBox()
        self.combo_capacity.setEditable(True)
        self._update_capacity_presets(self.combo_type.currentData())
        form_layout.addWidget(lbl_cap)
        form_layout.addWidget(self.combo_capacity)

        coord_layout = QHBoxLayout()
        coord_layout.setSpacing(6)

        lat_container = QVBoxLayout()
        lbl_lat = QLabel("Latitude:")
        self.input_lat = QLineEdit()
        self.input_lat.setPlaceholderText("-6.208800")
        self.input_lat.setValidator(QDoubleValidator(-90.0, 90.0, 8, self))
        lat_container.addWidget(lbl_lat)
        lat_container.addWidget(self.input_lat)

        lng_container = QVBoxLayout()
        lbl_lng = QLabel("Longitude:")
        self.input_lng = QLineEdit()
        self.input_lng.setPlaceholderText("106.845600")
        self.input_lng.setValidator(QDoubleValidator(-180.0, 180.0, 8, self))
        lng_container.addWidget(lbl_lng)
        lng_container.addWidget(self.input_lng)

        coord_layout.addLayout(lat_container)
        coord_layout.addLayout(lng_container)
        form_layout.addLayout(coord_layout)

        lbl_notes = QLabel("Catatan Teknis:")
        self.input_notes = QLineEdit()
        self.input_notes.setPlaceholderText("Kondisi lapangan, tiang eksisting, dll.")
        form_layout.addWidget(lbl_notes)
        form_layout.addWidget(self.input_notes)

        btn_layout = QHBoxLayout()
        self.btn_save_node = QPushButton("➕ Simpan Titik")
        self.btn_save_node.setObjectName("btnSaveNode")
        self.btn_save_node.clicked.connect(self._handle_save_node)

        self.btn_clear_form = QPushButton("🔄 Reset")
        self.btn_clear_form.clicked.connect(self.clear_form)

        btn_layout.addWidget(self.btn_save_node, 2)
        btn_layout.addWidget(self.btn_clear_form, 1)
        form_layout.addLayout(btn_layout)

        layout.addWidget(form_group)

        # Tabel Daftar Titik
        table_group = QGroupBox("📋 Titik Terencana")
        table_layout = QVBoxLayout(table_group)
        table_layout.setSpacing(8)

        # Baris Header Tabel & Opsi Pilih Semua
        top_table_layout = QHBoxLayout()
        self.lbl_table_summary = QLabel("Total: 0 Titik Terdata")
        self.lbl_table_summary.setStyleSheet("font-weight: bold; color: #0284c7;")

        self.chk_select_all_nodes = QCheckBox("Pilih Semua")
        self.chk_select_all_nodes.setStyleSheet("color: #64748b; font-size: 11px;")
        self.chk_select_all_nodes.stateChanged.connect(self._on_toggle_all_nodes)

        top_table_layout.addWidget(self.lbl_table_summary)
        top_table_layout.addStretch()
        top_table_layout.addWidget(self.chk_select_all_nodes)
        table_layout.addLayout(top_table_layout)

        self.table_nodes = QTableWidget(0, 4)
        self.table_nodes.setHorizontalHeaderLabels(["✓", "ID", "Jenis", "Nama Titik"])
        self.table_nodes.setColumnWidth(0, 32)
        self.table_nodes.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table_nodes.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_nodes.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_nodes.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_nodes.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_nodes.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_nodes.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table_nodes.setFixedHeight(180)
        table_layout.addWidget(self.table_nodes)

        table_btn_layout = QHBoxLayout()
        self.btn_delete_selected = QPushButton("🗑️ Hapus Terpilih")
        self.btn_delete_selected.clicked.connect(self._handle_delete_selected)

        self.btn_clear_all = QPushButton("🧹 Kosongkan")
        self.btn_clear_all.clicked.connect(self._handle_clear_all)

        table_btn_layout.addWidget(self.btn_delete_selected)
        table_btn_layout.addWidget(self.btn_clear_all)
        table_layout.addLayout(table_btn_layout)

        layout.addWidget(table_group)

        scroll.setWidget(container)
        return scroll

    def _create_export_footer(self) -> QWidget:
        """Footer persisten untuk ekspor KML (Titik + Garis Kabel)."""
        container = QFrame()
        container.setObjectName("exportFooter")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        info_lbl = QLabel("Ekspor seluruh simpul & jalur kabel (LineString) ke file format Google Earth Pro.")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        layout.addWidget(info_lbl)

        self.btn_export_kml = QPushButton("💾  Ekspor ke Google Earth (.kml)")
        self.btn_export_kml.setObjectName("btnExportKML")
        self.btn_export_kml.setMinimumHeight(38)
        self.btn_export_kml.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_kml.clicked.connect(self._handle_export_kml)
        layout.addWidget(self.btn_export_kml)

        return container

    def _on_type_changed(self):
        node_type: FTTHNodeType = self.combo_type.currentData()
        self._update_capacity_presets(node_type)
        self._auto_generate_id()

    def _update_capacity_presets(self, node_type: FTTHNodeType):
        self.combo_capacity.clear()
        if node_type == FTTHNodeType.ODP:
            self.combo_capacity.addItems(["8 Port (1:8 Splitter)", "16 Port (1:16 Splitter)", "4 Port (1:4 Splitter)"])
        elif node_type == FTTHNodeType.ODC:
            self.combo_capacity.addItems(["144 Port / Core", "288 Port / Core", "96 Port / Core", "72 Port / Core"])
        elif node_type == FTTHNodeType.POLE:
            self.combo_capacity.addItems(["Tiang 7 Meter (Besi)", "Tiang 9 Meter (Besi)", "Tiang Beton 9M", "Tiang Eksisting / Telkom"])
        elif node_type == FTTHNodeType.CLOSURE:
            self.combo_capacity.addItems(["24 Core", "48 Core", "96 Core", "144 Core"])
        elif node_type == FTTHNodeType.DROP_NODE:
            self.combo_capacity.addItems(["1 Core Drop Wire", "2 Core Drop Wire"])
        elif node_type == FTTHNodeType.ONT:
            self.combo_capacity.addItems(["1 Port GE + WiFi", "4 Port GE + VoIP + WiFi"])
        else:
            self.combo_capacity.addItems(["Standar", "Kustom"])

    def _auto_generate_id(self):
        node_type: FTTHNodeType = self.combo_type.currentData()
        prefix = node_type.short_code if node_type else "NOD"
        self.input_id.setText(f"{prefix}-{self.counter:03d}")

    def set_coordinates(self, lat: float, lng: float):
        # Otomatis alihkan ke Tab 0 (📌 Titik Simpul) agar input field terlihat
        self.tab_widget.setCurrentIndex(0)
        self.input_lat.setText(f"{lat:.7f}")
        self.input_lng.setText(f"{lng:.7f}")

    def clear_form(self):
        self._auto_generate_id()
        self.input_name.clear()
        self.input_lat.clear()
        self.input_lng.clear()
        self.input_notes.clear()
        if hasattr(self, 'btn_save_node'):
            self.btn_save_node.setText("➕ Simpan Titik")

    def _load_node_to_form(self, node_id: str):
        """Memuat atribut simpul yang dipilih ke dalam formulir untuk mode edit."""
        node = self.nodes.get(node_id)
        if not node:
            return
        self.input_id.setText(node.id)
        self.input_name.setText(node.name)
        idx = self.combo_type.findData(node.infra_type)
        if idx >= 0:
            self.combo_type.setCurrentIndex(idx)
        self.combo_capacity.setCurrentText(node.capacity)
        self.input_lat.setText(f"{node.latitude:.6f}")
        self.input_lng.setText(f"{node.longitude:.6f}")
        self.input_notes.setText(node.notes)
        if hasattr(self, 'btn_save_node'):
            self.btn_save_node.setText("💾 Perbarui Titik Simpul")

    def _handle_save_node(self):
        node_id = self.input_id.text().strip()
        name = self.input_name.text().strip()
        lat_str = self.input_lat.text().strip()
        lng_str = self.input_lng.text().strip()

        if not node_id:
            QMessageBox.warning(self, "Peringatan", "Kode / ID Simpul tidak boleh kosong.")
            return

        if not name:
            name = node_id

        if not lat_str or not lng_str:
            QMessageBox.warning(self, "Peringatan", "Silakan klik titik di peta terlebih dahulu untuk mengambil koordinat.")
            return

        try:
            lat = float(lat_str)
            lng = float(lng_str)
        except ValueError:
            QMessageBox.warning(self, "Peringatan", "Format koordinat Latitude/Longitude tidak valid.")
            return

        node_type: FTTHNodeType = self.combo_type.currentData()
        capacity = self.combo_capacity.currentText()
        notes = self.input_notes.text().strip()

        node = FTTHNode(
            id=node_id,
            name=name,
            infra_type=node_type,
            latitude=lat,
            longitude=lng,
            capacity=capacity,
            notes=notes
        )

        is_new = node.id not in self.nodes
        self.nodes[node.id] = node
        if is_new:
            self.counter += 1

        self._refresh_table()
        # Perbarui pilihan simpul di Tab Routing (Modul 2)
        self.routing_widget.update_nodes(self.nodes)

        self.nodeAdded.emit(node)
        self.clear_form()

    def _on_toggle_all_nodes(self, state):
        """Mencentang atau membatalkan centang pada seluruh titik di tabel."""
        is_checked = (state == Qt.CheckState.Checked.value or state == 2)
        self.table_nodes.blockSignals(True)
        for row in range(self.table_nodes.rowCount()):
            chk_item = self.table_nodes.item(row, 0)
            if chk_item:
                chk_item.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
        self.table_nodes.blockSignals(False)

    def _refresh_table(self):
        self.table_nodes.blockSignals(True)
        self.table_nodes.setRowCount(len(self.nodes))

        for row, node in enumerate(self.nodes.values()):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            chk_item.setCheckState(Qt.CheckState.Unchecked)

            id_item = QTableWidgetItem(node.id)
            type_item = QTableWidgetItem(node.infra_type.short_code)
            name_item = QTableWidgetItem(node.name)

            type_item.setForeground(QColor(node.infra_type.color_hex))
            font = self.font()
            font.setBold(True)
            type_item.setFont(font)

            self.table_nodes.setItem(row, 0, chk_item)
            self.table_nodes.setItem(row, 1, id_item)
            self.table_nodes.setItem(row, 2, type_item)
            self.table_nodes.setItem(row, 3, name_item)

        self.table_nodes.blockSignals(False)
        self.lbl_table_summary.setText(f"Total: {len(self.nodes)} Titik Terdata")
        if hasattr(self, 'chk_select_all_nodes'):
            self.chk_select_all_nodes.blockSignals(True)
            self.chk_select_all_nodes.setChecked(False)
            self.chk_select_all_nodes.blockSignals(False)

        self._sync_review_data()

    def _on_table_selection_changed(self):
        selected_rows = self.table_nodes.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            node_id_item = self.table_nodes.item(row, 1)  # Kolom 1 adalah ID
            if node_id_item:
                node_id = node_id_item.text()
                self.nodeSelected.emit(node_id)
                self._load_node_to_form(node_id)

    def _handle_delete_selected(self):
        # 1. Kumpulkan seluruh ID titik yang tercentang pada kolom 0
        checked_ids = []
        for row in range(self.table_nodes.rowCount()):
            chk_item = self.table_nodes.item(row, 0)
            id_item = self.table_nodes.item(row, 1)
            if chk_item and id_item and chk_item.checkState() == Qt.CheckState.Checked:
                checked_ids.append(id_item.text())

        # 2. Jika tidak ada yang dicentang, periksa baris yang sedang aktif disorot
        if not checked_ids:
            selected_rows = self.table_nodes.selectionModel().selectedRows()
            if selected_rows:
                row = selected_rows[0].row()
                id_item = self.table_nodes.item(row, 1)
                if id_item:
                    checked_ids.append(id_item.text())

        if not checked_ids:
            QMessageBox.information(
                self,
                "Pilih Titik",
                "Silakan centang (☑) titik infrastruktur pada kolom pertama yang ingin Anda hapus."
            )
            return

        confirm_msg = (
            f"Apakah Anda yakin ingin menghapus {len(checked_ids)} titik infrastruktur terpilih?"
            if len(checked_ids) > 1
            else f"Apakah Anda yakin ingin menghapus titik {checked_ids[0]}?"
        )
        confirm = QMessageBox.question(
            self,
            "Konfirmasi Hapus Titik",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            for node_id in checked_ids:
                if node_id in self.nodes:
                    del self.nodes[node_id]
                    self.nodeDeleted.emit(node_id)
            self._refresh_table()
            self.routing_widget.update_nodes(self.nodes)

    def _handle_clear_all(self):
        if not self.nodes:
            return

        confirm = QMessageBox.question(
            self,
            "Konfirmasi",
            "Apakah Anda yakin ingin menghapus semua titik survei jaringan?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            self.nodes.clear()
            self._refresh_table()
            self.routing_widget.update_nodes(self.nodes)
            self.allNodesCleared.emit()

    def _handle_batch_poles(self, poles: List[FTTHNode]):
        """Menyimpan seluruh tiang hasil generate otomatis ke daftar simpul dan memicu render peta."""
        for pole in poles:
            self.nodes[pole.id] = pole
            self.nodeAdded.emit(pole)
        self._refresh_table()
        self.routing_widget.update_nodes(self.nodes)

    def _handle_batch_cables(self, cables: List[CableSegment]):
        """Memicu render peta untuk seluruh rute kabel hasil generator otomatis."""
        for cable in cables:
            self.cableAdded.emit(cable)
        self._sync_review_data()

    def _sync_review_data(self):
        """Menyinkronkan data simpul dan jalur kabel ke modul review Quality Control."""
        if hasattr(self, 'review_widget'):
            self.review_widget.update_data(self.nodes, self.routing_widget.cables_dict)

    def _on_tab_changed(self, index: int):
        """Menjalankan audit saat tab Review Desain dibuka."""
        if index == 2:  # Tab Review Desain
            self._sync_review_data()

    def _on_validation_status_changed(self, is_valid: bool, status_msg: str):
        """Memperbarui ketersediaan tombol ekspor KML berdasarkan kelulusan audit QC."""
        if not is_valid:
            self.btn_export_kml.setEnabled(False)
            self.btn_export_kml.setToolTip(f"Ekspor terkunci: {status_msg}")
        else:
            self.btn_export_kml.setEnabled(True)
            self.btn_export_kml.setToolTip("Desain telah divalidasi dan siap diekspor ke KML Google Earth Pro.")

    def _handle_export_kml(self):
        """Mengekspor seluruh simpul dan jalur kabel ke file .kml untuk Google Earth Pro."""
        if not self.nodes:
            QMessageBox.warning(self, "Peringatan", "Belum ada titik infrastruktur yang ditambahkan untuk diekspor.")
            return

        # Pengecekan audit quality control sebelum ekspor
        if hasattr(self, 'review_widget') and not self.review_widget.latest_report.is_export_ready:
            confirm = QMessageBox.question(
                self,
                "Peringatan Quality Control",
                f"Hasil audit mendeteksi catatan kritis pada desain jaringan:\n\n"
                f"'{self.review_widget.latest_report.status_summary}'\n\n"
                f"Sangat disarankan memeriksa tab '🔍 Review Desain' terlebih dahulu.\n"
                f"Apakah Anda tetap ingin melanjutkan ekspor KML?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if confirm != QMessageBox.StandardButton.Yes:
                self.tab_widget.setCurrentIndex(2)  # Beralih ke tab review desain
                return

        cables_list = list(self.routing_widget.cables_dict.values())

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan File KML FTTH (Nodes & Routes)",
            "FTTH_Network_Plan.kml",
            "KML Files (*.kml);;All Files (*)"
        )

        if not filepath:
            return

        try:
            KMLExporter.export(
                nodes=list(self.nodes.values()),
                cables=cables_list,
                output_filepath=filepath,
                document_name="FTTH Complete Network Design"
            )

            total_cable_m = sum(c.total_length_m for c in cables_list)
            msg = (
                f"File KML berhasil diekspor!\n\n"
                f"Lokasi: {filepath}\n"
                f"Total Simpul (Points): {len(self.nodes)} titik\n"
                f"Total Jalur Kabel (LineStrings): {len(cables_list)} rute ({total_cable_m:.2f} m)\n\n"
                f"File dapat langsung dibuka di Google Earth Pro lengkap dengan visualisasi 3D garis dan titik."
            )
            QMessageBox.information(self, "Ekspor KML Berhasil", msg)
        except Exception as e:
            QMessageBox.critical(self, "Gagal Ekspor", f"Terjadi kesalahan saat mengekspor KML:\n{str(e)}")

    def clear_entire_project(self):
        """Mengosongkan seluruh data proyek aktif (simpul, jalur kabel, dan tabel)."""
        self.nodes.clear()
        self.counter = 1
        self.routing_widget.clear_all_cables()
        self.routing_widget.update_nodes(self.nodes)
        self.routing_widget.pole_counter = 1
        self.routing_widget.cable_counter = 1
        self._refresh_table()
        self.clear_form()
        self._sync_review_data()
        self._auto_generate_id()

    def load_project_data(
        self,
        nodes: Dict[str, FTTHNode],
        cables: Dict[str, CableSegment],
        settings: Optional[dict] = None
    ):
        """
        Memuat data proyek hasil parsing file JSON / .ftth ke dalam antarmuka sidebar,
        tabel simpul, tabel kabel, dan sinkronisasi modul review QC.
        """
        self.nodes = dict(nodes)
        self.routing_widget.set_cables_data(cables)
        self.routing_widget.update_nodes(self.nodes)
        self._refresh_table()
        self.clear_form()
        self._sync_review_data()

        # Terapkan konfigurasi proyek jika tersedia
        if settings and isinstance(settings, dict):
            if "auto_pole_spacing_m" in settings and hasattr(self.routing_widget, 'spin_spacing'):
                self.routing_widget.spin_spacing.setValue(float(settings["auto_pole_spacing_m"]))
            if "slack_percentage" in settings and hasattr(self.routing_widget, 'spin_slack'):
                self.routing_widget.spin_slack.setValue(float(settings["slack_percentage"]))
            if "routing_mode" in settings and hasattr(self.routing_widget, 'combo_routing_mode'):
                idx = self.routing_widget.combo_routing_mode.findData(settings["routing_mode"])
                if idx != -1:
                    self.routing_widget.combo_routing_mode.setCurrentIndex(idx)

        self._recalculate_counters()
        self._auto_generate_id()

    def _recalculate_counters(self):
        """Menghitung ulang nomor counter simpul, tiang, dan kabel agar tidak bentrok."""
        max_node_num = 0
        max_pole_num = 0
        for nid in self.nodes.keys():
            nums = re.findall(r'\d+', nid)
            if nums:
                val = int(nums[-1])
                if 'POLE' in nid.upper() or 'TIANG' in nid.upper():
                    if val > max_pole_num:
                        max_pole_num = val
                else:
                    if val > max_node_num:
                        max_node_num = val

        self.counter = max(max_node_num + 1, len(self.nodes) + 1)
        self.routing_widget.pole_counter = max_pole_num + 1 if max_pole_num > 0 else 1

        max_cable_num = 0
        cables_dict = self.routing_widget.cables_dict
        for cid in cables_dict.keys():
            nums = re.findall(r'\d+', cid)
            if nums:
                val = int(nums[-1])
                if val > max_cable_num:
                    max_cable_num = val

        self.routing_widget.cable_counter = max(max_cable_num + 1, len(cables_dict) + 1)

    def merge_imported_data(self, new_nodes: List[FTTHNode], new_cables: List[CableSegment]):
        """
        Menggabungkan data hasil impor ke dalam status proyek aktif saat ini.
        Menghindari duplikasi ID dengan menambahkan indeks pembeda jika diperlukan.
        """
        for node in new_nodes:
            original_id = node.id
            final_id = original_id
            suffix = 1
            while final_id in self.nodes:
                final_id = f"{original_id}_{suffix}"
                suffix += 1
            node.id = final_id
            self.nodes[node.id] = node

        for cable in new_cables:
            original_cid = cable.id
            final_cid = original_cid
            suffix = 1
            while final_cid in self.routing_widget.cables_dict:
                final_cid = f"{original_cid}_{suffix}"
                suffix += 1
            cable.id = final_cid
            self.routing_widget.cables_dict[cable.id] = cable

        self._refresh_table()
        self.routing_widget._refresh_cable_table()
        self.routing_widget.update_nodes(self.nodes)
        self._sync_review_data()
        self._recalculate_counters()
        self._auto_generate_id()
