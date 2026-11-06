import math

import pytest

import tridi  # noqa: F401
import MeshPart
import Part
from FreeCAD import Vector as V

from projects.barholder import build
from projects.barholder.params import BarholderParams, bolt_tip_z, effective
from projects.barholder.parts import build_plate, build_strip
from tridi.export import to_bed
from tridi.features import hex_prisms
from tridi.printers import get_printer, load_printers

CLEAR = 0.2
BORE = 10.3
MID_WALL = 11.8  # the middle of the cradle's wall: bore 10.3 + half of the 3 mm wall
STRIP_T = 8
LEDGE = 2
NUT_TOP = 5.4  # the slot's ceiling: ledge 2 + nut 3.2 + 0.2 of room
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


def test_a_steeper_arm_slope_clears_the_arms_further_from_the_wall():
    s = strip(arm_slope=60)  # at y=2, 5 mm above the strip: the slope reaches z = 8 + 5 × tan 60° = 16.66
    assert not inside(s, MID_WALL, 2, 16) and inside(s, MID_WALL, 2, 17.5)


def test_arm_slope_is_measured_from_the_wall(default_strip):
    assert inside(default_strip, MID_WALL, 2, 16)  # at 45° the slope has passed z = 13 here, well before 16


@pytest.mark.parametrize("slope", [0, 60])
def test_the_lips_still_hold_the_bar_at_any_slope(slope):
    assert overlap(strip(arm_slope=slope), lift_path()) > 1
    y = BORE * math.sin(math.radians(22.5))
    assert inside(strip(arm_slope=slope), 19.03 / 2 + 0.1, y, 24)


@pytest.fixture(scope="module")
def straight_strip():
    return strip(arm_slope=0)


def test_at_zero_slope_the_arms_reach_the_wall(straight_strip):
    assert inside(straight_strip, MID_WALL, 2, 1)
    assert inside(straight_strip, -MID_WALL, 2, 1)
    assert inside(straight_strip, MID_WALL, 2, STRIP_T + 1)


def test_at_zero_slope_the_arms_sit_on_the_bed(straight_strip):
    assert straight_strip.optimalBoundingBox().ZMin == pytest.approx(0, abs=0.01)
    assert inside(straight_strip, MID_WALL, 2, 0.5)
    assert not inside(straight_strip, MID_WALL, 2, -0.1)


def test_at_zero_slope_the_seat_still_ends_at_the_stop(straight_strip):
    assert inside(straight_strip, 0, -8, 5)
    assert not inside(straight_strip, 0, -8, STRIP_T + 0.5)
    assert overlap(straight_strip, bar()) == pytest.approx(0, abs=1e-6)


def test_at_zero_slope_a_nut_still_drops_past_the_arm_into_the_end_slot(straight_strip):
    path = Part.makeBox(7, 40, 3.2, V(88.5 - 3.5, -11, LEDGE))  # from the bolt to well above the arm's top
    assert overlap(straight_strip, path) == pytest.approx(0, abs=1e-6)


def test_strip_drop_moves_the_top_edge_and_the_arm_slope():
    s = strip(strip_drop=5)
    assert not inside(s, 45, -4.5, 3) and inside(s, 45, -5.5, 3)
    assert not inside(s, MID_WALL, 2, STRIP_T + 6) and inside(s, MID_WALL, 2, STRIP_T + 8)


def test_the_seat_ends_in_a_stop_so_the_bar_never_reaches_the_wall(default_strip):
    assert inside(default_strip, 0, -8, 5)
    assert not inside(default_strip, 0, -8, STRIP_T + 0.5)


def test_above_the_strip_the_cradle_is_open_to_the_wall(default_strip):
    assert not inside(default_strip, 0, 2, 3)


# ---- leaning wall: the strip lies flat on the wall, the cradle's axis stays level


LEAN = 3.9
TAN = math.tan(math.radians(LEAN))  # 0.0682


@pytest.fixture(scope="module")
def leaning_strip():
    return strip(wall_angle=LEAN)


def level_bar(angle, x=0.0, d=20.0, start=1.0, length=60):
    """A level bar as the strip sees it. On a wall leaning outward going up, the wall's normal points up into the box,
    so level runs downward against the strip's y as it leaves the wall. Starts `start` mm clear of the stop."""
    a = math.radians(angle)
    axis = V(0, -math.sin(a), math.cos(a))
    return Part.makeCylinder(d / 2, length, V(x, -start * math.tan(a), STRIP_T + start), axis)


