"""
Tool de Código (Excalidraw: "Tool de codigo para gerar o que precisar na linguagem o formato do arquivo que vamos editar").

Gera e materializa código estrutural/geométrico para:
- AutoCAD / DXF (`ezdxf` + arquivo `.dxf` real no disco)
- Blender 3D (`bpy` script Python executável no Blender 4.x)
- IFC / BIM (`ifcopenshell` + arquivo `.ifc` real no disco)
E cria automaticamente uma nova versão `vN+1` no `ProjectFile` ativo!
"""

import json
import os
from typing import Optional
from agno.run import RunContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from structura_ai.cad.bim_exporter import BimExporter
from structura_ai.config import settings
from structura_ai.database import AsyncSessionLocal
from structura_ai.models import ProjectFile, FileVersion, UserMemoryDecision
from structura_ai.physics.structural_core import StructuralCoreEngine
from structura_ai.tools.file_version_tools import _build_styled_svg_preview, _register_ui_mutation


def _generate_autocad_ezdxf_script(
    filename: str,
    span_m: float,
    cantilever_m: float,
    beam_h_cm: float,
    beam_w_cm: float,
    col_h_m: float,
    col_sec_cm: float,
    fck_mpa: float,
    instructions: str,
) -> str:
    return f'''"""
AutoCAD / DXF Structural Script — Gerado pelo Structura.AI
Arquivo Base: {filename}
Instrução: {instructions}
"""
import ezdxf

def build_structural_dxf(output_path: str = "structura_generated.dxf"):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    doc.layers.add("STRUCT_COLUMNS", color=3)
    doc.layers.add("STRUCT_BEAMS", color=1)
    doc.layers.add("STRUCT_ANNOTATIONS", color=2)

    span_m = {span_m:.2f}
    cantilever_m = {cantilever_m:.2f}
    beam_h_m = {beam_h_cm / 100.0:.3f}
    beam_w_m = {beam_w_cm / 100.0:.3f}
    col_h_m = {col_h_m:.2f}
    col_w_m = {col_sec_cm / 100.0:.3f}

    # Pilares P1 e P2
    msp.add_lwpolyline(
        [(0, 0), (col_w_m, 0), (col_w_m, col_h_m), (0, col_h_m), (0, 0)],
        dxfattribs={{"layer": "STRUCT_COLUMNS"}},
    )
    msp.add_lwpolyline(
        [(span_m, 0), (span_m + col_w_m, 0), (span_m + col_w_m, col_h_m), (span_m, col_h_m), (span_m, 0)],
        dxfattribs={{"layer": "STRUCT_COLUMNS"}},
    )

    # Viga Principal + Balanço
    total_len = span_m + cantilever_m
    msp.add_lwpolyline(
        [(0, col_h_m), (total_len, col_h_m), (total_len, col_h_m + beam_h_m), (0, col_h_m + beam_h_m), (0, col_h_m)],
        dxfattribs={{"layer": "STRUCT_BEAMS"}},
    )

    msp.add_text(
        f"VIGA V1 ({{int(beam_w_m*100)}}x{{int(beam_h_m*100)}}cm) fck={int(fck_mpa)}MPa | Vao={span_m}m Balanco={cantilever_m}m",
        dxfattribs={{"layer": "STRUCT_ANNOTATIONS", "height": 0.22, "insert": (0.2, col_h_m + beam_h_m + 0.25)}},
    )
    doc.saveas(output_path)
    return output_path

if __name__ == "__main__":
    build_structural_dxf()
'''


def _generate_blender_bpy_script(
    filename: str,
    span_m: float,
    cantilever_m: float,
    beam_h_cm: float,
    beam_w_cm: float,
    col_h_m: float,
    col_sec_cm: float,
    fck_mpa: float,
    instructions: str,
) -> str:
    return f'''"""
Blender 4.x Python (bpy) Parametric Structural Generator — Structura.AI
Arquivo Base: {filename}
Instrução: {instructions}
"""
import bpy

def create_structural_frame():
    # Limpa objetos antigos da coleção Structura
    collection_name = "Structura_Parametric_Frame"
    if collection_name not in bpy.data.collections:
        col = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(col)
    else:
        col = bpy.data.collections[collection_name]

    span_m = {span_m:.2f}
    cantilever_m = {cantilever_m:.2f}
    beam_h = {beam_h_cm / 100.0:.3f}
    beam_w = {beam_w_cm / 100.0:.3f}
    col_h = {col_h_m:.2f}
    col_sec = {col_sec_cm / 100.0:.3f}

    # Material Concreto fck {int(fck_mpa)} MPa
    mat = bpy.data.materials.new(name="Concrete_fck_{int(fck_mpa)}MPa")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.62, 0.64, 0.67, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.75

    # Pilar P1 (x = 0)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, col_h / 2.0))
    p1 = bpy.context.active_object
    p1.name = "Pilar_P1"
    p1.scale = (col_sec, col_sec, col_h)
    p1.data.materials.append(mat)

    # Pilar P2 (x = span_m)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(span_m, 0.0, col_h / 2.0))
    p2 = bpy.context.active_object
    p2.name = "Pilar_P2"
    p2.scale = (col_sec, col_sec, col_h)
    p2.data.materials.append(mat)

    # Viga Principal + Balanço
    total_len = span_m + cantilever_m
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(total_len / 2.0, 0.0, col_h + beam_h / 2.0),
    )
    beam = bpy.context.active_object
    beam.name = f"Viga_V1_{{int(beam_w*100)}}x{{int(beam_h*100)}}cm"
    beam.scale = (total_len, beam_w, beam_h)
    beam.data.materials.append(mat)

    if __name__ == "__main__":
        create_structural_frame()
'''


