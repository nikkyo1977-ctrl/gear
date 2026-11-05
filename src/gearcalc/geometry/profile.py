"""Profilo trasversale 2D della ruota (punti per spline/polilinea in CATIA).

Il fianco è l'evolvente esatta tra il cerchio di base (o di piede, se maggiore) e quello di
testa. **Limite attuale**: il piede è modellato con un tratto radiale dal cerchio di base al
cerchio di piede e un arco sul cerchio di piede; la trocoide di raccordo generata dal
creatore (raggio ρ_fP) è prevista nella fase 2. Il profilo è quindi adatto alla
rappresentazione CAD, non al calcolo FEM della tensione al piede.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from gearcalc.errors import GeometryError
from gearcalc.geometry.involute import involute_xy
from gearcalc.models import GearGeometry


def _polar_angle(p: tuple[float, float]) -> float:
    return math.atan2(p[1], p[0])


def tooth_flank(
    geo: GearGeometry, thickness_reduction: float = 0.0, n_flank: int = 40
) -> NDArray[np.float64]:
    """Fianco destro (lato y < 0) del dente centrato sull'asse x, dal piede alla testa.

    Args:
        geo: geometria della ruota.
        thickness_reduction: riduzione totale dello spessore trasversale al primitivo
            Δs_t [mm] (gioco tra i fianchi; ripartito sui due fianchi del dente).
        n_flank: numero di punti sull'evolvente.
    """
    r, r_b, r_a, r_f = geo.d / 2, geo.d_b / 2, geo.d_a / 2, geo.d_f / 2
    s_t = geo.s_t - thickness_reduction
    if s_t <= 0.0:
        raise GeometryError("Riduzione di spessore maggiore dello spessore del dente")
    t_tip = math.sqrt((r_a / r_b) ** 2 - 1.0)
    t_start = math.sqrt((r_f / r_b) ** 2 - 1.0) if r_f > r_b else 0.0
    t_ref = math.sqrt((r / r_b) ** 2 - 1.0)
    # rotazione: l'evolvente al primitivo deve stare a -s_t/(2r) dall'asse del dente
    rot = -s_t / (2.0 * r) - _polar_angle(involute_xy(r_b, t_ref))
    c, s = math.cos(rot), math.sin(rot)
    pts = np.array([involute_xy(r_b, t) for t in np.linspace(t_start, t_tip, n_flank)])
    flank: NDArray[np.float64] = pts @ np.array([[c, s], [-s, c]])
    return flank


def gear_profile(
    geo: GearGeometry,
    thickness_reduction: float = 0.0,
    n_flank: int = 40,
    n_tip: int = 8,
    n_root: int = 8,
) -> NDArray[np.float64]:
    """Contorno chiuso (antiorario) della sezione trasversale dell'intera ruota.

    Il primo dente è centrato sull'asse +x. Restituisce un array (N, 2) in mm, senza
    ripetere il primo punto in coda.
    """
    r_f, r_a, r_b = geo.d_f / 2, geo.d_a / 2, geo.d_b / 2
    right = tooth_flank(geo, thickness_reduction, n_flank)  # y<0, piede → testa
    left = right[::-1] * np.array([1.0, -1.0])  # y>0, testa → piede

    tooth: list[NDArray[np.float64]] = []
    if r_f < r_b:  # tratto radiale da r_f al cerchio di base
        a0 = math.atan2(right[0, 1], right[0, 0])
        tooth.append(np.array([[r_f * math.cos(a0), r_f * math.sin(a0)]]))
    tooth.append(right)
    a_tip = math.atan2(right[-1, 1], right[-1, 0])
    if a_tip >= 0.0:
        raise GeometryError("Dente appuntito: i fianchi si intersecano prima della testa")
    ang = np.linspace(a_tip, -a_tip, n_tip + 2)[1:-1]
    tooth.append(np.column_stack([r_a * np.cos(ang), r_a * np.sin(ang)]))
    tooth.append(left)
    if r_f < r_b:
        a1 = math.atan2(left[-1, 1], left[-1, 0])
        tooth.append(np.array([[r_f * math.cos(a1), r_f * math.sin(a1)]]))
    single = np.vstack(tooth)

    pitch = 2.0 * math.pi / geo.z
    a_end = math.atan2(single[-1, 1], single[-1, 0])
    a_next = math.atan2(single[0, 1], single[0, 0]) + pitch
    if a_next <= a_end:
        raise GeometryError("Vano nullo al piede: denti sovrapposti")
    root_ang = np.linspace(a_end, a_next, n_root + 2)[1:-1]
    root = np.column_stack([r_f * np.cos(root_ang), r_f * np.sin(root_ang)])
    unit = np.vstack([single, root])

    out = []
    for i in range(geo.z):
        c, s = math.cos(i * pitch), math.sin(i * pitch)
        out.append(unit @ np.array([[c, s], [-s, c]]))
    return np.vstack(out)
