"""
Módulo CAD/BIM do Structura.AI
Suporte para ingestão e normalização de DXF, IFC, OBJ e glTF.
"""
from structura_ai.cad.models import UnifiedProjectData, SpanElement, ColumnElement, BeamElement
from structura_ai.cad.cad_ingestor import CadIngestor, ingest_cad_file

__all__ = [
    "UnifiedProjectData",
    "SpanElement",
    "ColumnElement",
    "BeamElement",
    "CadIngestor",
    "ingest_cad_file",
]
