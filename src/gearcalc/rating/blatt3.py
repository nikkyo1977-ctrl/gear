"""VDI 2736 Blatt 3:2014-05, §§3.1–3.2.2. Vite metallica motrice, assi a 90°.

Geometria effettiva a metà tolleranza, ruota semicristallina. Quote in mm, angoli
in gradi (moduli), forze in N, tensioni in MPa. Carico costante sulla ruota.
"""

import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from gearcalc.errors import GeometryError
from gearcalc.geometry.involute import inv

Positive = Annotated[float, Field(gt=0)]
Angle = Annotated[float, Field(ge=0, lt=90)]
Source = Annotated[str, Field(min_length=1, pattern=r"\S")]


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class Blatt3Geometry(_Model):
    """1 = vite, 2 = ruota. d_s: lavoro, d_b: base, d_a: testa, d_m1: medio vite.

    d_form1/2: limiti superiori attivi per il ricoprimento con teste modificate.
    beta_s1: elica di lavoro vite, beta_b: eliche di base, beta_2: elica di riferimento
    ruota, gamma_m1: inclinazione della vite al diametro medio.
    """

    shaft_angle: Literal[90] = 90
    z1: int = Field(ge=1, lt=6)
    z2: int = Field(gt=0)
    m_n: float = Field(gt=0.3)
    a: Positive
    d_s1: Positive
    d_s2: Positive
    d_b1: Positive
    d_b2: Positive
    d_a1: Positive
    d_a2: Positive
    d_form1: Positive | None = None
    d_form2: Positive | None = None
    d_m1: Positive
    d_2: Positive
    b_2: Positive
    alpha_n: float = Field(gt=0, lt=90)
    beta_s1: Angle
    beta_b1: Angle
    beta_b2: Angle
    beta_2: Angle
    gamma_m1: float = Field(gt=0, lt=90)
    x2: float
    undercut2: bool = False
    epsilon_n_reference: Positive | None = Field(
        default=None, description="Ricoprimento dichiarato per confronto con la geometria attiva"
    )


class Blatt3Limit(_Model):
    """Limite esplicito [MPa], con fonte pertinente al materiale e al servizio."""

    value: Positive
    source: Source


class Blatt3FlankInput(_Model):
    """Elasticità isotropa alla temperatura di contatto. E in MPa, μ di esercizio."""

    E_1: Positive
    nu_1: float = Field(gt=-1, le=0.5)
    E_2: Positive
    nu_2: float = Field(gt=-1, le=0.5)
    mu: float = Field(ge=0)
    epsilon_source: Literal["geometry", "reference"] = "geometry"
    sigma_HP: Blatt3Limit | None = None


class Blatt3Input(_Model):
    geometry: Blatt3Geometry
    wheel_grade: Source = Field(description="Grado della ruota termoplastica semicristallina")
    theta_M: float = Field(gt=-273.15, description="Temperatura di massa ruota [°C]")
    T_2: Positive = Field(description="Coppia nominale in uscita [N·m]")
    n_1: Positive = Field(description="Velocità della vite [giri/min]")
    life_hours: Positive
    K_A: float = Field(default=1, ge=1)
    strong_self_heating: bool = False
    C_lim: Blatt3Limit | None = Field(
        default=None, description="Alla velocità e lubrificazione date"
    )
    sigma_ZSch: Blatt3Limit | None = Field(default=None, description="A theta_M e N_L della ruota")
    flank: Blatt3FlankInput | None = None


class Blatt3FlankResult(_Model):
    """Eq. (22)–(34). Angoli in gradi, lunghezze in mm, forza in N, pressione in MPa."""

    epsilon_source: Literal["geometry", "reference"]
    epsilon_used: float
    Z_epsilonS: float
    alpha_sn: float
    rho_z: float
    F_n: float
    rho_n1: float
    rho_n2: float
    rho_n: float
    phi: float
    theta: float
    eta: float
    xi: float
    Z_F: float
    a_h: float
    b_h: float
    sigma_Hm: float
    flank_ok: bool | None


class Blatt3Result(_Model):
    inputs: Blatt3Input
    n_2: float
    N_L: float
    F_t2: float
    v_gs: float
    m_x1: float
    b_m: float
    K_z: float | None
    C: float | None
    S_C: float | None
    S_Cmin: float
    preliminary_ok: bool | None
    g_an1: float
    g_an2: float
    epsilon_n: float
    epsilon_n_difference: float | None
    epsilon_nz: int
    Y_eps: float
    b_max: float
    d_x0: float
    used_reference_thickness: bool
    s_t2: float
    s_da1: float
    s_at2: float
    A_tau: float
    tau_F: float
    tau_Flim: float | None
    S_F: float | None
    S_Fmin: float
    root_ok: bool | None
    flank: Blatt3FlankResult | None = None
    warnings: tuple[str, ...]


