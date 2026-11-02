"""
Scope Guard & Pre-Flight Architectural Boundary Engine.
Validador determinístico de escopo que audita se o modelo arquitetônico submetido
está dentro do envelope de pré-dimensionamento gravitacional preliminar
(residências e edificações de até 4 pavimentos / 12 metros de altura)
ou se exige bloqueio por estabilidade global de 2ª ordem, vento dinâmico ou protensão.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ScopeAuditResult:
    is_within_scope: bool
    scope_category: str  # "STANDARD_LOW_RISE", "POST_TENSIONING_ZONE", "OUT_OF_SCOPE_TALL_BUILDING", "TORSION_RISK"
    severity: str  # "INFO", "WARNING", "HARD_BLOCK"
    title: str
    description: str
    required_engineer_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_within_scope": self.is_within_scope,
            "scope_category": self.scope_category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "required_engineer_actions": self.required_engineer_actions,
        }


class ScopeGuard:
    """
    Auditor determinístico de contorno de escopo para concepção de estruturas.
    """

    MAX_SAFE_SPAN_CONCRETE_RC_M = 12.0
    MAX_SAFE_CANTILEVER_RC_M = 4.5
    MAX_SAFE_BUILDING_HEIGHT_M = 12.0
    MAX_SAFE_STOREYS = 4

    @classmethod
    def audit_project_scope(
        cls,
        max_span_m: float = 6.0,
        max_cantilever_m: float = 0.0,
        total_height_m: float = 3.0,
        num_storeys: int = 1,
        is_indirect_support: bool = False,
        beam_height_cm: Optional[float] = None,
        cantilever_height_cm: Optional[float] = None,
    ) -> ScopeAuditResult:
        span = float(max_span_m or 0.0)
        cant = float(max_cantilever_m or 0.0)
        h_tot = float(total_height_m or 3.0)
        storeys = int(num_storeys or 1)

        # 1. Trava de Edificação Alta (Vento Dinâmico NBR 6123 & Gama-Z)
        if storeys > cls.MAX_SAFE_STOREYS or h_tot > cls.MAX_SAFE_BUILDING_HEIGHT_M:
            return ScopeAuditResult(
                is_within_scope=False,
                scope_category="OUT_OF_SCOPE_TALL_BUILDING",
                severity="HARD_BLOCK",
                title="Edificação Fora do Envelope de Pré-Dimensionamento Gravitacional",
                description=(
                    f"A edificação informada ({storeys} pavimentos / {h_tot:.1f}m de altura) ultrapassa o limite seguro "
                    f"de pré-dimensionamento preliminar 2D (máx {cls.MAX_SAFE_STOREYS} pavimentos / {cls.MAX_SAFE_BUILDING_HEIGHT_M:.0f}m). "
                    f"Edifícios desse porte são governados por efeitos dinâmicos de vento (ABNT NBR 6123:2023) "
                    f"e não-linearidade geométrica global de 2ª ordem (parâmetro γz / α da NBR 6118), exigindo "
                    f"obrigatoriamente modelagem espacial tridimensional completa pelo Engenheiro Calculista."
                ),
                required_engineer_actions=[
                    "Contratação mandatória de Engenheiro Calculista com ART (Lei 5.194/66).",
                    "Análise espacial tridimensional em software estrutural dedicado (TQS, Eberick, SAP2000).",
                    "Verificação de deslocamentos horizontais de topo e conforto humano per NBR 6123.",
                ],
            )

        # 2. Trava de Grandes Vãos / Protensão Recomendada
        if span > cls.MAX_SAFE_SPAN_CONCRETE_RC_M or cant > cls.MAX_SAFE_CANTILEVER_RC_M:
            excesso = "vão livre" if span > cls.MAX_SAFE_SPAN_CONCRETE_RC_M else "balanço"
            val = span if span > cls.MAX_SAFE_SPAN_CONCRETE_RC_M else cant
            return ScopeAuditResult(
                is_within_scope=True,
                scope_category="POST_TENSIONING_ZONE",
                severity="WARNING",
                title=f"Zona de Transição Especial / Protensão Sugerida ({excesso.capitalize()} de {val:.1f}m)",
                description=(
                    f"O projeto apresenta {excesso} arrojado de {val:.1f}m. Em concreto armado convencional moldado in-loco, "
                    f"este elemento exigiria alturas excessivas de viga (comprometendo o pé-direito e o forro de gesso). "
                    f"Recomenda-se prever solução em Concreto Protendido (cordoalhas engraxadas não-aderentes), "
                    f"vigas metálicas em perfil W ou lajes nervuradas protendidas."
                ),
                required_engineer_actions=[
                    "Alinhar com o calculista a viabilidade de concreto protendido com ancoragens ativas.",
                    "Prever faixa de reserva de altura para vigas de transição.",
                    "Verificar contra-flecha de execução na desforma.",
                ],
            )

        # 3. Trava de Apoio Indireto (Torção de Equilíbrio)
        if is_indirect_support:
            return ScopeAuditResult(
                is_within_scope=True,
                scope_category="TORSION_RISK",
                severity="WARNING",
                title="Apoio Indireto Detectado (Viga Apoiada em Viga)",
                description=(
                    "Foi detectada uma viga que se apoia no meio de outra viga sem pilar no nó de encontro. "
                    "Essa geometria induz esforço de torção de equilíbrio na viga de suporte, exigindo "
                    "estribos fechados duplos e armadura longitudinal de costura per NBR 6118."
                ),
                required_engineer_actions=[
                    "Verificar torção de equilíbrio (TRd2 e TRd3) na viga principal.",
                    "Prever armadura de suspensão na interseção das vigas.",
                ],
            )

        # 4. Trava de Flexibilidade Geométrica Excessiva (NBR 6118:2023 item 15.6)
        if beam_height_cm is not None and beam_height_cm > 0:
            h_m = float(beam_height_cm) / 100.0
            slenderness_span = span / h_m if h_m > 0 else 0
            if slenderness_span > 20.0:
                return ScopeAuditResult(
                    is_within_scope=True,
                    scope_category="EXCESSIVE_BEAM_FLEXIBILITY",
                    severity="WARNING",
                    title=f"Flexibilidade Geométrica Excessiva de Viga (L/h = {slenderness_span:.1f} > 20)",
                    description=(
                        f"A relação vão/altura da viga (L/h = {slenderness_span:.1f}) excede o limite prático de rigidez "
                        f"da NBR 6118:2023 item 15.6 (máx L/h = 20 para vigas biapoiadas). Elementos muito esbeltos estão "
                        f"sujeitos a deformações excessivas diferidas no tempo, vibrações induzidas por passos e trincas."
                    ),
                    required_engineer_actions=[
                        "Aumentar a altura útil da viga para manter L/h <= 15 a 20.",
                        "Verificar estados limites de vibração e deformação em serviço (ELS).",
                    ],
                )

        if cantilever_height_cm is not None and cantilever_height_cm > 0 and cant > 0:
            hc_m = float(cantilever_height_cm) / 100.0
            slenderness_cant = cant / hc_m if hc_m > 0 else 0
            if slenderness_cant > 7.0:
                return ScopeAuditResult(
                    is_within_scope=True,
                    scope_category="EXCESSIVE_CANTILEVER_FLEXIBILITY",
                    severity="WARNING",
                    title=f"Flexibilidade Excessiva em Balanço (Lc/h = {slenderness_cant:.1f} > 7)",
                    description=(
                        f"A relação balanço/altura (Lc/h = {slenderness_cant:.1f}) excede a recomendação prática "
                        f"da NBR 6118 (máx Lc/h = 7). Balanços esbeltos são altamente suscetíveis a flechas diferidas "
                        f"por fluência e amplificação dinâmica."
                    ),
                    required_engineer_actions=[
                        "Aumentar a altura da viga no engaste do balanço para manter Lc/h <= 7.",
                    ],
                )

        # 5. Enquadramento Padrão Seguro
        return ScopeAuditResult(
            is_within_scope=True,
            scope_category="STANDARD_LOW_RISE",
            severity="INFO",
            title="Concepção Dentro do Envelope Padrão de Pré-Dimensionamento",
            description=(
                f"O projeto ({span:.1f}m de vão livre, {cant:.1f}m de balanço, {storeys} pavimentos) enquadra-se "
                f"perfeitamente no regime de flexão e serviço de edificações residenciais e comerciais baixas."
            ),
            required_engineer_actions=[
                "Encaminhar anteprojeto para detalhamento executivo e emissão de ART pelo calculista.",
            ],
        )
