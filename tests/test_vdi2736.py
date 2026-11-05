import math

import numpy as np
import pytest
from pydantic import ValidationError

from gearcalc import CylindricalGear, GearPair, gear_geometry, pair_geometry
from gearcalc.rating import (
    Housing,
    Lubrication,
    Material,
    OperatingConditions,
    Polymer,
    VDI2736Input,
    loss_factor,
    rate_vdi2736,
    root_form_factors,
)
from gearcalc.rating.materials import flank_strength, friction_coefficient, root_strength

gb = pytest.importorskip("gearbox")


def _pair(
    z1: int = 12,
    z2: int = 45,
    m: float = 0.8,
    b: float = 6.0,
    beta: float = 0.0,
    x1: float = 0.4,
    x2: float = 0.1,
) -> GearPair:
    return GearPair(
        gear1=CylindricalGear(z=z1, m_n=m, b=b, beta=beta, x=x1),
        gear2=CylindricalGear(z=z2, m_n=m, b=b, beta=-beta, x=x2),
    )


def _input(
    lub: Lubrication = Lubrication.GREASE,
    m1: Polymer = Polymer.POM,
    m2: Polymer = Polymer.POM,
    **kw: object,
) -> VDI2736Input:
    op = OperatingConditions(T_1=0.15, n_1=3000.0, life_hours=500.0, theta_0=40.0)
    return VDI2736Input(
        pair=_pair(),
        material1=Material(polymer=m1),
        material2=Material(polymer=m2),
        lubrication=lub,
        operating=op,
        **kw,
    )


# --- fattori di forma -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("z", "x", "beta"), [(20, 0.0, 0.0), (17, 0.3, 0.0), (30, -0.2, 15.0), (50, 0.5, 25.0)]
)
def test_root_section_matches_python_gearbox(z: int, x: float, beta: float) -> None:
    from gearbox.standards.iso6336.bending import _tooth_root_geometry

    geo = gear_geometry(CylindricalGear(z=z, m_n=1.0, b=10.0, beta=beta, x=x))
    f = root_form_factors(geo)
    tool = gb.Tool(
        addendum_coefficient=1.0, dedendum_coefficient=1.25, root_fillet_radius_coefficient=0.38
    )
    mat = gb.Material(
        material_type=gb.MaterialType.THROUGH_HARDENED_STEEL,
        contact_stress_limit=600.0,
        bending_stress_limit=250.0,
        brinell_hardness=250.0,
    )

    def g(zz: int, xx: float):  # type: ignore[no-untyped-def]
        return gb.Gear(
            tool=tool,
            material=mat,
            number_of_teeth=zz,
            module=1.0,
            face_width=10.0,
            quality_grade=6,
            surface_roughness=1.0,
            shaft_diameter=20.0,
            shaft_arrangement=gb.ShaftArrangement.BETWEEN_BEARINGS_TOWARDS_TORQUED_END,
            bearing_span=100.0,
            offset=10.0,
            helix_angle=beta,
            profile_shift_coefficient=xx,
        )

    t = gb.Transmission(
        pinion=g(z, x),
        wheel=g(60, 0.0),
        lubricant=gb.Lubricant(kinematic_viscosity_40c=100.0),
        pinion_speed_rpm=1000.0,
        power_kw=1.0,
        design_life_hours=1000.0,
    )
    ref = _tooth_root_geometry(t, t.pinion)
    # python-gearbox itera 9 volte su θ: differenza residua ~1e-6 mm
    assert f.s_Fn == pytest.approx(ref.tooth_root_chord, abs=5e-6)
    assert f.rho_F == pytest.approx(ref.root_fillet_radius, abs=5e-7)


def test_form_factor_reference_chart() -> None:
    # DIN 3990-3 diagrammi: z = 20, x = 0, h_fP = 1.25, ρ_fP = 0.38 → Y_Fa ≈ 2.80, Y_Sa ≈ 1.55
    f = root_form_factors(gear_geometry(CylindricalGear(z=20, m_n=1.0, b=10.0)))
    assert f.Y_Fa == pytest.approx(2.80, abs=0.02)
    assert f.Y_Sa == pytest.approx(1.55, abs=0.02)


# --- grado di perdita ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("z1", "z2", "x1", "x2"), [(20, 40, 0.0, 0.0), (17, 51, 0.3, -0.1), (25, 25, 0.0, 0.0)]
)
def test_loss_factor_matches_numeric_integration(z1: int, z2: int, x1: float, x2: float) -> None:
    geo = pair_geometry(_pair(z1, z2, 1.0, 10.0, 0.0, x1, x2))
    p_bt = geo.gear1.p_bt
    r_b1, r_b2 = geo.gear1.d_b / 2, geo.gear2.d_b / 2
    tan = math.tan(math.radians(geo.alpha_wt))
    g_a1 = math.sqrt((geo.gear1.d_a / 2) ** 2 - r_b1**2) - r_b1 * tan
    g_a2 = math.sqrt((geo.gear2.d_a / 2) ** 2 - r_b2**2) - r_b2 * tan
    s = np.linspace(0.0, p_bt, 100001)[:-1]
    tot, n = np.zeros_like(s), np.zeros_like(s)
    for k in range(-3, 4):
        g = s + k * p_bt - g_a2
        inside = (g >= -g_a2) & (g <= g_a1)
        tot += np.where(inside, np.abs(g), 0.0)
        n += inside
    u = z2 / z1
    numeric = float(np.mean(tot / n)) * (u + 1) / (u * r_b1)
    assert loss_factor(geo) == pytest.approx(numeric, rel=1e-4)


# --- dati materiale -------------------------------------------------------------------


