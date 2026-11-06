import math

import pytest

import tridi  # noqa: F401
import MeshPart
import Part
from FreeCAD import Vector as V

from projects.barholder import build
from projects.barholder.params import BarholderParams, effective
from projects.barholder.parts import build_plate, build_strip
from tridi.export import to_bed
from tridi.printers import get_printer, load_printers

CLEAR = 0.2
BORE = 10.3
MID_WALL = 11.8  # the middle of the cradle's wall: bore 10.3 + half of the 3 mm wall
STRIP_T = 7
PRINTER = get_printer("mk3s", load_printers())


def strip(**kw):
    return build_strip(effective(BarholderParams(**kw))[0], CLEAR)


def plate(**kw):
    return build_plate(effective(BarholderParams(**kw))[0], CLEAR)


def part(name, **kw):
    return {x.name: x for x in build(BarholderParams(**kw), PRINTER)[0]}[name]


@pytest.fixture(scope="module")
def default_strip():
    return strip()


@pytest.fixture(scope="module")
def default_plate():
    return plate()


@pytest.fixture(scope="module")
def bracket_strip():
    return strip(bracket=True)


def inside(shape, x, y, z):
    return shape.isInside(V(x, y, z), 1e-6, True)


def overlap(shape, cutter):
    return shape.common(cutter).Volume


def bar(x=0.0, d=20.0, z0=STRIP_T + 0.01, length=60):
    return Part.makeCylinder(d / 2, length, V(x, 0, z0))


def lift_path(x=0.0, d=20.0, y0=0.0, z0=STRIP_T + 0.01):
    """What a bar sweeps through when lifted straight up out of its seat."""
    return Part.makeBox(d, 60, 60, V(x - d / 2, y0, z0))


# ---- strip: overall shape


def test_strip_is_one_solid_of_the_agreed_size(default_strip):
    assert default_strip.isValid() and len(default_strip.Solids) == 1
    bb = default_strip.optimalBoundingBox()
    assert bb.XLength == pytest.approx(193, abs=0.05)
    assert (bb.ZMin, bb.ZMax) == (pytest.approx(0, abs=0.01), pytest.approx(25, abs=0.01))
    assert bb.YMin == pytest.approx(-19, abs=0.05)


@pytest.mark.parametrize("depth", [22, 40, 80])
def test_cradle_depth_sets_how_far_the_part_stands_off_the_wall(depth):
    assert strip(cradle_depth=depth).optimalBoundingBox().ZMax == pytest.approx(depth, abs=0.01)


@pytest.mark.parametrize("count, x_len", [(1, 53), (2, 123), (3, 193)])
def test_each_extra_cradle_adds_one_pitch_of_length(count, x_len):
    assert strip(count=count).optimalBoundingBox().XLength == pytest.approx(x_len, abs=0.05)


# ---- cradle: seat and snap


@pytest.mark.parametrize("x", [-70, 0, 70])
def test_a_seated_bar_touches_nothing(default_strip, x):
    assert overlap(default_strip, bar(x)) == pytest.approx(0, abs=1e-6)


def test_a_seated_bar_touches_nothing_on_a_thicker_bar_too():
    assert overlap(strip(bar_d=30), bar(d=30)) == pytest.approx(0, abs=1e-6)


def test_a_bar_too_big_for_the_fit_gap_collides_with_the_seat(default_strip):
    assert overlap(default_strip, bar(d=21)) > 1


def test_the_lips_stand_in_a_bars_way_on_the_way_out(default_strip):
    assert overlap(default_strip, lift_path()) > 1


def test_at_180_degrees_a_bar_lifts_straight_out():
    assert overlap(strip(wrap=180), lift_path()) == pytest.approx(0, abs=1e-6)


