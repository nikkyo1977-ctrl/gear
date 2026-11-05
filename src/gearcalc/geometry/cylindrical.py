"""Geometria della singola ruota cilindrica esterna (ISO 21771:2007)."""

from __future__ import annotations

import math

from gearcalc.errors import GeometryError
from gearcalc.geometry.involute import inv
from gearcalc.models import CylindricalGear, GearGeometry


def transverse_pressure_angle(alpha_n_deg: float, beta_deg: float) -> float:
    """α_t [rad]: tan α_t = tan α_n / cos β."""
    return math.atan(math.tan(math.radians(alpha_n_deg)) / math.cos(math.radians(beta_deg)))


def x_min_undercut(gear: CylindricalGear) -> float:
    """Spostamento minimo senza sottosquadro per taglio con creatore (ISO 21771, §5.5).

    x_min = h_fP* − ρ_fP*·(1 − sin α_n) − z·sin²α_t / (2·cos β)

    Ipotesi: utensile creatore con addendum h_aP0* = h_fP* e raggio di testa ρ_aP0* = ρ_fP*,
    nessuna protuberanza. Per taglio con coltello stozzatore il limite è diverso.
    """
    a_n = math.radians(gear.rack.alpha_n)
    a_t = transverse_pressure_angle(gear.rack.alpha_n, gear.beta)
    beta = math.radians(gear.beta)
    r = gear.rack
    return (
        r.h_fP_star
        - r.rho_fP_star * (1.0 - math.sin(a_n))
        - gear.z * math.sin(a_t) ** 2 / (2.0 * math.cos(beta))
    )


def gear_geometry(gear: CylindricalGear, k: float = 0.0) -> GearGeometry:
    """Calcola la geometria nominale (senza tolleranze) della ruota.

    Args:
        gear: definizione della ruota.
        k: coefficiente di riduzione di testa (≤ 0), da :func:`pair_geometry`.

    Raises:
        GeometryError: se il diametro di testa non supera quello di base o se i dati
            non producono una geometria realizzabile.
    """
    if k > 1e-12:
        raise GeometryError(f"Il coefficiente di riduzione di testa k deve essere ≤ 0 (k={k})")

    m_n, z, x, r = gear.m_n, gear.z, gear.x, gear.rack
    beta = math.radians(gear.beta)
    a_n = math.radians(r.alpha_n)
    a_t = transverse_pressure_angle(r.alpha_n, gear.beta)
    cos_b = math.cos(beta)

    m_t = m_n / cos_b
    d = z * m_t
    d_b = d * math.cos(a_t)
    beta_b = math.asin(math.sin(beta) * math.cos(a_n))

    h_a = m_n * (r.h_aP_star + x + k)
    h_f = m_n * (r.h_fP_star - x)
    d_a = d + 2.0 * h_a
    d_f = d - 2.0 * h_f
    if d_f <= 0.0:
        raise GeometryError(f"Diametro di piede non positivo (d_f={d_f:.3f} mm)")
    if d_a <= d_b:
        raise GeometryError(f"d_a={d_a:.3f} ≤ d_b={d_b:.3f} mm: nessun fianco attivo")

    tan_an = math.tan(a_n)
    s_n = m_n * (math.pi / 2.0 + 2.0 * x * tan_an)
    s_t = m_t * (math.pi / 2.0 + 2.0 * x * tan_an)

    a_at = math.acos(d_b / d_a)
    s_at = d_a * (s_t / d + inv(a_t) - inv(a_at))
    beta_a = math.atan(math.tan(beta) * d_a / d)
    s_an = s_at * math.cos(beta_a)

    p_n = math.pi * m_n
    p_t = math.pi * m_t
    p_z = math.pi * d / math.tan(abs(beta)) if gear.beta != 0.0 else math.inf

    x_min = x_min_undercut(gear)

    return GearGeometry(
        z=z,
        m_n=m_n,
        m_t=m_t,
        alpha_n=r.alpha_n,
        alpha_t=math.degrees(a_t),
        beta=gear.beta,
        beta_b=math.degrees(beta_b),
        x=x,
        k=k,
        d=d,
        d_b=d_b,
        d_a=d_a,
        d_f=d_f,
        h_a=h_a,
        h_f=h_f,
        h=h_a + h_f,
        p_n=p_n,
        p_t=p_t,
        p_bt=p_t * math.cos(a_t),
        p_z=p_z,
        s_n=s_n,
        s_t=s_t,
        s_at=s_at,
        s_an=s_an,
        z_n=z / (math.cos(beta_b) ** 2 * cos_b),
        x_min_undercut=x_min,
        undercut=x < x_min - 1e-9,
    )
