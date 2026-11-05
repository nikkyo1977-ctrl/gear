"""Profilo trasversale 2D della ruota (punti per spline/polilinea in CATIA).

**Ruote esterne** — profilo generato da creatore: inviluppo esatto, nella sezione
trasversale, della dentiera-utensile (profilo di riferimento ISO 53 con raggio di testa
ρ_aP0 = ρ_fP). Ogni punto dell'utensile genera il punto della ruota quando la sua normale
passa per il centro istantaneo di rotolamento (equazione d'ingranamento). Il risultato
comprende la trocoide di raccordo al piede e l'eventuale sottosquadro; il fianco ottenuto
coincide con l'evolvente analitica (verificato nei test).

Per le elicoidali la dentiera è trasformata nel piano trasversale (ascisse divise per cos β);
il raggio di testa diventa un'ellisse. Il risultato è esatto per la sezione trasversale.

**Ruote interne** — evolvente analitica tra |d_a| e |d_f| e arco sul cerchio di piede:
il raccordo generato dal coltello stozzatore non è ancora modellato.

Riduzione di spessore (gioco): applicata come allargamento tangenziale dell'utensile, cioè
a diametro di piede invariato.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from gearcalc.errors import GeometryError
from gearcalc.geometry.involute import inv
from gearcalc.models import GearGeometry

Array = NDArray[np.float64]


def _rotate(pts: Array, ang: float) -> Array:
    c, s = math.cos(ang), math.sin(ang)
    out: Array = pts @ np.array([[c, s], [-s, c]])
    return out


def _generate(X: Array, Y: Array, nx: Array, ny: Array, r: float) -> Array:
    """Punti della ruota generati dai punti (X, Y) dell'utensile con normale (nx, ny).

    Sistema: centro ruota nell'origine, retta di rotolamento dell'utensile y = r (tangente
    al primitivo di riferimento). Per uno spostamento r·φ dell'utensile la ruota ruota di −φ;
    la condizione d'ingranamento (normale passante per il punto (0, r)) dà
    φ = ((Y − r)·n_x/n_y − X)/r. Il punto nel riferimento ruota è Rot(φ)·(X + r·φ, Y).
    """
    phi = ((Y - r) * nx / ny - X) / r
    px = X + r * phi
    c, s = np.cos(phi), np.sin(phi)
    out: Array = np.column_stack([c * px - s * Y, s * px + c * Y])
    return out


def _segment_intersection(A: Array, B: Array) -> tuple[int, int, Array] | None:
    """Prima intersezione tra le polilinee A e B: (indice segmento A, indice segmento B, punto)."""
    a0, a1 = A[:-1], A[1:]
    b0, b1 = B[:-1], B[1:]
    da = a1 - a0
    db = b1 - b0
    for i in range(len(a0)):
        den = da[i, 0] * db[:, 1] - da[i, 1] * db[:, 0]
        ok = np.abs(den) > 1e-18
        w = b0 - a0[i]
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (w[:, 0] * db[:, 1] - w[:, 1] * db[:, 0]) / den
            u = (w[:, 0] * da[i, 1] - w[:, 1] * da[i, 0]) / den
        hit = ok & (t > 1e-12) & (t <= 1.0) & (u >= 0.0) & (u <= 1.0)
        if np.any(hit):
            j = int(np.argmax(hit))
            p: Array = a0[i] + t[j] * da[i]
            return i, j, p
    return None


def _hob_flank_generation_frame(
    geo: GearGeometry, thickness_reduction: float, n_fillet: int, n_flank: int
) -> tuple[Array, Array, bool]:
    """Raccordo e fianco generati dal lato destro del dente dell'utensile.

    Ritorna (raccordo, fianco, sottosquadro) nel sistema di generazione (vano centrato su +y),
    entrambi ordinati dal piede verso la testa.
    """
    m_n, rack = geo.m_n, geo.rack
    r = geo.d / 2.0
    r_a = geo.d_a / 2.0
    cos_b = math.cos(math.radians(geo.beta))
    a_n = math.radians(geo.alpha_n)
    a_t = math.radians(geo.alpha_t)
    rho = rack.rho_fP_star * m_n
    h_P0 = rack.h_fP_star * m_n
    half_dr = thickness_reduction / 2.0

    Y_d = r + geo.x * m_n  # linea di riferimento dell'utensile
    Y_c = Y_d - h_P0 + rho  # centro del raggio di testa
    Xc_n = math.pi * m_n / 4.0 - (h_P0 - rho) * math.tan(a_n) - rho / math.cos(a_n)
    if Xc_n < -1e-12:
        raise GeometryError(
            "Raggio di testa dell'utensile troppo grande: i raccordi dei due fianchi si "
            f"sovrappongono (rho_fP*={rack.rho_fP_star})"
        )
    Xc = max(Xc_n, 0.0) / cos_b + half_dr

    # raccordo (arco di testa dell'utensile, ellisse nel piano trasversale)
    th = np.linspace(-math.pi / 2.0, -a_n, n_fillet)
    Xf = Xc + rho * np.cos(th) / cos_b
    Yf = Y_c + rho * np.sin(th)
    fillet = _generate(Xf, Yf, np.cos(th), np.sin(th) / cos_b, r)

    # fianco rettilineo: dal punto di tangenza (o dal punto T sul cerchio di base) fino
    # all'ordinata che genera il punto sul cerchio di testa
    Y_j = Y_c - rho * math.sin(a_n)
    Y_T = r * math.cos(a_t) ** 2
    undercut = Y_j < Y_T - 1e-12
    cot2 = 1.0 / math.tan(a_t) ** 2
    disc = (r * cot2) ** 2 - (cot2 + 1.0) * (r * r * cot2 - r_a * r_a)
    Y_top = (r * cot2 + math.sqrt(disc)) / (cot2 + 1.0)
    Y_l = np.linspace(max(Y_j, Y_T), Y_top, n_flank)
    X_l = math.pi * m_n / (4.0 * cos_b) + half_dr - (Y_d - Y_l) * math.tan(a_t)
    flank = _generate(
        X_l,
        Y_l,
        np.full_like(Y_l, math.cos(a_t)),
        np.full_like(Y_l, -math.sin(a_t)),
        r,
    )
    if undercut:
        hit = _segment_intersection(fillet, flank)
        if hit is not None:
            i, j, p = hit
            fillet = np.vstack([fillet[: i + 1], p])
            flank = np.vstack([p, flank[j + 1 :]])
    return fillet, flank, undercut


def _to_tooth_frame(pts: Array, z: int) -> Array:
    """Dal sistema di generazione (vano su +y) al dente centrato su +x, lato y < 0."""
    out = _rotate(pts, -(math.pi / 2.0 - math.pi / abs(z)))
    out[:, 1] *= -1.0
    return out


def undercut_form_diameter(geo: GearGeometry) -> float:
    """d_Ff di una ruota con sottosquadro: intersezione tra trocoide ed evolvente."""
    fillet, _, _ = _hob_flank_generation_frame(geo, 0.0, 400, 400)
    return float(2.0 * np.hypot(fillet[-1, 0], fillet[-1, 1]))


def _internal_flank(geo: GearGeometry, thickness_reduction: float, n_flank: int) -> Array:
    r_ref = abs(geo.d) / 2.0
    r_b, r_a, r_f = abs(geo.d_b) / 2.0, abs(geo.d_a) / 2.0, abs(geo.d_f) / 2.0
    a_t = math.radians(geo.alpha_t)
    s_t = geo.s_t - thickness_reduction
    t = np.linspace(math.sqrt((r_f / r_b) ** 2 - 1.0), math.sqrt((r_a / r_b) ** 2 - 1.0), n_flank)
    radius = r_b * np.sqrt(1.0 + t * t)
    alpha_y = np.arctan(t)
    psi = s_t / (2.0 * r_ref) - inv(a_t) + (np.tan(alpha_y) - alpha_y)
    out: Array = np.column_stack([radius * np.cos(-psi), radius * np.sin(-psi)])
    return out


def tooth_flank(
    geo: GearGeometry, thickness_reduction: float = 0.0, n_flank: int = 40, n_fillet: int = 20
) -> Array:
    """Fianco del dente centrato sull'asse +x, lato y < 0, dal cerchio di piede alla testa.

    Per le esterne comprende la trocoide di raccordo; per le interne è la sola evolvente.

    Args:
        geo: geometria della ruota.
        thickness_reduction: riduzione totale dello spessore trasversale Δs_t [mm] (gioco),
            ripartita sui due fianchi.
        n_flank: punti sul tratto ad evolvente.
        n_fillet: punti sul raccordo (solo esterne).
    """
    if thickness_reduction >= geo.s_t:
        raise GeometryError("Riduzione di spessore maggiore dello spessore del dente")
    if geo.internal:
        return _internal_flank(geo, thickness_reduction, n_flank)
    fillet, flank, _ = _hob_flank_generation_frame(geo, thickness_reduction, n_fillet, n_flank)
    return _to_tooth_frame(np.vstack([fillet, flank[1:]]), geo.z)


def gear_profile(
    geo: GearGeometry,
    thickness_reduction: float = 0.0,
    n_flank: int = 40,
    n_fillet: int = 20,
    n_tip: int = 8,
    n_root: int = 8,
) -> Array:
    """Contorno chiuso (antiorario) della sezione trasversale della dentatura.

    Il primo dente è centrato sull'asse +x. Restituisce un array (N, 2) in mm, senza
    ripetere il primo punto in coda. Per le interne è il contorno interno della corona.
    """
    r_f, r_a = abs(geo.d_f) / 2.0, abs(geo.d_a) / 2.0
    right = tooth_flank(geo, thickness_reduction, n_flank, n_fillet)  # y<0, piede → testa
    left = right[::-1] * np.array([1.0, -1.0])  # y>0, testa → piede

    a_tip = math.atan2(right[-1, 1], right[-1, 0])
    if a_tip >= 0.0:
        raise GeometryError("Dente appuntito: i fianchi si intersecano prima della testa")
    ang = np.linspace(a_tip, -a_tip, n_tip + 2)[1:-1]
    tip = np.column_stack([r_a * np.cos(ang), r_a * np.sin(ang)])
    single = np.vstack([right, tip, left])

    pitch = 2.0 * math.pi / abs(geo.z)
    a_end = math.atan2(single[-1, 1], single[-1, 0])
    a_next = math.atan2(single[0, 1], single[0, 0]) + pitch
    if a_next < a_end - 1e-12:
        raise GeometryError("Vano nullo al piede: denti sovrapposti")
    parts = [single]
    if a_next - a_end > 1e-9:
        root_ang = np.linspace(a_end, a_next, n_root + 2)[1:-1]
        parts.append(np.column_stack([r_f * np.cos(root_ang), r_f * np.sin(root_ang)]))
    unit = np.vstack(parts)
    return np.vstack([_rotate(unit, i * pitch) for i in range(abs(geo.z))])
