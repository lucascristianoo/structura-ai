"""
NBR 6118 Section Catalog Optimizer (OptiSection).
Performs discrete cross-section optimization against standard commercial concrete catalogs
and structural steel profiles to determine the most cost-effective and architecturally slim sections.
"""
import math
from typing import Dict, Any, List


class OptiSectionEngine:
    """
    Evaluates commercial section catalogs against ABNT NBR 6118:2023 (Concrete)
    and ABNT NBR 8800:2008 (Steel) to select the optimal structural dimensions.
    """

    # Standard Brazilian Commercial Concrete Beam Sections (width_cm, height_cm)
    COMMERCIAL_CONCRETE_SECTIONS = [
        (15.0, 30.0), (15.0, 40.0), (15.0, 50.0),
        (20.0, 30.0), (20.0, 35.0), (20.0, 40.0), (20.0, 45.0), (20.0, 50.0),
        (20.0, 60.0), (20.0, 70.0),
        (25.0, 40.0), (25.0, 50.0), (25.0, 60.0), (25.0, 70.0), (25.0, 80.0),
        (30.0, 60.0), (30.0, 70.0), (30.0, 80.0), (30.0, 100.0)
    ]

    # Standard Commercial Steel W-Shapes (Aço ASTM A572 Gr. 50 / Gerdau)
    # (name, depth_mm, flange_width_mm, mass_kg_m, Ix_cm4, Wx_cm3)
    COMMERCIAL_STEEL_SECTIONS = [
        ("W 200 x 26.6", 207.0, 133.0, 26.6, 2611.0, 252.0),
        ("W 250 x 38.5", 262.0, 147.0, 38.5, 6088.0, 465.0),
        ("W 310 x 52.0", 317.0, 167.0, 52.0, 12908.0, 814.0),
        ("W 360 x 64.0", 347.0, 203.0, 64.0, 21820.0, 1258.0),
        ("W 410 x 75.0", 412.0, 180.0, 75.0, 33890.0, 1645.0),
        ("W 460 x 82.0", 460.0, 191.0, 82.0, 47100.0, 2048.0),
        ("W 530 x 92.0", 533.0, 209.0, 92.0, 65200.0, 2446.0),
    ]

    @classmethod
    def optimize_beam_section(
        cls,
        span_length_m: float = 10.0,
        distributed_load_kn_m: float = 25.0,
        concrete_fck_mpa: float = 30.0,
        current_beam_height_cm: float = 30.0,
        current_beam_width_cm: float = 20.0,
    ) -> Dict[str, Any]:
        """
        Tests all catalog sections to find the minimum volume and minimum depth solutions
        satisfying NBR 6118 deflection limits (L/250) and shear capacity.
        """
        l_m = max(float(span_length_m or 1.0), 1.0)
        q_ser = max(float(distributed_load_kn_m or 1.0), 1.0)
        q_elu = q_ser * 1.4
        safe_fck = min(max(float(concrete_fck_mpa or 15.0), 15.0), 120.0)
        current_beam_height_cm = max(float(current_beam_height_cm or 30.0), 12.0)
        current_beam_width_cm = max(float(current_beam_width_cm or 20.0), 12.0)
        fcd_mpa = safe_fck / 1.4
        fcd_kpa = fcd_mpa * 1000.0
        e_gpa = 5600.0 * math.sqrt(safe_fck) / 1000.0
        e_kpa = e_gpa * 1e6
        allowable_deflection_mm = (l_m / 250.0) * 1000.0

        compliant_concrete: List[Dict[str, Any]] = []

        for bw_cm, bh_cm in cls.COMMERCIAL_CONCRETE_SECTIONS:
            bw_m = bw_cm / 100.0
            bh_m = bh_cm / 100.0

            # Inertia cracked
            i_gross = (bw_m * (bh_m ** 3)) / 12.0
            i_eff = 0.50 * i_gross
            ei = e_kpa * i_eff

            # Total long term deflection (fluência = 2.0)
            deflection_m = (2.5 * q_ser * (l_m ** 4)) / (384.0 * ei) * 3.0
            deflection_mm = deflection_m * 1000.0

            # Shear check: V_rd2 (esmagamento da biela)
            v_sd = q_elu * l_m / 2.0
            v_rd2 = 0.27 * (1.0 - safe_fck / 250.0) * fcd_kpa * bw_m * (bh_m * 0.9)
            shear_ok = v_sd <= v_rd2

            is_ok = (deflection_mm <= allowable_deflection_mm) and shear_ok

            volume_m3 = bw_m * bh_m * l_m
            est_cost_brl = volume_m3 * (495.0 + 85.0 * 9.85 + 92.0 * 2.0)

            section_record = {
                "section": f"{int(bw_cm)}x{int(bh_cm)}cm",
                "width_cm": bw_cm,
                "height_cm": bh_cm,
                "deflection_mm": round(deflection_mm, 1),
                "allowable_mm": round(allowable_deflection_mm, 1),
                "deflection_ratio": round(deflection_mm / allowable_deflection_mm, 2),
                "shear_ratio": round(v_sd / max(v_rd2, 1.0), 2),
                "volume_m3": round(volume_m3, 2),
                "estimated_cost_brl": round(est_cost_brl, 2),
                "status": "PASS" if is_ok else "FAIL",
            }
            if is_ok:
                compliant_concrete.append(section_record)

        # Sort compliant by cost/volume (most economic)
        compliant_concrete.sort(key=lambda s: s["volume_m3"])
        best_economic_rc = compliant_concrete[0] if compliant_concrete else None

        # Sort compliant by height (slimmest profile)
        slimmest_rc = min(compliant_concrete, key=lambda s: s["height_cm"]) if compliant_concrete else None

        # Steel Profile Evaluation
        compliant_steel: List[Dict[str, Any]] = []
        e_steel_kpa = 200.0 * 1e6
        for name, d_mm, bf_mm, mass_kg, ix_cm4, wx_cm3 in cls.COMMERCIAL_STEEL_SECTIONS:
            ix_m4 = ix_cm4 * 1e-8
            ei_s = e_steel_kpa * ix_m4
            # Deflection simple span: 5 * q * L^4 / (384 * EI)
            defl_steel_mm = (5.0 * q_ser * (l_m ** 4)) / (384.0 * ei_s) * 1000.0
            # Elastic stress check: M / Wx <= fy
            m_sd_knm = (q_elu * (l_m ** 2)) / 8.0
            wx_m3 = wx_cm3 * 1e-6
            sigma_mpa = (m_sd_knm / wx_m3) / 1000.0
            steel_ok = (defl_steel_mm <= allowable_deflection_mm) and (sigma_mpa <= 345.0)

            total_mass_kg = mass_kg * l_m
            cost_steel_brl = total_mass_kg * 16.50 * 1.35

            if steel_ok:
                compliant_steel.append({
                    "profile": name,
                    "depth_mm": d_mm,
                    "mass_total_kg": round(total_mass_kg, 1),
                    "deflection_mm": round(defl_steel_mm, 1),
                    "bending_stress_mpa": round(sigma_mpa, 1),
                    "estimated_cost_brl": round(cost_steel_brl, 2),
                    "status": "PASS",
                })

        best_steel = compliant_steel[0] if compliant_steel else None

        return {
            "evaluated_span_m": l_m,
            "allowable_deflection_mm": round(allowable_deflection_mm, 1),
            "current_section": f"{int(current_beam_width_cm)}x{int(current_beam_height_cm)}cm",
            "optimal_concrete_economic": best_economic_rc,
            "optimal_concrete_slim": slimmest_rc,
            "optimal_steel_w_profile": best_steel,
            "total_compliant_rc_sections_found": len(compliant_concrete),
            "recommendation_summary": (
                f"Para o vão de {l_m:.1f}m, a seção de concreto mais econômica é {best_economic_rc['section'] if best_economic_rc else 'Sob Medida'}, "
                f"atendendo à NBR 6118 com flecha de {best_economic_rc['deflection_mm'] if best_economic_rc else '-'}mm. "
                f"Caso necessite de altura reduzida, a seção {slimmest_rc['section'] if slimmest_rc else '-'} é a menor admissível."
            ),
        }
