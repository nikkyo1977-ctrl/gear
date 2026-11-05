"""Quote di controllo dello spessore e gioco tra i fianchi (ISO 21771, DIN 3960).

Gli scostamenti di spessore ``A_sne``/``A_sni`` sono input dell'utente: le tabelle della
DIN 3967 (serie di scostamento a…h, tolleranze 21…30) non sono incluse perché protette da
copyright; possono essere caricate come dati esterni in una fase successiva.
"""

from __future__ import annotations

import math

from scipy.optimize import brentq

from gearcalc.errors import GeometryError
from gearcalc.geometry.involute import inv, inv_inverse
from gearcalc.models import (
    Backlash,
    GearGeometry,
    PairGeometry,
    ThicknessAllowances,
    ToothMeasurement,
)


def span_teeth(geo: GearGeometry) -> int:
    """Numero di denti abbracciati k per contatto dei piattelli a metà altezza del dente.

    k = (z/π)·[tan α_Mt / cos²β_b − 2·x·tan α_n / z − inv α_t] + 0.5, con
    cos α_Mt = d_b / (d + 2·x·m_n)  (DIN 3960).
    """
    if geo.internal:
        raise GeometryError("La quota W_k non è misurabile sulle dentature interne")
    a_t = math.radians(geo.alpha_t)
    a_n = math.radians(geo.alpha_n)
    cos_bb = math.cos(math.radians(geo.beta_b))
    d_M = geo.d + 2.0 * geo.x * geo.m_n
    a_Mt = math.acos(min(geo.d_b / d_M, 1.0))
    k = (geo.z / math.pi) * (
        math.tan(a_Mt) / cos_bb**2 - 2.0 * geo.x * math.tan(a_n) / geo.z - inv(a_t)
    ) + 0.5
    return max(2, round(k))


def span_measurement(geo: GearGeometry, k: int, A_sn: float = 0.0) -> float:
    """Quota W_k su k denti, nel piano normale [mm].

    W_k = m_n·cos α_n·[π·(k − 0.5) + z·inv α_t] + 2·x·m_n·sin α_n + A_sn·cos α_n
    """
    a_n = math.radians(geo.alpha_n)
    a_t = math.radians(geo.alpha_t)
    return (
        geo.m_n * math.cos(a_n) * (math.pi * (k - 0.5) + geo.z * inv(a_t))
        + 2.0 * geo.x * geo.m_n * math.sin(a_n)
        + A_sn * math.cos(a_n)
    )


def _ball_center_angle(geo: GearGeometry, D_M: float, A_sn: float) -> float:
    """α_Mt [rad] del centro sfera (DIN 3960).

    esterne: inv α_Mt = inv α_t + s_n'/(m_n·z) + D_M/(m_n·z·cos α_n) − π/z
    interne: inv α_Mt = inv α_t + π/z − s_n'/(m_n·z) − D_M/(m_n·z·cos α_n)
    con s_n' = s_n + A_sn e z positivo.
    """
    z = abs(geo.z)
    a_t = math.radians(geo.alpha_t)
    a_n = math.radians(geo.alpha_n)
    s = geo.s_n + A_sn
    term = s / (geo.m_n * z) + D_M / (geo.m_n * z * math.cos(a_n)) - math.pi / z
    value = inv(a_t) - term if geo.internal else inv(a_t) + term
    if value <= 0.0:
        raise GeometryError(f"Sfera D_M = {D_M:.3f} mm non ammissibile per questa dentatura")
    return inv_inverse(value)


def _ball_contact_diameter(geo: GearGeometry, D_M: float, a_Mt: float) -> float:
    r_b = abs(geo.d_b) / 2.0
    half = D_M / (2.0 * math.cos(math.radians(geo.beta_b)))
    roll = r_b * math.tan(a_Mt) + (half if geo.internal else -half)
    return 2.0 * math.hypot(r_b, roll)


def over_balls(geo: GearGeometry, D_M: float, A_sn: float = 0.0) -> tuple[float, float]:
    """Quota su sfere (esterne) o tra sfere (interne) M_d e diametro di contatto [mm].

    Per z dispari: M_d = d_Mt·cos(π/2z) ± D_M. Per le elicoidali con z dispari la formula
    è l'approssimazione usuale della DIN 3960 (sfere non complanari).
    """
    a_Mt = _ball_center_angle(geo, D_M, A_sn)
    d_Mt = abs(geo.d_b) / math.cos(a_Mt)
    z = abs(geo.z)
    base = d_Mt if z % 2 == 0 else d_Mt * math.cos(math.pi / (2.0 * z))
    M = base - D_M if geo.internal else base + D_M
    return M, _ball_contact_diameter(geo, D_M, a_Mt)


def ideal_ball_diameter(geo: GearGeometry) -> float:
    """Diametro della sfera che tocca il fianco a metà altezza (|d| ± 2·x·m_n)."""
    target = abs(geo.d) + (-2.0 if geo.internal else 2.0) * geo.x * geo.m_n

    def f(D: float) -> float:
        a_Mt = _ball_center_angle(geo, D, 0.0)
        return _ball_contact_diameter(geo, D, a_Mt) - target

    # scansione 0.2…4·m_n fino al primo cambio di segno, poi Brent
    prev: tuple[float, float] | None = None
    for i in range(40):
        D = (0.2 + 0.1 * i) * geo.m_n
        try:
            v = f(D)
        except GeometryError:
            if prev is None:
                continue
            break
        if prev is not None and prev[1] * v <= 0.0:
            return float(brentq(f, prev[0], D, xtol=1e-9))
        prev = (D, v)
    raise GeometryError("Impossibile determinare il diametro ideale della sfera")


