"""gearcalc: libreria di calcolo ingranaggi (geometria e verifica), senza dipendenze CAD."""

from gearcalc.errors import GearCalcError, GeometryError
from gearcalc.geometry import (
    backlash,
    gear_geometry,
    gear_profile,
    pair_for_center_distance,
    pair_geometry,
    tooth_measurement,
)
from gearcalc.models import (
    Backlash,
    BasicRackProfile,
    CylindricalGear,
    GearGeometry,
    GearPair,
    PairGeometry,
    ShiftDistribution,
    StandardRack,
    ThicknessAllowances,
    ToothMeasurement,
)

__version__ = "0.1.0"

__all__ = [
    "Backlash",
    "BasicRackProfile",
    "CylindricalGear",
    "GearCalcError",
    "GearGeometry",
    "GearPair",
    "GeometryError",
    "PairGeometry",
    "ShiftDistribution",
    "StandardRack",
    "ThicknessAllowances",
    "ToothMeasurement",
    "__version__",
    "backlash",
    "gear_geometry",
    "gear_profile",
    "pair_for_center_distance",
    "pair_geometry",
    "tooth_measurement",
]