def test_the_mouth_has_the_narrowest_point_at_the_lip(default_strip):
    # 225° wrap: lips 22.5° above the bar's centre, 19.03 mm apart
    y = BORE * math.sin(math.radians(22.5))
    half = 19.03 / 2
    z = 24
    assert inside(default_strip, half + 0.1, y, z) and inside(default_strip, -half - 0.1, y, z)
    assert not inside(default_strip, half - 0.1, y, z)


def test_the_mouth_flares_wider_than_the_bar_at_its_top_for_an_easy_start(default_strip):
    top = default_strip.optimalBoundingBox().YMax
    assert not inside(default_strip, 10.5, top - 0.1, 24)


def test_a_wider_wrap_grips_tighter():
    loose, tight = strip(wrap=210), strip(wrap=240)
    assert overlap(loose, lift_path()) < overlap(tight, lift_path())


# ---- cradle: arms free of the strip, so the snap isn't locked solid near the wall


def test_arms_stand_free_of_the_strip_near_the_wall(default_strip):
    y = 2  # above the strip's top edge at -3
    assert not inside(default_strip, MID_WALL, y, 1)
    assert not inside(default_strip, MID_WALL, y, STRIP_T + 4)  # the 45° slope reaches y=2 at z=12
    assert inside(default_strip, MID_WALL, y, STRIP_T + 6)
    assert inside(default_strip, MID_WALL, y, 24)


def test_strip_drop_moves_the_top_edge_and_the_arm_slope():
    s = strip(strip_drop=5)
    assert not inside(s, 45, -4.5, 3) and inside(s, 45, -5.5, 3)
    assert not inside(s, MID_WALL, 2, STRIP_T + 6) and inside(s, MID_WALL, 2, STRIP_T + 8)


def test_the_seat_ends_in_a_stop_so_the_bar_never_reaches_the_wall(default_strip):
    assert inside(default_strip, 0, -8, 5)
    assert not inside(default_strip, 0, -8, STRIP_T + 0.5)


def test_above_the_strip_the_cradle_is_open_to_the_wall(default_strip):
    assert not inside(default_strip, 0, 2, 3)


# ---- drain


def test_drain_is_a_gap_in_the_floor_right_against_the_stop(default_strip):
    assert not inside(default_strip, 0, -MID_WALL, STRIP_T + 0.2)
    assert not inside(default_strip, 0, -MID_WALL, STRIP_T + 5.8)
    assert inside(default_strip, 0, -MID_WALL, STRIP_T + 6.2)


def test_drain_leaves_the_ring_closed_in_front_of_it(default_strip):
    assert inside(default_strip, 0, -MID_WALL, 24)


def test_drain_is_as_wide_as_asked(default_strip):
    assert not inside(default_strip, 1.9, -MID_WALL, STRIP_T + 2)
    assert inside(default_strip, 2.1, -MID_WALL, STRIP_T + 2)


def test_drain_can_be_turned_off():
    assert inside(strip(drain=False), 0, -MID_WALL, STRIP_T + 2)


# ---- bolts and nuts


@pytest.mark.parametrize("x", [-88.5, -35, 35, 88.5])
def test_each_bolt_has_a_nut_pocket_opening_toward_the_wall(default_strip, x):
    assert not inside(default_strip, x, -11, 0.5)
    assert not inside(default_strip, x + 3.4, -11, 3.2)  # 7.2 mm across flats, flats facing ±x
    assert inside(default_strip, x + 3.8, -11, 3.2)
    assert inside(default_strip, x + 3, -11, 3.6)  # the nut stops at the pocket's ceiling


@pytest.mark.parametrize("x", [-88.5, -35, 35, 88.5])
def test_no_bolt_or_nut_shows_on_the_meat_side(default_strip, x):
    assert not inside(default_strip, x, -11, 4.7)  # room for an M4×10's tip at 4.5 mm
    assert inside(default_strip, x, -11, 5.5)
    assert inside(default_strip, x, -11, STRIP_T - 0.1)


def test_blind_hole_follows_the_bolt_length():
    s = strip(box_wall=3)  # M4×12: tip at 5.5 mm
    assert not inside(s, 35, -11, 5.7) and inside(s, 35, -11, 6.5)