def _generate_grasshopper_rhino_script(
    filename: str,
    span_m: float,
    cantilever_m: float,
    beam_h_cm: float,
    beam_w_cm: float,
    col_h_m: float,
    col_sec_cm: float,
    fck_mpa: float,
    instructions: str,
) -> str:
    return f'''"""
Rhino 8 / Grasshopper GhPython Structural Generator — Structura.AI
Arquivo Base: {filename}
Instrução: {instructions}
"""
import rhinoscriptsyntax as rs

def build_rhino_parametric_frame():
    span_m = {span_m:.2f}
    cant_m = {cantilever_m:.2f}
    beam_h = {beam_h_cm / 100.0:.3f}
    beam_w = {beam_w_cm / 100.0:.3f}
    col_h = {col_h_m:.2f}
    col_sec = {col_sec_cm / 100.0:.3f}

    # Pilares P1 e P2
    p1 = rs.AddBox([(0,0,0),(col_sec,0,0),(col_sec,col_sec,0),(0,col_sec,0),(0,0,col_h),(col_sec,0,col_h),(col_sec,col_sec,col_h),(0,col_sec,col_h)])
    p2 = rs.AddBox([(span_m,0,0),(span_m+col_sec,0,0),(span_m+col_sec,col_sec,0),(span_m,col_sec,0),(span_m,0,col_h),(span_m+col_sec,0,col_h),(span_m+col_sec,col_sec,col_h),(span_m,col_sec,col_h)])

    # Viga Principal + Balanço (fck={int(fck_mpa)} MPa)
    total_l = span_m + cant_m
    v1 = rs.AddBox([(0,0,col_h),(total_l,0,col_h),(total_l,beam_w,col_h),(0,beam_w,col_h),(0,0,col_h+beam_h),(total_l,0,col_h+beam_h),(total_l,beam_w,col_h+beam_h),(0,beam_w,col_h+beam_h)])
    return [p1, p2, v1]
'''


def _generate_openscad_script(
    filename: str,
    span_m: float,
    cantilever_m: float,
    beam_h_cm: float,
    beam_w_cm: float,
    col_h_m: float,
    col_sec_cm: float,
    fck_mpa: float,
    instructions: str,
) -> str:
    return f'''// OpenSCAD Parametric Structural Model — Structura.AI
// Arquivo Base: {filename} | fck = {int(fck_mpa)} MPa
// Instrução: {instructions}

span_m = {span_m:.2f};
cantilever_m = {cantilever_m:.2f};
beam_h = {beam_h_cm / 100.0:.3f};
beam_w = {beam_w_cm / 100.0:.3f};
col_h = {col_h_m:.2f};
col_sec = {col_sec_cm / 100.0:.3f};

union() {{
    // Pilar P1
    translate([0, 0, 0]) cube([col_sec, col_sec, col_h]);
    // Pilar P2
    translate([span_m, 0, 0]) cube([col_sec, col_sec, col_h]);
    // Viga V1 + Balanco
    translate([0, 0, col_h]) cube([span_m + cantilever_m, beam_w, beam_h]);
}}
'''


