import math
from build123d import *

def create_rack_gear(module, num_teeth, width, base_height=5.0, alpha=20.0):
    """
    Create a straight rack gear.
    module: gear module (mm)
    num_teeth: number of teeth on the rack
    width: width of the rack
    base_height: height of the base below root line
    alpha: pressure angle
    """
    pitch = math.pi * module
    alpha_rad = math.radians(alpha)
    
    addendum = module
    dedendum = 1.25 * module
    total_height = addendum + dedendum
    
    # Width of tooth at pitch line
    thickness_pitch = pitch / 2.0
    
    # Top width of the tooth
    top_width = thickness_pitch - 2 * addendum * math.tan(alpha_rad)
    bottom_width = thickness_pitch + 2 * dedendum * math.tan(alpha_rad)
    
    # Let's define the points of a single tooth centered at x=0
    # The bottom is at y = -dedendum, the top is at y = addendum
    
    pts = [
        (-bottom_width/2.0, -dedendum),
        (-top_width/2.0, addendum),
        (top_width/2.0, addendum),
        (bottom_width/2.0, -dedendum)
    ]
    
    with BuildSketch() as tooth_sketch:
        with BuildLine():
            Polyline(*pts)
            Line(pts[-1], pts[0])
        make_face()
    
    with BuildPart() as part:
        # Create base
        rack_length = pitch * num_teeth
        Box(rack_length, total_height + base_height, width, align=(Align.CENTER, Align.MIN, Align.CENTER))
        
        # Position base slightly down so tooth root is exactly at the surface
        # Surface is y = total_height + base_height - (total_height+base_height)/2 ...
        # Actually doing a base from y = -dedendum - base_height to -dedendum
        # Let's remake the base properly
    
    with BuildPart() as base:
        Box(rack_length, base_height, width, align=(Align.CENTER, Align.MAX, Align.MIN))
        # Move base down
    
    # Better approach: Draw everything in one sketch
    with BuildSketch() as full_sketch:
        # Base rectangle
        Rectangle(rack_length, base_height, align=(Align.CENTER, Align.MAX))
        # Translate to -dedendum
        
    with BuildPart() as rack:
        with BuildSketch():
            # The base
            with Locations((0, -dedendum)):
                Rectangle(rack_length, base_height, align=(Align.CENTER, Align.MAX))
            
            # The teeth
            start_x = - (num_teeth - 1) * pitch / 2.0
            for i in range(num_teeth):
                with Locations((start_x + i * pitch, 0)):
                    add(tooth_sketch)
        
        extrude(amount=width)
        
    return rack.part
