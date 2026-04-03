import math
from build123d import *
from .involute import calculate_gear_parameters, involute_point

def generate_spur_gear_profile(m, z, alpha, x_shift=0.0):
    params = calculate_gear_parameters(m, z, alpha, x_shift)
    
    rb = params['rb']
    ra = params['ra']
    rf = params['rf']
    
    # Max parameter t for the involute at the tip circle
    # ra^2 = x^2 + y^2 = rb^2 * (1 + t^2)
    # t_max = sqrt((ra/rb)^2 - 1)
    t_max = math.sqrt((ra/rb)**2 - 1.0)
    
    # Generate points for the involute curve
    num_points = 20
    involute_points = [involute_point(rb, t_max * i / (num_points - 1)) for i in range(num_points)]
    
    # We need to rotate the involute so its center aligns properly
    # The thickness of the tooth at pitch circle is params['s']
    # The angle of the involute point at pitch circle:
    # rb^2 (1 + t_p^2) = r^2
    r = params['r']
    t_p = math.sqrt((r/rb)**2 - 1.0) if r > rb else 0.0
    
    # find the angle of the point at pitch circle
    xp, yp = involute_point(rb, t_p)
    angle_at_pitch = math.atan2(yp, xp)
    
    # We want to rotate so the right side involute crosses the pitch circle at -theta_s / 2
    rotation_angle = - (params['theta_s'] / 2.0) - angle_at_pitch
    
    # Rotate function
    def rotate(pt, theta):
        x, y = pt
        return (x * math.cos(theta) - y * math.sin(theta), 
                x * math.sin(theta) + y * math.cos(theta))
    
    right_points = [rotate(pt, rotation_angle) for pt in involute_points]
    left_points = [(pt[0], -pt[1]) for pt in right_points]
    left_points.reverse() # so it connects nicely
    
    # Now we have the right and left involute curves.
    # What about the section between base circle and root circle?
    # If rf < rb, we need to extend straight lines to the root circle, or draw a fillet (trochoid).
    # For simplicity in this FSD, we will just use a straight line to the center, then clip at root circle.
    
    pts = []
    
    # Start at root
    if rf < rb:
        # Radial line from root to base
        pt_right_base = right_points[0]
        ang_right_base = math.atan2(pt_right_base[1], pt_right_base[0])
        pts.append((rf * math.cos(ang_right_base), rf * math.sin(ang_right_base)))
        
    pts.extend(right_points)
    
    # Tip arc goes from right_points[-1] to left_points[0]
    pts.extend(left_points)
    
    if rf < rb:
        pt_left_base = left_points[-1]
        ang_left_base = math.atan2(pt_left_base[1], pt_left_base[0])
        pts.append((rf * math.cos(ang_left_base), rf * math.sin(ang_left_base)))
        
    # We have one tooth profile. 
    # Create the tooth wire
    edges = []
    
    # Right root-to-base
    if rf < rb:
        edges.append(Edge.make_line(pts[0], pts[1]))
        idx_right_inv = 1
    else:
        idx_right_inv = 0
        
    # Right involute
    num_inv_points = len(right_points)
    right_spline = Spline(pts[idx_right_inv : idx_right_inv + num_inv_points])
    edges.append(right_spline)
    
    # Tip arc
    idx_tip_start = idx_right_inv + num_inv_points - 1
    idx_tip_end = idx_tip_start + 1
    # Center is (0,0), radius ra
    tip_arc = Edge.make_three_point_arc(
        pts[idx_tip_start],
        (ra, 0), # midpoint of tip approximately
        pts[idx_tip_end]
    )
    edges.append(tip_arc)
    
    # Left involute
    left_spline = Spline(pts[idx_tip_end : idx_tip_end + num_inv_points])
    edges.append(left_spline)
    
    # Left base-to-root
    if rf < rb:
        edges.append(Edge.make_line(pts[-2], pts[-1]))
        
    # Bottom root arc connecting this tooth to the next?
    # Actually, we want to make a single piece that can be polar arrayed.
    # We need a wedge that covers 360/z degrees.
    # The tooth is centered at 0.
    # The wedge goes from -pi/z to pi/z.
    angle_pitch = math.pi * 2 / z
    
    # We will just create a single 2D face for the tooth, polar array it, and fuse with root cylinder!
    
    tooth_wire = Wire(edges)

    # Make a closed wire by connecting the bottom
    # We use a straight line for simplicity, later we boolean union with the root cylinder.
    bottom_line = Edge.make_line(pts[-1], pts[0])
    closed_tooth = Wire(edges + [bottom_line])
    
    tooth_face = Face(closed_tooth)

    with BuildSketch() as sketch:
        Circle(radius=rf)
        with PolarLocations(0, z):
            add(tooth_face)
            
    return sketch.sketch, params

def create_spur_gear(m, z, width, alpha=20.0, x_shift=0.0):
    sketch, params = generate_spur_gear_profile(m, z, alpha, x_shift)
    
    with BuildPart() as part:
        add(sketch)
        extrude(amount=width)
        
    return part.part