def test_a_level_bar_fits_the_seat_on_a_leaning_wall(leaning_strip):
    assert overlap(leaning_strip, level_bar(LEAN)) == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize("x", [-70, 70])
def test_every_cradle_on_the_strip_is_tilted(leaning_strip, x):
    assert overlap(leaning_strip, level_bar(LEAN, x)) == pytest.approx(0, abs=1e-6)


def test_a_level_bar_collides_with_a_cradle_made_for_a_straight_wall(default_strip):
    assert overlap(default_strip, level_bar(LEAN)) > 1


def test_a_cradle_tilted_the_wrong_way_would_fail_the_level_bar(leaning_strip):
    assert overlap(leaning_strip, level_bar(-LEAN)) > 1


def test_the_seat_drops_along_the_strip_as_it_leaves_the_wall(leaning_strip):
    # 16 mm past the stop at z = 24: down 16 × tan 3.9° = 1.09, so the floor runs from y = -11.39 to -14.39
    assert not inside(leaning_strip, 0, -11.2, 24)
    assert inside(leaning_strip, 0, -11.6, 24)
    assert inside(leaning_strip, 0, -14.2, 24)
    assert not inside(leaning_strip, 0, -14.6, 24)


def test_the_seat_is_where_it_was_at_the_stop():
    s = strip(wall_angle=LEAN, drain=False)
    assert not inside(s, 0, -10.2, STRIP_T + 0.1)
    assert inside(s, 0, -10.4, STRIP_T + 0.1)


def test_the_tilt_stays_inside_the_flat_faces_for_the_bed_and_the_front(leaning_strip):
    bb = leaning_strip.optimalBoundingBox()
    assert (bb.ZMin, bb.ZMax) == (pytest.approx(0, abs=0.01), pytest.approx(25, abs=0.01))


def test_the_strip_itself_does_not_tilt(leaning_strip):
    assert inside(leaning_strip, 45, -18.5, 0.5) and inside(leaning_strip, 45, -18.5, STRIP_T - 0.1)
    assert not inside(leaning_strip, 45, -3.2 + 0.4, 3) and inside(leaning_strip, 45, -3.2, 3)


def test_the_lips_still_stand_in_the_way_out_on_a_leaning_wall(leaning_strip):
    # 16 mm past the stop, the lip has dropped with the seat
    y = BORE * math.sin(math.radians(22.5)) - 16 * TAN
    assert inside(leaning_strip, 19.03 / 2 + 0.1, y, 24)
    assert not inside(leaning_strip, 19.03 / 2 - 0.1, y, 24)


def test_drain_still_runs_clear_through_a_tilted_floor(leaning_strip):
    path = Part.makeBox(3.8, 30, 5.8, V(-1.9, -40, STRIP_T + 0.1))
    assert overlap(leaning_strip, path) == pytest.approx(0, abs=1e-6)


def test_bracket_ribs_follow_the_tilted_cradle():
    s = strip(wall_angle=LEAN, bracket=True)
    assert s.isValid() and len(s.Solids) == 1
    assert overlap(s, level_bar(LEAN)) == pytest.approx(0, abs=1e-6)
    assert inside(s, 3.5, -15.5, 24.9)  # the rib's front runs below the dropped floor
    fall = Part.makeBox(3.9, 24, 5.9, V(-1.95, -34, STRIP_T + 0.01))
    assert overlap(s, fall) == pytest.approx(0, abs=1e-6)


def test_arm_slope_is_still_measured_from_the_wall_on_a_leaning_wall(leaning_strip):
    # the cut belongs to the print, not the cradle: it still reaches y = 2 at z = 13
    assert not inside(leaning_strip, MID_WALL, 2, 12)


def test_straight_arms_still_sit_on_the_bed_on_a_leaning_wall():
    s = strip(wall_angle=LEAN, arm_slope=0)
    assert s.optimalBoundingBox().ZMin == pytest.approx(0, abs=0.01)
    assert inside(s, MID_WALL, 2.3, 0.1)
    assert overlap(s, level_bar(LEAN)) == pytest.approx(0, abs=1e-6)


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


ENTRIES = ["top", "front"]


