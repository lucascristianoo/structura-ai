#!/usr/bin/env python3
"""
Gerador de Modelos Canônicos de Teste para o Structura.AI (DXF, IFC, OBJ).
Salva os arquivos em downloads/test_samples/ para teste e demonstração.
"""
from pathlib import Path
import ezdxf
from ezdxf import units
import ifcopenshell
import ifcopenshell.api


def generate_dxf_horizon_10m(dest: Path):
    """Cria prancha CAD DXF canônica da Residência Horizon com Vão de 10m."""
    doc = ezdxf.new("R2010", setup=True)
    doc.units = units.M
    msp = doc.modelspace()

    # Camadas normativas
    doc.layers.add("ESTRUTURA_PILARES", color=ezdxf.colors.BLUE)
    doc.layers.add("ESTRUTURA_VIGAS", color=ezdxf.colors.CYAN)
    doc.layers.add("ARQUITETURA_PAREDES", color=ezdxf.colors.WHITE)
    doc.layers.add("COTAS_DIMENSOES", color=ezdxf.colors.GREEN)

    # Pilares (seção 0.20 x 0.40m)
    p1 = [(-0.1, -0.2), (0.1, -0.2), (0.1, 0.2), (-0.1, 0.2), (-0.1, -0.2)]
    p2 = [(9.9, -0.2), (10.1, -0.2), (10.1, 0.2), (9.9, 0.2), (9.9, -0.2)]
    msp.add_lwpolyline(p1, dxfattribs={"layer": "ESTRUTURA_PILARES"})
    msp.add_lwpolyline(p2, dxfattribs={"layer": "ESTRUTURA_PILARES"})

    # Viga contínua de 10m de vão
    msp.add_line((0.0, -0.1), (10.0, -0.1), dxfattribs={"layer": "ESTRUTURA_VIGAS"})
    msp.add_line((0.0, 0.1), (10.0, 0.1), dxfattribs={"layer": "ESTRUTURA_VIGAS"})
    # Linha de eixo unifilar
    msp.add_line((0.0, 0.0), (10.0, 0.0), dxfattribs={"layer": "ESTRUTURA_VIGAS"})

    # Balanço frontal de 3.5m
    msp.add_line((10.0, -0.1), (13.5, -0.1), dxfattribs={"layer": "ESTRUTURA_VIGAS"})
    msp.add_line((10.0, 0.1), (13.5, 0.1), dxfattribs={"layer": "ESTRUTURA_VIGAS"})

    # Textos de especificação
    msp.add_text("P1 (20x40)", dxfattribs={"layer": "ESTRUTURA_PILARES", "height": 0.25}).set_placement((-0.5, -0.6))
    msp.add_text("P2 (20x40)", dxfattribs={"layer": "ESTRUTURA_PILARES", "height": 0.25}).set_placement((9.5, -0.6))
    msp.add_text("VIGA V101 (20x30) — VÃO LIVRE 10.00m", dxfattribs={"layer": "COTAS_DIMENSOES", "height": 0.3}).set_placement((2.5, 0.4))
    msp.add_text("BALANÇO GOURMET 3.50m", dxfattribs={"layer": "COTAS_DIMENSOES", "height": 0.25}).set_placement((10.5, 0.4))

    doc.saveas(str(dest))
    print(f"✅ DXF gerado: {dest} ({dest.stat().st_size} bytes)")


