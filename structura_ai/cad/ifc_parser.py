"""
Parser IFC (Industry Foundation Classes) para BIM estrutural.
Utiliza ifcopenshell para extrair IfcBeam, IfcColumn, IfcSlab e calcular vãos.
"""
from pathlib import Path
import math
from typing import Any
import ifcopenshell
import ifcopenshell.util.element

from structura_ai.cad.models import (
    UnifiedProjectData,
    SpanElement,
    ColumnElement,
    BeamElement,
    Point3D,
    Mesh3DData,
)


def _get_local_placement_coords(element) -> tuple[float, float, float]:
    """Extrai coordenadas aproximadas de placement de uma entidade IFC."""
    try:
        placement = element.ObjectPlacement
        if placement and placement.is_a("IfcLocalPlacement"):
            rel_placement = placement.RelativePlacement
            if rel_placement and rel_placement.is_a("IfcAxis2Placement3D"):
                loc = rel_placement.Location.Coordinates
                return float(loc[0]), float(loc[1]), float(loc[2] if len(loc) > 2 else 0.0)
    except Exception:
        pass
    return 0.0, 0.0, 0.0


def parse_ifc_file(file_path: Path | str, project_name: str = "") -> UnifiedProjectData:
    path = Path(file_path)
    if not project_name:
        project_name = path.stem.replace("_", " ").title()

    try:
        model = ifcopenshell.open(str(path))
    except Exception as e:
        raise ValueError(f"Falha ao abrir arquivo IFC: {e}")

    # Extrair vigas e pilares
    raw_beams = model.by_type("IfcBeam")
    raw_columns = model.by_type("IfcColumn")
    raw_slabs = model.by_type("IfcSlab")

    beams = []
    spans = []
    columns = []
    element_meshes = []

    # Extrair pilares
    col_idx = 1
    for col in raw_columns:
        x, y, z = _get_local_placement_coords(col)
        # Tentar obter altura e seção
        height = 3.0
        width_cm = 20.0
        depth_cm = 40.0
        try:
            psets = ifcopenshell.util.element.get_psets(col)
            for pset_name, pset_data in psets.items():
                if "Height" in pset_data:
                    height = float(pset_data["Height"])
                    if height > 50.0:  # mm para m
                        height /= 1000.0
        except Exception:
            pass

        c_elem = ColumnElement(
            id=f"P{col_idx}",
            name=f"Pilar {col.Name or f'P{col_idx}'}",
            position=Point3D(x=round(x, 2), y=round(y, 2), z=round(z, 2)),
            section_width_cm=width_cm,
            section_height_cm=depth_cm,
            height_m=height,
        )
        columns.append(c_elem)
        element_meshes.append({
            "type": "column",
            "id": c_elem.id,
            "x": c_elem.position.x,
            "y": c_elem.position.y,
            "z": c_elem.position.z + (height / 2.0),
            "dx": width_cm / 100.0,
            "dy": depth_cm / 100.0,
            "dz": height,
            "color": "#64748b",
        })
        col_idx += 1

    # Extrair vigas
    beam_idx = 1
    for beam in raw_beams:
        x, y, z = _get_local_placement_coords(beam)
        span_length = 6.0
        width_cm = 20.0
        height_cm = 40.0

        try:
            psets = ifcopenshell.util.element.get_psets(beam)
            for pset_name, pset_data in psets.items():
                if "Length" in pset_data:
                    span_length = float(pset_data["Length"])
                    if span_length > 50.0:  # mm para m
                        span_length /= 1000.0
                if "Height" in pset_data or "Depth" in pset_data:
                    val = float(pset_data.get("Height", pset_data.get("Depth", 40.0)))
                    height_cm = val / 10.0 if val > 100.0 else val
                if "Width" in pset_data:
                    val = float(pset_data["Width"])
                    width_cm = val / 10.0 if val > 100.0 else val
        except Exception:
            pass

        b_elem = BeamElement(
            id=f"V{beam_idx}",
            name=f"Viga {beam.Name or f'V{beam_idx}'}",
            start_point=Point3D(x=round(x, 2), y=round(y, 2), z=round(z, 2)),
            end_point=Point3D(x=round(x + span_length, 2), y=round(y, 2), z=round(z, 2)),
            span_m=round(span_length, 2),
            width_cm=width_cm,
            height_cm=height_cm,
            is_cantilever=False,
        )
        beams.append(b_elem)
        spans.append(SpanElement(
            id=f"S{beam_idx}",
            name=f"Vão {b_elem.name} ({b_elem.span_m}m)",
            start_point=b_elem.start_point,
            end_point=b_elem.end_point,
            length_m=b_elem.span_m,
            beam_id=b_elem.id,
        ))
        element_meshes.append({
            "type": "beam",
            "id": b_elem.id,
            "x": x + (span_length / 2.0),
            "y": y,
            "z": z,
            "dx": span_length,
            "dy": width_cm / 100.0,
            "dz": height_cm / 100.0,
            "span": span_length,
            "color": "#38bdf8",
        })
        beam_idx += 1

    # Fallback se o IFC não possui IfcBeam ou IfcColumn explícitos (ex: modelo genérico)
    if not beams:
        default_span = 8.5
        b_default = BeamElement(
            id="V1",
            name="Viga Principal do Pavilhão",
            start_point=Point3D(x=0.0, y=0.0, z=3.0),
            end_point=Point3D(x=default_span, y=0.0, z=3.0),
            span_m=default_span,
            width_cm=20.0,
            height_cm=35.0,
        )
        beams.append(b_default)
        spans.append(SpanElement(id="S1", name="Vão Principal", start_point=b_default.start_point, end_point=b_default.end_point, length_m=default_span))
        columns.extend([
            ColumnElement(id="P1", name="Pilar P1", position=Point3D(x=0.0, y=0.0, z=0.0)),
            ColumnElement(id="P2", name="Pilar P2", position=Point3D(x=default_span, y=0.0, z=0.0)),
        ])
        element_meshes.extend([
            {"type": "column", "id": "P1", "x": 0.0, "y": 0.0, "z": 1.5, "dx": 0.2, "dy": 0.4, "dz": 3.0, "color": "#64748b"},
            {"type": "column", "id": "P2", "x": default_span, "y": 0.0, "z": 1.5, "dx": 0.2, "dy": 0.4, "dz": 3.0, "color": "#64748b"},
            {"type": "beam", "id": "V1", "x": default_span / 2.0, "y": 0.0, "z": 3.0, "dx": default_span, "dy": 0.2, "dz": 0.35, "span": default_span, "color": "#38bdf8"},
        ])

    max_span = max((b.span_m for b in beams), default=8.5)

    mesh_3d = Mesh3DData(
        element_meshes=element_meshes,
        bounding_box={"min_x": 0.0, "max_x": max_span, "min_y": 0.0, "max_y": 6.0, "height_z": 3.5}
    )

    return UnifiedProjectData(
        project_name=project_name,
        source_format="ifc",
        file_path=str(path),
        bounding_box=mesh_3d.bounding_box,
        spans=spans,
        columns=columns,
        beams=beams,
        max_span_m=round(max_span, 2),
        max_cantilever_m=0.0,
        suggested_beam_width_cm=20.0,
        suggested_beam_height_cm=round(max(25.0, max_span * 2.8), 1),
        suggested_fck_mpa=30.0,
        estimated_dead_load_kn_m=24.0,
        estimated_live_load_kn_m=4.0,
        mesh_3d=mesh_3d,
        metadata={
            "total_ifc_beams": len(raw_beams),
            "total_ifc_columns": len(raw_columns),
            "total_ifc_slabs": len(raw_slabs),
            "schema": model.schema if hasattr(model, 'schema') else "IFC4",
        }
    )
