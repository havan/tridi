import math

import pytest

import tridi  # noqa: F401
import MeshPart
import Part
from FreeCAD import Vector as V

from projects.fanbox import build
from projects.fanbox.params import FanboxParams, effective, fan_bolt_length, lid_bolt_length, lid_bolt_xy
from projects.fanbox.parts import (NUT_CEILING, _duct_passage, _fan_nut_cutters, build_duct, build_frame, build_plate,
                                   frame_z, rim_z)
from tridi.export import to_bed
from tridi.features import hex_prisms, rounded_rect
from tridi.printers import get_printer, load_printers

P = effective(FanboxParams())[0]
CLEAR = 0.2
FAN = P.fan_hole_spacing / 2  # 62.25
SEAT = P.duct_height  # 55
RIM = rim_z(P)  # 80
POCKET = P.fan_size / 2 + P.fan_fit  # 70.3
OUTER = POCKET + P.socket_wall  # 72.7
LX, LY = lid_bolt_xy(P)  # 79, 35
EAR_TIP = P.base_length / 2 + P.ear_length  # 88
CORNERS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
PRINTER = get_printer("mk3s", load_printers())


def resolved(**kw):
    return effective(FanboxParams(**kw))[0]


@pytest.fixture(scope="module")
def duct():
    return build_duct(P, CLEAR)


@pytest.fixture(scope="module")
def plate():
    return build_plate(P, CLEAR)


@pytest.fixture(scope="module")
def frame():
    return build_frame(P, CLEAR)


def inside(shape, x, y, z):
    return shape.isInside(V(x, y, z), 1e-6, True)


def box(shape):
    return shape.optimalBoundingBox()


# ---- duct


def test_duct_is_one_solid_of_the_agreed_size(duct):
    assert duct.isValid() and len(duct.Solids) == 1
    bb = box(duct)
    assert bb.XLength == pytest.approx(176, abs=0.05)
    assert bb.YLength == pytest.approx(145.4, abs=0.05)
    assert (bb.ZMin, bb.ZMax) == (pytest.approx(0, abs=0.01), pytest.approx(80, abs=0.01))


def test_base_stays_inside_the_90_mm_width(duct):
    ys = [v.Y for w in duct.slice(V(0, 0, 1), 3) for v in w.Vertexes]
    assert max(ys) == pytest.approx(45, abs=0.01) and min(ys) == pytest.approx(-45, abs=0.01)


def test_air_passage_is_open_top_to_bottom(duct):
    for z in (0.5, 3, 10, 30, 48, 54.5, 60, 79):
        assert not inside(duct, 0, 0, z)
    # the 84 × 134 opening at the lid
    assert not inside(duct, 66.5, 0, 1) and not inside(duct, 0, 41.5, 1)
    assert inside(duct, 68.5, 0, 3) and inside(duct, 0, 43.5, 3)
    # the round bore under the fan
    assert not inside(duct, 67.5, 0, 54) and not inside(duct, 0, 67.5, 54)
    assert inside(duct, 69, 0, 54) and inside(duct, 0, 69, 54)


def test_duct_widens_from_90_to_the_socket_on_the_short_side(duct):
    assert not inside(duct, 0, 50, 8)  # outside the wall near the base
    assert inside(duct, 0, 71, 52)  # in the wall at the top
    assert not inside(duct, 0, 50, 40)  # in the passage higher up


def _wall_along(shape, z, angle):
    """Length of solid crossed going outward from the axis at this height and direction."""
    ray = Part.makeLine(V(0, 0, z), V(200 * math.cos(angle), 200 * math.sin(angle), z))
    return shape.common(ray).Length


@pytest.mark.parametrize("z", [8, 15, 25, 35, 45])
@pytest.mark.parametrize("deg", [0, 20, 60, 90, 120, 180, 270])
def test_wall_is_never_thin(duct, z, deg):
    assert _wall_along(duct, z, math.radians(deg)) >= 2.0


def test_lid_bolt_seat_is_a_countersink_opening_upward(duct):
    flange = P.flange_thickness
    assert not inside(duct, LX + 4.1, LY, flange - 0.1)  # wide at the top
    assert not inside(duct, LX + 2.15, LY, 0.1)  # shank clearance all the way down
    assert inside(duct, LX + 3, LY, 2)  # narrows to the shank, so the head can't pull through


def test_lid_bolt_head_sits_below_the_surface(duct):
    assert not inside(duct, LX + 4.15, LY, P.flange_thickness - 0.4)


# ---- socket


