import math

def involute_point(rb, t):
    """
    Calculate a point on the involute of a circle.
    rb: base radius
    t: parameter (angle in radians)
    """
    x = rb * (math.cos(t) + t * math.sin(t))
    y = rb * (math.sin(t) - t * math.cos(t))
    return x, y

def calculate_gear_parameters(m, z, alpha, x_shift=0.0):
    """
    Calculate standard gear parameters.
    m: module (mm)
    z: number of teeth
    alpha: pressure angle (degrees)
    x_shift: profile shift coefficient
    
    Returns: dictionary of parameters
    """
    alpha_rad = math.radians(alpha)
    
    # Pitch diameter
    d = m * z
    r = d / 2.0
    
    # Base diameter
    db = d * math.cos(alpha_rad)
    rb = db / 2.0
    
    # Addendum (Tip) diameter
    h_a = m * (1 + x_shift)
    da = d + 2 * h_a
    ra = da / 2.0
    
    # Dedendum (Root) diameter
    # standard addendum is 1*m, standard dedendum is 1.25*m
    h_f = m * (1.25 - x_shift)
    df = d - 2 * h_f
    rf = df / 2.0
    
    # Tooth thickness at pitch circle
    s = m * (math.pi / 2.0 + 2 * x_shift * math.tan(alpha_rad))
    
    # Angle of tooth thickness at pitch circle
    theta_s = s / r
    
    # Involute function at pitch circle (inv(alpha) = tan(alpha) - alpha)
    inv_alpha = math.tan(alpha_rad) - alpha_rad
    
    return {
        'm': m,
        'z': z,
        'alpha': alpha,
        'x_shift': x_shift,
        'd': d,
        'r': r,
        'db': db,
        'rb': rb,
        'da': da,
        'ra': ra,
        'df': df,
        'rf': rf,
        's': s,
        'theta_s': theta_s,
        'inv_alpha': inv_alpha
    }


def involute_function(alpha_rad):
    """Funzione evolvente: inv(α) = tan(α) - α"""
    return math.tan(alpha_rad) - alpha_rad


def inverse_involute(inv_val, tol=1e-10, max_iter=50):
    """
    Inversa della funzione evolvente tramite Newton-Raphson.
    Dato inv(α) ritorna α in radianti.
    Usata per calcolare l'angolo di pressione di lavoro nelle coppie con spostamento profilo.
    """
    # Stima iniziale (approssimazione per alpha vicino a 20°)
    alpha = (3 * inv_val) ** (1.0 / 3.0)
    for _ in range(max_iter):
        f = involute_function(alpha) - inv_val
        # Derivata: d/dα [tan(α) - α] = tan²(α)
        df = math.tan(alpha) ** 2
        if abs(df) < 1e-15:
            break
        delta = f / df
        alpha -= delta
        if abs(delta) < tol:
            break
    return alpha
