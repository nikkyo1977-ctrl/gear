import math

import pytest
from pydantic import ValidationError

from gearcalc import BasicRackProfile, CylindricalGear, GeometryError, StandardRack, gear_geometry
from gearcalc.geometry import x_min_undercut


def test_spur_reference_values() -> None:
    g = gear_geometry(CylindricalGear(z=20, m_n=2.0, b=20.0))
    assert g.d == pytest.approx(40.0)
    assert g.d_b == pytest.approx(40.0 * math.cos(math.radians(20.0)))
    assert g.d_a == pytest.approx(44.0)
    assert g.d_f == pytest.approx(35.0)
    assert g.s_n == pytest.approx(math.pi)
    assert g.s_at == pytest.approx(1.38976, abs=1e-5)
    assert g.p_z == math.inf
    assert g.z_n == pytest.approx(20.0)


def test_helical_transverse_quantities() -> None:
    g = gear_geometry(CylindricalGear(z=30, m_n=1.5, b=10.0, beta=20.0, x=0.2))
    cb = math.cos(math.radians(20.0))
    assert g.m_t == pytest.approx(1.5 / cb)
    assert g.alpha_t == pytest.approx(math.degrees(math.atan(math.tan(math.radians(20)) / cb)))
    assert g.d == pytest.approx(30 * 1.5 / cb)
    # lo spostamento è riferito al modulo normale: d_a = d + 2·m_n·(1 + x)
    assert g.d_a == pytest.approx(g.d + 2 * 1.5 * 1.2)
    assert g.s_t == pytest.approx(g.s_n / cb)
    assert g.p_z == pytest.approx(math.pi * g.d / math.tan(math.radians(20.0)))
    # sin(beta_b) = sin(beta)·cos(alpha_n)
    assert math.sin(math.radians(g.beta_b)) == pytest.approx(
        math.sin(math.radians(20.0)) * math.cos(math.radians(20.0))
    )


def test_undercut_limit_classic() -> None:
    # utensile a spigolo vivo, h_a0* = 1: z_min teorico = 2/sin²20° ≈ 17.1
    rack = BasicRackProfile(h_aP_star=1.0, h_fP_star=1.0001, rho_fP_star=0.0)
    assert x_min_undercut(CylindricalGear(z=17, m_n=1, b=1, rack=rack)) > 0.0
    assert x_min_undercut(CylindricalGear(z=18, m_n=1, b=1, rack=rack)) < 0.0


def test_undercut_flag_iso53a() -> None:
    g = gear_geometry(CylindricalGear(z=10, m_n=1.0, b=5.0))
    expected = (
        1.25 - 0.38 * (1 - math.sin(math.radians(20))) - 10 * math.sin(math.radians(20)) ** 2 / 2
    )
    assert g.x_min_undercut == pytest.approx(expected)
    assert g.undercut
    assert not gear_geometry(CylindricalGear(z=10, m_n=1.0, b=5.0, x=0.45)).undercut


def test_standard_racks() -> None:
    assert StandardRack.ISO53_D.profile().h_fP_star == pytest.approx(1.40)


def test_invalid_inputs() -> None:
    with pytest.raises(ValidationError):
        CylindricalGear(z=2, m_n=1.0, b=1.0)
    with pytest.raises(ValidationError):
        CylindricalGear(z=20, m_n=-1.0, b=1.0)
    with pytest.raises(ValidationError):
        BasicRackProfile(h_aP_star=1.0, h_fP_star=0.9)
    with pytest.raises(GeometryError):
        gear_geometry(CylindricalGear(z=20, m_n=1.0, b=1.0), k=0.1)


def test_json_roundtrip() -> None:
    g = CylindricalGear(z=23, m_n=0.8, b=6.0, beta=-15.0, x=0.1)
    assert CylindricalGear.model_validate_json(g.model_dump_json()) == g
