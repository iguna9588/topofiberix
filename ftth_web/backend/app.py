"""
Aplikasi Server FastAPI untuk FTTH Network Planner
Menyediakan REST API untuk perhitungan spasial, OSRM routing jalan,
QC audit, ekspor KML, serta penyajian aset web statis (Leaflet SPA).
"""

import os
from pathlib import Path
from typing import Any, Dict, List
from fastapi import FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .schemas import (
    AuditRequest,
    AuditResponse,
    AutoPoleRequest,
    AutoPoleResponse,
    CableModel,
    NodeModel,
    ProjectSaveRequest,
    RouteRequest,
    RouteResponse,
)
from .services import FTTHBackendService

# Path direktori statis
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="FTTH Network Planner API",
    description="Sistem Perencanaan Jaringan Fiber Optic Berbasis Geospasial & Web",
    version="2.0.0"
)

# Aktifkan CORS untuk kemudahan akses saat pengembangan
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount aset statis (CSS, JS, ikon)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_index():
    """Menyajikan halaman antarmuka web interaktif utama (Single Page Application)."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Halaman web index.html belum dibuat.")
    return FileResponse(str(index_file))


@app.get("/api/health")
def health_check():
    """Pemeriksaan status server aktif."""
    return {"status": "ok", "app": "FTTH Network Planner", "version": "2.0.0"}


@app.post("/api/route", response_model=RouteResponse)
def calculate_route(req: RouteRequest):
    """Menghitung rute kontur jalan OSRM atau garis lurus antara dua titik koordinat."""
    return FTTHBackendService.calculate_route(req)


@app.post("/api/generate-poles", response_model=AutoPoleResponse)
def generate_auto_poles(req: AutoPoleRequest):
    """Membagi rute jalan menjadi tiang-tiang berjarak presisi (cth: setiap 80m)."""
    return FTTHBackendService.generate_auto_poles(req)


@app.post("/api/review-audit", response_model=AuditResponse)
def audit_design(req: AuditRequest):
    """Menjalankan audit Quality Control validasi span jarak dan kelayakan desain."""
    return FTTHBackendService.audit_quality_control(req)


@app.get("/api/geocode")
def geocode_search(q: str = Query(..., min_length=2, description="Nama wilayah/jalan")):
    """Mencari koordinat wilayah via OpenStreetMap Nominatim."""
    try:
        results = FTTHBackendService.geocode(q)
        return {"query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export-kml")
def export_kml(payload: ProjectSaveRequest):
    """Mengekspor seluruh simpul dan jalur kabel jalan ke file KML Google Earth Pro."""
    try:
        kml_str = FTTHBackendService.export_kml_content(
            nodes=payload.nodes,
            cables=payload.cables,
            doc_name=payload.project_name
        )
        return Response(
            content=kml_str,
            media_type="application/vnd.google-earth.kml+xml",
            headers={"Content-Disposition": f'attachment; filename="{payload.project_name}.kml"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal generate file KML: {str(e)}")


@app.post("/api/project/save")
def save_project_state(payload: ProjectSaveRequest):
    """Menghasilkan struktur JSON proyek FTTH siap unduh atau simpan lokal."""
    return {
        "format": "FTTH_NETWORK_PLAN_PROJECT",
        "version": "2.0",
        "project_name": payload.project_name,
        "nodes": [n.model_dump() for n in payload.nodes],
        "cables": [c.model_dump() for c in payload.cables],
        "settings": payload.settings
    }
