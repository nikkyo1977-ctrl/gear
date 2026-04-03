"""
2D gear profile generation and export to SVG and DXF.
Inspired by heartworm/py_gear_gen and CodiPixelPL/Gear-Gen.

Supports: spur gears, rack profiles, optional shaft bore hole, backlash.
"""

import math
import numpy as np
from .involute import calculate_gear_parameters, involute_point


# ---------------------------------------------------------------------------
# Profile point generation
# ---------------------------------------------------------------------------

def gear_profile_points(m, z, alpha=20.0, x_shift=0.0, backlash=0.0, n_flank=30):
    """
    Generate 2D profile polygon for a full spur gear.

    Parameters
    ----------
    m        : module (mm)
    z        : number of teeth
    alpha    : pressure angle (degrees)
    x_shift  : profile shift coefficient
    backlash : total backlash (mm) — reduces tooth thickness by backlash/2 per side
    n_flank  : number of points per involute flank

    Returns
    -------
    numpy (N, 2) array of [x, y] coordinates (closed polygon, CCW orientation)
    """
    params = calculate_gear_parameters(m, z, alpha, x_shift)
    rb = params['rb']
    ra = params['ra']
    rf = params['rf']
    r  = params['r']

    # Tooth thickness reduced by backlash
    s = params['s'] - backlash / 2.0
    theta_s = s / r

    # Safety: ra must be > rb
    if ra <= rb:
        ra = rb * 1.001

    # Involute parameter at tip circle
    t_max = math.sqrt((ra / rb) ** 2 - 1.0)

    # Involute parameter at root circle (used when rf >= rb to clip involute)
    if rf >= rb:
        t_start = math.sqrt(max((rf / rb) ** 2 - 1.0, 0.0))
    else:
        t_start = 0.0

    # Angle of involute at pitch circle (for tooth centering)
    t_p = math.sqrt(max((r / rb) ** 2 - 1.0, 0.0))
    xp, yp = involute_point(rb, t_p)
    angle_at_pitch = math.atan2(yp, xp)
    rotation_angle = -(theta_s / 2.0) - angle_at_pitch

    def _rot(x, y, theta):
        c, s_ = math.cos(theta), math.sin(theta)
        return x * c - y * s_, x * s_ + y * c

    # Right flank involute (root → tip), rotated to centre the tooth at angle 0
    ts = np.linspace(t_start, t_max, n_flank)
    right_pts = [_rot(*involute_point(rb, t), rotation_angle) for t in ts]

    # Left flank = mirror about x-axis, reversed
    left_pts = [(x, -y) for x, y in right_pts[::-1]]

    # Tip arc: goes clockwise from right_pts[-1] through (ra, 0) to left_pts[0]
    ang_r = math.atan2(right_pts[-1][1], right_pts[-1][0])
    ang_l = math.atan2(left_pts[0][1],   left_pts[0][0])   # ≈ -ang_r
    n_tip = max(5, int(abs(ang_r - ang_l) / math.pi * 40))
    tip_angles = np.linspace(ang_r, ang_l, n_tip)          # decreasing → CW through 0
    tip_pts = [(ra * math.cos(a), ra * math.sin(a)) for a in tip_angles]

    # Build single tooth profile
    if rf < rb:
        # Radial line from rf to base circle on each side
        ang_r0  = math.atan2(right_pts[0][1], right_pts[0][0])
        ang_l_e = math.atan2(left_pts[-1][1], left_pts[-1][0])
        root_r  = (rf * math.cos(ang_r0),  rf * math.sin(ang_r0))
        root_l  = (rf * math.cos(ang_l_e), rf * math.sin(ang_l_e))
        tooth   = [root_r] + right_pts + tip_pts[1:-1] + left_pts + [root_l]
    else:
        # Involute already clipped at rf (t_start > 0)
        tooth = right_pts + tip_pts[1:-1] + left_pts

    # Replicate tooth z times and connect with root arcs
    pitch_angle = 2.0 * math.pi / z
    all_pts = []

    for i in range(z):
        ang  = i * pitch_angle
        c_a, s_a = math.cos(ang), math.sin(ang)
        rotated = [(x * c_a - y * s_a, x * s_a + y * c_a) for x, y in tooth]

        if all_pts:
            # CCW root arc from prev tooth's left-root to this tooth's right-root
            a1 = math.atan2(all_pts[-1][1], all_pts[-1][0])
            a2 = math.atan2(rotated[0][1],  rotated[0][0])
            while a2 < a1:
                a2 += 2.0 * math.pi
            n_arc = max(2, int((a2 - a1) / math.pi * 20))
            for a in np.linspace(a1, a2, n_arc)[1:-1]:
                all_pts.append((rf * math.cos(a), rf * math.sin(a)))

        all_pts.extend(rotated)

    # Closing root arc: last tooth's left-root → first tooth's right-root
    a1 = math.atan2(all_pts[-1][1], all_pts[-1][0])
    a2 = math.atan2(tooth[0][1],    tooth[0][0])
    while a2 < a1:
        a2 += 2.0 * math.pi
    n_arc = max(2, int((a2 - a1) / math.pi * 20))
    for a in np.linspace(a1, a2, n_arc)[1:]:
        all_pts.append((rf * math.cos(a), rf * math.sin(a)))

    return np.array(all_pts)


