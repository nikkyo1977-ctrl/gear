"""Geometria della coppia cilindrica, esterna o interna (ISO 21771:2007).

Le grandezze con segno seguono ISO 21771: per la coppia interna z2, d2, d_b2, a_d e a_w
sono negativi, e le formule restano formalmente le stesse della coppia esterna.
"""

from __future__ import annotations

import itertools
import math

from scipy.optimize import brentq

from gearcalc.errors import GeometryError
from gearcalc.geometry.cylindrical import gear_geometry, transverse_pressure_angle
from gearcalc.geometry.involute import inv, inv_inverse
from gearcalc.models import CylindricalGear, GearPair, PairGeometry, ShiftDistribution

#: Rapporto di condotta trasversale minimo consigliato (sotto 1.1 la continuità del moto
#: è compromessa dalle tolleranze di passo e dalle deformazioni).
EPSILON_ALPHA_MIN = 1.1
#: Spessore normale minimo in testa riferito al modulo (valore usuale per ruote bonificate;
#: per ruote cementate si adotta ~0.4).
S_AN_MIN_STAR = 0.2
#: Differenza minima di denti nelle coppie interne per evitare l'interferenza trocoidale
#: con profilo di riferimento standard (regola pratica; verifica completa in fase successiva).
INTERNAL_DZ_MIN = 10


def _signed_z(g: CylindricalGear) -> int:
    return -g.z if g.internal else g.z


def working_pressure_angle(pair: GearPair) -> float:
    """α_wt [rad] da inv α_wt = inv α_t + 2·(x1+x2)·tan α_n / (z1+z2)  (z2 < 0 se interna)."""
    g1, g2 = pair.gear1, pair.gear2
    a_n = math.radians(g1.rack.alpha_n)
    a_t = transverse_pressure_angle(g1.rack.alpha_n, g1.beta)
    value = inv(a_t) + 2.0 * (g1.x + g2.x) * math.tan(a_n) / (_signed_z(g1) + _signed_z(g2))
    return inv_inverse(value)


def _sliding(rho1: float, rho2: float, u_abs: float) -> tuple[float, float]:
    """Strisciamenti specifici ζ1 = 1 − ρ2/(|u|·ρ1), ζ2 = 1 − |u|·ρ1/ρ2 (ρ: curvature locali)."""
    if rho1 <= 0.0 or rho2 <= 0.0:
        return -math.inf, -math.inf
    return 1.0 - rho2 / (u_abs * rho1), 1.0 - u_abs * rho1 / rho2


