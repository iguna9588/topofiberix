"""
Modul Jendela Utama Aplikasi FTTH Network Planner
Mengintegrasikan komponen Search Bar, Leaflet Interactive Map,
Sidebar Form, Manajemen Simpul Jaringan, serta Status Bar.
"""

import os
from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .geocoding import GeocodingWorker
from .map_widget import LeafletMapWidget
from .importer import DataImportError, FTTHDataImporter
from .models import FTTHNode
from .project_manager import FTTHProjectManager, ProjectIOError
from .sidebar_widget import FTTHSidebarWidget
from .styles import apply_theme
from .web_bridge import MapBridge


class FTTHMainWindow(QMainWindow):
    """
    Jendela Utama Aplikasi FTTH Network Planner (GIS Fiber Optic Planning System).
    """
    def __init__(self):
        super().__init__()
        self.resize(1320, 820)
        self.setMinimumSize(980, 620)

        # Manajemen State Proyek Aktif
        self.current_project_filepath: Optional[str] = None
        self.current_project_name: str = "Proyek_FTTH_Baru"
        self.current_theme: str = "light"
        self._set_app_icon()
        self._update_window_title()

        # Inisialisasi thread worker geocoding
        self.geocoding_worker: Optional[GeocodingWorker] = None

        # Setup antarmuka
        self._init_ui()
        self._setup_connections()

        # Terapkan stylesheet GIS Modern Light Theme
        apply_theme(self, self.current_theme)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 1. LAYOUT UTAMA HORIZONTAL (Membungkus Panel Kiri & Panel Kanan)
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # 2. SPLITTER HORIZONTAL UTAMA (KIRI: Kontrol/Form, KANAN: Peta GIS)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("mainSplitter")

        # A. PANEL KIRI: Form Input, Routing, Tabel Titik/Kabel, & Ekspor KML
        self.sidebar_widget = FTTHSidebarWidget(self)
        self.sidebar_widget.setMinimumWidth(380)
        self.sidebar_widget.setMaximumWidth(580)
        splitter.addWidget(self.sidebar_widget)

        # B. PANEL KANAN: Kontainer Peta Interaktif & Kotak Pencarian
        right_container = QWidget()
        right_container.setMinimumWidth(480)
        right_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # Kotak Pencarian Geocoding di bagian atas area peta
        search_bar = self._create_search_bar()
        right_layout.addWidget(search_bar)

        # Widget Peta Leaflet & Bridge Komunikasi (Memenuhi sisa area kanan secara dinamis)
        self.bridge = MapBridge(self)
        self.map_widget = LeafletMapWidget(self.bridge, self)
        right_layout.addWidget(self.map_widget, 1)

        splitter.addWidget(right_container)

        # Atur proporsi split yang responsif (Kiri: panel tetap/nyaman, Kanan: dinamis berkembang)
        splitter.setStretchFactor(0, 0)  # Kiri: Form/Kontrol terjaga proporsional
        splitter.setStretchFactor(1, 1)  # Kanan: Peta GIS menyerap seluruh ruang sisa
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setSizes([430, 890])

        root_layout.addWidget(splitter)

        # 3. STATUS BAR BAWAH
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.lbl_cursor_coords = QLabel("📍 Kursor: --, --")
        self.lbl_cursor_coords.setStyleSheet("padding: 0 12px; color: #0284c7; font-weight: 600;")
        self.status_bar.addPermanentWidget(self.lbl_cursor_coords)

        self.lbl_status_msg = QLabel("Siap. Klik titik mana saja di peta untuk mengambil koordinat.")
        self.lbl_status_msg.setStyleSheet("color: #475569; padding-left: 6px;")
        self.status_bar.addWidget(self.lbl_status_msg)

        # 4. MENU BAR STANDAR
        self._create_menu_bar()

    def _create_menu_bar(self):
        """Membuat Menu Bar standar aplikasi: File, Edit, Tampilan, Review."""
        menu_bar = self.menuBar()
        menu_bar.clear()

        # ---------------- MENU FILE ----------------
        file_menu = menu_bar.addMenu("📁 File")

        action_new = QAction("📄 Proyek Baru", self)
        action_new.setShortcut(QKeySequence.StandardKey.New)
        action_new.setStatusTip("Buat proyek perencanaan jaringan baru")
        action_new.triggered.connect(self.handle_new_project)
        file_menu.addAction(action_new)

        action_open = QAction("📂 Buka Proyek...", self)
        action_open.setShortcut(QKeySequence.StandardKey.Open)
        action_open.setStatusTip("Buka dan impor file proyek (.ftth atau .json)")
        action_open.triggered.connect(self.handle_open_project)
        file_menu.addAction(action_open)

        action_import = QAction("📥 Import Data (KML, KMZ, CSV, Excel)...", self)
        action_import.setShortcut(QKeySequence("Ctrl+I"))
        action_import.setStatusTip("Impor titik infrastruktur dan jalur kabel dari file KML, KMZ, CSV, atau Excel")
        action_import.triggered.connect(self.handle_import_data)
        file_menu.addAction(action_import)

        file_menu.addSeparator()

        action_save = QAction("💾 Simpan Proyek", self)
        action_save.setShortcut(QKeySequence.StandardKey.Save)
        action_save.setStatusTip("Simpan status proyek saat ini")
        action_save.triggered.connect(self.handle_save_project)
        file_menu.addAction(action_save)

        action_save_as = QAction("💾 Simpan Proyek Sebagai...", self)
        action_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        action_save_as.setStatusTip("Simpan proyek ke lokasi atau nama file baru")
        action_save_as.triggered.connect(self.handle_save_project_as)
        file_menu.addAction(action_save_as)

        file_menu.addSeparator()

        action_export_kml = QAction("🌍 Ekspor Google Earth (KML)...", self)
        action_export_kml.setShortcut(QKeySequence("Ctrl+E"))
        action_export_kml.setStatusTip("Ekspor seluruh simpul dan jalur kabel ke format KML")
        action_export_kml.triggered.connect(self.sidebar_widget._handle_export_kml)
        file_menu.addAction(action_export_kml)

        file_menu.addSeparator()

        action_exit = QAction("🚪 Keluar", self)
        action_exit.setShortcut(QKeySequence("Ctrl+Q"))
        action_exit.setStatusTip("Tutup aplikasi FTTH Network Planner")
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

        # ---------------- MENU EDIT ----------------
        edit_menu = menu_bar.addMenu("✏️ Edit")

        action_clear_nodes = QAction("🗑️ Bersihkan Seluruh Simpul", self)
        action_clear_nodes.setStatusTip("Hapus semua titik simpul yang terdaftar")
        action_clear_nodes.triggered.connect(self.sidebar_widget._handle_clear_all)
        edit_menu.addAction(action_clear_nodes)

        action_clear_cables = QAction("🗑️ Bersihkan Seluruh Jalur Kabel", self)
        action_clear_cables.setStatusTip("Hapus semua rute kabel yang terdaftar")
        action_clear_cables.triggered.connect(self.sidebar_widget.routing_widget._handle_clear_cables)
        edit_menu.addAction(action_clear_cables)

        # ---------------- MENU TAMPILAN ----------------
        view_menu = menu_bar.addMenu("🗺️ Tampilan")

        action_fit_all = QAction("🎯 Fokus Seluruh Jaringan (Fit All)", self)
        action_fit_all.setShortcut(QKeySequence("Ctrl+F"))
        action_fit_all.setStatusTip("Arahkan peta untuk menampilkan seluruh simpul dan kabel")
        action_fit_all.triggered.connect(self.map_widget.fit_all_bounds)
        view_menu.addAction(action_fit_all)

        action_toggle_theme = QAction("🌓 Ganti Tema (Terang / Gelap)", self)
        action_toggle_theme.setShortcut(QKeySequence("Ctrl+T"))
        action_toggle_theme.setStatusTip("Beralih antara tema GIS Modern Light dan Dark")
        action_toggle_theme.triggered.connect(self.handle_toggle_theme)
        view_menu.addAction(action_toggle_theme)

        # ---------------- MENU REVIEW ----------------
        review_menu = menu_bar.addMenu("🔍 Review & QC")

        action_goto_review = QAction("📋 Audit Desain & Quality Control", self)
        action_goto_review.setShortcut(QKeySequence("Ctrl+R"))
        action_goto_review.setStatusTip("Jalankan modul audit Quality Control dan validasi span jarak")
        action_goto_review.triggered.connect(self.handle_trigger_review_audit)
        review_menu.addAction(action_goto_review)

    def _create_search_bar(self) -> QWidget:
        """Membuat panel pencarian wilayah geografis di bagian atas."""
        container = QFrame()
        container.setObjectName("searchContainer")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        lbl_icon = QLabel("🔍")
        lbl_icon.setStyleSheet("font-size: 14px; background: transparent;")
        layout.addWidget(lbl_icon)

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Cari nama kota, kelurahan, jalan, atau landmark (contoh: Kemang, Jakarta Selatan)...")
        self.input_search.returnPressed.connect(self._handle_search)
        layout.addWidget(self.input_search, 1)

        self.btn_search = QPushButton("Cari Wilayah")
        self.btn_search.setObjectName("btnSearchGeocode")
        self.btn_search.clicked.connect(self._handle_search)
        layout.addWidget(self.btn_search)

        # Indikator loading pencarian
        self.progress_search = QProgressBar()
        self.progress_search.setRange(0, 0)
        self.progress_search.setFixedWidth(80)
        self.progress_search.setFixedHeight(16)
        self.progress_search.setVisible(False)
        layout.addWidget(self.progress_search)

        return container

    def _setup_connections(self):
        """Menghubungkan sinyal antar modul."""
        # 1. Event dari Peta Leaflet -> Python Bridge
        self.bridge.mapClicked.connect(self._on_map_clicked)
        self.bridge.mouseMoved.connect(self._on_map_mouse_moved)
        self.bridge.markerClicked.connect(self._on_marker_clicked)

        # 2. Event dari Sidebar Form -> Peta Leaflet (Simpul / Modul 1)
        self.sidebar_widget.nodeAdded.connect(self.map_widget.add_or_update_marker)
        self.sidebar_widget.nodeDeleted.connect(self.map_widget.remove_marker)
        self.sidebar_widget.allNodesCleared.connect(self.map_widget.clear_markers)
        self.sidebar_widget.nodeSelected.connect(self.map_widget.highlight_marker)

        # 3. Event dari Routing Kabel -> Peta Leaflet (Kabel / Modul 2)
        self.sidebar_widget.cableAdded.connect(self.map_widget.add_or_update_cable)
        self.sidebar_widget.cableDeleted.connect(self.map_widget.remove_cable)
        self.sidebar_widget.allCablesCleared.connect(self.map_widget.clear_cables)
        self.sidebar_widget.cableSelected.connect(self.map_widget.highlight_cable)

        # 4. Event Manajemen Proyek dari Tombol Akses Cepat Sidebar
        self.sidebar_widget.newProjectRequested.connect(self.handle_new_project)
        self.sidebar_widget.openProjectRequested.connect(self.handle_open_project)
        self.sidebar_widget.saveProjectRequested.connect(self.handle_save_project)
        self.sidebar_widget.importRequested.connect(self.handle_import_data)

    def _set_app_icon(self):
        """Memasang icon aplikasi FTTH Network pada title bar jendela."""
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        ico_path = os.path.join(assets_dir, "topofiberix.ico")
        png_path = os.path.join(assets_dir, "topofiberix.png")
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))
        elif os.path.exists(png_path):
            self.setWindowIcon(QIcon(png_path))

    def _update_window_title(self):
        """Memperbarui judul jendela utama dengan nama file proyek aktif."""
        title = "TopoFiberix - Network Designer"
        if self.current_project_filepath:
            title += f" - [{self.current_project_name}]"
        self.setWindowTitle(title)

    def handle_toggle_theme(self):
        """Beralih antara tema cerah (Light) dan gelap (Dark)."""
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        apply_theme(self, self.current_theme)
        self.lbl_status_msg.setText(f"Tema tampilan diubah ke: {self.current_theme.upper()}")

    def handle_trigger_review_audit(self):
        """Membuka tab Review Desain, melakukan sinkronisasi data aktif, dan memunculkan dialog hasil audit."""
        # Pindah tab ke Tab Review Desain (index 2)
        self.sidebar_widget.tab_widget.setCurrentIndex(2)
        # Sinkronkan data terkini ke review widget
        self.sidebar_widget._sync_review_data()
        # Jalankan audit dengan dialog modal ringkasan
        self.sidebar_widget.review_widget.run_audit(show_dialog=True)
        # Berikan indikasi pada status bar
        self.lbl_status_msg.setText("📋 Audit Quality Control perencanaan jaringan telah selesai dievaluasi.")

    def handle_new_project(self):
        """Membuat proyek baru setelah konfirmasi jika terdapat data aktif."""
        has_data = bool(self.sidebar_widget.nodes or self.sidebar_widget.routing_widget.cables_dict)
        if has_data:
            confirm = QMessageBox.question(
                self,
                "Buat Proyek Baru",
                "Perubahan yang belum disimpan pada proyek aktif saat ini akan hilang.\n"
                "Apakah Anda yakin ingin membuat proyek baru?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

        # Kosongkan data di sidebar dan peta
        self.sidebar_widget.clear_entire_project()
        self.map_widget.clear_markers()
        self.map_widget.clear_cables()
        self.current_project_filepath = None
        self.current_project_name = "Proyek_FTTH_Baru"
        self._update_window_title()
        self.lbl_status_msg.setText("✨ Proyek baru telah dibuat. Ruang kerja telah dibersihkan.")

    def handle_save_project(self):
        """Menyimpan proyek ke file yang sudah aktif atau panggil Save As jika belum tersimpan."""
        if not self.current_project_filepath:
            self.handle_save_project_as()
        else:
            self._save_to_path(self.current_project_filepath)

    def handle_save_project_as(self):
        """Menyimpan proyek dengan memilih lokasi dan nama file baru."""
        default_filename = self.current_project_name
        if not (default_filename.endswith(".ftth") or default_filename.endswith(".json")):
            default_filename += ".ftth"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Proyek FTTH",
            default_filename,
            "FTTH Project (*.ftth);;JSON Project (*.json);;All Files (*)"
        )

        if not filepath:
            return

        self._save_to_path(filepath)

    def _save_to_path(self, filepath: str):
        """Eksekusi penyimpanan data proyek ke file fisik."""
        try:
            settings = {
                "routing_mode": self.sidebar_widget.routing_widget.combo_routing_mode.currentData(),
                "auto_pole_spacing_m": self.sidebar_widget.routing_widget.spin_spacing.value(),
                "slack_percentage": self.sidebar_widget.routing_widget.spin_slack.value(),
            }

            FTTHProjectManager.save_to_file(
                filepath=filepath,
                project_name=os.path.splitext(os.path.basename(filepath))[0],
                nodes=self.sidebar_widget.nodes,
                cables=self.sidebar_widget.routing_widget.cables_dict,
                settings=settings,
            )

            self.current_project_filepath = filepath
            self.current_project_name = os.path.basename(filepath)
            self._update_window_title()

            total_nodes = len(self.sidebar_widget.nodes)
            total_cables = len(self.sidebar_widget.routing_widget.cables_dict)
            QMessageBox.information(
                self,
                "Proyek Tersimpan",
                f"Proyek FTTH berhasil disimpan!\n\n"
                f"File: {filepath}\n"
                f"Total Simpul: {total_nodes} titik\n"
                f"Total Rute Kabel: {total_cables} rute\n"
            )
            self.lbl_status_msg.setText(f"💾 Proyek berhasil disimpan ke: {filepath}")

        except ProjectIOError as err:
            QMessageBox.critical(self, "Gagal Menyimpan Proyek", f"Kesalahan I/O Proyek:\n{str(err)}")
        except Exception as e:
            QMessageBox.critical(self, "Error Tidak Terduga", f"Gagal menyimpan file proyek:\n{str(e)}")

    def handle_open_project(self):
        """Membuka file proyek (.ftth / .json), memuat data ke tabel dan peta interaktif."""
        has_data = bool(self.sidebar_widget.nodes or self.sidebar_widget.routing_widget.cables_dict)
        if has_data:
            confirm = QMessageBox.question(
                self,
                "Buka Proyek",
                "Membuka file proyek akan menggantikan seluruh data aktif saat ini.\n"
                "Apakah Anda ingin melanjutkan?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Buka File Proyek FTTH",
            "",
            "FTTH Project (*.ftth *.json);;All Files (*)"
        )

        if not filepath:
            return

        try:
            data = FTTHProjectManager.load_from_file(filepath)
            loaded_nodes = data["nodes"]
            loaded_cables = data["cables"]
            loaded_settings = data.get("settings", {})
            project_name = data.get("project_name", os.path.basename(filepath))

            # 1. Bersihkan peta visual
            self.map_widget.clear_markers()
            self.map_widget.clear_cables()

            # 2. Muat data ke dalam struktur sidebar dan tabel
            self.sidebar_widget.load_project_data(loaded_nodes, loaded_cables, loaded_settings)

            # 3. Gambar ulang seluruh titik (markers) di peta Leaflet
            for node in loaded_nodes.values():
                self.map_widget.add_or_update_marker(node)

            # 4. Gambar ulang seluruh garis rute kabel (polylines) di peta Leaflet
            for cable in loaded_cables.values():
                self.map_widget.add_or_update_cable(cable)

            # 5. Sesuaikan batas pandang peta (fit bounds) ke seluruh titik dan rute
            self.map_widget.fit_all_bounds()

            # 6. Perbarui state proyek aktif
            self.current_project_filepath = filepath
            self.current_project_name = project_name
            self._update_window_title()

            total_cable_m = sum(c.total_length_m for c in loaded_cables.values())
            QMessageBox.information(
                self,
                "Proyek Berhasil Dimuat",
                f"File proyek berhasil diimpor ke aplikasi!\n\n"
                f"Nama Proyek: {project_name}\n"
                f"File: {filepath}\n"
                f"Total Simpul (Nodes): {len(loaded_nodes)} titik\n"
                f"Total Rute Kabel: {len(loaded_cables)} jalur ({total_cable_m:.1f} m)\n\n"
                f"Peta dan tabel telah diperbarui secara otomatis dan data siap diedit kembali."
            )
            self.lbl_status_msg.setText(
                f"📂 Proyek dimuat: {project_name} ({len(loaded_nodes)} simpul, {len(loaded_cables)} rute)"
            )

        except ProjectIOError as err:
            QMessageBox.critical(self, "Gagal Membuka Proyek", f"Kesalahan Format / Validasi File:\n{str(err)}")
        except Exception as e:
            QMessageBox.critical(self, "Error Tidak Terduga", f"Terjadi kesalahan saat membaca file proyek:\n{str(e)}")

    def handle_import_data(self):
        """
        Membuka dialog pemilihan file Multi-Format (.kml, .kmz, .csv, .xlsx, .xls)
        dan memuat data ke dalam aplikasi (mendukung opsi Merge atau Replace).
        """
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Import Data Jaringan FTTH (KML, KMZ, CSV, Excel)",
            "",
            FTTHDataImporter.FILE_FILTER
        )

        if not filepath:
            return

        try:
            result = FTTHDataImporter.import_file(filepath)

            # Jika sudah ada data aktif di ruang kerja, beri pilihan: GABUNGKAN atau GANTIKAN
            has_existing = bool(self.sidebar_widget.nodes or self.sidebar_widget.routing_widget.cables_dict)
            mode = "replace"

            if has_existing:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Metode Penggabungan Data")
                msg_box.setText(
                    f"File '{os.path.basename(filepath)}' berhasil dianalisis:\n\n"
                    f"• {len(result.nodes)} titik simpul ditemukan\n"
                    f"• {len(result.cables)} jalur kabel ditemukan\n\n"
                    f"Proyek saat ini sudah memiliki {len(self.sidebar_widget.nodes)} titik simpul aktif.\n"
                    f"Bagaimana Anda ingin memproses data impor ini?"
                )
                btn_merge = msg_box.addButton("🔗 Gabungkan (Merge)", QMessageBox.ButtonRole.AcceptRole)
                btn_replace = msg_box.addButton("🔄 Gantikan (Replace)", QMessageBox.ButtonRole.DestructiveRole)
                btn_cancel = msg_box.addButton("Batal", QMessageBox.ButtonRole.RejectRole)
                msg_box.setDefaultButton(btn_merge)
                msg_box.exec()

                clicked = msg_box.clickedButton()
                if clicked == btn_cancel:
                    return
                elif clicked == btn_merge:
                    mode = "merge"
                else:
                    mode = "replace"

            if mode == "replace":
                self.map_widget.clear_markers()
                self.map_widget.clear_cables()
                self.sidebar_widget.clear_entire_project()

                nodes_dict = {n.id: n for n in result.nodes}
                cables_dict = {c.id: c for c in result.cables}
                self.sidebar_widget.load_project_data(nodes_dict, cables_dict)
                self.current_project_filepath = None
                self.current_project_name = os.path.splitext(os.path.basename(filepath))[0]
                self._update_window_title()
            else:
                self.sidebar_widget.merge_imported_data(result.nodes, result.cables)

            # Gambar titik dan kabel ke dalam peta interaktif Leaflet
            for node in result.nodes:
                self.map_widget.add_or_update_marker(node)
            for cable in result.cables:
                self.map_widget.add_or_update_cable(cable)

            # Sesuaikan tingkat zoom peta agar menampilkan seluruh data
            self.map_widget.fit_all_bounds()

            # Susun teks catatan/peringatan jika ada baris data yang dilewati
            warning_text = ""
            if result.warnings:
                sample_warnings = "\n".join(result.warnings[:4])
                if len(result.warnings) > 4:
                    sample_warnings += f"\n...dan {len(result.warnings) - 4} catatan baris lainnya."
                warning_text = f"\n\nCatatan Validasi Baris:\n{sample_warnings}"

            QMessageBox.information(
                self,
                f"Impor {result.file_type} Berhasil",
                f"{result.summary_message}\n\n"
                f"Mode Operasi: {'Penggabungan (Merged ke data saat ini)' if mode == 'merge' else 'Proyek Baru (Replaced)'}"
                f"{warning_text}"
            )

            self.lbl_status_msg.setText(
                f"📥 Berhasil mengimpor {len(result.nodes)} simpul & {len(result.cables)} kabel dari {os.path.basename(filepath)}"
            )

        except DataImportError as die:
            QMessageBox.critical(self, "Gagal Impor Data", f"Kesalahan Validasi File:\n{str(die)}")
        except Exception as e:
            QMessageBox.critical(self, "Error Tidak Terduga", f"Terjadi kesalahan saat mengimpor file:\n{str(e)}")

    # ------------------ Slot Handlers ------------------

    def _on_map_clicked(self, lat: float, lng: float):
        """Dipanggil saat pengguna mengklik titik di peta."""
        self.sidebar_widget.set_coordinates(lat, lng)
        self.lbl_status_msg.setText(f"Titik dipilih: {lat:.6f}, {lng:.6f} (Koordinat disalin ke form input)")

    def _on_map_mouse_moved(self, lat: float, lng: float):
        """Memperbarui informasi koordinat kursor di status bar."""
        self.lbl_cursor_coords.setText(f"📍 Lat: {lat:.6f} | Lng: {lng:.6f}")

    def _on_marker_clicked(self, node_id: str):
        """Dipanggil saat pengguna mengklik marker di peta."""
        # Cari baris yang sesuai di tabel sidebar (Kolom 1 adalah ID)
        for row in range(self.sidebar_widget.table_nodes.rowCount()):
            item = self.sidebar_widget.table_nodes.item(row, 1)
            if item and item.text() == node_id:
                self.sidebar_widget.table_nodes.selectRow(row)
                break
        self.lbl_status_msg.setText(f"Memilih simpul: {node_id}")

    def _handle_search(self):
        """Memicu pencarian lokasi asinkron menggunakan GeocodingWorker."""
        query = self.input_search.text().strip()
        if not query:
            return

        self.btn_search.setEnabled(False)
        self.progress_search.setVisible(True)
        self.lbl_status_msg.setText(f"Mencari wilayah '{query}'...")

        self.geocoding_worker = GeocodingWorker(query)
        self.geocoding_worker.searchCompleted.connect(self._on_search_completed)
        self.geocoding_worker.searchFailed.connect(self._on_search_failed)
        self.geocoding_worker.start()

    def _on_search_completed(self, lat: float, lng: float, address: str):
        """Dipanggil saat geocoding berhasil menemukan koordinat."""
        self.btn_search.setEnabled(True)
        self.progress_search.setVisible(False)
        self.lbl_status_msg.setText(f"Lokasi ditemukan: {address}")

        # Geser peta ke lokasi hasil pencarian
        self.map_widget.fly_to(lat, lng, 16)

        # Isi koordinat awal ke form
        self.sidebar_widget.set_coordinates(lat, lng)

    def _on_search_failed(self, error_message: str):
        """Dipanggil saat geocoding gagal menemukan lokasi."""
        self.btn_search.setEnabled(True)
        self.progress_search.setVisible(False)
        self.lbl_status_msg.setText(f"❌ {error_message}")
