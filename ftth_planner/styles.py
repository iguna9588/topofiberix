"""
Tema Styling QSS (Qt Style Sheets) untuk Aplikasi FTTH Network Planner
Menyediakan tema cerah modern (Modern Light Theme) serta tema gelap (Dark Theme)
dengan prinsip UI/UX profesional, elegan, dan tata letak responsif.
"""

import os
from PyQt6.QtWidgets import QApplication, QWidget

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
_ASSETS_DIR = f"{_CURRENT_DIR}/assets"
_SPIN_UP_LIGHT = f"{_ASSETS_DIR}/spin_up.svg"
_SPIN_DOWN_LIGHT = f"{_ASSETS_DIR}/spin_down.svg"
_SPIN_UP_DARK = f"{_ASSETS_DIR}/spin_up_dark.svg"
_SPIN_DOWN_DARK = f"{_ASSETS_DIR}/spin_down_dark.svg"
_COMBO_DOWN_LIGHT = f"{_ASSETS_DIR}/combo_down.svg"
_COMBO_DOWN_DARK = f"{_ASSETS_DIR}/combo_down_dark.svg"


# ==============================================================================
# 1. TEMA TERANG MODERN & ELEGAN (MODERN LIGHT THEME - DEFAULT)
# ==============================================================================
LIGHT_GIS_THEME = """
/* Reset & Global */
QWidget {
    background-color: #F8FAFC;
    color: #1E293B;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Roboto", "Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
}

/* Jendela Utama & Kontainer */
QMainWindow {
    background-color: #F1F5F9;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* Splitter Antara Panel Form & Peta */
QSplitter::handle {
    background-color: #E2E8F0;
    width: 5px;
    height: 5px;
}

QSplitter::handle:hover {
    background-color: #0EA5E9;
}

/* GroupBox (Card Container) */
QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    margin-top: 20px;
    padding: 12px 10px 10px 10px;
    font-weight: 700;
    font-size: 12px;
    color: #0F172A;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 3px 10px;
    left: 12px;
    top: 4px;
    background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    color: #0369A1;
    font-weight: 700;
    font-size: 11px;
}

/* Labels */
QLabel {
    color: #475569;
    font-size: 12px;
    background: transparent;
}

/* Kotak Input, ComboBox, & SpinBox */
QLineEdit, QComboBox, QTextEdit, QDoubleSpinBox, QSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0F172A;
    selection-background-color: #0EA5E9;
    selection-color: #FFFFFF;
    min-height: 22px;
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
    border: 1.5px solid #0EA5E9;
    background-color: #FFFFFF;
}

QLineEdit[readOnly="true"] {
    background-color: #F1F5F9;
    color: #64748B;
    border-color: #E2E8F0;
}

QDoubleSpinBox, QSpinBox {
    padding-left: 8px;
    padding-right: 24px;
    padding-top: 4px;
    padding-bottom: 4px;
}

QDoubleSpinBox::up-button, QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid #CBD5E1;
    border-bottom: 1px solid #E2E8F0;
    border-top-right-radius: 5px;
    background-color: #F8FAFC;
    margin: 1px 1px 0px 0px;
}

QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover {
    background-color: #E2E8F0;
}

QDoubleSpinBox::up-arrow, QSpinBox::up-arrow {
    image: url("__SPIN_UP_LIGHT__");
    width: 7px;
    height: 4px;
}

QDoubleSpinBox::down-button, QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    border-left: 1px solid #CBD5E1;
    border-bottom-right-radius: 5px;
    background-color: #F8FAFC;
    margin: 0px 1px 1px 0px;
}

QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {
    background-color: #E2E8F0;
}

QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {
    image: url("__SPIN_DOWN_LIGHT__");
    width: 7px;
    height: 4px;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #E2E8F0;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox::down-arrow {
    image: url("__COMBO_DOWN_LIGHT__");
    width: 8px;
    height: 5px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    selection-background-color: #E0F2FE;
    selection-color: #0369A1;
    padding: 4px;
    outline: none;
}

/* CheckBox */
QCheckBox {
    color: #475569;
    font-size: 12px;
    spacing: 6px;
    background: transparent;
}

QCheckBox:hover {
    color: #0F172A;
}

/* Tab Widget & Tab Bar */
QTabWidget::pane {
    border: 1px solid #E2E8F0;
    background-color: #FFFFFF;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background-color: #F1F5F9;
    color: #64748B;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
    font-weight: 600;
    font-size: 12px;
    border: 1px solid #E2E8F0;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #0284C7;
    border-top: 2px solid #0EA5E9;
    border-left: 1px solid #E2E8F0;
    border-right: 1px solid #E2E8F0;
    border-bottom: 1px solid #FFFFFF;
}

QTabBar::tab:hover:!selected {
    background-color: #E2E8F0;
    color: #0F172A;
}

/* Tombol Default */
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    color: #334155;
}

QPushButton:hover {
    background-color: #F8FAFC;
    border-color: #0EA5E9;
    color: #0284C7;
}

QPushButton:pressed {
    background-color: #E2E8F0;
}

QPushButton:disabled {
    background-color: #F1F5F9;
    border-color: #E2E8F0;
    color: #94A3B8;
}

/* Tombol Aksi Spesifik (Gradien Modern) */
#btnSaveNode {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0D6EFD, stop:1 #0EA5E9);
    border: none;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 13px;
    padding: 9px 16px;
    border-radius: 6px;
}

#btnSaveNode:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0B5ED7, stop:1 #0284C7);
}

#btnSaveNode:pressed {
    background-color: #094CB2;
}

#btnExportKML {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F59E0B, stop:1 #D97706);
    border: none;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 13px;
    padding: 9px 16px;
    border-radius: 6px;
}

#btnExportKML:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #D97706, stop:1 #B45309);
}

#btnExportKML:pressed {
    background-color: #92400E;
}

#btnSearchGeocode {
    background-color: #0D6EFD;
    border: none;
    color: #FFFFFF;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 6px;
}

#btnSearchGeocode:hover {
    background-color: #0B5ED7;
}

#btnSearchGeocode:pressed {
    background-color: #094CB2;
}

#btnGeneratePoles {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #8B5CF6);
    border: none;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 13px;
    padding: 9px 16px;
    border-radius: 6px;
}

#btnGeneratePoles:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED);
}

#btnGeneratePoles:pressed {
    background-color: #4338CA;
}

/* Tabel Data Titik & Jalur Kabel */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    gridline-color: #F1F5F9;
    color: #1E293B;
    selection-background-color: #E0F2FE;
    selection-color: #0369A1;
    alternate-background-color: #F8FAFC;
}

QTableWidget::item {
    padding: 5px;
    border-bottom: 1px solid #F1F5F9;
}

QTableWidget::item:selected {
    background-color: #E0F2FE;
    color: #0284C7;
}

QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    padding: 6px;
    font-weight: 600;
    font-size: 11px;
    border: none;
    border-right: 1px solid #E2E8F0;
    border-bottom: 1px solid #E2E8F0;
}

/* Status Bar Bawah */
QStatusBar {
    background-color: #FFFFFF;
    color: #64748B;
    border-top: 1px solid #E2E8F0;
    font-size: 11px;
}

/* ScrollBars: Modern Slim Light Style */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    min-height: 24px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #CBD5E1;
    min-width: 24px;
    border-radius: 3px;
}

QScrollBar::handle:horizontal:hover {
    background: #94A3B8;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    background: none;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* Komponen Khusus Berbasis ObjectName */
QFrame#searchContainer {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 4px;
}

QFrame#exportFooter {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 8px;
}

QFrame#calcBox {
    background-color: #F8FAFC;
    border: 1px solid #BAE6FD;
    border-radius: 8px;
}

QFrame#previewAutoBox {
    background-color: #FAF5FF;
    border: 1px dashed #C084FC;
    border-radius: 8px;
}

/* Menu Bar & Menu Dropdown */
QMenuBar {
    background-color: #FFFFFF;
    color: #1E293B;
    border-bottom: 1px solid #E2E8F0;
    padding: 2px 6px;
    font-size: 12px;
    font-weight: 500;
}

QMenuBar::item {
    background: transparent;
    padding: 5px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #F1F5F9;
    color: #0284C7;
}

QMenu {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px;
    color: #1E293B;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #E0F2FE;
    color: #0284C7;
}

QMenu::separator {
    height: 1px;
    background-color: #E2E8F0;
    margin: 4px 6px;
}

/* Quick Project Bar */
QFrame#projectBar {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 3px 6px;
}

QFrame#projectBar QPushButton {
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 600;
    background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
}

QFrame#projectBar QPushButton:hover {
    background-color: #E0F2FE;
    border-color: #0EA5E9;
    color: #0284C7;
}
"""