def generate_dxf_balanco_critico(dest: Path):
    """Cria prancha CAD DXF de marquise/balanço crítico de 4.5m."""
    doc = ezdxf.new("R2010", setup=True)
    doc.units = units.M
    msp = doc.modelspace()

    doc.layers.add("ESTRUTURA_VIGAS", color=ezdxf.colors.RED)
    doc.layers.add("ESTRUTURA_PILARES", color=ezdxf.colors.BLUE)
    doc.layers.add("COTAS", color=ezdxf.colors.YELLOW)

    # Pilar de engaste na origem
    msp.add_lwpolyline([(-0.2, -0.3), (0.2, -0.3), (0.2, 0.3), (-0.2, 0.3), (-0.2, -0.3)], dxfattribs={"layer": "ESTRUTURA_PILARES"})
    # Marquise em balanço de 4.50m
    msp.add_line((0.0, 0.0), (4.5, 0.0), dxfattribs={"layer": "ESTRUTURA_VIGAS"})
    msp.add_line((0.0, -0.15), (4.5, -0.15), dxfattribs={"layer": "ESTRUTURA_VIGAS"})
    msp.add_line((0.0, 0.15), (4.5, 0.15), dxfattribs={"layer": "ESTRUTURA_VIGAS"})
    msp.add_text("MARQUISE BALANÇO CRÍTICO 4.50m — FLECHA ALTA", dxfattribs={"layer": "COTAS", "height": 0.25}).set_placement((0.5, 0.35))

    doc.saveas(str(dest))
    print(f"✅ DXF gerado: {dest} ({dest.stat().st_size} bytes)")


def generate_obj_residencia_3d(dest: Path):
    """Gera modelo 3D Wavefront (.obj) de residência com vão livre e laje delgada."""
    obj_lines = [
        "# Structura.AI Canonical 3D Benchmark — Residência Horizon",
        "# Unidades em Metros",
        "o Residencia_Horizon_3D",
        # Pilares (P1: x 0..0.3, y 0..0.4, z 0..3.2)
        "v 0.0 0.0 0.0", "v 0.3 0.0 0.0", "v 0.3 0.4 0.0", "v 0.0 0.4 0.0",
        "v 0.0 0.0 3.2", "v 0.3 0.0 3.2", "v 0.3 0.4 3.2", "v 0.0 0.4 3.2",
        # Pilares (P2: x 10.0..10.3, y 0..0.4, z 0..3.2)
        "v 10.0 0.0 0.0", "v 10.3 0.0 0.0", "v 10.3 0.4 0.0", "v 10.0 0.4 0.0",
        "v 10.0 0.0 3.2", "v 10.3 0.0 3.2", "v 10.3 0.4 3.2", "v 10.0 0.4 3.2",
        # Viga delgada V101 (x 0..10.3, y 0.1..0.3, z 2.9..3.2)
        "v 0.0 0.1 2.9", "v 10.3 0.1 2.9", "v 10.3 0.3 2.9", "v 0.0 0.3 2.9",
        "v 0.0 0.1 3.2", "v 10.3 0.1 3.2", "v 10.3 0.3 3.2", "v 0.0 0.3 3.2",
        # Laje de cobertura panorâmica (x -1.0..12.0, y -1.0..5.0, z 3.2..3.35)
        "v -1.0 -1.0 3.2", "v 12.0 -1.0 3.2", "v 12.0 5.0 3.2", "v -1.0 5.0 3.2",
        "v -1.0 -1.0 3.35", "v 12.0 -1.0 3.35", "v 12.0 5.0 3.35", "v -1.0 5.0 3.35",
        # Faces P1
        "f 1 2 3 4", "f 5 8 7 6", "f 1 5 6 2", "f 2 6 7 3", "f 3 7 8 4", "f 4 8 5 1",
        # Faces P2
        "f 9 10 11 12", "f 13 16 15 14", "f 9 13 14 10", "f 10 14 15 11", "f 11 15 16 12", "f 12 16 13 9",
        # Faces Viga V101
        "f 17 18 19 20", "f 21 24 23 22", "f 17 21 22 18", "f 18 22 23 19", "f 19 23 24 20", "f 20 24 21 17",
        # Faces Laje
        "f 25 26 27 28", "f 29 32 31 30", "f 25 29 30 26", "f 26 30 31 27", "f 27 31 32 28", "f 28 32 29 25",
    ]
    with open(dest, "w") as f:
        f.write("\n".join(obj_lines) + "\n")
    print(f"✅ OBJ 3D gerado: {dest} ({dest.stat().st_size} bytes)")


