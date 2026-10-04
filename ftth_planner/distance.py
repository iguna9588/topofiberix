"""
Modul Kalkulasi Jarak Geospasial, Road-Snapped Routing & Algoritma Interpolasi Rute FTTH
Menyediakan kalkulasi jarak geodesik presisi tinggi (WGS-84), perhitungan slack kabel,
integrasi layanan routing jalan raya (OSRM Road-Snapped Routing), serta algoritma
interpolasi tiang perantara di sepanjang jalur kontur jalan raya.
"""

import json
import math
import urllib.parse
import urllib.request
from typing import List, Optional, Tuple


def calculate_geodesic_distance(point_a: Tuple[float, float], point_b: Tuple[float, float]) -> float:
    """
    Menghitung jarak bentangan langsung (spasial) antara dua koordinat dalam satuan meter.
    point_a, point_b: Tuple (latitude, longitude)
    Menggunakan ellipsoida WGS-84 dari geopy, atau formula Haversine sebagai fallback.
    """
    lat1, lon1 = point_a
    lat2, lon2 = point_b

    # Jika koordinat persis sama
    if abs(lat1 - lat2) < 1e-9 and abs(lon1 - lon2) < 1e-9:
        return 0.0

    try:
        from geopy.distance import geodesic
        return float(geodesic((lat1, lon1), (lat2, lon2)).meters)
    except Exception:
        # Fallback Haversine Formula (Radius bumi = 6,371,000 meter)
        return haversine_distance(lat1, lon1, lat2, lon2)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Menghitung jarak lengkung lingkaran besar bola bumi menggunakan rumus Haversine.
    Hasil dalam satuan meter.
    """
    R = 6371000.0  # Radius bumi rata-rata dalam meter

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2

    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


def calculate_cable_length_with_slack(span_distance_m: float, slack_percent: float = 10.0) -> float:
    """
    Menghitung total panjang riil kabel di lapangan dengan memperhitungkan persentase
    cadangan kabel (slack / looping tiang & terminasi closure/ODP).
    Rumus: Total = Bentangan * (1 + Slack / 100)
    """
    if span_distance_m < 0:
        return 0.0
    slack_factor = max(0.0, slack_percent) / 100.0
    return span_distance_m * (1.0 + slack_factor)


def interpolate_geodesic_point(
    point_a: Tuple[float, float],
    point_b: Tuple[float, float],
    fraction: float
) -> Tuple[float, float]:
    """
    Menghitung koordinat perantara (Latitude, Longitude) pada fraksi jarak (0.0 s/d 1.0)
    sepanjang garis busur lingkaran besar (Great Circle / Geodesic) antara Titik A dan B.
    """
    if fraction <= 0.0:
        return point_a
    if fraction >= 1.0:
        return point_b

    lat1_r = math.radians(point_a[0])
    lon1_r = math.radians(point_a[1])
    lat2_r = math.radians(point_b[0])
    lon2_r = math.radians(point_b[1])

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = math.sin(dlat / 2.0) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2.0) ** 2
    delta = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))

    if delta < 1e-12:
        return point_a

    sin_delta = math.sin(delta)
    weight_a = math.sin((1.0 - fraction) * delta) / sin_delta
    weight_b = math.sin(fraction * delta) / sin_delta

    x = weight_a * math.cos(lat1_r) * math.cos(lon1_r) + weight_b * math.cos(lat2_r) * math.cos(lon2_r)
    y = weight_a * math.cos(lat1_r) * math.sin(lon1_r) + weight_b * math.cos(lat2_r) * math.sin(lon2_r)
    z = weight_a * math.sin(lat1_r) + weight_b * math.sin(lat2_r)

    lat_interp = math.atan2(z, math.sqrt(x * x + y * y))
    lon_interp = math.atan2(y, x)

    return (math.degrees(lat_interp), math.degrees(lon_interp))


def calculate_pole_distribution(
    total_distance_m: float,
    max_span_distance_m: float = 100.0
) -> Tuple[int, float]:
    """
    Menghitung jumlah rentang (span) dan jarak rentang efektif agar tidak melebihi max_span.
    """
    if total_distance_m <= 0.0 or max_span_distance_m <= 0.0:
        return (1, 0.0)

    num_spans = max(1, math.ceil(total_distance_m / max_span_distance_m))
    span_distance = total_distance_m / num_spans

    return (num_spans, span_distance)


# ==============================================================================
# FITUR ROAD-SNAPPED ROUTING BERBASIS OPENSTREETMAP (OSRM)
# ==============================================================================

def fetch_osrm_road_route(
    point_a: Tuple[float, float],
    point_b: Tuple[float, float],
    timeout_sec: int = 8
) -> Tuple[float, List[Tuple[float, float]]]:
    """
    Mengambil geometri rute jalan raya dari layanan OpenStreetMap OSRM API publik.
    
    Parameters:
        point_a: Tuple (lat1, lon1) - Titik Asal
        point_b: Tuple (lat2, lon2) - Titik Tujuan
        
    Returns:
        Tuple[total_road_distance_meter, list_of_lat_lng_tuples]
        Jika terjadi kegagalan jaringan, otomatis fallback ke garis lurus.
    """
    lat1, lon1 = point_a
    lat2, lon2 = point_b

    # Format OSRM: /route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson
    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{lon1:.7f},{lat1:.7f};{lon2:.7f},{lat2:.7f}"
        f"?overview=full&geometries=geojson"
    )

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "FTTHNetworkPlanner/2.0 (OSRM Road Routing)"}
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            data = json.loads(response.read().decode())

            if data.get("code") == "Ok" and data.get("routes"):
                best_route = data["routes"][0]
                total_distance = float(best_route.get("distance", 0.0))
                # GeoJSON coordinates format: [[lon, lat], [lon, lat], ...]
                raw_coords = best_route.get("geometry", {}).get("coordinates", [])

                # Konversi menjadi format Python [(lat, lon), (lat, lon), ...]
                path_lat_lng = [(float(c[1]), float(c[0])) for c in raw_coords]

                if path_lat_lng:
                    return (total_distance, path_lat_lng)

    except Exception as e:
        # Fallback graceful jika jaringan offline / timeout / server sibuk
        pass

    # Fallback ke garis lurus jika rute jalan tidak dapat diakses
    straight_distance = calculate_geodesic_distance(point_a, point_b)
    return (straight_distance, [point_a, point_b])


def interpolate_along_polyline(
    polyline: List[Tuple[float, float]],
    target_distance: float
) -> Tuple[float, float]:
    """
    Menghitung koordinat (Latitude, Longitude) pada jarak kumulatif tertentu
    di sepanjang polyline rute jalan raya.
    """
    if not polyline:
        return (0.0, 0.0)
    if len(polyline) == 1 or target_distance <= 0.0:
        return polyline[0]

    accumulated = 0.0
    for i in range(len(polyline) - 1):
        p1 = polyline[i]
        p2 = polyline[i + 1]
        seg_dist = calculate_geodesic_distance(p1, p2)

        if accumulated + seg_dist >= target_distance:
            # Titik target berada di antara p1 dan p2 pada segmen ini
            remaining = target_distance - accumulated
            fraction = remaining / seg_dist if seg_dist > 0.0 else 0.0
            return interpolate_geodesic_point(p1, p2, fraction)

        accumulated += seg_dist

    # Jika target_distance melebihi panjang total polyline, kembalikan titik terakhir
    return polyline[-1]


def split_road_polyline_into_spans(
    polyline: List[Tuple[float, float]],
    num_spans: int
) -> Tuple[List[Tuple[float, float]], List[List[Tuple[float, float]]]]:
    """
    Membagi polyline rute jalan menjadi rentang-rentang kabel proporsional:
    1. Menghitung posisi tiang perantara tepat di kontur jalan.
    2. Memotong polyline jalan menjadi sub-polyline untuk masing-masing segmen kabel
       sehingga setiap segmen kabel melengkung sempurna mengikuti jalan.
       
    Returns:
        Tuple[
            intermediate_pole_coordinates: List[(lat, lon)],
            span_sub_polylines: List[List[(lat, lon)]]
        ]
    """
    if len(polyline) < 2 or num_spans <= 1:
        return ([], [polyline])

    # 1. Hitung total panjang dan jarak kumulatif per vertex polyline
    cum_distances = [0.0]
    total_dist = 0.0
    for i in range(len(polyline) - 1):
        d = calculate_geodesic_distance(polyline[i], polyline[i + 1])
        total_dist += d
        cum_distances.append(total_dist)

    span_dist = total_dist / num_spans

    # 2. Hitung posisi tiang perantara (intermediate poles)
    intermediate_poles = []
    target_distances = [span_dist * i for i in range(1, num_spans)]

    for td in target_distances:
        pt = interpolate_along_polyline(polyline, td)
        intermediate_poles.append(pt)

    # 3. Potong polyline jalan menjadi segmen-segmen rentang (sub-polylines)
    # Target jarak pembatas rentang: [0.0, span_dist, 2*span_dist, ..., total_dist]
    all_cut_distances = [0.0] + target_distances + [total_dist]
    all_cut_points = [polyline[0]] + intermediate_poles + [polyline[-1]]

    sub_polylines: List[List[Tuple[float, float]]] = []

    for s in range(num_spans):
        dist_start = all_cut_distances[s]
        dist_end = all_cut_distances[s + 1]
        pt_start = all_cut_points[s]
        pt_end = all_cut_points[s + 1]

        seg_points = [pt_start]

        # Sisipkan semua vertex asli jalan raya yang berada di antara dist_start dan dist_end
        for v_idx in range(len(polyline)):
            v_dist = cum_distances[v_idx]
            if dist_start < v_dist < dist_end:
                seg_points.append(polyline[v_idx])

        seg_points.append(pt_end)
        sub_polylines.append(seg_points)

    return (intermediate_poles, sub_polylines)
