"""
Serviço determinístico de análise estrutural de projetos.
Executa o StructuralCoreEngine sem variantes estáticas ou mocks legados.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from structura_ai.models import Project, AnalysisResult
from structura_ai.physics.structural_core import StructuralCoreEngine


class AnalyzerService:

    @classmethod
    async def process_project_analysis(
        cls,
        db: AsyncSession,
        project_id: str,
        image_bytes: Optional[bytes] = None,
        image_mime: str = "image/png",
    ) -> AnalysisResult:
        """Executa a validação física determinística sobre os parâmetros do projeto e salva no banco."""
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        params = project.parameters or {}

        span = float(params.get("span_length_m", 9.5))
        cantilever = float(params.get("cantilever_length_m", 3.5))
        beam_h = float(params.get("beam_height_cm", 30.0))
        beam_w = float(params.get("beam_width_cm", 20.0))
        col_h = float(params.get("column_height_m", 3.2))
        col_sec = float(params.get("column_section_cm", 20.0))
        dead_load = float(params.get("dead_load_kpa", 4.5))
        live_load = float(params.get("live_load_kpa", 2.5))
        fck = float(params.get("concrete_fck_mpa", 30.0))

        evaluation = StructuralCoreEngine.evaluate_structure(
            span_length_m=span,
            cantilever_length_m=cantilever,
            beam_height_cm=beam_h,
            beam_width_cm=beam_w,
            column_height_m=col_h,
            column_section_cm=col_sec,
            dead_load_kpa=dead_load,
            live_load_kpa=live_load,
            concrete_fck_mpa=fck,
            category=project.category,
        )

        analysis = AnalysisResult(
            project_id=project.id,
            is_physically_viable=evaluation["is_physically_viable"],
            structural_score=evaluation["structural_score"],
            compliance_level=evaluation["compliance_level"],
            max_deflection_mm=evaluation["max_deflection_mm"],
            allowable_deflection_mm=evaluation["allowable_deflection_mm"],
            deflection_ratio=evaluation["deflection_ratio"],
            max_bending_moment_knm=evaluation["max_bending_moment_knm"],
            shear_utilization_ratio=evaluation["shear_utilization_ratio"],
            critical_column_buckling_ratio=evaluation["critical_column_buckling_ratio"],
            cantilever_stability_factor=evaluation["cantilever_stability_factor"],
            failure_reasons=evaluation["failure_reasons"],
            compliance_checklist=evaluation["compliance_checklist"],
            structural_diagnosis_text=evaluation["structural_diagnosis_text"],
            ai_gemini_review=evaluation["structural_diagnosis_text"],
            ai_model_used="gemini-2.5-flash",
        )

        db.add(analysis)
        project.status = "analyzed"
        await db.commit()
        await db.refresh(analysis)
        return analysis
