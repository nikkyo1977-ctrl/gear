"""Geometria della coppia vite cilindrica / ruota a dentatura globoidale (ISO/TS 14521, DIN 3975).

Convenzioni:
    - m = m_x: modulo assiale della vite = modulo trasversale della ruota [mm];
    - q = d_m1 / m: quoziente diametrale; γ_m: angolo d'elica sul diametro medio;
    - x2: spostamento del profilo della ruota (riferito a m), che modifica l'interasse;
    - angolo di pressione di riferimento α_0 nella sezione caratteristica della forma di fianco:
        ZA → sezione assiale (α_x = α_0);
        ZN, ZI, ZK → sezione normale (α_n = α_0; per ZK è l'approssimazione usuale).

Per le verifiche al piede la ruota è rappresentata dalla ruota cilindrica elicoidale virtuale
del piano medio (z2, β = γ_m, m_n = m·cos γ_m), ingranante con la vite vista come dentiera.
"""

from __future__ import annotations

import math
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gearcalc.models import BasicRackProfile, CylindricalGear


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FlankForm(StrEnum):
    ZA = "ZA"
    """Fianco rettilineo in sezione assiale (tornitura con utensile nel piano assiale)."""
    ZN = "ZN"
    """Fianco rettilineo in sezione normale al vano."""
    ZI = "ZI"
    """Elicoide a evolvente (fianco rettilineo nel piano tangente al cilindro di base)."""
    ZK = "ZK"
    """Fianco generato da mola biconica."""


class WormGearSet(_Frozen):
    z1: int = Field(..., ge=1, le=8, description="Numero di principi della vite")
    z2: int = Field(..., ge=10, description="Numero di denti della ruota")
    m: float = Field(..., gt=0.0, description="Modulo assiale m_x [mm]")
    q: float = Field(..., gt=3.0, lt=30.0, description="Quoziente diametrale d_m1 / m")
    alpha_0: float = Field(20.0, gt=5.0, lt=35.0, description="Angolo di pressione rif. [°]")
    flank_form: FlankForm = FlankForm.ZI
    x2: float = Field(0.0, ge=-1.0, le=1.0, description="Spostamento del profilo della ruota")
    b1: float = Field(..., gt=0.0, description="Lunghezza filettata della vite [mm]")
    b2: float = Field(..., gt=0.0, description="Larghezza della ruota [mm]")
    h_a_star: float = Field(1.0, gt=0.0, description="Addendum riferito a m")
    c_star: float = Field(0.2, ge=0.1, le=0.4, description="Gioco di testa riferito a m")
    rho_f2_star: float = Field(
        0.2, ge=0.0, le=0.4, description="Raggio di raccordo al piede della ruota riferito a m"
    )

    @model_validator(mode="after")
    def _check(self) -> WormGearSet:
        if self.q <= 2.0 * (self.h_a_star + self.c_star) + 1.0:
            raise ValueError("q troppo piccolo: diametro di piede della vite non realizzabile")
        return self


class WormGeometry(_Frozen):
    i: float = Field(description="Rapporto di trasmissione z2/z1")
    p_x: float = Field(description="Passo assiale [mm]")
    p_z: float = Field(description="Passo dell'elica (lead) [mm]")
    gamma_m: float = Field(description="Angolo d'elica sul diametro medio [°]")
    m_n: float = Field(description="Modulo normale m·cos γ_m [mm]")
    alpha_x: float = Field(description="Angolo di pressione assiale [°]")
    alpha_n: float = Field(description="Angolo di pressione normale sul diametro medio [°]")
    d_m1: float = Field(description="Diametro medio della vite [mm]")
    d_a1: float
    d_f1: float
    d_2: float = Field(description="Diametro primitivo della ruota [mm]")
    d_a2: float = Field(description="Diametro di testa (gola) della ruota [mm]")
    d_f2: float
    d_e2: float = Field(description="Diametro esterno indicativo della ruota d_a2 + m [mm]")
    a: float = Field(description="Interasse [mm]")
    b2_max: float = Field(description="Larghezza utile massima della ruota 4·√(r_m1·m) [mm]")
    b2_eff: float = Field(description="Larghezza utile min(b2, b2_max) [mm]")
    epsilon_alpha: float = Field(description="Rapporto di condotta nel piano medio")
    x2_min_undercut: float
    warnings: tuple[str, ...] = ()


def axial_pressure_angle(ws: WormGearSet) -> tuple[float, float]:
    """(α_x, α_n) [rad] sul diametro medio secondo la forma di fianco."""
    gamma = math.atan2(ws.z1, ws.q)
    a0 = math.radians(ws.alpha_0)
    if ws.flank_form is FlankForm.ZA:
        a_x = a0
        a_n = math.atan(math.tan(a0) * math.cos(gamma))
    else:
        a_n = a0
        a_x = math.atan(math.tan(a0) / math.cos(gamma))
    return a_x, a_n