@pytest.fixture(scope="module")
def front_strip():
    return strip(nut_entry="front")


def nut(x, y, z0=LEDGE, length=3.2, af=7.0):
    """A nut's solid, flats facing ±x as it has to sit to enter the slot."""
    return hex_prisms([(x, y)], af, z0, length, "y")


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("x", [-88.5, -35, 35, 88.5])
def test_tightening_clamps_the_strip_because_the_nut_pulls_on_plastic(entry, x):
    # the bolt pulls the nut toward the wall, so there has to be plastic between them all round the hole
    s = strip(nut_entry=entry)
    for dx, dy in ((3.0, 0), (-3.0, 0), (0, 3.0), (0, -3.0)):
        assert inside(s, x + dx, -11 + dy, 1)  # the ledge
        assert not inside(s, x + dx, -11 + dy, LEDGE + 0.2)  # the nut's place


@pytest.mark.parametrize("entry", ENTRIES)
def test_the_bolt_passes_the_ledge_through_its_hole(entry):
    s = strip(nut_entry=entry)
    assert not inside(s, 35, -11, 1) and not inside(s, 35 + 2, -11, 1)
    assert inside(s, 35 + 2.4, -11, 1)


@pytest.mark.parametrize("entry", ENTRIES)
def test_a_nut_at_the_bolt_touches_nothing(entry):
    assert overlap(strip(nut_entry=entry), nut(35, -11)) == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize("x", [-88.5, -35, 35, 88.5])
def test_slot_lets_a_nut_drop_in_from_the_strips_top_edge(default_strip, x):
    path = Part.makeBox(7, 11, 3.2, V(x - 3.5, -11, LEDGE))  # from the bolt to above the strip's top at -3
    assert overlap(default_strip, path) == pytest.approx(0, abs=1e-6)


def test_slot_stops_a_dropped_nut_centred_on_the_bolt(default_strip):
    assert overlap(default_strip, nut(35, -12)) > 1


def test_slot_holds_the_nut_from_turning(default_strip):
    assert not inside(default_strip, 35 + 3.6, -11, 3.5)  # 7.4 mm across flats: a sliding fit
    assert inside(default_strip, 35 + 3.8, -11, 3.5)


def test_slot_is_a_low_ceiling_with_the_meat_side_closed(default_strip):
    assert not inside(default_strip, 35 + 3, -11, NUT_TOP - 0.1)
    assert inside(default_strip, 35 + 3, -11, NUT_TOP + 0.1)
    assert inside(default_strip, 35 + 3, -11, STRIP_T - 0.1)


@pytest.mark.parametrize("x", [-88.5, -35, 35, 88.5])
def test_no_bolt_or_nut_shows_on_the_meat_side_with_a_slot(default_strip, x):
    assert not inside(default_strip, x, -11, 6.8)  # room for an M4×12's tip at 6.5 mm
    assert inside(default_strip, x, -11, 7.2)
    assert inside(default_strip, x, -11, STRIP_T - 0.1)


def test_blind_hole_follows_the_bolt_length():
    s = strip(box_wall=3, strip_thickness=11)  # M4×16: tip at 9.5 mm
    assert not inside(s, 35, -11, 9.8) and inside(s, 35, -11, 10.2)


def test_front_pocket_opens_toward_the_meat_side(front_strip):
    path = nut(35, -11, length=20)
    assert overlap(front_strip, path) == pytest.approx(0, abs=1e-6)
    assert not inside(front_strip, 35, -11, STRIP_T - 0.1)


def test_front_pocket_is_a_push_fit_closed_at_the_top_edge(front_strip):
    assert not inside(front_strip, 35 + 3.4, -11, 4)  # 7.2 mm across flats
    assert inside(front_strip, 35 + 3.8, -11, 4)
    assert inside(front_strip, 35, -5, 4)


def test_bolt_tip_stays_inside_the_front_pocket():
    p = effective(BarholderParams(nut_entry="front"))[0]
    assert bolt_tip_z(p) < p.strip_thickness


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


