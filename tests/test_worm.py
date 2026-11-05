import math

import numpy as np
import pytest
from pydantic import ValidationError

from gearcalc import gear_geometry
from gearcalc.geometry import FlankForm, WormGearSet, virtual_wheel, worm_geometry
from gearcalc.rating import (
    Lubrication,
    Material,
    Polymer,
    WormOperating,
    WormPlasticInput,
    efficiency,
    rate_worm_plastic,
)


def _ws(**kw: object) -> WormGearSet:
    base: dict[str, object] = dict(z1=1, z2=40, m=0.8, q=10.0, b1=20.0, b2=6.0)
    base.update(kw)
    return WormGearSet(**base)  # type: ignore[arg-type]


def _inp(lub: Lubrication = Lubrication.GREASE, **kw: object) -> WormPlasticInput:
    return WormPlasticInput(
        gearset=_ws(),
        wheel_material=Material(polymer=Polymer.POM),
        lubrication=lub,
        operating=WormOperating(T_2=1.0, n_1=3000.0, life_hours=300.0, theta_0=40.0),
        **kw,  # type: ignore[arg-type]
    )


def test_geometry_hand_values() -> None:
    g = worm_geometry(_ws(x2=0.2))
    assert g.d_m1 == pytest.approx(8.0)
    assert g.d_2 == pytest.approx(32.0)
    assert g.a == pytest.approx(20.0 + 0.2 * 0.8)
    assert g.gamma_m == pytest.approx(math.degrees(math.atan(0.1)))
    assert g.p_z == pytest.approx(math.pi * 0.8)
    assert g.d_a1 == pytest.approx(9.6) and g.d_f1 == pytest.approx(8.0 - 2 * 1.2 * 0.8)
    assert g.d_a2 == pytest.approx(32.0 + 2 * 0.8 * 1.2)
    # larghezza utile: 2·√(r_a1² − (r_m1 − h_a)²) = 4·√(r_m1·m) per h_a = m
    assert g.b2_max == pytest.approx(4.0 * math.sqrt(4.0 * 0.8))


@pytest.mark.parametrize("form", list(FlankForm))
def test_pressure_angles(form: FlankForm) -> None:
    g = worm_geometry(_ws(z1=2, q=9.0, flank_form=form))
    cg = math.cos(math.radians(g.gamma_m))
    if form is FlankForm.ZA:
        assert g.alpha_x == pytest.approx(20.0)
    else:
        assert g.alpha_n == pytest.approx(20.0)
    assert math.tan(math.radians(g.alpha_n)) == pytest.approx(
        math.tan(math.radians(g.alpha_x)) * cg
    )


@pytest.mark.parametrize("ws", [_ws(), _ws(z1=2, q=9.0, x2=0.3), _ws(flank_form=FlankForm.ZA)])
def test_virtual_wheel_matches_wheel(ws: WormGearSet) -> None:
    g = worm_geometry(ws)
    v = gear_geometry(virtual_wheel(ws))
    assert v.d == pytest.approx(g.d_2)
    assert v.d_a == pytest.approx(g.d_a2)
    assert v.d_f == pytest.approx(g.d_f2)
    assert v.alpha_t == pytest.approx(g.alpha_x)


def test_contact_ratio_against_rack_pair_limit() -> None:
    # ε_α della ruota con la vite come dentiera = limite z→∞ della coppia cilindrica
    from gearcalc import CylindricalGear, GearPair, pair_geometry

    ws = _ws(flank_form=FlankForm.ZA, z1=1, q=29.0)  # γ piccolo: piano medio ≈ trasversale
    g = worm_geometry(ws)
    p = pair_geometry(
        GearPair(
            gear1=CylindricalGear(z=40, m_n=0.8, b=6), gear2=CylindricalGear(z=4000, m_n=0.8, b=6)
        )
    )
    assert g.epsilon_alpha == pytest.approx(p.epsilon_alpha, rel=2e-3)