def test_a_single_cradle_only_has_end_holes():
    s = strip(count=1)
    assert not inside(s, 18.5, -11, 1) and not inside(s, -18.5, -11, 1)


# ---- backplate


def test_plate_is_one_solid_on_the_outside_of_the_wall(default_plate):
    assert default_plate.isValid() and len(default_plate.Solids) == 1
    bb = default_plate.optimalBoundingBox()
    assert (bb.ZMin, bb.ZMax) == (pytest.approx(-6, abs=0.01), pytest.approx(-2, abs=0.01))


@pytest.mark.parametrize("x", [-88.5, -35, 35, 88.5])
def test_plate_holes_are_on_the_strips_bolts_and_go_through(default_plate, x):
    assert not inside(default_plate, x + 2, -11, -3)  # the 4.5 mm hole
    assert inside(default_plate, x + 2.4, -11, -3)


def test_plate_countersink_opens_outward(default_plate):
    assert not inside(default_plate, 35 + 4, -11, -5.8)  # the 8.4 mm head at the outer face
    assert inside(default_plate, 35 + 4, -11, -3)


def outline_size(shape, z):
    box = max(shape.slice(V(0, 0, 1), z), key=lambda w: w.BoundBox.DiagonalLength).BoundBox
    return box.XLength, box.YLength


@pytest.mark.parametrize("kw", [{}, {"bracket": True}, {"bar_d": 40, "pitch": 100, "strip_height": 14}])
def test_plate_has_the_strips_outline(kw):
    assert outline_size(plate(**kw), -2.5) == pytest.approx(outline_size(strip(**kw), 0.5), abs=0.05)


# ---- support bracket


def test_no_bracket_by_default(default_strip):
    assert not inside(default_strip, 3.5, -22, 10)


def test_bracket_is_one_solid_with_the_strip(bracket_strip):
    assert bracket_strip.isValid() and len(bracket_strip.Solids) == 1


@pytest.mark.parametrize("x", [-70, 0, 70])
def test_each_cradle_gets_a_pair_of_ribs(bracket_strip, x):
    # ribs run from 2 to 5 mm either side of centre, from the foot up to the cradle's underside
    for side in (1, -1):
        assert inside(bracket_strip, x + side * 3.5, -22, 10)
        assert inside(bracket_strip, x + side * 3.5, -14.5, 24)
    assert not inside(bracket_strip, x, -22, 10)


def test_ribs_reach_the_front_of_the_cradle(bracket_strip):
    assert inside(bracket_strip, 3.5, -15, 24.9)


def test_ribs_slope_down_to_the_foot_at_the_wall(bracket_strip):
    # 20 mm bracket: foot at y = -33.3; slope from z = 7 there to z = 25 at y = -15.3
    assert inside(bracket_strip, 3.5, -33, 7.1)
    assert not inside(bracket_strip, 3.5, -30, 16)
    assert inside(bracket_strip, 3.5, -20, 16)


def test_foot_sits_flat_on_the_wall(bracket_strip):
    assert inside(bracket_strip, 0, -33, 0.5) and inside(bracket_strip, 0, -33, STRIP_T - 0.1)
    assert not inside(bracket_strip, 0, -33.6, 3)


def test_bracket_height_moves_the_foot():
    s = strip(bracket=True, bracket_height=30)
    assert inside(s, 0, -43, 3) and not inside(s, 0, -43.6, 3)


def test_ribs_keep_the_drain_clear(bracket_strip):
    # a drop leaving the notch falls past the ribs, in front of the strip and the foot
    fall = Part.makeBox(3.9, 24, 5.9, V(-1.95, -34, STRIP_T + 0.01))
    assert overlap(bracket_strip, fall) == pytest.approx(0, abs=1e-6)


def test_ribs_do_not_reach_into_the_bars_seat(bracket_strip):
    assert overlap(bracket_strip, bar()) == pytest.approx(0, abs=1e-6)


