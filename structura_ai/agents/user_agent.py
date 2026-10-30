"""
User Adversarial Agent (Agente User).
Persona: Demanding architect / competitor engineer attempting to reverse-engineer and clone our IP.
Aggressively stress-tests every feature, probes boundary cases, benchmarks scenarios,
and logs critical UX, calculation, and structural complaints.
"""
import time
from typing import Dict, Any, List
from structura_ai.physics.structural_core import StructuralCoreEngine
from structura_ai.physics.generator import RedesignGenerator
from structura_ai.physics.dsm_solver import DSMSolver
from structura_ai.physics.cost_carbon_engine import CostCarbonEngine
from structura_ai.physics.optisection import OptiSectionEngine
from structura_ai.cad.bim_exporter import BimExporter
from structura_ai.services.sample_projects import SAMPLE_PRESETS


class UserAdversarialAgent:
    """
    Simulates an aggressive architect/competitor testing the platform to replicate its IP.
    Logs friction points, boundary failures, and complaints for the Engineer Agent to curate.
    """

    def __init__(self, agent_id: str = "adversarial_architect_007"):
        self.agent_id = agent_id
        self.tested_features: List[str] = []
        self.complaints: List[Dict[str, Any]] = []
        self.benchmark_records: List[Dict[str, Any]] = []
        self.ip_cloning_log: List[Dict[str, Any]] = []

    def run_comprehensive_audit(self) -> Dict[str, Any]:
        """
        Executes end-to-end adversarial testing across all core modules.
        """
        start_time = time.perf_counter()

        # 1. Test Scenario 1 (Overstressed / Requiring Redesign)
        self._test_scenario_1_benchmarks()

        # 2. Test Scenario 2 (100% Compliant Benchmarks)
        self._test_scenario_2_benchmarks()

        # 3. Stress-Test Boundary Edge Cases
        self._test_extreme_boundaries()

        # 4. Probe Direct Stiffness Method (DSM) Matrix Engine
        self._probe_dsm_and_voronoi()

        # 5. Probe BIM Roundtrip Exporters (IFC4 & DXF)
        self._probe_bim_exporters()

        # 6. Audit Financial & Carbon Accuracy
        self._audit_cost_and_carbon()

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "agent_id": self.agent_id,
            "persona": "Adversarial Architect & Competitor IP Cloner",
            "execution_time_ms": elapsed_ms,
            "total_complaints_filed": len(self.complaints),
            "total_benchmarks_evaluated": len(self.benchmark_records),
            "tested_features": self.tested_features,
            "complaints": self.complaints,
            "benchmarks": self.benchmark_records,
            "ip_probe_status": {
                "cloning_feasibility_score": "45% (A física determinística é sólida e o acoplamento DSM-BIM é proprietário)",
                "critical_takeaway": "A velocidade (<50ms) e as 5 variantes automáticas são o maior obstáculo para cópia concorrente."
            }
        }

    def _test_scenario_1_benchmarks(self):
        self.tested_features.append("Scenario 1: Needs Structural Redesign Benchmarks")
        s1_keys = ["residencia_vao_livre_critico", "balanco_corporativo_extremo", "pe_direito_duplo_flambagem"]

        for key in s1_keys:
            preset = SAMPLE_PRESETS.get(key)
            if not preset:
                continue

            eval_res = StructuralCoreEngine.evaluate_structure(
                span_length_m=preset["span_length_m"],
                cantilever_length_m=preset["cantilever_length_m"],
                beam_height_cm=preset["beam_height_cm"],
                beam_width_cm=preset["beam_width_cm"],
                column_height_m=preset["column_height_m"],
                column_section_cm=preset["column_section_cm"],
                dead_load_kpa=preset["dead_load_kpa"],
                live_load_kpa=preset["live_load_kpa"],
                concrete_fck_mpa=preset["concrete_fck_mpa"]
            )

            is_viable = eval_res["is_physically_viable"]
            variants = RedesignGenerator.generate_5_variants(eval_res)

            self.benchmark_records.append({
                "preset_key": key,
                "scenario": 1,
                "title": preset["title"],
                "score": eval_res["structural_score"],
                "is_viable": is_viable,
                "variants_generated": len(variants),
                "verdict": "CORRECT_FAIL" if not is_viable else "UNEXPECTED_PASS"
            })

            # User Complaint: Architect complaining about aggressive rejection
            if not is_viable:
                self.complaints.append({
                    "category": "Architectural Freedom",
                    "severity": "HIGH",
                    "target_feature": f"Scenario 1 ({key})",
                    "complaint": (
                        f"O sistema reprovou meu projeto '{preset['title']}' com score {eval_res['structural_score']}! "
                        f"Como arquiteto, acho a flecha calculada ({eval_res['max_deflection_mm']}mm) conservadora demais. "
                        f"O cliente não quer vigas altas de {preset['beam_height_cm']}cm rebaixando o living!"
                    ),
                    "feature_requested": "Permitir que eu aplique protensão ativa diretamente sem ter que refazer o projeto no CAD."
                })

    def _test_scenario_2_benchmarks(self):
        self.tested_features.append("Scenario 2: 100% Compliant Benchmarks")
        s2_keys = ["sobrado_grid_racional", "pavilhao_otimizado_aprovado", "edificio_modulado_comercial"]

        for key in s2_keys:
            preset = SAMPLE_PRESETS.get(key)
            if not preset:
                continue

            eval_res = StructuralCoreEngine.evaluate_structure(
                span_length_m=preset["span_length_m"],
                cantilever_length_m=preset["cantilever_length_m"],
                beam_height_cm=preset["beam_height_cm"],
                beam_width_cm=preset["beam_width_cm"],
                column_height_m=preset["column_height_m"],
                column_section_cm=preset["column_section_cm"],
                dead_load_kpa=preset["dead_load_kpa"],
                live_load_kpa=preset["live_load_kpa"],
                concrete_fck_mpa=preset["concrete_fck_mpa"]
            )

            is_viable = eval_res["is_physically_viable"]
            self.benchmark_records.append({
                "preset_key": key,
                "scenario": 2,
                "title": preset["title"],
                "score": eval_res["structural_score"],
                "is_viable": is_viable,
                "verdict": "CORRECT_PASS" if is_viable else "UNEXPECTED_FAIL"
            })

            if not is_viable:
                self.complaints.append({
                    "category": "False Negative",
                    "severity": "CRITICAL",
                    "target_feature": f"Scenario 2 ({key})",
                    "complaint": f"O projeto conforme '{preset['title']}' foi reprovado injustamente!",
                    "feature_requested": "Ajustar tolerâncias para evitar falsos negativos em grelhas regulares."
                })
            else:
                self.complaints.append({
                    "category": "UX & Detail",
                    "severity": "LOW",
                    "target_feature": f"Scenario 2 ({key})",
                    "complaint": f"O projeto passou com score {eval_res['structural_score']}, mas senti falta de ver a armadura de cisalhamento detalhada no corte 2D.",
                    "feature_requested": "Adicionar taxa de estribos por metro linear no relatório."
                })

    def _test_extreme_boundaries(self):
        self.tested_features.append("Boundary Stress Testing")
        
        # Test extreme 25m span with tiny 10cm beam
        extreme_eval = StructuralCoreEngine.evaluate_structure(
            span_length_m=25.0,
            beam_height_cm=10.0,
            beam_width_cm=12.0
        )
        if extreme_eval["is_physically_viable"]:
            self.complaints.append({
                "category": "Physics Safety",
                "severity": "CRITICAL",
                "target_feature": "Extreme Boundary Span (25m)",
                "complaint": "O motor permitiu um vão de 25m com viga de 10cm! Isso é fisicamente impossível.",
                "feature_requested": "Trava rígida para esbeltez extrema."
            })
        else:
            self.complaints.append({
                "category": "UI Friction",
                "severity": "MEDIUM",
                "target_feature": "Boundary Feedback",
                "complaint": "Quando coloquei vão de 25m a flecha calculada deu centenas de milímetros. A interface gráfica precisa de um aviso amigável que oriente para treliças espaciais imediatamente.",
                "feature_requested": "Alerta proativo sugerindo sistema em treliça metálica para vãos > 16m."
            })

    def _probe_dsm_and_voronoi(self):
        self.tested_features.append("Direct Stiffness Method (DSM) Frame Engine")
        dsm = DSMSolver.solve_portal_frame(span_length_m=12.0, distributed_load_kn_m=30.0)
        voronoi = DSMSolver.calculate_voronoi_tributary(bay_x_m=12.0, bay_y_m=6.0)

        if not dsm.get("exact_midspan_deflection_mm"):
            self.complaints.append({
                "category": "Calculation Bug",
                "severity": "HIGH",
                "target_feature": "DSM Frame Solver",
                "complaint": "O Direct Stiffness Method não retornou a flecha nodal calculada.",
                "feature_requested": "Garantir chave exact_midspan_deflection_mm sempre presente."
            })
        else:
            self.complaints.append({
                "category": "Competitive IP Probe",
                "severity": "LOW",
                "target_feature": "DSM Precision",
                "complaint": f"Tentei clonar o solver DSM: ele calculou {dsm['exact_midspan_deflection_mm']}mm no meio do vão com engastamento perfeito. Gostaria que mostrasse os momentos fletores nodais esquematizados em um gráfico de barras.",
                "feature_requested": "Adicionar visualização de diagrama de momento fletor (DMF) diretamente no Three.js."
            })

    def _probe_bim_exporters(self):
        self.tested_features.append("Native BIM IFC4 & AutoCAD DXF Exporters")
        params = {"span_length_m": 9.0, "beam_height_cm": 35.0, "beam_width_cm": 20.0}
        
        ifc_str = BimExporter.export_project_ifc("Teste_Agent", params)
        dxf_str = BimExporter.export_project_dxf("Teste_Agent", params)

        if "IFC4" not in ifc_str or "IfcBeam" not in ifc_str:
            self.complaints.append({
                "category": "BIM Export Error",
                "severity": "HIGH",
                "target_feature": "IFC4 Exporter",
                "complaint": "O arquivo IFC4 exportado não contém entidades IfcBeam válidas.",
                "feature_requested": "Corrigir geração de entidades IFC4."
            })

        if "ESTRUTURA_VIGAS" not in dxf_str:
            self.complaints.append({
                "category": "CAD Export Error",
                "severity": "HIGH",
                "target_feature": "AutoCAD DXF Exporter",
                "complaint": "O arquivo DXF gerado não possui a camada padrão ESTRUTURA_VIGAS.",
                "feature_requested": "Garantir padrão CAD ABNT no DXF."
            })

    def _audit_cost_and_carbon(self):
        self.tested_features.append("SINAPI 2026 & Embodied Carbon Engine")
        bom = CostCarbonEngine.calculate_bom_and_cost(span_length_m=8.0, concrete_fck_mpa=30.0)
        
        total_cost = bom["financial_sinapi_2026"]["total_estimated_brl"]
        total_co2 = bom["embodied_carbon_a1_a3"]["total_emissions_kg_co2"]

        if total_cost <= 0 or total_co2 <= 0:
            self.complaints.append({
                "category": "Financial Zero Error",
                "severity": "HIGH",
                "target_feature": "BOM & Carbon",
                "complaint": "O custo financeiro ou a emissão de carbono retornou zero ou negativo.",
                "feature_requested": "Validar valores mínimos de materiais."
            })
        else:
            self.complaints.append({
                "category": "Market Competitiveness",
                "severity": "LOW",
                "target_feature": "SINAPI Unit Prices",
                "complaint": f"O custo estimado da estrutura deu R$ {total_cost:.2f} (R$ {bom['financial_sinapi_2026']['cost_per_m2_brl']}/m²). O aço CA-50 a R$ 9.85/kg está alinhado com o SINAPI 2026, mas em regiões do Norte/Nordeste o frete encarece em 15%.",
                "feature_requested": "Adicionar seletor de estado (UF) para ajuste de BDI regional."
            })
