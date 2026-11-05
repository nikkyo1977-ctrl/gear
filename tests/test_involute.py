import math

import pytest

from gearcalc.errors import GeometryError
from gearcalc.geometry.involute import inv, inv_inverse, involute_xy


def test_inv_20deg() -> None:
    assert inv(math.radians(20.0)) == pytest.approx(0.014904383867336446, rel=1e-12)


@pytest.mark.parametrize("deg", [0.5, 5.0, 14.5, 20.0, 25.0, 35.0, 50.0, 70.0])
def test_inv_roundtrip(deg: float) -> None:
    a = math.radians(deg)
    assert inv_inverse(inv(a)) == pytest.approx(a, rel=1e-12)


def test_inv_inverse_zero_and_negative() -> None:
    assert inv_inverse(0.0) == 0.0
    with pytest.raises(GeometryError):
        inv_inverse(-1e-3)


def test_involute_point_radius() -> None:
    r_b, t = 10.0, 0.7
    x, y = involute_xy(r_b, t)
    assert math.hypot(x, y) == pytest.approx(r_b * math.sqrt(1 + t * t))
