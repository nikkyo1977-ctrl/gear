"""VDI 2736 Blatt 3:2014-05, allegato A, PDF 21–27; risultati KB a precisione piena."""

import math

import pytest
from pydantic import ValidationError

from gearcalc.errors import GeometryError
from gearcalc.rating import Blatt3Input, rate_blatt3


def flank_case(case):
    data = annex(case)
    data["geometry"]["epsilon_n_reference"] = 2.130 if case == "A1" else 2.268
    data["flank"] = dict(
        mu=0.1,
        E_1=210000,
        nu_1=0.3,
        E_2=2100 if case == "A1" else 767,
        nu_2=0.4 if case == "A1" else 0.47,
    )
    return data


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("A1", (520.26, 5.028, 0.685189, 0.0846467, 2.22865, 0.741036, 103.060)),
        ("A2", (20.50, 1.574, 0.664016, 0.115234, 0.743302, 0.224696, 38.9069)),
    ],
)
def test_flank_annex(case, expected):
    data = flank_case(case)
    geometry_result = rate_blatt3(Blatt3Input(**data))
    data["flank"]["epsilon_source"] = "reference"
    annex_result = rate_blatt3(Blatt3Input(**data))
    f = annex_result.flank
    # Tolleranze assolute per la precisione degli intermedi indipendenti KB/PDF.
    tolerances = (
        0.01,
        0.001,
        0.000001,
        0.0000001 if case == "A1" else 0.000001,
        0.00001 if case == "A1" else 0.000001,
        0.000001,
        0.001 if case == "A1" else 0.0001,
    )
    for name, value, tol in zip(
        ("F_n", "rho_n", "Z_epsilonS", "Z_F", "a_h", "b_h", "sigma_Hm"),
        expected,
        tolerances,
        strict=True,
    ):
        assert getattr(f, name) == pytest.approx(value, abs=tol, rel=0), name
    fg = geometry_result.flank
    assert fg.epsilon_used == geometry_result.epsilon_n and fg.epsilon_source == "geometry"
    assert f.epsilon_used == data["geometry"]["epsilon_n_reference"]
    assert f.flank_ok is None
    assert fg.a_h == f.a_h and fg.b_h == f.b_h
    assert fg.sigma_Hm / f.sigma_Hm == pytest.approx(math.sqrt(f.epsilon_used / fg.epsilon_used))
    assert geometry_result.tau_F == annex_result.tau_F


@pytest.mark.parametrize(
    ("field", "diameter"), [("d_form1", 18.080899924), ("d_form2", 53.188327138)]
)
def test_a1_equivalent_form_circles(field, diameter):
    # Inversioni alternative della (12), esempi diagnostici senza attribuzione al pezzo.
    data = flank_case("A1")
    data["geometry"][field] = diameter
    result = rate_blatt3(Blatt3Input(**data))
    assert result.epsilon_n == pytest.approx(2.130, abs=1e-9)
    assert result.flank.sigma_Hm == pytest.approx(103.060, abs=0.001)


def test_flank_load_scaling_and_limit():
    data = flank_case("A1")
    data["flank"]["sigma_HP"] = dict(value=110, source="caso sintetico")
    nominal = rate_blatt3(Blatt3Input(**data)).flank
    data["K_A"] = 2
    loaded = rate_blatt3(Blatt3Input(**data)).flank
    assert nominal.flank_ok and not loaded.flank_ok
    assert nominal.F_n == loaded.F_n
    assert loaded.sigma_Hm / nominal.sigma_Hm == pytest.approx(math.cbrt(2))
    assert loaded.a_h / nominal.a_h == pytest.approx(math.cbrt(2))


def test_flank_requires_declared_reference_and_valid_working_angles():
    data = flank_case("A1")
    data["flank"]["epsilon_source"] = "reference"
    del data["geometry"]["epsilon_n_reference"]
    with pytest.raises(GeometryError, match="epsilon_n_reference"):
        rate_blatt3(Blatt3Input(**data))
    data["geometry"]["beta_s1"] = 5
    with pytest.raises(GeometryError, match="Angoli incompatibili"):
        rate_blatt3(Blatt3Input(**data))


