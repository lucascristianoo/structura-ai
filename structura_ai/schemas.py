from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ============================================================================
# SCHEMAS DE ARQUIVOS & VERSIONAMENTO (v1 .. vn) & ESTILO (AutoCAD, Blender)
# ============================================================================
class FileVersionOut(BaseModel):
    id: str
    file_id: str
    version_number: int
    version_label: str  # "v1", "v2", ..., "vn"
    render_style: str   # "autocad", "blender", "wireframe", "landscape_insight"
    landscape_context: Optional[str] = None
    file_path: Optional[str] = None
    image_url: Optional[str] = None
    generated_code: Optional[str] = None
    code_language: Optional[str] = None
    structural_parameters: Dict[str, Any] = {}
    validation_report: Dict[str, Any] = {}
    change_summary: Optional[str] = None
    created_by: str = "user_upload"
    created_at: str


class ProjectFileOut(BaseModel):
    id: str
    user_id: str
    project_id: Optional[str] = None
    filename: str
    file_format: str
    active_version_number: int
    is_selected: bool
    created_at: str
    active_version: Optional[FileVersionOut] = None
    versions: List[FileVersionOut] = []


class SelectFileRequest(BaseModel):
    user_id: str = Field(default="default_user")


class SwitchVersionRequest(BaseModel):
    version_number: int = Field(..., ge=1, description="Número da versão (1 para v1, 2 para v2, etc.)")
    user_id: str = Field(default="default_user")


class ChangeStyleRequest(BaseModel):
    render_style: str = Field(..., examples=["autocad", "blender", "wireframe", "landscape_insight"])
    landscape_context: Optional[str] = Field(None, examples=["encosta_montanhosa", "urbano_denso", "litoral_maresia"])
    create_new_version: bool = Field(default=True, description="Se True, cria uma nova versão vN+1 com o novo estilo")
    user_id: str = Field(default="default_user")


class GenerateCodeRequest(BaseModel):
    target_format: str = Field(default="autocad", examples=["autocad", "blender", "ifc"])
    instructions: str = Field(..., examples=["Aumentar altura da viga principal para 55cm e adicionar pilar central"])
    structural_overrides: Dict[str, Any] = Field(default_factory=dict)
    user_id: str = Field(default="default_user")


# ============================================================================
# SCHEMAS DE CHAT & ORQUESTRAÇÃO DE AGENTES (PADRÃO LEMBRY + EXCALIDRAW)
# ============================================================================
class UIStateMutation(BaseModel):
    action: str  # "file_selected", "version_switched", "version_created", "style_changed", "validation_completed"
    file_id: Optional[str] = None
    version_number: Optional[int] = None
    version_label: Optional[str] = None
    render_style: Optional[str] = None
    image_url: Optional[str] = None
    details: Dict[str, Any] = {}


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="Mensagem enviada pelo arquiteto no Chat")
    user_id: str = Field(default="default_user", description="ID do usuário")
    session_id: str = Field(default="default_session", description="ID da sessão de conversa")
    active_file_id: Optional[str] = Field(None, description="ID do arquivo atualmente selecionado na tela")
    region_country: str = Field(default="BR", description="País/Região do projeto (ex: BR, US, EU, JP)")
    selected_format: str = Field(default="autocad", description="Formato de software selecionado no topo (autocad, blender, ifc, grasshopper_rhino, openscad)")
    force_memory_flush: bool = Field(default=False, description="Força fechamento e consolidação de episódio EverMemOS")


class ChatMessageResponse(BaseModel):
    reply: str
    session_id: str
    user_id: str
    active_file: Optional[ProjectFileOut] = None
    ui_mutations: List[UIStateMutation] = []
    suggestions: List[str] = []


# ============================================================================
# SCHEMAS DO BANCO DE DADOS (MEMÓRIA & TABELA VETORIAL RAG)
# ============================================================================
class KnowledgeCreateRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="Null para norma global; preenchido para conhecimento do usuário")
    category: str = Field(
        default="norma_nacional",
        examples=["norma_nacional", "norma_internacional", "calculo_estrutural", "edificacao_tipologia", "relevo_geotecnia", "projeto_usuario"],
    )
    region_country: str = Field(default="BR", examples=["BR", "US", "EU", "JP", "GLOBAL"])
    title: str
    content: str
    technical_metadata: Dict[str, Any] = {}


class KnowledgeItemOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    category: str
    region_country: str
    title: str
    content: str
    technical_metadata: Dict[str, Any] = {}
    score: Optional[float] = None
    created_at: str


class UserMemoryOut(BaseModel):
    id: str
    user_id: str
    session_id: Optional[str] = None
    file_id: Optional[str] = None
    memory_type: str
    title: Optional[str] = None
    content: str
    decisions_metadata: Dict[str, Any] = {}
    created_at: str


# ============================================================================
# SCHEMAS DE PROJETO E MOTOR FÍSICO
# ============================================================================
class ProjectCreateRequest(BaseModel):
    title: str = Field(..., examples=["Residência Minimalista Vão Livre"])
    author_architect: Optional[str] = Field("Arquiteto Autor")
    category: Optional[str] = Field("Residencial")
    description: Optional[str] = Field("")
    span_length_m: Optional[float] = Field(9.5)
    cantilever_length_m: Optional[float] = Field(3.8)
    beam_height_cm: Optional[float] = Field(30.0)
    beam_width_cm: Optional[float] = Field(20.0)
    column_height_m: Optional[float] = Field(3.2)
    column_section_cm: Optional[float] = Field(20.0)
    dead_load_kpa: Optional[float] = Field(4.5)
    live_load_kpa: Optional[float] = Field(2.5)
    concrete_fck_mpa: Optional[float] = Field(30.0)


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
    type: str
    start: CanvasPoint
    end: Optional[CanvasPoint] = None
    properties: Dict[str, Any] = {}


class CanvasFloorplanPayload(BaseModel):
    title: str = "Planta Baixa Interativa"
    elements: List[CanvasElement] = []
    scale_pixels_per_meter: float = 40.0
