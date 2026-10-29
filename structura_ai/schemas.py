from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ProjectCreateRequest(BaseModel):
    title: str = Field(..., examples=["Residência Minimalista Vão Livre"])
    author_architect: Optional[str] = Field("Arquiteto Autor", examples=["Studio Arq & Design"])
    category: Optional[str] = Field("Residencial", examples=["Residencial"])
    description: Optional[str] = Field("", examples=["Projeto com grande sala de estar e balanço frontal para vista panorâmica."])
    
    # Structural initial parameters (if manually supplied or tweaked)
    span_length_m: Optional[float] = Field(9.5, description="Maior vão livre em metros", examples=[9.5])
    cantilever_length_m: Optional[float] = Field(3.8, description="Comprimento do balanço em metros", examples=[3.8])
    beam_height_cm: Optional[float] = Field(30.0, description="Altura estimada da viga em centímetros", examples=[30.0])
    beam_width_cm: Optional[float] = Field(20.0, description="Largura da viga em centímetros", examples=[20.0])
    column_height_m: Optional[float] = Field(3.2, description="Altura livre do pilar (pé-direito)", examples=[3.2])
    column_section_cm: Optional[float] = Field(20.0, description="Seção transversal do pilar (20x20 cm)", examples=[20.0])
    dead_load_kpa: Optional[float] = Field(4.5, description="Carga permanente (peso próprio + revestimentos kN/m²)", examples=[4.5])
    live_load_kpa: Optional[float] = Field(2.5, description="Sobrecarga de uso NBR 6120 (kN/m²)", examples=[2.5])
    concrete_fck_mpa: Optional[float] = Field(30.0, description="Resistência do concreto fck (MPa)", examples=[30.0])
    use_preset: Optional[str] = Field(None, description="Preset pré-configurado para demonstração")

class RedesignVariantOut(BaseModel):
    variant_number: int
    title: str
    strategy_name: str
    architectural_concept: str
    engineering_solution: str
    metrics_delta: Dict[str, Any]
    svg_render: Optional[str] = None
    visual_features: List[str] = []
    pitch_narrative: Optional[str] = None

class AnalysisResultOut(BaseModel):
    id: str
    project_id: str
    is_physically_viable: bool
    structural_score: float
    compliance_level: str
    max_deflection_mm: float
    allowable_deflection_mm: float
    deflection_ratio: float
    max_bending_moment_knm: float
    shear_utilization_ratio: float
    critical_column_buckling_ratio: float
    cantilever_stability_factor: float
    failure_reasons: List[str]
    compliance_checklist: Dict[str, Any]
    structural_diagnosis_text: Optional[str]
    ai_gemini_review: Optional[str]
    ai_model_used: Optional[str]
    variants: List[RedesignVariantOut] = []

class ProjectOut(BaseModel):
    id: str
    title: str
    author_architect: str
    category: str
    description: Optional[str]
    image_filename: Optional[str]
    image_path: Optional[str] = None
    parameters: Dict[str, Any]
    status: str
    created_at: str
    latest_analysis: Optional[AnalysisResultOut] = None

class CanvasPoint(BaseModel):
    x: float
    y: float

class CanvasElement(BaseModel):
    id: str
    type: str  # "column", "beam", "wall", "slab", "cantilever", "load"
    start: CanvasPoint
    end: Optional[CanvasPoint] = None
    properties: Dict[str, Any] = {}

class CanvasFloorplanPayload(BaseModel):
    title: str = "Planta Baixa Interativa"
    elements: List[CanvasElement] = []
    scale_pixels_per_meter: float = 40.0
