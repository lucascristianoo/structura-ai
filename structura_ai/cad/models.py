"""
Modelos de dados unificados para representação geométrica e estrutural CAD/BIM.
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class Point3D(BaseModel):
    x: float
    y: float
    z: float = 0.0


class SpanElement(BaseModel):
    id: str
    name: str = "Vão"
    start_point: Point3D
    end_point: Point3D
    length_m: float
    is_cantilever: bool = False
    beam_id: Optional[str] = None


class ColumnElement(BaseModel):
    id: str
    name: str = "Pilar"
    position: Point3D
    section_width_cm: float = 20.0
    section_height_cm: float = 40.0
    height_m: float = 3.0


class BeamElement(BaseModel):
    id: str
    name: str = "Viga"
    start_point: Point3D
    end_point: Point3D
    span_m: float
    width_cm: float = 20.0
    height_cm: float = 30.0
    is_cantilever: bool = False
    distributed_load_kn_m: float = 25.0


class Mesh3DData(BaseModel):
    vertices: list[list[float]] = Field(default_factory=list)
    faces: list[list[int]] = Field(default_factory=list)
    element_meshes: list[dict[str, Any]] = Field(default_factory=list)
    bounding_box: dict[str, float] = Field(default_factory=dict)


class UnifiedProjectData(BaseModel):
    project_name: str
    source_format: str  # "dxf", "ifc", "obj", "gltf", "plugin", "canvas"
    file_path: Optional[str] = None
    bounding_box: dict[str, float] = Field(default_factory=lambda: {"min_x": 0.0, "max_x": 10.0, "min_y": 0.0, "max_y": 10.0, "height_z": 3.0})
    spans: list[SpanElement] = Field(default_factory=list)
    columns: list[ColumnElement] = Field(default_factory=list)
    beams: list[BeamElement] = Field(default_factory=list)
    max_span_m: float = 10.0
    max_cantilever_m: float = 0.0
    suggested_beam_width_cm: float = 20.0
    suggested_beam_height_cm: float = 30.0
    suggested_fck_mpa: float = 30.0
    estimated_dead_load_kn_m: float = 22.0
    estimated_live_load_kn_m: float = 3.0
    mesh_3d: Optional[Mesh3DData] = None
    raw_2d_entities: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
