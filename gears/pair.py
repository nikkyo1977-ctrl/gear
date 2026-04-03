"""
Analisi della coppia di ingranaggi.
Calcola interasse di lavoro, rapporto di trasmissione, rapporto di contatto e rischi di sottosquadro.
Supporta anche il calcolo inverso: dato l'interasse imposto, determina lo spostamento profilo ottimale.
"""

import math
from .involute import calculate_gear_parameters, involute_function, inverse_involute


def pair_from_center_distance(a_w, m, z1, z2, alpha=20.0, beta=0.0):
    """
    Calcola gli spostamenti profilo x1, x2 necessari per ottenere un interasse imposto a_w.
    La somma (x1+x2) viene distribuita equamente: x1 = x2 = (x_sum)/2.

    Parametri:
        a_w   : interasse di lavoro desiderato [mm]
        m     : modulo nominale
        z1    : denti pignone
        z2    : denti ruota
        alpha : angolo pressione normale [°]
        beta  : angolo elica [°]

    Ritorna dict con:
        x_sum   : somma spostamenti profilo necessaria
        x1, x2  : spostamenti distribuiti equamente
        alpha_wt: angolo di pressione di lavoro risultante [°]
        a_std   : interasse standard [mm]
        warning : stringa di avviso se a_w < a_std (spostamento negativo) o troppo grande
        + tutti i campi di calculate_gear_pair()
    """
    beta_rad  = math.radians(beta)
    alpha_rad = math.radians(alpha)

    if beta > 0:
        mt = m / math.cos(beta_rad)
        alpha_t_rad = math.atan(math.tan(alpha_rad) / math.cos(beta_rad))
    else:
        mt = m
        alpha_t_rad = alpha_rad

    a_std = mt * (z1 + z2) / 2.0

    # Angolo pressione di lavoro dall'interasse:
    # a_w = a_std * cos(alpha_t) / cos(alpha_wt)  =>  cos(alpha_wt) = a_std*cos(alpha_t)/a_w
    cos_awt = a_std * math.cos(alpha_t_rad) / a_w
    if cos_awt > 1.0 or cos_awt <= 0.0:
        raise ValueError(
            f"Interasse a_w={a_w:.3f} mm non realizzabile con m={m}, z1={z1}, z2={z2}. "
            f"Interasse standard = {a_std:.3f} mm."
        )
    alpha_wt_rad = math.acos(cos_awt)

    # Somma spostamenti dalla funzione evolvente inversa
    inv_awt = involute_function(alpha_wt_rad)
    inv_at  = involute_function(alpha_t_rad)
    x_sum = (inv_awt - inv_at) * (z1 + z2) / (2.0 * math.tan(alpha_rad))
    x1 = x_sum / 2.0
    x2 = x_sum / 2.0

    warning = ""
    if x_sum < -0.5:
        warning = f"⚠ Spostamento molto negativo (x_sum={x_sum:.3f}): rischio sottosquadro."
    elif x_sum > 1.5:
        warning = f"⚠ Spostamento molto positivo (x_sum={x_sum:.3f}): verificare interferenza alla punta."

    result = calculate_gear_pair(m, z1, z2, alpha, x1, x2, beta)
    result['x_sum']    = round(x_sum, 5)
    result['x1']       = round(x1, 5)
    result['x2']       = round(x2, 5)
    result['a_std']    = round(a_std, 4)
    result['a_w_target'] = round(a_w, 4)
    result['warning']  = warning
    return result


