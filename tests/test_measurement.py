import math

import numpy as np
import pytest
from pydantic import ValidationError

from gearcalc import (
    CylindricalGear,
    GearPair,
    GeometryError,
    ThicknessAllowances,
    backlash,
    gear_geometry,
    pair_geometry,
    tooth_measurement,
)
from gearcalc.geometry import over_balls, span_measurement, span_teeth, tooth_flank
from gearcalc.geometry.measurement import _ball_center_angle


def test_span_reference_value() -> None:
    # tabella classica: m = 1, z = 20, α = 20°, k = 3 → W_3 = 7.6604 mm
    geo = gear_geometry(CylindricalGear(z=20, m_n=1.0, b=10.0))
    assert span_teeth(geo) == 3
    assert span_measurement(geo, 3) == pytest.approx(7.66044, abs=1e-5)


def test_span_allowance_shift() -> None:
    geo = gear_geometry(CylindricalGear(z=31, m_n=1.25, b=10.0, beta=15.0, x=0.2))
    k = span_teeth(geo)
    dW = span_measurement(geo, k, -0.05) - span_measurement(geo, k)
    assert dW == pytest.approx(-0.05 * math.cos(math.radians(20.0)))


@pytest.mark.parametrize(
    "gear",
    [
        CylindricalGear(z=20, m_n=2.0, b=10.0),
        CylindricalGear(z=23, m_n=1.0, b=10.0, x=0.3),
        CylindricalGear(z=17, m_n=1.0, b=10.0, beta=15.0, x=0.2),
        CylindricalGear(z=60, m_n=1.0, b=10.0, x=0.2, internal=True),
    ],
)
def test_ball_is_tangent_to_generated_flank(gear: CylindricalGear) -> None:
    """Verifica indipendente: la sfera calcolata è tangente al fianco del profilo generato."""
    geo = gear_geometry(gear)
    tm = tooth_measurement(geo)
    a_Mt = _ball_center_angle(geo, tm.D_M, 0.0)
    r_M = abs(geo.d_b) / 2.0 / math.cos(a_Mt)
    z = abs(geo.z)
    c = np.array([r_M * math.cos(-math.pi / z), r_M * math.sin(-math.pi / z)])
    fl = tooth_flank(geo, n_flank=4000, n_fillet=200)
    dist = float(np.min(np.hypot(fl[:, 0] - c[0], fl[:, 1] - c[1])))
    # nel piano trasversale la sezione della sfera lungo la normale al fianco vale D/cos β_b
    expected = tm.D_M / math.cos(math.radians(geo.beta_b))
    assert 2.0 * dist == pytest.approx(expected, abs=1e-6)
    # sfera ideale: contatto a metà altezza
    target = abs(geo.d) + (-2 if geo.internal else 2) * geo.x * geo.m_n
    assert tm.d_M == pytest.approx(target, abs=1e-6)
    assert tm.warnings == ()


def test_odd_teeth_and_allowances() -> None:
    geo = gear_geometry(CylindricalGear(z=21, m_n=1.0, b=10.0))
    tm = tooth_measurement(geo, ThicknessAllowances(A_sne=-0.02, A_sni=-0.05), D_M=1.75)
    M_even_like, _ = over_balls(geo, 1.75)
    assert tm.M_d == pytest.approx(M_even_like)
    assert tm.M_d_min < tm.M_d_max < tm.M_d
    assert tm.W_k_min is not None and tm.W_k_max is not None and tm.W_k is not None
    assert tm.W_k_min < tm.W_k_max < tm.W_k


def test_internal_has_no_span() -> None:
    geo = gear_geometry(CylindricalGear(z=60, m_n=1.0, b=10.0, internal=True))
    tm = tooth_measurement(geo, ThicknessAllowances(A_sne=-0.02, A_sni=-0.05))
    assert tm.k is None and tm.W_k is None
    # corona: spessore minore → vano maggiore → quota tra sfere maggiore
    assert tm.M_d < tm.M_d_min < tm.M_d_max
    with pytest.raises(GeometryError):
        span_teeth(geo)


def test_allowance_validation() -> None:
    with pytest.raises(ValidationError):
        ThicknessAllowances(A_sne=-0.05, A_sni=-0.02)


def test_backlash_formula() -> None:
    p = pair_geometry(
        GearPair(
            gear1=CylindricalGear(z=17, m_n=1.0, b=8.0, beta=10.0, x=0.2),
            gear2=CylindricalGear(z=45, m_n=1.0, b=8.0, beta=-10.0),
        )
    )
    a1 = ThicknessAllowances(A_sne=-0.03, A_sni=-0.06)
    a2 = ThicknessAllowances(A_sne=-0.04, A_sni=-0.08)
    bl = backlash(p, a1, a2, A_ae=0.02, A_ai=-0.01)
    a_t, a_wt = math.radians(p.gear1.alpha_t), math.radians(p.alpha_wt)
    cb = math.cos(math.radians(10.0))
    j_min = 0.07 / cb * math.cos(a_t) - 2 * 0.01 * math.sin(a_wt)
    j_max = 0.14 / cb * math.cos(a_t) + 2 * 0.02 * math.sin(a_wt)
    assert bl.j_wt_min == pytest.approx(j_min / math.cos(a_wt))
    assert bl.j_wt_max == pytest.approx(j_max / math.cos(a_wt))
    assert bl.j_bn_min == pytest.approx(j_min * math.cos(math.radians(p.gear1.beta_b)))
    assert bl.warnings == ()
    zero = backlash(p, ThicknessAllowances(), ThicknessAllowances(), A_ai=-0.01)
    assert zero.j_wt_min < 0.0 and zero.warnings
