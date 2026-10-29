"""
Structural Load Calculator according to NBR 6120:2019.
Combines dead loads (peso próprio, revestimentos) and live loads (sobrecargas normativas).
"""
from typing import Dict, Any

OCCUPANCY_LIVE_LOADS_KPA = {
    "Residencial": 2.0,      # NBR 6120 Tabela 2 - Salas e dormitórios: 1.5 - 2.0 kN/m²
    "Comercial": 3.0,        # Escritórios e salas comerciais: 2.5 - 3.0 kN/m²
    "Institucional": 4.0,    # Escolas, auditórios, bibliotecas: 4.0 kN/m²
    "Cobertura/Terraço": 2.5,# Terraços transitáveis: 2.0 - 2.5 kN/m²
    "Garagem": 3.0           # Garagens de veículos leves: 3.0 kN/m²
}

CONCRETE_DENSITY_KN_M3 = 25.0  # Concreto armado: 25 kN/m³

class LoadCalculator:
    @staticmethod
    def calculate_distributed_load(
        tributary_width_m: float,
        slab_thickness_m: float = 0.12,
        finishing_load_kpa: float = 1.5,
        live_load_kpa: float = 2.0,
        beam_width_m: float = 0.20,
        beam_height_m: float = 0.40,
        gamma_g: float = 1.4,
        gamma_q: float = 1.4
    ) -> Dict[str, float]:
        """
        Calculates line load q (kN/m) along the beam.
        """
        # Beam self weight
        beam_self_weight_kn_m = beam_width_m * beam_height_m * CONCRETE_DENSITY_KN_M3
        
        # Slab dead load per m²
        slab_dead_load_kpa = slab_thickness_m * CONCRETE_DENSITY_KN_M3
        total_dead_load_kpa = slab_dead_load_kpa + finishing_load_kpa
        
        # Distributed line load (serviceability - ELS)
        q_dead_service_kn_m = beam_self_weight_kn_m + (total_dead_load_kpa * tributary_width_m)
        q_live_service_kn_m = live_load_kpa * tributary_width_m
        q_total_service_kn_m = q_dead_service_kn_m + q_live_service_kn_m
        
        # Factored line load (ultimate limit state - ELU)
        q_factored_elu_kn_m = (gamma_g * q_dead_service_kn_m) + (gamma_q * q_live_service_kn_m)
        
        return {
            "beam_self_weight_kn_m": round(beam_self_weight_kn_m, 2),
            "q_dead_service_kn_m": round(q_dead_service_kn_m, 2),
            "q_live_service_kn_m": round(q_live_service_kn_m, 2),
            "q_total_service_kn_m": round(q_total_service_kn_m, 2),
            "q_factored_elu_kn_m": round(q_factored_elu_kn_m, 2)
        }
