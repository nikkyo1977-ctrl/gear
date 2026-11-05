"""Eccezioni di gearcalc."""


class GearCalcError(Exception):
    """Errore base della libreria."""


class GeometryError(GearCalcError, ValueError):
    """Geometria non realizzabile o fuori dal campo di validità."""
