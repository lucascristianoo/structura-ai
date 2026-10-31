"""
Testes rigorosos orientados a samples reais (tests/samples/).
Regerar: .venv/bin/python tests/samples/generate_samples.py
"""
import json
import math
import time
from pathlib import Path

import pytest

from structura_ai.cad import CadIngestor, UnifiedProjectData

SAMPLES = Path(__file__).parent / "samples"
MANIFEST = json.loads((SAMPLES / "manifest.json").read_text())

def _p(keys):
    """Parametriza respeitando 'known_issue' como xfail estrito (bug conhecido do código, não do sample)."""
    out = []
    for k in keys:
        issue = MANIFEST[k].get("known_issue")
        marks = [pytest.mark.xfail(strict=True, reason=issue)] if issue else []
        out.append(pytest.param(k, id=k, marks=marks))
    return out


OK = sorted(k for k, v in MANIFEST.items() if v["kind"] == "ok")
REJECT = sorted(k for k, v in MANIFEST.items() if v["kind"] == "reject")
IMAGES = sorted(k for k, v in MANIFEST.items() if v["kind"] == "image")


def test_manifest_matches_disk():
    """Todo sample do manifest existe e não há arquivo órfão."""
    on_disk = {
        str(p.relative_to(SAMPLES))
        for p in SAMPLES.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".py", ".json", ".bin")
    }
    assert set(MANIFEST) == on_disk
    assert len(OK) >= 30 and len(REJECT) >= 8


@pytest.mark.parametrize("rel", _p(OK))
def test_valid_sample_ingests_with_sane_output(rel):
    exp = MANIFEST[rel]
    data = CadIngestor.ingest(SAMPLES / rel)

    assert isinstance(data, UnifiedProjectData)
    assert data.source_format == exp["format"]
    assert data.project_name

    # Invariantes numéricos: nada de NaN/inf/negativo
    for v in (data.max_span_m, data.max_cantilever_m, data.suggested_beam_width_cm,
              data.suggested_beam_height_cm, data.suggested_fck_mpa):
        assert math.isfinite(v)
    assert data.max_span_m > 0
    assert data.suggested_beam_height_cm > 0 and data.suggested_beam_width_cm > 0

    # Coerência interna
    for b in data.beams:
        assert math.isfinite(b.span_m) and b.span_m >= 0
        assert b.span_m <= 50.0 + 1e-6
    for s in data.spans:
        assert s.length_m <= data.max_span_m + 1e-6
    ids = [b.id for b in data.beams]
    assert len(ids) == len(set(ids)), "IDs de viga duplicados"
    cids = [c.id for c in data.columns]
    assert len(cids) == len(set(cids)), "IDs de pilar duplicados"

    # Expectativas específicas do sample
    if "max_span_m" in exp:
        assert data.max_span_m == pytest.approx(exp["max_span_m"], abs=exp.get("tol", 0.1)), rel
    if "min_beams" in exp:
        assert len(data.beams) >= exp["min_beams"], rel
    if "min_columns" in exp:
        assert len(data.columns) >= exp["min_columns"], rel
    if "min_vertices" in exp:
        assert data.mesh_3d is not None and len(data.mesh_3d.vertices) >= exp["min_vertices"], rel
    if "max_faces" in exp:
        assert len(data.mesh_3d.faces) <= exp["max_faces"], rel
    if "schema" in exp:
        assert data.metadata.get("schema") == exp["schema"], rel


@pytest.mark.parametrize("rel", OK)
def test_valid_sample_is_deterministic_and_serializable(rel):
    a = CadIngestor.ingest(SAMPLES / rel)
    b = CadIngestor.ingest(SAMPLES / rel)
    assert a.max_span_m == b.max_span_m
    assert len(a.beams) == len(b.beams) and len(a.columns) == len(b.columns)
    dumped = a.model_dump_json()
    assert UnifiedProjectData.model_validate_json(dumped).max_span_m == a.max_span_m


@pytest.mark.parametrize("rel", _p(REJECT))
def test_invalid_sample_is_rejected_cleanly(rel):
    """Arquivos corrompidos devem gerar ValueError controlado (nunca crash/outra exceção)."""
    with pytest.raises(ValueError):
        CadIngestor.ingest(SAMPLES / rel)


def test_dxf_unit_scales_agree():
    """O mesmo pórtico em m, cm e mm deve produzir o mesmo vão (invariância de escala)."""
    spans = [CadIngestor.ingest(SAMPLES / f"dxf/portico_{u}.dxf").max_span_m
             for u in ("metros", "centimetros", "milimetros")]
    assert max(spans) - min(spans) < 0.15, spans


def test_mesh_formats_agree():
    """A mesma caixa em OBJ/STL/GLB/glTF deve resultar na mesma geometria."""
    for unit in ("m", "cm", "mm"):
        results = [
            CadIngestor.ingest(SAMPLES / rel)
            for rel in (f"mesh/caixa_12x4x3_{unit}.obj", f"mesh/caixa_12x4x3_{unit}.stl",
                        f"mesh/caixa_12x4x3_{unit}.glb", f"mesh/gltf_{unit}/caixa_12x4x3.gltf")
        ]
        spans = {round(r.max_span_m, 1) for r in results}
        assert spans == {12.0}, (unit, spans)


def test_dxf_ignores_oversized_line():
    d = CadIngestor.ingest(SAMPLES / "dxf/linha_80m_ignorada.dxf")
    assert all(b.span_m <= 50.0 for b in d.beams)


def test_ifc_element_counts_exact():
    d = CadIngestor.ingest(SAMPLES / "ifc/portico_ifc4.ifc")
    assert (len(d.beams), len(d.columns)) == (4, 6)
    d = CadIngestor.ingest(SAMPLES / "ifc/estresse_225_pilares_225_vigas.ifc")
    assert len(d.columns) == 225


@pytest.mark.parametrize("rel", [
    "dxf/estresse_3000_entidades.dxf",
    "ifc/estresse_225_pilares_225_vigas.ifc",
    "mesh/esfera_densa_20k_faces.obj",
])
def test_stress_samples_within_time_budget(rel):
    t0 = time.perf_counter()
    CadIngestor.ingest(SAMPLES / rel)
    assert time.perf_counter() - t0 < 30.0


@pytest.mark.parametrize("rel", IMAGES)
def test_image_samples_are_valid_png(rel):
    from PIL import Image
    exp = MANIFEST[rel]
    with Image.open(SAMPLES / rel) as im:
        im.verify()
    with Image.open(SAMPLES / rel) as im:
        assert im.format == "PNG" and im.size == (exp["width"], exp["height"])
    assert CadIngestor.is_cad_format(rel) is False


def test_extension_dispatch_rejects_unknown():
    with pytest.raises(ValueError):
        CadIngestor.ingest(SAMPLES / "invalid/extensao_nao_suportada.xyz")
