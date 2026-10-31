"""
Parser 3D (OBJ, glTF, GLB, STL) para modelos arquitetônicos tridimensionais.
Utiliza a biblioteca trimesh.
"""
from pathlib import Path
from typing import Any
import trimesh
import numpy as np

from structura_ai.cad.models import (
    UnifiedProjectData,
    SpanElement,
    ColumnElement,
    BeamElement,
    Point3D,
    Mesh3DData,
)


def parse_mesh_file(file_path: Path | str, project_name: str = "") -> UnifiedProjectData:
    path = Path(file_path)
    if not project_name:
        project_name = path.stem.replace("_", " ").title()

    try:
        loaded = trimesh.load(str(path))
    except Exception as e:
        raise ValueError(f"Falha ao processar arquivo de malha 3D ({path.suffix}): {e}")

    # Normalizar para lista de meshes se for Scene
    if isinstance(loaded, trimesh.Scene):
        # dump() aplica as transformações dos nós do grafo da cena (geometrias instanciadas
        # em posições distintas) antes de concatenar.
        meshes = [g for g in loaded.dump() if isinstance(g, trimesh.Trimesh)]
        if meshes:
            combined = trimesh.util.concatenate(meshes)
        else:
            combined = trimesh.Trimesh()
    elif isinstance(loaded, trimesh.Trimesh):
        combined = loaded
    else:
        raise ValueError(f"Tipo de geometria 3D não suportado: {type(loaded)}")

    if len(combined.vertices) == 0 or len(combined.faces) == 0:
        raise ValueError(f"Arquivo de malha 3D ({path.suffix}) não contém geometria (vértices/faces) válida")

    bounds = combined.bounds
    if bounds is None or len(bounds) < 2:
        min_pt = np.array([0.0, 0.0, 0.0])
        max_pt = np.array([10.0, 6.0, 3.0])
    else:
        min_pt = bounds[0]
        max_pt = bounds[1]

    dim = max_pt - min_pt
    dx, dy, dz = float(dim[0]), float(dim[1]), float(dim[2])

    # Detectar escala (se veio em mm, cm ou m)
    max_d = max(dx, dy)
    scale = 1.0
    # Limiar 5000: 10-50 m em cm (1000-5000 un) não deve ser lido como mm.
    if max_d > 5000.0:
        scale = 0.001
    elif max_d > 50.0:
        scale = 0.01

    span_x = dx * scale
    span_y = dy * scale
    height_z = dz * scale if dz > 0 else 3.0
    max_span = max(span_x, span_y)
    if max_span < 2.0:
        max_span = 8.0

    # Simplificar malha para transmissão rápida no frontend (máx 5000 faces)
    if len(combined.faces) > 5000:
        try:
            decimated = combined.simplify_quadric_decimation(5000)
        except Exception:
            decimated = combined
    else:
        decimated = combined

    vertices_list = (decimated.vertices * scale).round(3).tolist() if len(decimated.vertices) > 0 else []
    faces_list = decimated.faces.tolist() if len(decimated.faces) > 0 else []

    # Criar representação estrutural aproximada
    beams = [
        BeamElement(
            id="V1",
            name=f"Viga Principal ({round(max_span, 1)}m)",
            start_point=Point3D(x=0.0, y=0.0, z=round(height_z, 2)),
            end_point=Point3D(x=round(max_span, 2), y=0.0, z=round(height_z, 2)),
            span_m=round(max_span, 2),
            width_cm=20.0,
            height_cm=round(max(25.0, max_span * 2.8), 1),
        )
    ]
    spans = [
        SpanElement(
            id="S1",
            name=f"Vão Maior ({round(max_span, 1)}m)",
            start_point=beams[0].start_point,
            end_point=beams[0].end_point,
            length_m=round(max_span, 2),
            beam_id="V1",
        )
    ]
    columns = [
        ColumnElement(id="P1", name="Pilar Esquerdo", position=Point3D(x=0.0, y=0.0, z=0.0), height_m=round(height_z, 2)),
        ColumnElement(id="P2", name="Pilar Direito", position=Point3D(x=round(max_span, 2), y=0.0, z=0.0), height_m=round(height_z, 2)),
    ]

    element_meshes = [
        {"type": "column", "id": "P1", "x": 0.0, "y": 0.0, "z": height_z / 2.0, "dx": 0.2, "dy": 0.4, "dz": height_z, "color": "#64748b"},
        {"type": "column", "id": "P2", "x": max_span, "y": 0.0, "z": height_z / 2.0, "dx": 0.2, "dy": 0.4, "dz": height_z, "color": "#64748b"},
        {"type": "beam", "id": "V1", "x": max_span / 2.0, "y": 0.0, "z": height_z, "dx": max_span, "dy": 0.2, "dz": 0.35, "span": max_span, "color": "#38bdf8"},
    ]

    mesh_3d = Mesh3DData(
        vertices=vertices_list[:12000],
        faces=faces_list[:6000],
        element_meshes=element_meshes,
        bounding_box={
            "min_x": 0.0,
            "max_x": round(max_span, 2),
            "min_y": 0.0,
            "max_y": round(min(span_x, span_y), 2),
            "height_z": round(height_z, 2),
        }
    )

    return UnifiedProjectData(
        project_name=project_name,
        source_format=path.suffix.lstrip(".").lower(),
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
        estimated_dead_load_kn_m=22.0,
        estimated_live_load_kn_m=3.0,
        mesh_3d=mesh_3d,
        metadata={
            "total_vertices": len(decimated.vertices),
            "total_faces": len(decimated.faces),
            "original_bounds_m": [round(float(v), 2) for v in dim * scale],
        }
    )
