"""
Layanan Inti Backend FTTH Network Planner
Menghubungkan endpoint API dengan logika komputasi geospasial OSRM, KML, dan Audit QC.
"""

import os
import tempfile
import urllib.parse
from typing import Any, Dict, List, Tuple
import requests

from ftth_planner.distance import (
    calculate_cable_length_with_slack,
    calculate_geodesic_distance,
    fetch_osrm_road_route,
    split_road_polyline_into_spans,
)
from ftth_planner.models import (
    CableSegment,
    CableType,
    FTTHNode,
    FTTHNodeType,
    KMLExporter,
)
from ftth_planner.project_manager import FTTHProjectManager
from .schemas import (
    AuditRequest,
    AuditResponse,
    AutoPoleRequest,
    AutoPoleResponse,
    CableModel,
    NodeModel,
    RouteRequest,
    RouteResponse,
)


class FTTHBackendService:
    @staticmethod
    def calculate_route(req: RouteRequest) -> RouteResponse:
        """Kalkulasi rute jalan OSRM atau garis lurus."""
        p_a = (req.source_lat, req.source_lng)
        p_b = (req.target_lat, req.target_lng)

        if req.mode == "road":
            try:
                dist, coords = fetch_osrm_road_route(p_a, p_b, timeout_sec=8)
                return RouteResponse(distance_m=dist, path_coordinates=coords, mode_used="road")
            except Exception as e:
                # Fallback ke garis lurus jika OSRM timeout atau tidak ada jaringan
                straight_dist = calculate_geodesic_distance(p_a, p_b)
                return RouteResponse(
                    distance_m=straight_dist,
                    path_coordinates=[p_a, p_b],
                    mode_used="fallback_straight"
                )
        else:
            straight_dist = calculate_geodesic_distance(p_a, p_b)
            return RouteResponse(
                distance_m=straight_dist,
                path_coordinates=[p_a, p_b],
                mode_used="straight"
            )

    @staticmethod
    def generate_auto_poles(req: AutoPoleRequest) -> AutoPoleResponse:
        """Membagi rute kontur jalan menjadi bentangan tiang berinterval presisi."""
        p_a = (req.source_lat, req.source_lng)
        p_b = (req.target_lat, req.target_lng)
        path = req.path_coordinates if req.path_coordinates and len(req.path_coordinates) >= 2 else [p_a, p_b]

        # 1. Hitung total jarak sepanjang polyline
        total_dist = 0.0
        for i in range(len(path) - 1):
            total_dist += calculate_geodesic_distance(path[i], path[i + 1])

        from ftth_planner.distance import calculate_pole_distribution
        num_spans, span_len = calculate_pole_distribution(total_dist, req.spacing_m)

        if len(path) > 2 and num_spans > 1:
            pole_coords, sub_polylines = split_road_polyline_into_spans(path, num_spans)
        else:
            from ftth_planner.distance import interpolate_geodesic_point
            pole_coords = [
                interpolate_geodesic_point(p_a, p_b, i / float(num_spans))
                for i in range(1, num_spans)
            ]
            all_pts = [p_a] + pole_coords + [p_b]
            sub_polylines = [
                [all_pts[k], all_pts[k + 1]] for k in range(num_spans)
            ]

        generated_poles: List[NodeModel] = []
        pole_idx = req.start_pole_num
        for i, (p_lat, p_lng) in enumerate(pole_coords, start=1):
            pole_id = f"POLE-{pole_idx:02d}"
            pole_name = f"Tiang {pole_idx:02d} ({req.source_node_id}➔{req.target_node_id})"
            pole_idx += 1
            dist_along = i * span_len
            node_m = NodeModel(
                id=pole_id,
                name=pole_name,
                infra_type="POLE",
                latitude=p_lat,
                longitude=p_lng,
                capacity="Tiang Tumpu 7m",
                notes=f"Auto-generated di rute jalan: {dist_along:.1f}m dari {req.source_node_id}"
            )
            generated_poles.append(node_m)

        # Rangkaian seluruh titik simpul
        chain_models = [
            (req.source_node_id, req.source_node_name, req.source_lat, req.source_lng)
        ] + [
            (p.id, p.name, p.latitude, p.longitude) for p in generated_poles
        ] + [
            (req.target_node_id, req.target_node_name, req.target_lat, req.target_lng)
        ]

        generated_cables: List[CableModel] = []
        cable_idx = req.start_cable_num
        total_cable_len = 0.0

        for j in range(len(chain_models) - 1):
            s_id, s_name, s_lat, s_lng = chain_models[j]
            t_id, t_name, t_lat, t_lng = chain_models[j + 1]
            seg_path = sub_polylines[j] if j < len(sub_polylines) else [(s_lat, s_lng), (t_lat, t_lng)]

            seg_span_m = 0.0
            for v in range(len(seg_path) - 1):
                seg_span_m += calculate_geodesic_distance(seg_path[v], seg_path[v + 1])

            total_seg_len = calculate_cable_length_with_slack(seg_span_m, req.slack_percent)
            total_cable_len += total_seg_len

            cab_model = CableModel(
                id=f"CAB-{cable_idx:03d}",
                name=f"Kabel {s_id} ke {t_id}",
                cable_type=req.cable_type,
                source_node_id=s_id,
                source_node_name=s_name,
                source_lat=s_lat,
                source_lng=s_lng,
                target_node_id=t_id,
                target_node_name=t_name,
                target_lat=t_lat,
                target_lng=t_lng,
                span_distance_m=round(seg_span_m, 2),
                slack_percent=req.slack_percent,
                total_length_m=round(total_seg_len, 2),
                core_count=req.core_count,
                notes=f"Bentangan otomatis {seg_span_m:.1f}m",
                path_coordinates=seg_path
            )
            generated_cables.append(cab_model)
            cable_idx += 1

        return AutoPoleResponse(
            generated_poles=generated_poles,
            generated_cables=generated_cables,
            total_spans=len(generated_cables),
            total_cable_length_m=round(total_cable_len, 2)
        )

    @staticmethod
    def audit_quality_control(req: AuditRequest) -> AuditResponse:
        """Menjalankan audit quality control span jarak dan kelayakan KML."""
        findings = []
        total_span = sum(c.span_distance_m for c in req.cables)
        total_real = sum(c.total_length_m for c in req.cables)
        total_slack = total_real - total_span

        poles_count = sum(1 for n in req.nodes if "POLE" in n.infra_type.upper() or "TIANG" in n.infra_type.upper())
        odp_count = sum(1 for n in req.nodes if "ODP" in n.infra_type.upper())
        odc_count = sum(1 for n in req.nodes if "ODC" in n.infra_type.upper())

        span_over_cnt = 0
        span_under_cnt = 0

        # Validasi setiap bentangan kabel
        for cable in req.cables:
            if cable.span_distance_m > req.max_span_m:
                span_over_cnt += 1
                findings.append({
                    "severity": "WARNING",
                    "category": "Bentangan Melebihi Batas",
                    "target_id": cable.id,
                    "metric_value": f"{cable.span_distance_m:.1f} m",
                    "description": f"Bentangan {cable.source_node_id} -> {cable.target_node_id} ({cable.span_distance_m:.1f} m) melebihi batas maksimal {req.max_span_m} m.",
                    "recommendation": "Sisipkan tiang sisipan di tengah rentang jalan ini."
                })
            elif cable.span_distance_m < req.min_span_m and cable.span_distance_m > 0:
                span_under_cnt += 1
                findings.append({
                    "severity": "INFO",
                    "category": "Bentangan Terlalu Rapat",
                    "target_id": cable.id,
                    "metric_value": f"{cable.span_distance_m:.1f} m",
                    "description": f"Bentangan {cable.source_node_id} -> {cable.target_node_id} ({cable.span_distance_m:.1f} m) kurang dari {req.min_span_m} m.",
                    "recommendation": "Pertimbangkan menggabungkan simpul untuk efisiensi biaya material."
                })

        is_export_ready = len(req.nodes) >= 2 and len(req.cables) >= 1

        if not is_export_ready:
            findings.insert(0, {
                "severity": "CRITICAL",
                "category": "Infrastruktur Belum Lengkap",
                "target_id": "GLOBAL",
                "metric_value": f"{len(req.nodes)} simpul, {len(req.cables)} kabel",
                "description": "Desain memerlukan minimal 2 simpul dan 1 rute kabel aktif untuk diekspor.",
                "recommendation": "Tambahkan simpul dan hubungkan kabel terlebih dahulu."
            })
            status_summary = "CRITICAL: Data desain belum memenuhi syarat minimal ekspor."
        elif span_over_cnt > 0:
            status_summary = f"WARNING: Terdapat {span_over_cnt} bentangan kabel melebihi rekomendasi teknis ({req.max_span_m}m)."
        else:
            status_summary = "PASS: Seluruh parameter topologi jaringan memenuhi standar teknis FTTH."

        return AuditResponse(
            total_nodes=len(req.nodes),
            total_poles=poles_count,
            total_odp=odp_count,
            total_odc=odc_count,
            total_cables=len(req.cables),
            total_span_distance_m=round(total_span, 2),
            total_slack_meter=round(total_slack, 2),
            total_real_cable_m=round(total_real, 2),
            span_over_limit_count=span_over_cnt,
            span_under_limit_count=span_under_cnt,
            findings=findings,
            is_export_ready=is_export_ready,
            status_summary=status_summary
        )

    @staticmethod
    def geocode(query: str) -> List[Dict[str, Any]]:
        """Mencari wilayah via OpenStreetMap Nominatim."""
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(query)}&limit=5&countrycodes=id"
        headers = {"User-Agent": "FTTHPlannerHybridApp/2.0"}
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            return resp.json()
        return []

    @staticmethod
    def export_kml_content(nodes: List[NodeModel], cables: List[CableModel], doc_name: str = "FTTH Network") -> str:
        """Mengekspor data menjadi string XML KML murni."""
        domain_nodes = [
            FTTHNode(
                id=n.id,
                name=n.name,
                infra_type=FTTHNodeType.from_string(n.infra_type),
                latitude=n.latitude,
                longitude=n.longitude,
                capacity=n.capacity,
                notes=n.notes
            )
            for n in nodes
        ]

        domain_cables = [
            CableSegment(
                id=c.id,
                name=c.name,
                cable_type=CableType.from_string(c.cable_type),
                source_node_id=c.source_node_id,
                source_node_name=c.source_node_name,
                source_lat=c.source_lat,
                source_lng=c.source_lng,
                target_node_id=c.target_node_id,
                target_node_name=c.target_node_name,
                target_lat=c.target_lat,
                target_lng=c.target_lng,
                span_distance_m=c.span_distance_m,
                slack_percent=c.slack_percent,
                total_length_m=c.total_length_m,
                core_count=c.core_count,
                notes=c.notes,
                path_coordinates=c.path_coordinates
            )
            for c in cables
        ]

        with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            KMLExporter.export(domain_nodes, domain_cables, tmp_path, doc_name)
            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
