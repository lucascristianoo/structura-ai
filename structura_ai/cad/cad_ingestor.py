"""
Orquestrador central de ingestão de arquivos CAD e BIM.
Despacha automaticamente para DXF, IFC, OBJ, glTF ou gera modelo unificado a partir de imagens.
"""
from pathlib import Path
from typing import Any
from structura_ai.cad.models import UnifiedProjectData
from structura_ai.cad.dxf_parser import parse_dxf_file
from structura_ai.cad.ifc_parser import parse_ifc_file
from structura_ai.cad.mesh_parser import parse_mesh_file


class CadIngestor:
    SUPPORTED_FORMATS = {
        ".dxf": "AutoCAD Drawing Exchange Format",
        ".ifc": "Industry Foundation Classes (BIM)",
        ".obj": "Wavefront 3D Object",
        ".gltf": "GL Transmission Format (3D)",
        ".glb": "Binary GL Transmission Format (3D)",
        ".stl": "Stereolithography 3D Mesh",
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

        if ext == ".dxf":
            return parse_dxf_file(path, project_name=proj_title)
        elif ext == ".ifc":
            return parse_ifc_file(path, project_name=proj_title)
        elif ext in (".obj", ".gltf", ".glb", ".stl"):
            return parse_mesh_file(path, project_name=proj_title)
        else:
            raise ValueError(
                f"Formato '{ext}' não suportado pelo motor CAD/BIM. "
                f"Formatos aceitos: {', '.join(cls.SUPPORTED_FORMATS.keys())}"
            )


def ingest_cad_file(file_path: Path | str, filename: str = "", project_name: str = "") -> UnifiedProjectData:
    return CadIngestor.ingest(file_path, filename=filename, project_name=project_name)
