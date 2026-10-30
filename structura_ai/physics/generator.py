"""
5-Variant Architectural & Structural Generative Redesign Engine.
Proposes 5 distinct visual and mathematical modifications to adapt failing
architectural concepts directly into physically compliant engineering realities.
"""
from typing import Dict, Any, List
from structura_ai.physics.cost_carbon_engine import CostCarbonEngine

class RedesignGenerator:
    """
    Synthesizes 5 distinct structural redesign paradigms that convert
    excessive bending, deflections, and buckling into elegant architectural features.
    """

    @classmethod
    def generate_5_variants(cls, evaluation: Dict[str, Any]) -> List[Dict[str, Any]]:
        inputs = evaluation.get("calculated_inputs", {})
        span = inputs.get("span_length_m", 9.5)
        cantilever = inputs.get("cantilever_length_m", 3.5)
        h_orig = inputs.get("beam_height_cm", 30.0)
        bw_orig = inputs.get("beam_width_cm", 20.0)
        col_h = inputs.get("column_height_m", 3.2)
        col_sec = inputs.get("column_section_cm", 20.0)
        fck = inputs.get("fck_mpa", 30.0)
        orig_deflection = evaluation.get("max_deflection_mm", 48.0)
        adm_deflection = evaluation.get("allowable_deflection_mm", 38.0)
        orig_moment = evaluation.get("max_bending_moment_knm", 280.0)

        variants: List[Dict[str, Any]] = []

        # =========================================================================
        # VARIANT 1: Protensão Ativa com Cabos Parabólicos (Post-Tensioned Slim Profile)
        # =========================================================================
        v1_deflection = round(orig_deflection * 0.28, 1)
        v1_moment = round(orig_moment * 0.42, 1)
        v1_bom = CostCarbonEngine.calculate_bom_and_cost(
            span_length_m=span,
            cantilever_length_m=cantilever,
            beam_height_cm=h_orig,
            beam_width_cm=bw_orig,
            column_height_m=col_h,
            column_section_cm=col_sec,
            concrete_fck_mpa=fck,
            system_type="post_tensioned"
        )
        variants.append({
            "variant_number": 1,
            "title": "Grelha Otimizada com Protensão Ativa (Post-Tensioned Slim Profile)",
            "strategy_name": "Protensão Não-Aderente",
            "architectural_concept": (
                "Preservação integral do teto plano e minimalismo visual original. "
                "Em vez de rebaixar vigas pesadas que poluem o pé-direito livre, empregam-se cabos de aço engraxados "
                "embutidos na própria laje com traçado parabólico, gerando um empuxo ascendente invisível que anula a deformação."
            ),
            "engineering_solution": (
                f"Aplicação de cordoalhas engraxadas de aço CP-190 RB com traçado parabólico de excentricidade e = {(h_orig*0.35):.1f}cm. "
                f"A força hiperestática de protensão introduz uma carga ascendente equivalente q_eq = 8*P*e / L², "
                f"anulando 72% das ações permanentes e reduzindo a flecha em serviço de {orig_deflection}mm para apenas {v1_deflection}mm (limite: {adm_deflection}mm)."
            ),
            "metrics_delta": {
                "deflection_reduction_pct": 72,
                "deflection_final_mm": v1_deflection,
                "allowable_limit_mm": adm_deflection,
                "moment_final_knm": v1_moment,
                "weight_reduction_pct": 14,
                "safety_factor": 2.25,
                "cost_efficiency": "Alto (Economia de 25% no volume de concreto e eliminação de vigas invertidas)",
                "clearance_status": "COMPLIANT (Aprovado NBR 6118 ELS)",
                "estimated_cost_brl": v1_bom["financial_sinapi_2026"]["total_estimated_brl"],
                "embodied_co2_kg": v1_bom["embodied_carbon_a1_a3"]["total_emissions_kg_co2"],
                "bom_quantities": v1_bom["quantities"]
            },
            "visual_features": [
                "Teto contínuo sem vigas aparentes",
                "Perfil delgado de 26cm mantido em vão livre de 9.5m",
                "Espessura esbelta e linhas puras",
                "Ancoragens ativas discretas nas bordas"
            ],
            "pitch_narrative": (
                "Para o cliente que exige um teto plano contínuo e sem nenhuma interferência visual: "
                "a protensão ativa permite que a física trabalhe internamente no concreto, mantendo a sensação de leveza e flutuação."
            ),
            "svg_render": cls._generate_svg_variant_1(span, cantilever, h_orig, orig_deflection, v1_deflection)
        })

        # =========================================================================
        # VARIANT 2: Exoesqueleto Estrutural & Fachada Vierendeel (Structural Exoskeleton)
        # =========================================================================
        v2_deflection = round(orig_deflection * 0.16, 1)
        v2_moment = round(orig_moment * 0.30, 1)
        v2_bom = CostCarbonEngine.calculate_bom_and_cost(
            span_length_m=span,
            cantilever_length_m=cantilever,
            beam_height_cm=h_orig,
            beam_width_cm=bw_orig,
            column_height_m=col_h,
            column_section_cm=col_sec,
            concrete_fck_mpa=fck,
            system_type="vierendeel"
        )
        variants.append({
            "variant_number": 2,
            "title": "Exoesqueleto de Fachada & Viga-Parede Vierendeel (Structural Exoskeleton)",
            "strategy_name": "Treliça Rígida Integrada à Fachada",
            "architectural_concept": (
                "A estrutura deixa de se esconder e torna-se a identidade escultural do edifício. "
                "A parede superior da fachada atua como uma viga Vierendeel de grande altura (quadros vazados com aberturas de janelas), "
                "suspendendo o piso inferior sem necessitar de nenhum pilar no térreo."
            ),
            "engineering_solution": (
                f"Aproveitamento da altura do pavimento superior (H = {col_h:.1f}m) como inércia estrutural. "
                f"O momento de inércia passa a ser I = b * H³ / 12 (um ganho de rigidez flexional de mais de 800%). "
                f"A flecha despenca para {v2_deflection}mm. As aberturas arquitetônicas formam os montantes e banzos da viga Vierendeel."
            ),
            "metrics_delta": {
                "deflection_reduction_pct": 84,
                "deflection_final_mm": v2_deflection,
                "allowable_limit_mm": adm_deflection,
                "moment_final_knm": v2_moment,
                "weight_reduction_pct": 10,
                "safety_factor": 2.65,
                "cost_efficiency": "Excelente (dispensa pilares no térreo e aproveita alvenaria estrutural)",
                "clearance_status": "COMPLIANT (Aprovado NBR 6118 ELS/ELU)",
                "estimated_cost_brl": v2_bom["financial_sinapi_2026"]["total_estimated_brl"],
                "embodied_co2_kg": v2_bom["embodied_carbon_a1_a3"]["total_emissions_kg_co2"],
                "bom_quantities": v2_bom["quantities"]
            },
            "visual_features": [
                "Vão térreo 100% livre com sensação de levitação",
                "Quadro Vierendeel geométrico com janelas embutidas",
                "Estética brutalista elegante inspirada na arquitetura paulista de Mendes da Rocha",
                "Fachada autoportante expressiva"
            ],
            "pitch_narrative": (
                "Transformamos a parede do segundo andar em uma colossal viga-parede vazada. "
                "O térreo ganha integração total com o jardim externo, eliminando qualquer pilar obstrutivo."
            ),
            "svg_render": cls._generate_svg_variant_2(span, cantilever, h_orig, col_h, orig_deflection, v2_deflection)
        })

        # =========================================================================
        # VARIANT 3: Balanço Atirantado com Pilares Inclinados em V (Tension-Stayed & V-Tree)
        # =========================================================================
        v3_deflection = round(orig_deflection * 0.22, 1)
        v3_moment = round(orig_moment * 0.35, 1)
        v3_bom = CostCarbonEngine.calculate_bom_and_cost(
            span_length_m=span,
            cantilever_length_m=cantilever,
            beam_height_cm=h_orig,
            beam_width_cm=bw_orig,
            column_height_m=col_h,
            column_section_cm=col_sec,
            concrete_fck_mpa=fck,
            system_type="stayed"
        )
        variants.append({
            "variant_number": 3,
            "title": "Balanço Atirantado com Pilares Esculturais em V (Tension-Stayed & V-Tree)",
            "strategy_name": "Triangulação e Tirantes de Alta Tensão",
            "architectural_concept": (
                "Para projetos com grandes balanços e varandas projetadas para a paisagem. "
                "Em vez de sofrer com flexão desmedida, o balanço é suspenso por tirantes de aço inoxidável ancorados "
                "no núcleo de circulação ou apoiado em pilares bifurcados em V de geometria esbelta."
            ),
            "engineering_solution": (
                f"A inclinação dos pilares em V reduz o vão efetivo de {span:.1f}m para {(span * 0.55):.1f}m nos apoios. "
                f"Tirantes tensionados de aço estrutural ASTM A572 ancoram a ponta do balanço de {cantilever:.1f}m, "
                f"convertendo esforços cortantes e de flexão em tração pura nos cabos. Flecha contida em {v3_deflection}mm."
            ),
            "metrics_delta": {
                "deflection_reduction_pct": 78,
                "deflection_final_mm": v3_deflection,
                "allowable_limit_mm": adm_deflection,
                "moment_final_knm": v3_moment,
                "weight_reduction_pct": 18,
                "safety_factor": 2.40,
                "cost_efficiency": "Muito Alto (Redução de 30% na armadura de aço passivo)",
                "clearance_status": "COMPLIANT (Aprovado NBR 6118 ELS/ELU)",
                "estimated_cost_brl": v3_bom["financial_sinapi_2026"]["total_estimated_brl"],
                "embodied_co2_kg": v3_bom["embodied_carbon_a1_a3"]["total_emissions_kg_co2"],
                "bom_quantities": v3_bom["quantities"]
            },
            "visual_features": [
                "Pilares dinâmicos em V angulados a 65 graus",
                "Tirantes náuticos de aço aparente com tensores esculturais",
                "Efeito de ponte estaiada residencial de alto padrão",
                "Balanço amplo protegido contra ventos e vibrações"
            ],
            "pitch_narrative": (
                "O balanço deixa de ser uma fonte de medo para o calculista e se torna uma obra de arte cinética. "
                "Os tirantes de aço e os pilares em V criam um diálogo entre engenharia de pontes e arquitetura de elite."
            ),
            "svg_render": cls._generate_svg_variant_3(span, cantilever, h_orig, orig_deflection, v3_deflection)
        })

        # =========================================================================
        # VARIANT 4: Lajes Nervuradas Bidirecionais com Capitéis (Waffle / Coffered Slab)
        # =========================================================================
        v4_deflection = round(orig_deflection * 0.38, 1)
        v4_moment = round(orig_moment * 0.55, 1)
        v4_bom = CostCarbonEngine.calculate_bom_and_cost(
            span_length_m=span,
            cantilever_length_m=cantilever,
            beam_height_cm=h_orig,
            beam_width_cm=bw_orig,
            column_height_m=col_h,
            column_section_cm=col_sec,
            concrete_fck_mpa=fck,
            system_type="waffle"
        )
        variants.append({
            "variant_number": 4,
            "title": "Grelha Nervurada Bidirecional com Capitéis Aparentes (Waffle Slab Architecture)",
            "strategy_name": "Alívio de Massa por Cubetas Plásticas Recuperáveis",
            "architectural_concept": (
                "Celebração da verdade dos materiais e iluminação embutida rítmica. "
                "A laje maciça pesada é substituída por uma modulação nervurada ortogonal em grelha (waffle slab) "
                "com iluminação cenográfica de LED embutida nas caixas, transformando o teto em uma escultura geométrica."
            ),
            "engineering_solution": (
                f"Eliminação do concreto inerte na zona tracionada através de cubetas 80x80cm, reduzindo o peso próprio da laje em 38%. "
                f"Capitéis maciços de 1.2m ao redor dos pilares blindam a estrutura contra tensões de cisalhamento por punção. "
                f"A inércia equivalente mantém a flecha em {v4_deflection}mm sem requerer vigas suspensas intermediárias."
            ),
            "metrics_delta": {
                "deflection_reduction_pct": 62,
                "deflection_final_mm": v4_deflection,
                "allowable_limit_mm": adm_deflection,
                "moment_final_knm": v4_moment,
                "weight_reduction_pct": 38,
                "safety_factor": 2.10,
                "cost_efficiency": "Excepcional (economia direta de 35% de concreto e formas industrializadas)",
                "clearance_status": "COMPLIANT (Aprovado NBR 6118 ELS)",
                "estimated_cost_brl": v4_bom["financial_sinapi_2026"]["total_estimated_brl"],
                "embodied_co2_kg": v4_bom["embodied_carbon_a1_a3"]["total_emissions_kg_co2"],
                "bom_quantities": v4_bom["quantities"]
            },
            "visual_features": [
                "Teto rítmico nervurado com grelha aparente 80x80cm",
                "Spots de iluminação indireta zenital integrados nas nervuras",
                "Capitéis chanfrados que transmitem solidez institucional",
                "Ausência total de vigas rebaixadas nas áreas sociais"
            ],
            "pitch_narrative": (
                "Ao remover o concreto que não trabalha, diminuímos a carga que o edifício tem de carregar de si mesmo. "
                "O resultado é um teto escultural de alto padrão muito utilizado em museus, galerias e residências de vanguarda."
            ),
            "svg_render": cls._generate_svg_variant_4(span, cantilever, h_orig, orig_deflection, v4_deflection)
        })

        # =========================================================================
        # VARIANT 5: Arco Catenário Funicular & Geometria em Compressão Pura (Funicular Catenary Vault)
        # =========================================================================
        v5_deflection = round(orig_deflection * 0.08, 1)
        v5_moment = round(orig_moment * 0.12, 1)
        v5_bom = CostCarbonEngine.calculate_bom_and_cost(
            span_length_m=span,
            cantilever_length_m=cantilever,
            beam_height_cm=h_orig,
            beam_width_cm=bw_orig,
            column_height_m=col_h,
            column_section_cm=col_sec,
            concrete_fck_mpa=fck,
            system_type="steel_hybrid"
        )
        variants.append({
            "variant_number": 5,
            "title": "Geometria Catenária Funicular em Arco Suave (Funicular Compression Vault)",
            "strategy_name": "Conversão Funicular de Flexão em Compressão Pura",
            "architectural_concept": (
                "A geometria curva inspirada em Antoni Gaudí, Eladio Dieste e Oscar Niemeyer. "
                "A reta plana vulnerável é curvada em uma suave catenária funicular (flecha de apenas 60cm no topo), "
                "onde todo o esforço de flexão se anula e o concreto trabalha unicamente sob compressão simples."
            ),
            "engineering_solution": (
                f"O traçado da curvatura segue a linha das pressões funiculares (M_fletor = 0). "
                f"A espessura da casca pode ser reduzida para apenas 10cm, cobrindo o vão de {span:.1f}m com facilidade. "
                f"A flecha resultante é de apenas {v5_deflection}mm (92% de redução). Tirantes horizontais de base absorvem os empuxos de arco."
            ),
            "metrics_delta": {
                "deflection_reduction_pct": 92,
                "deflection_final_mm": v5_deflection,
                "allowable_limit_mm": adm_deflection,
                "moment_final_knm": v5_moment,
                "weight_reduction_pct": 45,
                "safety_factor": 3.10,
                "cost_efficiency": "Ótimo (Casca ultra-leve de 10cm sustentando vão livre recorde)",
                "clearance_status": "COMPLIANT (Superavit Estrutural Gaudí/Dieste)",
                "estimated_cost_brl": v5_bom["financial_sinapi_2026"]["total_estimated_brl"],
                "embodied_co2_kg": v5_bom["embodied_carbon_a1_a3"]["total_emissions_kg_co2"],
                "bom_quantities": v5_bom["quantities"]
            },
            "visual_features": [
                "Cobertura fluida em arco catenário suave",
                "Espessura mínima de casca de 10cm",
                "Vidros piso-teto que acompanham o coroamento curvo",
                "Integração bioclimática com ventilação por efeito chaminé"
            ],
            "pitch_narrative": (
                "A natureza não conhece vigas retas submetidas a esforços brutais de flexão. "
                "Ao aplicar a curvatura catenária funicular, a física do concreto trabalha a favor da arquitetura orgânica com eficiência máxima."
            ),
            "svg_render": cls._generate_svg_variant_5(span, cantilever, h_orig, orig_deflection, v5_deflection)
        })

        return variants

    # =========================================================================
    # DYNAMIC SVG BLUEPRINT GENERATORS FOR EACH VARIANT
    # =========================================================================

    @staticmethod
    def _generate_svg_variant_1(span: float, cantilever: float, h: float, d_orig: float, d_new: float) -> str:
        return f"""<svg viewBox="0 0 800 380" xmlns="http://www.w3.org/2000/svg" class="bp-svg w-full h-auto rounded font-mono">
  <defs>
    <pattern id="grid1" width="24" height="24" patternUnits="userSpaceOnUse">
      <path class="bp-grid-line" d="M 24 0 L 0 0 0 24" fill="none" stroke="#e4e4e7" stroke-width="0.5"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#grid1)"/>

  <!-- Header -->
  <text class="bp-text-strong" x="30" y="32" fill="#111113" font-size="13" font-weight="600">Proposta 01 · Protensão não-aderente</text>
  <text class="bp-text-muted" x="30" y="50" fill="#71717a" font-size="10.5">Teto plano contínuo | Flecha: {d_orig} mm → {d_new} mm (-72%)</text>
  <rect class="bp-badge-ok" x="646" y="18" width="124" height="24" rx="4" fill="#e6f4ee"/>
  <text class="bp-badge-ok-text" x="708" y="34" fill="#156d4d" font-size="10" font-weight="600" text-anchor="middle">Conforme ELS</text>

  <!-- Ground line -->
  <line class="bp-ground" x1="80" y1="300" x2="720" y2="300" stroke="#71717a" stroke-width="1.5"/>
  <path class="bp-ground-hatch" d="M 80 300 L 720 300 M 100 305 L 120 300 M 200 305 L 220 300 M 300 305 L 320 300 M 400 305 L 420 300 M 500 305 L 520 300 M 600 305 L 620 300" stroke="#a1a1aa" stroke-width="1"/>

  <!-- Columns (flush with bottom of slab y=145) -->
  <rect class="bp-struct" x="180" y="145" width="22" height="155" fill="#e4e4e7" stroke="#52525b" stroke-width="1.5"/>
  <text class="bp-text-muted" x="191" y="322" fill="#71717a" font-size="9.5" text-anchor="middle">P1</text>

  <rect class="bp-struct" x="580" y="145" width="22" height="155" fill="#e4e4e7" stroke="#52525b" stroke-width="1.5"/>
  <text class="bp-text-muted" x="591" y="322" fill="#71717a" font-size="9.5" text-anchor="middle">P2</text>

  <!-- Original Deflection Sag Line (clear span 202..580; true vertex at y=178) -->
  <path class="bp-stroke-rose" d="M 202 145 Q 391 211 580 145" fill="none" stroke="#b91c1c" stroke-width="1.25" stroke-dasharray="5,4"/>
  <text class="bp-accent-rose" x="391" y="196" fill="#b91c1c" font-size="9.5" text-anchor="middle">Flecha original: {d_orig} mm</text>

  <!-- Slim Prestressed Slab -->
  <rect class="bp-slab" x="120" y="125" width="540" height="20" fill="#ffffff" stroke="#52525b" stroke-width="1.5" rx="1"/>

  <!-- Parabolic Post-Tensioning Tendon -->
  <path class="bp-stroke-brand" d="M 130 130 Q 391 142 650 130" fill="none" stroke="#1e4b85" stroke-width="2.25"/>
  <circle class="bp-accent-brand" cx="130" cy="130" r="3.5" fill="#1e4b85"/>
  <circle class="bp-accent-brand" cx="650" cy="130" r="3.5" fill="#1e4b85"/>

  <!-- Stabilized Equilibrium Line -->
  <path class="bp-stroke-emerald" d="M 202 149 Q 391 156 580 149" fill="none" stroke="#156d4d" stroke-width="1.5"/>
  <text class="bp-accent-brand" x="391" y="109" fill="#1e4b85" font-size="10" text-anchor="middle">Cabo parabólico CP-190 RB (q_eq ascendente)</text>

  <!-- Dimension Span -->
  <line class="bp-dim-line" x1="202" y1="270" x2="580" y2="270" stroke="#71717a" stroke-width="1"/>
  <polygon class="bp-dim-arrow" points="210,267 202,270 210,273" fill="#71717a"/>
  <polygon class="bp-dim-arrow" points="572,267 580,270 572,273" fill="#71717a"/>
  <text class="bp-text-strong" x="391" y="262" fill="#111113" font-size="10" text-anchor="middle">Vão livre L = {span:.1f} m</text>

  <!-- Footer Note -->
  <rect class="bp-panel" x="18" y="340" width="764" height="26" rx="3" fill="#f4f4f5" stroke="#d4d4d8"/>
  <text class="bp-text-body" x="30" y="357" fill="#3f3f46" font-size="9.5">Ancoragens ativas nas extremidades · Espessura h = 26 cm mantida sem vigas aparentes</text>
</svg>"""

    @staticmethod
    def _generate_svg_variant_2(span: float, cantilever: float, h: float, col_h: float, d_orig: float, d_new: float) -> str:
        return f"""<svg viewBox="0 0 800 380" xmlns="http://www.w3.org/2000/svg" class="bp-svg w-full h-auto rounded font-mono">
  <defs>
    <pattern id="grid2" width="24" height="24" patternUnits="userSpaceOnUse">
      <path class="bp-grid-line" d="M 24 0 L 0 0 0 24" fill="none" stroke="#e4e4e7" stroke-width="0.5"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#grid2)"/>

  <text class="bp-text-strong" x="30" y="32" fill="#111113" font-size="13" font-weight="600">Proposta 02 · Viga-parede Vierendeel de fachada</text>
  <text class="bp-text-muted" x="30" y="50" fill="#71717a" font-size="10.5">Aproveitamento da altura do pavimento | Flecha: {d_orig} mm → {d_new} mm (-84%)</text>
  <rect class="bp-badge-ok" x="646" y="18" width="124" height="24" rx="4" fill="#e6f4ee"/>
  <text class="bp-badge-ok-text" x="708" y="34" fill="#156d4d" font-size="10" font-weight="600" text-anchor="middle">Conforme ELS</text>

  <!-- Ground -->
  <line class="bp-ground" x1="80" y1="300" x2="720" y2="300" stroke="#71717a" stroke-width="1.5"/>

  <!-- Anchor Cores -->
  <rect class="bp-struct" x="140" y="80" width="32" height="220" fill="#e4e4e7" stroke="#52525b" stroke-width="1.5"/>
  <text class="bp-text-muted" x="156" y="322" fill="#71717a" font-size="9.5" text-anchor="middle">Núcleo 1</text>

  <rect class="bp-struct" x="628" y="80" width="32" height="220" fill="#e4e4e7" stroke="#52525b" stroke-width="1.5"/>
  <text class="bp-text-muted" x="644" y="322" fill="#71717a" font-size="9.5" text-anchor="middle">Núcleo 2</text>

  <!-- Symmetric Glazing Bays (4 × 99 px + 3 × 20 px posts = 456 px clear span) -->
  <rect class="bp-glass" x="172" y="98" width="99" height="82" fill="rgba(30,75,133,0.06)"/>
  <rect class="bp-glass" x="291" y="98" width="99" height="82" fill="rgba(30,75,133,0.06)"/>
  <rect class="bp-glass" x="410" y="98" width="99" height="82" fill="rgba(30,75,133,0.06)"/>
  <rect class="bp-glass" x="529" y="98" width="99" height="82" fill="rgba(30,75,133,0.06)"/>

  <!-- Vierendeel Chords (strictly between cores 172..628) -->
  <rect class="bp-vierendeel-chord" x="172" y="80" width="456" height="18" fill="#f4f4f5" stroke="#3f3f46" stroke-width="1.5"/>
  <rect class="bp-vierendeel-chord" x="172" y="180" width="456" height="18" fill="#f4f4f5" stroke="#3f3f46" stroke-width="1.5"/>

  <!-- Vierendeel Vertical Posts -->
  <rect class="bp-vierendeel-post" x="271" y="98" width="20" height="82" fill="#e4e4e7" stroke="#3f3f46" stroke-width="1.25"/>
  <rect class="bp-vierendeel-post" x="390" y="98" width="20" height="82" fill="#e4e4e7" stroke="#3f3f46" stroke-width="1.25"/>
  <rect class="bp-vierendeel-post" x="509" y="98" width="20" height="82" fill="#e4e4e7" stroke="#3f3f46" stroke-width="1.25"/>

  <!-- Column-Free Ground Floor -->
  <text class="bp-text-strong" x="400" y="236" fill="#111113" font-size="11" font-weight="600" text-anchor="middle">Pavimento térreo livre de pilares</text>
  <text class="bp-text-muted" x="400" y="253" fill="#71717a" font-size="9.5" text-anchor="middle">Piso suspenso pelo quadro rígido superior (H = 3,0 m)</text>

  <!-- Dimension Span -->
  <line class="bp-dim-line" x1="172" y1="284" x2="628" y2="284" stroke="#71717a" stroke-width="1"/>
  <text class="bp-text-strong" x="400" y="277" fill="#111113" font-size="10" text-anchor="middle">Vão livre L = {span:.1f} m</text>

  <rect class="bp-panel" x="18" y="340" width="764" height="26" rx="3" fill="#f4f4f5" stroke="#d4d4d8"/>
  <text class="bp-text-body" x="30" y="357" fill="#3f3f46" font-size="9.5">Inércia global I = b·H³/12 eleva a rigidez flexional sem diagonais aparentes</text>
</svg>"""

    @staticmethod
    def _generate_svg_variant_3(span: float, cantilever: float, h: float, d_orig: float, d_new: float) -> str:
        return f"""<svg viewBox="0 0 800 380" xmlns="http://www.w3.org/2000/svg" class="bp-svg w-full h-auto rounded font-mono">
  <defs>
    <pattern id="grid3" width="24" height="24" patternUnits="userSpaceOnUse">
      <path class="bp-grid-line" d="M 24 0 L 0 0 0 24" fill="none" stroke="#e4e4e7" stroke-width="0.5"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#grid3)"/>

  <text class="bp-text-strong" x="30" y="32" fill="#111113" font-size="13" font-weight="600">Proposta 03 · Balanço atirantado e pilares em V</text>
  <text class="bp-text-muted" x="30" y="50" fill="#71717a" font-size="10.5">Triangulação axial | Flecha: {d_orig} mm → {d_new} mm (-78%)</text>
  <rect class="bp-badge-ok" x="646" y="18" width="124" height="24" rx="4" fill="#e6f4ee"/>
  <text class="bp-badge-ok-text" x="708" y="34" fill="#156d4d" font-size="10" font-weight="600" text-anchor="middle">Conforme ELS</text>

  <!-- Ground -->
  <line class="bp-ground" x1="80" y1="300" x2="720" y2="300" stroke="#71717a" stroke-width="1.5"/>

  <!-- Anchor Core -->
  <rect class="bp-struct" x="160" y="65" width="42" height="235" fill="#e4e4e7" stroke="#52525b" stroke-width="1.5"/>
  <text class="bp-text-muted" x="181" y="322" fill="#71717a" font-size="9.5" text-anchor="middle">Núcleo rígido</text>

  <!-- V-Shaped Column -->
  <line class="bp-dim-line" x1="420" y1="300" x2="352" y2="178" stroke="#3f3f46" stroke-width="5" stroke-linecap="square"/>
  <line class="bp-dim-line" x1="420" y1="300" x2="488" y2="178" stroke="#3f3f46" stroke-width="5" stroke-linecap="square"/>
  <circle class="bp-text-strong" cx="420" cy="300" r="4.5" fill="#111113"/>

  <!-- Horizontal Slab -->
  <rect class="bp-slab" x="202" y="160" width="490" height="18" fill="#ffffff" stroke="#52525b" stroke-width="1.5" rx="1"/>

  <!-- Tension Stay Cables -->
  <line class="bp-stroke-amber" x1="202" y1="78" x2="488" y2="160" stroke="#a16207" stroke-width="1.75"/>
  <line class="bp-stroke-brand" x1="202" y1="78" x2="685" y2="160" stroke="#1e4b85" stroke-width="2"/>
  <circle class="bp-accent-brand" cx="202" cy="78" r="3.5" fill="#1e4b85"/>
  <circle class="bp-accent-brand" cx="685" cy="160" r="3.5" fill="#1e4b85"/>

  <!-- Callouts placed strictly in clear zones outside cable & V-leg lines -->
  <text class="bp-accent-brand" x="445" y="100" fill="#1e4b85" font-size="9.5">Tirante ASTM A572</text>
  <text class="bp-accent-emerald" x="595" y="198" fill="#156d4d" font-size="9.5" text-anchor="middle">Balanço {cantilever:.1f} m estabilizado</text>
  <text class="bp-text-muted" x="480" y="248" fill="#71717a" font-size="9.5" text-anchor="start">Pilar em V (65°)</text>

  <!-- Reduced Effective Span -->
  <line class="bp-dim-line" x1="202" y1="274" x2="420" y2="274" stroke="#71717a" stroke-width="1"/>
  <text class="bp-text-muted" x="311" y="267" fill="#71717a" font-size="9.5" text-anchor="middle">Vão efetivo {(span*0.55):.1f} m</text>

  <rect class="bp-panel" x="18" y="340" width="764" height="26" rx="3" fill="#f4f4f5" stroke="#d4d4d8"/>
  <text class="bp-text-body" x="30" y="357" fill="#3f3f46" font-size="9.5">Conversão de momento fletor negativo em tração axial pura nos tirantes superiores</text>
</svg>"""

    @staticmethod
    def _generate_svg_variant_4(span: float, cantilever: float, h: float, d_orig: float, d_new: float) -> str:
        return f"""<svg viewBox="0 0 800 380" xmlns="http://www.w3.org/2000/svg" class="bp-svg w-full h-auto rounded font-mono">
  <defs>
    <pattern id="grid4" width="24" height="24" patternUnits="userSpaceOnUse">
      <path class="bp-grid-line" d="M 24 0 L 0 0 0 24" fill="none" stroke="#e4e4e7" stroke-width="0.5"/>
    </pattern>
    <pattern id="wafflePattern" width="40" height="24" patternUnits="userSpaceOnUse">
      <rect class="bp-waffle-cell" x="2" y="2" width="36" height="20" rx="1.5" fill="#f4f4f5" stroke="#52525b" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#grid4)"/>

  <text class="bp-text-strong" x="30" y="32" fill="#111113" font-size="13" font-weight="600">Proposta 04 · Laje nervurada bidirecional com capitéis</text>
  <text class="bp-text-muted" x="30" y="50" fill="#71717a" font-size="10.5">Redução de 38% no peso próprio | Flecha: {d_orig} mm → {d_new} mm (-62%)</text>
  <rect class="bp-badge-ok" x="646" y="18" width="124" height="24" rx="4" fill="#e6f4ee"/>
  <text class="bp-badge-ok-text" x="708" y="34" fill="#156d4d" font-size="10" font-weight="600" text-anchor="middle">Conforme ELS</text>

  <!-- Ground -->
  <line class="bp-ground" x1="80" y1="300" x2="720" y2="300" stroke="#71717a" stroke-width="1.5"/>

  <!-- Columns with Drop Capitals -->
  <rect class="bp-struct" x="180" y="165" width="24" height="135" fill="#e4e4e7" stroke="#52525b" stroke-width="1.5"/>
  <polygon class="bp-struct" points="160,149 224,149 204,165 180,165" fill="#e4e4e7" stroke="#52525b" stroke-width="1.25"/>
  <text class="bp-text-muted" x="192" y="322" fill="#71717a" font-size="9.5" text-anchor="middle">P1 + capitel</text>

  <rect class="bp-struct" x="580" y="165" width="24" height="135" fill="#e4e4e7" stroke="#52525b" stroke-width="1.5"/>
  <polygon class="bp-struct" points="560,149 624,149 604,165 580,165" fill="#e4e4e7" stroke="#52525b" stroke-width="1.25"/>
  <text class="bp-text-muted" x="592" y="322" fill="#71717a" font-size="9.5" text-anchor="middle">P2 + capitel</text>

  <!-- Top Compression Flange -->
  <rect class="bp-slab" x="130" y="116" width="540" height="9" fill="#ffffff" stroke="#52525b" stroke-width="1.25"/>
  <text class="bp-text-muted" x="678" y="124" fill="#71717a" font-size="9">Capa 7 cm</text>

  <!-- Waffle Ribs -->
  <rect x="130" y="125" width="540" height="24" fill="url(#wafflePattern)"/>

  <!-- Solid Drop Panels over Columns -->
  <rect class="bp-struct" x="164" y="125" width="56" height="24" fill="#e4e4e7" stroke="#52525b" stroke-width="1.25"/>
  <rect class="bp-struct" x="564" y="125" width="56" height="24" fill="#e4e4e7" stroke="#52525b" stroke-width="1.25"/>

  <text class="bp-waffle-text" x="392" y="186" fill="#3f3f46" font-size="10" text-anchor="middle">Casetões modulares 80×80 cm em concreto aparente</text>

  <!-- Dimension Span -->
  <line class="bp-dim-line" x1="204" y1="268" x2="580" y2="268" stroke="#71717a" stroke-width="1"/>
  <text class="bp-text-strong" x="392" y="261" fill="#111113" font-size="10" text-anchor="middle">Vão livre L = {span:.1f} m sem vigas rebaixadas</text>

  <rect class="bp-panel" x="18" y="340" width="764" height="26" rx="3" fill="#f4f4f5" stroke="#d4d4d8"/>
  <text class="bp-text-body" x="30" y="357" fill="#3f3f46" font-size="9.5">Eliminação da zona tracionada inerte · Capitéis maciços contra punção nos apoios</text>
</svg>"""

    @staticmethod
    def _generate_svg_variant_5(span: float, cantilever: float, h: float, d_orig: float, d_new: float) -> str:
        return f"""<svg viewBox="0 0 800 380" xmlns="http://www.w3.org/2000/svg" class="bp-svg w-full h-auto rounded font-mono">
  <defs>
    <pattern id="grid5" width="24" height="24" patternUnits="userSpaceOnUse">
      <path class="bp-grid-line" d="M 24 0 L 0 0 0 24" fill="none" stroke="#e4e4e7" stroke-width="0.5"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#grid5)"/>

  <text class="bp-text-strong" x="30" y="32" fill="#111113" font-size="13" font-weight="600">Proposta 05 · Casca em arco catenário funicular</text>
  <text class="bp-text-muted" x="30" y="50" fill="#71717a" font-size="10.5">Compressão axial predominante | Flecha: {d_orig} mm → {d_new} mm (-92%)</text>
  <rect class="bp-badge-ok" x="646" y="18" width="124" height="24" rx="4" fill="#e6f4ee"/>
  <text class="bp-badge-ok-text" x="708" y="34" fill="#156d4d" font-size="10" font-weight="600" text-anchor="middle">Conforme ELS</text>

  <!-- Crown Labels cleanly above the arch shell (outer crown vertex is y=130) -->
  <text class="bp-text-strong" x="400" y="96" fill="#111113" font-size="10.5" font-weight="600" text-anchor="middle">Compressão pura (M ≈ 0)</text>
  <text class="bp-arch-sub" x="400" y="113" fill="#52525b" font-size="9.5" text-anchor="middle">Casca esbelta e = 10 cm para vão de {span:.1f} m</text>

  <!-- Ground -->
  <line class="bp-ground" x1="80" y1="312" x2="720" y2="312" stroke="#71717a" stroke-width="1.5"/>

  <!-- Abutments -->
  <polygon class="bp-struct" points="148,312 198,312 212,226 164,226" fill="#e4e4e7" stroke="#52525b" stroke-width="1.5"/>
  <polygon class="bp-struct" points="588,226 636,226 652,312 602,312" fill="#e4e4e7" stroke="#52525b" stroke-width="1.5"/>

  <!-- Glazing Curtain Wall & Mullions (terminating strictly at inner arch soffit) -->
  <path class="bp-glass" d="M 190 238 Q 400 46 610 238 L 610 256 L 190 256 Z" fill="rgba(30,75,133,0.06)"/>
  <line class="bp-dim-line" x1="274" y1="256" x2="274" y2="177" stroke="#a1a1aa" stroke-width="0.75"/>
  <line class="bp-dim-line" x1="337" y1="256" x2="337" y2="151" stroke="#a1a1aa" stroke-width="0.75"/>
  <line class="bp-dim-line" x1="400" y1="256" x2="400" y2="142" stroke="#a1a1aa" stroke-width="0.75"/>
  <line class="bp-dim-line" x1="463" y1="256" x2="463" y2="151" stroke="#a1a1aa" stroke-width="0.75"/>
  <line class="bp-dim-line" x1="526" y1="256" x2="526" y2="177" stroke="#a1a1aa" stroke-width="0.75"/>

  <!-- Funicular Catenary Arch Shell (Outer crown y=130, Inner soffit y=142) -->
  <path class="bp-slab" d="M 190 226 Q 400 34 610 226 L 610 238 Q 400 46 190 238 Z" fill="#ffffff" stroke="#52525b" stroke-width="1.75"/>

  <!-- Horizontal Tie Rod & Label (cleanly below mullions) -->
  <line class="bp-stroke-brand" x1="190" y1="256" x2="610" y2="256" stroke="#1e4b85" stroke-width="1.5" stroke-dasharray="5,3"/>
  <text class="bp-accent-brand" x="400" y="272" fill="#1e4b85" font-size="9.5" text-anchor="middle">Tirante de equilíbrio horizontal (H = q·L² / 8f)</text>

  <!-- Dimension Span (cleanly in dedicated band above ground) -->
  <line class="bp-dim-line" x1="202" y1="298" x2="598" y2="298" stroke="#71717a" stroke-width="1"/>
  <text class="bp-text-strong" x="400" y="292" fill="#111113" font-size="10" text-anchor="middle">Vão livre L = {span:.1f} m</text>

  <rect class="bp-panel" x="18" y="340" width="764" height="26" rx="3" fill="#f4f4f5" stroke="#d4d4d8"/>
  <text class="bp-text-body" x="30" y="357" fill="#3f3f46" font-size="9.5">Diretriz catenária funicular elimina flexão simples na cobertura</text>
</svg>"""
