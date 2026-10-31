"""
Direct Stiffness Method (DSM) Frame Matrix Solver & Voronoi Tributary Load Engine.
Provides rigorous 1st-order linear elastic matrix structural analysis
for 2D portal and continuous architectural concrete/steel frames.
"""
import math
from typing import Dict, Any, List, Tuple
import numpy as np


class DSMSolver:
    """
    Direct Stiffness Method (DSM) 2D Frame Solver.
    Computes nodal displacements, joint rotations, member end forces,
    and beam midspan deflections under serviceability and ultimate loads.
    """

    @classmethod
    def solve_portal_frame(
        cls,
        span_length_m: float = 10.0,
        cantilever_length_m: float = 0.0,
        beam_height_cm: float = 30.0,
        beam_width_cm: float = 20.0,
        column_height_m: float = 3.2,
        column_section_cm: float = 20.0,
        elastic_modulus_gpa: float = 30.0,
        distributed_load_kn_m: float = 25.0,
        lateral_wind_kn: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Solves 2D Frame: 2 base supports (fixed), 2 top beam-column joints,
        optional cantilever tip node.

        Node Layout:
        Node 0: Base Column 1 (0.0, 0.0) - Fixed
        Node 1: Top Column 1 / Beam Left (0.0, col_h) - Free (u1, v1, theta1)
        Node 2: Top Column 2 / Beam Right (span, col_h) - Free (u2, v2, theta2)
        Node 3: Base Column 2 (span, 0.0) - Fixed
        Node 4 (Optional): Cantilever Tip (span + cantilever, col_h)
        """
        l_span = max(float(span_length_m or 1.0), 0.5)
        l_cant = max(float(cantilever_length_m or 0.0), 0.0)
        col_h = max(float(column_height_m or 3.0), 1.0)
        e_kpa = max(float(elastic_modulus_gpa or 25.0), 10.0) * 1e6  # kN/m2

        # Beam properties
        bw = max(float(beam_width_cm or 20.0) / 100.0, 0.12)
        bh = max(float(beam_height_cm or 30.0) / 100.0, 0.15)
        a_beam = bw * bh
        # NBR 6118 cracked effective inertia
        i_beam = 0.50 * (bw * (bh ** 3)) / 12.0
        ei_beam = e_kpa * i_beam
        ea_beam = e_kpa * a_beam

        # Column properties
        cw = max(float(column_section_cm or 20.0) / 100.0, 0.14)
        a_col = cw * cw
        i_col = 0.50 * (cw * (cw ** 3)) / 12.0
        ei_col = e_kpa * i_col
        ea_col = e_kpa * a_col

        q = float(distributed_load_kn_m)

        # DOFs:
        # Node 1 (Joint 1): DOF 0 (u1), DOF 1 (v1), DOF 2 (theta1)
        # Node 2 (Joint 2): DOF 3 (u2), DOF 4 (v2), DOF 5 (theta2)
        # If cantilever present: Node 4: DOF 6 (u4), DOF 7 (v4), DOF 8 (theta4)
        has_cant = l_cant > 0.05
        num_dofs = 9 if has_cant else 6
        k_global = np.zeros((num_dofs, num_dofs), dtype=float)
        f_global = np.zeros(num_dofs, dtype=float)

        # --- Element 1: Column 1 (Node 0 [fixed] to Node 1 [free]) ---
        # Vertical member from y=0 to y=col_h.
        # At top node (Node 1):
        # Axial stiffness along y: k_v = EA/col_h
        # Lateral stiffness along x: k_u = 12*EI / col_h^3
        # Rotational stiffness: k_theta = 4*EI / col_h
        # Coupling u - theta: -6*EI / col_h^2
        k_global[0, 0] += 12.0 * ei_col / (col_h ** 3)
        k_global[0, 2] += -6.0 * ei_col / (col_h ** 2)
        k_global[2, 0] += -6.0 * ei_col / (col_h ** 2)
        k_global[1, 1] += ea_col / col_h
        k_global[2, 2] += 4.0 * ei_col / col_h

        # Lateral wind load at top of column 1
        if lateral_wind_kn != 0.0:
            f_global[0] += lateral_wind_kn

        # --- Element 2: Column 2 (Node 3 [fixed] to Node 2 [free]) ---
        # Vertical member at x=l_span, y=0 to y=col_h.
        # At top node (Node 2, DOFs 3, 4, 5):
        k_global[3, 3] += 12.0 * ei_col / (col_h ** 3)
        k_global[3, 5] += -6.0 * ei_col / (col_h ** 2)
        k_global[5, 3] += -6.0 * ei_col / (col_h ** 2)
        k_global[4, 4] += ea_col / col_h
        k_global[5, 5] += 4.0 * ei_col / col_h

        # --- Element 3: Main Beam (Node 1 [DOFs 0,1,2] to Node 2 [DOFs 3,4,5]) ---
        # Horizontal member from x=0 to x=l_span.
        # Axial along x: EA / l_span
        k_beam_axial = ea_beam / l_span
        k_global[0, 0] += k_beam_axial
        k_global[0, 3] += -k_beam_axial
        k_global[3, 0] += -k_beam_axial
        k_global[3, 3] += k_beam_axial

        # Bending along y and theta:
        k11 = 12.0 * ei_beam / (l_span ** 3)
        k12 = 6.0 * ei_beam / (l_span ** 2)
        k22 = 4.0 * ei_beam / l_span
        k23 = 2.0 * ei_beam / l_span

        # Node 1 DOFs (1: v1, 2: theta1)
        k_global[1, 1] += k11
        k_global[1, 2] += k12
        k_global[2, 1] += k12
        k_global[2, 2] += k22

        # Node 2 DOFs (4: v2, 5: theta2)
        k_global[4, 4] += k11
        k_global[4, 5] += -k12
        k_global[5, 4] += -k12
        k_global[5, 5] += k22

        # Cross coupling Node 1 <-> Node 2
        k_global[1, 4] += -k11
        k_global[1, 5] += k12
        k_global[4, 1] += -k11
        k_global[5, 1] += k12

        k_global[2, 4] += -k12
        k_global[2, 5] += k23
        k_global[4, 2] += -k12
        k_global[5, 2] += k23

        # Equivalent nodal load vector for uniform load q on main span (gravity downwards, y negative):
        # Transverse loads: -q * l_span / 2 on DOFs 1 and 4
        # Fixed-end moments: Node 1: -q * l_span^2 / 12, Node 2: +q * l_span^2 / 12
        f_global[1] += -q * l_span / 2.0
        f_global[2] += -q * (l_span ** 2) / 12.0
        f_global[4] += -q * l_span / 2.0
        f_global[5] += q * (l_span ** 2) / 12.0

        # --- Element 4: Cantilever Beam (Node 2 to Node 4) if present ---
        if has_cant:
            lc = l_cant
            k_c_axial = ea_beam / lc
            # Axial DOFs 3 and 6
            k_global[3, 3] += k_c_axial
            k_global[3, 6] += -k_c_axial
            k_global[6, 3] += -k_c_axial
            k_global[6, 6] += k_c_axial

            kc11 = 12.0 * ei_beam / (lc ** 3)
            kc12 = 6.0 * ei_beam / (lc ** 2)
            kc22 = 4.0 * ei_beam / lc
            kc23 = 2.0 * ei_beam / lc

            # Node 2 (DOFs 4, 5)
            k_global[4, 4] += kc11
            k_global[4, 5] += kc12
            k_global[5, 4] += kc12
            k_global[5, 5] += kc22

            # Node 4 (DOFs 7, 8)
            k_global[7, 7] += kc11
            k_global[7, 8] += -kc12
            k_global[8, 7] += -kc12
            k_global[8, 8] += kc22

            # Coupling
            k_global[4, 7] += -kc11
            k_global[4, 8] += kc12
            k_global[7, 4] += -kc11
            k_global[8, 4] += kc12

            k_global[5, 7] += -kc12
            k_global[5, 8] += kc23
            k_global[7, 5] += -kc12
            k_global[8, 5] += kc23

            # Loads on cantilever
            f_global[4] += -q * lc / 2.0
            f_global[5] += -q * (lc ** 2) / 12.0
            f_global[7] += -q * lc / 2.0
            f_global[8] += q * (lc ** 2) / 12.0

        # Solve system: K * U = F
        try:
            u_disp = np.linalg.solve(k_global, f_global)
        except np.linalg.LinAlgError:
            u_disp = np.linalg.lstsq(k_global, f_global, rcond=None)[0]

        # Extract primary displacements
        u1, v1, th1 = u_disp[0], u_disp[1], u_disp[2]
        u2, v2, th2 = u_disp[3], u_disp[4], u_disp[5]
        v_cant = u_disp[7] if has_cant else 0.0

        # Fixed-end midspan deflection for uniform load q:
        # delta_fixed = q * L^4 / (384 * EI)
        delta_fixed = (q * (l_span ** 4)) / (384.0 * ei_beam)
        # Combined midspan deflection taking joint rotations and vertical settlements into account:
        v_supports = (v1 + v2) / 2.0
        v_rotation_effect = ((th1 - th2) * l_span) / 8.0
        total_midspan_deflection_m = delta_fixed - v_supports - v_rotation_effect
        total_midspan_deflection_mm = round(abs(total_midspan_deflection_m) * 1000.0, 2)

        # Cantilever tip deflection
        cantilever_deflection_mm = round(abs(v_cant) * 1000.0, 2) if has_cant else 0.0

        # Internal moments via slope-deflection
        # M_12 = 2EI/L * (2*th1 + th2 - 3*(v2-v1)/L) - q*L^2/12
        # M_21 = 2EI/L * (th1 + 2*th2 - 3*(v2-v1)/L) + q*L^2/12
        delta_v = v2 - v1
        m_node1_knm = round(
            float((2.0 * ei_beam / l_span) * (2.0 * th1 + th2 - 3.0 * delta_v / l_span) - (q * (l_span ** 2)) / 12.0),
            2
        )
        m_node2_knm = round(
            float((2.0 * ei_beam / l_span) * (th1 + 2.0 * th2 - 3.0 * delta_v / l_span) + (q * (l_span ** 2)) / 12.0),
            2
        )
        # Maximum positive midspan moment M_pos ~= q*L^2/8 - (M1 + M2)/2
        m_midspan_knm = round(
            float((q * (l_span ** 2) / 8.0) - abs(m_node1_knm + m_node2_knm) / 2.0),
            2
        )

        return {
            "solver": "Direct Stiffness Method (DSM) 2D Plane Frame",
            "degrees_of_freedom": int(num_dofs),
            "displacements": {
                "joint1_u_mm": round(float(u1 * 1000.0), 3),
                "joint1_v_mm": round(float(v1 * 1000.0), 3),
                "joint1_rotation_rad": round(float(th1), 5),
                "joint2_u_mm": round(float(u2 * 1000.0), 3),
                "joint2_v_mm": round(float(v2 * 1000.0), 3),
                "joint2_rotation_rad": round(float(th2), 5),
                "cantilever_tip_deflection_mm": cantilever_deflection_mm,
            },
            "exact_midspan_deflection_mm": total_midspan_deflection_mm,
            "internal_moments_knm": {
                "support_left_m1": abs(m_node1_knm),
                "midspan_positive_m": max(m_midspan_knm, 1.0),
                "support_right_m2": abs(m_node2_knm),
            },
            "reactions_kn": {
                "column1_vertical_reaction_kn": round(abs(float(ea_col / col_h * v1)), 1),
                "column2_vertical_reaction_kn": round(abs(float(ea_col / col_h * v2)), 1),
                "column1_shear_reaction_kn": round(abs(float(12.0 * ei_col / (col_h ** 3) * u1)), 1),
            },
        }

    @classmethod
    def calculate_voronoi_tributary(
        cls,
        bay_x_m: float = 10.0,
        bay_y_m: float = 6.0,
        slab_surface_load_kpa: float = 6.5,
    ) -> Dict[str, Any]:
        """
        Calculates Tributary Areas based on 45-degree plastic yield line (charnière plástica)
        and Voronoi partitioning for two-way and one-way slabs per NBR 6118.
        """
        safe_x = max(float(bay_x_m or 1.0), 0.5)
        safe_y = max(float(bay_y_m or 1.0), 0.5)
        slab_surface_load_kpa = max(float(slab_surface_load_kpa or 1.0), 0.5)
        lx = min(safe_x, safe_y)  # menor vão
        ly = max(safe_x, safe_y)  # maior vão
        ratio = ly / lx

        # Se ly / lx > 2.0 -> Laje armada em uma direção (carrega apenas vigas longas)
        if ratio >= 2.0:
            area_long_beam_m2 = (lx / 2.0) * ly
            area_short_beam_m2 = 0.0
            q_eq_long_kn_m = (slab_surface_load_kpa * lx) / 2.0
            q_eq_short_kn_m = 0.0
            behavior = "Laje Armada em Uma Direção (Unidirecional)"
        else:
            # Laje armada em duas direções (Charneiras a 45 graus: 2 triângulos e 2 trapézios)
            # Área dos triângulos (vigas no vão menor lx):
            area_short_beam_m2 = (lx * (lx / 2.0)) / 2.0
            # Área dos trapézios (vigas no vão maior ly):
            area_long_beam_m2 = (lx / 2.0) * (ly - lx / 2.0)
            # Cargas distribuídas equivalentes retangulares (q_eq):
            # Trapézio: q_eq = q * (lx / 2) * (1 - 2/3 * (lx / (2*ly))^2)
            alpha_trap = 1.0 - (2.0 / 3.0) * ((lx / (2.0 * ly)) ** 2)
            q_eq_long_kn_m = slab_surface_load_kpa * (lx / 2.0) * alpha_trap
            # Triângulo: q_eq = q * lx / 3
            q_eq_short_kn_m = slab_surface_load_kpa * (lx / 3.0)
            behavior = "Laje Armada em Duas Direções (Bidirecional / Charneiras Plásticas 45°)"

        return {
            "bay_geometry": {"lx_m": lx, "ly_m": ly, "aspect_ratio": round(ratio, 2)},
            "behavior": behavior,
            "tributary_areas_m2": {
                "trapezoidal_long_beam_m2": round(area_long_beam_m2, 2),
                "triangular_short_beam_m2": round(area_short_beam_m2, 2),
                "total_bay_area_m2": round(lx * ly, 2),
            },
            "equivalent_uniform_loads_kn_m": {
                "long_beam_load_kn_m": round(q_eq_long_kn_m, 2),
                "short_beam_load_kn_m": round(q_eq_short_kn_m, 2),
            },
        }
