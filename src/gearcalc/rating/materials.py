"""Materiali per la verifica VDI 2736 (ruote in termoplastico).

Fonti dei dati:
    - curve di resistenza σ_FlimN(θ, N) e σ_HlimN(θ, N): VDI 2736-2:2014, note alle figure
      di resistenza (POM e PA66 al piede; PA66 lubrificato a olio/grasso e PBT a grasso al
      fianco). Valide per N_L = 1e5 … 1e8;
    - coefficienti d'attrito (Tab. 2), di scambio termico (Tab. 3) e di usura (Tab. 6):
      VDI 2736-2;
    - moduli elastici e loro gradiente termico: **valori indicativi** da letteratura e
      schede tecniche tipiche (non dalla norma), da sostituire con i dati del fornitore.

Per PBT al piede e per POM al fianco la norma non fornisce curve: il valore va dato
dall'utente (``sigma_FlimN`` / ``sigma_HlimN``) oppure la verifica non viene eseguita.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Polymer(StrEnum):
    POM = "POM"
    PA66 = "PA66"
    PBT = "PBT"
    STEEL = "STEEL"


class Lubrication(StrEnum):
    DRY = "dry"
    GREASE = "grease"
    """Grasso (es. Klüber Isoflex Topas L32): μ = 0.09 da VDI 2736-2 Tab. 2."""
    OIL_MIST = "oil_mist"
    OIL_INJECTION = "oil_injection"


class Material(BaseModel):
    """Dati di materiale; i campi opzionali sostituiscono i valori standard."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    polymer: Polymer
    E_23: float | None = Field(None, gt=0.0, description="Modulo elastico a 23 °C [MPa]")
    dE_dT: float | None = Field(None, le=0.0, description="Gradiente di E [MPa/K]")
    nu: float | None = Field(None, gt=0.0, lt=0.5, description="Coefficiente di Poisson")
    theta_max: float | None = Field(None, description="Temperatura massima d'impiego [°C]")
    sigma_FlimN: float | None = Field(
        None, gt=0.0, description="Resistenza a fatica al piede (sostituisce la curva) [MPa]"
    )
    sigma_HlimN: float | None = Field(
        None, gt=0.0, description="Resistenza a fatica del fianco (sostituisce la curva) [MPa]"
    )

    @property
    def is_steel(self) -> bool:
        return self.polymer is Polymer.STEEL

    def elastic_modulus(self, theta: float) -> float:
        """E(θ) lineare, limitato inferiormente al 10 % di E_23."""
        E0 = self.E_23 if self.E_23 is not None else _DEFAULTS[self.polymer][0]
        dE = self.dE_dT if self.dE_dT is not None else _DEFAULTS[self.polymer][1]
        return max(E0 + dE * (theta - 23.0), 0.1 * E0)

    def poisson(self) -> float:
        return self.nu if self.nu is not None else _DEFAULTS[self.polymer][2]

    def max_temperature(self) -> float:
        return self.theta_max if self.theta_max is not None else _DEFAULTS[self.polymer][3]


#: (E_23 [MPa], dE/dθ [MPa/K], ν, θ_max [°C]) — indicativi, non da norma.
_DEFAULTS: dict[Polymer, tuple[float, float, float, float]] = {
    Polymer.POM: (2800.0, -14.0, 0.35, 100.0),
    Polymer.PA66: (3000.0, -20.0, 0.35, 120.0),  # secco come stampato; condizionato ≈ −40 %
    Polymer.PBT: (2600.0, -20.0, 0.35, 120.0),
    Polymer.STEEL: (206000.0, 0.0, 0.30, 300.0),
}


def root_strength(material: Material, theta: float, N: float) -> float | None:
    """σ_FlimN(θ_Fuß, N_L) [MPa] secondo VDI 2736-2, o il valore dato dall'utente."""
    if material.sigma_FlimN is not None:
        return material.sigma_FlimN
    if material.polymer is Polymer.POM:
        return float(26.0 - 0.0025 * theta**2 + 400.0 * N**-0.2)
    if material.polymer is Polymer.PA66:
        return float(30.0 - 0.22 * theta + (4600.0 - 900.0 * theta**0.3) * N ** (-1.0 / 3.0))
    return None


def flank_strength(material: Material, theta: float, N: float, lub: Lubrication) -> float | None:
    """σ_HlimN(θ_Fla, N_L) [MPa] secondo VDI 2736-2, o il valore dato dall'utente."""
    if material.sigma_HlimN is not None:
        return material.sigma_HlimN
    if material.polymer is Polymer.PA66:
        if lub in (Lubrication.OIL_MIST, Lubrication.OIL_INJECTION):
            return float(36.0 - 0.0012 * theta**2 + (1000.0 - 0.025 * theta**2) * N**-0.21)
        if lub is Lubrication.GREASE:
            return float(20.0 - 0.0003 * theta**2 + (950.0 - 0.017 * theta**2) * N**-0.21)
    if material.polymer is Polymer.PBT and lub is Lubrication.GREASE:
        return float(27.0 - 0.25 * theta + (500.0 - 0.5 * theta**1.3) * N**-0.2)
    return None


def friction_coefficient(m1: Polymer, m2: Polymer, lub: Lubrication) -> float | None:
    """μ medio secondo VDI 2736-2 Tab. 2; None se la combinazione non è tabellata."""
    if lub is Lubrication.OIL_INJECTION:
        return 0.04
    if lub is Lubrication.OIL_MIST:
        return 0.07
    if lub is Lubrication.GREASE:
        return 0.09
    pair = frozenset((m1, m2))
    if Polymer.STEEL in pair and len(pair) == 2:
        return 0.20
    return _DRY_MU.get(pair)


_DRY_MU: dict[frozenset[Polymer], float] = {
    frozenset((Polymer.PA66,)): 0.40,
    frozenset((Polymer.POM,)): 0.28,
    frozenset((Polymer.POM, Polymer.PA66)): 0.18,
    frozenset((Polymer.PA66, Polymer.PBT)): 0.35,
    frozenset((Polymer.POM, Polymer.PBT)): 0.18,
}


def heat_transfer_coefficients(m1: Polymer, m2: Polymer, lub: Lubrication) -> tuple[float, float]:
    """(k_θ,Fuß, k_θ,Fla) [K·(m/s)^0.75·mm^1.75/W] secondo VDI 2736-2 Tab. 3."""
    if lub is Lubrication.OIL_INJECTION:
        return 0.0, 0.0
    if Polymer.STEEL in (m1, m2):
        return 900.0, 6300.0
    return 2100.0, 9000.0


def wear_coefficient(plastic: Polymer, counterpart: Polymer, steel_Rz: float) -> float | None:
    """k_W [mm³/(N·m)] a secco contro acciaio, VDI 2736-2 Tab. 6 (interpolazione lineare in Rz
    tra 0.45 e 1.5 µm, estremi mantenuti fuori intervallo). None se non tabellato."""
    if counterpart is not Polymer.STEEL:
        return None
    table = {Polymer.POM: (1.0e-6, 3.4e-6), Polymer.PBT: (3.7e-6, 7.8e-6)}
    if plastic not in table:
        return None
    lo, hi = table[plastic]
    t = min(max((steel_Rz - 0.45) / (1.5 - 0.45), 0.0), 1.0)
    return lo + t * (hi - lo)
