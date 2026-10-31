import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from structura_ai.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================================
# TABELA 1 (Excalidraw): Memória, Histórico de Conversa e Decisões do Usuário
# ============================================================================
class UserMemoryDecision(Base):
    """
    Tabela a) memoria:
    ID user, historico de conversa, memoria, decisoes.
    Registra decisões arquitetônicas/estruturais, preferências de normas e histórico consolidado.
    """
    __tablename__ = "user_memory_decisions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(120), nullable=False, index=True, default="default_user")
    session_id = Column(String(120), nullable=True, index=True)
    file_id = Column(String(36), nullable=True, index=True)

    memory_type = Column(String(50), nullable=False, default="decision")
    # Tipos: "decision", "conversation_turn", "user_preference", "project_learning"

    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    decisions_metadata = Column(JSON, default=dict)

    created_at = Column(DateTime, default=get_utc_now)


# ============================================================================
# TABELA 2 (Excalidraw): Base Vetorial (tabela_vet) — Cálculos, Normas BR/Exterior, Relevo e Projetos
# ============================================================================
class KnowledgeVector(Base):
    """
    Tabela b) tabela_vet:
    Infos sobre cálculos, edificações para cada tipo de lugar, normas nacionais (NBR)
    e internacionais (Eurocode, ACI, ASCE), infos sobre relevo/solo e conhecimento
    gerado pelos próprios projetos avaliados do arquiteto.
    """
    __tablename__ = "knowledge_vectors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    # NULL = conhecimento técnico global; Preenchido = base de conhecimento do próprio usuário
    user_id = Column(String(120), nullable=True, index=True)

    category = Column(String(80), nullable=False, index=True, default="norma_nacional")
    # Categorias: "norma_nacional", "norma_internacional", "calculo_estrutural",
    #             "edificacao_tipologia", "relevo_geotecnia", "projeto_usuario"

    region_country = Column(String(80), nullable=False, index=True, default="BR")
    # Ex: "BR", "US", "EU", "JP", "CHILE_SISMICO", "GLOBAL"

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    technical_metadata = Column(JSON, default=dict)
    embedding = Column(JSON, default=list)  # Vetor denso normalizado (compatível com pgvector e SQLite)
    lifecycle = Column(String(30), nullable=False, default="active", index=True)

    created_at = Column(DateTime, default=get_utc_now)


# ============================================================================
# TABELA 3 (Excalidraw): Arquivos Carregados & Árvore de Versionamento (v1..vn) por Arquivo
# ============================================================================
class ProjectFile(Base):
    """
    Representa cada arquivo carregado pelo arquiteto.
    Quando o arquivo ativo é alternado no loader (ou pelo chat), a barra superior
    de versões (v1 .. vn) reflete exclusivamente as versões deste arquivo.
    """
    __tablename__ = "project_files"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(120), nullable=False, index=True, default="default_user")
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)

    filename = Column(String(255), nullable=False)
    file_format = Column(String(50), nullable=False, default="dxf")
    # Ex: "dxf" (AutoCAD), "blend" (Blender), "ifc" (BIM), "obj", "stl", "png", "jpg"

    active_version_number = Column(Integer, nullable=False, default=1)
    is_selected = Column(Boolean, nullable=False, default=True, index=True)

    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    versions = relationship(
        "FileVersion",
        back_populates="project_file",
        cascade="all, delete-orphan",
        order_by="FileVersion.version_number",
    )


class FileVersion(Base):
    """
    Representa uma versão imutável (v1, v2, ..., vn) de um ProjectFile específico.
    Guarda a imagem/render atual, o estilo (AutoCAD, Blender, Paisagem), os cálculos
    validados pelo Agente Validador e o código gerado pela Tool de Código.
    """
    __tablename__ = "file_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    file_id = Column(String(36), ForeignKey("project_files.id"), nullable=False, index=True)

    version_number = Column(Integer, nullable=False, default=1)
    version_label = Column(String(30), nullable=False, default="v1")  # "v1", "v2", ..., "vn"

    render_style = Column(String(60), nullable=False, default="autocad")
    # Estilos do Excalidraw: "autocad", "blender", "wireframe", "landscape_insight"

    landscape_context = Column(String(120), nullable=True)
    # Ex: "urbano_denso", "encosta_montanhosa", "litoral_maresia", "planalto_continental"

    file_path = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)  # "Aqui fica a imagem" no viewport central
    generated_code = Column(Text, nullable=True)    # Código gerado pela Tool de Código (DXF/Blender/IFC)
    code_language = Column(String(50), nullable=True)

    structural_parameters = Column(JSON, default=dict)
    validation_report = Column(JSON, default=dict)
    change_summary = Column(Text, nullable=True)
    created_by = Column(String(50), nullable=False, default="user_upload")

    created_at = Column(DateTime, default=get_utc_now)

    project_file = relationship("ProjectFile", back_populates="versions")


