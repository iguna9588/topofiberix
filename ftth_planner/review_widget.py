"""
Modul Review Desain & Quality Control (QC) FTTH Network Planner
Melakukan audit otomatis terhadap integritas data spasial, penghitungan total material kabel,
jumlah infrastruktur (Tiang/ODP/ODC), dan validasi rentang jarak antar tiang (Span Check)
sebelum tahap ekspor ke format Google Earth (KML).
"""

import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .models import CableSegment, FTTHNode, FTTHNodeType


class AuditSeverity(str, Enum):
    """Tingkat urgensi hasil audit quality control."""
    PASS = "PASS"         # Lolos standar teknis
    INFO = "INFO"         # Informasi arsitektur/desain
    WARNING = "WARNING"   # Peringatan (misal tiang terlalu renggang/terlalu rapat)
    CRITICAL = "CRITICAL" # Kritis (data kosong, koordinat cacat, 0 node)


@dataclass
class AuditFinding:
    """Representasi satu item temuan hasil audit."""
    severity: AuditSeverity
    category: str
    target_id: str
    metric_value: str
    description: str
    recommendation: str


@dataclass
class AuditReport:
    """Laporan komprehensif hasil audit QC."""
    total_nodes: int = 0
    total_poles: int = 0
    total_odp: int = 0
    total_odc: int = 0
    total_other_nodes: int = 0
    total_cables: int = 0
    total_span_distance_m: float = 0.0
    total_slack_meter: float = 0.0
    total_real_cable_m: float = 0.0
    span_over_limit_count: int = 0
    span_under_limit_count: int = 0
    findings: List[AuditFinding] = None
    is_export_ready: bool = False
    status_summary: str = ""

    def __post_init__(self):
        if self.findings is None:
            self.findings = []