# ==============================================================================
# 2. TEMA GELAP MODERN (DARK GIS THEME) - DUKUNGAN OPSIONAL
# ==============================================================================
DARK_GIS_THEME = """
/* Reset & Global */
QWidget {
    background-color: #171a22;
    color: #e2e8f0;
    font-family: "Segoe UI", -apple-system, Roboto, Helvetica, Arial, sans-serif;
    font-size: 12px;
}

QMainWindow {
    background-color: #111318;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

QSplitter::handle {
    background-color: #2e384d;
    width: 5px;
    height: 5px;
}

QSplitter::handle:hover {
    background-color: #00adb5;
}

QGroupBox {
    background-color: #1a1e27;
    border: 1px solid #2e384d;
    border-radius: 8px;
    margin-top: 26px;
    padding: 16px 10px 12px 10px;
    font-weight: bold;
    font-size: 12px;
    color: #00adb5;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 3px 12px;
    left: 12px;
    top: 4px;
    background-color: #222938;
    border: 1px solid #3b4760;
    border-radius: 4px;
    color: #00adb5;
    font-size: 11px;
}

QLineEdit, QComboBox, QTextEdit, QDoubleSpinBox, QSpinBox {
    background-color: #12151c;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #ffffff;
    selection-background-color: #00adb5;
    min-height: 22px;
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
    border: 1px solid #00adb5;
    background-color: #161a24;
}

QDoubleSpinBox, QSpinBox {
    padding-left: 8px;
    padding-right: 24px;
    padding-top: 4px;
    padding-bottom: 4px;
}

QDoubleSpinBox::up-button, QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid #334155;
    border-bottom: 1px solid #334155;
    border-top-right-radius: 5px;
    background-color: #1e2533;
    margin: 1px 1px 0px 0px;
}

QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover {
    background-color: #2d3748;
}

QDoubleSpinBox::up-arrow, QSpinBox::up-arrow {
    image: url("__SPIN_UP_DARK__");
    width: 7px;
    height: 4px;
}

QDoubleSpinBox::down-button, QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    border-left: 1px solid #334155;
    border-bottom-right-radius: 5px;
    background-color: #1e2533;
    margin: 0px 1px 1px 0px;
}

QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {
    background-color: #2d3748;
}

QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {
    image: url("__SPIN_DOWN_DARK__");
    width: 7px;
    height: 4px;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #334155;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox::down-arrow {
    image: url("__COMBO_DOWN_DARK__");
    width: 8px;
    height: 5px;
}

QTabWidget::pane {
    border: 1px solid #2d3748;
    background-color: #1c212c;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background-color: #141720;
    color: #8b9bb4;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
    font-weight: 600;
    font-size: 12px;
    border: 1px solid #263042;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: #1c212c;
    color: #00adb5;
    border-top: 2px solid #00adb5;
    border-left: 1px solid #2d3748;
    border-right: 1px solid #2d3748;
    border-bottom: 1px solid #1c212c;
}

QPushButton {
    background-color: #242c3b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    color: #f1f5f9;
}

QPushButton:hover {
    background-color: #2d3748;
    border-color: #00adb5;
}

#btnSaveNode {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00adb5, stop:1 #0ea5e9);
    border: none;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 9px 16px;
    border-radius: 6px;
}

#btnExportKML {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e67e22, stop:1 #d35400);
    border: none;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 9px 16px;
    border-radius: 6px;
}

#btnSearchGeocode {
    background-color: #00adb5;
    border: none;
    color: #ffffff;
    font-weight: bold;
}

#btnGeneratePoles {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8e44ad, stop:1 #3498db);
    border: none;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 9px 16px;
    border-radius: 6px;
}

QTableWidget {
    background-color: #12151c;
    border: 1px solid #2d3748;
    border-radius: 6px;
    gridline-color: #1e2533;
    color: #f1f5f9;
}

QHeaderView::section {
    background-color: #1c212c;
    color: #94a3b8;
    padding: 6px;
    font-weight: 600;
    border: none;
    border-right: 1px solid #2d3748;
    border-bottom: 1px solid #2d3748;
}

QStatusBar {
    background-color: #111318;
    color: #94a3b8;
    border-top: 1px solid #263042;
    font-size: 11px;
}

QFrame#searchContainer {
    background-color: #232834;
    border: 1px solid #333c4d;
    border-radius: 8px;
    padding: 4px;
}

QFrame#exportFooter {
    background-color: #1a1e27;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 8px;
}

QFrame#calcBox {
    background-color: #12151d;
    border: 1px solid #00adb5;
    border-radius: 8px;
}

QFrame#previewAutoBox {
    background-color: #161822;
    border: 1px dashed #9b59b6;
    border-radius: 8px;
}

QMenuBar {
    background-color: #111318;
    color: #E2E8F0;
    border-bottom: 1px solid #263042;
    padding: 2px 6px;
    font-size: 12px;
}

QMenuBar::item {
    background: transparent;
    padding: 5px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #1C212C;
    color: #00ADB5;
}

QMenu {
    background-color: #171A22;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px;
    color: #E2E8F0;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #00ADB5;
    color: #FFFFFF;
}

QMenu::separator {
    height: 1px;
    background-color: #334155;
    margin: 4px 6px;
}

QFrame#projectBar {
    background-color: #1A1E27;
    border: 1px solid #2E384D;
    border-radius: 8px;
    padding: 3px 6px;
}

QFrame#projectBar QPushButton {
    padding: 5px 12px;
    font-size: 11px;
    background-color: #242C3B;
    border: 1px solid #334155;
}

QFrame#projectBar QPushButton:hover {
    background-color: #2D3748;
    border-color: #00ADB5;
    color: #00ADB5;
}
"""