def generate_ifc_pavilhao_bim(dest: Path):
    """Gera modelo BIM IFC4 válido com vigas e pilares estruturais."""
    f = ifcopenshell.file(schema="IFC4")
    
    # Contexto e Projeto
    project = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name="Pavilhao_Estrutural_BIM")
    ctx = ifcopenshell.api.run("context.add_context", f, context_type="Model")
    body = ifcopenshell.api.run("context.add_context", f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)
    
    site = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSite", name="Canteiro Central")
    building = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Pavilhao Multiuso")
    storey = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="Nivel Terreo")

    ifcopenshell.api.run("aggregate.assign_object", f, relating_object=project, products=[site])
    ifcopenshell.api.run("aggregate.assign_object", f, relating_object=site, products=[building])
    ifcopenshell.api.run("aggregate.assign_object", f, relating_object=building, products=[storey])

    # Pilares
    col1 = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcColumn", name="Pilar_P1_0.20x0.40")
    col2 = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcColumn", name="Pilar_P2_0.20x0.40")
    ifcopenshell.api.run("spatial.assign_container", f, relating_structure=storey, products=[col1, col2])

    # Viga de 10.5m de vão
    beam = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBeam", name="Viga_Principal_V101_10.5m")
    ifcopenshell.api.run("spatial.assign_container", f, relating_structure=storey, products=[beam])

    # Adicionar Property Set com métricas
    pset_beam = ifcopenshell.api.run("pset.add_pset", f, product=beam, name="Pset_BeamCommon")
    ifcopenshell.api.run("pset.edit_pset", f, pset=pset_beam, properties={"Length": 10.5, "Depth": 320.0, "Width": 200.0, "Span": 10.5})

    pset_col = ifcopenshell.api.run("pset.add_pset", f, product=col1, name="Pset_ColumnCommon")
    ifcopenshell.api.run("pset.edit_pset", f, pset=pset_col, properties={"Height": 3200.0, "CrossSection": "200x400"})

    f.write(str(dest))
    print(f"✅ IFC BIM gerado: {dest} ({dest.stat().st_size} bytes)")


def generate_dxf_sobrado_conforme_5m(dest: Path):
    """Cria prancha CAD DXF de Residência Modular Conforme NBR 6118 (Vão 5.0m, Viga 20x45cm)."""
    doc = ezdxf.new("R2010", setup=True)
    doc.units = units.M
    msp = doc.modelspace()

    doc.layers.add("ESTRUTURA_PILARES", color=ezdxf.colors.BLUE)
    doc.layers.add("ESTRUTURA_VIGAS", color=ezdxf.colors.GREEN)
    doc.layers.add("COTAS_DIMENSOES", color=ezdxf.colors.WHITE)
    doc.layers.add("STATUS_NBR6118", color=ezdxf.colors.GREEN)

    # Pilares P1 e P2 (20x30cm)
    msp.add_lwpolyline([(-0.1, -0.15), (0.1, -0.15), (0.1, 0.15), (-0.1, 0.15), (-0.1, -0.15)], dxfattribs={"layer": "ESTRUTURA_PILARES"})
    msp.add_lwpolyline([(4.9, -0.15), (5.1, -0.15), (5.1, 0.15), (4.9, 0.15), (4.9, -0.15)], dxfattribs={"layer": "ESTRUTURA_PILARES"})

    # Viga V1 (20x45cm) em vão de 5.0m
    msp.add_line((0.0, -0.1), (5.0, -0.1), dxfattribs={"layer": "ESTRUTURA_VIGAS"})
    msp.add_line((0.0, 0.1), (5.0, 0.1), dxfattribs={"layer": "ESTRUTURA_VIGAS"})
    msp.add_line((0.0, 0.0), (5.0, 0.0), dxfattribs={"layer": "ESTRUTURA_VIGAS"})

    msp.add_text("P1 (20x30)", dxfattribs={"layer": "ESTRUTURA_PILARES", "height": 0.2}).set_placement((-0.4, -0.5))
    msp.add_text("P2 (20x30)", dxfattribs={"layer": "ESTRUTURA_PILARES", "height": 0.2}).set_placement((4.7, -0.5))
    msp.add_text("VIGA V1 (20x45) — VÃO 5.00m [CONFORME NBR 6118]", dxfattribs={"layer": "COTAS_DIMENSOES", "height": 0.25}).set_placement((0.8, 0.3))
    msp.add_text("FLECHA 8.2mm <= LIMITE 20.0mm (FOLGA 59%)", dxfattribs={"layer": "STATUS_NBR6118", "height": 0.2}).set_placement((0.8, -0.4))

    doc.saveas(str(dest))
    print(f"✅ DXF Conforme gerado: {dest} ({dest.stat().st_size} bytes)")