def rack_profile_points(m, n_teeth, alpha=20.0, base_height=None):
    """
    Generate 2D profile polygon for a straight rack (linear, no curvature).

    Returns numpy (N, 2) array. Origin at the pitch line centre.
    """
    alpha_rad = math.radians(alpha)
    pitch     = math.pi * m
    ha        = m
    hf        = 1.25 * m
    base_h    = base_height if base_height is not None else 2.0 * m

    total_len = pitch * n_teeth
    half_len  = total_len / 2.0

    pts = [(-half_len, -hf - base_h), (-half_len, -hf)]

    for i in range(n_teeth):
        x_c      = -half_len + (i + 0.5) * pitch
        half_bot = pitch / 2.0 + hf * math.tan(alpha_rad)
        half_top = max(pitch / 2.0 - ha * math.tan(alpha_rad), 0.05 * m)

        pts.append((x_c - half_bot, -hf))
        pts.append((x_c - half_top,  ha))
        pts.append((x_c + half_top,  ha))
        pts.append((x_c + half_bot, -hf))

        if i < n_teeth - 1:
            x_next = -half_len + (i + 1) * pitch
            pts.append((x_next - (pitch / 2.0 + hf * math.tan(alpha_rad)), -hf))

    pts.append((half_len, -hf))
    pts.append((half_len, -hf - base_h))

    return np.array(pts)


# ---------------------------------------------------------------------------
# SVG export
# ---------------------------------------------------------------------------

def export_svg(filepath, points, shaft_dia=0.0, title="Gear Profile",
               fill_color="#d6e8fa", stroke_color="#1a4fc2"):
    """
    Export 2D profile as SVG file.

    Parameters
    ----------
    filepath     : output path (.svg)
    points       : (N, 2) numpy array from gear_profile_points() or rack_profile_points()
    shaft_dia    : shaft bore diameter [mm], 0 → no hole
    title        : document title
    fill_color   : gear body fill (CSS colour)
    stroke_color : outline colour
    """
    try:
        import svgwrite
        _export_svg_svgwrite(filepath, points, shaft_dia, title, fill_color, stroke_color)
    except ImportError:
        _export_svg_plain(filepath, points, shaft_dia, title, fill_color, stroke_color)


