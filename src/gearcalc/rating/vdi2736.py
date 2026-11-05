"""Verifica di ruote cilindriche in termoplastico secondo VDI 2736-2:2014.

Sequenza (flusso di calcolo della norma):
    1. temperature del dente al piede θ_Fuß e al fianco θ_Fla (eq. 7–9);
    2. resistenza al piede σ_F ≤ σ_FP con σ_FG = Y_ST·σ_FlimN(θ_Fuß, N_L) (eq. 10–13);
    3. resistenza del fianco σ_H ≤ σ_HP con σ_HlimN(θ_Fla, N_L) (eq. 14–17);
    4. usura a secco W_m ≤ W_zul (eq. 18–21);
    5. deformazione del dente λ ≤ 0.07·m_n (eq. 22).

Ipotesi e limiti:
    - solo coppie esterne (le interne richiedono Y_Fa/Y_Sa da coltello stozzatore);
    - K_F = K_H = K_A·K_v·K_β·K_α con K_v = K_β = K_α = 1 di default, come raccomanda la
      norma per ruote in plastica con b/m_n ≤ 12 (verificato con avviso);
    - curve di resistenza valide per N_L = 1e5 … 1e8: sotto 1e5 si usa 1e5 (a favore di
      sicurezza), oltre 1e8 si estrapola con avviso;
    - termine del carter R_λ,G / A_G con P in W: θ in K;
    - verifica a carico di picco (σ_S) non ancora implementata.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gearcalc.errors import GearCalcError
from gearcalc.geometry.pair import pair_geometry
from gearcalc.models import GearPair, PairGeometry
from gearcalc.rating.materials import (
    Lubrication,
    Material,
    flank_strength,
    friction_coefficient,
    heat_transfer_coefficients,
    root_strength,
    wear_coefficient,
)
from gearcalc.rating.root_form import root_form_factors

N_MIN, N_MAX = 1.0e5, 1.0e8
Y_ST = 2.0


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Housing(_Frozen):
    """Carter (VDI 2736-2 Tab. 4): aperto R=0; parzialmente aperto 0.015–0.045; chiuso 0.06."""

    R_lambda_G: float = Field(0.0, ge=0.0, description="Resistenza termica del carter [m²·K/W]")
    A_G: float = Field(0.0, ge=0.0, description="Superficie di scambio del carter [m²]")

    @model_validator(mode="after")
    def _check(self) -> Housing:
        if self.R_lambda_G > 0.0 and self.A_G <= 0.0:
            raise ValueError("Con R_lambda_G > 0 serve la superficie del carter A_G > 0")
        return self


class OperatingConditions(_Frozen):
    T_1: float = Field(..., gt=0.0, description="Coppia nominale sul pignone [N·m]")
    n_1: float = Field(..., gt=0.0, description="Velocità del pignone [min⁻¹]")
    life_hours: float = Field(..., gt=0.0, description="Durata richiesta [h]")
    theta_0: float = Field(23.0, description="Temperatura ambiente [°C]")
    ED: float = Field(1.0, gt=0.0, le=1.0, description="Durata relativa d'inserzione (su 10 min)")
    K_A: float = Field(1.0, ge=1.0, description="Fattore di applicazione")
    K_v: float = Field(1.0, ge=1.0)
    K_beta: float = Field(1.0, ge=1.0)
    K_alpha: float = Field(1.0, ge=1.0)


class VDI2736Input(_Frozen):
    pair: GearPair
    material1: Material
    material2: Material
    lubrication: Lubrication
    operating: OperatingConditions
    housing: Housing = Field(default_factory=Housing)
    mu: float | None = Field(
        None, gt=0.0, description="Coefficiente d'attrito (sostituisce Tab. 2)"
    )
    k_W1: float | None = Field(None, gt=0.0, description="Coefficiente d'usura ruota 1 [mm³/(N·m)]")
    k_W2: float | None = Field(None, gt=0.0, description="Coefficiente d'usura ruota 2 [mm³/(N·m)]")
    steel_Rz: float = Field(0.45, gt=0.0, description="Rugosità della controruota in acciaio [µm]")
    W_zul_star: float = Field(0.1, gt=0.0, le=0.3, description="Usura ammissibile W_zul / m_n")
    S_Fmin: float = Field(2.0, gt=0.0)
    S_Hmin: float = Field(1.4, gt=0.0)
    lambda_zul_star: float = Field(0.07, gt=0.0, description="Deformazione ammissibile / m_n")

    @model_validator(mode="after")
    def _check(self) -> VDI2736Input:
        if self.pair.gear2.internal:
            raise ValueError("VDI 2736: coppie interne non ancora supportate")
        if self.material1.is_steel and self.material2.is_steel:
            raise ValueError("VDI 2736 richiede almeno una ruota in termoplastico")
        return self


class GearRatingVDI(_Frozen):
    """Risultati per una ruota. ``None`` = verifica non eseguibile (dati mancanti o acciaio)."""

    theta_root: float = Field(description="Temperatura al piede θ_Fuß [°C]")
    theta_flank: float = Field(description="Temperatura del fianco θ_Fla [°C]")
    N_L: float = Field(description="Cicli di carico")
    Y_Fa: float
    Y_Sa: float
    sigma_F: float = Field(description="Tensione al piede [MPa]")
    sigma_FlimN: float | None = Field(description="Resistenza a fatica al piede [MPa]")
    S_F: float | None = Field(description="Sicurezza al piede Y_ST·σ_FlimN/σ_F")
    sigma_HlimN: float | None = Field(description="Resistenza a fatica del fianco [MPa]")
    S_H: float | None = Field(description="Sicurezza del fianco σ_HlimN/σ_H")
    l_Fl: float = Field(description="Lunghezza del fianco attivo [mm]")
    W_m: float | None = Field(description="Usura media lineare [mm]")
    W_zul: float = Field(description="Usura ammissibile [mm]")
    E_root: float = Field(description="Modulo elastico alla temperatura del piede [MPa]")


class VDI2736Result(_Frozen):
    geometry: PairGeometry
    F_t: float = Field(description="Forza tangenziale al primitivo di riferimento [N]")
    v_t: float = Field(description="Velocità periferica [m/s]")
    P: float = Field(description="Potenza [W]")
    mu: float
    H_V: float = Field(description="Grado di perdita")
    sigma_H: float = Field(description="Pressione di contatto [MPa]")
    Z_E: float
    Z_H: float
    Z_eps: float
    Z_beta: float
    Y_eps: float
    Y_beta: float
    lambda_: float = Field(description="Deformazione del dente [mm]")
    lambda_zul: float
    gear1: GearRatingVDI | None
    gear2: GearRatingVDI | None
    warnings: tuple[str, ...]


def loss_factor(geo: PairGeometry) -> float:
    """Grado di perdita H_V (VDI 2736-2 eq. 8, Niemann).

    H_V = π·(1/z1 + 1/z2)/cos β_b · (1 − ε_α + ε_1² + ε_2²),  ε_i = g_ai / p_bt.
    Ipotesi: carico ripartito in parti uguali tra le coppie in presa; 1 ≤ ε_α ≤ 2, ε_i ≤ 1.
    """
    tan_wt = math.tan(math.radians(geo.alpha_wt))
    r_b1, r_b2 = geo.gear1.d_b / 2.0, geo.gear2.d_b / 2.0
    g_a1 = math.sqrt((geo.gear1.d_a / 2.0) ** 2 - r_b1**2) - r_b1 * tan_wt
    g_a2 = math.sqrt((geo.gear2.d_a / 2.0) ** 2 - r_b2**2) - r_b2 * tan_wt
    p = geo.gear1.p_bt
    e1, e2 = g_a1 / p, g_a2 / p
    cos_bb = math.cos(math.radians(geo.gear1.beta_b))
    return (
        math.pi
        * (1.0 / geo.gear1.z + 1.0 / geo.gear2.z)
        / cos_bb
        * (1.0 - (e1 + e2) + e1**2 + e2**2)
    )


def _tooth_temperature(
    theta_0: float,
    P: float,
    mu: float,
    H_V: float,
    k: float,
    b: float,
    z: int,
    v_t: float,
    m_n: float,
    housing: Housing,
    ED: float,
) -> float:
    gear_term = k / (b * z * (v_t * m_n) ** 0.75)
    housing_term = housing.R_lambda_G / housing.A_G if housing.R_lambda_G > 0.0 else 0.0
    return float(theta_0 + P * mu * H_V * (gear_term + housing_term) * ED**0.64)


def rate_vdi2736(inp: VDI2736Input) -> VDI2736Result:
    """Esegue la verifica VDI 2736-2 della coppia."""
    pair, op, lub = inp.pair, inp.operating, inp.lubrication
    m1, m2 = inp.material1, inp.material2
    geo = pair_geometry(pair)
    g1, g2 = geo.gear1, geo.gear2
    warnings: list[str] = list(geo.warnings)
    m_n = g1.m_n
    b = geo.b_eff
    u = geo.u

    F_t = 2000.0 * op.T_1 / g1.d
    v_t = math.pi * g1.d * op.n_1 / 60000.0
    P = op.T_1 * 2.0 * math.pi * op.n_1 / 60.0

    mu = inp.mu if inp.mu is not None else friction_coefficient(m1.polymer, m2.polymer, lub)
    if mu is None:
        raise GearCalcError(
            f"Coefficiente d'attrito a secco non tabellato per {m1.polymer}/{m2.polymer}: "
            "fornire mu"
        )
    H_V = loss_factor(geo)
    if not 1.0 <= geo.epsilon_alpha <= 2.0:
        warnings.append(f"H_V: ε_α = {geo.epsilon_alpha:.3f} fuori dal campo 1…2 della formula")
    k_root, k_flank = heat_transfer_coefficients(m1.polymer, m2.polymer, lub)

    K = op.K_A * op.K_v * op.K_beta * op.K_alpha
    if b / m_n > 12.0 and op.K_beta == 1.0:
        warnings.append(f"b/m_n = {b / m_n:.1f} > 12: K_β = 1 non giustificato")

    eps_b = min(geo.epsilon_beta, 1.0)
    beta_abs = abs(g1.beta)
    Y_eps = 0.25 + 0.75 / geo.epsilon_alpha
    Y_beta = 1.0 - eps_b * min(beta_abs, 30.0) / 120.0

    # temperature e materiali per ruota
    N_L1 = 60.0 * op.n_1 * op.life_hours
    N_L2 = N_L1 / abs(u)
    thetas: list[tuple[float, float]] = []
    for z, mat in ((g1.z, m1), (g2.z, m2)):
        if mat.is_steel:
            thetas.append((op.theta_0, op.theta_0))
            continue
        tr = _tooth_temperature(op.theta_0, P, mu, H_V, k_root, b, z, v_t, m_n, inp.housing, op.ED)
        tf = _tooth_temperature(op.theta_0, P, mu, H_V, k_flank, b, z, v_t, m_n, inp.housing, op.ED)
        thetas.append((tr, tf))

    # contatto (moduli alla temperatura del fianco)
    E1f, E2f = m1.elastic_modulus(thetas[0][1]), m2.elastic_modulus(thetas[1][1])
    nu1, nu2 = m1.poisson(), m2.poisson()
    Z_E = math.sqrt(1.0 / (math.pi * ((1 - nu1**2) / E1f + (1 - nu2**2) / E2f)))
    a_t = math.radians(g1.alpha_t)
    a_wt = math.radians(geo.alpha_wt)
    beta_b = math.radians(g1.beta_b)
    Z_H = math.sqrt(2.0 * math.cos(beta_b) * math.cos(a_wt) / (math.cos(a_t) ** 2 * math.sin(a_wt)))
    ea = geo.epsilon_alpha
    if geo.epsilon_beta < 1.0:
        Z_eps = math.sqrt((4.0 - ea) / 3.0 * (1.0 - geo.epsilon_beta) + geo.epsilon_beta / ea)
    else:
        Z_eps = math.sqrt(1.0 / ea)
    Z_beta = math.sqrt(math.cos(math.radians(beta_abs)))
    sigma_H = Z_E * Z_H * Z_eps * Z_beta * math.sqrt(K * F_t * (u + 1.0) / (b * g1.d * u))

    # deformazione (moduli alla temperatura del piede)
    E1r, E2r = m1.elastic_modulus(thetas[0][0]), m2.elastic_modulus(thetas[1][0])
    lam = 7.5 * F_t / (b * math.cos(math.radians(beta_abs))) * (1.0 / E1r + 1.0 / E2r)
    lam_zul = inp.lambda_zul_star * m_n
    if lam > lam_zul:
        warnings.append(
            f"Deformazione λ = {lam:.4f} mm > {inp.lambda_zul_star}·m_n: valutare la "
            "correzione di testa o ridurre il carico"
        )

    W_zul = inp.W_zul_star * m_n
    results: list[GearRatingVDI | None] = []
    sides = (
        (1, g1, m1, m2, N_L1, thetas[0], geo.d_Nf1, inp.k_W1, op.T_1),
        (2, g2, m2, m1, N_L2, thetas[1], geo.d_Nf2, inp.k_W2, op.T_1 * abs(u)),
    )
    for i, gg, mat, other, N_L, (t_root, t_flank), d_Nf, k_W_in, T_i in sides:
        if mat.is_steel:
            results.append(None)
            continue
        rf = root_form_factors(gg)
        sigma_F = K * rf.Y_Fa * rf.Y_Sa * Y_eps * Y_beta * F_t / (b * m_n)
        N_eff = max(N_L, N_MIN)
        if N_L > N_MAX:
            warnings.append(f"Ruota {i}: N_L = {N_L:.2e} > 1e8, curve di resistenza estrapolate")
        s_Flim = root_strength(mat, t_root, N_eff)
        S_F = Y_ST * s_Flim / sigma_F if s_Flim is not None and s_Flim > 0 else None
        if s_Flim is None:
            warnings.append(f"Ruota {i} ({mat.polymer}): σ_FlimN non disponibile in VDI 2736")
        elif S_F is not None and inp.S_Fmin > S_F:
            warnings.append(f"Ruota {i}: S_F = {S_F:.2f} < S_Fmin = {inp.S_Fmin}")
        s_Hlim = flank_strength(mat, t_flank, N_eff, lub)
        S_H = s_Hlim / sigma_H if s_Hlim is not None and s_Hlim > 0 else None
        if s_Hlim is None:
            warnings.append(
                f"Ruota {i} ({mat.polymer}, {lub}): σ_HlimN non disponibile in VDI 2736 — "
                + (
                    "a secco governa l'usura"
                    if lub is Lubrication.DRY
                    else "per POM lubrificato la norma ritiene critico il piede"
                )
            )
        elif S_H is not None and inp.S_Hmin > S_H:
            warnings.append(f"Ruota {i}: S_H = {S_H:.2f} < S_Hmin = {inp.S_Hmin}")
        if max(t_root, t_flank) > mat.max_temperature():
            warnings.append(
                f"Ruota {i}: temperatura {max(t_root, t_flank):.0f} °C oltre il limite "
                f"d'impiego {mat.max_temperature():.0f} °C del {mat.polymer}"
            )

        # usura (solo a secco)
        r_b = gg.d_b / 2.0
        l_Fl = ((gg.d_a / 2.0) ** 2 - (d_Nf / 2.0) ** 2) / (2.0 * r_b)
        W_m: float | None = None
        if lub is Lubrication.DRY:
            k_W = (
                k_W_in
                if k_W_in is not None
                else wear_coefficient(mat.polymer, other.polymer, inp.steel_Rz)
            )
            if k_W is None:
                warnings.append(f"Ruota {i}: k_W non tabellato per {mat.polymer}/{other.polymer}")
            else:
                W_m = T_i * 2.0 * math.pi * N_L * H_V * k_W / (b * gg.z * l_Fl)
                if W_m > W_zul:
                    warnings.append(f"Ruota {i}: usura W_m = {W_m:.3f} mm > W_zul = {W_zul:.3f} mm")

        results.append(
            GearRatingVDI(
                theta_root=t_root,
                theta_flank=t_flank,
                N_L=N_L,
                Y_Fa=rf.Y_Fa,
                Y_Sa=rf.Y_Sa,
                sigma_F=sigma_F,
                sigma_FlimN=s_Flim,
                S_F=S_F,
                sigma_HlimN=s_Hlim,
                S_H=S_H,
                l_Fl=l_Fl,
                W_m=W_m,
                W_zul=W_zul,
                E_root=mat.elastic_modulus(t_root),
            )
        )

    return VDI2736Result(
        geometry=geo,
        F_t=F_t,
        v_t=v_t,
        P=P,
        mu=mu,
        H_V=H_V,
        sigma_H=sigma_H,
        Z_E=Z_E,
        Z_H=Z_H,
        Z_eps=Z_eps,
        Z_beta=Z_beta,
        Y_eps=Y_eps,
        Y_beta=Y_beta,
        lambda_=lam,
        lambda_zul=lam_zul,
        gear1=results[0],
        gear2=results[1],
        warnings=tuple(warnings),
    )
