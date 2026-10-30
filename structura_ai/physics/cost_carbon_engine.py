"""
Quantitative Bill of Materials (BOM), SINAPI 2026 / CUB R$ Cost Engine,
and Embodied Carbon Lifecycle (A1-A3) Calculator for Brazilian Structural Projects.
"""
from typing import Dict, Any, Optional


class CostCarbonEngine:
    """
    Computes precise material takeoffs, financial estimates based on SINAPI/CUB 2026,
    and Cradle-to-Gate (A1-A3) Embodied Carbon emissions for reinforced concrete
    and hybrid structural systems.
    """

    # Reference Unit Costs (SINAPI 2026 / CUB Médio Brasil - R$)
    COST_CONCRETE_C25_M3 = 450.00
    COST_CONCRETE_C30_M3 = 495.00
    COST_CONCRETE_C40_M3 = 570.00
    COST_CONCRETE_C50_M3 = 650.00
    COST_STEEL_CA50_KG = 9.85
    COST_POST_TENSION_CABLE_KG = 24.50
    COST_STRUCTURAL_STEEL_KG = 16.50
    COST_FORMWORK_M2 = 92.00
    LABOR_AND_EQUIPMENT_FACTOR = 1.35  # BDI e mão de obra indireta

    # Embodied Carbon Emission Factors (kg CO2e / unit) - A1-A3 Lifecycle (Ecoinvent / SIDAC Brasil)
    CO2_CONCRETE_C25_M3 = 285.0
    CO2_CONCRETE_C30_M3 = 320.0
    CO2_CONCRETE_C40_M3 = 390.0
    CO2_CONCRETE_C50_M3 = 460.0
    CO2_STEEL_CA50_KG = 1.82
    CO2_POST_TENSION_KG = 2.10
    CO2_STRUCTURAL_STEEL_KG = 2.25

    @classmethod
    def get_concrete_cost_per_m3(cls, fck_mpa: float) -> float:
        if fck_mpa <= 25.0:
            return cls.COST_CONCRETE_C25_M3
        elif fck_mpa <= 30.0:
            return cls.COST_CONCRETE_C30_M3
        elif fck_mpa <= 40.0:
            return cls.COST_CONCRETE_C40_M3
        else:
            return cls.COST_CONCRETE_C50_M3

    @classmethod
    def get_concrete_co2_factor(cls, fck_mpa: float) -> float:
        if fck_mpa <= 25.0:
            return cls.CO2_CONCRETE_C25_M3
        elif fck_mpa <= 30.0:
            return cls.CO2_CONCRETE_C30_M3
        elif fck_mpa <= 40.0:
            return cls.CO2_CONCRETE_C40_M3
        else:
            return cls.CO2_CONCRETE_C50_M3

    @classmethod
    def calculate_bom_and_cost(
        cls,
        span_length_m: float = 10.0,
        cantilever_length_m: float = 0.0,
        beam_height_cm: float = 30.0,
        beam_width_cm: float = 20.0,
        column_height_m: float = 3.2,
        column_section_cm: float = 20.0,
        num_columns: int = 2,
        tributary_width_m: float = 4.0,
        concrete_fck_mpa: float = 30.0,
        system_type: str = "standard_rc"  # "standard_rc", "post_tensioned", "vierendeel", "stayed", "waffle", "steel_hybrid"
    ) -> Dict[str, Any]:
        """
        Computes BOM, SINAPI 2026 cost, and A1-A3 embodied carbon.
        """
        span_m = max(span_length_m, 1.0)
        cantilever_m = max(cantilever_length_m, 0.0)
        total_beam_len_m = span_m + cantilever_m
        bw_m = max(beam_width_cm / 100.0, 0.12)
        bh_m = max(beam_height_cm / 100.0, 0.15)
        col_w_m = max(column_section_cm / 100.0, 0.14)
        col_h_m = max(column_height_m, 2.0)
        tributary_w = max(tributary_width_m, 1.0)
        footprint_area_m2 = total_beam_len_m * tributary_w

        # 1. Concrete Volumes
        v_beam_m3 = total_beam_len_m * bw_m * bh_m
        v_cols_m3 = num_columns * (col_w_m * col_w_m * col_h_m)
        slab_thick_m = 0.12
        v_slab_m3 = footprint_area_m2 * slab_thick_m

        # Formwork areas (m2)
        formwork_beam_m2 = total_beam_len_m * (bw_m + 2.0 * bh_m)
        formwork_cols_m2 = num_columns * (4.0 * col_w_m * col_h_m)
        formwork_slab_m2 = footprint_area_m2
        total_formwork_m2 = formwork_beam_m2 + formwork_cols_m2 + formwork_slab_m2

        # Adjust volumes and materials according to structural system
        steel_pt_kg = 0.0
        structural_steel_kg = 0.0

        if system_type == "post_tensioned":
            # Post-tensioning reduces slab/beam concrete volume by ~22%, adds CP-190 cables
            v_beam_m3 *= 0.78
            v_slab_m3 *= 0.82
            steel_rc_kg = (v_beam_m3 + v_cols_m3 + v_slab_m3) * 45.0  # Reduced rebar density
            steel_pt_kg = footprint_area_m2 * 4.2  # kg of CP-190 tendons
        elif system_type == "waffle":
            # Waffle slab saves ~30% concrete volume through polystyrene or polypropylene voids
            v_slab_m3 *= 0.68
            steel_rc_kg = (v_beam_m3 + v_cols_m3 + v_slab_m3) * 75.0
        elif system_type == "steel_hybrid":
            # Steel truss replaces heavy concrete beam
            structural_steel_kg = total_beam_len_m * 42.0  # W-profile weight
            v_beam_m3 = 0.0
            formwork_beam_m2 = 0.0
            total_formwork_m2 = formwork_cols_m2 + formwork_slab_m2
            steel_rc_kg = (v_cols_m3 + v_slab_m3) * 65.0
        elif system_type == "vierendeel":
            # Exoskeleton Vierendeel utilizes wall stiffness; higher rebar in chords
            v_beam_m3 *= 1.15
            steel_rc_kg = (v_beam_m3 + v_cols_m3 + v_slab_m3) * 92.0
        elif system_type == "stayed":
            # Inclined columns and tension rods
            steel_pt_kg = total_beam_len_m * 12.0  # High-strength steel stays
            steel_rc_kg = (v_beam_m3 + v_cols_m3 + v_slab_m3) * 78.0
        else:
            # Standard RC Frame
            # Average rebar consumption: 85 kg/m3 for beams/slabs, 110 kg/m3 for columns
            steel_rc_kg = (v_beam_m3 + v_slab_m3) * 85.0 + v_cols_m3 * 110.0

        total_concrete_m3 = v_beam_m3 + v_cols_m3 + v_slab_m3

        # Cost calculations
        unit_conc_cost = cls.get_concrete_cost_per_m3(concrete_fck_mpa)
        cost_concrete_brl = total_concrete_m3 * unit_conc_cost
        cost_steel_rc_brl = steel_rc_kg * cls.COST_STEEL_CA50_KG
        cost_steel_pt_brl = steel_pt_kg * cls.COST_POST_TENSION_CABLE_KG
        cost_steel_struct_brl = structural_steel_kg * cls.COST_STRUCTURAL_STEEL_KG
        cost_formwork_brl = total_formwork_m2 * cls.COST_FORMWORK_M2

        subtotal_materials_brl = (
            cost_concrete_brl
            + cost_steel_rc_brl
            + cost_steel_pt_brl
            + cost_steel_struct_brl
            + cost_formwork_brl
        )
        total_cost_brl = subtotal_materials_brl * cls.LABOR_AND_EQUIPMENT_FACTOR
        cost_per_m2_brl = total_cost_brl / max(footprint_area_m2, 1.0)

        # Carbon Emissions A1-A3
        unit_co2_conc = cls.get_concrete_co2_factor(concrete_fck_mpa)
        co2_concrete_kg = total_concrete_m3 * unit_co2_conc
        co2_steel_rc_kg = steel_rc_kg * cls.CO2_STEEL_CA50_KG
        co2_steel_pt_kg = steel_pt_kg * cls.CO2_POST_TENSION_KG
        co2_steel_struct_kg = structural_steel_kg * cls.CO2_STRUCTURAL_STEEL_KG
        total_co2_kg = (
            co2_concrete_kg + co2_steel_rc_kg + co2_steel_pt_kg + co2_steel_struct_kg
        )
        co2_per_m2_kg = total_co2_kg / max(footprint_area_m2, 1.0)

        return {
            "system_type": system_type,
            "footprint_area_m2": round(footprint_area_m2, 1),
            "quantities": {
                "concrete_volume_total_m3": round(total_concrete_m3, 2),
                "concrete_beam_m3": round(v_beam_m3, 2),
                "concrete_columns_m3": round(v_cols_m3, 2),
                "concrete_slab_m3": round(v_slab_m3, 2),
                "formwork_area_m2": round(total_formwork_m2, 1),
                "steel_rebar_ca50_kg": round(steel_rc_kg, 1),
                "steel_post_tension_kg": round(steel_pt_kg, 1),
                "steel_structural_kg": round(structural_steel_kg, 1),
            },
            "financial_sinapi_2026": {
                "concrete_brl": round(cost_concrete_brl, 2),
                "steel_ca50_brl": round(cost_steel_rc_brl, 2),
                "steel_special_brl": round(cost_steel_pt_brl + cost_steel_struct_brl, 2),
                "formwork_brl": round(cost_formwork_brl, 2),
                "labor_equipment_bdi_brl": round(total_cost_brl - subtotal_materials_brl, 2),
                "total_estimated_brl": round(total_cost_brl, 2),
                "cost_per_m2_brl": round(cost_per_m2_brl, 2),
                "currency": "BRL (R$)",
                "sinapi_base": "2026 / CUB-Medio",
            },
            "embodied_carbon_a1_a3": {
                "concrete_emissions_kg_co2": round(co2_concrete_kg, 1),
                "steel_emissions_kg_co2": round(
                    co2_steel_rc_kg + co2_steel_pt_kg + co2_steel_struct_kg, 1
                ),
                "total_emissions_kg_co2": round(total_co2_kg, 1),
                "emissions_intensity_kg_co2_per_m2": round(co2_per_m2_kg, 1),
                "standard": "ISO 14040 / A1-A3 Cradle-to-Gate",
            },
        }
