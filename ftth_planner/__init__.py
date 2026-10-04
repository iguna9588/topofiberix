"""
FTTH Network Planner - Modul 1 & Modul 2:
- Modul 1: Geographic Information System (GIS) & Spatial Survey
- Modul 2: Cable Routing Calculation, Slack Management & Google Earth KML
"""

from .main_window import FTTHMainWindow
from .models import CableSegment, CableType, FTTHNode, FTTHNodeType, KMLExporter
from .distance import (
    calculate_cable_length_with_slack,
    calculate_geodesic_distance,
    calculate_pole_distribution,
    fetch_osrm_road_route,
    interpolate_geodesic_point,
    split_road_polyline_into_spans,
)

__all__ = [
    "FTTHMainWindow",
    "FTTHNode",
    "FTTHNodeType",
    "CableSegment",
    "CableType",
    "KMLExporter",
    "calculate_geodesic_distance",
    "calculate_cable_length_with_slack",
    "interpolate_geodesic_point",
    "calculate_pole_distribution",
    "fetch_osrm_road_route",
    "split_road_polyline_into_spans",
]
