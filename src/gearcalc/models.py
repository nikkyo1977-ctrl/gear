"""Modello dati di input/output (pydantic v2, immutabile, serializzabile JSON per MCP).

Convenzioni:
    - lunghezze in mm, angoli in gradi (input e output), forze in N, coppie in N·m;
    - nomi dei campi = simboli ISO 21771 in snake_case (``m_n``, ``alpha_wt``, ``d_a`` ...);
    - coefficienti adimensionali riferiti a ``m_n`` sono marcati con suffisso ``_star``.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class BasicRackProfile(_Frozen):
    """Profilo di riferimento della dentiera (ISO 53), riferito al modulo normale.

    ``h_fP_star`` è il dedendum del profilo di riferimento della *ruota*, pari
    all'addendum dell'utensile creatore ``h_aP0*``; ``rho_fP_star`` è il raggio di
    raccordo al piede della ruota (= raggio di testa dell'utensile ``rho_aP0*``).
    """

    alpha_n: float = Field(20.0, gt=0.0, lt=45.0, description="Angolo di pressione normale [°]")
    h_aP_star: float = Field(
        1.0, gt=0.0, description="Addendum del profilo di riferimento h_aP/m_n"
    )
    h_fP_star: float = Field(
        1.25, gt=0.0, description="Dedendum del profilo di riferimento h_fP/m_n"
    )
    rho_fP_star: float = Field(0.38, ge=0.0, description="Raggio di raccordo al piede rho_fP/m_n")

    @model_validator(mode="after")
    def _check(self) -> BasicRackProfile:
        if self.h_fP_star <= self.h_aP_star:
            raise ValueError("h_fP* deve essere > h_aP* (gioco di testa positivo)")
        return self


class StandardRack(StrEnum):
    """Profili di riferimento ISO 53:1998."""

    ISO53_A = "ISO53_A"
    ISO53_B = "ISO53_B"
    ISO53_C = "ISO53_C"
    ISO53_D = "ISO53_D"

    def profile(self) -> BasicRackProfile:
        return _ISO53[self]


_ISO53: dict[StandardRack, BasicRackProfile] = {
    StandardRack.ISO53_A: BasicRackProfile(h_aP_star=1.0, h_fP_star=1.25, rho_fP_star=0.38),
    StandardRack.ISO53_B: BasicRackProfile(h_aP_star=1.0, h_fP_star=1.25, rho_fP_star=0.30),
    StandardRack.ISO53_C: BasicRackProfile(h_aP_star=1.0, h_fP_star=1.25, rho_fP_star=0.25),
    StandardRack.ISO53_D: BasicRackProfile(h_aP_star=1.0, h_fP_star=1.40, rho_fP_star=0.39),
}


class CylindricalGear(_Frozen):
    """Ruota cilindrica a evolvente a dentatura esterna (dritta o elicoidale).

    ``beta`` con segno: >0 elica destra, <0 elica sinistra. Nella coppia esterna le
    due ruote devono avere elica di verso opposto (beta1 = -beta2).
    """

    z: int = Field(..., ge=3, description="Numero di denti")
    m_n: float = Field(..., gt=0.0, description="Modulo normale [mm]")
    b: float = Field(..., gt=0.0, description="Larghezza di fascia [mm]")
    beta: float = Field(0.0, gt=-60.0, lt=60.0, description="Angolo d'elica al primitivo [°]")
    x: float = Field(0.0, ge=-1.5, le=2.5, description="Coefficiente di spostamento del profilo")
    rack: BasicRackProfile = Field(default_factory=BasicRackProfile)


class GearPair(_Frozen):
    """Coppia cilindrica esterna. ``tip_shortening`` applica la riduzione di testa k·m_n
    che ripristina il gioco di testa nominale quando x1+x2 ≠ y (ISO 21771 §5.3)."""

    gear1: CylindricalGear
    gear2: CylindricalGear
    tip_shortening: bool = False

    @model_validator(mode="after")
    def _check(self) -> GearPair:
        g1, g2 = self.gear1, self.gear2
        if abs(g1.m_n - g2.m_n) > 1e-9:
            raise ValueError("Le due ruote devono avere lo stesso modulo normale")
        if g1.rack.alpha_n != g2.rack.alpha_n:
            raise ValueError("Le due ruote devono avere lo stesso angolo di pressione normale")
        if abs(g1.beta + g2.beta) > 1e-9:
            raise ValueError("Coppia esterna: eliche di verso opposto, beta2 = -beta1")
        return self


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class GearGeometry(_Frozen):
    """Geometria della singola ruota (ISO 21771). Spessori senza tolleranze (gioco zero)."""

    z: int
    m_n: float = Field(description="Modulo normale [mm]")
    m_t: float = Field(description="Modulo trasversale [mm]")
    alpha_n: float = Field(description="Angolo di pressione normale [°]")
    alpha_t: float = Field(description="Angolo di pressione trasversale [°]")
    beta: float = Field(description="Angolo d'elica al primitivo [°]")
    beta_b: float = Field(description="Angolo d'elica al cerchio base [°]")
    x: float
    k: float = Field(description="Coefficiente di riduzione di testa (≤0)")
    d: float = Field(description="Diametro primitivo di riferimento [mm]")
    d_b: float = Field(description="Diametro di base [mm]")
    d_a: float = Field(description="Diametro di testa [mm]")
    d_f: float = Field(description="Diametro di piede [mm]")
    h_a: float = Field(description="Addendum [mm]")
    h_f: float = Field(description="Dedendum [mm]")
    h: float = Field(description="Altezza del dente [mm]")
    p_n: float = Field(description="Passo normale [mm]")
    p_t: float = Field(description="Passo trasversale [mm]")
    p_bt: float = Field(description="Passo base trasversale [mm]")
    p_z: float = Field(description="Passo dell'elica (lead) [mm]; inf per denti dritti")
    s_n: float = Field(description="Spessore normale al primitivo [mm]")
    s_t: float = Field(description="Spessore trasversale al primitivo [mm]")
    s_at: float = Field(description="Spessore trasversale in testa [mm]")
    s_an: float = Field(description="Spessore normale in testa (appross. s_at·cos beta_a) [mm]")
    z_n: float = Field(description="Numero di denti virtuale z/(cos²beta_b·cos beta)")
    x_min_undercut: float = Field(description="Spostamento minimo senza sottosquadro")
    undercut: bool = Field(description="True se x < x_min_undercut")


class PairGeometry(_Frozen):
    gear1: GearGeometry
    gear2: GearGeometry
    u: float = Field(description="Rapporto di ingranamento z2/z1")
    a_d: float = Field(description="Interasse di riferimento [mm]")
    a_w: float = Field(description="Interasse di lavoro [mm]")
    alpha_wt: float = Field(description="Angolo di pressione di lavoro trasversale [°]")
    x_sum: float = Field(description="x1 + x2")
    y: float = Field(description="Coefficiente di variazione dell'interasse (a_w - a_d)/m_n")
    k: float = Field(description="Riduzione di testa k = y - (x1+x2) (≤0)")
    g_alpha: float = Field(description="Lunghezza del segmento di contatto [mm]")
    epsilon_alpha: float = Field(description="Rapporto di condotta trasversale")
    epsilon_beta: float = Field(description="Rapporto di ricoprimento")
    epsilon_gamma: float = Field(description="Rapporto di condotta totale")
    b_eff: float = Field(description="Larghezza in presa min(b1, b2) [mm]")
    warnings: tuple[str, ...] = ()
