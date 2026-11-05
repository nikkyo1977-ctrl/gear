"""Geometria della coppia cilindrica esterna (ISO 21771:2007)."""

from __future__ import annotations

import math

from gearcalc.errors import GeometryError
from gearcalc.geometry.cylindrical import gear_geometry, transverse_pressure_angle
from gearcalc.geometry.involute import inv, inv_inverse
from gearcalc.models import CylindricalGear, GearPair, PairGeometry

#: Rapporto di condotta trasversale minimo consigliato (sotto 1.1 la continuità del moto
#: è compromessa dalle tolleranze di passo e dalle deformazioni).
EPSILON_ALPHA_MIN = 1.1
#: Spessore normale minimo in testa riferito al modulo (valore usuale per ruote bonificate;
#: per ruote cementate si adotta ~0.4).
S_AN_MIN_STAR = 0.2


def working_pressure_angle(pair: GearPair) -> float:
    """α_wt [rad] da inv α_wt = inv α_t + 2·(x1+x2)·tan α_n / (z1+z2)."""
    g1, g2 = pair.gear1, pair.gear2
    a_n = math.radians(g1.rack.alpha_n)
    a_t = transverse_pressure_angle(g1.rack.alpha_n, g1.beta)
    value = inv(a_t) + 2.0 * (g1.x + g2.x) * math.tan(a_n) / (g1.z + g2.z)
    return inv_inverse(value)


def pair_geometry(pair: GearPair) -> PairGeometry:
    """Geometria di ingranamento: interasse di lavoro, α_wt, rapporti di condotta, verifiche."""
    g1, g2 = pair.gear1, pair.gear2
    m_n = g1.m_n
    a_t = transverse_pressure_angle(g1.rack.alpha_n, g1.beta)
    a_wt = working_pressure_angle(pair)

    # geometria senza riduzione di testa, per ricavare a_d e k
    geo1, geo2 = gear_geometry(g1), gear_geometry(g2)
    a_d = (geo1.d + geo2.d) / 2.0
    a_w = a_d * math.cos(a_t) / math.cos(a_wt)
    x_sum = g1.x + g2.x
    y = (a_w - a_d) / m_n
    k = min(y - x_sum, 0.0)

    if pair.tip_shortening and k < 0.0:
        geo1, geo2 = gear_geometry(g1, k=k), gear_geometry(g2, k=k)

    r_b1, r_b2 = geo1.d_b / 2.0, geo2.d_b / 2.0
    r_a1, r_a2 = geo1.d_a / 2.0, geo2.d_a / 2.0
    g_a1 = math.sqrt(r_a1**2 - r_b1**2)  # dal punto T1 al punto di fine contatto
    g_a2 = math.sqrt(r_a2**2 - r_b2**2)
    T1T2 = a_w * math.sin(a_wt)  # lunghezza della retta d'azione tra i punti di tangenza
    g_alpha = g_a1 + g_a2 - T1T2
    if g_alpha <= 0.0:
        raise GeometryError("Segmento di contatto nullo: le ruote non ingranano")

    epsilon_alpha = g_alpha / geo1.p_bt
    b_eff = min(g1.b, g2.b)
    epsilon_beta = b_eff * math.sin(math.radians(abs(g1.beta))) / (math.pi * m_n)

    warnings: list[str] = []
    if epsilon_alpha < 1.0:
        warnings.append(f"ε_α = {epsilon_alpha:.3f} < 1: trasmissione non continua")
    elif epsilon_alpha < EPSILON_ALPHA_MIN:
        warnings.append(f"ε_α = {epsilon_alpha:.3f} < {EPSILON_ALPHA_MIN}: condotta insufficiente")
    # interferenza: la testa della controruota non deve oltrepassare il punto di tangenza
    if g_a2 > T1T2:
        warnings.append("Interferenza: la testa della ruota 2 scava il piede della ruota 1")
    if g_a1 > T1T2:
        warnings.append("Interferenza: la testa della ruota 1 scava il piede della ruota 2")
    for i, geo in ((1, geo1), (2, geo2)):
        if geo.undercut:
            warnings.append(
                f"Ruota {i}: sottosquadro (x = {geo.x:.3f} < x_min = {geo.x_min_undercut:.3f})"
            )
        if geo.s_an < S_AN_MIN_STAR * m_n:
            warnings.append(
                f"Ruota {i}: spessore in testa s_an = {geo.s_an:.3f} mm < {S_AN_MIN_STAR}·m_n"
            )
    if k < -0.05 and not pair.tip_shortening:
        warnings.append(
            f"Gioco di testa ridotto di {-k * m_n:.3f} mm: valutare riduzione di testa (k={k:.3f})"
        )

    return PairGeometry(
        gear1=geo1,
        gear2=geo2,
        u=g2.z / g1.z,
        a_d=a_d,
        a_w=a_w,
        alpha_wt=math.degrees(a_wt),
        x_sum=x_sum,
        y=y,
        k=k,
        g_alpha=g_alpha,
        epsilon_alpha=epsilon_alpha,
        epsilon_beta=epsilon_beta,
        epsilon_gamma=epsilon_alpha + epsilon_beta,
        b_eff=b_eff,
        warnings=tuple(warnings),
    )


def x_sum_for_center_distance(
    a_w: float, z1: int, z2: int, m_n: float, alpha_n: float = 20.0, beta: float = 0.0
) -> float:
    """Somma degli spostamenti x1+x2 che realizza l'interasse di lavoro a_w.

    cos α_wt = a_d·cos α_t / a_w ;  x1+x2 = (inv α_wt − inv α_t)·(z1+z2) / (2·tan α_n)
    """
    a_t = transverse_pressure_angle(alpha_n, beta)
    a_d = m_n * (z1 + z2) / (2.0 * math.cos(math.radians(beta)))
    cos_awt = a_d * math.cos(a_t) / a_w
    if not 0.0 < cos_awt < 1.0:
        raise GeometryError(
            f"Interasse a_w = {a_w:.4f} mm non realizzabile (interasse di riferimento {a_d:.4f} mm)"
        )
    a_wt = math.acos(cos_awt)
    return (inv(a_wt) - inv(a_t)) * (z1 + z2) / (2.0 * math.tan(math.radians(alpha_n)))


def pair_for_center_distance(
    a_w: float,
    gear1: CylindricalGear,
    gear2: CylindricalGear,
    x1: float | None = None,
    *,
    tip_shortening: bool = False,
) -> GearPair:
    """Costruisce la coppia con gli spostamenti che realizzano l'interasse imposto.

    Se ``x1`` è None la somma è ripartita in parti uguali; altrimenti x2 = Σx − x1.
    Gli ``x`` presenti in ``gear1``/``gear2`` vengono ignorati.
    """
    x_sum = x_sum_for_center_distance(
        a_w, gear1.z, gear2.z, gear1.m_n, gear1.rack.alpha_n, gear1.beta
    )
    x1_val = x_sum / 2.0 if x1 is None else x1
    return GearPair(
        gear1=CylindricalGear.model_validate(gear1.model_dump() | {"x": x1_val}),
        gear2=CylindricalGear.model_validate(gear2.model_dump() | {"x": x_sum - x1_val}),
        tip_shortening=tip_shortening,
    )