# ==============================================================================
# 3. HELPER FUNCTIONS UNTUK MANAJEMEN TEMA GLOBAL
# ==============================================================================
def get_light_theme() -> str:
    """Mengembalikan kode QSS untuk tema cerah modern dengan ikon SVG terintegrasi."""
    return (
        LIGHT_GIS_THEME
        .replace("__SPIN_UP_LIGHT__", _SPIN_UP_LIGHT)
        .replace("__SPIN_DOWN_LIGHT__", _SPIN_DOWN_LIGHT)
        .replace("__COMBO_DOWN_LIGHT__", _COMBO_DOWN_LIGHT)
    )


def get_dark_theme() -> str:
    """Mengembalikan kode QSS untuk tema gelap dengan ikon SVG terintegrasi."""
    return (
        DARK_GIS_THEME
        .replace("__SPIN_UP_DARK__", _SPIN_UP_DARK)
        .replace("__SPIN_DOWN_DARK__", _SPIN_DOWN_DARK)
        .replace("__COMBO_DOWN_DARK__", _COMBO_DOWN_DARK)
    )


def apply_theme(target: QWidget | QApplication, theme_name: str = "light") -> None:
    """
    Menerapkan stylesheet tema ke instance QApplication atau QWidget/QMainWindow.
    
    Args:
        target: Instance QApplication atau QWidget.
        theme_name: 'light' (default) atau 'dark'.
    """
    stylesheet = get_light_theme() if theme_name.lower() == "light" else get_dark_theme()
    target.setStyleSheet(stylesheet)