def pair_geometry(pair: GearPair) -> PairGeometry:
    """Geometria di ingranamento: interasse di lavoro, α_wt, condotta, d_Nf, strisciamenti."""
    g1, g2 = pair.gear1, pair.gear2
    internal = g2.internal
    m_n = g1.m_n
    a_t = transverse_pressure_angle(g1.rack.alpha_n, g1.beta)
    a_wt = working_pressure_angle(pair)

    geo1, geo2 = gear_geometry(g1), gear_geometry(g2)
    a_d = (geo1.d + geo2.d) / 2.0
    a_w = a_d * math.cos(a_t) / math.cos(a_wt)
    x_sum = g1.x + g2.x
    y = (a_w - a_d) / m_n
    k = 0.0 if internal else min(y - x_sum, 0.0)
    if pair.tip_shortening and k < 0.0:
        geo1, geo2 = gear_geometry(g1, k=k), gear_geometry(g2, k=k)

    tan_wt = math.tan(a_wt)
    r_b1, r_b2 = geo1.d_b / 2.0, geo2.d_b / 2.0
    r_a1, r_a2 = geo1.d_a / 2.0, geo2.d_a / 2.0
    # tratti della retta d'azione oltre il punto primitivo C (ISO 21771, con segno)
    g_a1 = math.sqrt(r_a1**2 - r_b1**2) - r_b1 * tan_wt
    g_a2 = math.copysign(math.sqrt(r_a2**2 - r_b2**2), r_b2) - r_b2 * tan_wt
    g_alpha = g_a1 + g_a2
    if g_alpha <= 0.0:
        raise GeometryError("Segmento di contatto nullo: le ruote non ingranano")

    epsilon_alpha = g_alpha / geo1.p_bt
    b_eff = min(g1.b, g2.b)
    epsilon_beta = b_eff * math.sin(math.radians(abs(g1.beta))) / (math.pi * m_n)

    # raggi di curvatura trasversali agli estremi del segmento di contatto
    # A: inizio (piede del pignone, testa della ruota) - E: fine (testa del pignone)
    rho1_A = r_b1 * tan_wt - g_a2
    rho1_E = r_b1 * tan_wt + g_a1
    T = (r_b1 + r_b2) * tan_wt  # T1T2 con segno (negativo se interna)
    rho2_A = (rho1_A - T) if internal else (T - rho1_A)
    rho2_E = (rho1_E - T) if internal else (T - rho1_E)
    u_abs = abs(geo2.z / geo1.z)
    zeta_A1, _ = _sliding(rho1_A, rho2_A, u_abs)
    _, zeta_E2 = _sliding(rho1_E, rho2_E, u_abs)

    d_Nf1 = 2.0 * math.hypot(r_b1, rho1_A)
    d_Nf2 = math.copysign(2.0 * math.hypot(r_b2, rho2_E), r_b2)

    warnings: list[str] = []
    if epsilon_alpha < 1.0:
        warnings.append(f"ε_α = {epsilon_alpha:.3f} < 1: trasmissione non continua")
    elif epsilon_alpha < EPSILON_ALPHA_MIN:
        warnings.append(f"ε_α = {epsilon_alpha:.3f} < {EPSILON_ALPHA_MIN}: condotta insufficiente")
    if rho1_A < 0.0:
        warnings.append("Interferenza: la testa della ruota 2 scava il piede della ruota 1")
    if not internal and rho2_E < 0.0:
        warnings.append("Interferenza: la testa della ruota 1 scava il piede della ruota 2")
    for i, geo, d_Nf in ((1, geo1, d_Nf1), (2, geo2, d_Nf2)):
        if geo.undercut:
            warnings.append(
                f"Ruota {i}: sottosquadro (x = {geo.x:.3f} < x_min = {geo.x_min_undercut:.3f})"
            )
        if geo.d_Ff is not None and d_Nf < geo.d_Ff - 1e-9:
            warnings.append(
                f"Ruota {i}: il contatto inizia sul raccordo (d_Nf = {d_Nf:.3f} < "
                f"d_Ff = {geo.d_Ff:.3f} mm)"
            )
        if geo.s_an < S_AN_MIN_STAR * m_n:
            warnings.append(
                f"Ruota {i}: spessore in testa s_an = {geo.s_an:.3f} mm < {S_AN_MIN_STAR}·m_n"
            )
    if k < -0.05 and not pair.tip_shortening:
        warnings.append(
            f"Gioco di testa ridotto di {-k * m_n:.3f} mm: valutare riduzione di testa (k={k:.3f})"
        )
    if internal:
        if g2.z - g1.z < INTERNAL_DZ_MIN:
            warnings.append(
                f"Coppia interna con z2 − z1 = {g2.z - g1.z} < {INTERNAL_DZ_MIN}: "
                "rischio di interferenza trocoidale in montaggio/funzionamento"
            )
        warnings.append(
            "Coppia interna: d_Ff della corona non calcolato (dipende dal coltello stozzatore)"
        )

    return PairGeometry(
        gear1=geo1,
        gear2=geo2,
        internal=internal,
        u=geo2.z / geo1.z,
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
        d_Nf1=d_Nf1,
        d_Nf2=d_Nf2,
        zeta_A1=zeta_A1,
        zeta_E2=zeta_E2,
        warnings=tuple(warnings),
    )


