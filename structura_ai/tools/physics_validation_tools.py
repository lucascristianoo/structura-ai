"""
Tools determinísticas do Agente Validador (Excalidraw: "Agente validador (valida se os calculos fazem sentido)").
Conecta o motor físico (`StructuralCoreEngine`, `DSMSolver2D`, `OptiSectionEngine`) ao banco de dados.
"""

import json
from typing import Optional
from agno.run import RunContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from structura_ai.database import AsyncSessionLocal
from structura_ai.models import ProjectFile, UserMemoryDecision
from structura_ai.physics.dsm_solver import DSMSolver
from structura_ai.physics.optisection import OptiSectionEngine
from structura_ai.physics.structural_core import StructuralCoreEngine
from structura_ai.tools.file_version_tools import _register_ui_mutation


async def validate_structural_calculations(
    run_context: RunContext,
    span_length_m: Optional[float] = None,
    cantilever_length_m: Optional[float] = None,
    beam_height_cm: Optional[float] = None,
    beam_width_cm: Optional[float] = None,
    column_height_m: Optional[float] = None,
    column_section_cm: Optional[float] = None,
    concrete_fck_mpa: Optional[float] = None,
    occupancy_category: str = "Residencial",
    region_country: str = "BR",
) -> str:
    """
    Executa validação físico-matemática completa (Euler-Bernoulli, Método da Rigidez Direta DSM 2D,
    flambagem de Euler e verificação normativa NBR 6118 / Eurocode 2 / ACI 318 / BSLJ) para verificar
    se os cálculos e dimensões estruturais fazem sentido.

    Se os parâmetros forem omitidos, lê automaticamente os parâmetros da versão ativa do arquivo selecionado.
    """
    deps = (run_context.dependencies if run_context else None) or {}
    user_id = deps.get("user_id", "default_user")
    target_file_id = deps.get("active_file_id")

    async with AsyncSessionLocal() as db:
        pf = None
        if target_file_id:
            stmt = select(ProjectFile).options(selectinload(ProjectFile.versions)).where(ProjectFile.id == target_file_id)
            res = await db.execute(stmt)
            pf = res.scalar_one_or_none()
        if not pf:
            stmt = (
                select(ProjectFile)
                .options(selectinload(ProjectFile.versions))
                .where(ProjectFile.user_id == user_id, ProjectFile.is_selected.is_(True))
            )
            res = await db.execute(stmt)
            pf = res.scalar_one_or_none()

        current_ver = None
        file_params = {}
        if pf and pf.versions:
            current_ver = next(
                (v for v in pf.versions if v.version_number == pf.active_version_number),
                pf.versions[-1],
            )
            file_params = dict(current_ver.structural_parameters or {})

        span = float(span_length_m if span_length_m is not None else file_params.get("span_length_m", 9.5))
        cantilever = float(cantilever_length_m if cantilever_length_m is not None else file_params.get("cantilever_length_m", 3.5))
        beam_h = float(beam_height_cm if beam_height_cm is not None else file_params.get("beam_height_cm", 35.0))
        beam_w = float(beam_width_cm if beam_width_cm is not None else file_params.get("beam_width_cm", 20.0))
        col_h = float(column_height_m if column_height_m is not None else file_params.get("column_height_m", 3.2))
        col_sec = float(column_section_cm if column_section_cm is not None else file_params.get("column_section_cm", 25.0))
        fck = float(concrete_fck_mpa if concrete_fck_mpa is not None else file_params.get("concrete_fck_mpa", 30.0))

        core_eval = StructuralCoreEngine.evaluate_structure(
            span_length_m=span,
            cantilever_length_m=cantilever,
            beam_height_cm=beam_h,
            beam_width_cm=beam_w,
            column_height_m=col_h,
            column_section_cm=col_sec,
            concrete_fck_mpa=fck,
            category=occupancy_category,
        )

        dsm_eval = DSMSolver.solve_portal_frame(
            span_length_m=span,
            cantilever_length_m=cantilever,
            column_height_m=col_h,
            beam_width_cm=beam_w,
            beam_height_cm=beam_h,
            column_section_cm=col_sec,
        )

        opti_eval = OptiSectionEngine.optimize_beam_section(
            span_length_m=span,
            concrete_fck_mpa=fck,
            current_beam_height_cm=beam_h,
            current_beam_width_cm=beam_w,
        )
        slim_rc = opti_eval.get("optimal_concrete_slim") or {}
        recommended_h_cm = slim_rc.get("height_cm", max(beam_h, round(span * 100.0 / 12.0, 0)))

        # Adequação de Norma Regional (BR vs Exterior)
        reg = (region_country or deps.get("region_country", "BR")).upper()
        norm_reference = "ABNT NBR 6118:2023 (Brasil)"
        international_notes = []
        if reg == "US":
            norm_reference = "ACI 318-19 / ASCE 7-22 (EUA)"
            allowable_us = (span * 1000.0) / 360.0
            international_notes.append(
                f"Critério ACI 318 (L/360 sobrecarga imediata): limite {allowable_us:.1f}mm vs calculado {core_eval['max_deflection_mm']:.1f}mm."
            )
        elif reg == "EU":
            norm_reference = "Eurocode 2 EN 1992-1-1 / EN 1998 (União Europeia)"
            international_notes.append(
                f"Critério Eurocode 2 (L/250 quase-permanente, L/500 divisórias frágeis = {(span*1000.0)/500.0:.1f}mm)."
            )
        elif reg == "JP":
            norm_reference = "Building Standard Law of Japan (BSLJ / AIJ)"
            international_notes.append(
                "Critério Sísmico BSLJ Japão: balanços > 2.5m exigem verificação de aceleração vertical sísmica e drift inter-pavimento <= 1/200."
            )

        validation_summary = {
            "norm_reference": norm_reference,
            "region_country": reg,
            "parameters_tested": {
                "span_length_m": span,
                "cantilever_length_m": cantilever,
                "beam_height_cm": beam_h,
                "beam_width_cm": beam_w,
                "column_height_m": col_h,
                "column_section_cm": col_sec,
                "concrete_fck_mpa": fck,
            },
            "is_physically_viable": core_eval["is_physically_viable"],
            "structural_score": core_eval["structural_score"],
            "compliance_level": core_eval["compliance_level"],
            "max_deflection_mm": core_eval["max_deflection_mm"],
            "allowable_deflection_mm": core_eval["allowable_deflection_mm"],
            "deflection_ratio": core_eval["deflection_ratio"],
            "max_bending_moment_knm": core_eval["max_bending_moment_knm"],
            "shear_utilization_ratio": core_eval["shear_utilization_ratio"],
            "critical_column_buckling_ratio": core_eval["critical_column_buckling_ratio"],
            "failure_reasons": core_eval["failure_reasons"],
            "dsm_midspan_deflection_mm": dsm_eval.get("exact_midspan_deflection_mm"),
            "recommended_minimum_beam_height_cm": recommended_h_cm,
            "international_notes": international_notes,
            "diagnosis": core_eval["structural_diagnosis_text"],
        }

        if current_ver is not None:
            current_ver.validation_report = validation_summary
            current_ver.structural_parameters = validation_summary["parameters_tested"]

        db.add(
            UserMemoryDecision(
                user_id=user_id,
                session_id=run_context.session_id if run_context else None,
                file_id=pf.id if pf else None,
                memory_type="decision",
                title=f"Validação Estrutural ({norm_reference}): {core_eval['compliance_level']}",
                content=core_eval["structural_diagnosis_text"],
                decisions_metadata=validation_summary,
            )
        )
        await db.commit()

        _register_ui_mutation(
            run_context,
            {
                "action": "validation_completed",
                "file_id": pf.id if pf else None,
                "version_number": current_ver.version_number if current_ver else 1,
                "version_label": current_ver.version_label if current_ver else "v1",
                "details": validation_summary,
            },
        )

        return json.dumps(validation_summary, ensure_ascii=False)