def _contact_length(tip: float, working: float, base: float, beta_base: float) -> float:
    """Lunghezza di accesso/recesso normale, §3.2.1, eq. (11)-(12)."""
    if not base <= working <= tip:
        raise GeometryError("Richiesti d_b ≤ d_s ≤ diametro di testa attivo")
    return (math.sqrt(tip**2 - base**2) - math.sqrt(working**2 - base**2)) / (
        2 * math.cos(math.radians(beta_base))
    )


def _flank_contact(
    g: Blatt3Geometry, flank: Blatt3FlankInput, epsilon_n: float, F_t2: float, K_A: float
) -> Blatt3FlankResult:
    """Contatto ellittico con vite motrice (§3.2.2); assi perpendicolari."""
    rad = math.radians
    beta1 = rad(90 - g.gamma_m1)
    beta_s1 = rad(g.beta_s1)
    if beta_s1 == 0:
        raise GeometryError("Elica di lavoro della vite nulla")
    cos_alpha_sn = math.sin(beta1) * math.cos(rad(g.alpha_n)) / math.sin(beta_s1)
    if cos_alpha_sn > 1 + 1e-14:
        raise GeometryError("Angoli incompatibili con la pressione normale di lavoro")
    alpha_sn = math.acos(min(1.0, cos_alpha_sn))
    rho_z = math.atan(flank.mu / math.cos(alpha_sn))
    beta_s2 = rad(90 - g.beta_s1)
    if rho_z >= beta_s1:
        raise GeometryError("Attrito e angoli incompatibili con la vite motrice")
    F_n = F_t2 * math.cos(rho_z) / (math.cos(alpha_sn) * math.cos(beta_s2 + rho_z))

    rho_n1 = math.sqrt(g.d_s1**2 - g.d_b1**2) / (2 * math.cos(rad(g.beta_b1)))
    rho_n2 = math.sqrt(g.d_s2**2 - g.d_b2**2) / (2 * math.cos(rad(g.beta_b2)))
    if min(rho_n1, rho_n2) <= 0:
        raise GeometryError("Raggio di curvatura nullo al punto di lavoro")
    rho_n = 1 / (1 / rho_n1 + 1 / rho_n2)
    sin_alpha = math.sin(rad(g.alpha_n))
    phi = math.atan(math.tan(beta1) * sin_alpha) + math.atan(math.tan(rad(g.beta_2)) * sin_alpha)
    # Forma equivalente alla (29), stabile per piccoli angoli: sin(theta) da 1-cos²(theta).
    sin_theta = 2 * math.sqrt(rho_n1 * rho_n2) * math.sin(phi) / (rho_n1 + rho_n2)
    theta = math.degrees(math.asin(min(1.0, sin_theta)))
    if theta <= 0:
        raise GeometryError("Contatto ellittico degenere")
    eta = 0.09727 * theta**0.488
    xi = 39.26 * theta**-0.786
    Z_F = math.cbrt(1.5 * ((1 - flank.nu_1**2) / flank.E_1 + (1 - flank.nu_2**2) / flank.E_2))
    length = Z_F * math.cbrt(K_A * F_n * rho_n)
    a_h, b_h = xi * length, eta * length

    epsilon = epsilon_n
    if flank.epsilon_source == "reference":
        if g.epsilon_n_reference is None:
            raise GeometryError("Richiesto epsilon_n_reference per il fianco con fonte reference")
        epsilon = g.epsilon_n_reference
    Z_epsilonS = 1 / math.sqrt(epsilon)
    sigma_Hm = 1.5 * K_A * F_n * Z_epsilonS / (math.pi * a_h * b_h)
    return Blatt3FlankResult(
        epsilon_source=flank.epsilon_source,
        epsilon_used=epsilon,
        Z_epsilonS=Z_epsilonS,
        alpha_sn=math.degrees(alpha_sn),
        rho_z=math.degrees(rho_z),
        F_n=F_n,
        rho_n1=rho_n1,
        rho_n2=rho_n2,
        rho_n=rho_n,
        phi=math.degrees(phi),
        theta=theta,
        eta=eta,
        xi=xi,
        Z_F=Z_F,
        a_h=a_h,
        b_h=b_h,
        sigma_Hm=sigma_Hm,
        flank_ok=None if flank.sigma_HP is None else sigma_Hm <= flank.sigma_HP.value,
    )


