import math

import numpy as np
import pytest

from gearcalc import CylindricalGear, gear_geometry
from gearcalc.geometry import gear_outline


def _sample(outline) -> np.ndarray:  # type: ignore[no-untyped-def]
    pts: list[tuple[float, float]] = []
    for s in outline.segments:
        if s.kind == "spline":
            pts.extend(s.points[:-1])
        else:
            for a in np.linspace(s.a0, s.a1, 40)[:-1]:
                pts.append((s.r * math.cos(a), s.r * math.sin(a)))
    return np.array(pts)


@pytest.mark.parametrize(
    "gear",
    [
        CylindricalGear(z=20, m_n=2.0, b=10.0),
        CylindricalGear(z=10, m_n=1.0, b=5.0),  # sottosquadro: due spline per fianco
        CylindricalGear(z=45, m_n=1.0, b=10.0, x=0.3),
        CylindricalGear(z=60, m_n=1.0, b=10.0, x=0.2, internal=True),
    ],
)
def test_outline_closed_and_consistent(gear: CylindricalGear) -> None:
    geo = gear_geometry(gear)
    o = gear_outline(geo)
    segs = o.segments
    for a, b in zip(segs, segs[1:] + segs[:1], strict=True):
        assert a.p1 == pytest.approx(b.p0, abs=1e-12)
    per_flank = 2 if geo.undercut else 1
    assert sum(s.kind == "spline" for s in segs) == 2 * per_flank * gear.z
    for s in segs:
        if s.kind == "arc":
            assert s.a1 > s.a0
            for p, a in ((s.p0, s.a0), (s.p1, s.a1)):
                assert math.hypot(*p) == pytest.approx(s.r, abs=1e-9)
                assert p == pytest.approx((s.r * math.cos(a), s.r * math.sin(a)), abs=1e-9)
        else:
            assert s.points[0] == s.p0 and s.points[-1] == s.p1
    pts = _sample(o)
    x, y = pts[:, 0], pts[:, 1]
    area = 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)
    assert area == pytest.approx(o.area, rel=2e-3)
    assert (
        math.pi * o.r_f**2 * (1 if not geo.internal else 0)
        < o.area
        < math.pi * max(o.r_a, o.r_f) ** 2
    )