def generate_ifc_sobrado_conforme(dest: Path):
    """Gera modelo IFC4 de referência 100% conforme com NBR 6118."""
    f = ifcopenshell.file(schema="IFC4")
    project = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name="Sobrado_Racional_NBR6118")
    ctx = ifcopenshell.api.run("context.add_context", f, context_type="Model")
    body = ifcopenshell.api.run("context.add_context", f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)

    site = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSite", name="Lote Residencial")
    building = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Residencia Sobrado")
    storey = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="Piso Superior")

    ifcopenshell.api.run("aggregate.assign_object", f, relating_object=project, products=[site])
    ifcopenshell.api.run("aggregate.assign_object", f, relating_object=site, products=[building])
    ifcopenshell.api.run("aggregate.assign_object", f, relating_object=building, products=[storey])

    col1 = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcColumn", name="Pilar_P1_25x25")
    col2 = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcColumn", name="Pilar_P2_25x25")
    beam = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBeam", name="Viga_V1_20x45_Vao_5m")

    ifcopenshell.api.run("spatial.assign_container", f, relating_structure=storey, products=[col1, col2, beam])

    pset_beam = ifcopenshell.api.run("pset.add_pset", f, product=beam, name="Pset_BeamCommon")
    ifcopenshell.api.run("pset.edit_pset", f, pset=pset_beam, properties={"Length": 5.0, "Depth": 450.0, "Width": 200.0, "Span": 5.0})

    pset_comp = ifcopenshell.api.run("pset.add_pset", f, product=beam, name="Pset_StructuraCompliance")
    ifcopenshell.api.run("pset.edit_pset", f, pset=pset_comp, properties={"IsViable": True, "Score": 98.5, "Standard": "NBR 6118:2023"})

    f.write(str(dest))
    print(f"✅ IFC Conforme gerado: {dest} ({dest.stat().st_size} bytes)")


def main():
    root = Path(__file__).resolve().parent.parent
    dest_dir = root / "downloads" / "test_samples"
    dest_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  🏛️ Gerando Amostras Canônicas CAD/BIM para o Structura.AI")
    print(f"  📂 Destino: {dest_dir}")
    print("=" * 60)

    # Cenário 1: Requer Redesign Estrutural
    generate_dxf_horizon_10m(dest_dir / "residencia_horizon_10m.dxf")
    generate_dxf_balanco_critico(dest_dir / "cobertura_balanco_critico.dxf")
    generate_obj_residencia_3d(dest_dir / "residencia_horizon_3d.obj")

    # Cenário 2: Totalmente Conforme NBR 6118
    generate_ifc_pavilhao_bim(dest_dir / "pavilhao_estrutural_bim.ifc")
    generate_dxf_sobrado_conforme_5m(dest_dir / "sobrado_grid_racional_5m.dxf")
    generate_ifc_sobrado_conforme(dest_dir / "sobrado_conforme_nbr6118.ifc")

    print("\n🎉 Todas as 6 amostras oficiais de teste foram geradas com sucesso!")


if __name__ == "__main__":
    main()

