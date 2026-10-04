"""
Pydantic Schemas untuk Validasi Data API Backend FTTH Network Planner
"""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class NodeModel(BaseModel):
    id: str
    name: str
    infra_type: str = "ODP"
    latitude: float
    longitude: float
    capacity: str = "N/A"
    notes: str = ""
    created_at: Optional[str] = None


class CableModel(BaseModel):
    id: str
    name: str
    cable_type: str = "Kabel Distribusi (ODC ke ODP)"
    source_node_id: str
    source_node_name: str
    source_lat: float
    source_lng: float
    target_node_id: str
    target_node_name: str
    target_lat: float
    target_lng: float
    span_distance_m: float
    slack_percent: float = 10.0
    total_length_m: float
    core_count: str = "24 Core"
    notes: str = ""
    path_coordinates: List[Tuple[float, float]] = Field(default_factory=list)
    created_at: Optional[str] = None


class RouteRequest(BaseModel):
    source_lat: float
    source_lng: float
    target_lat: float
    target_lng: float
    mode: str = "road"  # "road" atau "straight"


class RouteResponse(BaseModel):
    distance_m: float
    path_coordinates: List[Tuple[float, float]]
    mode_used: str


class AutoPoleRequest(BaseModel):
    source_node_id: str
    source_node_name: str
    source_lat: float
    source_lng: float
    target_node_id: str
    target_node_name: str
    target_lat: float
    target_lng: float
    spacing_m: float = 80.0
    slack_percent: float = 10.0
    cable_type: str = "Kabel Distribusi (ODC ke ODP)"
    core_count: str = "24 Core"
    path_coordinates: List[Tuple[float, float]] = Field(default_factory=list)
    start_pole_num: int = 1
    start_cable_num: int = 1


class AutoPoleResponse(BaseModel):
    generated_poles: List[NodeModel]
    generated_cables: List[CableModel]
    total_spans: int
    total_cable_length_m: float


class AuditRequest(BaseModel):
    nodes: List[NodeModel]
    cables: List[CableModel]
    max_span_m: float = 120.0
    min_span_m: float = 25.0


class AuditResponse(BaseModel):
    total_nodes: int
    total_poles: int
    total_odp: int
    total_odc: int
    total_cables: int
    total_span_distance_m: float
    total_slack_meter: float
    total_real_cable_m: float
    span_over_limit_count: int
    span_under_limit_count: int
    findings: List[Dict[str, Any]]
    is_export_ready: bool
    status_summary: str


class ProjectSaveRequest(BaseModel):
    project_name: str = "Proyek_FTTH"
    nodes: List[NodeModel]
    cables: List[CableModel]
    settings: Dict[str, Any] = Field(default_factory=dict)


class GeocodeRequest(BaseModel):
    query: str