def calculate_gear_pair(m, z1, z2, alpha=20.0, x1=0.0, x2=0.0, beta=0.0):
    """
    Analisi completa di una coppia di ingranaggi cilindrici.

    Parametri:
        m     : modulo nominale (mm) — per ingranaggi elicoidali è il modulo normale mn
        z1    : numero denti pignone
        z2    : numero denti ruota
        alpha : angolo di pressione normale (gradi), default 20°
        x1    : spostamento profilo pignone
        x2    : spostamento profilo ruota
        beta  : angolo di elica (gradi), 0 per ingranaggi dritti

    Ritorna dict con:
        i               : rapporto di trasmissione z2/z1
        a_std           : interasse standard (mm)
        a_w             : interasse di lavoro con spostamento (mm)
        alpha_wt        : angolo di pressione di lavoro trasversale (gradi)
        epsilon_alpha   : rapporto di contatto trasversale
        epsilon_beta    : rapporto di ricoprimento (solo elicoidali)
        epsilon_gamma   : rapporto di contatto totale
        da1_max         : diametro punta massimo pignone per evitare interferenza (mm)
        da2_max         : diametro punta massimo ruota per evitare interferenza (mm)
        undercut_risk_1 : True se pignone rischia sottosquadro (z < z_min)
        undercut_risk_2 : True se ruota rischia sottosquadro (z < z_min)
        z_min           : numero minimo denti per evitare sottosquadro senza spostamento
    """
    beta_rad = math.radians(beta)
    alpha_n_rad = math.radians(alpha)

    # Modulo trasversale
    if beta > 0:
        mt = m / math.cos(beta_rad)
        alpha_t_rad = math.atan(math.tan(alpha_n_rad) / math.cos(beta_rad))
    else:
        mt = m
        alpha_t_rad = alpha_n_rad

    alpha_t = math.degrees(alpha_t_rad)

    # Parametri geometrici individuali
    p1 = calculate_gear_parameters(mt, z1, alpha_t, x1)
    p2 = calculate_gear_parameters(mt, z2, alpha_t, x2)

    # Interasse standard
    a_std = mt * (z1 + z2) / 2.0

    # Angolo di pressione di lavoro (con spostamento profilo)
    x_sum = x1 + x2
    if abs(x_sum) < 1e-9:
        alpha_wt_rad = alpha_t_rad
    else:
        inv_awt = involute_function(alpha_t_rad) + 2 * x_sum * math.tan(alpha_n_rad) / (z1 + z2)
        alpha_wt_rad = inverse_involute(inv_awt)

    alpha_wt = math.degrees(alpha_wt_rad)

    # Interasse di lavoro
    a_w = a_std * math.cos(alpha_t_rad) / math.cos(alpha_wt_rad)

    # Rapporto di contatto trasversale (epsilon_alpha)
    # ε_α = [z1(tan(α_at1) - tan(α_wt)) + z2(tan(α_at2) - tan(α_wt))] / (2π)
    # dove α_at1, α_at2 sono gli angoli alla punta
    ra1 = p1['ra']
    ra2 = p2['ra']
    rb1 = p1['rb']
    rb2 = p2['rb']

    # Angoli alla punta
    cos_a_at1 = rb1 / ra1
    cos_a_at2 = rb2 / ra2
    cos_a_at1 = max(min(cos_a_at1, 1.0), -1.0)
    cos_a_at2 = max(min(cos_a_at2, 1.0), -1.0)
    alpha_at1 = math.acos(cos_a_at1)
    alpha_at2 = math.acos(cos_a_at2)

    epsilon_alpha = (z1 * (math.tan(alpha_at1) - math.tan(alpha_wt_rad)) +
                     z2 * (math.tan(alpha_at2) - math.tan(alpha_wt_rad))) / (2 * math.pi)

    # Rapporto di ricoprimento (solo elicoidali)
    b_ref = mt * max(z1, z2)  # larghezza di riferimento (non nota qui, si usa il valore nominale)
    # epsilon_beta richiede la fascia b; ritorniamo la formula per b=1mm come coefficiente
    # L'utente moltiplica per b[mm] / (pi * mt / sin(beta))
    if beta > 0.0:
        epsilon_beta_coeff = math.sin(beta_rad) / (math.pi * m)  # per unità di larghezza [1/mm]
    else:
        epsilon_beta_coeff = 0.0

    epsilon_beta = 0.0  # senza conoscere b non calcolabile qui

    epsilon_gamma = epsilon_alpha  # + epsilon_beta quando b è nota

    # Diametri punta massimi per evitare interferenza con la controparte
    # da1_max: la punta di 1 non deve penetrare sotto il cerchio base di 2
    # Condizione: ga <= g_f2 => ra1*sin(a_at1) - rb1*tan(a_wt) <= a_w*sin(a_wt) - rb2*tan(a_at2_min)
    # Formula semplificata (standard ISO):
    # da1_max = 2*(a_w*sin(alpha_wt) + rb2*tan(alpha_at2) - rb1*tan(alpha_wt) + rb1*tan(alpha_wt))
    # In pratica: limite di interferenza se epsilon_alpha >= 1 è già verificato
    # Calcoliamo il valore limite semplificato:
    da1_max = 2 * math.sqrt(rb1**2 + (a_w * math.sin(alpha_wt_rad) - math.sqrt(ra2**2 - rb2**2))**2)
    da2_max = 2 * math.sqrt(rb2**2 + (a_w * math.sin(alpha_wt_rad) - math.sqrt(ra1**2 - rb1**2))**2)

    # Rischio sottosquadro: z_min = 2*cos(beta) / sin²(alpha_t) senza spostamento
    z_min = math.ceil(2 * math.cos(beta_rad) / math.sin(alpha_t_rad)**2)
    undercut_risk_1 = (z1 < z_min) and (x1 == 0.0)
    undercut_risk_2 = (z2 < z_min) and (x2 == 0.0)

    return {
        'i': z2 / z1,
        'a_std': round(a_std, 4),
        'a_w': round(a_w, 4),
        'alpha_t': round(alpha_t, 4),
        'alpha_wt': round(alpha_wt, 4),
        'epsilon_alpha': round(epsilon_alpha, 4),
        'epsilon_beta_coeff': round(epsilon_beta_coeff, 6),
        'epsilon_gamma': round(epsilon_gamma, 4),
        'da1_max': round(da1_max, 4),
        'da2_max': round(da2_max, 4),
        'undercut_risk_1': undercut_risk_1,
        'undercut_risk_2': undercut_risk_2,
        'z_min': z_min,
    }
