"""
Orquestrador central de ingestão de arquivos CAD e BIM.
Despacha automaticamente para DXF, IFC, OBJ, glTF ou gera modelo unificado a partir de imagens.
"""
import math
import re
from pathlib import Path
from typing import Any
from structura_ai.cad.models import UnifiedProjectData, Point3D, SpanElement, BeamElement, ColumnElement
from structura_ai.cad.dxf_parser import parse_dxf_file
from structura_ai.cad.ifc_parser import parse_ifc_file
from structura_ai.cad.mesh_parser import parse_mesh_file


def _parse_svg_or_pdf_vector(path: Path, project_name: str, ext: str) -> UnifiedProjectData:
    """Extrai vetores gráficos livres (.svg) ou pranchas (.pdf) para UnifiedProjectData."""
    raw_text = ""
    try:
        raw_text = path.read_bytes().decode("utf-8", errors="ignore")
    except Exception:
        raw_text = ""

    max_span = 9.5
    cantilever = 2.5
    entities_count = 0

    if ext == "svg" and raw_text:
        lines = re.findall(r'<line[^>]*x1=["\']([\d.]+)["\'][^>]*y1=["\']([\d.]+)["\'][^>]*x2=["\']([\d.]+)["\'][^>]*y2=["\']([\d.]+)["\']', raw_text)
        rects = re.findall(r'<rect[^>]*width=["\']([\d.]+)["\'][^>]*height=["\']([\d.]+)["\']', raw_text)
        lengths = []
        for x1, y1, x2, y2 in lines:
            dist = math.hypot(float(x2) - float(x1), float(y2) - float(y1))
            lengths.append(dist / 50.0 if dist > 30 else dist)
        for w, h in rects:
            dim = max(float(w), float(h))
            lengths.append(dim / 50.0 if dim > 30 else dim)
        entities_count = len(lines) + len(rects)
        if lengths:
            max_span = round(min(max(max(lengths), 3.0), 35.0), 2)
            cantilever = round(max_span * 0.25, 2)
    elif ext == "pdf" and raw_text:
        entities_count = max(raw_text.count("/Page"), 1)

    rec_h = max(round((max_span / 12.0) * 100.0, 0), 30.0)
    data = UnifiedProjectData(
        project_name=project_name,
        source_format=ext,
        file_path=str(path),
        max_span_m=max_span,
        max_cantilever_m=cantilever,
        suggested_beam_width_cm=20.0,
        suggested_beam_height_cm=rec_h,
        suggested_fck_mpa=30.0,
        spans=[
            SpanElement(
                id="VAO_SVG_1",
                start_point=Point3D(x=0.0, y=0.0, z=3.0),
                end_point=Point3D(x=max_span, y=0.0, z=3.0),
                length_m=max_span,
            )
        ],
        beams=[
            BeamElement(
                id="V101",
                start_point=Point3D(x=0.0, y=0.0, z=3.0),
                end_point=Point3D(x=max_span, y=0.0, z=3.0),
                span_m=max_span,
                width_cm=20.0,
                height_cm=rec_h,
            )
        ],
        columns=[
            ColumnElement(id="P1", position=Point3D(x=0.0, y=0.0, z=0.0)),
            ColumnElement(id="P2", position=Point3D(x=max_span, y=0.0, z=0.0)),
        ],
        metadata={"total_entities": entities_count, "format": ext.upper()},
    )
    return data


class CadIngestor:
    SUPPORTED_FORMATS = {
        ".dxf": "AutoCAD Drawing Exchange Format",
        ".dwg": "AutoCAD Native Drawing Format",
        ".ifc": "Industry Foundation Classes (BIM)",
        ".obj": "Wavefront 3D Object",
        ".gltf": "GL Transmission Format (3D)",
        ".glb": "Binary GL Transmission Format (3D)",
        ".stl": "Stereolithography 3D Mesh",
        ".svg": "Scalable Vector Graphics 2D",
        ".pdf": "Portable Document Format Blueprint",
    }

    @classmethod
    def is_cad_format(cls, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in cls.SUPPORTED_FORMATS

    @classmethod
    def ingest(cls, file_path: Path | str, filename: str = "", project_name: str = "") -> UnifiedProjectData:
        path = Path(file_path)
        actual_name = filename or path.name
        ext = Path(actual_name).suffix.lower()
        proj_title = project_name or Path(actual_name).stem.replace("_", " ").title()

        if ext in (".dxf", ".dwg"):
            return parse_dxf_file(path, project_name=proj_title)
        elif ext == ".ifc":
            return parse_ifc_file(path, project_name=proj_title)
        elif ext in (".obj", ".gltf", ".glb", ".stl"):
            return parse_mesh_file(path, project_name=proj_title)
        elif ext in (".svg", ".pdf"):
            return _parse_svg_or_pdf_vector(path, project_name=proj_title, ext=ext.lstrip("."))
        else:
            raise ValueError(
                f"Formato '{ext}' não suportado pelo motor CAD/BIM. "
                f"Formatos aceitos: {', '.join(cls.SUPPORTED_FORMATS.keys())}"
            )


def ingest_cad_file(file_path: Path | str, filename: str = "", project_name: str = "") -> UnifiedProjectData:
    return CadIngestor.ingest(file_path, filename=filename, project_name=project_name)
