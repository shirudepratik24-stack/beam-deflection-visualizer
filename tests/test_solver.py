import pytest
import math
from fastapi.testclient import TestClient
from main import app
from app.solver import solve_beam
from app.models import BeamAnalysisRequest, BeamParameters, Support, Load, SupportType, LoadType

client = TestClient(app)

def test_simply_supported_center_load():
    L = 6.0
    P = 20.0  # kN
    E_gpa = 200.0
    I_1e6 = 83.3

    req = BeamAnalysisRequest(
        beam=BeamParameters(length=L, elastic_modulus=E_gpa, moment_of_inertia=I_1e6),
        supports=[
            Support(id="A", type=SupportType.PIN, position=0.0),
            Support(id="B", type=SupportType.ROLLER, position=L)
        ],
        loads=[
            Load(type=LoadType.POINT, magnitude=P, position=L / 2.0)
        ]
    )

    res = solve_beam(req)
    assert res.success is True
    assert res.equilibrium.is_equilibrated is True

    # Reactions should be P / 2 = 10 kN each
    assert math.isclose(res.reactions[0].vertical_force_kN, 10.0, abs_tol=0.05)
    assert math.isclose(res.reactions[1].vertical_force_kN, 10.0, abs_tol=0.05)

    # Max moment should be P * L / 4 = 20 * 6 / 4 = 30 kN*m
    assert math.isclose(res.max_moment_kNm, 30.0, abs_tol=0.2)

    # Theoretical deflection: delta = P * L^3 / (48 * E * I)
    E_si = E_gpa * 1e9
    I_si = I_1e6 * 1e-6
    theoretical_deflection_mm = (P * 1000.0 * (L ** 3) / (48.0 * E_si * I_si)) * 1000.0
    assert math.isclose(abs(res.max_deflection_mm), theoretical_deflection_mm, rel_tol=0.02)
    assert math.isclose(res.max_deflection_x, 3.0, abs_tol=0.05)

def test_cantilever_end_load():
    L = 4.0
    P = 15.0  # kN
    E_gpa = 200.0
    I_1e6 = 65.0

    req = BeamAnalysisRequest(
        beam=BeamParameters(length=L, elastic_modulus=E_gpa, moment_of_inertia=I_1e6),
        supports=[
            Support(id="Fix", type=SupportType.FIXED, position=0.0)
        ],
        loads=[
            Load(type=LoadType.POINT, magnitude=P, position=L)
        ]
    )

    res = solve_beam(req)
    assert res.success is True
    assert res.equilibrium.is_equilibrated is True

    # Reaction force should be 15 kN upwards
    assert math.isclose(res.reactions[0].vertical_force_kN, 15.0, abs_tol=0.05)

    # Max moment at root should be -60 kN*m
    assert math.isclose(res.min_moment_kNm, -60.0, abs_tol=0.1)

    # Theoretical tip deflection: P * L^3 / (3 * E * I)
    E_si = E_gpa * 1e9
    I_si = I_1e6 * 1e-6
    theoretical_deflection_mm = (P * 1000.0 * (L ** 3) / (3.0 * E_si * I_si)) * 1000.0
    assert math.isclose(abs(res.max_deflection_mm), theoretical_deflection_mm, rel_tol=0.02)
    assert math.isclose(res.max_deflection_x, 4.0, abs_tol=0.05)

def test_simply_supported_full_udl():
    L = 8.0
    w = 12.0  # kN/m
    E_gpa = 200.0
    I_1e6 = 120.0

    req = BeamAnalysisRequest(
        beam=BeamParameters(length=L, elastic_modulus=E_gpa, moment_of_inertia=I_1e6),
        supports=[
            Support(id="A", type=SupportType.PIN, position=0.0),
            Support(id="B", type=SupportType.ROLLER, position=L)
        ],
        loads=[
            Load(type=LoadType.UDL, start_pos=0.0, end_pos=L, start_magnitude=w, end_magnitude=w)
        ]
    )

    res = solve_beam(req)
    assert res.success is True
    assert res.equilibrium.is_equilibrated is True

    # Reactions should be w * L / 2 = 48 kN
    assert math.isclose(res.reactions[0].vertical_force_kN, 48.0, abs_tol=0.1)
    assert math.isclose(res.reactions[1].vertical_force_kN, 48.0, abs_tol=0.1)

    # Max moment should be w * L^2 / 8 = 12 * 64 / 8 = 96 kN*m
    assert math.isclose(res.max_moment_kNm, 96.0, abs_tol=0.3)

    # Theoretical midspan deflection: 5 * w * L^4 / (384 * E * I)
    E_si = E_gpa * 1e9
    I_si = I_1e6 * 1e-6
    theoretical_deflection_mm = (5.0 * (w * 1000.0) * (L ** 4) / (384.0 * E_si * I_si)) * 1000.0
    assert math.isclose(abs(res.max_deflection_mm), theoretical_deflection_mm, rel_tol=0.02)

def test_api_endpoints():
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "healthy"

    r_presets = client.get("/api/presets")
    assert r_presets.status_code == 200
    assert len(r_presets.json()["presets"]) >= 5

    r_materials = client.get("/api/materials")
    assert r_materials.status_code == 200
    assert "structural_steel" in r_materials.json()["materials"]

    r_sec = client.post("/api/section-calculator", json={
        "section_type": "rectangle",
        "parameters": {"width_mm": 100, "height_mm": 200}
    })
    assert r_sec.status_code == 200
    assert r_sec.json()["properties"]["moment_of_inertia_1e6_mm4"] == 66.667

def test_unstable_beam_rejection():
    req = BeamAnalysisRequest(
        beam=BeamParameters(length=5.0, elastic_modulus=200.0, moment_of_inertia=50.0),
        supports=[
            Support(id="A", type=SupportType.ROLLER, position=2.0)
        ],
        loads=[
            Load(type=LoadType.POINT, magnitude=10.0, position=3.0)
        ]
    )
    with pytest.raises(ValueError, match="unstable"):
        solve_beam(req)

def test_propped_cantilever_indeterminate():
    L = 6.0
    w = 16.0  # kN/m
    E_gpa = 200.0
    I_1e6 = 100.0

    req = BeamAnalysisRequest(
        beam=BeamParameters(length=L, elastic_modulus=E_gpa, moment_of_inertia=I_1e6),
        supports=[
            Support(id="FixedA", type=SupportType.FIXED, position=0.0),
            Support(id="RollerB", type=SupportType.ROLLER, position=L)
        ],
        loads=[
            Load(type=LoadType.UDL, start_pos=0.0, end_pos=L, start_magnitude=w, end_magnitude=w)
        ]
    )

    res = solve_beam(req)
    assert res.success is True
    assert res.equilibrium.is_equilibrated is True

    # Check reactions against textbook formulas:
    # Rb = 3/8 * w * L = 36 kN
    # Ra = 5/8 * w * L = 60 kN
    # Ma = w * L^2 / 8 = 72 kN*m (hogging = -72 kN*m)
    r_a = next(r for r in res.reactions if r.support_id == "FixedA")
    r_b = next(r for r in res.reactions if r.support_id == "RollerB")

    assert math.isclose(r_b.vertical_force_kN, 36.0, abs_tol=0.2)
    assert math.isclose(r_a.vertical_force_kN, 60.0, abs_tol=0.2)
    assert math.isclose(r_a.moment_kNm, 72.0, abs_tol=0.3)
    assert math.isclose(res.min_moment_kNm, -72.0, abs_tol=0.3)
