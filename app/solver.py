import math
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from app.models import (
    BeamAnalysisRequest,
    BeamAnalysisResponse,
    ReactionForce,
    EquilibriumSummary,
    CriticalPoint,
    DiagramData,
    SupportType,
    LoadType
)

def solve_beam(req: BeamAnalysisRequest) -> BeamAnalysisResponse:
    L = float(req.beam.length)
    E = float(req.beam.elastic_modulus) * 1.0e9  # GPa -> Pa (N/m^2)
    I = float(req.beam.moment_of_inertia) * 1.0e-6  # 10^6 mm^4 -> m^4
    EI = E * I

    # Basic validations
    if L <= 0:
        raise ValueError("Beam length must be greater than zero.")
    if len(req.supports) == 0:
        raise ValueError("At least one support is required.")

    for s in req.supports:
        if s.position < -1e-6 or s.position > L + 1e-6:
            raise ValueError(f"Support position {s.position}m is outside beam bounds [0, {L}m].")

    for load in req.loads:
        if load.type in [LoadType.POINT, LoadType.MOMENT]:
            if load.position is None or load.position < -1e-6 or load.position > L + 1e-6:
                raise ValueError(f"{load.type} load position must be within [0, {L}m].")
        elif load.type in [LoadType.UDL, LoadType.UVL]:
            if load.start_pos is None or load.end_pos is None:
                raise ValueError(f"{load.type} load requires start_pos and end_pos.")
            if load.start_pos < -1e-6 or load.end_pos > L + 1e-6 or load.start_pos >= load.end_pos:
                raise ValueError(f"Invalid range [{load.start_pos}, {load.end_pos}] for {load.type} load on beam length {L}m.")

    # Collect all key positions
    key_points = {0.0, L}
    for s in req.supports:
        key_points.add(round(float(s.position), 6))

    for load in req.loads:
        if load.type in [LoadType.POINT, LoadType.MOMENT] and load.position is not None:
            key_points.add(round(float(load.position), 6))
        elif load.type in [LoadType.UDL, LoadType.UVL]:
            key_points.add(round(float(load.start_pos), 6))
            key_points.add(round(float(load.end_pos), 6))

    sorted_key_points = sorted(list(key_points))

    # Discretize segments so that maximum element length is at most L / 300
    target_dl = L / 300.0
    nodes_list: List[float] = []

    for i in range(len(sorted_key_points) - 1):
        x_start = sorted_key_points[i]
        x_end = sorted_key_points[i + 1]
        seg_len = x_end - x_start
        if seg_len <= 1e-7:
            continue
        num_sub = max(1, int(math.ceil(seg_len / target_dl)))
        for k in range(num_sub):
            nodes_list.append(x_start + k * (seg_len / num_sub))
    nodes_list.append(L)

    # Ensure strictly sorted unique nodes
    nodes = np.unique(np.array(nodes_list, dtype=float))
    num_nodes = len(nodes)
    num_elements = num_nodes - 1
    num_dofs = 2 * num_nodes

    # Global stiffness matrix and load vector
    K = np.zeros((num_dofs, num_dofs), dtype=float)
    F = np.zeros(num_dofs, dtype=float)

    # Helper to find nearest node index
    def find_node(x_val: float) -> int:
        return int(np.argmin(np.abs(nodes - x_val)))

    # Assemble element stiffness matrices
    for e in range(num_elements):
        x1 = nodes[e]
        x2 = nodes[e + 1]
        he = x2 - x1
        if he <= 1e-9:
            continue

        he2 = he * he
        he3 = he2 * he

        c = EI / he3
        ke = c * np.array([
            [12.0,       6.0 * he,  -12.0,      6.0 * he],
            [6.0 * he,   4.0 * he2,  -6.0 * he,  2.0 * he2],
            [-12.0,     -6.0 * he,   12.0,     -6.0 * he],
            [6.0 * he,   2.0 * he2,  -6.0 * he,  4.0 * he2]
        ], dtype=float)

        dofs = [2 * e, 2 * e + 1, 2 * (e + 1), 2 * (e + 1) + 1]
        for r in range(4):
            for col in range(4):
                K[dofs[r], dofs[col]] += ke[r, col]

    # Apply distributed loads (UDL & UVL) to nodal force vector
    for load in req.loads:
        if load.type in [LoadType.UDL, LoadType.UVL]:
            x_start = float(load.start_pos)
            x_end = float(load.end_pos)
            w_start = float(load.start_magnitude or load.magnitude or 0.0) * 1000.0  # kN/m -> N/m (downward)
            w_end = float(load.end_magnitude if load.end_magnitude is not None else w_start) * 1000.0

            # Sign convention: downward load is in -y direction
            q_start = -w_start
            q_end = -w_end
            load_span = x_end - x_start

            for e in range(num_elements):
                elem_x1 = nodes[e]
                elem_x2 = nodes[e + 1]
                elem_len = elem_x2 - elem_x1

                # Check overlap
                overlap_start = max(elem_x1, x_start)
                overlap_end = min(elem_x2, x_end)

                if overlap_end - overlap_start > 1e-7:
                    # Linearly interpolate load intensities at element nodes
                    t1 = (elem_x1 - x_start) / load_span if load_span > 1e-9 else 0.0
                    t2 = (elem_x2 - x_start) / load_span if load_span > 1e-9 else 0.0
                    t1 = np.clip(t1, 0.0, 1.0)
                    t2 = np.clip(t2, 0.0, 1.0)

                    qe1 = q_start + t1 * (q_end - q_start)
                    qe2 = q_start + t2 * (q_end - q_start)

                    # Work-equivalent load vector for linear load
                    he = elem_len
                    f1 = he * (7.0 * qe1 + 3.0 * qe2) / 20.0
                    m1 = (he ** 2) * (qe1 / 20.0 + qe2 / 30.0)
                    f2 = he * (3.0 * qe1 + 7.0 * qe2) / 20.0
                    m2 = -(he ** 2) * (qe1 / 30.0 + qe2 / 20.0)

                    dofs = [2 * e, 2 * e + 1, 2 * (e + 1), 2 * (e + 1) + 1]
                    F[dofs[0]] += f1
                    F[dofs[1]] += m1
                    F[dofs[2]] += f2
                    F[dofs[3]] += m2

        elif load.type == LoadType.POINT:
            xp = float(load.position)
            idx = find_node(xp)
            # Downward point load is in -y direction
            p_val = float(load.magnitude or 0.0) * 1000.0  # kN -> N
            F[2 * idx] += -p_val

        elif load.type == LoadType.MOMENT:
            xm = float(load.position)
            idx = find_node(xm)
            # Counter-clockwise moment is positive rotation
            m_val = float(load.magnitude or 0.0) * 1000.0  # kN*m -> N*m
            F[2 * idx + 1] += m_val

    # Boundary conditions
    prescribed_dofs: Dict[int, float] = {}
    support_node_map: List[Tuple[int, SupportType, float, str]] = []

    for i, s in enumerate(req.supports):
        sup_id = s.id or f"S{i+1}"
        pos = float(s.position)
        node_idx = find_node(pos)

        if s.type in [SupportType.PIN, SupportType.ROLLER]:
            prescribed_dofs[2 * node_idx] = 0.0  # Restrain vertical displacement
            support_node_map.append((node_idx, s.type, pos, sup_id))
        elif s.type == SupportType.FIXED:
            prescribed_dofs[2 * node_idx] = 0.0      # Restrain vertical displacement
            prescribed_dofs[2 * node_idx + 1] = 0.0  # Restrain rotation
            support_node_map.append((node_idx, s.type, pos, sup_id))

    # Stability verification
    if len(prescribed_dofs) < 2 and not any(s.type == SupportType.FIXED for s in req.supports):
        raise ValueError("Structure is unstable (under-constrained). Provide at least two vertical restraints or one fixed support.")

    # Solve system: K_free * u_free = F_free
    all_dofs = np.arange(num_dofs)
    prescribed_dofs_indices = np.array(sorted(list(prescribed_dofs.keys())), dtype=int)
    free_dofs = np.setdiff1d(all_dofs, prescribed_dofs_indices)

    K_free = K[np.ix_(free_dofs, free_dofs)]
    F_free = F[free_dofs]

    # Check singularity
    cond = np.linalg.cond(K_free)
    if cond > 1e16 or np.isnan(cond):
        raise ValueError("Structure is mathematically singular or unstable. Please verify support layout.")

    u_free = np.linalg.solve(K_free, F_free)

    # Full displacement vector
    u_full = np.zeros(num_dofs, dtype=float)
    u_full[free_dofs] = u_free
    for dof, val in prescribed_dofs.items():
        u_full[dof] = val

    # Reactions calculation: R = K * u - F
    reactions_raw = K @ u_full - F

    # Group reactions by support
    reactions_list: List[ReactionForce] = []
    seen_supports = set()
    for node_idx, s_type, pos, sup_id in support_node_map:
        if (node_idx, sup_id) in seen_supports:
            continue
        seen_supports.add((node_idx, sup_id))
        vert_reac_N = reactions_raw[2 * node_idx]
        moment_reac_Nm = reactions_raw[2 * node_idx + 1] if s_type == SupportType.FIXED else 0.0

        reactions_list.append(ReactionForce(
            support_id=sup_id,
            support_type=s_type.value,
            position=round(pos, 4),
            vertical_force_kN=round(vert_reac_N / 1000.0, 4),
            moment_kNm=round(moment_reac_Nm / 1000.0, 4)
        ))

    # Global equilibrium check
    sum_reaction_vert = sum(r.vertical_force_kN for r in reactions_list)
    sum_reaction_moment = sum(r.moment_kNm + r.vertical_force_kN * r.position for r in reactions_list)

    total_applied_vert = 0.0
    total_applied_moment = 0.0
    for load in req.loads:
        if load.type == LoadType.POINT:
            p_val = float(load.magnitude or 0.0)
            xp = float(load.position or 0.0)
            total_applied_vert += p_val
            total_applied_moment += p_val * xp
        elif load.type in [LoadType.UDL, LoadType.UVL]:
            x1 = float(load.start_pos or 0.0)
            x2 = float(load.end_pos or 0.0)
            w1 = float(load.start_magnitude or load.magnitude or 0.0)
            w2 = float(load.end_magnitude if load.end_magnitude is not None else w1)
            span = x2 - x1
            total_w = 0.5 * (w1 + w2) * span
            # Centroid of trapezoid from x1
            if abs(w1 + w2) > 1e-9:
                x_cent = x1 + (span / 3.0) * ((w1 + 2.0 * w2) / (w1 + w2))
            else:
                x_cent = 0.5 * (x1 + x2)
            total_applied_vert += total_w
            total_applied_moment += total_w * x_cent
        elif load.type == LoadType.MOMENT:
            m_val = float(load.magnitude or 0.0)
            # Counter-clockwise moment contributes negatively to clockwise sum
            total_applied_moment -= m_val

    vert_error = abs(sum_reaction_vert - total_applied_vert)
    moment_error = abs(sum_reaction_moment - total_applied_moment)
    is_equilibrated = (vert_error < 0.05) and (moment_error < 0.1)

    equilibrium = EquilibriumSummary(
        sum_applied_vertical_kN=round(total_applied_vert, 4),
        sum_reaction_vertical_kN=round(sum_reaction_vert, 4),
        vertical_balance_error_kN=round(vert_error, 5),
        sum_applied_moment_kNm=round(total_applied_moment, 4),
        sum_reaction_moment_kNm=round(sum_reaction_moment, 4),
        moment_balance_error_kNm=round(moment_error, 5),
        is_equilibrated=is_equilibrated
    )

    # Evaluate continuous internal forces & deformations
    # To handle step changes at concentrated loads/reactions accurately,
    # we generate a fine uniform grid of sample points plus points just before and after discontinuities
    eval_x_set = set()
    for x_val in np.linspace(0.0, L, 350):
        eval_x_set.add(round(float(x_val), 5))

    eps = 1e-5
    for kp in key_points:
        if kp > eps:
            eval_x_set.add(round(kp - eps, 5))
        eval_x_set.add(round(kp, 5))
        if kp < L - eps:
            eval_x_set.add(round(kp + eps, 5))

    sorted_eval_x = np.array(sorted(list(eval_x_set)))

    shear_force_list: List[float] = []
    bending_moment_list: List[float] = []
    slope_list: List[float] = []
    deflection_list: List[float] = []

    # Prepare active forces for sectional calculation (Method of Sections)
    # Upward forces: reactions
    # Downward forces: point loads, distributed loads
    for x in sorted_eval_x:
        # Internal shear force V(x): sum of vertical forces to the left of x
        # Sign convention: upward force to the left produces positive shear
        # Downward force to the left produces negative shear
        v_val_kN = 0.0
        m_val_kNm = 0.0

        # Reactions contribution
        for r in reactions_list:
            if r.position < x or abs(r.position - x) < 1e-7:
                # Vertical reaction force
                v_val_kN += r.vertical_force_kN
                m_val_kNm += r.vertical_force_kN * (x - r.position)
                # Counter-clockwise reaction moment on left portion creates hogging (negative moment)
                m_val_kNm -= r.moment_kNm

        # Point loads
        for load in req.loads:
            if load.type == LoadType.POINT:
                xp = float(load.position)
                if xp < x or abs(xp - x) < 1e-7:
                    p_mag = float(load.magnitude or 0.0)
                    v_val_kN -= p_mag
                    m_val_kNm -= p_mag * (x - xp)
            elif load.type == LoadType.MOMENT:
                xm = float(load.position)
                if xm < x or abs(xm - x) < 1e-7:
                    m_mag = float(load.magnitude or 0.0)
                    # Counter-clockwise applied moment to the left creates hogging (negative moment)
                    m_val_kNm -= m_mag
            elif load.type in [LoadType.UDL, LoadType.UVL]:
                x1 = float(load.start_pos)
                x2 = float(load.end_pos)
                if x > x1:
                    w1 = float(load.start_magnitude or load.magnitude or 0.0)
                    w2 = float(load.end_magnitude if load.end_magnitude is not None else w1)
                    x_eff_end = min(x, x2)
                    dx = x_eff_end - x1

                    if abs(w2 - w1) < 1e-7:
                        # Pure UDL
                        load_res = w1 * dx
                        arm = x - (x1 + 0.5 * dx)
                        v_val_kN -= load_res
                        m_val_kNm -= load_res * arm
                    else:
                        # Linear UVL
                        total_span = x2 - x1
                        w_at_eff = w1 + (w2 - w1) * (dx / total_span)
                        load_res = 0.5 * (w1 + w_at_eff) * dx
                        if abs(w1 + w_at_eff) > 1e-9:
                            cent_from_x1 = (dx / 3.0) * ((w1 + 2.0 * w_at_eff) / (w1 + w_at_eff))
                        else:
                            cent_from_x1 = 0.5 * dx
                        arm = x - (x1 + cent_from_x1)
                        v_val_kN -= load_res
                        m_val_kNm -= load_res * arm

        shear_force_list.append(round(v_val_kN, 3))
        bending_moment_list.append(round(m_val_kNm, 3))

        # Deflection and slope from Hermite element interpolation
        # Locate containing element
        elem_idx = int(np.searchsorted(nodes, x)) - 1
        elem_idx = max(0, min(elem_idx, num_elements - 1))

        x_e1 = nodes[elem_idx]
        x_e2 = nodes[elem_idx + 1]
        he = x_e2 - x_e1
        xi = (x - x_e1) / he if he > 1e-9 else 0.0
        xi = max(0.0, min(1.0, xi))

        v1 = u_full[2 * elem_idx]
        th1 = u_full[2 * elem_idx + 1]
        v2 = u_full[2 * (elem_idx + 1)]
        th2 = u_full[2 * (elem_idx + 1) + 1]

        # Hermite shape functions
        H1 = 1.0 - 3.0 * xi**2 + 2.0 * xi**3
        H2 = he * (xi - 2.0 * xi**2 + xi**3)
        H3 = 3.0 * xi**2 - 2.0 * xi**3
        H4 = he * (-xi**2 + xi**3)

        v_interp = H1 * v1 + H2 * th1 + H3 * v2 + H4 * th2

        # Derivative shape functions for slope
        dH1 = (-6.0 * xi + 6.0 * xi**2) / he
        dH2 = 1.0 - 4.0 * xi + 3.0 * xi**2
        dH3 = (6.0 * xi - 6.0 * xi**2) / he
        dH4 = -2.0 * xi + 3.0 * xi**2

        th_interp = dH1 * v1 + dH2 * th1 + dH3 * v2 + dH4 * th2

        # Convert deflection to mm (negative y is downward deflection)
        # In engineering, deflection is commonly reported as downward displacement = -v
        # Let's keep deflection in mm with true Cartesian sign (negative = downwards)
        deflection_list.append(round(v_interp * 1000.0, 4))
        slope_list.append(round(th_interp * 1000.0, 4))  # mrad

    # Extract extrema and critical points
    v_arr = np.array(shear_force_list)
    m_arr = np.array(bending_moment_list)
    d_arr = np.array(deflection_list)

    max_v = float(np.max(v_arr))
    min_v = float(np.min(v_arr))
    max_m = float(np.max(m_arr))
    min_m = float(np.min(m_arr))

    # Absolute max deflection
    abs_d_arr = np.abs(d_arr)
    max_d_idx = int(np.argmax(abs_d_arr))
    max_deflection_mm = float(d_arr[max_d_idx])
    max_deflection_x = float(sorted_eval_x[max_d_idx])

    critical_points: List[CriticalPoint] = []

    # Max deflection point
    critical_points.append(CriticalPoint(
        type="max_deflection",
        position=round(max_deflection_x, 3),
        value=round(abs(max_deflection_mm), 3),
        unit="mm",
        description=f"Maximum deflection of {abs(max_deflection_mm):.3f} mm occurs at x = {max_deflection_x:.3f} m"
    ))

    # Max positive moment (sagging)
    max_m_idx = int(np.argmax(m_arr))
    if max_m > 0.01:
        critical_points.append(CriticalPoint(
            type="max_positive_moment",
            position=round(float(sorted_eval_x[max_m_idx]), 3),
            value=round(max_m, 3),
            unit="kN*m",
            description=f"Peak sagging moment of {max_m:.3f} kN*m at x = {sorted_eval_x[max_m_idx]:.3f} m"
        ))

    # Max negative moment (hogging)
    min_m_idx = int(np.argmin(m_arr))
    if min_m < -0.01:
        critical_points.append(CriticalPoint(
            type="max_negative_moment",
            position=round(float(sorted_eval_x[min_m_idx]), 3),
            value=round(min_m, 3),
            unit="kN*m",
            description=f"Peak hogging moment of {min_m:.3f} kN*m at x = {sorted_eval_x[min_m_idx]:.3f} m"
        ))

    # Points of zero shear (potential local moment extrema)
    for i in range(len(sorted_eval_x) - 1):
        if (v_arr[i] > 0 and v_arr[i+1] < 0) or (v_arr[i] < 0 and v_arr[i+1] > 0):
            # Zero crossing
            x_zero = sorted_eval_x[i] + (0.0 - v_arr[i]) * (sorted_eval_x[i+1] - sorted_eval_x[i]) / (v_arr[i+1] - v_arr[i])
            m_zero = bending_moment_list[i]
            critical_points.append(CriticalPoint(
                type="zero_shear",
                position=round(float(x_zero), 3),
                value=round(float(m_zero), 3),
                unit="kN*m",
                description=f"Zero shear at x = {x_zero:.3f} m (Bending Moment = {m_zero:.3f} kN*m)"
            ))

    # Points of contraflexure (where moment changes sign)
    for i in range(len(sorted_eval_x) - 1):
        if (m_arr[i] > 0.05 and m_arr[i+1] < -0.05) or (m_arr[i] < -0.05 and m_arr[i+1] > 0.05):
            x_contra = sorted_eval_x[i] + (0.0 - m_arr[i]) * (sorted_eval_x[i+1] - sorted_eval_x[i]) / (m_arr[i+1] - m_arr[i])
            critical_points.append(CriticalPoint(
                type="point_of_contraflexure",
                position=round(float(x_contra), 3),
                value=0.0,
                unit="kN*m",
                description=f"Point of contraflexure (M = 0) at x = {x_contra:.3f} m"
            ))

    # Formulate summary text
    reac_str = ", ".join([
        f"{r.support_id} ({r.support_type.capitalize()} @ {r.position}m): Ry = {r.vertical_force_kN} kN" +
        (f", M = {r.moment_kNm} kN*m" if abs(r.moment_kNm) > 0.001 else "")
        for r in reactions_list
    ])
    summary_text = (
        f"Beam Length: {L} m | Material E: {req.beam.elastic_modulus} GPa | Moment of Inertia I: {req.beam.moment_of_inertia} x 10^6 mm^4\n"
        f"Support Reactions: {reac_str}\n"
        f"Equilibrium: Vertical Error = {vert_error:.4f} kN, Moment Error = {moment_error:.4f} kN*m (Status: {'PASSED' if is_equilibrated else 'CHECK'})\n"
        f"Maximum Deflection: {abs(max_deflection_mm):.3f} mm at x = {max_deflection_x:.3f} m\n"
        f"Shear Range: [{min_v:.2f} kN, {max_v:.2f} kN] | Moment Range: [{min_m:.2f} kN*m, {max_m:.2f} kN*m]"
    )

    return BeamAnalysisResponse(
        success=True,
        error=None,
        beam_length=round(L, 3),
        reactions=reactions_list,
        equilibrium=equilibrium,
        max_deflection_mm=round(max_deflection_mm, 4),
        max_deflection_x=round(max_deflection_x, 3),
        max_shear_kN=round(max_v, 3),
        min_shear_kN=round(min_v, 3),
        max_moment_kNm=round(max_m, 3),
        min_moment_kNm=round(min_m, 3),
        critical_points=critical_points,
        diagrams=DiagramData(
            x=[round(float(xv), 4) for xv in sorted_eval_x],
            shear_force=shear_force_list,
            bending_moment=bending_moment_list,
            slope=slope_list,
            deflection=deflection_list
        ),
        summary_text=summary_text
    )
