import math
from build123d import *


def create_worm_zi(mx, z1, q, length, alpha_n=20.0):
    """
    Create a ZI profile worm (Involute helicoid).
    Modello CAD: profilo trapezoidale assiale sweep lungo elica.

    mx     : modulo assiale
    z1     : numero di principi (filetti)
    q      : quoziente diametrale (q = d1 / mx)
    length : lunghezza assiale della vite
    alpha_n: angolo di pressione normale
    """
    d1 = q * mx                             # diametro primitivo
    r1 = d1 / 2.0
    gamma_rad = math.atan2(z1, q)           # angolo di passo
    alpha_n_rad = math.radians(alpha_n)

    # Geometria del dente in sezione assiale
    p_ax = math.pi * mx                     # passo assiale
    ha = mx                                 # addendum
    hf = 1.25 * mx                          # dedendum
    rf = r1 - hf

    # Lead totale (passo elicoidale per un principio)
    lead = p_ax * z1                        # avanzamento assiale per giro completo

    # Profilo del filetto in sezione assiale (trapezio simmetrico)
    half_top = (p_ax / 2.0 - 2.0 * ha * math.tan(alpha_n_rad) * math.cos(gamma_rad)) / 2.0
    half_bot = (p_ax / 2.0 + 2.0 * hf * math.tan(alpha_n_rad) * math.cos(gamma_rad)) / 2.0
    half_top = max(half_top, 0.05 * mx)    # evita degenerazione

    # Corpo base: cilindro piede

    with BuildPart() as worm_body:
        # Cilindro corpo
        Cylinder(radius=rf, height=length, align=(Align.CENTER, Align.CENTER, Align.MIN))

        # Per ogni principio, crea un filetto sweep lungo elica
        for start in range(z1):
            angle_offset = start * 360.0 / z1
            helix_path = Helix(
                pitch=lead,
                height=length,
                radius=r1,
                center=(0, 0, 0),
                direction=(0, 0, 1),
            ).rotate(Axis.Z, angle_offset)

            # Profilo nel piano perpendicolare alla partenza dell'elica
            start_rad = math.radians(angle_offset)
            cx = r1 * math.cos(start_rad)
            cy = r1 * math.sin(start_rad)
            tang = Vector(-math.sin(start_rad), math.cos(start_rad), 0)
            profile_plane = Plane(
                origin=(cx, cy, 0),
                x_dir=tang,
                z_dir=(0, 0, 1),
            )
            with BuildSketch(profile_plane) as tooth_sk:
                with BuildLine():
                    Polyline(
                        (-half_bot, 0),
                        (-half_top, ha + hf),
                        (half_top,  ha + hf),
                        (half_bot,  0),
                        (-half_bot, 0),
                    )
                make_face()

            sweep(tooth_sk.sketch, path=helix_path, mode=Mode.ADD)

    return worm_body.part
