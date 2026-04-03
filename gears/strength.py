"""
Calcoli di resistenza per ingranaggi cilindrici.
Metodo semplificato ISO 6336 Metodo B.

Riferimenti:
    - ISO 6336-2: Bending strength
    - ISO 6336-3: Contact (Hertz) stress
    - Niemann, Maschinenelemente Band 2
"""

import math


def tangential_force_from_power(P_kW, n_rpm, d_mm):
    """
    Calcola la forza tangenziale sul cerchio primitivo.
    Ft = 2000 * P [kW] * 60 / (pi * n [rpm] * d [mm]) = 2*T/d
    """
    if n_rpm <= 0 or d_mm <= 0:
        raise ValueError("Velocità e diametro devono essere > 0")
    omega = 2 * math.pi * n_rpm / 60.0  # rad/s
    T_Nmm = P_kW * 1e3 / omega * 1e3   # Nm -> Nmm
    Ft = 2.0 * T_Nmm / d_mm
    return Ft


def _lewis_form_factor(z, x_shift=0.0, alpha=20.0):
    """
    Fattore di forma di Lewis YF per il metodo della tangente a 30°.
    Approssimazione per ingranaggi ISO standard (ISO 6336-3 metodo B semplificato).
    Formula di Bairard/Niemann che dipende dal numero di denti virtuale z_n.
    """
    alpha_rad = math.radians(alpha)
    # Numero denti virtuale (per evolvente di riferimento)
    z_n = max(z, 5)
    # Coefficiente di forma approssimato (Niemann, Tab. 22/3):
    # YF ≈ (2.06 + 0.02*x) + (6.0 - 0.15*x) / z_n  per alpha=20°
    YF = (2.06 + 0.02 * x_shift) + (6.0 - 0.15 * x_shift) / z_n
    return max(YF, 1.0)


def _stress_correction_factor(z, x_shift=0.0):
    """
    Fattore di correzione tensione YS (effetto di intaglio alla radice).
    Approssimazione per ingranaggi standard.
    """
    # Formula semplificata Niemann
    z_n = max(z, 5)
    YS = 1.0 + 0.07 * math.log(z_n / 10.0 + 1.0) - 0.1 * x_shift
    return max(YS, 0.8)


def _contact_ratio_factor_bending(epsilon_alpha):
    """Fattore rapporto di contatto per flessione Yeps."""
    if epsilon_alpha <= 0:
        return 1.0
    return 0.25 + 0.75 / epsilon_alpha


def calculate_lewis_bending(params, b, Ft, material,
                             KA=1.25, KV=1.1, KHb=1.1, KHa=1.0,
                             epsilon_alpha=None):
    """
    Calcola la tensione di flessione alla radice del dente (ISO 6336-3 semplificato).

    Parametri:
        params        : dict da calculate_gear_parameters()
        b             : larghezza di fascia [mm]
        Ft            : forza tangenziale [N]
        material      : dict da materials.get_material()
        KA            : fattore di applicazione (default 1.25)
        KV            : fattore dinamico (default 1.1)
        KHb           : fattore di distribuzione del carico su fascia (default 1.1)
        KHa           : fattore di distribuzione del carico su più denti (default 1.0)
        epsilon_alpha : rapporto di contatto (opzionale, migliora Yeps)

    Ritorna dict:
        sigma_F       : tensione di flessione calcolata [MPa]
        sigma_F_perm  : tensione ammissibile [MPa]
        SF            : coefficiente di sicurezza a flessione
        YF            : fattore di forma
        YS            : fattore di correzione tensione
        Yeps          : fattore rapporto di contatto
    """
    m = params['m']
    z = params['z']
    x = params['x_shift']
    alpha = params['alpha']

    if b <= 0 or Ft <= 0:
        raise ValueError("Larghezza di fascia e forza tangenziale devono essere > 0")

    YF = _lewis_form_factor(z, x, alpha)
    YS = _stress_correction_factor(z, x)

    if epsilon_alpha is not None and epsilon_alpha > 0:
        Yeps = _contact_ratio_factor_bending(epsilon_alpha)
    else:
        Yeps = 0.625  # valore tipico per epsilon_alpha ~ 1.6

    # Fattore combinato di carico per flessione
    KF = KA * KV * KHb * KHa

    # Tensione di flessione ISO 6336
    sigma_F = (Ft / (b * m)) * YF * YS * Yeps * KF

    # Tensione ammissibile (con fattori di sicurezza minimi raccomandati)
    # sigma_F_perm = sigma_Flim / SF_min — qui usiamo sigma_Flim direttamente
    # SF = sigma_Flim / sigma_F
    sigma_Flim = material['sigma_Flim']
    SF = sigma_Flim / sigma_F if sigma_F > 0 else float('inf')

    return {
        'sigma_F': round(sigma_F, 2),
        'sigma_F_perm': round(sigma_Flim, 2),
        'SF': round(SF, 3),
        'YF': round(YF, 3),
        'YS': round(YS, 3),
        'Yeps': round(Yeps, 3),
        'KF': round(KF, 3),
    }