def worm_geometry(ws: WormGearSet) -> WormGeometry:
    m = ws.m
    gamma = math.atan2(ws.z1, ws.q)
    a_x, a_n = axial_pressure_angle(ws)
    d_m1 = ws.q * m
    d_2 = ws.z2 * m
    h_a = ws.h_a_star * m
    c = ws.c_star * m
    d_a1 = d_m1 + 2.0 * h_a
    d_f1 = d_m1 - 2.0 * (h_a + c)
    d_a2 = d_2 + 2.0 * (h_a + ws.x2 * m)
    d_f2 = d_2 - 2.0 * (h_a + c - ws.x2 * m)
    a = (d_m1 + d_2) / 2.0 + ws.x2 * m

    # larghezza utile: corda del cilindro di testa della vite alla quota della gola della ruota
    r_a1 = d_a1 / 2.0
    gap = a - d_a2 / 2.0  # distanza asse vite – gola della ruota = r_m1 − h_a
    b2_max = 2.0 * math.sqrt(max(r_a1**2 - gap**2, 0.0))

    # condotta nel piano medio: ruota z2 con dentiera (vite) di angolo α_x
    r_2, r_a2 = d_2 / 2.0, d_a2 / 2.0
    r_b2 = r_2 * math.cos(a_x)
    g_alpha = (
        math.sqrt(r_a2**2 - r_b2**2)
        - r_2 * math.sin(a_x)
        + (ws.h_a_star - ws.x2) * m / math.sin(a_x)
    )
    eps = g_alpha / (math.pi * m * math.cos(a_x))
    x_min = ws.h_a_star - ws.z2 * math.sin(a_x) ** 2 / 2.0

    w: list[str] = []
    if ws.b2 > b2_max:
        w.append(f"b2 = {ws.b2} mm > larghezza utile {b2_max:.2f} mm: eccedenza non portante")
    if ws.x2 < x_min:
        w.append(f"Ruota: sottosquadro (x2 = {ws.x2:.3f} < {x_min:.3f})")
    if eps < 1.1:
        w.append(f"ε_α nel piano medio = {eps:.3f} < 1.1")
    l_min = 2.0 * math.sqrt(max((d_a2 / 2.0) ** 2 - (a - d_a1 / 2.0) ** 2, 0.0))
    if ws.b1 < l_min:
        w.append(f"Vite corta: b1 = {ws.b1} mm < lunghezza d'ingranamento {l_min:.2f} mm")
    if ws.flank_form is FlankForm.ZK:
        w.append("ZK: α_n = α_0 approssimato (dipende dal diametro della mola)")

    return WormGeometry(
        i=ws.z2 / ws.z1,
        p_x=math.pi * m,
        p_z=math.pi * m * ws.z1,
        gamma_m=math.degrees(gamma),
        m_n=m * math.cos(gamma),
        alpha_x=math.degrees(a_x),
        alpha_n=math.degrees(a_n),
        d_m1=d_m1,
        d_a1=d_a1,
        d_f1=d_f1,
        d_2=d_2,
        d_a2=d_a2,
        d_f2=d_f2,
        d_e2=d_a2 + m,
        a=a,
        b2_max=b2_max,
        b2_eff=min(ws.b2, b2_max),
        epsilon_alpha=eps,
        x2_min_undercut=x_min,
        warnings=tuple(w),
    )


def virtual_wheel(ws: WormGearSet) -> CylindricalGear:
    """Ruota elicoidale virtuale del piano medio (z2, β = γ_m, m_n = m·cos γ_m).

    Il creatore della ruota ha il profilo della vite: in unità di m_n
    h_aP* = h_a*/cos γ, h_fP* = (h_a* + c*)/cos γ, ρ_fP* = ρ_f2*/cos γ, x_n = x2/cos γ.
    Così d = z2·m, d_a = d_a2 e d_f = d_f2 coincidono con la geometria della ruota.
    """
    gamma = math.atan2(ws.z1, ws.q)
    cg = math.cos(gamma)
    _, a_n = axial_pressure_angle(ws)
    rack = BasicRackProfile(
        alpha_n=math.degrees(a_n),
        h_aP_star=ws.h_a_star / cg,
        h_fP_star=(ws.h_a_star + ws.c_star) / cg,
        rho_fP_star=ws.rho_f2_star / cg,
    )
    return CylindricalGear(
        z=ws.z2,
        m_n=ws.m * cg,
        b=ws.b2,
        beta=math.degrees(gamma),
        x=ws.x2 / cg,
        rack=rack,
    )