# ============================================================================
# Entidades de Projeto / Análise Físico-Estrutural (Compatibilidade com Motor DSM/CAD)
# ============================================================================
class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(200), nullable=False)
    author_architect = Column(String(120), default="Arquiteto Autor")
    category = Column(String(50), default="Residencial")
    description = Column(Text, nullable=True)

    image_filename = Column(String(255), nullable=True)
    image_path = Column(String(500), nullable=True)
    blueprint_svg = Column(Text, nullable=True)
    parameters = Column(JSON, default=dict)

    status = Column(String(30), default="pending")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    analyses = relationship(
        "AnalysisResult",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="AnalysisResult.created_at",
    )


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)

    is_physically_viable = Column(Boolean, default=False)
    structural_score = Column(Float, default=0.0)
    compliance_level = Column(String(50), default="Crítico")

    max_deflection_mm = Column(Float, default=0.0)
    allowable_deflection_mm = Column(Float, default=0.0)
    deflection_ratio = Column(Float, default=0.0)

    max_bending_moment_knm = Column(Float, default=0.0)
    shear_utilization_ratio = Column(Float, default=0.0)
    critical_column_buckling_ratio = Column(Float, default=0.0)
    cantilever_stability_factor = Column(Float, default=1.0)

    failure_reasons = Column(JSON, default=list)
    compliance_checklist = Column(JSON, default=dict)
    structural_diagnosis_text = Column(Text, nullable=True)

    ai_gemini_review = Column(Text, nullable=True)
    ai_model_used = Column(String(100), default="gemini-2.5-flash")

    created_at = Column(DateTime, default=get_utc_now)

    project = relationship("Project", back_populates="analyses")


# ============================================================================
# ARQUITETURA EVERMEMOS (Padrão Lembry.Chatbot):
# EpisodeBuffer -> MemCell -> MemScene -> UserProfile
# ============================================================================
class MemoryBufferRow(Base):
    """Fila de mensagens brutas não consumidas (EpisodeBufferStore)."""
    __tablename__ = "memory_buffers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(120), nullable=False, index=True)
    session_id = Column(String(120), nullable=False, index=True, default="default_session")
    role = Column(String(30), nullable=False)
    content = Column(Text, nullable=False)
    message_timestamp = Column(DateTime, default=get_utc_now)
    processed = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, default=get_utc_now)


class MemoryCellRow(Base):
    """Unidade atômica de memória episódica consolidada (MemCell)."""
    __tablename__ = "memory_cells"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(120), nullable=False, index=True)
    session_id = Column(String(120), nullable=False, index=True, default="default_session")
    episode = Column(Text, nullable=False)
    searchable_text = Column(Text, nullable=False)
    facts = Column(JSON, default=list)        # list[{category, fact}]
    foresights = Column(JSON, default=list)   # list[{text, valid_from, valid_until}]
    embedding = Column(JSON, default=list)    # Vetor 1536d normalizado
    message_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=get_utc_now)


class MemorySceneRow(Base):
    """Agrupamento temático de MemCells por centroide semântico (MemScene)."""
    __tablename__ = "memory_scenes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(120), nullable=False, index=True)
    topic = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    centroid_embedding = Column(JSON, default=list)
    cell_count = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)


class MemorySceneCellRow(Base):
    """Associação N:N entre MemScene e MemCell."""
    __tablename__ = "memory_scene_cells"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scene_id = Column(String(36), ForeignKey("memory_scenes.id", ondelete="CASCADE"), nullable=False, index=True)
    cell_id = Column(String(36), ForeignKey("memory_cells.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=get_utc_now)


class MemorySceneVersionRow(Base):
    """Histórico imutável de evolução de cada MemScene."""
    __tablename__ = "memory_scene_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scene_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(120), nullable=False, index=True)
    topic = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    trigger_cell_id = Column(String(36), nullable=True)
    cell_count_at_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=get_utc_now)


class UserProfileRow(Base):
    """Perfil consolidado do Arquiteto/Engenheiro (UserProfile)."""
    __tablename__ = "user_profiles"

    user_id = Column(String(120), primary_key=True)
    explicit_facts = Column(JSON, default=list)  # list[{category, value}]
    patterns = Column(JSON, default=list)        # list[{category, observation}]
    summary = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)


class UserProfileVersionRow(Base):
    """Histórico auditável de evolução do UserProfile."""
    __tablename__ = "user_profile_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(120), nullable=False, index=True)
    explicit_facts = Column(JSON, default=list)
    patterns = Column(JSON, default=list)
    summary = Column(Text, nullable=False, default="")
    trigger_scene_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