class FTTHAuditResultDialog(QDialog):
    """
    Dialog Modal Modern untuk menampilkan Laporan Hasil Audit Quality Control
    secara komprehensif dengan status banner, kartu metrik, tabel temuan,
    serta tombol aksi (Salin Laporan, Ekspor KML, Tutup).
    """
    def __init__(
        self,
        parent=None,
        report: Optional[AuditReport] = None,
        min_span: float = 25.0,
        max_span: float = 120.0,
        text_summary: str = "",
        on_export_callback=None
    ):
        super().__init__(parent)
        self.report = report or AuditReport()
        self.min_span = min_span
        self.max_span = max_span
        self.text_summary = text_summary
        self.on_export_callback = on_export_callback

        self.setWindowTitle("📋 Laporan Hasil Audit Quality Control Desain FTTH")
        self.resize(720, 560)
        self.setMinimumSize(620, 480)

        # Pasang icon aplikasi pada jendela dialog
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        ico_path = os.path.join(assets_dir, "topofiberix.ico")
        png_path = os.path.join(assets_dir, "topofiberix.png")
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))
        elif os.path.exists(png_path):
            self.setWindowIcon(QIcon(png_path))

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # 1. Header Banner Kelayakan Desain
        has_critical = any(f.severity == AuditSeverity.CRITICAL for f in self.report.findings)
        has_warnings = any(f.severity == AuditSeverity.WARNING for f in self.report.findings)

        banner = QFrame()
        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(14, 12, 14, 12)
        banner_layout.setSpacing(4)

        if has_critical:
            banner.setStyleSheet("""
                QFrame {
                    background-color: #FEF2F2;
                    border: 1.5px solid #F87171;
                    border-radius: 8px;
                }
            """)
            lbl_title = QLabel("❌ KUALITAS DESAIN DITOLAK (GALAT KRITIS DITEMUKAN)")
            lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #991B1B; background: transparent;")
            lbl_desc = QLabel(self.report.status_summary)
            lbl_desc.setStyleSheet("font-size: 11px; color: #B91C1C; background: transparent;")
        elif has_warnings:
            banner.setStyleSheet("""
                QFrame {
                    background-color: #FFFBEB;
                    border: 1.5px solid #FBBF24;
                    border-radius: 8px;
                }
            """)
            lbl_title = QLabel("⚠️ KUALITAS DESAIN PERLU DITINJAU (CATATAN PERINGATAN)")
            lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #92400E; background: transparent;")
            lbl_desc = QLabel(self.report.status_summary)
            lbl_desc.setStyleSheet("font-size: 11px; color: #B45309; background: transparent;")
        else:
            banner.setStyleSheet("""
                QFrame {
                    background-color: #F0FDF4;
                    border: 1.5px solid #34D399;
                    border-radius: 8px;
                }
            """)
            lbl_title = QLabel("✅ KUALITAS DESAIN TERVERIFIKASI & MEMENUHI STANDAR")
            lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #166534; background: transparent;")
            lbl_desc = QLabel(self.report.status_summary)
            lbl_desc.setStyleSheet("font-size: 11px; color: #15803D; background: transparent;")

        lbl_desc.setWordWrap(True)
        banner_layout.addWidget(lbl_title)
        banner_layout.addWidget(lbl_desc)
        layout.addWidget(banner)

        # 2. Grid Kartu KPI Rekapitulasi Ringkas
        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(10)
        kpi_grid.setVerticalSpacing(8)

        card1 = self._create_mini_kpi("📍 Simpul Infrastruktur", f"{self.report.total_nodes} Titik", f"{self.report.total_odc} ODC | {self.report.total_odp} ODP | {self.report.total_poles} Tiang")
        card2 = self._create_mini_kpi("📏 Total Panjang Kabel", f"{self.report.total_real_cable_m:.1f} m", f"{self.report.total_cables} Rute (Slack: {self.report.total_slack_meter:.1f} m)")
        card3 = self._create_mini_kpi("⚡ Standar Span Tiang", f"{self.min_span:.0f}m - {self.max_span:.0f}m", f"Pelanggaran: {self.report.span_over_limit_count} Segmen")
        card4 = self._create_mini_kpi("📋 Catatan Temuan", f"{len(self.report.findings)} Item", "Rincian tabel tertera di bawah")

        kpi_grid.addWidget(card1, 0, 0)
        kpi_grid.addWidget(card2, 0, 1)
        kpi_grid.addWidget(card3, 0, 2)
        kpi_grid.addWidget(card4, 0, 3)
        layout.addLayout(kpi_grid)

        # 3. Tabel Temuan Rinci
        findings_group = QGroupBox(f"📋 Rincian Temuan & Rekomendasi Audit ({len(self.report.findings)} Item)")
        findings_layout = QVBoxLayout(findings_group)
        findings_layout.setContentsMargins(8, 12, 8, 8)
        findings_layout.setSpacing(6)

        table = QTableWidget(len(self.report.findings), 5)
        table.setHorizontalHeaderLabels(["Status", "Kategori", "Objek / Segmen", "Nilai Jarak", "Deskripsi & Saran Rekomendasi"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)

        for row, f in enumerate(self.report.findings):
            status_item = QTableWidgetItem()
            if f.severity == AuditSeverity.PASS:
                status_item.setText("✅ Lolos")
                status_item.setForeground(QColor("#059669"))
            elif f.severity == AuditSeverity.WARNING:
                status_item.setText("⚠️ Warning")
                status_item.setForeground(QColor("#D97706"))
            elif f.severity == AuditSeverity.CRITICAL:
                status_item.setText("❌ Kritis")
                status_item.setForeground(QColor("#DC2626"))
            else:
                status_item.setText("ℹ️ Info")
                status_item.setForeground(QColor("#0284C7"))

            font_bold = status_item.font()
            font_bold.setBold(True)
            status_item.setFont(font_bold)

            cat_item = QTableWidgetItem(f.category)
            target_item = QTableWidgetItem(f.target_id)
            val_item = QTableWidgetItem(f.metric_value)
            desc_text = f"{f.description}\nSaran: {f.recommendation}" if f.recommendation else f.description
            desc_item = QTableWidgetItem(desc_text)

            for col_idx, itm in enumerate([status_item, cat_item, target_item, val_item, desc_item]):
                itm.setFlags(itm.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, col_idx, itm)

            table.setRowHeight(row, 44)

        findings_layout.addWidget(table)
        layout.addWidget(findings_group, 1)

        # 4. Baris Tombol Aksi Bawah
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_copy = QPushButton("📋  Salin Ringkasan Laporan")
        self.btn_copy.setMinimumHeight(36)
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #1E293B;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                border-color: #94A3B8;
            }
        """)
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_layout.addWidget(self.btn_copy)

        btn_layout.addStretch()

        self.btn_close = QPushButton("Tutup & Kembali")
        self.btn_close.setMinimumHeight(36)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #F8FAFC;
                color: #0F172A;
            }
        """)
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)

        self.btn_export = QPushButton("🚀  Lanjut Ekspor KML")
        self.btn_export.setMinimumHeight(36)
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        if self.report.is_export_ready:
            self.btn_export.setStyleSheet("""
                QPushButton {
                    background-color: #0D6EFD;
                    color: #FFFFFF;
                    border: 1px solid #0B5ED7;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0B5ED7;
                }
            """)
            self.btn_export.clicked.connect(self._trigger_export)
        else:
            self.btn_export.setEnabled(False)
            self.btn_export.setToolTip("Perbaiki galat kritis sebelum melanjutkan ekspor KML.")
            self.btn_export.setStyleSheet("""
                QPushButton {
                    background-color: #F1F5F9;
                    color: #94A3B8;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-weight: bold;
                }
            """)
        btn_layout.addWidget(self.btn_export)

        layout.addLayout(btn_layout)

    def _create_mini_kpi(self, title: str, val: str, sub: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
            }
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(10, 8, 10, 8)
        c_layout.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 10px; font-weight: bold; color: #64748B; background: transparent;")
        lbl_v = QLabel(val)
        lbl_v.setStyleSheet("font-size: 13px; font-weight: bold; color: #0284C7; background: transparent;")
        lbl_s = QLabel(sub)
        lbl_s.setStyleSheet("font-size: 9px; color: #94A3B8; background: transparent;")

        c_layout.addWidget(lbl_t)
        c_layout.addWidget(lbl_v)
        c_layout.addWidget(lbl_s)
        return card

    def _copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.text_summary)
            self.btn_copy.setText("✅  Laporan Berhasil Disalin!")
            self.btn_copy.setStyleSheet("""
                QPushButton {
                    background-color: #DCFCE7;
                    color: #166534;
                    border: 1px solid #86EFAC;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-weight: bold;
                }
            """)

    def _trigger_export(self):
        self.accept()
        if self.on_export_callback:
            self.on_export_callback()


