import math

import numpy as np
import pytest

from gearcalc import CylindricalGear, GeometryError, gear_geometry, gear_profile
from gearcalc.geometry import tooth_flank


@pytest.mark.parametrize(
    "gear",
    [
        CylindricalGear(z=20, m_n=2.0, b=10.0),
        CylindricalGear(z=45, m_n=1.0, b=10.0, x=0.3),  # r_f > r_b
        CylindricalGear(z=14, m_n=0.5, b=4.0, beta=18.0, x=0.4),
    ],
)
def test_profile_bounds_and_closure(gear: CylindricalGear) -> None:
    geo = gear_geometry(gear)
    pts = gear_profile(geo)
    r = np.hypot(pts[:, 0], pts[:, 1])
    assert r.min() >= geo.d_f / 2 - 1e-9
    assert r.max() <= geo.d_a / 2 + 1e-9
    # antiorario: area con segno positivo; area tra quella del cerchio di piede e di testa
    x, y = pts[:, 0], pts[:, 1]
    area = 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)
    assert math.pi * (geo.d_f / 2) ** 2 < area < math.pi * (geo.d_a / 2) ** 2
    # angolo polare monotono (nessun ripiegamento del contorno)
    ang = np.unwrap(np.arctan2(y, x))
    assert np.all(np.diff(ang) >= -1e-12)


def test_flank_thickness_at_pitch_circle() -> None:
    geo = gear_geometry(CylindricalGear(z=24, m_n=1.5, b=10.0, x=0.2))
    dr = 0.1
    flank = tooth_flank(geo, thickness_reduction=dr, n_flank=4001)
    r = np.hypot(flank[:, 0], flank[:, 1])
    i = int(np.argmin(np.abs(r - geo.d / 2)))
    half_angle = -math.atan2(flank[i, 1], flank[i, 0])
    assert 2 * half_angle * geo.d / 2 == pytest.approx(geo.s_t - dr, abs=1e-3)


def test_excessive_thickness_reduction() -> None:
    geo = gear_geometry(CylindricalGear(z=20, m_n=1.0, b=5.0))
    with pytest.raises(GeometryError):
        tooth_flank(geo, thickness_reduction=geo.s_t + 0.1)
