"""Contorno trasversale strutturato della dentatura, per la costruzione CAD (schizzo).

Il contorno chiuso (antiorario) è una sequenza di segmenti con estremi coincidenti:
    - ``spline``: punti di passaggio del fianco (raccordo + evolvente; spezzato in due spline
      in caso di sottosquadro, dove raccordo ed evolvente si intersecano con uno spigolo);
    - ``arc``: arco del cerchio di testa o di piede, centro nell'origine, da ``a0`` ad ``a1``
      in senso antiorario (radianti, a1 > a0).

L'area racchiusa è calcolata su un profilo fitto (``gear_profile`` a 400 punti per fianco),
indipendente dal numero di punti delle spline: serve a verificare il volume del solido CAD.
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from gearcalc.errors import GeometryError
from gearcalc.geometry.profile import (
    Array,
    _hob_flank_generation_frame,
    _internal_flank,
    _rotate,
    _to_tooth_frame,
    gear_profile,
)
from gearcalc.models import GearGeometry

Point = tuple[float, float]


class OutlineSegment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["spline", "arc"]
    p0: Point
    p1: Point
    points: tuple[Point, ...] = Field((), description="Punti di passaggio (solo spline), p0…p1")
    r: float = Field(0.0, description="Raggio (solo arco), centro nell'origine [mm]")
    a0: float = Field(0.0, description="Angolo iniziale (solo arco) [rad]")
    a1: float = Field(0.0, description="Angolo finale > a0 (solo arco) [rad]")


class GearOutline(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    z: int
    internal: bool
    segments: tuple[OutlineSegment, ...]
    area: float = Field(description="Area racchiusa dal contorno [mm²]")
    r_a: float
    r_f: float


def _area(pts: Array) -> float:
    x, y = pts[:, 0], pts[:, 1]
    return float(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _flank_parts(
    geo: GearGeometry, thickness_reduction: float, n_flank: int, n_fillet: int
) -> list[Array]:
    """Parti del fianco (lato y < 0, dal piede alla testa) da rappresentare con spline distinte."""
    if thickness_reduction >= geo.s_t:
        raise GeometryError("Riduzione di spessore maggiore dello spessore del dente")
    if geo.internal:
        return [_internal_flank(geo, thickness_reduction, n_flank)]
    fillet, flank, undercut = _hob_flank_generation_frame(
        geo, thickness_reduction, n_fillet, n_flank
    )
    if undercut:
        # intersezione trocoide/evolvente su campionamento fitto, poi ricampionamento: con pochi
        # punti le due polilinee potrebbero non intersecarsi
        fd, ld, _ = _hob_flank_generation_frame(geo, thickness_reduction, 400, 400)
        fil = _to_tooth_frame(_subsample(fd, n_fillet), geo.z)
        inv = _to_tooth_frame(_subsample(ld, n_flank), geo.z)
        return [fil, inv]  # spigolo all'intersezione: due spline
    fil = _to_tooth_frame(fillet, geo.z)
    inv = _to_tooth_frame(flank, geo.z)
    return [np.vstack([fil, inv[1:]])]  # raccordo tangente all'evolvente: una spline


def _subsample(pts: Array, n: int) -> Array:
    idx = np.unique(np.round(np.linspace(0, len(pts) - 1, max(n, 2))).astype(int))
    out: Array = pts[idx]
    return out


def _pt(p: Array) -> Point:
    return (float(p[0]), float(p[1]))


def gear_outline(
    geo: GearGeometry, thickness_reduction: float = 0.0, n_flank: int = 15, n_fillet: int = 10
) -> GearOutline:
    """Contorno della dentatura come spline e archi (primo dente centrato su +x)."""
    r_a, r_f = abs(geo.d_a) / 2.0, abs(geo.d_f) / 2.0
    right_parts = _flank_parts(geo, thickness_reduction, n_flank, n_fillet)
    flip = np.array([1.0, -1.0])
    left_parts = [p[::-1] * flip for p in reversed(right_parts)]  # y > 0, testa → piede
    z = abs(geo.z)
    pitch = 2.0 * math.pi / z

    tip_start = right_parts[-1][-1]
    a_tip = math.atan2(tip_start[1], tip_start[0])
    if a_tip >= 0.0:
        raise GeometryError("Dente appuntito: i fianchi si intersecano prima della testa")
    root_end = left_parts[-1][-1]
    a_root0 = math.atan2(root_end[1], root_end[0])
    root_start = right_parts[0][0]
    a_root1 = math.atan2(root_start[1], root_start[0]) + pitch
    if a_root1 < a_root0 - 1e-12:
        raise GeometryError("Vano nullo al piede: denti sovrapposti")

    segs: list[OutlineSegment] = []
    for i in range(z):
        ang = i * pitch

        def rot(p: Array, ang: float = ang) -> Array:
            out: Array = _rotate(p[None, :], ang)[0]
            return out

        for part in right_parts:
            pts = _rotate(part, ang)
            segs.append(
                OutlineSegment(
                    kind="spline",
                    p0=_pt(pts[0]),
                    p1=_pt(pts[-1]),
                    points=tuple(_pt(p) for p in pts),
                )
            )
        segs.append(
            OutlineSegment(
                kind="arc",
                p0=segs[-1].p1,
                p1=_pt(rot(left_parts[0][0])),
                r=r_a,
                a0=a_tip + ang,
                a1=-a_tip + ang,
            )
        )
        for part in left_parts:
            pts = _rotate(part, ang)
            segs.append(
                OutlineSegment(
                    kind="spline",
                    p0=_pt(pts[0]),
                    p1=_pt(pts[-1]),
                    points=tuple(_pt(p) for p in pts),
                )
            )
        if a_root1 - a_root0 > 1e-9:
            nxt = _rotate(right_parts[0][:1], ang + pitch)[0] if i < z - 1 else right_parts[0][0]
            segs.append(
                OutlineSegment(
                    kind="arc",
                    p0=segs[-1].p1,
                    p1=_pt(nxt),
                    r=r_f,
                    a0=a_root0 + ang,
                    a1=a_root1 + ang,
                )
            )
    dense = gear_profile(geo, thickness_reduction, n_flank=400, n_fillet=400, n_tip=60, n_root=60)
    return GearOutline(
        z=z, internal=geo.internal, segments=tuple(segs), area=_area(dense), r_a=r_a, r_f=r_f
    )