def test_fan_sits_on_a_flat_seat(duct):
    assert inside(duct, 69, 0, SEAT - 0.1) and not inside(duct, 69, 0, SEAT + 0.1)
    assert inside(duct, 0, 69, SEAT - 0.1) and not inside(duct, 0, 69, SEAT + 0.1)


def test_socket_walls_surround_the_fan_to_the_rim(duct):
    for z in (SEAT + 0.5, 65, RIM - 0.5):
        for x, y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            assert not inside(duct, x * (POCKET - 0.1), y * (POCKET - 0.1), z)
            assert inside(duct, x * (POCKET + 0.1), y * (POCKET + 0.1), z)
            assert inside(duct, x * (OUTER - 0.1), y * (OUTER - 0.1), z)
            assert not inside(duct, x * (OUTER + 0.1), y * (OUTER + 0.1), z)


def test_fan_fits_the_socket(duct):
    half = P.fan_size / 2
    fan = rounded_rect(-half, -half, half, half, P.fan_corner_r, SEAT, P.fan_thickness)
    assert fan.common(duct).Volume == pytest.approx(0, abs=1e-6)


def test_socket_stops_the_fan_from_shifting(duct):
    half = P.fan_size / 2 + 2 * P.fan_fit + 0.05
    fan = rounded_rect(-half, -half, half, half, P.fan_corner_r, SEAT, P.fan_thickness)
    assert fan.common(duct).Volume > 0


def test_cable_notch_is_on_the_chosen_side_only(duct):
    y = P.cable_offset
    assert not inside(duct, OUTER - 1, y, RIM - 1)  # through the wall
    assert inside(duct, OUTER - 1, y, RIM - P.cable_notch_depth - 0.1)  # with a floor
    assert inside(duct, OUTER - 1, y + P.cable_notch_width / 2 + 0.1, RIM - 1)  # and sides
    assert inside(duct, OUTER - 1, -y, RIM - 1) and inside(duct, -OUTER + 1, y, RIM - 1)


@pytest.mark.parametrize("side, x, y", [("right", 1, 0), ("left", -1, 0), ("back", 0, 1), ("front", 0, -1)])
def test_cable_notch_side_and_offset_are_customizable(side, x, y):
    d = build_duct(resolved(cable_side=side, cable_offset=20, cable_notch_width=8, cable_notch_depth=6), CLEAR)
    along = 20
    px, py = (x * (OUTER - 1), along) if x else (along, y * (OUTER - 1))
    assert not inside(d, px, py, RIM - 5.5)
    assert inside(d, px, py, RIM - 6.5)


def test_cable_notch_can_be_left_out():
    d = build_duct(resolved(cable_notch_width=0), CLEAR)
    assert inside(d, OUTER - 1, P.cable_offset, RIM - 1)


def test_mesh_lift_raises_the_rim_above_the_fan():
    p = resolved(mesh_lift=1.5)
    assert rim_z(p) == pytest.approx(RIM + 1.5)
    assert box(build_duct(p, CLEAR)).ZMax == pytest.approx(RIM + 1.5, abs=0.01)
    assert frame_z(p) == pytest.approx(frame_z(P) + 1.5)


def test_socket_wall_and_fit_are_customizable():
    d = build_duct(resolved(socket_wall=3, fan_fit=0.5, ear_length=20), CLEAR)
    assert not inside(d, 70.4, 0, 60) and inside(d, 70.6, 0, 60)
    assert inside(d, 73.4, 0, 60) and not inside(d, 73.6, 0, 60)


# ---- fan bolts and nuts


def test_fan_bolt_hole_runs_through_flange_and_into_nut_slot(duct):
    for sx, sy in CORNERS:
        for z in (SEAT - 0.2, SEAT - 3, SEAT - NUT_CEILING - 1, SEAT - NUT_CEILING - 3):
            assert not inside(duct, sx * FAN, sy * FAN, z), (sx, sy, z)


def test_nut_slot_opens_on_the_side_and_holds_the_nut_against_the_flange(duct):
    z = SEAT - NUT_CEILING - 1.5
    assert not inside(duct, OUTER - 0.1, FAN, z)  # open to the outside, so the nut slides in
    assert not inside(duct, FAN, FAN + 3.5, z)  # room for the nut's width
    assert inside(duct, FAN, FAN + 4.2, z)  # but it can't turn or wander
    assert inside(duct, FAN + 3, FAN, SEAT - NUT_CEILING + 0.3)  # solid plastic above the nut
    assert inside(duct, FAN + 3, FAN, SEAT - NUT_CEILING - 3.7)  # and below