async def generate_cad_code_tool(
    run_context: RunContext,
    target_format: str,
    modification_instructions: str,
    span_length_m: Optional[float] = None,
    cantilever_length_m: Optional[float] = None,
    beam_height_cm: Optional[float] = None,
    beam_width_cm: Optional[float] = None,
    concrete_fck_mpa: Optional[float] = None,
) -> str:
    """
    Tool de Código (Excalidraw): Gera código executável e arquivo real na linguagem/formato
    do arquivo que estamos editando ('autocad'/'dxf', 'blender'/'bpy', ou 'ifc'/'bim'),
    aplicando as modificações estruturais/geométricas pedidas e criando uma nova versão vN+1.

    Args:
        target_format: Formato/linguagem alvo ('autocad', 'dxf', 'blender', 'ifc').
        modification_instructions: Descrição clara do que o código gerado deve alterar na estrutura.
        span_length_m: Opcional. Novo vão livre em metros.
        cantilever_length_m: Opcional. Novo balanço em metros.
        beam_height_cm: Opcional. Nova altura da viga em cm.
        beam_width_cm: Opcional. Nova largura da viga em cm.
        concrete_fck_mpa: Opcional. Novo fck do concreto em MPa.
    """
    deps = (run_context.dependencies if run_context else None) or {}
    user_id = deps.get("user_id", "default_user")
    target_file_id = deps.get("active_file_id")

    async with AsyncSessionLocal() as db:
        if target_file_id:
            stmt = (
                select(ProjectFile)
                .options(selectinload(ProjectFile.versions))
                .where(ProjectFile.id == target_file_id)
            )
        else:
            stmt = (
                select(ProjectFile)
                .options(selectinload(ProjectFile.versions))
                .where(ProjectFile.user_id == user_id, ProjectFile.is_selected.is_(True))
            )
        res = await db.execute(stmt)
        pf = res.scalar_one_or_none()

        # Se o usuário ainda não tinha um arquivo carregado, criamos um automaticamente para não travar a conversa!
        if not pf:
            pf = ProjectFile(
                user_id=user_id,
                filename=f"projeto_estrutural.{'blend' if 'blend' in target_format.lower() else 'dxf'}",
                file_format="blend" if "blend" in target_format.lower() else "dxf",
                active_version_number=1,
                is_selected=True,
            )
            db.add(pf)
            await db.flush()
            pf_versions = []
        else:
            pf_versions = list(pf.versions)

        current_ver = next(
            (v for v in pf_versions if v.version_number == pf.active_version_number),
            pf_versions[-1] if pf_versions else None,
        )
        params = dict(current_ver.structural_parameters or {}) if current_ver else {}

        span_m = float(span_length_m if span_length_m is not None else params.get("span_length_m", 9.5))
        cant_m = float(cantilever_length_m if cantilever_length_m is not None else params.get("cantilever_length_m", 3.5))
        beam_h = float(beam_height_cm if beam_height_cm is not None else params.get("beam_height_cm", 45.0))
        beam_w = float(beam_width_cm if beam_width_cm is not None else params.get("beam_width_cm", 20.0))
        col_h = float(params.get("column_height_m", 3.2))
        col_sec = float(params.get("column_section_cm", 25.0))
        fck = float(concrete_fck_mpa if concrete_fck_mpa is not None else params.get("concrete_fck_mpa", 35.0))

        params.update(
            {
                "span_length_m": span_m,
                "cantilever_length_m": cant_m,
                "beam_height_cm": beam_h,
                "beam_width_cm": beam_w,
                "column_height_m": col_h,
                "column_section_cm": col_sec,
                "concrete_fck_mpa": fck,
            }
        )

        # Roda avaliação física determinística sobre os novos parâmetros
        eval_report = StructuralCoreEngine.evaluate_structure(
            span_length_m=span_m,
            cantilever_length_m=cant_m,
            beam_height_cm=beam_h,
            beam_width_cm=beam_w,
            column_height_m=col_h,
            column_section_cm=col_sec,
            concrete_fck_mpa=fck,
        )

        next_num = (max((v.version_number for v in pf_versions), default=0)) + 1
        ver_label = f"v{next_num}"

        fmt = target_format.lower().strip()
        os.makedirs(settings.GENERATED_DIR, exist_ok=True)
        safe_base = "".join(c if c.isalnum() else "_" for c in pf.filename)[:25]

        if "blend" in fmt or "bpy" in fmt:
            code_lang = "python_blender_bpy"
            render_style = "blender"
            pf.file_format = "blend"
            code_str = _generate_blender_bpy_script(
                pf.filename, span_m, cant_m, beam_h, beam_w, col_h, col_sec, fck, modification_instructions
            )
            artifact_filename = f"{safe_base}_{ver_label}_blender.py"
            artifact_path = os.path.join(settings.GENERATED_DIR, artifact_filename)
            with open(artifact_path, "w", encoding="utf-8") as f:
                f.write(code_str)
        elif "rhino" in fmt or "grasshopper" in fmt:
            code_lang = "python_rhino_grasshopper"
            render_style = "blender"
            pf.file_format = "rhino_py"
            code_str = _generate_grasshopper_rhino_script(
                pf.filename, span_m, cant_m, beam_h, beam_w, col_h, col_sec, fck, modification_instructions
            )
            artifact_filename = f"{safe_base}_{ver_label}_rhino_gh.py"
            artifact_path = os.path.join(settings.GENERATED_DIR, artifact_filename)
            with open(artifact_path, "w", encoding="utf-8") as f:
                f.write(code_str)
        elif "scad" in fmt or "openscad" in fmt:
            code_lang = "openscad"
            render_style = "wireframe"
            pf.file_format = "scad"
            code_str = _generate_openscad_script(
                pf.filename, span_m, cant_m, beam_h, beam_w, col_h, col_sec, fck, modification_instructions
            )
            artifact_filename = f"{safe_base}_{ver_label}.scad"
            artifact_path = os.path.join(settings.GENERATED_DIR, artifact_filename)
            with open(artifact_path, "w", encoding="utf-8") as f:
                f.write(code_str)
        elif "ifc" in fmt or "bim" in fmt:
            code_lang = "ifc_bim"
            render_style = "autocad"
            pf.file_format = "ifc"
            ifc_str = BimExporter.export_project_ifc(
                project_title=pf.filename,
                parameters=params,
                analysis_data=eval_report,
            )
            artifact_filename = f"{safe_base}_{ver_label}.ifc"
            artifact_path = os.path.join(settings.GENERATED_DIR, artifact_filename)
            with open(artifact_path, "w", encoding="utf-8") as f:
                f.write(ifc_str)
            code_str = ifc_str[:4000]
        else:
            code_lang = "python_ezdxf_autocad"
            render_style = "autocad"
            pf.file_format = "dxf"
            code_str = _generate_autocad_ezdxf_script(
                pf.filename, span_m, cant_m, beam_h, beam_w, col_h, col_sec, fck, modification_instructions
            )
            dxf_str = BimExporter.export_project_dxf(
                project_title=pf.filename,
                parameters=params,
                analysis_data=eval_report,
            )
            artifact_filename = f"{safe_base}_{ver_label}.dxf"
            artifact_path = os.path.join(settings.GENERATED_DIR, artifact_filename)
            with open(artifact_path, "w", encoding="utf-8") as f:
                f.write(dxf_str)

        image_url = _build_styled_svg_preview(
            pf.filename,
            ver_label,
            render_style,
            params,
            current_ver.landscape_context if current_ver else None,
        )

        new_ver = FileVersion(
            file_id=pf.id,
            version_number=next_num,
            version_label=ver_label,
            render_style=render_style,
            landscape_context=current_ver.landscape_context if current_ver else None,
            file_path=f"/uploads/generated/{artifact_filename}",
            image_url=image_url,
            generated_code=code_str,
            code_language=code_lang,
            structural_parameters=params,
            validation_report={
                "is_physically_viable": eval_report["is_physically_viable"],
                "structural_score": eval_report["structural_score"],
                "compliance_level": eval_report["compliance_level"],
                "max_deflection_mm": eval_report["max_deflection_mm"],
                "allowable_deflection_mm": eval_report["allowable_deflection_mm"],
            },
            change_summary=f"[{code_lang}] {modification_instructions}",
            created_by="code_tool",
        )
        db.add(new_ver)
        pf.active_version_number = next_num

        db.add(
            UserMemoryDecision(
                user_id=user_id,
                session_id=run_context.session_id if run_context else None,
                file_id=pf.id,
                memory_type="decision",
                title=f"Código gerado ({code_lang}) -> {ver_label}",
                content=f"Gerada versão {ver_label} no formato {target_format}: {modification_instructions}",
                decisions_metadata={"version": ver_label, "format": target_format, "parameters": params},
            )
        )
        await db.commit()

        _register_ui_mutation(
            run_context,
            {
                "action": "version_created",
                "file_id": pf.id,
                "version_number": next_num,
                "version_label": ver_label,
                "render_style": render_style,
                "image_url": image_url,
                "details": {
                    "code_language": code_lang,
                    "download_url": f"/uploads/generated/{artifact_filename}",
                    "structural_parameters": params,
                    "validation_summary": new_ver.validation_report,
                },
            },
        )

        return json.dumps(
            {
                "status": "success",
                "file_id": pf.id,
                "filename": pf.filename,
                "new_version": ver_label,
                "render_style": render_style,
                "code_language": code_lang,
                "artifact_download_url": f"/uploads/generated/{artifact_filename}",
                "image_url": image_url,
                "structural_parameters": params,
                "validation_summary": new_ver.validation_report,
                "generated_code_preview": code_str[:1500],
            },
            ensure_ascii=False,
        )


async def convert_project_format_tool(
    run_context: RunContext,
    target_format: str,
    conversion_notes: str = "Conversão de formato solicitada pelo usuário",
) -> str:
    """
    Converte o projeto ativo do usuário para outro formato de software ('autocad'/'dxf', 'blender'/'bpy',
    'ifc'/'bim', 'grasshopper_rhino', 'openscad'), gerando o código/arquivo correspondente e criando uma nova versão.
    """
    return await generate_cad_code_tool(
        run_context=run_context,
        target_format=target_format,
        modification_instructions=f"[Conversão de Formato -> {target_format}] {conversion_notes}",
    )

