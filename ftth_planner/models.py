"""
Modul Model Data FTTH dan Generator Ekspor KML (Modul 1 & Modul 2)
Menyediakan representasi objek data infrastruktur FTTH, segmen kabel (routing),
serta fungsionalitas ekspor data spasial titik (Placemark) dan garis (LineString)
ke format KML (Keyhole Markup Language) untuk Google Earth Pro dengan urutan
koordinat standar OGC KML: Longitude, Latitude, Altitude (Lon, Lat, 0).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple


class FTTHNodeType(str, Enum):
    """Enumerasi jenis infrastruktur FTTH dengan kode warna dan representasi visual."""
    ODC = "ODC (Optical Distribution Cabinet)"
    ODP = "ODP (Optical Distribution Point)"
    POLE = "Pole (Tiang Jaringan)"
    CLOSURE = "Joint Closure (FOSC)"
    HANDHOLE = "Handhole / Manhole"
    DROP_NODE = "Drop Cable Node"
    ONT = "Customer Premise (ONT)"

    @property
    def short_code(self) -> str:
        codes = {
            self.ODC: "ODC",
            self.ODP: "ODP",
            self.POLE: "POLE",
            self.CLOSURE: "CLS",
            self.HANDHOLE: "HH",
            self.DROP_NODE: "DCN",
            self.ONT: "ONT",
        }
        return codes.get(self, "NODE")

    @property
    def color_hex(self) -> str:
        """Hex color untuk marker pada Leaflet map."""
        colors = {
            self.ODC: "#e74c3c",       # Merah cerah
            self.ODP: "#2ecc71",       # Hijau
            self.POLE: "#f39c12",      # Kuning / Oranye
            self.CLOSURE: "#9b59b6",   # Ungu
            self.HANDHOLE: "#34495e",  # Abu-abu gelap
            self.DROP_NODE: "#1abc9c", # Toska
            self.ONT: "#3498db",       # Biru
        }
        return colors.get(self, "#3498db")

    @classmethod
    def from_string(cls, val: str) -> "FTTHNodeType":
        for item in cls:
            if item.value == val or item.name == val or item.short_code == val:
                return item
        return cls.POLE

    @property
    def kml_color(self) -> str:
        """Format warna KML (aabbggrr dalam heksadesimal)."""
        kml_colors = {
            self.ODC: "ff3c4ce7",       # Merah
            self.ODP: "ff71cc2e",       # Hijau
            self.POLE: "ff129cf3",      # Kuning oranye
            self.CLOSURE: "ffb6599b",   # Ungu
            self.HANDHOLE: "ff5e4934",  # Abu-abu gelap
            self.DROP_NODE: "ff9cbc1a", # Toska
            self.ONT: "ffdb9834",       # Biru
        }
        return kml_colors.get(self, "ffffffff")


class CableType(str, Enum):
    """Kategori kabel fiber optik dalam topologi FTTH."""
    FEEDER = "Kabel Feeder (Backbone ODC)"
    DISTRIBUTION = "Kabel Distribusi (ODC ke ODP)"
    DROP = "Drop Cable (ODP ke Pelanggan)"

    @property
    def short_code(self) -> str:
        codes = {
            self.FEEDER: "FDR",
            self.DISTRIBUTION: "DST",
            self.DROP: "DRP",
        }
        return codes.get(self, "CBL")

    @property
    def color_hex(self) -> str:
        """Hex color untuk garis polyline pada peta Leaflet."""
        colors = {
            self.FEEDER: "#e74c3c",       # Merah tegas
            self.DISTRIBUTION: "#3498db", # Biru cerah
            self.DROP: "#2ecc71",         # Hijau
        }
        return colors.get(self, "#00adb5")

    @property
    def kml_color(self) -> str:
        """Format warna garis KML (aabbggrr)."""
        kml_colors = {
            self.FEEDER: "ff3c4ce7",       # Merah
            self.DISTRIBUTION: "ffdb9834", # Biru
            self.DROP: "ff71cc2e",         # Hijau
        }
        return kml_colors.get(self, "ffb5ad00")

    @classmethod
    def from_string(cls, val: str) -> "CableType":
        for item in cls:
            if item.value == val or item.name == val or item.short_code == val:
                return item
        return cls.DISTRIBUTION

    @property
    def line_width(self) -> int:
        """Ketebalan garis di Google Earth."""
        widths = {
            self.FEEDER: 5,
            self.DISTRIBUTION: 4,
            self.DROP: 3,
        }
        return widths.get(self, 4)


@dataclass
class FTTHNode:
    """Representasi satu titik infrastruktur jaringan fiber optik."""
    id: str
    name: str
    infra_type: FTTHNodeType
    latitude: float
    longitude: float
    capacity: str = "N/A"
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "infra_type": self.infra_type.value,
            "infra_code": self.infra_type.short_code,
            "color": self.infra_type.color_hex,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "capacity": self.capacity,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FTTHNode":
        infra_raw = data.get("infra_type") or data.get("infra_code") or ""
        infra_type = FTTHNodeType.from_string(str(infra_raw))
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            infra_type=infra_type,
            latitude=float(data.get("latitude", 0.0)),
            longitude=float(data.get("longitude", 0.0)),
            capacity=str(data.get("capacity", "N/A")),
            notes=str(data.get("notes", "")),
            created_at=str(data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        )


@dataclass
class CableSegment:
    """Representasi segmen jalur kabel optik yang menghubungkan dua simpul FTTH."""
    id: str
    name: str
    cable_type: CableType
    source_node_id: str
    source_node_name: str
    source_lat: float
    source_lng: float
    target_node_id: str
    target_node_name: str
    target_lat: float
    target_lng: float
    span_distance_m: float       # Jarak bentangan geospasial lurus atau jalan (meter)
    slack_percent: float         # Persentase cadangan kabel (cth: 10.0%)
    total_length_m: float        # Total panjang riil kabel (meter)
    core_count: str = "24 Core"  # Jumlah core serat optik
    notes: str = ""
    path_coordinates: List[Tuple[float, float]] = field(default_factory=list)  # Titik-titik kontur jalan (lat, lon)
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "cable_type": self.cable_type.value,
            "cable_code": self.cable_type.short_code,
            "color": self.cable_type.color_hex,
            "source_node_id": self.source_node_id,
            "source_node_name": self.source_node_name,
            "source_lat": self.source_lat,
            "source_lng": self.source_lng,
            "target_node_id": self.target_node_id,
            "target_node_name": self.target_node_name,
            "target_lat": self.target_lat,
            "target_lng": self.target_lng,
            "span_distance_m": self.span_distance_m,
            "slack_percent": self.slack_percent,
            "total_length_m": self.total_length_m,
            "core_count": self.core_count,
            "path_coordinates": self.path_coordinates or [[self.source_lat, self.source_lng], [self.target_lat, self.target_lng]],
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CableSegment":
        cable_raw = data.get("cable_type") or data.get("cable_code") or ""
        cable_type = CableType.from_string(str(cable_raw))

        path_coords = []
        if "path_coordinates" in data and isinstance(data["path_coordinates"], list):
            for pt in data["path_coordinates"]:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    path_coords.append((float(pt[0]), float(pt[1])))

        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            cable_type=cable_type,
            source_node_id=str(data.get("source_node_id", "")),
            source_node_name=str(data.get("source_node_name", "")),
            source_lat=float(data.get("source_lat", 0.0)),
            source_lng=float(data.get("source_lng", 0.0)),
            target_node_id=str(data.get("target_node_id", "")),
            target_node_name=str(data.get("target_node_name", "")),
            target_lat=float(data.get("target_lat", 0.0)),
            target_lng=float(data.get("target_lng", 0.0)),
            span_distance_m=float(data.get("span_distance_m", 0.0)),
            slack_percent=float(data.get("slack_percent", 10.0)),
            total_length_m=float(data.get("total_length_m", 0.0)),
            core_count=str(data.get("core_count", "24 Core")),
            notes=str(data.get("notes", "")),
            path_coordinates=path_coords,
            created_at=str(data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        )


class KMLExporter:
    """Generator dokumen KML 2.2 terstruktur untuk visualisasi di Google Earth Pro."""

    @staticmethod
    def normalize_to_lon_lat(pt: Union[Tuple[float, float], List[float]]) -> Tuple[float, float]:
        """
        Mengonversi tuple/list koordinat dari representasi Leaflet/OSRM (lat, lon)
        menjadi format standar KML (lon, lat).
        
        Pemeriksaan batas geografis:
        - Lintang (Latitude): -90 s/d +90
        - Bujur (Longitude): -180 s/d +180
        """
        c1, c2 = float(pt[0]), float(pt[1])
        if abs(c1) > 90.0 >= abs(c2):
            # c1 adalah Longitude, c2 adalah Latitude
            return (c1, c2)
        elif abs(c2) > 90.0 >= abs(c1):
            # c2 adalah Longitude, c1 adalah Latitude (format Leaflet/OSRM)
            return (c2, c1)
        else:
            # Jika kedua nilai <= 90, standar Leaflet/OSRM adalah (lat, lon), dibalik ke (lon, lat)
            return (c2, c1)

    @staticmethod
    def _format_coord(pt: Union[Tuple[float, float], List[float]]) -> str:
        """
        Memastikan format koordinat selalu dalam urutan standar KML:
        Longitude,Latitude,Altitude (tanpa spasi di antara koma).
        Contoh: "106.8456000,-6.2088000,0"
        """
        lon, lat = KMLExporter.normalize_to_lon_lat(pt)
        return f"{lon:.7f},{lat:.7f},0"

    @staticmethod
    def export(
        nodes: List[FTTHNode],
        cables: Optional[List[CableSegment]] = None,
        output_filepath: str = "FTTH_Network.kml",
        document_name: str = "FTTH Network Design & Routing",
        use_simplekml: bool = False
    ) -> bool:
        """
        Mengekspor daftar FTTHNode (Placemarks Point) dan CableSegment (Placemarks LineString)
        ke file .kml dengan format koordinat Longitude,Latitude standar OGC KML 2.2.
        
        Jika use_simplekml=True, ekspor akan didelegasikan ke library simplekml.
        """
        if use_simplekml:
            return KMLExporter.export_with_simplekml(nodes, cables, output_filepath, document_name)

        if cables is None:
            cables = []

        kml_header = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
  <Document>
    <name>{document_name}</name>
    <open>1</open>
    <description>Hasil Perencanaan Jaringan, Survey Spasial, dan Rute Kabel FTTH</description>
"""

        # 1. Definisikan Styles untuk Titik Simpul (Nodes)
        styles = ""
        for node_type in FTTHNodeType:
            style_id = f"style_{node_type.short_code}"
            color_kml = node_type.kml_color
            styles += f"""    <Style id="{style_id}">
      <IconStyle>
        <color>{color_kml}</color>
        <scale>1.2</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href>
        </Icon>
      </IconStyle>
      <LabelStyle>
        <scale>0.8</scale>
      </LabelStyle>
      <BalloonStyle>
        <text><![CDATA[
          <h3>$[name]</h3>
          $[description]
        ]]></text>
      </BalloonStyle>
    </Style>
"""

        # 2. Definisikan Styles untuk Jalur Garis Kabel (LineString)
        for cable_type in CableType:
            style_id = f"style_line_{cable_type.short_code}"
            color_kml = cable_type.kml_color
            width = cable_type.line_width
            styles += f"""    <Style id="{style_id}">
      <LineStyle>
        <color>{color_kml}</color>
        <width>{width}</width>
      </LineStyle>
      <BalloonStyle>
        <text><![CDATA[
          <h3>$[name]</h3>
          $[description]
        ]]></text>
      </BalloonStyle>
    </Style>
"""

        # 3. FOLDER 1: Titik Simpul FTTH (Placemark Points)
        nodes_folder = """    <Folder>
      <name>📍 Infrastruktur Simpul FTTH</name>
      <open>1</open>
"""
        grouped_nodes = {}
        for node in nodes:
            grouped_nodes.setdefault(node.infra_type, []).append(node)

        for infra_type, node_list in grouped_nodes.items():
            nodes_folder += f"""      <Folder>
        <name>{infra_type.value} ({len(node_list)})</name>
        <open>1</open>
"""
            style_id = f"style_{infra_type.short_code}"
            for node in node_list:
                coord_str = KMLExporter._format_coord((node.latitude, node.longitude))
                description_html = f"""<![CDATA[
<table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse; font-family:Arial, sans-serif; font-size:12px; width:290px;">
  <tr bgcolor="#2c3e50">
    <th colspan="2" align="left" style="color:white; padding:6px;">Detail Titik FTTH</th>
  </tr>
  <tr><td><b>Kode / ID</b></td><td>{node.id}</td></tr>
  <tr><td><b>Nama</b></td><td>{node.name}</td></tr>
  <tr><td><b>Kategori</b></td><td>{node.infra_type.value}</td></tr>
  <tr><td><b>Kapasitas</b></td><td>{node.capacity}</td></tr>
  <tr><td><b>Koordinat</b></td><td>{node.latitude:.6f}, {node.longitude:.6f}</td></tr>
  <tr><td><b>Catatan</b></td><td>{node.notes or '-'}</td></tr>
  <tr><td><b>Waktu Survey</b></td><td>{node.created_at}</td></tr>
</table>
]]>"""
                nodes_folder += f"""        <Placemark>
          <name>{node.name} [{node.id}]</name>
          <styleUrl>#{style_id}</styleUrl>
          <description>{description_html}</description>
          <Point>
            <altitudeMode>clampToGround</altitudeMode>
            <coordinates>{coord_str}</coordinates>
          </Point>
        </Placemark>
"""
            nodes_folder += "      </Folder>\n"

        nodes_folder += "    </Folder>\n"

        # 4. FOLDER 2: Rute Kabel Optik (Placemark LineStrings)
        cables_folder = """    <Folder>
      <name>🔗 Jalur Kabel Optik (Routing)</name>
      <open>1</open>
"""
        grouped_cables = {}
        for cable in cables:
            grouped_cables.setdefault(cable.cable_type, []).append(cable)

        for cable_type, cable_list in grouped_cables.items():
            cables_folder += f"""      <Folder>
        <name>{cable_type.value} ({len(cable_list)})</name>
        <open>1</open>
"""
            style_id = f"style_line_{cable_type.short_code}"

            for cable in cable_list:
                desc_html = f"""<![CDATA[
<table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse; font-family:Arial, sans-serif; font-size:12px; width:300px;">
  <tr bgcolor="#1b2a4a">
    <th colspan="2" align="left" style="color:white; padding:6px;">Rincian Jalur Kabel FTTH</th>
  </tr>
  <tr><td><b>Kode Jalur</b></td><td>{cable.id}</td></tr>
  <tr><td><b>Nama Rute</b></td><td>{cable.name}</td></tr>
  <tr><td><b>Jenis Kabel</b></td><td>{cable.cable_type.value}</td></tr>
  <tr><td><b>Kapasitas Core</b></td><td>{cable.core_count}</td></tr>
  <tr><td><b>Titik Asal</b></td><td>{cable.source_node_name} [{cable.source_node_id}]</td></tr>
  <tr><td><b>Titik Tujuan</b></td><td>{cable.target_node_name} [{cable.target_node_id}]</td></tr>
  <tr bgcolor="#f9f9f9"><td><b>Jarak Bentang (Span)</b></td><td><b>{cable.span_distance_m:.2f} meter</b></td></tr>
  <tr bgcolor="#f9f9f9"><td><b>Cadangan (Slack)</b></td><td>{cable.slack_percent:.1f}% ({cable.span_distance_m * cable.slack_percent / 100:.2f} m)</td></tr>
  <tr bgcolor="#e8f8f5"><td><b>Total Panjang Riil</b></td><td><b style="color:#117a65; font-size:13px;">{cable.total_length_m:.2f} meter</b></td></tr>
  <tr><td><b>Catatan Lapangan</b></td><td>{cable.notes or '-'}</td></tr>
  <tr><td><b>Waktu Perancangan</b></td><td>{cable.created_at}</td></tr>
</table>
]]>"""
                # Ekstraksi seluruh koordinat rute jalan raya dalam format standar KML: Longitude,Latitude,Altitude
                if cable.path_coordinates and len(cable.path_coordinates) >= 2:
                    coords_list = [KMLExporter._format_coord(pt) for pt in cable.path_coordinates]
                else:
                    coords_list = [
                        KMLExporter._format_coord((cable.source_lat, cable.source_lng)),
                        KMLExporter._format_coord((cable.target_lat, cable.target_lng)),
                    ]

                # Standar KML OGC: setiap koordinat dipisahkan spasi tunggal tanpa spasi di sekitar koma
                coords_str = " ".join(coords_list)

                cables_folder += f"""        <Placemark>
          <name>{cable.name} ({cable.total_length_m:.1f}m)</name>
          <styleUrl>#{style_id}</styleUrl>
          <description>{desc_html}</description>
          <LineString>
            <tessellate>1</tessellate>
            <altitudeMode>clampToGround</altitudeMode>
            <coordinates>{coords_str}</coordinates>
          </LineString>
        </Placemark>
"""
            cables_folder += "      </Folder>\n"

        cables_folder += "    </Folder>\n"

        kml_footer = """  </Document>
</kml>"""

        full_kml = kml_header + styles + nodes_folder + (cables_folder if cables else "") + kml_footer

        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(full_kml)

        return True

    @staticmethod
    def export_with_simplekml(
        nodes: List[FTTHNode],
        cables: Optional[List[CableSegment]] = None,
        output_filepath: str = "FTTH_Network.kml",
        document_name: str = "FTTH Complete Network Design"
    ) -> bool:
        """
        Mengekspor data FTTH menggunakan library simplekml.
        
        CATATAN PENTING SESUAI STANDAR GEOSPASIAL KML:
        - simplekml method newlinestring(coords=...) WAJIB menerima list tuple (lon, lat)
          atau (lon, lat, alt), BUKAN (lat, lon).
        - Leaflet dan OSRM internal menggunakan format (lat, lon), sehingga harus
          dikonversi dengan benar ke (lon, lat) saat dimasukkan ke simplekml.
        """
        try:
            import simplekml
        except ImportError:
            # Fallback ke pure generator jika simplekml belum terinstal
            return KMLExporter.export(nodes, cables, output_filepath, document_name, use_simplekml=False)

        kml = simplekml.Kml(name=document_name)

        if cables is None:
            cables = []

        # 1. Folder Titik Simpul Infrastruktur
        nodes_folder = kml.newfolder(name="📍 Infrastruktur Simpul FTTH")
        grouped_nodes = {}
        for node in nodes:
            grouped_nodes.setdefault(node.infra_type, []).append(node)

        for infra_type, node_list in grouped_nodes.items():
            sub_folder = nodes_folder.newfolder(name=f"{infra_type.value} ({len(node_list)})")
            for node in node_list:
                lon, lat = KMLExporter.normalize_to_lon_lat((node.latitude, node.longitude))
                pnt = sub_folder.newpoint(
                    name=f"{node.name} [{node.id}]",
                    coords=[(lon, lat)]  # PENTING: (lon, lat) untuk simplekml
                )
                pnt.altitudemode = simplekml.AltitudeMode.clamptoground
                pnt.style.iconstyle.color = node.infra_type.kml_color
                pnt.style.iconstyle.scale = 1.2
                pnt.style.iconstyle.icon.href = "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"
                pnt.description = f"""<b>Detail Titik FTTH:</b><br/>
ID: {node.id}<br/>
Kategori: {node.infra_type.value}<br/>
Kapasitas: {node.capacity}<br/>
Koordinat: {node.latitude:.6f}, {node.longitude:.6f}<br/>
Catatan: {node.notes or '-'}"""

        # 2. Folder Rute Kabel Optik (LineStrings)
        cables_folder = kml.newfolder(name="🔗 Jalur Kabel Optik (Routing)")
        grouped_cables = {}
        for cable in cables:
            grouped_cables.setdefault(cable.cable_type, []).append(cable)

        for cable_type, cable_list in grouped_cables.items():
            sub_folder = cables_folder.newfolder(name=f"{cable_type.value} ({len(cable_list)})")
            for cable in cable_list:
                # Ambil seluruh titik koordinat rute jalan raya dan konversi ke (lon, lat)
                if cable.path_coordinates and len(cable.path_coordinates) >= 2:
                    kml_coords = [KMLExporter.normalize_to_lon_lat(pt) for pt in cable.path_coordinates]
                else:
                    kml_coords = [
                        KMLExporter.normalize_to_lon_lat((cable.source_lat, cable.source_lng)),
                        KMLExporter.normalize_to_lon_lat((cable.target_lat, cable.target_lng))
                    ]

                # Buat LineString dengan koordinat (lon, lat)
                ls = sub_folder.newlinestring(
                    name=f"{cable.name} ({cable.total_length_m:.1f}m)",
                    coords=kml_coords  # WAJIB [(lon, lat), ...]
                )
                ls.tessellate = 1
                ls.altitudemode = simplekml.AltitudeMode.clamptoground
                ls.style.linestyle.width = cable.cable_type.line_width
                ls.style.linestyle.color = cable.cable_type.kml_color
                ls.description = f"""<b>Rincian Jalur Kabel FTTH:</b><br/>
Kode Jalur: {cable.id}<br/>
Tipe: {cable.cable_type.value}<br/>
Kapasitas: {cable.core_count}<br/>
Dari: {cable.source_node_name} [{cable.source_node_id}]<br/>
Ke: {cable.target_node_name} [{cable.target_node_id}]<br/>
Bentang Jalan: {cable.span_distance_m:.2f} m<br/>
Slack: {cable.slack_percent:.1f}%<br/>
Total Panjang Kabel: {cable.total_length_m:.2f} m"""

        kml.save(output_filepath)
        return True