def test_fan_bolt_tip_stays_in_the_hole(duct):
    tip_below_seat = 0.5 + fan_bolt_length(P) - P.frame_thickness - P.mesh_thickness - P.fan_thickness
    assert not inside(duct, FAN, FAN, SEAT - tip_below_seat + 0.05)


FAN_VARIANTS = [
    dict(),
    dict(fan_size=120),
    dict(fan_size=92),
    dict(fan_size=80),
    dict(fan_size=200, lid_flat_length=300, duct_height=80),
    dict(fan_size=130, fan_hole_spacing=115),
    dict(fan_thickness=38),
    dict(fan_thickness=15),
    dict(mesh_lift=2),
]


@pytest.mark.parametrize("kw", FAN_VARIANTS, ids=str)
def test_fan_variants_build_print_and_keep_the_passage_sealed(kw):
    p = resolved(**kw)
    parts = build(p, get_printer("400x400x400", load_printers()))[0]
    for part in parts:
        assert part.shape.isValid() and len(part.shape.Solids) == 1, part.name
    assert _fan_nut_cutters(p)[0].fuse(_fan_nut_cutters(p)[1:]).common(_duct_passage(p)).Volume == pytest.approx(0, abs=1e-6)
    assert parts[0].shape.common(parts[2].shape).Volume == pytest.approx(0, abs=1e-6)
    area, heights = _downward_area(to_bed(parts[0].shape, parts[0].rotation), 0)
    assert heights <= {round(p.duct_height - NUT_CEILING, 1)}, heights


def test_longer_base_than_the_fan_still_builds_with_open_nut_slots():
    p = resolved(base_length=160)
    d = build_duct(p, CLEAR)
    assert d.isValid() and len(d.Solids) == 1
    z = SEAT - NUT_CEILING - 1.5
    assert not inside(d, OUTER + 0.5, FAN, z) and not inside(d, FAN + 4, FAN, z)


def test_nut_slot_breaking_into_the_passage_is_refused():
    from projects.fanbox.params import ParamError
    with pytest.raises(ParamError, match="air passage"):
        build_duct(resolved(fan_hole_spacing=90, frame_opening=100), CLEAR)


def _downward_area(shape, zmin):
    """Facets facing down more steeply than 45° and not on the bed: (area, set of their heights)."""
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.2618)
    area, heights = 0.0, set()
    for f in mesh.Facets:
        cz = sum(p[2] for p in f.Points) / 3
        if f.Normal.z < -0.72 and cz > zmin + 0.01:
            area += f.Area
            heights.add(round(cz, 1))
    return area, heights


def test_duct_prints_without_supports(duct):
    # the only overhangs allowed are the four short bridges over the nut slots
    bed = to_bed(duct, build(P, PRINTER)[0][0].rotation)
    area, heights = _downward_area(bed, 0)
    assert area < 4 * 115
    assert heights <= {round(SEAT - NUT_CEILING, 1)}


# ---- underside plate


def test_plate_is_one_solid_below_the_lid(plate):
    assert plate.isValid() and len(plate.Solids) == 1
    bb = box(plate)
    assert bb.ZMax == pytest.approx(-P.lid_thickness, abs=0.01)
    assert bb.XLength == pytest.approx(176, abs=0.05) and bb.YLength == pytest.approx(90, abs=0.05)


def test_plate_opening_matches_the_duct(plate):
    z = -P.lid_thickness - 1
    assert not inside(plate, 66.5, 0, z) and not inside(plate, 0, 41.5, z)
    assert inside(plate, 68.5, 0, z) and inside(plate, 0, 43.5, z)


def test_plate_nut_pocket_opens_toward_the_box(plate):
    zb = box(plate).ZMin
    assert not inside(plate, LX + 3.5, LY, zb + 0.1)  # room for the nut at the open end
    assert not inside(plate, LX, LY, zb + 3.3)
    assert inside(plate, LX + 3.5, LY, -P.lid_thickness - 1)  # plastic between nut and lid
    assert not inside(plate, LX + 2.15, LY, -P.lid_thickness - 1)  # bolt passes


def test_plate_pocket_grips_the_nut_flats(plate):
    zb = box(plate).ZMin
    across = 7.2 / 2
    found = [deg for deg in range(0, 180, 5)
             if inside(plate, LX + (across + 0.25) * math.cos(math.radians(deg)),
                       LY + (across + 0.25) * math.sin(math.radians(deg)), zb + 1)]
    assert found


def test_plate_prints_without_supports(plate):
    bed = to_bed(plate, build(P, PRINTER)[0][1].rotation)
    assert _downward_area(bed, 0)[0] == pytest.approx(0, abs=0.01)


# ---- mesh frame


