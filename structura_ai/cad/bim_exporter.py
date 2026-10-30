"""
Native BIM & CAD Roundtrip Exporter (IFC4 & DXF R2010).
Converts Structura.AI project models and redesign variants into standard IFC4
and AutoCAD DXF files for bidirectional roundtrip with Revit, Archicad, Blender, and Rhino.
"""
import io
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import ezdxf
from ezdxf import units
import ifcopenshell
import ifcopenshell.api


class BimExporter:
    """
    Exports structural framing models and redesign variants to IFC4 and DXF.
    """

    @classmethod
    def export_project_ifc(
        cls,
        project_title: str,
        parameters: Dict[str, Any],
        analysis_data: Optional[Dict[str, Any]] = None,
        variant: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generates standard IFC4 building model string with IfcBeam, IfcColumn, IfcSlab,
        and custom property sets for NBR 6118 compliance and SINAPI cost/carbon.
        """
        f = ifcopenshell.file(schema="IFC4")

        # Root setup
        proj_name = f"{project_title} - {variant.get('strategy_name', 'Original') if variant else 'Original'}"
        project = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name=proj_name)
        ctx = ifcopenshell.api.run("context.add_context", f, context_type="Model")
        body = ifcopenshell.api.run("context.add_context", f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)

        site = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSite", name="Terreno")
        building = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Edificio Principal")
        storey = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="Nivel Cobertura")

        ifcopenshell.api.run("aggregate.assign_object", f, relating_object=project, products=[site])
        ifcopenshell.api.run("aggregate.assign_object", f, relating_object=site, products=[building])
        ifcopenshell.api.run("aggregate.assign_object", f, relating_object=building, products=[storey])

        # Geometry extraction
        span_m = float(parameters.get("span_length_m", 10.0))
        cant_m = float(parameters.get("cantilever_length_m", 0.0))
        bh_cm = float(parameters.get("beam_height_cm", 30.0))
        bw_cm = float(parameters.get("beam_width_cm", 20.0))
        col_h_m = float(parameters.get("column_height_m", 3.2))
        col_sec_cm = float(parameters.get("column_section_cm", 20.0))
        fck_mpa = float(parameters.get("concrete_fck_mpa", 30.0))

        # Adjust dimensions if variant is applied
        if variant:
            strat = variant.get("strategy_name", "")
            if "Protensão" in strat:
                bh_cm = max(bh_cm - 4.0, 24.0)
            elif "Vierendeel" in strat:
                bh_cm = col_h_m * 100.0  # Full floor depth

        # Columns
        col1 = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcColumn", name="Pilar_P1_Esquerdo")
        col2 = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcColumn", name="Pilar_P2_Direito")
        ifcopenshell.api.run("spatial.assign_container", f, relating_structure=storey, products=[col1, col2])

        pset_col1 = ifcopenshell.api.run("pset.add_pset", f, product=col1, name="Pset_ColumnCommon")
        ifcopenshell.api.run("pset.edit_pset", f, pset=pset_col1, properties={"Height": col_h_m * 1000.0, "CrossSection": f"{col_sec_cm}x{col_sec_cm}"})

        pset_col2 = ifcopenshell.api.run("pset.add_pset", f, product=col2, name="Pset_ColumnCommon")
        ifcopenshell.api.run("pset.edit_pset", f, pset=pset_col2, properties={"Height": col_h_m * 1000.0, "CrossSection": f"{col_sec_cm}x{col_sec_cm}"})

        # Main Beam
        beam_title = f"Viga_V101_Vao_{span_m:.1f}m"
        beam = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBeam", name=beam_title)
        ifcopenshell.api.run("spatial.assign_container", f, relating_structure=storey, products=[beam])

        pset_beam = ifcopenshell.api.run("pset.add_pset", f, product=beam, name="Pset_BeamCommon")
        ifcopenshell.api.run("pset.edit_pset", f, pset=pset_beam, properties={
            "Span": span_m,
            "Length": span_m + cant_m,
            "Width": bw_cm * 10.0,
            "Depth": bh_cm * 10.0,
        })

        # Custom Structura.AI Property Set (Compliance, Cost & Carbon)
        pset_structura = ifcopenshell.api.run("pset.add_pset", f, product=beam, name="Pset_StructuraCompliance")
        structura_props = {
            "ComplianceStandard": "ABNT NBR 6118:2023",
            "ConcreteFckMpa": fck_mpa,
            "EngineSolver": "Direct Stiffness Method (DSM) Frame Engine",
        }
        if analysis_data:
            structura_props["StructuralScore"] = float(analysis_data.get("structural_score", 100.0))
            structura_props["MaxDeflectionMm"] = float(analysis_data.get("max_deflection_mm", 0.0))
            structura_props["AllowableDeflectionMm"] = float(analysis_data.get("allowable_deflection_mm", 0.0))
            structura_props["IsViable"] = bool(analysis_data.get("is_physically_viable", True))
        if variant:
            structura_props["RedesignVariantStrategy"] = variant.get("strategy_name", "")
            structura_props["VariantNumber"] = int(variant.get("variant_number", 1))

        ifcopenshell.api.run("pset.edit_pset", f, pset=pset_structura, properties=structura_props)

        # Slab
        slab = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSlab", name="Laje_Cobertura")
        ifcopenshell.api.run("spatial.assign_container", f, relating_structure=storey, products=[slab])
        pset_slab = ifcopenshell.api.run("pset.add_pset", f, product=slab, name="Pset_SlabCommon")
        ifcopenshell.api.run("pset.edit_pset", f, pset=pset_slab, properties={"Thickness": 120.0})

        # Output to string
        with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            f.write(tmp_path)
            with open(tmp_path, "r", encoding="utf-8", errors="replace") as rf:
                content = rf.read()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        return content

    @classmethod
    def export_project_dxf(
        cls,
        project_title: str,
        parameters: Dict[str, Any],
        analysis_data: Optional[Dict[str, Any]] = None,
        variant: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generates standard AutoCAD DXF (R2010) drawing string containing
        columns, beams, dimensions, axis, and technical compliance table.
        """
        doc = ezdxf.new("R2010", setup=True)
        doc.units = units.M
        msp = doc.modelspace()

        # Normative layers
        doc.layers.add("ESTRUTURA_PILARES", color=ezdxf.colors.BLUE)
        doc.layers.add("ESTRUTURA_VIGAS", color=ezdxf.colors.CYAN)
        doc.layers.add("ESTRUTURA_EIXOS", color=ezdxf.colors.RED, linetype="DASHDOT")
        doc.layers.add("COTAS_DIMENSOES", color=ezdxf.colors.GREEN)
        doc.layers.add("LAUDO_ESTRUTURAL_NBR6118", color=ezdxf.colors.YELLOW)

        span_m = float(parameters.get("span_length_m", 10.0))
        cant_m = float(parameters.get("cantilever_length_m", 0.0))
        bh_cm = float(parameters.get("beam_height_cm", 30.0))
        bw_cm = float(parameters.get("beam_width_cm", 20.0))
        col_w_m = float(parameters.get("column_section_cm", 20.0)) / 100.0
        bw_m = bw_cm / 100.0
        bh_m = bh_cm / 100.0

        variant_title = variant.get("title", "Estrutura Original") if variant else "Estrutura Original"

        # Pillars
        half_cw = col_w_m / 2.0
        p1_pts = [(-half_cw, -col_w_m), (half_cw, -col_w_m), (half_cw, col_w_m), (-half_cw, col_w_m), (-half_cw, -col_w_m)]
        p2_pts = [(span_m - half_cw, -col_w_m), (span_m + half_cw, -col_w_m), (span_m + half_cw, col_w_m), (span_m - half_cw, col_w_m), (span_m - half_cw, -col_w_m)]
        msp.add_lwpolyline(p1_pts, dxfattribs={"layer": "ESTRUTURA_PILARES"})
        msp.add_lwpolyline(p2_pts, dxfattribs={"layer": "ESTRUTURA_PILARES"})

        # Beam lines
        half_bw = bw_m / 2.0
        msp.add_line((0.0, -half_bw), (span_m, -half_bw), dxfattribs={"layer": "ESTRUTURA_VIGAS"})
        msp.add_line((0.0, half_bw), (span_m, half_bw), dxfattribs={"layer": "ESTRUTURA_VIGAS"})

        # Beam center axis
        msp.add_line((-1.0, 0.0), (span_m + cant_m + 1.0, 0.0), dxfattribs={"layer": "ESTRUTURA_EIXOS"})

        # Cantilever if present
        if cant_m > 0:
            msp.add_line((span_m, -half_bw), (span_m + cant_m, -half_bw), dxfattribs={"layer": "ESTRUTURA_VIGAS"})
            msp.add_line((span_m, half_bw), (span_m + cant_m, half_bw), dxfattribs={"layer": "ESTRUTURA_VIGAS"})
            msp.add_line((span_m + cant_m, -half_bw), (span_m + cant_m, half_bw), dxfattribs={"layer": "ESTRUTURA_VIGAS"})
            msp.add_text(f"BALANÇO {cant_m:.2f}m", dxfattribs={"layer": "COTAS_DIMENSOES", "height": 0.25}).set_placement((span_m + 0.2, 0.35))

        # Annotations & Technical Text
        msp.add_text("P1 (20x20)", dxfattribs={"layer": "ESTRUTURA_PILARES", "height": 0.25}).set_placement((-0.8, -1.4))
        msp.add_text("P2 (20x20)", dxfattribs={"layer": "ESTRUTURA_PILARES", "height": 0.25}).set_placement((span_m - 0.4, -1.4))
        msp.add_text(f"VIGA V101 ({int(bw_cm)}x{int(bh_cm)}) — VÃO LIVRE {span_m:.2f}m", dxfattribs={"layer": "COTAS_DIMENSOES", "height": 0.3}).set_placement((span_m * 0.25, 0.4))

        # Technical compliance legend block
        y_legend = -2.5
        msp.add_text(f"STRUCTURA.AI — {project_title.upper()}", dxfattribs={"layer": "LAUDO_ESTRUTURAL_NBR6118", "height": 0.35}).set_placement((0.0, y_legend))
        msp.add_text(f"VARIANTE: {variant_title}", dxfattribs={"layer": "LAUDO_ESTRUTURAL_NBR6118", "height": 0.25}).set_placement((0.0, y_legend - 0.45))
        
        if analysis_data:
            score = analysis_data.get("structural_score", 100)
            defl = analysis_data.get("max_deflection_mm", 0)
            adm = analysis_data.get("allowable_deflection_mm", 0)
            status_text = "CONFORME NBR 6118" if analysis_data.get("is_physically_viable") else "REPROVADO POR FLECHA (ELS)"
            msp.add_text(f"STATUS FÍSICO: {status_text} | SCORE: {score}/100", dxfattribs={"layer": "LAUDO_ESTRUTURAL_NBR6118", "height": 0.22}).set_placement((0.0, y_legend - 0.85))
            msp.add_text(f"FLECHA CALCULADA: {defl}mm (LIMITE NBR: {adm}mm)", dxfattribs={"layer": "LAUDO_ESTRUTURAL_NBR6118", "height": 0.22}).set_placement((0.0, y_legend - 1.20))

        # Write to string
        s_out = io.StringIO()
        doc.write(s_out)
        return s_out.getvalue()
