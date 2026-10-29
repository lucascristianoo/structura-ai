"""
Orchestration Service for Structura.AI.
Combines Structural Physics, Google Gemini Vision, and Generative Redesigns.
"""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from structura_ai.models import Project, AnalysisResult, RedesignVariant
from structura_ai.physics.structural_core import StructuralCoreEngine
from structura_ai.physics.generator import RedesignGenerator
from structura_ai.ai.gemini_client import GeminiVisionClient
from structura_ai.services.sample_projects import SAMPLE_PRESETS

class AnalyzerService:

    @classmethod
    async def process_project_analysis(
        cls,
        db: AsyncSession,
        project_id: str,
        image_bytes: Optional[bytes] = None,
        image_mime: str = "image/png"
    ) -> AnalysisResult:
        """
        Executes full physical analysis, AI review, and generates 5 redesign variants.
        Persists results into the database.
        """
        # Fetch project
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        params = project.parameters or {}

        # Extract numerical parameters with robust defaults
        span = float(params.get("span_length_m", 9.5))
        cantilever = float(params.get("cantilever_length_m", 3.5))
        beam_h = float(params.get("beam_height_cm", 30.0))
        beam_w = float(params.get("beam_width_cm", 20.0))
        col_h = float(params.get("column_height_m", 3.2))
        col_sec = float(params.get("column_section_cm", 20.0))
        dead_load = float(params.get("dead_load_kpa", 4.5))
        live_load = float(params.get("live_load_kpa", 2.5))
        fck = float(params.get("concrete_fck_mpa", 30.0))

        # 1. Deterministic Physical Calculation
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
            category=project.category
        )

        # 2. Google Gemini Vision Analysis
        ai_output = await GeminiVisionClient.analyze_project(
            project_title=project.title,
            category=project.category,
            evaluation=evaluation,
            image_bytes=image_bytes,
            image_mime=image_mime
        )

        # 3. Create Analysis Record
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
            ai_gemini_review=ai_output.get("review"),
            ai_model_used=ai_output.get("model", "gemini-2.5-flash")
        )

        db.add(analysis)
        await db.flush()  # Flush to get analysis.id

        # 4. Generate the 5 Visual Redesign Proposals
        # Generated whenever the project has failures or recommendations
        variants_data = RedesignGenerator.generate_5_variants(evaluation)
        for v in variants_data:
            variant_obj = RedesignVariant(
                analysis_id=analysis.id,
                variant_number=v["variant_number"],
                title=v["title"],
                strategy_name=v["strategy_name"],
                architectural_concept=v["architectural_concept"],
                engineering_solution=v["engineering_solution"],
                metrics_delta=v["metrics_delta"],
                svg_render=v.get("svg_render"),
                visual_features=v.get("visual_features", []),
                pitch_narrative=v.get("pitch_narrative")
            )
            db.add(variant_obj)

        project.status = "analyzed"
        await db.commit()
        await db.refresh(analysis)
        return analysis

    @classmethod
    async def create_from_preset(cls, db: AsyncSession, preset_key: str) -> Project:
        """Creates a project directly from a preloaded HackTown preset."""
        preset = SAMPLE_PRESETS.get(preset_key)
        if not preset:
            preset = SAMPLE_PRESETS["residencia_vao_livre_critico"]

        project = Project(
            title=preset["title"],
            author_architect=preset["author_architect"],
            category=preset["category"],
            description=preset["description"],
            parameters={
                "span_length_m": preset["span_length_m"],
                "cantilever_length_m": preset["cantilever_length_m"],
                "beam_height_cm": preset["beam_height_cm"],
                "beam_width_cm": preset["beam_width_cm"],
                "column_height_m": preset["column_height_m"],
                "column_section_cm": preset["column_section_cm"],
                "dead_load_kpa": preset["dead_load_kpa"],
                "live_load_kpa": preset["live_load_kpa"],
                "concrete_fck_mpa": preset["concrete_fck_mpa"],
            },
            status="pending"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project