@pytest.mark.parametrize("kw", [{}, {"bracket": True},
                                {"bar_d": 40, "pitch": 100, "strip_height": 14, "cradle_depth": 30}])
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
    # 20 mm bracket: foot at y = -33.3; slope from z = 8 there to z = 25 at y = -15.3
    assert inside(bracket_strip, 3.5, -33, 8.1)
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
                                {"wrap": 180, "drain": False}, {"nut_entry": "front"},
                                {"arm_slope": 0}, {"arm_slope": 60}, {"arm_slope": 0, "bracket": True},
                                {"wall_angle": 3.9}, {"wall_angle": 3.9, "bracket": True},
                                {"wall_angle": 8, "arm_slope": 0}])
def test_strip_needs_no_supports_beyond_short_bridges(kw):
    # the only flat undersides allowed: the nut slots' ceilings, the bolt holes' ends and the drain's roof
    p = part("strip", **kw)
    assert steep_overhang_heights(to_bed(p.shape, p.rotation)) <= {NUT_TOP, 7.0, 14.0}


def test_at_zero_slope_nothing_overhangs_at_all():
    p = part("strip", arm_slope=0, nut_entry="front", drain=False)
    assert steep_overhang_heights(to_bed(p.shape, p.rotation)) == set()


def test_a_slope_shallower_than_45_overhangs_along_the_arms():
    p = part("strip", arm_slope=30, nut_entry="front", drain=False)
    assert steep_overhang_heights(to_bed(p.shape, p.rotation))


def test_front_pockets_print_with_no_bridge_over_the_nut():
    p = part("strip", nut_entry="front", drain=False)
    assert steep_overhang_heights(to_bed(p.shape, p.rotation)) == set()


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
    {"bar_d": 12}, {"bar_d": 25}, {"bar_d": 40, "pitch": 100, "cradle_depth": 30},
    {"count": 1}, {"count": 1, "bracket": True}, {"count": 2, "pitch": 50},
    {"wrap": 180}, {"wrap": 200}, {"wrap": 240},
    {"cradle_depth": 60, "bracket": True, "bracket_height": 40},
    {"cradle_wall": 2}, {"cradle_wall": 5},
    {"strip_height": 24}, {"strip_drop": 0}, {"strip_drop": 6},
    {"drain": False}, {"backplate": False}, {"bed_chamfer": 0},
    {"bar_d": 40, "pitch": 100, "strip_height": 14, "cradle_depth": 30},
    {"bar_d": 40, "pitch": 100, "strip_height": 14, "cradle_depth": 30, "bracket": True},
    {"wall_angle": 3.9}, {"wall_angle": 3.9, "bracket": True}, {"wall_angle": 3.9, "arm_slope": 0},
    {"wall_angle": 3.9, "arm_slope": 60}, {"wall_angle": 3.9, "nut_entry": "front"}, {"wall_angle": 3.9, "count": 1},
    {"wall_angle": 3.9, "cradle_depth": 40, "bracket": True}, {"wall_angle": 15, "cradle_depth": 40},
    {"wall_angle": 15, "cradle_depth": 40, "bracket": True, "bracket_height": 30},
    {"wall_angle": 3.9, "bar_d": 40, "pitch": 100, "strip_height": 14, "cradle_depth": 30},
    {"wall_angle": 3.9, "drain": False}, {"wall_angle": 3.9, "bar_d": 12, "wrap": 240, "bracket": True},
    {"arm_slope": 0}, {"arm_slope": 0, "bracket": True}, {"arm_slope": 0, "nut_entry": "front"},
    {"arm_slope": 0, "count": 1}, {"arm_slope": 0, "wrap": 180}, {"arm_slope": 0, "bar_d": 12},
    {"arm_slope": 0, "bar_d": 40, "pitch": 100, "cradle_depth": 30, "strip_height": 14},
    {"arm_slope": 30}, {"arm_slope": 60}, {"arm_slope": 60, "bracket": True},
    {"arm_slope": 80, "cradle_depth": 60},
    {"nut_entry": "front"}, {"nut_entry": "front", "bracket": True}, {"nut_entry": "front", "count": 1},
    {"nut_entry": "front", "backplate": False}, {"count": 1, "strip_height": 14}, {"nut_af": 10, "strip_height": 18},
    {"bar_d": 12, "wrap": 240, "cradle_wall": 4, "bracket": True},
])
def test_common_variants_build_one_valid_solid(kw):
    p = effective(BarholderParams(**kw))[0]
    for shape in (build_strip(p, CLEAR), build_plate(p, CLEAR)):
        assert shape.isValid() and len(shape.Solids) == 1 and shape.Volume > 0
