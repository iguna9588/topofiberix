"""
Modul Multi-Format Importer (KML, KMZ, CSV, XLSX) untuk FTTH Network Planner
Mendukung pembacaan data spasial infrastruktur dan kabel dari berbagai sumber file eksternal:
- CSV & Excel (.xlsx, .xls) menggunakan Pandas (pencocokan kolom cerdas)
- Google Earth KML & KMZ terkompresi (ekstraksi Placemark Point & LineString)
"""

import os
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from .distance import calculate_geodesic_distance
from .models import CableSegment, CableType, FTTHNode, FTTHNodeType


class DataImportError(Exception):
    """Exception khusus saat terjadi kesalahan parsing atau format file tidak valid."""
    pass


@dataclass
class ImportResult:
    """Hasil ekstraksi data dari file yang diimpor."""
    nodes: List[FTTHNode] = field(default_factory=list)
    cables: List[CableSegment] = field(default_factory=list)
    file_type: str = ""
    total_parsed: int = 0
    skipped_count: int = 0
    warnings: List[str] = field(default_factory=list)
    summary_message: str = ""


class FTTHDataImporter:
    """
    Kelas parser terintegrasi untuk membaca dan mengonversi berbagai format
    file geospasial & tabular ke struktur objek FTTHNode dan CableSegment.
    """

    SUPPORTED_EXTENSIONS = ('.kml', '.kmz', '.csv', '.xlsx', '.xls')
    FILE_FILTER = (
        "Semua Format Didukung (*.kml *.kmz *.csv *.xlsx *.xls);;"
        "Google Earth KML (*.kml);;"
        "Google Earth KMZ (*.kmz);;"
        "Comma Separated Values (*.csv);;"
        "Microsoft Excel (*.xlsx *.xls);;"
        "Semua File (*.*)"
    )

    @classmethod
    def import_file(cls, filepath: str) -> ImportResult:
        """
        Fungsi utama untuk mengimpor file berdasarkan ekstensinya.
        
        Args:
            filepath: Jalur lengkap ke file yang dipilih.
            
        Returns:
            ImportResult berisi daftar FTTHNode dan CableSegment.
            
        Raises:
            DataImportError jika file tidak valid, korup, atau tidak memiliki koordinat.
        """
        if not os.path.exists(filepath):
            raise DataImportError(f"File tidak ditemukan: {filepath}")

        ext = os.path.splitext(filepath)[1].lower()

        if ext == '.csv':
            return cls._import_csv(filepath)
        elif ext in ('.xlsx', '.xls'):
            return cls._import_excel(filepath)
        elif ext == '.kml':
            return cls._import_kml(filepath)
        elif ext == '.kmz':
            return cls._import_kmz(filepath)
        else:
            raise DataImportError(
                f"Format ekstensi '{ext}' tidak didukung.\n"
                f"Format yang didukung: {', '.join(cls.SUPPORTED_EXTENSIONS)}"
            )

    # =========================================================================
    # 1. PARSER TABULAR (CSV & EXCEL)
    # =========================================================================

    @classmethod
    def _import_csv(cls, filepath: str) -> ImportResult:
        """Membaca file CSV dengan berbagai opsi separator dan encoding."""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        df = None
        last_error = None

        for enc in encodings:
            try:
                # Coba deteksi separator secara otomatis (koma atau titik-koma)
                df = pd.read_csv(filepath, sep=None, engine='python', encoding=enc)
                if df is not None and len(df.columns) > 1:
                    break
            except Exception as e:
                last_error = e
                continue

        if df is None or df.empty:
            # Fallback membaca dengan delimiter koma standar
            try:
                df = pd.read_csv(filepath)
            except Exception as e:
                raise DataImportError(f"Gagal membaca file CSV: {str(last_error or e)}")

        return cls._parse_dataframe(df, file_type="CSV")

    @classmethod
    def _import_excel(cls, filepath: str) -> ImportResult:
        """Membaca file Microsoft Excel (.xlsx, .xls) sheet pertama."""
        try:
            df = pd.read_excel(filepath, sheet_name=0)
        except Exception as e:
            raise DataImportError(f"Gagal membaca file Excel (.xlsx/.xls): {str(e)}")

        return cls._parse_dataframe(df, file_type="Excel")

    @classmethod
    def _parse_dataframe(cls, df: pd.DataFrame, file_type: str) -> ImportResult:
        """
        Menganalisis kolom DataFrame secara adaptif dan mengekstrak titik simpul FTTH.
        Mencocokkan variasi penamaan kolom (cth: lat, latitude, lintang, y).
        """
        if df.empty:
            raise DataImportError(f"File {file_type} kosong atau tidak memiliki baris data.")

        # Buat pemetaan kolom case-insensitive & bersih
        col_map = {}
        for c in df.columns:
            clean = str(c).strip().lower().replace("_", "").replace(" ", "").replace("-", "")
            col_map[clean] = c

        def find_col(candidates: List[str]) -> Optional[str]:
            # 1. Exact match
            for cand in candidates:
                cand_clean = cand.lower().replace("_", "").replace(" ", "").replace("-", "")
                if cand_clean in col_map:
                    return col_map[cand_clean]
            # 2. Substring match
            for col_clean, orig_col in col_map.items():
                for cand in candidates:
                    cand_clean = cand.lower().replace("_", "").replace(" ", "").replace("-", "")
                    if len(cand_clean) >= 3 and cand_clean in col_clean:
                        return orig_col
            return None

        # Identifikasi kolom koordinat (Wajib)
        lat_col = find_col(['latitude', 'lat', 'lintang', 'y', 'koordinaty', 'latdd'])
        lng_col = find_col(['longitude', 'lng', 'lon', 'long', 'bujur', 'x', 'koordinatx', 'londd'])

        if not lat_col or not lng_col:
            found_cols = ", ".join([str(c) for c in df.columns[:8]])
            raise DataImportError(
                f"File {file_type} tidak memiliki kolom koordinat Latitude dan Longitude yang valid.\n\n"
                f"Kolom terdeteksi: [{found_cols}]\n\n"
                f"Pastikan terdapat kolom seperti 'Latitude' / 'Lat' dan 'Longitude' / 'Lng'."
            )

        # Identifikasi kolom opsional
        id_col = find_col(['id', 'kode', 'code', 'nodeid', 'kodesimpul', 'kodetitik', 'siteid', 'titikid', 'no'])
        name_col = find_col(['name', 'nama', 'label', 'sitename', 'namatitik', 'namalokasi', 'lokasi', 'alamat', 'keterangan'])
        type_col = find_col(['type', 'tipe', 'jenis', 'infratype', 'kategori', 'infratypename'])
        cap_col = find_col(['capacity', 'kapasitas', 'spec', 'spesifikasi', 'core', 'port'])
        notes_col = find_col(['notes', 'catatan', 'remark', 'remarks', 'desc', 'deskripsi'])

        nodes: List[FTTHNode] = []
        warnings: List[str] = []
        skipped = 0

        for idx, row in df.iterrows():
            row_num = idx + 2  # Asumsi header baris 1 (1-indexed)

            # Ekstraksi dan sanitasi Latitude & Longitude
            raw_lat = row[lat_col]
            raw_lng = row[lng_col]

            lat_val = cls._clean_coordinate(raw_lat)
            lng_val = cls._clean_coordinate(raw_lng)

            if lat_val is None or lng_val is None:
                skipped += 1
                warnings.append(f"Baris {row_num}: Koordinat tidak valid ({raw_lat}, {raw_lng}), dilewati.")
                continue

            if not (-90.0 <= lat_val <= 90.0) or not (-180.0 <= lng_val <= 180.0):
                # Deteksi jika tertukar
                if (-90.0 <= lng_val <= 90.0) and (-180.0 <= lat_val <= 180.0):
                    lat_val, lng_val = lng_val, lat_val
                else:
                    skipped += 1
                    warnings.append(f"Baris {row_num}: Koordinat di luar rentang geografis ({lat_val}, {lng_val}), dilewati.")
                    continue

            # Ekstraksi ID & Nama
            node_id = str(row[id_col]).strip() if id_col and pd.notna(row[id_col]) else f"IMP-{len(nodes) + 1:03d}"
            # Hilangkan desimal jika ID terbaca float (misal 101.0 -> 101)
            if node_id.endswith('.0'):
                node_id = node_id[:-2]

            name = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else f"Titik {node_id}"

            # Ekstraksi Tipe Infrastruktur
            raw_type = str(row[type_col]).strip() if type_col and pd.notna(row[type_col]) else ""
            if not raw_type:
                # Inferensi dari nama atau ID
                raw_type = cls._infer_infra_type_from_string(f"{node_id} {name}")

            infra_type = FTTHNodeType.from_string(raw_type)

            capacity = str(row[cap_col]).strip() if cap_col and pd.notna(row[cap_col]) else "N/A"
            notes = str(row[notes_col]).strip() if notes_col and pd.notna(row[notes_col]) else f"Imported from {file_type}"

            node = FTTHNode(
                id=node_id,
                name=name,
                infra_type=infra_type,
                latitude=lat_val,
                longitude=lng_val,
                capacity=capacity,
                notes=notes
            )
            nodes.append(node)

        if not nodes:
            raise DataImportError(
                f"Tidak ada baris data valid yang berhasil diekstraksi dari file {file_type}.\n"
                f"Jumlah baris dilewati: {skipped}."
            )

        summary = (
            f"Impor {file_type} Berhasil!\n\n"
            f"• Total Titik Simpul Diekstrak: {len(nodes)} titik\n"
            f"• Baris Dilewati / Tidak Valid: {skipped} baris"
        )

        return ImportResult(
            nodes=nodes,
            cables=[],
            file_type=file_type,
            total_parsed=len(nodes),
            skipped_count=skipped,
            warnings=warnings,
            summary_message=summary
        )

    # =========================================================================
    # 2. PARSER GEOSPASIAL (KML & KMZ)
    # =========================================================================

    @classmethod
    def _import_kmz(cls, filepath: str) -> ImportResult:
        """Membuka file arsip ZIP KMZ dan mengekstrak file KML utama (doc.kml)."""
        try:
            with zipfile.ZipFile(filepath, 'r') as z:
                # Cari file dengan ekstensi .kml di dalam arsip
                kml_filename = None
                for fname in z.namelist():
                    if fname.lower().endswith('.kml'):
                        kml_filename = fname
                        break

                if not kml_filename:
                    raise DataImportError("File KMZ ini tidak memuat file dokumen .kml di dalamnya.")

                kml_bytes = z.read(kml_filename)
                return cls._parse_kml_content(kml_bytes, file_type="KMZ")
        except zipfile.BadZipFile:
            raise DataImportError("File KMZ rusak atau bukan format arsip ZIP yang valid.")
        except Exception as e:
            raise DataImportError(f"Gagal mengekstrak file KMZ: {str(e)}")

    @classmethod
    def _import_kml(cls, filepath: str) -> ImportResult:
        """Membaca file XML Google Earth KML langsung."""
        try:
            with open(filepath, 'rb') as f:
                kml_bytes = f.read()
            return cls._parse_kml_content(kml_bytes, file_type="KML")
        except Exception as e:
            raise DataImportError(f"Gagal membaca file KML: {str(e)}")

    @classmethod
    def _parse_kml_content(cls, kml_bytes: bytes, file_type: str) -> ImportResult:
        """
        Parsing konten XML KML menggunakan xml.etree.ElementTree.
        Mengekstrak Placemark Point (Simpul) dan LineString (Rute Kabel).
        """
        try:
            root = ET.fromstring(kml_bytes)
        except ET.ParseError as err:
            raise DataImportError(f"Struktur XML KML rusak atau tidak valid:\n{str(err)}")

        # Hapus deklarasi namespace XML agar pencarian elemen fleksibel
        cls._strip_xml_namespaces(root)

        nodes: List[FTTHNode] = []
        cables: List[CableSegment] = []
        warnings: List[str] = []
        skipped = 0

        # Cari semua elemen Placemark
        placemarks = root.findall('.//Placemark')
        if not placemarks:
            raise DataImportError(f"Tidak ditemukan elemen <Placemark> di dalam file {file_type}.")

        node_counter = 1
        cable_counter = 1

        for pm in placemarks:
            name_el = pm.find('name')
            desc_el = pm.find('description')
            name = name_el.text.strip() if (name_el is not None and name_el.text) else f"Placemark {node_counter}"
            desc = desc_el.text.strip() if (desc_el is not None and desc_el.text) else ""

            # -----------------------------------------------------------------
            # A. KASUS 1: TITIK SIMPUL (<Point>)
            # -----------------------------------------------------------------
            point_el = pm.find('.//Point')
            if point_el is not None:
                coord_el = point_el.find('coordinates')
                if coord_el is not None and coord_el.text:
                    coord_str = coord_el.text.strip()
                    parts = coord_str.split(',')
                    if len(parts) >= 2:
                        try:
                            # Format Standar KML: Longitude, Latitude [, Altitude]
                            lng_val = float(parts[0].strip())
                            lat_val = float(parts[1].strip())

                            # Validasi rentang
                            if not (-90.0 <= lat_val <= 90.0) or not (-180.0 <= lng_val <= 180.0):
                                skipped += 1
                                warnings.append(f"Titik '{name}': Koordinat di luar batas ({lat_val}, {lng_val}).")
                                continue

                            # Buat ID simpul
                            node_id = cls._extract_id_from_name(name, default_prefix="KML", index=node_counter)
                            node_counter += 1

                            # Inferensi tipe infrastruktur
                            infra_type = FTTHNodeType.from_string(cls._infer_infra_type_from_string(f"{name} {desc}"))

                            node = FTTHNode(
                                id=node_id,
                                name=name,
                                infra_type=infra_type,
                                latitude=lat_val,
                                longitude=lng_val,
                                capacity="Imported KML",
                                notes=desc or f"Imported from {file_type}"
                            )
                            nodes.append(node)
                            continue
                        except ValueError:
                            skipped += 1
                            continue

            # -----------------------------------------------------------------
            # B. KASUS 2: JALUR KABEL (<LineString>)
            # -----------------------------------------------------------------
            linestring_el = pm.find('.//LineString')
            if linestring_el is not None:
                coord_el = linestring_el.find('coordinates')
                if coord_el is not None and coord_el.text:
                    raw_text = coord_el.text.strip()
                    # Pisahkan berdasarkan spasi atau baris baru
                    coord_tokens = re.split(r'\s+', raw_text)
                    path_coords: List[Tuple[float, float]] = []

                    for token in coord_tokens:
                        token = token.strip()
                        if not token:
                            continue
                        parts = token.split(',')
                        if len(parts) >= 2:
                            try:
                                lon_p = float(parts[0].strip())
                                lat_p = float(parts[1].strip())
                                path_coords.append((lat_p, lon_p))
                            except ValueError:
                                continue

                    if len(path_coords) >= 2:
                        s_lat, s_lng = path_coords[0]
                        t_lat, t_lng = path_coords[-1]

                        # Hitung jarak bentangan jalan
                        span_dist = 0.0
                        for vi in range(len(path_coords) - 1):
                            span_dist += calculate_geodesic_distance(path_coords[vi], path_coords[vi + 1])

                        cable_id = f"CAB-IMP-{cable_counter:02d}"
                        cable_counter += 1

                        # Inferensi tipe kabel dari nama
                        cable_type = CableType.DISTRIBUTION
                        name_upper = name.upper()
                        if "FEEDER" in name_upper:
                            cable_type = CableType.FEEDER
                        elif "DROP" in name_upper:
                            cable_type = CableType.DROP

                        cable = CableSegment(
                            id=cable_id,
                            name=name or f"Rute {cable_id}",
                            cable_type=cable_type,
                            source_node_id=f"SRC-{cable_id}",
                            source_node_name=f"Titik Asal {name}",
                            source_lat=s_lat,
                            source_lng=s_lng,
                            target_node_id=f"TGT-{cable_id}",
                            target_node_name=f"Titik Tujuan {name}",
                            target_lat=t_lat,
                            target_lng=t_lng,
                            span_distance_m=round(span_dist, 2),
                            slack_percent=10.0,
                            total_length_m=round(span_dist * 1.10, 2),
                            core_count="24 Core",
                            notes=desc or f"Imported from {file_type} LineString",
                            path_coordinates=path_coords
                        )
                        cables.append(cable)

        if not nodes and not cables:
            raise DataImportError(
                f"File {file_type} tidak memuat satupun objek Point atau LineString yang dapat dibaca."
            )

        total_cable_m = sum(c.total_length_m for c in cables)
        summary = (
            f"Impor {file_type} Berhasil!\n\n"
            f"• Total Titik Simpul (Point): {len(nodes)} titik\n"
            f"• Total Jalur Kabel (LineString): {len(cables)} rute ({total_cable_m:.1f} m)\n"
            f"• Objek Dilewati: {skipped}"
        )

        return ImportResult(
            nodes=nodes,
            cables=cables,
            file_type=file_type,
            total_parsed=len(nodes) + len(cables),
            skipped_count=skipped,
            warnings=warnings,
            summary_message=summary
        )

    # =========================================================================
    # 3. HELPER METHODS
    # =========================================================================

    @staticmethod
    def _clean_coordinate(val: Any) -> Optional[float]:
        """Membersihkan nilai koordinat, mengubah format koma desimal ke float."""
        if val is None or pd.isna(val):
            return None
        if isinstance(val, (int, float)):
            return float(val)
        try:
            s = str(val).strip().replace(',', '.')
            return float(s)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _strip_xml_namespaces(elem: ET.Element):
        """Menghapus prefix namespace XML {http://...} dari seluruh tag secara rekursif."""
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]
        for child in elem:
            FTTHDataImporter._strip_xml_namespaces(child)

    @staticmethod
    def _infer_infra_type_from_string(text: str) -> str:
        """Mendeteksi tipe infrastruktur dari teks nama atau ID."""
        t = (text or "").upper()
        if "ODC" in t:
            return "ODC"
        elif "POLE" in t or "TIANG" in t:
            return "POLE"
        elif "CLOSURE" in t or "JOINT" in t or "JC" in t:
            return "CLOSURE"
        elif "HANDHOLE" in t or "MANHOLE" in t:
            return "HANDHOLE"
        elif "DROP" in t:
            return "DROP_NODE"
        elif "ONT" in t:
            return "ONT"
        return "ODP"

    @staticmethod
    def _extract_id_from_name(name: str, default_prefix: str, index: int) -> str:
        """Membuat kode ID yang rapi dari nama Placemark."""
        clean_name = name.strip()
        # Jika nama sudah berbentuk kode seperti ODC-01, ODP-KBY-02, dll.
        if re.match(r'^[A-Za-z0-9_-]{3,15}$', clean_name):
            return clean_name
        # Ekstrak kata pertama jika pendek
        first_word = clean_name.split()[0]
        if len(first_word) <= 10 and re.match(r'^[A-Za-z0-9_-]+$', first_word):
            return first_word
        return f"{default_prefix}-{index:03d}"
