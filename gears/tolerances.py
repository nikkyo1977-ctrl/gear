"""
Tolleranze geometriche degli ingranaggi secondo ISO 1328-1.
Formule basate sulle tabelle ISO 1328-1:2013 per gradi di qualità 3-12.
"""

import math


def iso1328_tolerances(grade: int, d_mm: float, m_mm: float, b_mm: float) -> dict:
    """
    Calcola le deviazioni ammissibili secondo ISO 1328-1 per ingranaggi cilindrici.

    Parametri:
        grade : grado di qualità ISO 1328 (intero da 3 a 12)
        d_mm  : diametro primitivo [mm]
        m_mm  : modulo [mm]
        b_mm  : larghezza di fascia [mm]

    Ritorna dict con:
        Ff   : deviazione totale del profilo [µm]
        Fb   : deviazione totale dell'elica [µm]
        fp   : deviazione del passo singolo [µm]
        Fp   : deviazione cumulativa del passo [µm]
        grade: grado di qualità inserito
    """
    if not (3 <= grade <= 12):
        raise ValueError(f"Grado ISO 1328 deve essere tra 3 e 12, ricevuto: {grade}")
    if d_mm <= 0 or m_mm <= 0 or b_mm <= 0:
        raise ValueError("Diametro, modulo e fascia devono essere > 0")

    # Fattore di scala del grado: ogni grado scala di 2^(1/2) ≈ 1.414
    # Grado di riferimento: 5 (i coefficienti sono per grado 5)
    scale = 2 ** ((grade - 5) / 2.0)

    # --- Deviazione totale del profilo Ff [µm] ---
    # ISO 1328 Tab. 1: Ff = (2.5 + 0.17*d^0.5 + 0.5*m^0.5) * scala
    Ff = (2.5 + 0.17 * math.sqrt(d_mm) + 0.5 * math.sqrt(m_mm)) * scale

    # --- Deviazione totale dell'elica Fb [µm] ---
    # ISO 1328 Tab. 1: Fb = (4.0 + 0.4*d^0.5 + 0.4*b^0.5) * scala  (appross.)
    Fb = (4.0 + 0.4 * math.sqrt(d_mm) + 0.4 * math.sqrt(b_mm)) * scale

    # --- Deviazione del passo singolo fp [µm] ---
    # ISO 1328 Tab. 1: fp = (0.3*m + 0.003*d + 5.2) * scala
    fp = (0.3 * m_mm + 0.003 * d_mm + 5.2) * scale

    # --- Deviazione cumulativa del passo Fp [µm] ---
    # ISO 1328 Tab. 1: Fp ≈ fp * z^0.5 semplificato; oppure:
    # Fp = (0.025*d + 0.3*m + 19) * scala
    Fp = (0.025 * d_mm + 0.3 * m_mm + 19.0) * scale

    return {
        'grade': grade,
        'Ff': round(Ff, 1),
        'Fb': round(Fb, 1),
        'fp': round(fp, 1),
        'Fp': round(Fp, 1),
    }