def test_frame_is_one_solid_covering_the_socket(frame):
    assert frame.isValid() and len(frame.Solids) == 1
    bb = box(frame)
    assert bb.ZMin == pytest.approx(frame_z(P), abs=0.01)
    assert bb.ZLength == pytest.approx(P.frame_thickness, abs=0.01)
    assert bb.XLength == pytest.approx(145.4, abs=0.05) and bb.YLength == pytest.approx(145.4, abs=0.05)


def test_frame_opening_and_rim(frame):
    z = frame_z(P) + 2
    assert not inside(frame, 65.5, 0, z) and inside(frame, 66.5, 0, z)


def test_frame_covers_the_whole_socket_rim(frame):
    # the mesh is clamped on the rim all the way round, which is what keeps flies out
    z = frame_z(P) + 1
    for x, y in ((OUTER - 1, 0), (-OUTER + 1, 0), (0, OUTER - 1), (0, -OUTER + 1), (OUTER - 1, P.cable_offset)):
        assert inside(frame, x, y, z)


def test_frame_bolt_seat_is_a_countersink_opening_upward(frame):
    top = frame_z(P) + P.frame_thickness
    assert not inside(frame, FAN + 4.1, FAN, top - 0.1)
    assert inside(frame, FAN + 3, FAN, frame_z(P) + 1)
    assert not inside(frame, FAN + 2.15, FAN, frame_z(P) + 0.1)


def test_frame_prints_without_supports(frame):
    bed = to_bed(frame, build(P, PRINTER)[0][2].rotation)
    assert _downward_area(bed, 0)[0] == pytest.approx(0, abs=0.01)


# ---- together


def test_parts_do_not_collide(duct, plate, frame):
    assert duct.common(plate).Volume == pytest.approx(0, abs=1e-6)
    assert duct.common(frame).Volume == pytest.approx(0, abs=1e-6)


def test_lid_bolt_goes_straight_through_duct_and_plate(duct, plate):
    for sx, sy in CORNERS:
        x, y = sx * LX, sy * LY
        assert not any(inside(duct, x, y, z / 2) for z in range(0, 12))
        zb = box(plate).ZMin
        assert not any(inside(plate, x, y, zb + z / 2) for z in range(0, 12))


def test_fan_bolt_goes_straight_through_frame_and_duct(duct, frame):
    for sx, sy in CORNERS:
        x, y = sx * FAN, sy * FAN
        assert not any(inside(frame, x, y, frame_z(P) + z / 2) for z in range(0, 10))
        assert not inside(duct, x, y, SEAT - 0.1)


def test_hex_key_reaches_lid_bolts_from_above(duct, frame):
    # nothing above the seat, right up past the mesh frame, within the head's radius
    for z in range(int(P.flange_thickness), 120, 2):
        for dx, dy in ((0, 0), (4.1, 0), (-4.1, 0), (0, 4.1), (0, -4.1)):
            assert not inside(duct, LX + dx, LY + dy, z + 0.1)
            assert not inside(frame, LX + dx, LY + dy, z + 0.1)


def test_bolts_are_long_enough_to_pass_through_the_nut():
    sunk = 0.5  # the head sits this far below the surface
    tip = sunk + lid_bolt_length(P)
    assert tip >= P.flange_thickness + P.lid_thickness + P.plate_ledge + P.nut_height
    tip = sunk + fan_bolt_length(P)
    assert tip >= P.frame_thickness + P.mesh_thickness + P.fan_thickness + NUT_CEILING + P.nut_height


def test_build_gives_three_parts_flat_on_the_bed():
    parts, notes = build(P, PRINTER)
    assert [p.name for p in parts] == ["duct", "lid_plate", "mesh_frame"]
    assert all(p.count == 1 for p in parts)
    assert box(to_bed(parts[1].shape, parts[1].rotation)).ZMin == pytest.approx(0, abs=0.01)
    assert notes


def test_build_resolves_auto_values_itself():
    parts, _ = build(FanboxParams(fan_size=120), PRINTER)
    assert box(parts[2].shape).XLength == pytest.approx(125.4, abs=0.05)
    assert box(parts[1].shape).XLength == pytest.approx(156, abs=0.05)


def test_lid_side_of_the_plate_is_on_the_bed():
    part = build(P, PRINTER)[0][1]
    bed = to_bed(part.shape, part.rotation)
    bb = box(bed)
    # the nut pockets face up: the solid ledge is on the bed, the pocket at the top
    cx, cy = bb.XLength / 2, bb.YLength / 2
    assert inside(bed, cx + LX + 3.5, cy + LY, 1) or inside(bed, cx + LX + 3.5, cy - LY, 1)
    assert not inside(bed, cx + LX + 3.5, cy + LY, bb.ZMax - 0.5)


