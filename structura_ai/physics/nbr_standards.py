"""
ABNT NBR 6118:2023 & NBR 6120:2019 Structural Standards & Coefficients.
Includes normative deflection limits, concrete properties, and load combinations.
"""
import math

class ConcreteProperties:
    """Calculates concrete stiffness and material parameters."""
    @staticmethod
    def get_elastic_modulus_gpa(fck_mpa: float = 30.0, aggregate_factor: float = 1.0) -> float:
        """
        NBR 6118 item 8.2.8:
        E_ci = alpha_E * 5600 * sqrt(fck) in MPa.
        Returns value in GPa.
        """
        safe_fck = max(float(fck_mpa or 15.0), 15.0)
        e_ci_mpa = max(float(aggregate_factor or 1.0), 0.5) * 5600.0 * math.sqrt(safe_fck)
        # Tangent initial modulus to secant modulus Ecs = alpha_i * Eci
        alpha_i = min(0.8 + 0.2 * (safe_fck / 80.0), 1.0)
        e_cs_mpa = e_ci_mpa * alpha_i
        return e_cs_mpa / 1000.0  # Convert to GPa (kN/mm² or 10^6 kN/m²)

    @staticmethod
    def get_long_term_creep_factor() -> float:
        """
        NBR 6118 item 17.3.2.1.2:
        Long-term creep coefficient (alpha_f = Delta_xi / (1 + 50*rho')).
        Typically 1.2 to 1.4 for beam sections with nominal compression reinforcement.
        """
        return 1.3


class DeflectionLimits:
    """NBR 6118:2023 Table 13.2 - Serviceability Limit State (ELS) Limits."""
    @staticmethod
    def visual_sag_limit_mm(span_m: float) -> float:
        """Visual acceptability limit: delta_adm = L / 250."""
        return (span_m * 1000.0) / 250.0

    @staticmethod
    def masonry_damage_limit_mm(span_m: float) -> float:
        """Damage to brittle masonry walls underneath: delta_adm = L / 350."""
        return (span_m * 1000.0) / 350.0

    @staticmethod
    def cantilever_visual_limit_mm(cantilever_length_m: float) -> float:
        """Cantilever visual acceptability: delta_adm = 2 * Lc / 250 = Lc / 125."""
        return (cantilever_length_m * 1000.0) / 125.0


class ColumnLimits:
    """NBR 6118 item 15.8.1 - Column slenderness & stability."""
    MAX_SLENDERNESS_LAMBDA: float = 140.0
    WARNING_SLENDERNESS_LAMBDA: float = 90.0