def annex(case):
    # Dati assegnati dall'esempio. Le resistenze sono letture pubblicate, non curve interpolate.
    if case == "A1":
        geometry = dict(
            z1=2,
            z2=29,
            m_n=1.7,
            a=32.432,
            d_s1=13.826,
            d_s2=51.039,
            d_b1=8.802,
            d_b2=48.773,
            d_a1=18.632,
            d_a2=53.865,
            d_m1=13.137,
            d_2=50.862,
            b_2=15,
            alpha_n=16,
            beta_s1=75.716,
            beta_b1=68.203,
            beta_b2=13.674,
            beta_2=14.236,
            gamma_m1=15,
            x2=0.96,
        )
        grade, temp, torque, speed, hours, limit, strength = "POM", 80, 12, 2200, 700, 7.798, 23.3
    else:
        geometry = dict(
            z1=2,
            z2=42,
            m_n=0.75,
            a=18.685,
            d_s1=4.249,
            d_s2=33.121,
            d_b1=3.667,
            d_b2=32.366,
            d_a1=5.943,
            d_a2=34.093,
            d_m1=4.854,
            d_2=33.668,
            b_2=8,
            alpha_n=15,
            beta_s1=69.636,
            beta_b1=66.73,
            beta_b2=19.937,
            beta_2=20.672,
            gamma_m1=18,
            x2=0.363,
        )
        grade, temp, torque, speed, hours, limit, strength = (
            "PA46",
            150,
            0.3,
            4500,
            500,
            8.975,
            12.76,
        )
    return dict(
        geometry=geometry,
        wheel_grade=grade,
        theta_M=temp,
        T_2=torque,
        n_1=speed,
        life_hours=hours,
        C_lim=dict(value=limit, source=case),
        sigma_ZSch=dict(value=strength, source=case),
    )


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        (
            "A1",
            dict(
                F_t2=470.229,
                v_gs=1.64337,
                C=7.0681,
                b_m=13.213,
                b_max=15.0,
                d_x0=46.232,
                s_t2=3.721,
                A_tau=52.8788,
                tau_F=4.44628,
                S_F=3.93025,
                N_L=6372413.79,
            ),
        ),
        (
            "A2",
            dict(
                F_t2=18.1154,
                v_gs=1.06792,
                C=1.8070,
                b_m=3.429,
                b_max=4.958,
                d_x0=31.427,
                s_t2=1.415,
                A_tau=6.90226,
                tau_F=1.31228,
                S_F=7.29265,
                N_L=6428571.43,
            ),
        ),
    ],
)
def test_annex(case, expected):
    raw = annex(case)
    reference = 2.130 if case == "A1" else 2.268
    raw["geometry"]["epsilon_n_reference"] = reference
    data = Blatt3Input(**raw)
    r = rate_blatt3(data)
    for name, value in expected.items():
        tolerance = {
            "F_t2": 0.001 if case == "A1" else 0.0001,
            "v_gs": 0.00001,
            "C": 0.0001,
            "b_m": 0.001,
            "b_max": 0.001,
            "d_x0": 0.001,
            "s_t2": 0.001,
            "N_L": 0.01,
            "A_tau": 0.0001 if case == "A1" else 0.00001,
            "tau_F": 0.00001,
            "S_F": 0.00001,
        }[name]
        assert getattr(r, name) == pytest.approx(value, abs=tolerance, rel=0), name
    assert r.used_reference_thickness and r.s_da1 == r.s_t2
    assert r.Y_eps == 0.5 and r.epsilon_nz == 2
    assert r.preliminary_ok and r.root_ok
    assert pytest.approx(data.C_lim.value / r.C) == r.S_C
    assert r.tau_Flim == pytest.approx(0.75 * data.sigma_ZSch.value)
    assert r.epsilon_n == pytest.approx(2.29473 if case == "A1" else 2.26754, abs=0.00001)
    assert r.epsilon_n_difference == pytest.approx(r.epsilon_n - reference)


def test_load_factor_and_missing_limits():
    raw = annex("A1")
    initial = rate_blatt3(Blatt3Input(**raw))
    raw.update(K_A=2, C_lim=None, sigma_ZSch=None)
    r = rate_blatt3(Blatt3Input(**raw))
    assert r.F_t2 == initial.F_t2 and r.C == 2 * initial.C and r.tau_F == 2 * initial.tau_F
    assert r.S_C is r.S_F is r.preliminary_ok is r.root_ok is None


def test_contact_ratio_integer_boundary():
    raw = annex("A1")
    g = raw["geometry"]
    # Invert the path length for the active tip diameter at exactly two teeth.
    r = rate_blatt3(Blatt3Input(**raw))
    pitch = math.pi * g["m_n"] * math.cos(math.radians(g["alpha_n"]))
    working = math.sqrt(g["d_s1"] ** 2 - g["d_b1"] ** 2)
    projected = working + 2 * math.cos(math.radians(g["beta_b1"])) * (2 * pitch - r.g_an2)
    boundary = math.hypot(g["d_b1"], projected)
    for offset, expected in [(-1e-6, 1), (1e-6, 2)]:
        g["d_form1"] = boundary + offset
        assert rate_blatt3(Blatt3Input(**raw)).epsilon_nz == expected
    g["epsilon_n_reference"] = 1.99
    with pytest.raises(GeometryError, match="ε_nz"):
        rate_blatt3(Blatt3Input(**raw))


def test_section_above_base_and_undercut():
    raw = annex("A2")
    raw["geometry"]["d_a1"] = 4.95
    r = rate_blatt3(Blatt3Input(**raw))
    assert r.d_x0 > raw["geometry"]["d_b2"] and not r.used_reference_thickness
    assert r.s_da1 != r.s_t2
    raw["geometry"]["undercut2"] = True
    assert rate_blatt3(Blatt3Input(**raw)).s_da1 == r.s_t2


def test_high_heating_and_invalid_geometry():
    raw = annex("A1")
    raw["strong_self_heating"] = True
    assert rate_blatt3(Blatt3Input(**raw)).preliminary_ok is False
    raw["geometry"]["z2"] = 19
    r = rate_blatt3(Blatt3Input(**raw))
    assert r.K_z is r.C is r.preliminary_ok is None and r.root_ok
    raw["geometry"]["d_b2"] = 80
    with pytest.raises(GeometryError):
        rate_blatt3(Blatt3Input(**raw))
    raw["K_A"] = float("nan")
    with pytest.raises(ValidationError):
        Blatt3Input(**raw)
