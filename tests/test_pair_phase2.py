import pytest
from pydantic import ValidationError

from gearcalc import (
    CylindricalGear,
    GearPair,
    ShiftDistribution,
    pair_for_center_distance,
    pair_geometry,
)
from gearcalc.geometry import balanced_sliding_x1, x_sum_for_center_distance


def test_balanced_sliding_distribution() -> None:
    g1 = CylindricalGear(z=12, m_n=1.0, b=8.0)
    g2 = CylindricalGear(z=40, m_n=1.0, b=8.0)
    p = pair_for_center_distance(26.5, g1, g2, distribution=ShiftDistribution.BALANCED_SLIDING)
    geo = pair_geometry(p)
    assert geo.a_w == pytest.approx(26.5, abs=1e-9)
    assert abs(geo.zeta_A1) == pytest.approx(abs(geo.zeta_E2), rel=1e-6)
    assert p.gear1.x > p.gear2.x  # il pignone piccolo riceve lo spostamento maggiore
    eq = pair_geometry(pair_for_center_distance(26.5, g1, g2))
    assert max(abs(eq.zeta_A1), abs(eq.zeta_E2)) > abs(geo.zeta_A1)


def test_balanced_sliding_internal() -> None:
    g1 = CylindricalGear(z=15, m_n=1.0, b=8.0)
    g2 = CylindricalGear(z=48, m_n=1.0, b=8.0, internal=True)
    x1 = balanced_sliding_x1(g1, g2, 0.0)
    geo = pair_geometry(
        GearPair(gear1=g1.model_copy(update={"x": x1}), gear2=g2.model_copy(update={"x": -x1}))
    )
    assert abs(geo.zeta_A1) == pytest.approx(abs(geo.zeta_E2), rel=1e-6)


def test_sliding_symmetry_equal_gears() -> None:
    geo = pair_geometry(
        GearPair(gear1=CylindricalGear(z=30, m_n=1, b=5), gear2=CylindricalGear(z=30, m_n=1, b=5))
    )
    assert geo.zeta_A1 == pytest.approx(geo.zeta_E2)
    assert geo.d_Nf1 == pytest.approx(geo.d_Nf2)


def test_active_diameters_consistent_with_contact_length() -> None:
    geo = pair_geometry(
        GearPair(
            gear1=CylindricalGear(z=19, m_n=1.5, b=10, x=0.25),
            gear2=CylindricalGear(z=53, m_n=1.5, b=10, x=-0.1),
        )
    )
    r_b1 = geo.gear1.d_b / 2
    # rotolamento sul pignone tra d_Nf1 e d_a1 = lunghezza del segmento di contatto
    import math

    roll = math.sqrt((geo.gear1.d_a / 2) ** 2 - r_b1**2) - math.sqrt((geo.d_Nf1 / 2) ** 2 - r_b1**2)
    assert roll == pytest.approx(geo.g_alpha)
    assert geo.gear1.d_Ff is not None and geo.d_Nf1 > geo.gear1.d_Ff


def test_internal_center_distance_roundtrip() -> None:
    g1 = CylindricalGear(z=15, m_n=1.0, b=8.0, beta=12.0)
    g2 = CylindricalGear(z=52, m_n=1.0, b=8.0, beta=12.0, internal=True)
    p = pair_for_center_distance(19.2, g1, g2, x1=0.3)
    geo = pair_geometry(p)
    assert geo.a_w == pytest.approx(-19.2, abs=1e-10)
    assert x_sum_for_center_distance(19.2, 15, 52, 1.0, beta=12.0, internal=True) == pytest.approx(
        p.gear1.x + p.gear2.x
    )


def test_internal_validation() -> None:
    with pytest.raises(ValidationError):  # eliche dello stesso verso
        GearPair(
            gear1=CylindricalGear(z=15, m_n=1, b=5, beta=10),
            gear2=CylindricalGear(z=50, m_n=1, b=5, beta=-10, internal=True),
        )
    with pytest.raises(ValidationError):  # pignone interno
        GearPair(
            gear1=CylindricalGear(z=15, m_n=1, b=5, internal=True),
            gear2=CylindricalGear(z=50, m_n=1, b=5),
        )
    with pytest.raises(ValidationError):  # riduzione di testa
        GearPair(
            gear1=CylindricalGear(z=15, m_n=1, b=5),
            gear2=CylindricalGear(z=50, m_n=1, b=5, internal=True),
            tip_shortening=True,
        )
    with pytest.raises(ValidationError):
        GearPair(
            gear1=CylindricalGear(z=30, m_n=1, b=5),
            gear2=CylindricalGear(z=30, m_n=1, b=5, internal=True),
        )


def test_internal_small_tooth_difference_warning() -> None:
    geo = pair_geometry(
        GearPair(
            gear1=CylindricalGear(z=40, m_n=1, b=5),
            gear2=CylindricalGear(z=46, m_n=1, b=5, internal=True),
        )
    )
    assert any("trocoidale" in w for w in geo.warnings)
