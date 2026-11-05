"""Geometria degli ingranaggi."""

from gearcalc.geometry.cylindrical import form_diameter_hob, gear_geometry, x_min_undercut
from gearcalc.geometry.involute import inv, inv_inverse, involute_xy
from gearcalc.geometry.measurement import (
    backlash,
    ideal_ball_diameter,
    over_balls,
    span_measurement,
    span_teeth,
    tooth_measurement,
)
from gearcalc.geometry.outline import GearOutline, OutlineSegment, gear_outline
from gearcalc.geometry.pair import (
    balanced_sliding_x1,
    pair_for_center_distance,
    pair_geometry,
    working_pressure_angle,
    x_sum_for_center_distance,
)
from gearcalc.geometry.profile import gear_profile, tooth_flank, undercut_form_diameter
from gearcalc.geometry.worm import (
    FlankForm,
    WormGearSet,
    WormGeometry,
    virtual_wheel,
    worm_geometry,
)

__all__ = [
    "FlankForm",
    "GearOutline",
    "OutlineSegment",
    "WormGearSet",
    "WormGeometry",
    "backlash",
    "balanced_sliding_x1",
    "form_diameter_hob",
    "gear_geometry",
    "gear_outline",
    "gear_profile",
    "ideal_ball_diameter",
    "inv",
    "inv_inverse",
    "involute_xy",
    "over_balls",
    "pair_for_center_distance",
    "pair_geometry",
    "span_measurement",
    "span_teeth",
    "tooth_flank",
    "tooth_measurement",
    "undercut_form_diameter",
    "virtual_wheel",
    "working_pressure_angle",
    "worm_geometry",
    "x_min_undercut",
    "x_sum_for_center_distance",
]
