import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from structura_ai.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def get_utc_now():
    return datetime.now(timezone.utc)

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(200), nullable=False)
    author_architect = Column(String(120), default="Arquiteto Autor")
    category = Column(String(50), default="Residencial")
    description = Column(Text, nullable=True)
    
    # Uploaded image/blueprint metadata
    image_filename = Column(String(255), nullable=True)
    image_path = Column(String(500), nullable=True)
    blueprint_svg = Column(Text, nullable=True)  # Vector representation if generated/saved
    
    # Spatial parameters provided by architect or extracted
    parameters = Column(JSON, default=dict)
    
    status = Column(String(30), default="pending")  # pending, analyzed, failed
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Relationship to analysis results
    analyses = relationship("AnalysisResult", back_populates="project", cascade="all, delete-orphan")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    
    # Global verdict
    is_physically_viable = Column(Boolean, default=False)
    structural_score = Column(Float, default=0.0)  # 0 to 100
    compliance_level = Column(String(50), default="Crítico")  # "Aprovado", "Alerta", "Crítico/Reprovado"
    
    # Core structural engineering indicators
    max_deflection_mm = Column(Float, default=0.0)
    allowable_deflection_mm = Column(Float, default=0.0)
    deflection_ratio = Column(Float, default=0.0)  # max / allowable
    
    max_bending_moment_knm = Column(Float, default=0.0)
    shear_utilization_ratio = Column(Float, default=0.0)
    critical_column_buckling_ratio = Column(Float, default=0.0)
    cantilever_stability_factor = Column(Float, default=1.0)
    
    # Detailed diagnostics & breakdown
    failure_reasons = Column(JSON, default=list)  # List of identified physical violations
    compliance_checklist = Column(JSON, default=dict)  # NBR 6118 / ACI checklist
    structural_diagnosis_text = Column(Text, nullable=True)
    
    # Google Gemini AI Multi-modal review
    ai_gemini_review = Column(Text, nullable=True)
    ai_model_used = Column(String(100), default="gemini-2.5-flash")
    
    created_at = Column(DateTime, default=get_utc_now)

    project = relationship("Project", back_populates="analyses")
    variants = relationship("RedesignVariant", back_populates="analysis", cascade="all, delete-orphan")


class RedesignVariant(Base):
    __tablename__ = "redesign_variants"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analysis_results.id"), nullable=False)
    
    variant_number = Column(Integer, nullable=False)  # 1 to 5
    title = Column(String(200), nullable=False)
    strategy_name = Column(String(100), nullable=False)
    
    architectural_concept = Column(Text, nullable=False)
    engineering_solution = Column(Text, nullable=False)
    
    # Mathematical improvements compared to original
    metrics_delta = Column(JSON, default=dict)  # deflection_reduction, safety_factor, weight_delta, etc.
    
    # Visual graphics data
    svg_render = Column(Text, nullable=True)  # Dynamic 2D structural diagram
    visual_features = Column(JSON, default=list)  # Key elements to render
    
    # Client pitch & engineering rationale
    pitch_narrative = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_utc_now)

    analysis = relationship("AnalysisResult", back_populates="variants")
