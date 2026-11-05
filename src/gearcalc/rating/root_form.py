"""Fattori di forma al piede con carico in testa (ISO 6336-3 / DIN 3990-3), per ruote da creatore.

Sezione critica con il metodo della tangente a 30° sulla ruota virtuale z_n, raccordo generato
dal profilo di riferimento (h_fP, ρ_fP, senza protuberanza). È il procedimento che la VDI 2736-2
richiama per Y_Fa e Y_Sa.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from gearcalc.errors import GeometryError
from gearcalc.geometry.involute import inv
from gearcalc.models import GearGeometry


@dataclass(frozen=True)
class RootFormFactors:
    s_Fn: float
    """Corda al piede nella sezione critica [mm]."""
    rho_F: float
    """Raggio di raccordo nella sezione critica [mm]."""
    h_Fa: float
    """Braccio di flessione con carico in testa [mm]."""
    alpha_Fan: float
    """Angolo di carico in testa [rad]."""
    Y_Fa: float
    Y_Sa: float


def root_form_factors(geo: GearGeometry) -> RootFormFactors:
    """Y_Fa e Y_Sa per carico applicato in testa (ruote esterne da creatore)."""
    if geo.internal:
        raise GeometryError("Fattori di forma per dentature interne non ancora implementati")
    m = geo.m_n
    a_n = math.radians(geo.alpha_n)
    z_n = geo.z_n
    rho_fP = geo.rack.rho_fP_star * m
    h_fP = geo.rack.h_fP_star * m
    x = geo.x

    E = math.pi / 4.0 * m - h_fP * math.tan(a_n) - (1.0 - math.sin(a_n)) * rho_fP / math.cos(a_n)
    G = rho_fP / m - h_fP / m + x
    H = 2.0 / z_n * (math.pi / 2.0 - E / m) - math.pi / 3.0
    theta = math.pi / 6.0
    for _ in range(50):
        new = 2.0 * G / z_n * math.tan(theta) - H
        if abs(new - theta) < 1e-14:
            theta = new
            break
        theta = new
    s_Fn = m * (
        z_n * math.sin(math.pi / 3.0 - theta) + math.sqrt(3.0) * (G / math.cos(theta) - rho_fP / m)
    )
    rho_F = m * (
        rho_fP / m + 2.0 * G**2 / (math.cos(theta) * (z_n * math.cos(theta) ** 2 - 2.0 * G))
    )

    # ruota virtuale: d_n = m·z_n, d_an = d_n + d_a − d
    d_n = m * z_n
    d_bn = d_n * math.cos(a_n)
    d_an = d_n + geo.d_a - geo.d
    a_an = math.acos(d_bn / d_an)
    gamma_a = (math.pi / 2.0 + 2.0 * x * math.tan(a_n)) / z_n + inv(a_n) - inv(a_an)
    a_Fan = a_an - gamma_a
    h_Fa = (
        0.5
        * m
        * (
            (math.cos(gamma_a) - math.sin(gamma_a) * math.tan(a_Fan)) * d_an / m
            - z_n * math.cos(math.pi / 3.0 - theta)
            - G / math.cos(theta)
            + rho_fP / m
        )
    )
    if s_Fn <= 0.0 or h_Fa <= 0.0 or rho_F <= 0.0:
        raise GeometryError("Sezione critica al piede non determinabile")
    Y_Fa = 6.0 * (h_Fa / m) * math.cos(a_Fan) / ((s_Fn / m) ** 2 * math.cos(a_n))
    L_a = s_Fn / h_Fa
    q_s = s_Fn / (2.0 * rho_F)
    Y_Sa = (1.2 + 0.13 * L_a) * q_s ** (1.0 / (1.21 + 2.3 / L_a))
    return RootFormFactors(s_Fn, rho_F, h_Fa, a_Fan, Y_Fa, Y_Sa)