def test_material_curves() -> None:
    pom, pa = Material(polymer=Polymer.POM), Material(polymer=Polymer.PA66)
    assert root_strength(pom, 20.0, 1e8) == pytest.approx(26 - 1.0 + 400 * 1e8**-0.2)
    assert root_strength(pa, 60.0, 1e6) == pytest.approx(
        30 - 0.22 * 60 + (4600 - 900 * 60**0.3) * 1e6 ** (-1 / 3)
    )
    assert root_strength(Material(polymer=Polymer.PBT), 60.0, 1e6) is None
    assert root_strength(Material(polymer=Polymer.PBT, sigma_FlimN=30.0), 60.0, 1e6) == 30.0
    assert flank_strength(pa, 60.0, 1e6, Lubrication.GREASE) is not None
    assert flank_strength(pom, 60.0, 1e6, Lubrication.GREASE) is None
    assert flank_strength(pa, 60.0, 1e6, Lubrication.DRY) is None
    # la resistenza cala con temperatura e cicli
    assert root_strength(pom, 80.0, 1e6) < root_strength(pom, 40.0, 1e6)  # type: ignore[operator]
    assert root_strength(pom, 40.0, 1e8) < root_strength(pom, 40.0, 1e6)  # type: ignore[operator]
    assert friction_coefficient(Polymer.POM, Polymer.POM, Lubrication.DRY) == 0.28
    assert friction_coefficient(Polymer.STEEL, Polymer.PA66, Lubrication.DRY) == 0.20
    assert friction_coefficient(Polymer.POM, Polymer.PA66, Lubrication.GREASE) == 0.09
    assert friction_coefficient(Polymer.PBT, Polymer.PBT, Lubrication.DRY) is None


# --- verifica completa -------------------------------------------------------------------


def test_rating_hand_check() -> None:
    inp = _input()
    r = rate_vdi2736(inp)
    geo = r.geometry
    assert r.F_t == pytest.approx(2000 * 0.15 / geo.gear1.d)
    assert pytest.approx(0.15 * 2 * math.pi * 3000 / 60) == r.P
    assert r.mu == 0.09
    g1 = r.gear1
    assert g1 is not None
    # eq. 7: k_θ,Fuß = 2100 (plastica/plastica), carter aperto, ED = 1
    theta = 40.0 + r.P * 0.09 * r.H_V * 2100 / (6.0 * 12 * (r.v_t * 0.8) ** 0.75)
    assert g1.theta_root == pytest.approx(theta)
    sigma_F = g1.Y_Fa * g1.Y_Sa * r.Y_eps * r.Y_beta * r.F_t / (6.0 * 0.8)
    assert g1.sigma_F == pytest.approx(sigma_F)
    assert (
        pytest.approx(2.0 * root_strength(Material(polymer=Polymer.POM), theta, g1.N_L) / sigma_F)
        == g1.S_F
    )  # type: ignore[operator]
    assert pytest.approx(60 * 3000 * 500) == g1.N_L
    assert r.gear2 is not None and pytest.approx(g1.N_L * 12 / 45) == r.gear2.N_L
    assert g1.W_m is None  # a grasso niente usura


def test_steel_pinion_dry_wear() -> None:
    r = rate_vdi2736(_input(Lubrication.DRY, Polymer.STEEL, Polymer.POM))
    assert r.gear1 is None
    g2 = r.gear2
    assert g2 is not None and g2.W_m is not None
    T2 = 0.15 * 45 / 12
    W = T2 * 2 * math.pi * g2.N_L * r.H_V * 1.0e-6 / (6.0 * 45 * g2.l_Fl)
    assert g2.W_m == pytest.approx(W)
    assert r.mu == 0.20
    # k_θ plastica/acciaio è minore → ruota più fredda che con POM/POM
    r_pp = rate_vdi2736(_input(Lubrication.DRY, Polymer.POM, Polymer.POM))
    assert r_pp.gear2 is not None and g2.theta_root < r_pp.gear2.theta_root


def test_housing_and_ambient_raise_temperature() -> None:
    base = rate_vdi2736(_input())
    closed = rate_vdi2736(_input(housing=Housing(R_lambda_G=0.06, A_G=0.01)))
    assert base.gear1 is not None and closed.gear1 is not None
    assert closed.gear1.theta_flank > base.gear1.theta_flank
    assert closed.gear1.S_F is not None and base.gear1.S_F is not None
    assert closed.gear1.S_F < base.gear1.S_F


def test_pa66_flank_check_with_grease() -> None:
    r = rate_vdi2736(_input(Lubrication.GREASE, Polymer.STEEL, Polymer.PA66))
    assert r.gear2 is not None and r.gear2.S_H is not None
    assert pytest.approx(r.gear2.sigma_HlimN / r.sigma_H) == r.gear2.S_H  # type: ignore[operator]


def test_input_validation() -> None:
    with pytest.raises(ValidationError):
        Housing(R_lambda_G=0.06)
    with pytest.raises(ValidationError):
        _input(m1=Polymer.STEEL, m2=Polymer.STEEL)
    internal = GearPair(
        gear1=CylindricalGear(z=15, m_n=1, b=5),
        gear2=CylindricalGear(z=50, m_n=1, b=5, internal=True),
    )
    with pytest.raises(ValidationError):
        VDI2736Input(
            pair=internal,
            material1=Material(polymer=Polymer.POM),
            material2=Material(polymer=Polymer.POM),
            lubrication=Lubrication.GREASE,
            operating=OperatingConditions(T_1=0.1, n_1=1000, life_hours=100),
        )


def test_json_roundtrip() -> None:
    inp = _input(Lubrication.DRY, Polymer.STEEL, Polymer.POM)
    assert VDI2736Input.model_validate_json(inp.model_dump_json()) == inp
    out = rate_vdi2736(inp)
    assert out.model_dump_json()
