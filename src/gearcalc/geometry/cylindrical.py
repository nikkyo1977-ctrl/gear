"""Geometria della singola ruota cilindrica, esterna o interna (ISO 21771:2007)."""

from __future__ import annotations

import math

from gearcalc.errors import GeometryError
from gearcalc.geometry.involute import inv
from gearcalc.models import CylindricalGear, GearGeometry


def transverse_pressure_angle(alpha_n_deg: float, beta_deg: float) -> float:
    """α_t [rad]: tan α_t = tan α_n / cos β."""
    return math.atan(math.tan(math.radians(alpha_n_deg)) / math.cos(math.radians(beta_deg)))


def x_min_undercut(gear: CylindricalGear) -> float:
    """Spostamento minimo senza sottosquadro per taglio con creatore (ISO 21771).

    x_min = h_fP* − ρ_fP*·(1 − sin α_n) − z·sin²α_t / (2·cos β)

    Ipotesi: creatore con addendum h_aP0* = h_fP* e raggio di testa ρ_aP0* = ρ_fP*, senza
    protuberanza. È la condizione per cui il punto di tangenza tra fianco rettilineo e
    raccordo dell'utensile genera il fianco esattamente sul cerchio di base.
    """
    if gear.internal:
        raise GeometryError("Il limite di sottosquadro da creatore non si applica alle interne")
    a_n = math.radians(gear.rack.alpha_n)
    a_t = transverse_pressure_angle(gear.rack.alpha_n, gear.beta)
    r = gear.rack
    return (
        r.h_fP_star
        - r.rho_fP_star * (1.0 - math.sin(a_n))
        - gear.z * math.sin(a_t) ** 2 / (2.0 * math.cos(math.radians(gear.beta)))
    )


def form_diameter_hob(gear: CylindricalGear, d: float, d_b: float) -> float | None:
    """Diametro di forma al piede d_Ff per taglio con creatore (ISO 21771).

    d_Ff = √( d_b² + [d·sin α_t − 2·(h_aP0 − x·m_n − ρ_aP0·(1 − sin α_n)) / sin α_t]² )

    Restituisce None in caso di sottosquadro (termine in parentesi quadre negativo): il
    fianco ad evolvente è allora intaccato dalla trocoide e d_Ff va determinato
    dall'intersezione tra trocoide ed evolvente (vedi :mod:`gearcalc.geometry.profile`).
    """
    m_n, r = gear.m_n, gear.rack
    a_n = math.radians(r.alpha_n)
    a_t = transverse_pressure_angle(r.alpha_n, gear.beta)
    h = m_n * (r.h_fP_star - gear.x - r.rho_fP_star * (1.0 - math.sin(a_n)))
    term = d * math.sin(a_t) - 2.0 * h / math.sin(a_t)
    if term < 0.0:
        return None
    return math.sqrt(d_b**2 + term**2)


def gear_geometry(gear: CylindricalGear, k: float = 0.0) -> GearGeometry:
    """Calcola la geometria nominale (senza tolleranze) della ruota.

    Args:
        gear: definizione della ruota.
        k: coefficiente di riduzione di testa (≤ 0, solo esterne), da :func:`pair_geometry`.

    Raises:
        GeometryError: se il diametro di testa non supera quello di base o se i dati
            non producono una geometria realizzabile.
    """
    if k > 1e-12:
        raise GeometryError(f"Il coefficiente di riduzione di testa k deve essere ≤ 0 (k={k})")
    if gear.internal and k != 0.0:
        raise GeometryError("La riduzione di testa non si applica alle ruote interne")

    m_n, x, r = gear.m_n, gear.x, gear.rack
    z = -gear.z if gear.internal else gear.z  # convenzione ISO 21771
    beta = math.radians(gear.beta)
    a_n = math.radians(r.alpha_n)
    a_t = transverse_pressure_angle(r.alpha_n, gear.beta)
    cos_b = math.cos(beta)

    m_t = m_n / cos_b
    d = z * m_t
    d_b = d * math.cos(a_t)
    beta_b = math.asin(math.sin(beta) * math.cos(a_n))

    # ISO 21771: d_a = d + 2·h_a, d_f = d − 2·h_f, validi con segno anche per le interne
    h_a = m_n * (r.h_aP_star + x + k)
    h_f = m_n * (r.h_fP_star - x)
    d_a = d + 2.0 * h_a
    d_f = d - 2.0 * h_f
    if not gear.internal and d_f <= 0.0:
        raise GeometryError(f"Diametro di piede non positivo (d_f={d_f:.3f} mm)")
    if abs(d_a) <= abs(d_b):
        raise GeometryError(f"|d_a|={abs(d_a):.3f} ≤ |d_b|={abs(d_b):.3f} mm: nessun fianco attivo")

    tan_an = math.tan(a_n)
    s_n = m_n * (math.pi / 2.0 + 2.0 * x * tan_an)
    s_t = m_t * (math.pi / 2.0 + 2.0 * x * tan_an)

    a_at = math.acos(d_b / d_a)
    if gear.internal:
        # il dente della corona si assottiglia verso l'interno (verso la testa)
        s_at = abs(d_a) * (s_t / abs(d) - inv(a_t) + inv(a_at))
    else:
        s_at = d_a * (s_t / d + inv(a_t) - inv(a_at))
    beta_a = math.atan(math.tan(beta) * d_a / d)
    s_an = s_at * math.cos(beta_a)

    p_n = math.pi * m_n
    p_t = math.pi * m_t
    p_z = math.pi * abs(d) / math.tan(abs(beta)) if gear.beta != 0.0 else math.inf

    x_min = None if gear.internal else x_min_undercut(gear)
    d_Ff = None if gear.internal else form_diameter_hob(gear, d, d_b)

    geo = GearGeometry(
        z=z,
        internal=gear.internal,
        rack=r,
        m_n=m_n,
        m_t=m_t,
        alpha_n=r.alpha_n,
        alpha_t=math.degrees(a_t),
        beta=gear.beta,
        beta_b=math.degrees(beta_b),
        b=gear.b,
        x=x,
        k=k,
        d=d,
        d_b=d_b,
        d_a=d_a,
        d_f=d_f,
        d_Ff=d_Ff,
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
        z_n=abs(z) / (math.cos(beta_b) ** 2 * cos_b),
        x_min_undercut=x_min,
        # equivalente a x < x_min: il termine di d_Ff si annulla esattamente per x = x_min
        undercut=not gear.internal and d_Ff is None,
    )
    if geo.undercut:
        from gearcalc.geometry.profile import undercut_form_diameter

        geo = geo.model_copy(update={"d_Ff": undercut_form_diameter(geo)})
    return geo
