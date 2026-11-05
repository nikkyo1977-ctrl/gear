"""gearcalc: libreria di calcolo ingranaggi (geometria e verifica), senza dipendenze CAD."""

from gearcalc.errors import GearCalcError, GeometryError
from gearcalc.geometry import gear_geometry, gear_profile, pair_for_center_distance, pair_geometry
from gearcalc.models import (
    BasicRackProfile,
    CylindricalGear,
    GearGeometry,
    GearPair,
    PairGeometry,
    StandardRack,
)

__version__ = "0.1.0"

__all__ = [
    "BasicRackProfile",
    "CylindricalGear",
    "GearCalcError",
    "GearGeometry",
    "GearPair",
    "GeometryError",
    "PairGeometry",
    "StandardRack",
    "__version__",
    "gear_geometry",
    "gear_profile",
    "pair_for_center_distance",
    "pair_geometry",
]
