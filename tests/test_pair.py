import math

import pytest
from pydantic import ValidationError

from gearcalc import (
    CylindricalGear,
    GearPair,
    GeometryError,
    pair_for_center_distance,
    pair_geometry,
)
from gearcalc.geometry import x_sum_for_center_distance


def _pair(
    z1: int,
    z2: int,
    m: float,
    b: float,
    beta: float,
    x1: float,
    x2: float,
    tip_shortening: bool = False,
) -> GearPair:
    return GearPair(
        gear1=CylindricalGear(z=z1, m_n=m, b=b, beta=beta, x=x1),
        gear2=CylindricalGear(z=z2, m_n=m, b=b, beta=-beta, x=x2),
        tip_shortening=tip_shortening,
    )


def test_zero_shift_pair() -> None:
    p = pair_geometry(_pair(20, 40, 2.0, 20.0, 0.0, 0.0, 0.0))
    assert p.a_w == pytest.approx(60.0)
    assert p.alpha_wt == pytest.approx(20.0)
    assert p.y == pytest.approx(0.0, abs=1e-12)
    assert p.k == pytest.approx(0.0, abs=1e-12)
    assert p.epsilon_alpha == pytest.approx(1.6352, abs=1e-4)
    assert p.epsilon_beta == 0.0
    assert p.warnings == ()


def test_overlap_ratio() -> None:
    p = pair_geometry(_pair(22, 63, 2.5, 30.0, 15.0, 0.0, 0.0))
    assert p.epsilon_beta == pytest.approx(30 * math.sin(math.radians(15)) / (math.pi * 2.5))
    assert p.epsilon_gamma == pytest.approx(p.epsilon_alpha + p.epsilon_beta)


def test_center_distance_roundtrip() -> None:
    g1 = CylindricalGear(z=17, m_n=1.0, b=8.0, beta=12.0)
    g2 = CylindricalGear(z=52, m_n=1.0, b=8.0, beta=-12.0)
    pair = pair_for_center_distance(35.6, g1, g2, x1=0.4)
    assert pair.gear1.x == pytest.approx(0.4)
    assert pair_geometry(pair).a_w == pytest.approx(35.6, abs=1e-10)
    eq = pair_for_center_distance(35.6, g1, g2)
    assert eq.gear1.x == pytest.approx(eq.gear2.x)


def test_center_distance_not_feasible() -> None:
    with pytest.raises(GeometryError):
        x_sum_for_center_distance(10.0, 20, 40, 2.0)


def test_tip_shortening() -> None:
    p0 = pair_geometry(_pair(15, 30, 2.0, 10.0, 0.0, 0.6, 0.6))
    assert p0.k < -0.05
    assert any("Gioco di testa" in w for w in p0.warnings)
    p1 = pair_geometry(_pair(15, 30, 2.0, 10.0, 0.0, 0.6, 0.6, tip_shortening=True))
    # con riduzione di testa il gioco di testa torna a c* = 0.25·m_n
    c = p1.a_w - p1.gear1.d_a / 2 - p1.gear2.d_f / 2
    assert c == pytest.approx(0.25 * 2.0)
    assert p1.epsilon_alpha < p0.epsilon_alpha


def test_warnings_undercut_and_low_contact_ratio() -> None:
    p = pair_geometry(_pair(9, 12, 1.0, 5.0, 0.0, 0.0, 0.0))
    assert any("sottosquadro" in w for w in p.warnings)
    assert any("Interferenza" in w for w in p.warnings)


def test_pair_validation() -> None:
    with pytest.raises(ValidationError):
        GearPair(
            gear1=CylindricalGear(z=20, m_n=1, b=1), gear2=CylindricalGear(z=20, m_n=1.25, b=1)
        )
    with pytest.raises(ValidationError):
        GearPair(
            gear1=CylindricalGear(z=20, m_n=1, b=1, beta=10),
            gear2=CylindricalGear(z=20, m_n=1, b=1, beta=10),
        )