def test_bed_edges_are_chamfered(duct, plate, frame):
    # elephant's foot: the very first layer is pulled in from the outline
    assert not inside(duct, EAR_TIP - 0.05, LY, 0.05) and inside(duct, EAR_TIP - 0.5, LY, 1)
    assert not inside(plate, EAR_TIP - 0.05, LY, -P.lid_thickness - 0.05)
    assert not inside(frame, OUTER - 0.05, 0, frame_z(P) + 0.05)


def test_outer_corners_are_rounded(duct, plate, frame):
    # sharp corners lift off the bed
    assert not inside(duct, EAR_TIP - 0.5, 44.5, 3)
    assert not inside(plate, EAR_TIP - 0.5, 44.5, -P.lid_thickness - 3)
    assert not inside(frame, OUTER - 0.3, OUTER - 0.3, frame_z(P) + 2)


def test_ear_joins_the_duct_with_a_fillet(duct):
    assert inside(duct, 70.3, 24.7, 3)  # the inside corner has material, it's not a sharp notch


def test_thicker_fan_lifts_the_frame():
    assert frame_z(resolved(fan_thickness=38)) == pytest.approx(frame_z(P) + 13)


def test_exported_meshes_are_clean(duct, plate, frame):
    for shape in (duct, plate, frame):
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.2618)
        assert mesh.isSolid() and not mesh.hasNonManifolds()
        assert not mesh.hasSelfIntersections()


# ---- the real hardware, modelled and put in place


def _bolt(x, y, seat_z, length, head_d=8.0):
    """A countersunk bolt pointing down, its head in a 90° seat whose wide end is at seat_z and 8.4 mm across."""
    rim = 0.3
    cone_h = (head_d - 4) / 2
    wide_z = seat_z - (8.4 - head_d) / 2  # where the seat narrows to the head's diameter
    cone = Part.makeCone(2, head_d / 2, cone_h, V(x, y, wide_z - cone_h))
    head = Part.makeCylinder(head_d / 2, rim, V(x, y, wide_z))
    top = wide_z + rim
    shaft = Part.makeCylinder(2, length - rim - cone_h, V(x, y, top - length))
    return cone.fuse([head, shaft]), top - length, top


def _nut(x, y, z0, vertex):
    return hex_prisms([(x, y)], 7.0, z0, 3.2, vertex)


def test_lid_hardware_fits(duct, plate):
    pocket_top = -P.lid_thickness - P.plate_ledge
    for sx, sy in CORNERS:
        x, y = sx * LX, sy * LY
        bolt, tip, head_top = _bolt(x, y, P.flange_thickness - 0.5, lid_bolt_length(P))
        nut = _nut(x, y, pocket_top - 3.2, "y")
        assert head_top <= P.flange_thickness  # flush or below
        assert tip <= pocket_top - 3.2  # right through the nut
        for shape, part in ((bolt, duct), (bolt, plate), (nut, plate)):
            assert shape.common(part).Volume == pytest.approx(0, abs=1e-3)


def test_fan_hardware_fits(duct, frame):
    top = frame_z(P) + P.frame_thickness
    ceiling = SEAT - NUT_CEILING
    for sx, sy in CORNERS:
        x, y = sx * FAN, sy * FAN
        bolt, tip, head_top = _bolt(x, y, top - 0.5, fan_bolt_length(P))
        nut = _nut(x, y, ceiling - 3.2, "x")
        assert head_top <= top
        assert tip <= ceiling - 3.2
        for shape, part in ((bolt, duct), (bolt, frame), (nut, duct)):
            assert shape.common(part).Volume == pytest.approx(0, abs=1e-3)


def test_nut_slides_in_from_outside_without_hitting_anything(duct):
    ceiling = SEAT - NUT_CEILING
    for sx, sy in ((1, 1), (-1, -1)):
        for d in range(0, 16, 2):
            nut = hex_prisms([(sx * (FAN + d), sy * FAN)], 7.0, ceiling - 3.2, 3.2, "x")
            assert nut.common(duct).Volume == pytest.approx(0, abs=1e-3)


def test_lid_with_its_cut_fits_between_duct_and_plate(duct, plate):
    lid = Part.makeBox(230, 95, P.lid_thickness, V(-115, -47.5, -P.lid_thickness))
    assert lid.common(duct).Volume == pytest.approx(0, abs=1e-6)
    assert lid.common(plate).Volume == pytest.approx(0, abs=1e-6)