def _export_svg_svgwrite(filepath, points, shaft_dia, title, fill_color, stroke_color):
    import svgwrite

    pts = points.copy()
    pts[:, 1] = -pts[:, 1]          # flip Y (SVG Y grows downward)

    min_xy = pts.min(axis=0)
    max_xy = pts.max(axis=0)
    w, h   = max_xy - min_xy
    margin = max(w, h) * 0.05

    dwg = svgwrite.Drawing(
        filepath,
        size=(f"{w + 2*margin:.4f}mm", f"{h + 2*margin:.4f}mm"),
        viewBox=(f"{min_xy[0]-margin:.4f} {min_xy[1]-margin:.4f} "
                 f"{w+2*margin:.4f} {h+2*margin:.4f}"),
    )
    # Add title as a <desc> comment (svgwrite does not expose a title() helper)
    dwg.attribs['id'] = title.replace(' ', '_')

    path_d = "M " + " L ".join(f"{x:.4f},{y:.4f}" for x, y in pts) + " Z"
    dwg.add(dwg.path(
        d=path_d,
        fill=fill_color,
        stroke=stroke_color,
        stroke_width=0.15,
        fill_rule="evenodd",
    ))

    if shaft_dia > 0:
        dwg.add(dwg.circle(
            center=(0, 0),
            r=shaft_dia / 2,
            fill="white",
            stroke=stroke_color,
            stroke_width=0.15,
        ))

    dwg.save()


def _export_svg_plain(filepath, points, shaft_dia, title, fill_color, stroke_color):
    """Fallback SVG writer — no external dependencies."""
    pts = points.copy()
    pts[:, 1] = -pts[:, 1]

    min_xy = pts.min(axis=0)
    max_xy = pts.max(axis=0)
    w, h   = max_xy - min_xy
    margin = max(w, h) * 0.05
    vb_x   = min_xy[0] - margin
    vb_y   = min_xy[1] - margin
    vb_w   = w + 2 * margin
    vb_h   = h + 2 * margin

    poly_pts = " ".join(f"{x:.4f},{y:.4f}" for x, y in pts)

    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        (f'<svg xmlns="http://www.w3.org/2000/svg" '
         f'viewBox="{vb_x:.4f} {vb_y:.4f} {vb_w:.4f} {vb_h:.4f}" '
         f'width="{vb_w:.2f}mm" height="{vb_h:.2f}mm">'),
        f'  <title>{title}</title>',
        (f'  <polygon points="{poly_pts}" fill="{fill_color}" '
         f'stroke="{stroke_color}" stroke-width="0.15" fill-rule="evenodd"/>'),
    ]
    if shaft_dia > 0:
        lines.append(
            f'  <circle cx="0" cy="0" r="{shaft_dia/2:.4f}" '
            f'fill="white" stroke="{stroke_color}" stroke-width="0.15"/>'
        )
    lines.append('</svg>')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


# ---------------------------------------------------------------------------
# DXF export
# ---------------------------------------------------------------------------

def export_dxf(filepath, points, shaft_dia=0.0, layer="GEAR"):
    """
    Export 2D profile as DXF file (R2010, millimetres).

    Parameters
    ----------
    filepath  : output path (.dxf)
    points    : (N, 2) numpy array
    shaft_dia : shaft bore diameter [mm], 0 → no hole
    layer     : DXF layer name for all entities
    """
    try:
        import ezdxf
    except ImportError:
        raise ImportError("ezdxf not installed — run: pip install ezdxf")

    doc = ezdxf.new('R2010')
    doc.header['$MEASUREMENT'] = 1   # metric
    doc.header['$INSUNITS']    = 4   # mm

    msp = doc.modelspace()

    pts_2d = [(float(x), float(y)) for x, y in points]
    msp.add_lwpolyline(pts_2d, dxfattribs={'closed': True, 'layer': layer})

    if shaft_dia > 0:
        msp.add_circle(
            center=(0.0, 0.0),
            radius=shaft_dia / 2,
            dxfattribs={'layer': layer},
        )

    doc.saveas(filepath)
