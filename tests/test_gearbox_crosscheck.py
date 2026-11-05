"""Confronto della geometria di coppia con python-gearbox (ISO 6336:2019)."""

import pytest

from gearcalc import CylindricalGear, GearPair, pair_geometry

gb = pytest.importorskip("gearbox")

CASES = [
    (20, 40, 2.0, 20.0, 0.0, 0.0, 0.0),
    (17, 51, 3.0, 30.0, 0.0, 0.3, -0.1),
    (22, 63, 2.5, 30.0, 15.0, 0.4, 0.25),
    (13, 47, 0.8, 6.0, 25.0, 0.45, 0.1),
]


def _gearbox_transmission(  # type: ignore[no-untyped-def]
    z1: int, z2: int, m: float, b: float, beta: float, x1: float, x2: float, internal: bool = False
):
    hob = gb.Tool(
        addendum_coefficient=1.0, dedendum_coefficient=1.25, root_fillet_radius_coefficient=0.38
    )
    shaper = gb.Tool(
        addendum_coefficient=1.0,
        dedendum_coefficient=1.25,
        root_fillet_radius_coefficient=0.38,
        cutter_type="shaper",
        cutter_teeth=25,
    )
    mat = gb.Material(
        material_type=gb.MaterialType.THROUGH_HARDENED_STEEL,
        contact_stress_limit=600.0,
        bending_stress_limit=250.0,
        brinell_hardness=250.0,
    )

    def gear(z: int, x: float, internal: bool = False):  # type: ignore[no-untyped-def]
        return gb.Gear(
            tool=shaper if internal else hob,
            internal=internal,
            material=mat,
            number_of_teeth=z,
            module=m,
            face_width=b,
            quality_grade=6,
            surface_roughness=1.0,
            shaft_diameter=20.0,
            shaft_arrangement=gb.ShaftArrangement.BETWEEN_BEARINGS_TOWARDS_TORQUED_END,
            bearing_span=100.0,
            offset=10.0,
            helix_angle=beta,
            profile_shift_coefficient=x,
        )

    return gb.Transmission(
        pinion=gear(z1, x1),
        wheel=gear(z2, x2, internal),
        lubricant=gb.Lubricant(kinematic_viscosity_40c=100.0),
        pinion_speed_rpm=1000.0,
        power_kw=1.0,
        design_life_hours=1000.0,
        dynamic_factor_method=gb.DynamicFactorMethod.METHOD_C,
    )


@pytest.mark.parametrize("case", CASES)
def test_against_python_gearbox(case: tuple[int, int, float, float, float, float, float]) -> None:
    z1, z2, m, b, beta, x1, x2 = case
    ref = _gearbox_transmission(*case)
    p = pair_geometry(
        GearPair(
            gear1=CylindricalGear(z=z1, m_n=m, b=b, beta=beta, x=x1),
            gear2=CylindricalGear(z=z2, m_n=m, b=b, beta=-beta, x=x2),
        )
    )
    assert p.a_w == pytest.approx(ref.working_center_distance, rel=1e-10)
    assert p.alpha_wt == pytest.approx(ref.working_pressure_angle, rel=1e-10)
    assert p.epsilon_alpha == pytest.approx(ref.transverse_contact_ratio, rel=1e-9)
    assert p.epsilon_beta == pytest.approx(ref.overlap_ratio, rel=1e-10)
    assert p.gear1.d_b == pytest.approx(ref.pinion.base_diameter, rel=1e-10)
    assert p.gear2.d_f == pytest.approx(ref.wheel.root_diameter, rel=1e-10)


INTERNAL_CASES = [
    (20, 60, 2.0, 20.0, 0.0, 0.0, 0.0),
    (15, 52, 1.0, 10.0, 12.0, 0.3, 0.2),
    (18, 45, 1.5, 10.0, 20.0, 0.2, -0.3),
]


@pytest.mark.parametrize("case", INTERNAL_CASES)
def test_internal_against_python_gearbox(
    case: tuple[int, int, float, float, float, float, float],
) -> None:
    z1, z2, m, b, beta, x1, x2 = case
    ref = _gearbox_transmission(*case, internal=True)
    p = pair_geometry(
        GearPair(
            gear1=CylindricalGear(z=z1, m_n=m, b=b, beta=beta, x=x1),
            gear2=CylindricalGear(z=z2, m_n=m, b=b, beta=beta, x=x2, internal=True),
        )
    )
    assert p.a_w == pytest.approx(ref.working_center_distance, rel=1e-10)
    assert p.alpha_wt == pytest.approx(ref.working_pressure_angle, rel=1e-10)
    assert p.epsilon_alpha == pytest.approx(ref.transverse_contact_ratio, rel=1e-9)
    assert p.gear2.d_a == pytest.approx(ref.wheel.tip_diameter, rel=1e-12)
    assert p.gear2.d_f == pytest.approx(ref.wheel.root_diameter, rel=1e-12)
    assert p.gear2.d_b == pytest.approx(ref.wheel.base_diameter, rel=1e-12)
