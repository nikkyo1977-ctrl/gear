"""Vite in acciaio / ruota in termoplastico: rendimento, forze, temperatura, piede, usura.

**Impostazione adattata (non normativa).** La ISO/TS 14521 e la DIN 3996 sono scritte per
ruote in bronzo; per le ruote in plastica il riferimento specifico è la VDI 2736-3, non
ancora recepita in questo codice. Qui si combinano:

    - cinematica, forze e rendimento della coppia vite-ruota (relazioni esatte con
      angolo d'attrito ρ' = atan(μ / cos α_n));
    - attrito secondo VDI 2736-2 Tab. 2 (plastica/acciaio a secco 0.20, grasso 0.09);
    - temperatura del dente della ruota con la struttura delle eq. 7/9 della VDI 2736-2, ma con
      la potenza dissipata P_V = P1 − P2 e la velocità di strisciamento v_g al posto di
      P·μ·H_V e v_t: **stima**, da tarare con prove o con la VDI 2736-3. È possibile
      imporre la temperatura misurata con ``theta_wheel``;
    - piede della ruota come ruota elicoidale virtuale del piano medio (z2, β = γ_m) con
      Y_Fa, Y_Sa da geometria reale e σ_FG = Y_ST·σ_FlimN (VDI 2736-2);
    - usura a secco con legge di Archard coerente con la VDI 2736-2:
      W_m = k_W·F_n·v_g·t / (z2·b2·l_Fl).

Non sono verificati: pitting del fianco della ruota (per le plastiche raramente critico
rispetto a temperatura e usura), rottura per taglio con il metodo ISO/TS 14521, carico di picco.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gearcalc.errors import GearCalcError
from gearcalc.geometry.cylindrical import gear_geometry
from gearcalc.geometry.worm import WormGearSet, WormGeometry, virtual_wheel, worm_geometry
from gearcalc.rating.materials import (
    Lubrication,
    Material,
    Polymer,
    friction_coefficient,
    heat_transfer_coefficients,
    root_strength,
    wear_coefficient,
)
from gearcalc.rating.root_form import root_form_factors
from gearcalc.rating.vdi2736 import N_MAX, N_MIN, Y_ST, Housing


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class WormOperating(_Frozen):
    T_2: float = Field(..., gt=0.0, description="Coppia sulla ruota (uscita) [N·m]")
    n_1: float = Field(..., gt=0.0, description="Velocità della vite [min⁻¹]")
    life_hours: float = Field(..., gt=0.0, description="Ore di funzionamento sotto carico [h]")
    theta_0: float = Field(23.0, description="Temperatura ambiente [°C]")
    ED: float = Field(1.0, gt=0.0, le=1.0, description="Durata relativa d'inserzione")
    K_A: float = Field(1.0, ge=1.0, description="Fattore di applicazione")


class WormPlasticInput(_Frozen):
    gearset: WormGearSet
    wheel_material: Material
    lubrication: Lubrication
    operating: WormOperating
    housing: Housing = Field(default_factory=Housing)
    mu: float | None = Field(None, gt=0.0, description="Attrito (sostituisce VDI 2736-2 Tab. 2)")
    mu_static: float | None = Field(
        None, gt=0.0, description="Attrito statico per la verifica di autobloccaggio da fermo"
    )
    theta_wheel: float | None = Field(
        None, description="Temperatura del dente della ruota imposta (misurata) [°C]"
    )
    k_W: float | None = Field(None, gt=0.0, description="Coefficiente d'usura [mm³/(N·m)]")
    steel_Rz: float = Field(0.45, gt=0.0, description="Rugosità del fianco della vite [µm]")
    W_zul_star: float = Field(0.1, gt=0.0, le=0.3, description="Usura ammissibile / m")
    S_Fmin: float = Field(2.0, gt=0.0)
    bearing_span: float | None = Field(None, gt=0.0, description="Interasse cuscinetti vite [mm]")
    E_worm: float = Field(206000.0, gt=0.0, description="Modulo elastico della vite [MPa]")
    delta_lim_star: float = Field(
        0.01, gt=0.0, description="Freccia ammissibile della vite / m (valore guida)"
    )

    @model_validator(mode="after")
    def _check(self) -> WormPlasticInput:
        if self.wheel_material.is_steel:
            raise ValueError("Questo modulo verifica ruote in termoplastico")
        return self


class WormPlasticResult(_Frozen):
    geometry: WormGeometry
    v_1: float = Field(description="Velocità periferica della vite [m/s]")
    v_g: float = Field(description="Velocità di strisciamento [m/s]")
    n_2: float = Field(description="Velocità della ruota [min⁻¹]")
    mu: float
    rho_prime: float = Field(description="Angolo d'attrito ρ' = atan(μ/cos α_n) [°]")
    eta: float = Field(description="Rendimento con vite motrice")
    eta_back: float = Field(description="Rendimento con ruota motrice (≤ 0: irreversibile)")
    self_locking_dynamic: bool = Field(description="γ_m ≤ ρ' con l'attrito di funzionamento")
    self_locking_static: bool | None = Field(description="γ_m ≤ ρ'_0 (solo se mu_static dato)")
    T_1: float = Field(description="Coppia richiesta alla vite [N·m]")
    P_1: float = Field(description="Potenza in ingresso [W]")
    P_V: float = Field(description="Potenza dissipata nell'ingranamento [W]")
    F_t2: float = Field(description="Forza tangenziale ruota = assiale vite [N]")
    F_t1: float = Field(description="Forza tangenziale vite = assiale ruota [N]")
    F_r: float = Field(description="Forza radiale [N]")
    F_n: float = Field(description="Forza normale al fianco [N]")
    theta_root: float = Field(description="Temperatura al piede della ruota [°C]")
    theta_flank: float = Field(description="Temperatura del fianco della ruota [°C]")
    temperature_estimated: bool
    N_L2: float = Field(description="Cicli di carico per dente della ruota")
    Y_Fa: float
    Y_Sa: float
    Y_eps: float
    Y_beta: float
    sigma_F: float = Field(description="Tensione al piede della ruota [MPa]")
    sigma_FlimN: float | None
    S_F: float | None
    l_Fl: float = Field(description="Lunghezza del fianco attivo della ruota (piano medio) [mm]")
    W_m: float | None = Field(description="Usura media lineare del fianco della ruota [mm]")
    W_zul: float
    delta: float | None = Field(description="Freccia della vite [mm]")
    delta_lim: float
    warnings: tuple[str, ...]


def efficiency(gamma: float, rho_prime: float) -> tuple[float, float]:
    """(η vite motrice, η ruota motrice) = (tan γ / tan(γ+ρ'), tan(γ−ρ') / tan γ)."""
    return math.tan(gamma) / math.tan(gamma + rho_prime), math.tan(gamma - rho_prime) / math.tan(
        gamma
    )


def rate_worm_plastic(inp: WormPlasticInput) -> WormPlasticResult:
    ws, op, mat, lub = inp.gearset, inp.operating, inp.wheel_material, inp.lubrication
    geo = worm_geometry(ws)
    w: list[str] = list(geo.warnings)
    m = ws.m
    gamma = math.radians(geo.gamma_m)
    a_n = math.radians(geo.alpha_n)

    v_1 = math.pi * geo.d_m1 * op.n_1 / 60000.0
    v_g = v_1 / math.cos(gamma)
    n_2 = op.n_1 / geo.i

    mu = inp.mu if inp.mu is not None else friction_coefficient(Polymer.STEEL, mat.polymer, lub)
    if mu is None:
        raise GearCalcError("Coefficiente d'attrito non disponibile: fornire mu")
    rho = math.atan(mu / math.cos(a_n))
    eta, eta_back = efficiency(gamma, rho)
    if eta <= 0.0:
        raise GearCalcError("Rendimento nullo: attrito troppo elevato per questo γ_m")
    self_dyn = gamma <= rho
    self_static: bool | None = None
    if inp.mu_static is not None:
        self_static = gamma <= math.atan(inp.mu_static / math.cos(a_n))
    if self_dyn:
        w.append(
            "Irreversibile in moto (γ_m ≤ ρ'); con vibrazioni l'autobloccaggio non è garantito"
        )

    # forze (vite motrice), carico di calcolo con K_A
    T2 = op.T_2 * op.K_A
    F_t2 = 2000.0 * T2 / geo.d_2
    F_n = F_t2 / (math.cos(a_n) * math.cos(gamma) - mu * math.sin(gamma))
    F_t1 = F_n * (math.cos(a_n) * math.sin(gamma) + mu * math.cos(gamma))
    F_r = F_n * math.sin(a_n)
    T_1 = op.T_2 / (geo.i * eta)
    P_2 = op.T_2 * 2.0 * math.pi * n_2 / 60.0
    P_1 = P_2 / eta
    P_V = P_1 - P_2

    # temperatura della ruota
    b2 = geo.b2_eff
    if inp.theta_wheel is not None:
        t_root = t_flank = inp.theta_wheel
        estimated = False
    else:
        k_root, k_flank = heat_transfer_coefficients(Polymer.STEEL, mat.polymer, lub)
        housing = inp.housing.R_lambda_G / inp.housing.A_G if inp.housing.R_lambda_G > 0 else 0.0

        def theta(k: float) -> float:
            return float(
                op.theta_0 + P_V * (k / (b2 * ws.z2 * (v_g * m) ** 0.75) + housing) * op.ED**0.64
            )

        t_root, t_flank = theta(k_root), theta(k_flank)
        estimated = True
        w.append(
            "Temperatura della ruota stimata con modello VDI 2736-2 adattato (P_V, v_g): "
            "valore indicativo, da verificare con prove o imporre con theta_wheel"
        )
    if max(t_root, t_flank) > mat.max_temperature():
        w.append(
            f"Temperatura ruota {max(t_root, t_flank):.0f} °C oltre il limite d'impiego "
            f"{mat.max_temperature():.0f} °C del {mat.polymer}"
        )

    # piede della ruota (ruota elicoidale virtuale)
    vgeo = gear_geometry(virtual_wheel(ws))
    rf = root_form_factors(vgeo)
    Y_eps = 0.25 + 0.75 / geo.epsilon_alpha
    eps_beta = min(b2 * math.sin(gamma) / (math.pi * geo.m_n), 1.0)
    Y_beta = 1.0 - eps_beta * min(geo.gamma_m, 30.0) / 120.0
    sigma_F = rf.Y_Fa * rf.Y_Sa * Y_eps * Y_beta * F_t2 / (b2 * geo.m_n)
    N_L2 = 60.0 * n_2 * op.life_hours
    if N_L2 > N_MAX:
        w.append(f"N_L2 = {N_L2:.2e} > 1e8: curve di resistenza estrapolate")
    s_Flim = root_strength(mat, t_root, max(N_L2, N_MIN))
    S_F = Y_ST * s_Flim / sigma_F if s_Flim is not None and s_Flim > 0 else None
    if s_Flim is None:
        w.append(f"σ_FlimN non disponibile per {mat.polymer}: fornire sigma_FlimN")
    elif S_F is not None and inp.S_Fmin > S_F:
        w.append(f"Ruota: S_F = {S_F:.2f} < S_Fmin = {inp.S_Fmin}")

    # usura (a secco): Archard, lavoro d'attrito/μ = F_n·v_g·t
    # fianco attivo nel piano medio: dalla testa della ruota al punto in cui la testa della
    # vite (dentiera) interseca la retta d'azione; lunghezza d'arco dell'evolvente
    a_x = math.radians(geo.alpha_x)
    r_2 = geo.d_2 / 2.0
    r_b2 = vgeo.d_b / 2.0
    rho_start = max(r_2 * math.sin(a_x) - (ws.h_a_star - ws.x2) * m / math.sin(a_x), 0.0)
    rho_tip = math.sqrt((geo.d_a2 / 2.0) ** 2 - r_b2**2)
    l_Fl = (rho_tip**2 - rho_start**2) / (2.0 * r_b2)
    W_zul = inp.W_zul_star * m
    W_m: float | None = None
    if lub is Lubrication.DRY:
        k_W = (
            inp.k_W
            if inp.k_W is not None
            else wear_coefficient(mat.polymer, Polymer.STEEL, inp.steel_Rz)
        )
        if k_W is None:
            w.append(f"k_W non tabellato per {mat.polymer}/acciaio: fornire k_W")
        else:
            t = op.life_hours * 3600.0
            W_m = k_W * (F_n / op.K_A) * v_g * t / (ws.z2 * b2 * l_Fl)
            if W_m > W_zul:
                w.append(f"Usura W_m = {W_m:.3f} mm > W_zul = {W_zul:.3f} mm")

    # freccia della vite (trave appoggiata, carico in mezzeria, sezione al piede)
    delta: float | None = None
    delta_lim = inp.delta_lim_star * m
    if inp.bearing_span is not None:
        I_f1 = math.pi * geo.d_f1**4 / 64.0
        delta = math.hypot(F_t1, F_r) * inp.bearing_span**3 / (48.0 * inp.E_worm * I_f1)
        if delta > delta_lim:
            w.append(f"Freccia della vite {delta:.4f} mm > {inp.delta_lim_star}·m")

    return WormPlasticResult(
        geometry=geo,
        v_1=v_1,
        v_g=v_g,
        n_2=n_2,
        mu=mu,
        rho_prime=math.degrees(rho),
        eta=eta,
        eta_back=eta_back,
        self_locking_dynamic=self_dyn,
        self_locking_static=self_static,
        T_1=T_1,
        P_1=P_1,
        P_V=P_V,
        F_t2=F_t2,
        F_t1=F_t1,
        F_r=F_r,
        F_n=F_n,
        theta_root=t_root,
        theta_flank=t_flank,
        temperature_estimated=estimated,
        N_L2=N_L2,
        Y_Fa=rf.Y_Fa,
        Y_Sa=rf.Y_Sa,
        Y_eps=Y_eps,
        Y_beta=Y_beta,
        sigma_F=sigma_F,
        sigma_FlimN=s_Flim,
        S_F=S_F,
        l_Fl=l_Fl,
        W_m=W_m,
        W_zul=W_zul,
        delta=delta,
        delta_lim=delta_lim,
        warnings=tuple(w),
    )
