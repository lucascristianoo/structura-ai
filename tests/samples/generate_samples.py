"""
Gerador determinístico dos samples CAD/BIM usados nos testes.

Uso:  .venv/bin/python tests/samples/generate_samples.py
Gera arquivos em tests/samples/{dxf,ifc,mesh,vector,image,invalid}/ e o manifest.json
com as expectativas (tolerâncias incluídas) consumidas por tests/test_samples_rigorous.py.
"""
from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import ezdxf
import numpy as np
import trimesh

ROOT = Path(__file__).parent
MANIFEST: dict[str, dict] = {}


def reg(rel: str, **expect) -> Path:
    """Registra um sample no manifest. expect: kind ('ok'|'reject'), max_span_m, tol, formato etc."""
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST[rel] = expect
    return path


# ---------------------------------------------------------------- DXF
def _dxf(rel, entities, version="R2010", units=None, **expect):
    doc = ezdxf.new(version)
    for layer in ("VIGAS", "PILARES", "COTAS", "ARQ"):
        doc.layers.add(layer)
    msp = doc.modelspace()
    entities(msp)
    path = reg(rel, **expect)
    doc.saveas(path)


def gen_dxf():
    def portal_frame(scale):
        def f(msp):
            # Pórtico 2 vãos: 6 m e 4 m; layers estruturais
            for x in (0, 6, 10):
                msp.add_line((x * scale, 0), (x * scale, 3 * scale), dxfattribs={"layer": "PILARES"})
            msp.add_line((0, 3 * scale), (6 * scale, 3 * scale), dxfattribs={"layer": "VIGAS"})
            msp.add_line((6 * scale, 3 * scale), (10 * scale, 3 * scale), dxfattribs={"layer": "VIGAS"})
            msp.add_text("V1 20x40", dxfattribs={"layer": "COTAS", "insert": (3 * scale, 3.2 * scale), "height": 0.2 * scale})
        return f

    for name, scale in (("meters", 1), ("centimeters", 100), ("millimeters", 1000)):
        _dxf(f"dxf/portal_frame_{name}.dxf", portal_frame(scale), kind="ok", format="dxf",
             max_span_m=6.0, tol=0.15, min_beams=2, min_columns=3)

    def lwpoly(msp):
        msp.add_lwpolyline([(0, 0), (8, 0), (8, 5), (0, 5), (0, 0)], dxfattribs={"layer": "VIGAS"})
    _dxf("dxf/plan_lwpolyline_8x5.dxf", lwpoly, kind="ok", format="dxf", max_span_m=8.0, tol=0.15, min_beams=4)

    def sem_layer(msp):
        msp.add_line((0, 0), (12, 0))
        msp.add_line((0, 0), (0, 2))  # < 3m, não é viga sem layer estrutural
    _dxf("dxf/lines_no_layer_12m.dxf", sem_layer, kind="ok", format="dxf", max_span_m=12.0, tol=0.2)

    def empty(msp):
        pass
    _dxf("dxf/valid_empty.dxf", empty, kind="ok", format="dxf", max_span_m=10.0, tol=0.01, fallback=True)

    def so_texto(msp):
        msp.add_text("Somente anotacao", dxfattribs={"insert": (1, 1), "height": 0.5})
    _dxf("dxf/text_only.dxf", so_texto, kind="ok", format="dxf", max_span_m=10.0, tol=0.01, fallback=True)

    def diagonal(msp):
        msp.add_line((0, 0), (3, 4), dxfattribs={"layer": "VIGAS"})  # 5 m
    _dxf("dxf/diagonal_beam_3_4_5.dxf", diagonal, kind="ok", format="dxf", max_span_m=5.0, tol=0.05, min_beams=1)

    def coords_negativas(msp):
        msp.add_line((-20, -10), (-12, -10), dxfattribs={"layer": "VIGAS"})
    _dxf("dxf/negative_coordinates_8m.dxf", coords_negativas, kind="ok", format="dxf", max_span_m=8.0, tol=0.05)

    def longa_demais(msp):  # > 50 m: não deve virar viga
        msp.add_line((0, 0), (80, 0), dxfattribs={"layer": "VIGAS"})
        msp.add_line((0, 5), (7, 5), dxfattribs={"layer": "VIGAS"})
    _dxf("dxf/line_80m_ignored.dxf", longa_demais, kind="ok", format="dxf", min_beams=0)

    def grande(msp):  # estresse: 3000 entidades
        for i in range(1000):
            msp.add_line((i % 40, i // 40), ((i % 40) + 4, i // 40), dxfattribs={"layer": "VIGAS"})
            msp.add_line((i % 40, i // 40), (i % 40, (i // 40) + 3.5), dxfattribs={"layer": "PILARES"})
            msp.add_text(f"E{i}", dxfattribs={"insert": (i % 40, i // 40), "height": 0.1})
    _dxf("dxf/stress_3000_entities.dxf", grande, kind="ok", format="dxf", max_span_m=4.0, tol=0.2)

    def unicode_txt(msp):
        msp.add_line((0, 0), (7, 0), dxfattribs={"layer": "VIGAS"})
        msp.add_text("Viga ção ñ 梁 ✓", dxfattribs={"insert": (1, 1), "height": 0.2})
    for ver in ("R12", "R2000", "R2018"):
        _dxf(f"dxf/version_{ver}_7m.dxf", unicode_txt, version=ver, kind="ok", format="dxf", max_span_m=7.0, tol=0.05)


# ---------------------------------------------------------------- IFC
def gen_ifc():
    import ifcopenshell
    import ifcopenshell.api

    def build(rel, schema, beams, columns, slabs=0, **expect):
        f = ifcopenshell.api.run("project.create_file", version=schema)
        if schema == "IFC2X3":  # exige OwnerHistory
            import ifcopenshell.api.owner.settings as osett
            person = f.createIfcPerson()
            org = f.createIfcOrganization()
            user = f.createIfcPersonAndOrganization(person, org)
            app = f.createIfcApplication(org, "1", "Sample", "sample")
            osett.get_user = lambda _f: user
            osett.get_application = lambda _f: app
        project = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name="Sample")
        ifcopenshell.api.run("unit.assign_unit", f)
        ctx = ifcopenshell.api.run("context.add_context", f, context_type="Model")
        site = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSite", name="Site")
        bld = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Bld")
        ifcopenshell.api.run("aggregate.assign_object", f, products=[site], relating_object=project)
        ifcopenshell.api.run("aggregate.assign_object", f, products=[bld], relating_object=site)

        def add(cls, name, x, y, z):
            e = ifcopenshell.api.run("root.create_entity", f, ifc_class=cls, name=name)
            m = np.eye(4)
            m[:3, 3] = (x, y, z)
            ifcopenshell.api.run("geometry.edit_object_placement", f, product=e, matrix=m)
            ifcopenshell.api.run("spatial.assign_container", f, products=[e], relating_structure=bld)
            return e

        for i, (x, y, z) in enumerate(beams):
            add("IfcBeam", f"V{i+1}", x, y, z)
        for i, (x, y, z) in enumerate(columns):
            add("IfcColumn", f"P{i+1}", x, y, z)
        for i in range(slabs):
            add("IfcSlab", f"L{i+1}", 0, 0, 3)
        path = reg(rel, kind="ok", format="ifc", min_beams=len(beams) if beams else 0,
                   min_columns=len(columns) if columns else 0, schema=schema, **expect)
        f.write(str(path))

    cols = [(0, 0, 0), (6, 0, 0), (12, 0, 0), (0, 5, 0), (6, 5, 0), (12, 5, 0)]
    beams = [(0, 0, 3), (6, 0, 3), (0, 5, 3), (6, 5, 3)]
    build("ifc/portal_frame_ifc4.ifc", "IFC4", beams, cols, slabs=2)
    build("ifc/portal_frame_ifc2x3.ifc", "IFC2X3", beams, cols, slabs=1)
    build("ifc/columns_only.ifc", "IFC4", [], cols[:3])
    build("ifc/empty_model.ifc", "IFC4", [], [])
    big_cols = [(i * 4.0, j * 4.0, 0) for i in range(15) for j in range(15)]
    big_beams = [(i * 4.0, j * 4.0, 3) for i in range(15) for j in range(15)]
    build("ifc/stress_225_columns_225_beams.ifc", "IFC4", big_beams, big_cols, slabs=10)


# ---------------------------------------------------------------- Malhas
def gen_mesh():
    def box(ex, name_scale=1.0):
        return trimesh.creation.box(extents=[e * name_scale for e in ex])

    for unit, s in (("m", 1.0), ("cm", 100.0), ("mm", 1000.0)):
        m = box((12, 4, 3), s)
        for ext in ("obj", "stl", "glb", "gltf"):
            # gltf usa .bin externo: isola em subpasta para não colidir entre samples
            rel = f"mesh/gltf_{unit}/box_12x4x3.gltf" if ext == "gltf" else f"mesh/box_12x4x3_{unit}.{ext}"
            p = reg(rel, kind="ok", format=ext, max_span_m=12.0, tol=0.05, min_vertices=8)
            m.export(p)

    # STL ASCII escrito à mão
    p = reg("mesh/ascii_triangle_10m.stl", kind="ok", format="stl", max_span_m=10.0, tol=0.05, min_vertices=3)
    p.write_text("solid t\n facet normal 0 0 1\n  outer loop\n   vertex 0 0 0\n   vertex 10 0 0\n   vertex 0 5 0\n  endloop\n endfacet\nendsolid t\n")

    # Malha densa (> 5000 faces => decimação)
    sph = trimesh.creation.icosphere(subdivisions=5, radius=6.0)  # 20480 faces, diâmetro 12
    p = reg("mesh/dense_sphere_20k_faces.obj", kind="ok", format="obj", max_span_m=12.0, tol=0.2, max_faces=6000)
    sph.export(p)

    # Cena glTF com múltiplas geometrias
    scene = trimesh.Scene()
    scene.add_geometry(box((2, 2, 3)), node_name="p1")
    t = trimesh.transformations.translation_matrix([10, 0, 0])
    scene.add_geometry(box((2, 2, 3)), node_name="p2", transform=t)
    p = reg("mesh/scene_two_columns.glb", kind="ok", format="glb", max_span_m=12.0, tol=0.1, min_vertices=16)
    scene.export(p)

    # Malha pequena (< 2m => max_span fallback 8.0)
    p = reg("mesh/cube_1m_fallback.obj", kind="ok", format="obj", max_span_m=8.0, tol=0.01)
    box((1, 1, 1)).export(p)

    # OBJ com faces quadradas, normais e UV
    p = reg("mesh/quad_normals_uv.obj", kind="ok", format="obj", max_span_m=9.0, tol=0.05, min_vertices=4)
    p.write_text("# quad\nv 0 0 0\nv 9 0 0\nv 9 3 0\nv 0 3 0\nvt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\nvn 0 0 1\n"
                 "f 1/1/1 2/2/1 3/3/1 4/4/1\n")


# ---------------------------------------------------------------- Vetor / imagem
def gen_vector_image():
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400">'
           '<line x1="0" y1="0" x2="400" y2="0" stroke="black"/>'
           '<rect x="0" y="0" width="150" height="100"/></svg>')
    reg("vector/plan_line_8m.svg", kind="ok", format="svg", max_span_m=8.0, tol=0.01).write_text(svg)
    reg("vector/svg_no_primitives.svg", kind="ok", format="svg", max_span_m=9.5, tol=0.01).write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><circle r="5"/></svg>')
    pdf = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
           b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")
    reg("vector/minimal_sheet.pdf", kind="ok", format="pdf", max_span_m=9.5, tol=0.01).write_bytes(pdf)

    def png(w, h, color):
        raw = b"".join(b"\x00" + bytes(color) * w for _ in range(h))
        def chunk(t, d):
            c = struct.pack(">I", len(d)) + t + d
            return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    reg("image/sketch_64x64.png", kind="image", format="png", width=64, height=64).write_bytes(png(64, 64, (255, 255, 255)))
    reg("image/blueprint_512x256.png", kind="image", format="png", width=512, height=256).write_bytes(png(512, 256, (10, 40, 120)))


# ---------------------------------------------------------------- Inválidos
def gen_invalid():
    def bad(rel, data):
        reg(rel, kind="reject").write_bytes(data)

    bad("invalid/empty.dxf", b"")
    bad("invalid/random_binary.dxf", bytes(np.random.default_rng(1).integers(0, 256, 4096, dtype=np.uint8)))
    bad("invalid/truncated_dxf.dxf", b"0\nSECTION\n2\nENTITIES\n0\nLINE\n8\n0\n10\n")
    bad("invalid/header_without_endsec.ifc", b"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('x'),'2;1');\n#1=GARBAGE(")
    bad("invalid/plain_text.ifc", b"isto nao e um arquivo ifc\n")
    bad("invalid/empty.ifc", b"")
    bad("invalid/obj_no_vertices.obj", b"# nada aqui\n")
    bad("invalid/corrupted_stl.stl", b"solid x\nfacet normal a b c\n\x00\xff")
    bad("invalid/glb_wrong_magic.glb", b"NOTGLTF" + b"\x00" * 64)
    bad("invalid/gltf_broken_json.gltf", b'{"asset": {"version": "2.0"}, "scenes": [')
    bad("invalid/unsupported_extension.xyz", b"qualquer coisa")


def main():
    for d in ("dxf", "ifc", "mesh", "vector", "image", "invalid"):
        for f in sorted((ROOT / d).rglob("*"), reverse=True):
            f.unlink() if f.is_file() else f.rmdir()
    gen_dxf(); gen_ifc(); gen_mesh(); gen_vector_image(); gen_invalid()
    (ROOT / "manifest.json").write_text(json.dumps(MANIFEST, indent=2, ensure_ascii=False, sort_keys=True))
    print(f"{len(MANIFEST)} samples gerados em {ROOT}")


if __name__ == "__main__":
    main()
