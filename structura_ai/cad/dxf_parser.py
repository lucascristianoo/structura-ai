"""
Parser DXF para extração de entidades estruturais (Vigas, Pilares, Vãos, Cotas).
Utiliza a biblioteca ezdxf.
"""
from pathlib import Path
import math
from typing import Any
import ezdxf
from ezdxf.entities import Line, LWPolyline, Text, MText

from structura_ai.cad.models import (
    UnifiedProjectData,
    SpanElement,
    ColumnElement,
    BeamElement,
    Point3D,
    Mesh3DData,
)


def parse_dxf_file(file_path: Path | str, project_name: str = "") -> UnifiedProjectData:
    path = Path(file_path)
    if not project_name:
        project_name = path.stem.replace("_", " ").title()

    try:
        doc = ezdxf.readfile(str(path))
        msp = doc.modelspace()
    except Exception as e:
        # Fallback para parsing resiliente
        raise ValueError(f"Não foi possível ler o arquivo DXF: {e}")

    # Coleta de entidades brutas
    lines_raw = []
    texts_raw = []
    all_points = []

    for entity in msp:
        layer_name = (entity.dxf.layer or "").upper()
        if entity.dxftype() == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            lines_raw.append({
                "layer": layer_name,
                "start": (float(start.x), float(start.y), float(start.z if hasattr(start, 'z') else 0.0)),
                "end": (float(end.x), float(end.y), float(end.z if hasattr(end, 'z') else 0.0)),
            })
            all_points.extend([(float(start.x), float(start.y)), (float(end.x), float(end.y))])

        elif entity.dxftype() == "LWPOLYLINE":
            pts = list(entity.get_points())
            for i in range(len(pts) - 1):
                p1, p2 = pts[i], pts[i + 1]
                lines_raw.append({
                    "layer": layer_name,
                    "start": (float(p1[0]), float(p1[1]), 0.0),
                    "end": (float(p2[0]), float(p2[1]), 0.0),
                })
                all_points.extend([(float(p1[0]), float(p1[1])), (float(p2[0]), float(p2[1]))])

        elif entity.dxftype() in ("TEXT", "MTEXT"):
            insert = entity.dxf.insert if hasattr(entity.dxf, 'insert') else (0, 0, 0)
            text_val = entity.dxf.text if hasattr(entity.dxf, 'text') else str(getattr(entity, 'text', ''))
            texts_raw.append({
                "text": text_val,
                "layer": layer_name,
                "position": (float(insert[0]), float(insert[1]), float(insert[2] if len(insert) > 2 else 0.0)),
            })

    if not all_points:
        # DXF vazio ou sem linhas reconhecidas
        return UnifiedProjectData(
            project_name=project_name,
            source_format="dxf",
            file_path=str(path),
            spans=[SpanElement(id="S1", start_point=Point3D(x=0, y=0, z=0), end_point=Point3D(x=10, y=0, z=0), length_m=10.0)],
            columns=[
                ColumnElement(id="P1", position=Point3D(x=0, y=0, z=0)),
                ColumnElement(id="P2", position=Point3D(x=10, y=0, z=0)),
            ],
            beams=[BeamElement(id="V1", start_point=Point3D(x=0, y=0, z=0), end_point=Point3D(x=10, y=0, z=0), span_m=10.0)],
            max_span_m=10.0,
        )

    # Detectar escala (mm, cm ou metros)
    min_x = min(p[0] for p in all_points)
    max_x = max(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)
    max_y = max(p[1] for p in all_points)

    dim_x = max_x - min_x
    dim_y = max_y - min_y
    max_dim = max(dim_x, dim_y)

    scale_to_meters = 1.0
    if max_dim > 500.0:  # Provavelmente em milímetros
        scale_to_meters = 0.001
    elif max_dim > 50.0:  # Provavelmente em centímetros
        scale_to_meters = 0.01

    # Normalizar linhas para metros centradas em 0,0
    scaled_lines = []
    beams = []
    spans = []
    columns_map = {}

    beam_idx = 1
    span_idx = 1
    col_idx = 1

    for line in lines_raw:
        x1 = (line["start"][0] - min_x) * scale_to_meters
        y1 = (line["start"][1] - min_y) * scale_to_meters
        x2 = (line["end"][0] - min_x) * scale_to_meters
        y2 = (line["end"][1] - min_y) * scale_to_meters
        length = math.hypot(x2 - x1, y2 - y1)

        layer = line["layer"]
        is_structural = any(k in layer for k in ["VIGA", "BEAM", "ESTRUT", "STRUCT", "FRAME"])
        is_column_layer = any(k in layer for k in ["PILAR", "COLUMN", "COL"])

        scaled_lines.append({
            "x1": round(x1, 3),
            "y1": round(y1, 3),
            "x2": round(x2, 3),
            "y2": round(y2, 3),
            "length": round(length, 3),
            "layer": layer,
            "is_structural": is_structural,
        })

        if is_column_layer:
            k = (round(x1, 1), round(y1, 1))
            if k not in columns_map:
                columns_map[k] = ColumnElement(
                    id=f"P{col_idx}",
                    name=f"Pilar P{col_idx}",
                    position=Point3D(x=round(x1, 2), y=round(y1, 2), z=0.0),
                    section_width_cm=20.0,
                    section_height_cm=40.0,
                    height_m=3.0,
                )
                col_idx += 1

        if (is_structural or length >= 3.0) and length <= 50.0:
            beam_id = f"V{beam_idx}"
            b = BeamElement(
                id=beam_id,
                name=f"Viga {beam_id}",
                start_point=Point3D(x=round(x1, 2), y=round(y1, 2), z=3.0),
                end_point=Point3D(x=round(x2, 2), y=round(y2, 2), z=3.0),
                span_m=round(length, 2),
                width_cm=20.0,
                height_cm=30.0,
                is_cantilever=False,
            )
            beams.append(b)
            spans.append(SpanElement(
                id=f"S{span_idx}",
                name=f"Vão {span_idx} ({round(length, 2)}m)",
                start_point=b.start_point,
                end_point=b.end_point,
                length_m=round(length, 2),
                beam_id=beam_id,
            ))
            beam_idx += 1
            span_idx += 1

    # Se não identificou pilares por layer, gerar nos extremos dos maiores vãos
    if not columns_map and beams:
        for b in beams[:4]:
            k1 = (round(b.start_point.x, 1), round(b.start_point.y, 1))
            k2 = (round(b.end_point.x, 1), round(b.end_point.y, 1))
            for k, pt in [(k1, b.start_point), (k2, b.end_point)]:
                if k not in columns_map:
                    columns_map[k] = ColumnElement(
                        id=f"P{col_idx}",
                        name=f"Pilar P{col_idx}",
                        position=Point3D(x=pt.x, y=pt.y, z=0.0),
                        section_width_cm=20.0,
                        section_height_cm=40.0,
                        height_m=3.0,
                    )
                    col_idx += 1

    # Ordenar e encontrar o vão crítico
    columns = list(columns_map.values())
    max_span = max((s.length_m for s in spans), default=10.0)

    # Gerar malhas 3D para o Three.js
    element_meshes = []
    # Mesh pilares (caixas 3D)
    for c in columns:
        element_meshes.append({
            "type": "column",
            "id": c.id,
            "x": c.position.x,
            "y": c.position.y,
            "z": c.height_m / 2.0,
            "dx": c.section_width_cm / 100.0,
            "dy": c.section_height_cm / 100.0,
            "dz": c.height_m,
            "color": "#64748b",
        })
    # Mesh vigas
    for b in beams:
        cx = (b.start_point.x + b.end_point.x) / 2.0
        cy = (b.start_point.y + b.end_point.y) / 2.0
        cz = 3.0 - (b.height_cm / 200.0)
        dx = abs(b.end_point.x - b.start_point.x) or (b.width_cm / 100.0)
        dy = abs(b.end_point.y - b.start_point.y) or (b.width_cm / 100.0)
        element_meshes.append({
            "type": "beam",
            "id": b.id,
            "x": cx,
            "y": cy,
            "z": cz,
            "dx": dx,
            "dy": dy,
            "dz": b.height_cm / 100.0,
            "span": b.span_m,
            "color": "#38bdf8",
        })

    mesh_3d = Mesh3DData(
        element_meshes=element_meshes,
        bounding_box={
            "min_x": 0.0,
            "max_x": round(dim_x * scale_to_meters, 2),
            "min_y": 0.0,
            "max_y": round(dim_y * scale_to_meters, 2),
            "height_z": 3.0,
        }
    )

    # Parse text entities for explicit cross-section dimensions and cantilever annotations
    import re
    suggested_bw = 20.0
    suggested_bh = round(max(25.0, max_span * 2.8), 1)
    extracted_cantilever = 0.0

    for t in texts_raw:
        txt = t.get("text", "")
        sec_match = re.search(r"\(?(\d{2})\s*[xX]\s*(\d{2})\)?", txt)
        if sec_match:
            w_val = float(sec_match.group(1))
            h_val = float(sec_match.group(2))
            if 12.0 <= w_val <= 60.0 and 20.0 <= h_val <= 150.0:
                suggested_bw = w_val
                suggested_bh = h_val
        cant_match = re.search(r"BALAN[CÇ]O\s*(?:GOURMET|MARQUISE|CR[IÍ]TICO)?\s*(\d+(?:\.\d+)?)\s*m?", txt, re.IGNORECASE)
        if cant_match:
            c_val = float(cant_match.group(1))
            if 0.5 <= c_val <= 10.0:
                extracted_cantilever = c_val

    return UnifiedProjectData(
        project_name=project_name,
        source_format="dxf",
        file_path=str(path),
        bounding_box=mesh_3d.bounding_box,
        spans=spans or [SpanElement(id="S1", start_point=Point3D(x=0, y=0, z=0), end_point=Point3D(x=max_span, y=0, z=0), length_m=max_span)],
        columns=columns or [
            ColumnElement(id="P1", position=Point3D(x=0, y=0, z=0)),
            ColumnElement(id="P2", position=Point3D(x=max_span, y=0, z=0)),
        ],
        beams=beams or [BeamElement(id="V1", start_point=Point3D(x=0, y=0, z=3.0), end_point=Point3D(x=max_span, y=0, z=3.0), span_m=max_span)],
        max_span_m=max_span,
        max_cantilever_m=extracted_cantilever,
        suggested_beam_width_cm=suggested_bw,
        suggested_beam_height_cm=suggested_bh,
        suggested_fck_mpa=30.0,
        estimated_dead_load_kn_m=22.0,
        estimated_live_load_kn_m=3.0,
        mesh_3d=mesh_3d,
        raw_2d_entities=scaled_lines[:300],  # Primeiras 300 entidades para desenho no canvas
        metadata={
            "total_dxf_lines": len(lines_raw),
            "detected_scale": scale_to_meters,
            "total_spans": len(spans),
            "total_columns": len(columns),
        }
    )