class FTTHReviewWidget(QWidget):
    """
    Widget Panel Review Desain & Quality Control (QC).
    Menyediakan dashboard rekapitulasi, parameter validasi span, tabel temuan,
    serta gerbang verifikasi sebelum ekspor KML.
    """
    # Sinyal saat status validasi berubah (is_valid, pesan_status)
    validationStatusChanged = pyqtSignal(bool, str)
    # Sinyal saat pengguna meminta ekspor langsung dari modul review
    requestExport = pyqtSignal()
    # Sinyal pemilihan objek di peta (id simpul atau id kabel)
    itemSelected = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.nodes: Dict[str, FTTHNode] = {}
        self.cables: Dict[str, CableSegment] = {}
        self.latest_report = AuditReport()

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(8)

        # Scroll Area agar seluruh kartu metrik dan tabel responsif
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        # 1. GROUPBOX: PARAMETER AUDIT & KONTROL
        ctrl_group = QGroupBox("⚙️ Parameter Audit & Quality Control")
        ctrl_layout = QVBoxLayout(ctrl_group)
        ctrl_layout.setSpacing(6)

        param_grid = QGridLayout()
        param_grid.setHorizontalSpacing(10)
        param_grid.setVerticalSpacing(4)

        lbl_max_span = QLabel("Batas Maksimal Rentang Tiang:")
        lbl_max_span.setStyleSheet("font-weight: 600; color: #334155;")
        self.spin_max_span_limit = QDoubleSpinBox()
        self.spin_max_span_limit.setRange(40.0, 300.0)
        self.spin_max_span_limit.setValue(120.0)  # Standar teknis FTTH 120m
        self.spin_max_span_limit.setSingleStep(10.0)
        self.spin_max_span_limit.setDecimals(0)
        self.spin_max_span_limit.setSuffix(" m")
        self.spin_max_span_limit.setFixedWidth(115)
        self.spin_max_span_limit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_max_span_limit.valueChanged.connect(lambda _: self.run_audit(show_dialog=False))

        lbl_min_span = QLabel("Batas Minimal Rentang Tiang:")
        lbl_min_span.setStyleSheet("font-weight: 600; color: #334155;")
        self.spin_min_span_limit = QDoubleSpinBox()
        self.spin_min_span_limit.setRange(5.0, 100.0)
        self.spin_min_span_limit.setValue(25.0)  # Standar efisiensi minimal 25m
        self.spin_min_span_limit.setSingleStep(5.0)
        self.spin_min_span_limit.setDecimals(0)
        self.spin_min_span_limit.setSuffix(" m")
        self.spin_min_span_limit.setFixedWidth(115)
        self.spin_min_span_limit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_min_span_limit.valueChanged.connect(lambda _: self.run_audit(show_dialog=False))

        param_grid.addWidget(lbl_max_span, 0, 0)
        param_grid.addWidget(self.spin_max_span_limit, 0, 1)
        param_grid.addWidget(lbl_min_span, 1, 0)
        param_grid.addWidget(self.spin_min_span_limit, 1, 1)
        ctrl_layout.addLayout(param_grid)

        # Baris Tombol Aksi Audit & Salin
        btn_action_layout = QHBoxLayout()
        btn_action_layout.setSpacing(6)

        self.btn_run_audit = QPushButton("🔄  Jalankan Audit & Pengecekan Desain")
        self.btn_run_audit.setObjectName("btnSearchGeocode")
        self.btn_run_audit.setMinimumHeight(34)
        self.btn_run_audit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run_audit.setToolTip("Jalankan audit menyeluruh dan tampilkan dialog laporan hasil QC")
        self.btn_run_audit.clicked.connect(self.handle_btn_run_audit)
        btn_action_layout.addWidget(self.btn_run_audit, 3)

        self.btn_copy_summary = QPushButton("📋 Salin")
        self.btn_copy_summary.setMinimumHeight(34)
        self.btn_copy_summary.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_summary.setToolTip("Salin teks ringkasan hasil audit langsung ke clipboard")
        self.btn_copy_summary.clicked.connect(self.copy_audit_summary_to_clipboard)
        btn_action_layout.addWidget(self.btn_copy_summary, 1)

        ctrl_layout.addLayout(btn_action_layout)

        layout.addWidget(ctrl_group)

        # 2. STATUS BANNER KELAYAKAN DESAIN (QC Status Banner)
        self.status_banner = QFrame()
        self.status_banner.setObjectName("statusBanner")
        banner_layout = QVBoxLayout(self.status_banner)
        banner_layout.setContentsMargins(12, 10, 12, 10)
        banner_layout.setSpacing(4)

        self.lbl_banner_title = QLabel("STATUS VALIDASI BELUM DIJALANKAN")
        self.lbl_banner_title.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.lbl_banner_desc = QLabel("Klik tombol audit untuk menganalisis data topologi jaringan.")
        self.lbl_banner_desc.setWordWrap(True)
        self.lbl_banner_desc.setStyleSheet("font-size: 11px;")

        banner_layout.addWidget(self.lbl_banner_title)
        banner_layout.addWidget(self.lbl_banner_desc)
        layout.addWidget(self.status_banner)

        # 3. KARTU REKAPITULASI METRIK (Summary KPI Cards)
        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(8)
        kpi_grid.setVerticalSpacing(8)

        # Kartu 1: Total Kabel Riil
        self.card_cable, self.val_cable = self._create_kpi_card(
            "Panjang Kabel Riil", "0.0 m", "Termasuk Cadangan Slack", "#0284c7"
        )
        # Kartu 2: Total Tiang (Poles)
        self.card_poles, self.val_poles = self._create_kpi_card(
            "Total Tiang (Poles)", "0 Unit", "Tiang Perantara & Jalur", "#059669"
        )
        # Kartu 3: Total ODP & ODC
        self.card_odp_odc, self.val_odp_odc = self._create_kpi_card(
            "Distribusi (ODC/ODP)", "0 ODC | 0 ODP", "Simpul Pembagi Optik", "#7c3aed"
        )
        # Kartu 4: Validasi Span
        self.card_span, self.val_span = self._create_kpi_card(
            "Validasi Rentang (Span)", "Belum Ada Data", "Pemeriksaan Jarak Aman", "#d97706"
        )

        kpi_grid.addWidget(self.card_cable, 0, 0)
        kpi_grid.addWidget(self.card_poles, 0, 1)
        kpi_grid.addWidget(self.card_odp_odc, 1, 0)
        kpi_grid.addWidget(self.card_span, 1, 1)
        layout.addLayout(kpi_grid)

        # 4. TABEL REKAPITULASI AUDIT & TEMUAN (Findings Table)
        findings_group = QGroupBox("📋 Hasil Rekapitulasi Audit & Temuan")
        findings_layout = QVBoxLayout(findings_group)
        findings_layout.setSpacing(6)

        self.lbl_findings_count = QLabel("Total: 0 Catatan Audit")
        self.lbl_findings_count.setStyleSheet("font-weight: bold; color: #0284c7; font-size: 11px;")
        findings_layout.addWidget(self.lbl_findings_count)

        self.table_findings = QTableWidget(0, 5)
        self.table_findings.setHorizontalHeaderLabels([
            "Status", "Kategori", "Komponen / Segmen", "Nilai Jarak", "Deskripsi & Rekomendasi"
        ])
        self.table_findings.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_findings.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_findings.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_findings.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_findings.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table_findings.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_findings.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_findings.itemDoubleClicked.connect(self._on_table_item_double_clicked)
        self.table_findings.setFixedHeight(210)
        findings_layout.addWidget(self.table_findings)

        hint_tbl = QLabel("💡 Tips: Klik dua kali pada baris temuan untuk menyorot objek di peta.")
        hint_tbl.setStyleSheet("color: #64748b; font-size: 10px; font-style: italic;")
        findings_layout.addWidget(hint_tbl)

        layout.addWidget(findings_group)

        # 5. GERBANG VALIDASI AKHIR & EKSPOR
        action_box = QFrame()
        action_box.setObjectName("calcBox")
        action_layout = QVBoxLayout(action_box)
        action_layout.setContentsMargins(12, 10, 12, 10)
        action_layout.setSpacing(6)

        lbl_action_title = QLabel("GERBANG KELULUSAN EKSPOR KML")
        lbl_action_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #0284c7; letter-spacing: 0.5px;")
        action_layout.addWidget(lbl_action_title)

        self.lbl_export_status = QLabel(
            "Ekspor KML memerlukan validasi data lengkap bebas dari galat kritis (seperti data kosong)."
        )
        self.lbl_export_status.setWordWrap(True)
        self.lbl_export_status.setStyleSheet("color: #475569; font-size: 11px;")
        action_layout.addWidget(self.lbl_export_status)

        self.btn_validate_and_export = QPushButton("🚀  Verifikasi Desain & Lanjut Ekspor KML")
        self.btn_validate_and_export.setObjectName("btnSaveNode")
        self.btn_validate_and_export.setMinimumHeight(38)
        self.btn_validate_and_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_validate_and_export.clicked.connect(self._handle_validate_and_export)
        action_layout.addWidget(self.btn_validate_and_export)

        layout.addWidget(action_box)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Terapkan gaya awal banner
        self._update_banner_style(AuditSeverity.INFO, "SIAP AUDIT", "Silakan klik tombol audit untuk menganalisis perencanaan.")

    def _create_kpi_card(self, title: str, initial_val: str, subtitle: str, color_hex: str):
        """Membuat widget kartu metrik ringkasan (KPI Card)."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 6px;
            }}
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(8, 8, 8, 8)
        c_layout.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 10px; font-weight: 600; color: #64748B; text-transform: uppercase;")
        
        lbl_v = QLabel(initial_val)
        lbl_v.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color_hex};")
        
        lbl_s = QLabel(subtitle)
        lbl_s.setStyleSheet("font-size: 10px; color: #94A3B8;")

        c_layout.addWidget(lbl_t)
        c_layout.addWidget(lbl_v)
        c_layout.addWidget(lbl_s)
        return card, lbl_v

    def refresh_from_parent(self):
        """Mengambil data simpul dan jalur kabel terkini dari widget induk (FTTHSidebarWidget) jika tersedia."""
        curr = self.parent()
        while curr:
            if hasattr(curr, 'nodes') and hasattr(curr, 'routing_widget'):
                self.nodes = curr.nodes
                if hasattr(curr.routing_widget, 'cables_dict'):
                    self.cables = curr.routing_widget.cables_dict
                return
            curr = curr.parent()

    def handle_btn_run_audit(self):
        """Menjalankan audit dengan sinkronisasi data terkini dan menampilkan dialog hasil audit."""
        self.refresh_from_parent()
        self.run_audit(show_dialog=True)

    def copy_audit_summary_to_clipboard(self):
        """Menyalin ringkasan teks hasil audit ke clipboard sistem."""
        self.refresh_from_parent()
        self.run_audit(show_dialog=False)
        summary = self.generate_text_summary()
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(summary)
            self.btn_copy_summary.setText("✅ Disalin!")
            self.btn_copy_summary.setStyleSheet("background-color: #DCFCE7; color: #166534; font-weight: bold;")
            QTimer.singleShot(2000, lambda: self.reset_copy_button_text())

    def reset_copy_button_text(self):
        """Mengembalikan teks tombol salin ke semula."""
        self.btn_copy_summary.setText("📋 Salin")
        self.btn_copy_summary.setStyleSheet("")

    def generate_text_summary(self) -> str:
        """Menghasilkan teks laporan ringkas dan terstruktur dari hasil audit Quality Control."""
        r = self.latest_report
        min_span = self.spin_min_span_limit.value()
        max_span = self.spin_max_span_limit.value()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        has_critical = any(f.severity == AuditSeverity.CRITICAL for f in r.findings)
        has_warnings = any(f.severity == AuditSeverity.WARNING for f in r.findings)

        if has_critical:
            status_str = "❌ DITOLAK (TERDAPAT GALAT KRITIS)"
        elif has_warnings:
            status_str = "⚠️ LOLOS BERSYARAT (CATATAN PERINGATAN)"
        else:
            status_str = "✅ MEMENUHI STANDAR TEKNIS FTTH (LOLOS)"

        lines = [
            "=" * 64,
            "📋 LAPORAN AUDIT & QUALITY CONTROL DESAIN JARINGAN FTTH",
            "=" * 64,
            f"Waktu Pengecekan : {now_str}",
            f"Status Kelayakan : {status_str}",
            f"Ringkasan Sistem : {r.status_summary}",
            "",
            "📊 REKAPITULASI INFRASTRUKTUR & MATERIAL:",
            f"• Total Titik Simpul   : {r.total_nodes} titik",
            f"  - ODC (Kabin Optik)  : {r.total_odc} unit",
            f"  - ODP (Kotak Distrib): {r.total_odp} unit",
            f"  - Tiang (Poles)      : {r.total_poles} unit",
            f"  - Simpul Lainnya     : {r.total_other_nodes} unit",
            f"• Total Jalur Kabel    : {r.total_cables} rute penarikan",
            f"• Total Jarak Bentang  : {r.total_span_distance_m:.1f} meter",
            f"• Total Panjang Kabel  : {r.total_real_cable_m:.1f} meter (Termasuk Slack {r.total_slack_meter:.1f} m)",
            f"• Batas Toleransi Span : Min {min_span:.0f} m | Max {max_span:.0f} m",
            f"• Pelanggaran Rentang  : {r.span_over_limit_count} bentangan melebihi batas",
            "",
            f"🔍 RINCIAN TEMUAN & REKOMENDASI AUDIT ({len(r.findings)} item):"
        ]

        if not r.findings:
            lines.append("  (Tidak ditemukan catatan atau pelanggaran teknis pada desain jaringan)")
        else:
            for idx, f in enumerate(r.findings, 1):
                lines.append(f"{idx}. [{f.severity.value}] Kategori: {f.category} | Target: {f.target_id}")
                if f.metric_value:
                    lines.append(f"   Parameter   : {f.metric_value}")
                lines.append(f"   Deskripsi   : {f.description}")
                if f.recommendation:
                    lines.append(f"   Rekomendasi : {f.recommendation}")
                lines.append("")

        lines.extend([
            "=" * 64,
            "Sistem FTTH Network Planner - Quality Control Module",
            "=" * 64
        ])
        return "\n".join(lines)

    def _show_audit_summary_dialog(self, report: AuditReport):
        """Menampilkan dialog ringkasan audit QC komprehensif ke pengguna."""
        summary_text = self.generate_text_summary()
        dlg = FTTHAuditResultDialog(
            parent=self.window(),
            report=report,
            min_span=self.spin_min_span_limit.value(),
            max_span=self.spin_max_span_limit.value(),
            text_summary=summary_text,
            on_export_callback=self._handle_validate_and_export
        )
        dlg.exec()

    def update_data(self, nodes: Dict[str, FTTHNode], cables: Dict[str, CableSegment]):
        """Memperbarui referensi data simpul dan jalur kabel dari aplikasi utama."""
        self.nodes = nodes
        self.cables = cables
        # Otomatis jalankan audit latar belakang tanpa memunculkan popup
        self.run_audit(show_dialog=False)

    def run_audit(self, show_dialog: bool = False, *args, **kwargs):
        """
        Melakukan audit menyeluruh terhadap data jaringan:
        - Integritas data titik (kekosongan koordinat / nama).
        - Rekapitulasi kuantitas tiang, ODP, ODC.
        - Total panjang kabel riil (+ slack).
        - Validasi rentang span antar tiang (Span Check).
        """
        # Selalu pastikan mengambil data paling mutakhir dari parent jika tersedia
        self.refresh_from_parent()

        max_span = self.spin_max_span_limit.value()
        min_span = self.spin_min_span_limit.value()

        report = AuditReport()
        report.total_nodes = len(self.nodes)
        report.total_cables = len(self.cables)

        # 1. Pengecekan Jika Proyek Masih Kosong
        if report.total_nodes == 0:
            report.findings.append(AuditFinding(
                severity=AuditSeverity.CRITICAL,
                category="Integritas Proyek",
                target_id="N/A",
                metric_value="0 Titik",
                description="Belum ada titik simpul infrastruktur yang dibuat pada perencanaan.",
                recommendation="Tambahkan minimal titik ODC, ODP, atau Tiang melalui Tab 1 sebelum ekspor."
            ))
            report.is_export_ready = False
            report.status_summary = "Gagal Validasi: Data simpul jaringan masih kosong."
            self._render_report(report)
            if show_dialog:
                self._show_audit_summary_dialog(report)
            return

        # 2. Rekapitulasi Komponen & Validasi Titik Simpul
        for node_id, node in self.nodes.items():
            if node.infra_type == FTTHNodeType.POLE:
                report.total_poles += 1
            elif node.infra_type == FTTHNodeType.ODP:
                report.total_odp += 1
            elif node.infra_type == FTTHNodeType.ODC:
                report.total_odc += 1
            else:
                report.total_other_nodes += 1

            # Validasi Nama Kosong
            if not node.name.strip():
                report.findings.append(AuditFinding(
                    severity=AuditSeverity.WARNING,
                    category="Atribut Simpul",
                    target_id=node.id,
                    metric_value="Nama Kosong",
                    description=f"Simpul {node.id} belum memiliki label/nama titik yang deskriptif.",
                    recommendation="Isi nama titik agar mudah diidentifikasi di lapangan dan Google Earth."
                ))

            # Validasi Koordinat Tidak Wajar (0, 0)
            if abs(node.latitude) < 0.0001 and abs(node.longitude) < 0.0001:
                report.findings.append(AuditFinding(
                    severity=AuditSeverity.CRITICAL,
                    category="Geospasial",
                    target_id=node.id,
                    metric_value="0.0, 0.0",
                    description=f"Simpul {node.id} memiliki koordinat nol (pulau antah berantah).",
                    recommendation="Pilih lokasi geografis yang benar pada peta."
                ))

        # 3. Rekapitulasi Kabel & Validasi Rentang Span Antar Tiang (Span Check)
        for cable_id, cable in self.cables.items():
            report.total_span_distance_m += cable.span_distance_m
            report.total_real_cable_m += cable.total_length_m
            report.total_slack_meter += (cable.total_length_m - cable.span_distance_m)

            src_node = self.nodes.get(cable.source_node_id)
            tgt_node = self.nodes.get(cable.target_node_id)

            span = cable.span_distance_m

            # Pengecekan Span Kabel Antar Tiang / Simpul
            is_pole_involved = (
                (src_node and src_node.infra_type == FTTHNodeType.POLE) or
                (tgt_node and tgt_node.infra_type == FTTHNodeType.POLE)
            )

            # Jika melibatkan tiang dan melebihi batas maksimal span
            if is_pole_involved and span > max_span:
                report.span_over_limit_count += 1
                severity = AuditSeverity.CRITICAL if span > (max_span * 1.35) else AuditSeverity.WARNING
                report.findings.append(AuditFinding(
                    severity=severity,
                    category="Jarak Tiang (Span)",
                    target_id=f"{cable.source_node_id} ➔ {cable.target_node_id}",
                    metric_value=f"{span:.1f} m (Max: {max_span:.0f} m)",
                    description=(
                        f"Bentangan kabel antara {cable.source_node_id} dan {cable.target_node_id} "
                        f"melebihi batas maksimal {max_span:.0f} meter."
                    ),
                    recommendation=(
                        "Tambahkan tiang perantara (POLE) di sepanjang rute untuk mencegah kabel kendur "
                        "atau putus akibat beban mekanik."
                    )
                ))
            elif is_pole_involved and span < min_span and span > 0:
                report.span_under_limit_count += 1
                report.findings.append(AuditFinding(
                    severity=AuditSeverity.WARNING,
                    category="Jarak Tiang (Span)",
                    target_id=f"{cable.source_node_id} ➔ {cable.target_node_id}",
                    metric_value=f"{span:.1f} m (Min: {min_span:.0f} m)",
                    description=(
                        f"Bentangan kabel antara {cable.source_node_id} dan {cable.target_node_id} "
                        f"terlalu rapat (di bawah {min_span:.0f} meter)."
                    ),
                    recommendation="Evaluasi penempatan tiang untuk efisiensi anggaran pengadaan tiang."
                ))
            elif span <= 0:
                report.findings.append(AuditFinding(
                    severity=AuditSeverity.CRITICAL,
                    category="Integritas Jalur",
                    target_id=cable.id,
                    metric_value="0.0 m",
                    description=f"Jalur kabel {cable.id} memiliki jarak nol atau titik asal-tujuan identik.",
                    recommendation="Hapus atau perbaiki rute kabel ini."
                ))
            else:
                # Segmen memenuhi syarat
                report.findings.append(AuditFinding(
                    severity=AuditSeverity.PASS,
                    category="Jarak Tiang (Span)",
                    target_id=f"{cable.source_node_id} ➔ {cable.target_node_id}",
                    metric_value=f"{span:.1f} m",
                    description=f"Bentangan kabel memenuhi standar teknis toleransi ({min_span:.0f}m - {max_span:.0f}m).",
                    recommendation="Kondisi ideal, siap diimplementasikan."
                ))

        # Pengecekan rasio tiang dan ODP
        if report.total_odp > 0 and report.total_cables == 0:
            report.findings.append(AuditFinding(
                severity=AuditSeverity.WARNING,
                category="Topologi Jaringan",
                target_id=f"{report.total_odp} ODP",
                metric_value="0 Jalur Kabel",
                description="Terdapat titik ODP namun belum ada rute penarikan kabel penghubung sama sekali.",
                recommendation="Hubungkan titik ODP ke ODC melalui Tab 'Jalur Kabel' sebelum ekspor KML final."
            ))

        # Evaluasi Kelulusan Audit
        has_critical = any(f.severity == AuditSeverity.CRITICAL for f in report.findings)
        has_warnings = any(f.severity == AuditSeverity.WARNING for f in report.findings)

        if has_critical:
            report.is_export_ready = False
            report.status_summary = "Audit Gagal: Ditemukan galat kritis yang harus diperbaiki sebelum ekspor."
        elif has_warnings:
            report.is_export_ready = True
            report.status_summary = "Audit Lolos Bersyarat: Desain memiliki beberapa catatan peringatan (warning)."
        else:
            report.is_export_ready = True
            report.status_summary = "Audit Sempurna: Seluruh titik dan bentangan kabel memenuhi standar teknis FTTH."

        self._render_report(report)

        # Tampilkan modal dialog laporan komprehensif jika diminta
        if show_dialog:
            self._show_audit_summary_dialog(report)

    def _render_report(self, report: AuditReport):
        """Memperbarui visualisasi antarmuka berdasarkan hasil audit report."""
        self.latest_report = report

        # 1. Update KPI Cards
        # Total Kabel
        if report.total_real_cable_m >= 1000:
            km_val = report.total_real_cable_m / 1000.0
            self.val_cable.setText(f"{km_val:.2f} km")
        else:
            self.val_cable.setText(f"{report.total_real_cable_m:.1f} m")

        # Total Tiang
        self.val_poles.setText(f"{report.total_poles} Tiang")

        # Total ODP & ODC
        self.val_odp_odc.setText(f"{report.total_odc} ODC | {report.total_odp} ODP")

        # Status Rentang (Span)
        if report.span_over_limit_count > 0:
            self.val_span.setText(f"⚠️ {report.span_over_limit_count} Span Melebihi")
            self.val_span.setStyleSheet("font-size: 14px; font-weight: bold; color: #dc2626;")
        elif report.total_cables == 0:
            self.val_span.setText("0 Jalur Kabel")
            self.val_span.setStyleSheet("font-size: 14px; font-weight: bold; color: #d97706;")
        else:
            self.val_span.setText("✅ Seluruh Span Sesuai")
            self.val_span.setStyleSheet("font-size: 14px; font-weight: bold; color: #059669;")

        # 2. Update Banner Status
        has_critical = any(f.severity == AuditSeverity.CRITICAL for f in report.findings)
        has_warnings = any(f.severity == AuditSeverity.WARNING for f in report.findings)

        if has_critical:
            self._update_banner_style(
                AuditSeverity.CRITICAL,
                "❌ KUALITAS DESAIN DITOLAK (GALAT KRITIS)",
                report.status_summary
            )
            self.btn_validate_and_export.setEnabled(False)
            self.btn_validate_and_export.setText("⛔  Perbaiki Galat Kritis Sebelum Ekspor")
            self.btn_validate_and_export.setStyleSheet("""
                background-color: #F1F5F9;
                color: #94A3B8;
                border: 1px solid #CBD5E1;
                font-weight: bold;
                padding: 9px;
                border-radius: 6px;
            """)
            self.validationStatusChanged.emit(False, report.status_summary)
        elif has_warnings:
            self._update_banner_style(
                AuditSeverity.WARNING,
                "⚠️ PERINGATAN KUALITAS DESAIN (PERLU DITINJAU)",
                report.status_summary
            )
            self.btn_validate_and_export.setEnabled(True)
            self.btn_validate_and_export.setText("🚀  Validasi & Lanjut Ekspor ke Google Earth (.kml)")
            self.btn_validate_and_export.setStyleSheet("")  # Gunakan QSS bawaan #btnSaveNode
            self.validationStatusChanged.emit(True, report.status_summary)
        else:
            self._update_banner_style(
                AuditSeverity.PASS,
                "✅ KUALITAS DESAIN TERVERIFIKASI & MEMENUHI STANDAR",
                report.status_summary
            )
            self.btn_validate_and_export.setEnabled(True)
            self.btn_validate_and_export.setText("🚀  Validasi & Ekspor ke Google Earth (.kml)")
            self.btn_validate_and_export.setStyleSheet("")
            self.validationStatusChanged.emit(True, report.status_summary)

        # 3. Populate Tabel Temuan
        self.table_findings.setRowCount(0)
        self.table_findings.blockSignals(True)
        self.table_findings.setRowCount(len(report.findings))

        for row, finding in enumerate(report.findings):
            # Badge Status
            status_item = QTableWidgetItem()
            if finding.severity == AuditSeverity.PASS:
                status_item.setText("✅ Lolos")
                status_item.setForeground(QColor("#059669"))
            elif finding.severity == AuditSeverity.WARNING:
                status_item.setText("⚠️ Perhatian")
                status_item.setForeground(QColor("#d97706"))
            elif finding.severity == AuditSeverity.CRITICAL:
                status_item.setText("❌ Kritis")
                status_item.setForeground(QColor("#dc2626"))
            else:
                status_item.setText("ℹ️ Info")
                status_item.setForeground(QColor("#0284c7"))

            font_bold = self.font()
            font_bold.setBold(True)
            status_item.setFont(font_bold)

            cat_item = QTableWidgetItem(finding.category)
            target_item = QTableWidgetItem(finding.target_id)
            target_item.setFont(font_bold)
            val_item = QTableWidgetItem(finding.metric_value)
            
            desc_text = f"{finding.description} [Rekomendasi: {finding.recommendation}]"
            desc_item = QTableWidgetItem(desc_text)
            desc_item.setToolTip(desc_text)

            self.table_findings.setItem(row, 0, status_item)
            self.table_findings.setItem(row, 1, cat_item)
            self.table_findings.setItem(row, 2, target_item)
            self.table_findings.setItem(row, 3, val_item)
            self.table_findings.setItem(row, 4, desc_item)

        self.table_findings.blockSignals(False)
        self.lbl_findings_count.setText(f"Total: {len(report.findings)} Item Audit & Evaluasi")

    def _update_banner_style(self, severity: AuditSeverity, title: str, desc: str):
        """Mengubah warna latar belakang dan teks banner status QC."""
        self.lbl_banner_title.setText(title)
        self.lbl_banner_desc.setText(desc)

        if severity == AuditSeverity.PASS:
            self.status_banner.setStyleSheet("""
                QFrame#statusBanner {
                    background-color: #F0FDF4;
                    border: 1.5px solid #86EFAC;
                    border-radius: 8px;
                }
                QFrame#statusBanner QLabel {
                    color: #166534;
                    background: transparent;
                }
            """)
        elif severity == AuditSeverity.WARNING:
            self.status_banner.setStyleSheet("""
                QFrame#statusBanner {
                    background-color: #FFFBEB;
                    border: 1.5px solid #FDE68A;
                    border-radius: 8px;
                }
                QFrame#statusBanner QLabel {
                    color: #92400E;
                    background: transparent;
                }
            """)
        elif severity == AuditSeverity.CRITICAL:
            self.status_banner.setStyleSheet("""
                QFrame#statusBanner {
                    background-color: #FEF2F2;
                    border: 1.5px solid #FECACA;
                    border-radius: 8px;
                }
                QFrame#statusBanner QLabel {
                    color: #991B1B;
                    background: transparent;
                }
            """)
        else:
            self.status_banner.setStyleSheet("""
                QFrame#statusBanner {
                    background-color: #F8FAFC;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                }
                QFrame#statusBanner QLabel {
                    color: #334155;
                    background: transparent;
                }
            """)

    def _on_table_item_double_clicked(self, item: QTableWidgetItem):
        """Memancarkan sinyal pemilihan simpul atau rute kabel ke peta saat baris temuan diklik."""
        row = item.row()
        target_item = self.table_findings.item(row, 2)
        if not target_item:
            return

        target_text = target_item.text()
        if "➔" in target_text:
            parts = [p.strip() for p in target_text.split("➔")]
            if parts:
                self.itemSelected.emit(parts[0])
        elif target_text in self.nodes:
            self.itemSelected.emit(target_text)

    def _handle_validate_and_export(self):
        """Memvalidasi desain akhir dan meminta jendela utama mengekspor KML."""
        self.refresh_from_parent()
        self.run_audit(show_dialog=False)

        if not self.latest_report.is_export_ready:
            crit_findings = [f for f in self.latest_report.findings if f.severity == AuditSeverity.CRITICAL]
            msg_lines = ["⚠️ Desain jaringan belum dapat diekspor karena terdapat kendala kritis:\n"]
            if crit_findings:
                for idx, f in enumerate(crit_findings[:5], 1):
                    msg_lines.append(f"{idx}. [{f.category}] {f.target_id}: {f.description}")
                if len(crit_findings) > 5:
                    msg_lines.append(f"... dan {len(crit_findings) - 5} kendala lainnya.")
            else:
                msg_lines.append(f"• {self.latest_report.status_summary}")
            msg_lines.append("\nHarap perbaiki kendala di atas pada tab 'Titik Simpul' atau 'Jalur Kabel' sebelum melanjutkan ekspor.")

            QMessageBox.warning(
                self,
                "Validasi Ekspor KML Gagal",
                "\n".join(msg_lines)
            )
            return

        # Jika ada temuan warning, konfirmasi ke pengguna
        warn_findings = [f for f in self.latest_report.findings if f.severity == AuditSeverity.WARNING]
        if warn_findings:
            reply = QMessageBox.question(
                self,
                "Konfirmasi Ekspor KML (Catatan Peringatan)",
                f"Hasil audit mendeteksi {len(warn_findings)} catatan peringatan (warning) pada desain jaringan.\n\n"
                f"Status: {self.latest_report.status_summary}\n\n"
                f"Apakah Anda ingin tetap melanjutkan ekspor ke format KML Google Earth Pro?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.requestExport.emit()

