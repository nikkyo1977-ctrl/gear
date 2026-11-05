"""Funzione evolvente e sua inversa."""

from __future__ import annotations

import math

from gearcalc.errors import GeometryError


def inv(alpha: float) -> float:
    """inv(α) = tan α − α, con α in radianti."""
    return math.tan(alpha) - alpha


def inv_inverse(value: float, *, tol: float = 1e-14, max_iter: int = 60) -> float:
    """Inversa della funzione evolvente: restituisce α [rad] tale che inv(α) = value.

    Newton-Raphson su f(α) = tan α − α − value, f'(α) = tan²α. Stima iniziale di
    Cheng (1992) valida per inv ∈ [0, ~1.5): α0 = (3v)^(1/3) − 2v/5 (errore < 1 %
    fino a ~60°). Convergenza quadratica in 3–5 iterazioni.
    """
    if value < 0.0:
        raise GeometryError(f"inv(α) deve essere ≥ 0, ricevuto {value}")
    if value == 0.0:
        return 0.0
    alpha = (3.0 * value) ** (1.0 / 3.0) - 0.4 * value
    alpha = min(max(alpha, 1e-6), math.pi / 2 - 1e-6)
    for _ in range(max_iter):
        t = math.tan(alpha)
        delta = (t - alpha - value) / (t * t)
        alpha -= delta
        if abs(delta) < tol:
            return float(alpha)
    raise GeometryError(f"inv_inverse non converge per value={value}")


def involute_xy(r_b: float, t: float) -> tuple[float, float]:
    """Punto dell'evolvente del cerchio di raggio r_b al parametro di rotolamento t [rad].

    Origine dell'evolvente sull'asse x positivo, sviluppo antiorario.
    """
    return (
        r_b * (math.cos(t) + t * math.sin(t)),
        r_b * (math.sin(t) - t * math.cos(t)),
    )