def x_sum_for_center_distance(
    a_w: float,
    z1: int,
    z2: int,
    m_n: float,
    alpha_n: float = 20.0,
    beta: float = 0.0,
    *,
    internal: bool = False,
) -> float:
    """Somma degli spostamenti x1+x2 che realizza l'interasse di lavoro.

    cos α_wt = a_d·cos α_t / a_w ;  x1+x2 = (inv α_wt − inv α_t)·(z1+z2) / (2·tan α_n)

    ``a_w`` e ``z2`` si danno positivi anche per la coppia interna (``internal=True``).
    """
    z2s = -z2 if internal else z2
    a_t = transverse_pressure_angle(alpha_n, beta)
    a_d = m_n * (z1 + z2s) / (2.0 * math.cos(math.radians(beta)))
    a_w_s = -abs(a_w) if internal else a_w
    cos_awt = a_d * math.cos(a_t) / a_w_s
    if not 0.0 < cos_awt < 1.0:
        raise GeometryError(
            f"Interasse a_w = {abs(a_w):.4f} mm non realizzabile "
            f"(interasse di riferimento {abs(a_d):.4f} mm)"
        )
    a_wt = math.acos(cos_awt)
    return (inv(a_wt) - inv(a_t)) * (z1 + z2s) / (2.0 * math.tan(math.radians(alpha_n)))


def _with_x(g: CylindricalGear, x: float) -> CylindricalGear:
    return CylindricalGear.model_validate(g.model_dump() | {"x": x})


def balanced_sliding_x1(
    gear1: CylindricalGear, gear2: CylindricalGear, x_sum: float, *, tip_shortening: bool = False
) -> float:
    """x1 che, a Σx fissata, rende uguali gli strisciamenti specifici |ζ_A1| = |ζ_E2|.

    Scansione di x1 ∈ [−1, 1.5] a passo 0.05 e raffinamento con Brent sul primo cambio di
    segno. Le configurazioni non realizzabili (d_a ≤ d_b, interferenza) vengono saltate.
    """

    def f(x1: float) -> float:
        p = GearPair(
            gear1=_with_x(gear1, x1),
            gear2=_with_x(gear2, x_sum - x1),
            tip_shortening=tip_shortening,
        )
        geo = pair_geometry(p)
        return abs(geo.zeta_A1) - abs(geo.zeta_E2)

    vals: list[tuple[float, float]] = []
    for i in range(-20, 31):
        x1 = i / 20.0
        try:
            v = f(x1)
        except (GeometryError, ValueError):
            continue
        if math.isfinite(v):
            vals.append((x1, v))
    for (xa, fa), (xb, fb) in itertools.pairwise(vals):
        if fa == 0.0:
            return xa
        if fa * fb < 0.0:
            return float(brentq(f, xa, xb, xtol=1e-10))
    raise GeometryError("Nessuna ripartizione di Σx bilancia gli strisciamenti specifici")


def pair_for_center_distance(
    a_w: float,
    gear1: CylindricalGear,
    gear2: CylindricalGear,
    x1: float | None = None,
    *,
    distribution: ShiftDistribution = ShiftDistribution.EQUAL,
    tip_shortening: bool = False,
) -> GearPair:
    """Costruisce la coppia con gli spostamenti che realizzano l'interasse imposto |a_w|.

    Se ``x1`` è dato, x2 = Σx − x1; altrimenti Σx è ripartita secondo ``distribution``.
    Gli ``x`` presenti in ``gear1``/``gear2`` vengono ignorati.
    """
    x_sum = x_sum_for_center_distance(
        a_w,
        gear1.z,
        gear2.z,
        gear1.m_n,
        gear1.rack.alpha_n,
        gear1.beta,
        internal=gear2.internal,
    )
    if x1 is not None:
        x1_val = x1
    elif distribution is ShiftDistribution.BALANCED_SLIDING:
        x1_val = balanced_sliding_x1(gear1, gear2, x_sum, tip_shortening=tip_shortening)
    else:
        x1_val = x_sum / 2.0
    return GearPair(
        gear1=_with_x(gear1, x1_val),
        gear2=_with_x(gear2, x_sum - x1_val),
        tip_shortening=tip_shortening,
    )
