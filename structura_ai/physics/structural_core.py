"""
Deterministic Structural Physics & Finite Compliance Engine.
Evaluates beam flexure, serviceability deflection (ELS), cantilever equilibrium,
and column Euler buckling stability per ABNT NBR 6118:2023.
"""
import math
from typing import Dict, Any, List
from structura_ai.physics.nbr_standards import ConcreteProperties, DeflectionLimits, ColumnLimits
from structura_ai.physics.load_calculator import LoadCalculator
from structura_ai.physics.cost_carbon_engine import CostCarbonEngine
from structura_ai.physics.dsm_solver import DSMSolver
from structura_ai.physics.optisection import OptiSectionEngine

class StructuralCoreEngine:
    """
    Core civil engineering physics engine for architectural project validation.
    """

    @classmethod
    def evaluate_structure(
        cls,
        span_length_m: float = 9.5,
        cantilever_length_m: float = 3.5,
        beam_height_cm: float = 30.0,
        beam_width_cm: float = 20.0,
        column_height_m: float = 3.2,
        column_section_cm: float = 20.0,
        dead_load_kpa: float = 4.5,
        live_load_kpa: float = 2.5,
        concrete_fck_mpa: float = 30.0,
        tributary_width_m: float = 4.0,
        category: str = "Residencial"
    ) -> Dict[str, Any]:
        """
        Executes complete structural mechanics evaluation.
        Returns safety factor, deflection, bending moments, failure diagnostic, and verdict.
        """
        # Material stiffness
        e_gpa = ConcreteProperties.get_elastic_modulus_gpa(concrete_fck_mpa)
        e_kpa = e_gpa * 1e6  # kN/m²
        creep_factor = ConcreteProperties.get_long_term_creep_factor()

        # Geometry conversions
        bw_m = max(beam_width_cm / 100.0, 0.12)
        h_m = max(beam_height_cm / 100.0, 0.15)
        
        # Gross Moment of Inertia for beam (m^4)
        i_gross = (bw_m * (h_m ** 3)) / 12.0
        # NBR 6118 item 17.3.2.1.1: Cracked section effective inertia (EI)_eff ~= 0.5 * (EI)_gross
        i_eff = 0.50 * i_gross
        stiffness_ei = e_kpa * i_eff  # kN*m²

        # Load Calculation with physical safeguards
        safe_dead_load_kpa = max(dead_load_kpa, 1.5)
        slab_thickness_m = 0.12
        slab_self_weight = slab_thickness_m * 25.0  # 3.0 kN/m²
        finishing_load_kpa = max(safe_dead_load_kpa - slab_self_weight, 0.5)

        loads = LoadCalculator.calculate_distributed_load(
            tributary_width_m=tributary_width_m,
            slab_thickness_m=slab_thickness_m,
            finishing_load_kpa=finishing_load_kpa,
            live_load_kpa=max(live_load_kpa, 1.0),
            beam_width_m=bw_m,
            beam_height_m=h_m
        )
        q_ser = loads["q_total_service_kn_m"]
        q_elu = loads["q_factored_elu_kn_m"]

        failures: List[str] = []
        checklist: Dict[str, Any] = {}

        # -------------------------------------------------------------
        # 1. MAIN BEAM SPAN ANALYSIS (Vão Livre Principal)
        # -------------------------------------------------------------
        # Monolithic concrete frames have end rotational stiffness from columns (semi-rigid)
        # Moment coefficient M ~= q * L^2 / 10 to q * L^2 / 8
        max_moment_knm = (q_elu * (span_length_m ** 2)) / 10.0
        shear_kn = (q_elu * span_length_m) / 2.0
        
        # Immediate elastic deflection with semi-rigid framed joint restraint factor (2.5 / 384)
        immediate_deflection_m = (2.5 * q_ser * (span_length_m ** 4)) / (384.0 * stiffness_ei)
        # Total long-term deflection including creep (fluência do concreto alpha_f)
        total_deflection_mm = round(immediate_deflection_m * (1.0 + creep_factor) * 1000.0, 1)

        # Allowable deflection limit (NBR 6118: L / 250)
        allowable_deflection_mm = round(DeflectionLimits.visual_sag_limit_mm(span_length_m), 1)
        deflection_ratio = round(total_deflection_mm / max(allowable_deflection_mm, 0.1), 2)

        # Recommended minimum structural depth (rule of thumb: L / 12 to L / 15)
        recommended_h_min_cm = round((span_length_m / 13.0) * 100.0, 0)
        depth_ratio = beam_height_cm / max(recommended_h_min_cm, 1.0)

        beam_deflection_ok = total_deflection_mm <= allowable_deflection_mm
        checklist["flecha_vao_principal"] = {
            "status": "PASS" if beam_deflection_ok else "FAIL",
            "valor_calculado_mm": total_deflection_mm,
            "limite_nbr6118_mm": allowable_deflection_mm,
            "razao": deflection_ratio
        }

        if not beam_deflection_ok:
            failures.append(
                f"Flecha excessiva no vão principal de {span_length_m:.1f}m: deformação total de {total_deflection_mm}mm "
                f"supera o limite normativo NBR 6118 de {allowable_deflection_mm}mm (excesso de {round((deflection_ratio - 1)*100)}%). "
                f"Altura da viga ({beam_height_cm:.0f}cm) insuficiente para o vão (recomendado mínimo {recommended_h_min_cm:.0f}cm)."
            )

        # -------------------------------------------------------------
        # 2. CANTILEVER ANALYSIS (Balanço Estrutural)
        # -------------------------------------------------------------
        cantilever_stability_factor = 1.0
        cantilever_deflection_mm = 0.0
        cantilever_allowable_mm = 0.0

        if cantilever_length_m > 0.0:
            cantilever_moment_knm = (q_elu * (cantilever_length_m ** 2)) / 2.0
            cantilever_immediate_m = (q_ser * (cantilever_length_m ** 4)) / (8.0 * stiffness_ei)
            cantilever_deflection_mm = round(cantilever_immediate_m * (1.0 + creep_factor) * 1000.0, 1)
            cantilever_allowable_mm = round(DeflectionLimits.cantilever_visual_limit_mm(cantilever_length_m), 1)
            
            c_deflection_ratio = round(cantilever_deflection_mm / max(cantilever_allowable_mm, 0.1), 2)
            
            # Cantilever span to beam depth check: usually cantilever depth h >= L_c / 6 to L_c / 8
            req_cantilever_h_cm = (cantilever_length_m / 7.0) * 100.0
            
            cantilever_ok = (cantilever_deflection_mm <= cantilever_allowable_mm) and (beam_height_cm >= req_cantilever_h_cm * 0.85)
            checklist["balanco_estrutural"] = {
                "status": "PASS" if cantilever_ok else "FAIL",
                "comprimento_m": cantilever_length_m,
                "flecha_ponta_mm": cantilever_deflection_mm,
                "limite_nbr6118_mm": cantilever_allowable_mm,
                "momento_engaste_knm": round(cantilever_moment_knm, 1)
            }

            if not cantilever_ok:
                cantilever_stability_factor = round(cantilever_allowable_mm / max(cantilever_deflection_mm, 0.1), 2)
                failures.append(
                    f"Balanço crítico de {cantilever_length_m:.1f}m sem travamento adequado: flecha na extremidade de {cantilever_deflection_mm}mm "
                    f"ultrapassa o limite de {cantilever_allowable_mm}mm. Risco de fissuração severa e rotação do engaste."
                )

        # -------------------------------------------------------------
        # 3. COLUMN BUCKLING & AXIAL CAPACITY (Flambagem e Estabilidade de Pilares)
        # -------------------------------------------------------------
        c_sec_m = max(column_section_cm / 100.0, 0.14)
        c_area_m2 = c_sec_m * c_sec_m
        c_i_m4 = (c_sec_m ** 4) / 12.0
        c_radius_gyration_m = c_sec_m / math.sqrt(12.0)
        
        # Slenderness lambda = (K * L) / r
        k_factor = 1.0  # Biapoiado/Translação travada
        effective_col_length_m = k_factor * column_height_m
        col_slenderness = round(effective_col_length_m / c_radius_gyration_m, 1)
        
        # Euler Critical Buckling Load P_cr = (pi^2 * E * I) / (L_e^2)
        p_cr_kn = (math.pi ** 2 * e_kpa * c_i_m4) / (effective_col_length_m ** 2)
        
        # Tributary vertical load N_sd
        # Tributary area roughly (span / 2) * tributary_width
        col_tributary_area = (span_length_m / 2.0) * tributary_width_m
        estimated_axial_load_kn = col_tributary_area * (dead_load_kpa + live_load_kpa) * 1.4
        
        # Buckling safety ratio
        buckling_utilization = round((estimated_axial_load_kn * 2.0) / max(p_cr_kn, 1.0), 2)

        col_slenderness_ok = col_slenderness <= ColumnLimits.MAX_SLENDERNESS_LAMBDA
        col_axial_ok = buckling_utilization <= 1.0

        checklist["esbeltez_pilar"] = {
            "status": "PASS" if col_slenderness_ok and col_axial_ok else "FAIL",
            "indice_esbeltez_lambda": col_slenderness,
            "limite_lambda_nbr6118": ColumnLimits.MAX_SLENDERNESS_LAMBDA,
            "carga_critica_euler_kn": round(p_cr_kn, 1),
            "carga_atuante_estimada_kn": round(estimated_axial_load_kn, 1),
            "razao_utilizacao": buckling_utilization
        }

        if not col_slenderness_ok:
            failures.append(
                f"Pilar com esbeltez crítica (lambda = {col_slenderness:.1f} > limite normativo de {ColumnLimits.MAX_SLENDERNESS_LAMBDA}). "
                f"Seção de {column_section_cm:.0f}x{column_section_cm:.0f}cm insuficiente para pé-direito de {column_height_m:.1f}m, vulnerável a flambagem por compressão centrada e flexo-compressão."
            )
        elif not col_axial_ok:
            failures.append(
                f"Carga vertical atuante no pilar ({estimated_axial_load_kn:.1f} kN) próxima da carga crítica de Euler ({p_cr_kn:.1f} kN). "
                f"Fator de segurança contra flambagem abaixo do admissível pela NBR 6118."
            )

        # -------------------------------------------------------------
        # 4. OVERALL FEASIBILITY & COMPLIANCE SCORE
        # -------------------------------------------------------------
        # Base score 100, penalties for each structural deficiency
        score = 100.0
        if deflection_ratio > 1.0:
            penalty = min((deflection_ratio - 1.0) * 35.0, 45.0)
            score -= penalty
            
        if cantilever_stability_factor < 1.0:
            penalty = min((1.0 - cantilever_stability_factor) * 30.0, 30.0)
            score -= penalty
            
        if col_slenderness > 90.0:
            penalty = min(((col_slenderness - 90.0) / 50.0) * 25.0, 25.0)
            score -= penalty

        score = max(round(score, 1), 12.0)
        is_viable = len(failures) == 0 and score >= 75.0

        if is_viable:
            compliance_level = "Aprovado para Detalhamento"
            diagnosis_text = (
                f"O projeto atende com excelência aos critérios normativos de física estrutural da ABNT NBR 6118:2023. "
                f"A rigidez da seção transversal (viga {beam_height_cm:.0f}cm x {beam_width_cm:.0f}cm) suporta com folga o vão livre de {span_length_m:.1f}m, "
                f"mantendo a flecha máxima calculada ({total_deflection_mm}mm) confortavelmente abaixo da tolerância admissível ({allowable_deflection_mm}mm). "
                f"Os pilares apresentam taxa de esbeltez estável ({col_slenderness:.1f}) contra flambagem Euleriana. O projeto pode prosseguir para modelagem executiva."
            )
        else:
            if score >= 50.0:
                compliance_level = "Alerta - Ajustes Recomendados"
            else:
                compliance_level = "Crítico - Reprovação Estrutural Imediata"
                
            diagnosis_text = (
                f"O modelo arquitetônico atual viola leis fundamentais da mecânica das estruturas e limites de serviço da NBR 6118:2023. "
                f"A relação entre vão livre ({span_length_m:.1f}m) e espessura da viga ({beam_height_cm:.0f}cm) produz deformação elasto-plástica inaceitável "
                f"({total_deflection_mm}mm contra limite de {allowable_deflection_mm}mm), o que causará trincas severas em alvenarias e sensação de insegurança aos ocupantes. "
                f"Foram identificados {len(failures)} ponto(s) de intervenção mandatória antes do envio ao engenheiro calculista."
            )

        # Calculate BOM, SINAPI 2026 Cost and Embodied Carbon
        bom_data = CostCarbonEngine.calculate_bom_and_cost(
            span_length_m=span_length_m,
            cantilever_length_m=cantilever_length_m,
            beam_height_cm=beam_height_cm,
            beam_width_cm=beam_width_cm,
            column_height_m=column_height_m,
            column_section_cm=column_section_cm,
            tributary_width_m=tributary_width_m,
            concrete_fck_mpa=concrete_fck_mpa,
            system_type="standard_rc"
        )

        # Run Direct Stiffness Method (DSM) Frame Analysis
        dsm_result = DSMSolver.solve_portal_frame(
            span_length_m=span_length_m,
            cantilever_length_m=cantilever_length_m,
            beam_height_cm=beam_height_cm,
            beam_width_cm=beam_width_cm,
            column_height_m=column_height_m,
            column_section_cm=column_section_cm,
            elastic_modulus_gpa=e_gpa,
            distributed_load_kn_m=q_ser
        )

        # Run Section Catalog Optimizer
        optisection_result = OptiSectionEngine.optimize_beam_section(
            span_length_m=span_length_m,
            distributed_load_kn_m=q_ser,
            concrete_fck_mpa=concrete_fck_mpa,
            current_beam_height_cm=beam_height_cm,
            current_beam_width_cm=beam_width_cm
        )

        return {
            "is_physically_viable": is_viable,
            "structural_score": score,
            "compliance_level": compliance_level,
            "max_deflection_mm": total_deflection_mm,
            "allowable_deflection_mm": allowable_deflection_mm,
            "deflection_ratio": deflection_ratio,
            "max_bending_moment_knm": round(max_moment_knm, 1),
            "shear_utilization_ratio": round(shear_kn / max((bw_m * h_m * 1000.0 * 0.25 * math.sqrt(concrete_fck_mpa)), 1.0), 2),
            "critical_column_buckling_ratio": buckling_utilization,
            "cantilever_stability_factor": cantilever_stability_factor,
            "failure_reasons": failures,
            "compliance_checklist": checklist,
            "structural_diagnosis_text": diagnosis_text,
            "calculated_inputs": {
                "span_length_m": span_length_m,
                "cantilever_length_m": cantilever_length_m,
                "beam_height_cm": beam_height_cm,
                "beam_width_cm": beam_width_cm,
                "column_height_m": column_height_m,
                "column_section_cm": column_section_cm,
                "fck_mpa": concrete_fck_mpa
            },
            "bom_and_cost": bom_data,
            "dsm_analysis": dsm_result,
            "section_optimization": optisection_result,
        }