def test_efficiency_from_vector_mechanics() -> None:
    """η da potenze calcolate con la forza normale e d'attrito in 3D sul punto primitivo."""
    for gamma_deg, mu, a_n_deg in [(5.71, 0.09, 20.0), (15.0, 0.2, 20.0), (25.0, 0.05, 15.0)]:
        g, a = math.radians(gamma_deg), math.radians(a_n_deg)
        n = np.array([math.sin(g) * math.cos(a), math.sin(a), math.cos(g) * math.cos(a)])
        v1 = np.array([1.0, 0.0, 0.0])  # vite (tangenziale)
        v2 = np.array([0.0, 0.0, math.tan(g)])  # ruota (assiale alla vite)
        s = (v1 - v2) / np.linalg.norm(v1 - v2)  # strisciamento della vite sulla ruota
        assert abs(float(n @ s)) < 1e-12  # lo strisciamento giace nel piano tangente
        F = n + mu * s  # forza sulla ruota per F_n = 1
        eta_vec = float(F @ v2) / float(F @ v1)
        eta, _ = efficiency(g, math.atan(mu / math.cos(a)))
        assert eta == pytest.approx(eta_vec, rel=1e-12)


def test_rating_power_balance_and_forces() -> None:
    r = rate_worm_plastic(_inp())
    g = r.geometry
    assert r.mu == 0.09
    assert r.n_2 == pytest.approx(3000 / 40)
    assert r.P_1 * r.eta == pytest.approx(r.P_1 - r.P_V)
    assert r.T_1 * 2 * math.pi * 3000 / 60 == pytest.approx(r.P_1)
    assert r.F_t2 == pytest.approx(2000 * 1.0 / g.d_2)
    gamma, rho = math.radians(g.gamma_m), math.radians(r.rho_prime)
    assert r.F_t1 == pytest.approx(r.F_t2 * math.tan(gamma + rho))
    assert r.v_g == pytest.approx(r.v_1 / math.cos(gamma))


def test_self_locking() -> None:
    r = rate_worm_plastic(_inp(Lubrication.DRY, mu_static=0.3))
    assert r.mu == 0.20
    assert r.self_locking_dynamic and r.eta_back < 0.0
    assert r.self_locking_static
    r2 = rate_worm_plastic(
        WormPlasticInput(
            gearset=_ws(z1=3, q=8.0),
            wheel_material=Material(polymer=Polymer.POM),
            lubrication=Lubrication.GREASE,
            operating=WormOperating(T_2=1.0, n_1=3000.0, life_hours=10.0),
        )
    )
    assert not r2.self_locking_dynamic and r2.eta_back > 0.0


def test_imposed_temperature_and_root_strength() -> None:
    r = rate_worm_plastic(_inp(theta_wheel=60.0))
    assert not r.temperature_estimated
    assert r.theta_root == r.theta_flank == 60.0
    assert r.sigma_FlimN == pytest.approx(26 - 0.0025 * 3600 + 400 * r.N_L2**-0.2)
    assert pytest.approx(2 * r.sigma_FlimN / r.sigma_F) == r.S_F  # type: ignore[operator]
    est = rate_worm_plastic(_inp())
    assert est.temperature_estimated and any("stimata" in w for w in est.warnings)


def test_dry_wear_archard() -> None:
    r = rate_worm_plastic(_inp(Lubrication.DRY))
    assert r.W_m is not None
    expected = 1.0e-6 * r.F_n * r.v_g * 300 * 3600 / (40 * 6.0 * r.l_Fl)
    assert r.W_m == pytest.approx(expected)
    assert rate_worm_plastic(_inp()).W_m is None


def test_worm_deflection() -> None:
    r = rate_worm_plastic(_inp(bearing_span=30.0))
    inertia = math.pi * r.geometry.d_f1**4 / 64
    assert r.delta == pytest.approx(math.hypot(r.F_t1, r.F_r) * 30**3 / (48 * 206000 * inertia))


def test_validation() -> None:
    with pytest.raises(ValidationError):
        _ws(q=3.2)
    with pytest.raises(ValidationError):
        WormPlasticInput(
            gearset=_ws(),
            wheel_material=Material(polymer=Polymer.STEEL),
            lubrication=Lubrication.GREASE,
            operating=WormOperating(T_2=1, n_1=1000, life_hours=1),
        )
    g = worm_geometry(_ws(b2=12.0))
    assert any("larghezza utile" in w for w in g.warnings)
