import math
from build123d import *
from .spur import generate_spur_gear_profile


def create_helical_gear(mn, z, width, beta, alpha_n=20.0, x_shift=0.0):
    """
    Create a helical gear using loft between bottom and rotated top profile.
    mn: normal module
    z: number of teeth
    width: face width
    beta: helix angle in degrees
    alpha_n: normal pressure angle
    x_shift: profile shift coefficient
    """
    beta_rad = math.radians(beta)

    # Transverse parameters
    mt = mn / math.cos(beta_rad)
    alpha_t = math.degrees(math.atan(math.tan(math.radians(alpha_n)) / math.cos(beta_rad)))

    # Generate transverse profile sketch
    sketch, params = generate_spur_gear_profile(mt, z, alpha_t, x_shift)
    r_pitch = params['r']

    # Twist angle over the full width
    twist_deg = math.degrees((width * math.tan(beta_rad)) / r_pitch)

    # Bottom face at z=0
    bot_face = sketch.face()

    # Top face: same shape moved to z=width and rotated by twist_deg
    top_face = bot_face.moved(Location((0, 0, width)))
    top_face = top_face.rotate(Axis.Z, twist_deg)

    with BuildPart() as part:
        loft([bot_face, top_face])

    return part.part
