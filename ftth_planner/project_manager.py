"""
Modul Pengelolaan Proyek FTTH (FTTH Project Manager)
Menangani serialisasi dan deserialisasi state aplikasi lengkap (titik simpul ODC/ODP/tiang,
rute jalur kabel polyline, pengaturan slack, dan parameter toleransi QC)
ke dan dari file format JSON / .ftth dengan penanganan kesalahan yang tangguh.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .models import CableSegment, FTTHNode


class ProjectIOError(Exception):
    """Exception khusus saat terjadi kesalahan I/O atau format file proyek."""
    pass


class FTTHProjectManager:
    """
    Manajer Serialisasi State Proyek FTTH.
    Menyediakan fungsi simpan dan buka proyek dengan validasi skema data.
    """
    FILE_EXTENSION = ".ftth"
    FILE_FILTER = "FTTH Project Files (*.ftth *.json);;JSON Files (*.json);;All Files (*)"
    CURRENT_VERSION = "1.0"

    @classmethod
    def save_to_file(
        cls,
        filepath: str,
        nodes: Dict[str, FTTHNode],
        cables: Dict[str, CableSegment],
        project_name: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Menyimpan seluruh data aktif aplikasi ke file JSON lokal.
        
        Args:
            filepath: Jalur file tujuan penyimpanan.
            nodes: Kamus objek FTTHNode.
            cables: Kamus objek CableSegment.
            project_name: Nama proyek (opsional).
            settings: Parameter pengaturan tambahan (opsional).
            
        Returns:
            True jika berhasil disimpan.
            
        Raises:
            ProjectIOError jika terjadi kegagalan penulisan atau serialisasi.
        """
        if not filepath:
            raise ProjectIOError("Jalur file tujuan penyimpanan tidak ditentukan.")

        # Default nama proyek dari nama file
        if not project_name:
            project_name = os.path.splitext(os.path.basename(filepath))[0]

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        project_payload = {
            "file_format": "FTTH_NETWORK_PLANNER_PROJECT",
            "schema_version": cls.CURRENT_VERSION,
            "project_name": project_name,
            "saved_at": now_str,
            "app_name": "FTTH Network Planner - GIS Survey & Routing System",
            "settings": settings or {},
            "summary": {
                "total_nodes": len(nodes),
                "total_cables": len(cables),
                "total_cable_length_m": sum(c.total_length_m for c in cables.values())
            },
            "nodes": [node.to_dict() for node in nodes.values()],
            "cables": [cable.to_dict() for cable in cables.values()]
        }

        try:
            # Pastikan direktori tujuan tersedia
            dir_name = os.path.dirname(filepath)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(project_payload, f, indent=2, ensure_ascii=False)
            return True
        except Exception as exc:
            raise ProjectIOError(f"Gagal menulis file proyek ke '{filepath}':\n{str(exc)}")

    @classmethod
    def load_from_file(
        cls,
        filepath: str
    ) -> Dict[str, Any]:
        """
        Membaca dan memverifikasi data proyek dari file JSON / .ftth.
        
        Args:
            filepath: Jalur file proyek yang akan dimuat.
            
        Returns:
            Dict dengan kunci: 'project_name', 'nodes', 'cables', 'settings'
            
        Raises:
            ProjectIOError jika file tidak ditemukan, rusak, atau skema tidak valid.
        """
        if not os.path.isfile(filepath):
            raise ProjectIOError(f"File proyek tidak ditemukan: '{filepath}'")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except json.JSONDecodeError as err:
            raise ProjectIOError(f"Format JSON tidak valid atau file rusak:\n{str(err)}")
        except Exception as exc:
            raise ProjectIOError(f"Gagal membaca file '{filepath}':\n{str(exc)}")

        if not isinstance(payload, dict):
            raise ProjectIOError("Format isi file proyek tidak valid (harus berupa objek JSON).")

        project_name = payload.get("project_name") or os.path.splitext(os.path.basename(filepath))[0]
        settings = payload.get("settings", {})

        # Rekonstruksi Simpul (Nodes)
        nodes_dict: Dict[str, FTTHNode] = {}
        raw_nodes = payload.get("nodes", [])
        if not isinstance(raw_nodes, list):
            raise ProjectIOError("Format array 'nodes' pada file proyek tidak valid.")

        for item in raw_nodes:
            if isinstance(item, dict):
                try:
                    node = FTTHNode.from_dict(item)
                    nodes_dict[node.id] = node
                except Exception as n_err:
                    print(f"Peringatan: Gagal memuat satu simpul: {n_err}")

        # Rekonstruksi Rute Kabel (Cables)
        cables_dict: Dict[str, CableSegment] = {}
        raw_cables = payload.get("cables", [])
        if not isinstance(raw_cables, list):
            raise ProjectIOError("Format array 'cables' pada file proyek tidak valid.")

        for item in raw_cables:
            if isinstance(item, dict):
                try:
                    cable = CableSegment.from_dict(item)
                    cables_dict[cable.id] = cable
                except Exception as c_err:
                    print(f"Peringatan: Gagal memuat satu rute kabel: {c_err}")

        return {
            "project_name": project_name,
            "nodes": nodes_dict,
            "cables": cables_dict,
            "settings": settings,
        }
