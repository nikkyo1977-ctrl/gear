"""Profilo generato da creatore: confronto con l'evolvente analitica e con d_Ff ISO 21771."""

import math

import numpy as np
import pytest

from gearcalc import CylindricalGear, gear_geometry, gear_profile
from gearcalc.geometry import form_diameter_hob, inv, tooth_flank

CASES = [
    CylindricalGear(z=20, m_n=2.0, b=10.0),
    CylindricalGear(z=14, m_n=0.5, b=4.0, beta=18.0, x=0.4),
    CylindricalGear(z=40, m_n=1.0, b=4.0, beta=30.0, x=-0.3),
    CylindricalGear(z=10, m_n=1.0, b=4.0),  # sottosquadro
]


def _polar(flank: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.hypot(flank[:, 0], flank[:, 1]), -np.arctan2(flank[:, 1], flank[:, 0])


@pytest.mark.parametrize("gear", CASES)
def test_generated_flank_is_exact_involute(gear: CylindricalGear) -> None:
    geo = gear_geometry(gear)
    assert geo.d_Ff is not None
    R, ang = _polar(tooth_flank(geo, n_flank=200, n_fillet=60))
    above = geo.d_Ff / 2.0 + 1e-6 < R
    a_y = np.arccos(np.minimum(geo.d_b / (2.0 * R[above]), 1.0))
    psi = geo.s_t / geo.d + inv(math.radians(geo.alpha_t)) - (np.tan(a_y) - a_y)
    assert np.max(np.abs(ang[above] - psi) * R[above]) < 1e-9  # mm
    assert R.min() == pytest.approx(geo.d_f / 2.0, abs=1e-9)
    assert R.max() == pytest.approx(geo.d_a / 2.0, abs=1e-9)


@pytest.mark.parametrize("gear", CASES[:3])
def test_form_diameter_matches_envelope(gear: CylindricalGear) -> None:
    geo = gear_geometry(gear)
    d_Ff = form_diameter_hob(gear, geo.d, geo.d_b)
    fl = tooth_flank(geo, n_flank=10, n_fillet=50)
    # l'ultimo punto del raccordo (indice n_fillet-1) è il punto di tangenza utensile
    assert d_Ff == pytest.approx(2.0 * math.hypot(*fl[49]), rel=1e-12)


def test_undercut_form_diameter() -> None:
    geo = gear_geometry(CylindricalGear(z=10, m_n=1.0, b=4.0))
    assert geo.undercut
    assert geo.d_Ff is not None
    assert geo.d_b < geo.d_Ff < geo.d
    # senza sottosquadro (x sufficiente) d_Ff torna dalla formula chiusa
    geo2 = gear_geometry(CylindricalGear(z=10, m_n=1.0, b=4.0, x=0.45))
    assert not geo2.undercut


def test_fillet_is_tangent_continuous() -> None:
    geo = gear_geometry(CylindricalGear(z=25, m_n=1.0, b=4.0, x=0.1))
    fl = tooth_flank(geo, n_flank=400, n_fillet=400)
    d = np.diff(fl, axis=0)
    ang = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    assert np.max(np.abs(np.diff(ang))) < 0.02  # nessuno spigolo alla giunzione


@pytest.mark.parametrize(
    "gear",
    [
        CylindricalGear(z=60, m_n=1.0, b=10.0, internal=True),
        CylindricalGear(z=52, m_n=1.0, b=10.0, beta=12.0, x=0.2, internal=True),
    ],
)
def test_internal_profile(gear: CylindricalGear) -> None:
    geo = gear_geometry(gear)
    pts = gear_profile(geo)
    R = np.hypot(pts[:, 0], pts[:, 1])
    assert R.min() == pytest.approx(abs(geo.d_a) / 2.0)
    assert R.max() == pytest.approx(abs(geo.d_f) / 2.0)
    ang = np.unwrap(np.arctan2(pts[:, 1], pts[:, 0]))
    assert np.all(np.diff(ang) >= -1e-12)
    # spessore al primitivo del dente della corona
    R_f, a_f = _polar(tooth_flank(geo, n_flank=4001))
    i = int(np.argmin(np.abs(R_f - abs(geo.d) / 2.0)))
    assert 2.0 * a_f[i] * abs(geo.d) / 2.0 == pytest.approx(geo.s_t, abs=2e-3)