def tooth_measurement(
    geo: GearGeometry,
    allowances: ThicknessAllowances | None = None,
    *,
    k: int | None = None,
    D_M: float | None = None,
) -> ToothMeasurement:
    """Quote di controllo W_k e M_d con i relativi limiti di tolleranza.

    Args:
        geo: geometria della ruota.
        allowances: scostamenti di spessore normale (default: nulli).
        k: denti abbracciati (default: :func:`span_teeth`).
        D_M: diametro sfere (default: :func:`ideal_ball_diameter`, da arrotondare alla
            serie commerciale disponibile).
    """
    al = allowances or ThicknessAllowances()
    warnings: list[str] = []
    D = D_M if D_M is not None else ideal_ball_diameter(geo)

    M_nom, d_M = over_balls(geo, D)
    M_e, _ = over_balls(geo, D, al.A_sne)
    M_i, _ = over_balls(geo, D, al.A_sni)
    r_tip, r_root = abs(geo.d_a), geo.d_Ff if geo.d_Ff is not None else abs(geo.d_b)
    lo_d, hi_d = (r_tip, abs(geo.d_f)) if geo.internal else (r_root, r_tip)
    if not lo_d <= d_M <= hi_d:
        warnings.append(f"Sfera D_M = {D:.3f} mm: contatto fuori dal fianco (d = {d_M:.3f} mm)")
    if not geo.internal and M_nom <= abs(geo.d_a):
        warnings.append("La sfera non sporge dal diametro di testa: quota non misurabile")
    if geo.internal and M_nom >= abs(geo.d_a):
        warnings.append("La sfera non sporge dal diametro di testa della corona")

    kk: int | None = None
    W = W_max = W_min = d_Wk = None
    if not geo.internal:
        kk = k if k is not None else span_teeth(geo)
        W = span_measurement(geo, kk)
        W_max = span_measurement(geo, kk, al.A_sne)
        W_min = span_measurement(geo, kk, al.A_sni)
        cos_bb = math.cos(math.radians(geo.beta_b))
        d_Wk = 2.0 * math.hypot(geo.d_b / 2.0, W / (2.0 * cos_bb))
        lo = geo.d_Ff if geo.d_Ff is not None else geo.d_b
        if not lo <= d_Wk <= geo.d_a:
            warnings.append(f"W_{kk}: contatto dei piattelli fuori dal fianco (d = {d_Wk:.3f} mm)")
        b_min = W * math.sin(math.radians(abs(geo.beta_b)))
        if geo.b <= b_min:
            warnings.append(f"W_{kk} non misurabile: b = {geo.b} mm ≤ W_k·sin β_b = {b_min:.2f} mm")

    return ToothMeasurement(
        k=kk,
        W_k=W,
        W_k_max=W_max,
        W_k_min=W_min,
        d_Wk=d_Wk,
        D_M=D,
        M_d=M_nom,
        M_d_max=max(M_e, M_i),
        M_d_min=min(M_e, M_i),
        d_M=d_M,
        warnings=tuple(warnings),
    )


def backlash(
    pair: PairGeometry,
    allowances1: ThicknessAllowances,
    allowances2: ThicknessAllowances,
    A_ae: float = 0.0,
    A_ai: float = 0.0,
) -> Backlash:
    """Gioco tra i fianchi da scostamenti di spessore e di interasse (ISO 21771).

    Lungo la retta d'azione: j_bt = −(A_st1 + A_st2)·cos α_t ± 2·A_a·sin α_wt
    (+ per coppia esterna, − per interna), con A_st = A_sn / cos β.
    Circonferenziale al primitivo di lavoro j_wt = j_bt / cos α_wt; normale j_bn = j_bt·cos β_b.
    ``A_ae``/``A_ai``: scostamenti superiore/inferiore dell'interasse |a_w| [mm].
    Non include deformazioni, dilatazioni termiche né errori di forma (che riducono il gioco).
    """
    if A_ai > A_ae:
        raise GeometryError("A_ai deve essere ≤ A_ae")
    g1 = pair.gear1
    a_t = math.radians(g1.alpha_t)
    a_wt = math.radians(pair.alpha_wt)
    cos_b = math.cos(math.radians(g1.beta))
    cos_bb = math.cos(math.radians(g1.beta_b))
    sign = -1.0 if pair.internal else 1.0

    def j_bt(As1: float, As2: float, Aa: float) -> float:
        return -(As1 + As2) / cos_b * math.cos(a_t) + sign * 2.0 * Aa * math.sin(a_wt)

    a_min, a_max = (A_ae, A_ai) if pair.internal else (A_ai, A_ae)
    jmin = j_bt(allowances1.A_sne, allowances2.A_sne, a_min)
    jmax = j_bt(allowances1.A_sni, allowances2.A_sni, a_max)
    warnings: tuple[str, ...] = ()
    if jmin < 0.0:
        warnings = ("Gioco minimo negativo: rischio di bloccaggio della coppia",)
    return Backlash(
        j_wt_min=jmin / math.cos(a_wt),
        j_wt_max=jmax / math.cos(a_wt),
        j_bn_min=jmin * cos_bb,
        j_bn_max=jmax * cos_bb,
        warnings=warnings,
    )