def test_plate_extends_behind_the_foot_only_with_a_bracket():
    assert inside(plate(bracket=True), 0, -32, -4)
    assert not inside(plate(), 0, -32, -4)


def test_bracket_works_without_a_drain():
    s = strip(bracket=True, drain=False)
    assert inside(s, 3.5, -22, 10) and inside(s, 0, -MID_WALL, STRIP_T + 2)


# ---- printing


def steep_overhang_heights(shape):
    """Heights, in print orientation, of surfaces facing the bed at more than 45°. The bed itself and the chamfer
    along it don't count: that chamfer is 45° and meshes a little steeper on tight corners."""
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.2618)
    heights = set()
    for facet in mesh.Facets:
        z = min(p[2] for p in facet.Points)
        if facet.Normal.z < -0.72 and z > 0.41:
            heights.add(round(z, 1))
    return heights


@pytest.mark.parametrize("kw", [{}, {"bracket": True}, {"cradle_depth": 40, "bracket": True},
                                {"wrap": 180, "drain": False}])
def test_strip_needs_no_supports_beyond_short_bridges(kw):
    # the only flat undersides allowed: the nut pockets' ceilings, the bolt holes' ends and the drain's roof
    p = part("strip", **kw)
    assert steep_overhang_heights(to_bed(p.shape, p.rotation)) <= {3.4, 5.0, 13.0}


def test_plate_prints_with_the_wall_side_on_the_bed_and_seats_up():
    p = part("backplate")
    plated = to_bed(p.shape, p.rotation)
    assert plated.optimalBoundingBox().ZLength == pytest.approx(4, abs=0.01)
    assert steep_overhang_heights(plated) == set()
    # the bolt's shaft on the bed, widening to the head's seat on top
    def hole_at(z):
        wires = sorted(plated.slice(V(0, 0, 1), z), key=lambda w: w.BoundBox.XLength)
        return wires[0].BoundBox.XLength
    assert hole_at(1) == pytest.approx(4.5, abs=0.05)
    assert hole_at(3.9) == pytest.approx(8.4, abs=0.05)


def test_build_makes_a_strip_and_a_plate():
    names = [x.name for x in build(BarholderParams(), PRINTER)[0]]
    assert names == ["strip", "backplate"]


def test_backplate_can_be_left_out():
    names = [x.name for x in build(BarholderParams(backplate=False), PRINTER)[0]]
    assert names == ["strip"]


def test_bed_edges_are_chamfered_against_elephants_foot(default_strip):
    assert inside(default_strip, 45, -18.5, 0.5)
    assert not inside(default_strip, 45, -18.9, 0.05)


# ---- combinations a user is likely to try


@pytest.mark.parametrize("kw", [
    {"bar_d": 12}, {"bar_d": 25}, {"bar_d": 40, "pitch": 100},
    {"count": 1}, {"count": 1, "bracket": True}, {"count": 2, "pitch": 50},
    {"wrap": 180}, {"wrap": 200}, {"wrap": 240},
    {"cradle_depth": 60, "bracket": True, "bracket_height": 40},
    {"cradle_wall": 2}, {"cradle_wall": 5},
    {"strip_height": 24}, {"strip_drop": 0}, {"strip_drop": 6},
    {"drain": False}, {"backplate": False}, {"bed_chamfer": 0},
    {"bar_d": 40, "pitch": 100, "strip_height": 14},
    {"bar_d": 40, "pitch": 100, "strip_height": 14, "bracket": True},
    {"bar_d": 12, "wrap": 240, "cradle_wall": 4, "bracket": True},
])
def test_common_variants_build_one_valid_solid(kw):
    p = effective(BarholderParams(**kw))[0]
    for shape in (build_strip(p, CLEAR), build_plate(p, CLEAR)):
        assert shape.isValid() and len(shape.Solids) == 1 and shape.Volume > 0