def calculate_hertz_contact(params1, params2, b, Ft, mat1, mat2,
                             KA=1.25, KV=1.1, KHb=1.1, KHa=1.0):
    """
    Calcola la tensione di contatto (Hertz) tra due ingranaggi (ISO 6336-2 semplificato).

    Parametri:
        params1, params2 : dict da calculate_gear_parameters() per pignone e ruota
        b                : larghezza di fascia [mm]
        Ft               : forza tangenziale al primitivo [N]
        mat1, mat2       : dict da materials.get_material() per i due ingranaggi
        KA, KV, KHb, KHa : fattori di carico

    Ritorna dict:
        sigma_H      : tensione di contatto calcolata [MPa]
        sigma_H_perm : tensione ammissibile (min tra i due materiali) [MPa]
        SH           : coefficiente di sicurezza Hertz
        ZE           : fattore elastico
        ZH           : fattore di zona
        Zeps         : fattore rapporto di contatto
    """
    if b <= 0 or Ft <= 0:
        raise ValueError("Larghezza di fascia e forza tangenziale devono essere > 0")

    # Fattore elastico ZE (ISO 6336-2)
    E1, nu1 = mat1['E'], mat1['nu']
    E2, nu2 = mat2['E'], mat2['nu']
    ZE = math.sqrt(1.0 / (math.pi * ((1 - nu1**2) / E1 + (1 - nu2**2) / E2)))

    # Fattore di zona ZH
    alpha_rad = math.radians(params1['alpha'])
    ZH = math.sqrt(2.0 * math.cos(alpha_rad) / math.sin(alpha_rad))

    # Fattore rapporto di contatto Zeps (approssimazione per coppia cilindrica diritta)
    # Zeps ≈ sqrt(4 - epsilon_alpha) / 3  per epsilon_alpha tra 1 e 2
    z1 = params1['z']
    z2 = params2['z']
    # Stima epsilon_alpha dalla geometria
    rb1 = params1['rb']
    rb2 = params2['rb']
    ra1 = params1['ra']
    ra2 = params2['ra']
    a_w = (params1['r'] + params2['r'])  # interasse standard semplificato

    try:
        alpha_at1 = math.acos(rb1 / ra1)
        alpha_at2 = math.acos(rb2 / ra2)
        epsilon_alpha = (z1 * (math.tan(alpha_at1) - math.tan(alpha_rad)) +
                         z2 * (math.tan(alpha_at2) - math.tan(alpha_rad))) / (2 * math.pi)
        epsilon_alpha = max(epsilon_alpha, 1.0)
    except Exception:
        epsilon_alpha = 1.6  # fallback tipico

    Zeps = math.sqrt((4.0 - epsilon_alpha) / 3.0) if epsilon_alpha <= 2.0 else math.sqrt(1.0 / 3.0)

    # Raggio di curvatura ridotto al punto primitivo
    r1 = params1['r']
    r2 = params2['r']
    sin_alpha = math.sin(alpha_rad)
    rho_red = (r1 * sin_alpha * r2 * sin_alpha) / (r1 * sin_alpha + r2 * sin_alpha)

    # Fattore di carico combinato
    KH = KA * KV * KHb * KHa

    # Tensione di contatto (formula ISO semplificata)
    sigma_H = ZE * ZH * Zeps * math.sqrt(Ft * KH / (b * r1) * (z1 + z2) / z2)

    # Tensione ammissibile: il più basso dei due sigma_Hlim
    sigma_Hlim = min(mat1['sigma_Hlim'], mat2['sigma_Hlim'])
    SH = sigma_Hlim / sigma_H if sigma_H > 0 else float('inf')

    return {
        'sigma_H': round(sigma_H, 2),
        'sigma_H_perm': round(sigma_Hlim, 2),
        'SH': round(SH, 3),
        'ZE': round(ZE, 3),
        'ZH': round(ZH, 3),
        'Zeps': round(Zeps, 3),
        'KH': round(KH, 3),
        'epsilon_alpha': round(epsilon_alpha, 3),
    }