def rate_blatt3(data: Blatt3Input) -> Blatt3Result:
    """Preliminare e taglio, più pressione al fianco se sono forniti i dati di contatto."""
    g = data.geometry
    rad = math.radians
    # Le quote di lavoro degli allegati sono stampate al millesimo di millimetro.
    if not math.isclose(g.a, (g.d_s1 + g.d_s2) / 2, abs_tol=0.001, rel_tol=1e-12):
        raise GeometryError("Interasse incoerente con i diametri di lavoro (oltre 0,001 mm)")
    if not g.d_b2 <= g.d_2 <= g.d_a2:
        raise GeometryError("Richiesti d_b2 ≤ d_2 ≤ d_a2")
    n_2 = data.n_1 * g.z1 / g.z2
    F_t2 = 2000 * data.T_2 / g.d_s2
    v_gs = math.pi * g.d_s2 * n_2 / (60000 * math.cos(rad(g.beta_s1)))
    if g.d_a1 <= g.d_m1:
        raise GeometryError("La testa della vite deve superare il diametro medio")
    m_x1 = g.m_n / math.cos(rad(g.gamma_m1))
    b_m = math.sqrt(g.d_a1**2 - g.d_m1**2)
    warnings = []
    K_z = C = S_C = None
    if 20 <= g.z2 <= 100:
        K_z = ((1.8974e-6 * g.z2 - 5.0262e-4) * g.z2 + 0.049159) * g.z2 - 0.1385
        C = F_t2 * data.K_A / (math.pi * K_z * b_m * m_x1)
        if data.C_lim is not None:
            S_C = data.C_lim.value / C
        else:
            warnings.append("C_lim non assegnato: sicurezza preliminare indeterminata")
    else:
        warnings.append("K_z fuori campo (20…100 denti): preliminare indeterminato")
    S_Cmin = 2.0 if data.strong_self_heating else 1.0

    tip1 = g.d_form1 or g.d_a1
    tip2 = g.d_form2 or g.d_a2
    if tip1 > g.d_a1 or tip2 > g.d_a2:
        raise GeometryError("Il diametro di forma supera il diametro di testa")
    g_an1 = _contact_length(tip1, g.d_s1, g.d_b1, g.beta_b1)
    g_an2 = _contact_length(tip2, g.d_s2, g.d_b2, g.beta_b2)
    alpha = rad(g.alpha_n)
    epsilon_n = (g_an1 + g_an2) / (math.pi * g.m_n * math.cos(alpha))
    epsilon_nz = math.floor(epsilon_n)
    if epsilon_nz < 1:
        raise GeometryError("Ricoprimento normale inferiore a uno")
    difference = None
    if g.epsilon_n_reference is not None:
        difference = epsilon_n - g.epsilon_n_reference
        if epsilon_nz != math.floor(g.epsilon_n_reference):
            raise GeometryError("La geometria e il ricoprimento dichiarato danno ε_nz diversi")
    Y_eps = 1 / epsilon_nz

    gap = 2 * g.a - g.d_a2
    d_x0 = 2 * g.a - g.d_a1
    if not 0 <= gap < g.d_a1 or d_x0 <= 0:
        raise GeometryError("Interasse e diametri di testa incompatibili con la sezione di taglio")
    b_max = min(g.b_2, math.sqrt(g.d_a1**2 - gap**2))
    cos_beta = math.cos(rad(g.beta_2))
    alpha_t = math.atan(math.tan(alpha) / cos_beta)
    s_t2 = g.m_n / cos_beta * (math.pi / 2 + 2 * g.x2 * math.tan(alpha))

    def thickness(diameter: float) -> float:
        return diameter * (s_t2 / g.d_2 + inv(alpha_t) - inv(math.acos(g.d_b2 / diameter)))

    used_reference = g.undercut2 or d_x0 < g.d_b2
    s_da1 = s_t2 if used_reference else thickness(d_x0)
    s_at2 = thickness(g.d_a2)
    if min(s_t2, s_da1, s_at2) <= 0:
        raise GeometryError("Spessore del dente non positivo")
    A_tau = b_max * (4 * s_da1 + s_at2) / 5
    tau_F = F_t2 * data.K_A * Y_eps / A_tau
    tau_Flim = S_F = None
    if data.sigma_ZSch is not None:
        tau_Flim = 0.75 * data.sigma_ZSch.value
        S_F = tau_Flim / tau_F
    else:
        warnings.append("Resistenza a temperatura e cicli assegnati mancante: piede indeterminato")
    flank = None
    if data.flank is not None:
        flank = _flank_contact(g, data.flank, epsilon_n, F_t2, data.K_A)
        if flank.flank_ok is None:
            warnings.append("Pressione ammissibile mancante: verifica del fianco indeterminata")
    return Blatt3Result(
        flank=flank,
        inputs=data,
        n_2=n_2,
        N_L=60 * n_2 * data.life_hours,
        F_t2=F_t2,
        v_gs=v_gs,
        m_x1=m_x1,
        b_m=b_m,
        K_z=K_z,
        C=C,
        S_C=S_C,
        S_Cmin=S_Cmin,
        preliminary_ok=None if S_C is None else S_Cmin <= S_C,
        g_an1=g_an1,
        g_an2=g_an2,
        epsilon_n=epsilon_n,
        epsilon_n_difference=difference,
        epsilon_nz=epsilon_nz,
        Y_eps=Y_eps,
        b_max=b_max,
        d_x0=d_x0,
        used_reference_thickness=used_reference,
        s_t2=s_t2,
        s_da1=s_da1,
        s_at2=s_at2,
        A_tau=A_tau,
        tau_F=tau_F,
        tau_Flim=tau_Flim,
        S_F=S_F,
        S_Fmin=1.3,
        root_ok=None if S_F is None else S_F >= 1.3,
        warnings=tuple(warnings),
    )
