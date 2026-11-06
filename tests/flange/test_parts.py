import math

import pytest

import tridi  # noqa: F401
from FreeCAD import Vector as V

from projects.flange import build
from projects.flange.layout import bar_segments, rim_bolt_xy
from projects.flange.params import FlangeParams, effective, outer_height, outer_z0
from projects.flange.parts import build_inner, build_outer
from tridi.export import to_bed
from tridi.printers import get_printer, load_printers

CLEAR = 0.2
PRINTER = get_printer("mk3s", load_printers())


def resolved(**kw):
    return effective(FlangeParams(**kw))[0]


def solid_at(shape, x, y, z):
    return shape.isInside(V(x, y, z), 1e-6, False)


@pytest.fixture(scope="module")
def outer():
    return build_outer(resolved(), CLEAR)


@pytest.fixture(scope="module")
def inner():
    return build_inner(resolved(), CLEAR)


def test_outer_size_and_position(outer):
    bb = outer.BoundBox
    assert (bb.XLength, bb.YLength) == pytest.approx((78, 78), abs=0.01)
    assert (bb.ZMin, bb.ZMax) == pytest.approx((0.5, 4.5))
    assert outer.isValid()


def test_outer_grips_the_mesh_at_the_rim(outer):
    assert solid_at(outer, 21.2, 21.2, 2)
    assert not solid_at(outer, 24, 0, 2)


def test_outer_head_seats_are_flush_side_up(outer):
    for z in (1, 2.5, 4):
        assert not solid_at(outer, 0, 32, z)
    assert not solid_at(outer, 3, 32, 4)
    assert solid_at(outer, 3, 32, 1)


def test_inner_has_a_collar(inner):
    assert solid_at(inner, 25.8, 0, -1)
    assert not solid_at(inner, 27.2, 0, -1)
    assert not solid_at(inner, 24, 0, -1)
    assert (inner.BoundBox.ZMin, inner.BoundBox.ZMax) == pytest.approx((-7, -0.3))


def test_inner_has_nut_pockets_on_the_bed_side(inner):
    assert not solid_at(inner, 3, 32, -6.5)
    assert solid_at(inner, 3, 32, -3)
    assert not solid_at(inner, 0, 32, -2.5)


def test_no_collar_when_zero():
    assert build_inner(resolved(collar_height=0), CLEAR).BoundBox.ZMax == pytest.approx(-2)


def test_slot_pieces_are_single_solids_with_eight_seats():
    p = resolved(shape="slot")
    for piece in (build_outer(p, CLEAR), build_inner(p, CLEAR)):
        bb = piece.BoundBox
        assert (bb.XLength, bb.YLength) == pytest.approx((218, 49), abs=0.01)
        mid = (bb.ZMin + bb.ZMax) / 2
        for x, y in rim_bolt_xy(p):
            assert not solid_at(piece, x, y, mid)


def test_one_piece_builds_only_the_outer():
    parts, _ = build(FlangeParams(fixing="one_piece"), PRINTER)
    assert [part.name for part in parts] == ["outer"]


def test_two_piece_builds_both():
    parts, _ = build(FlangeParams(), PRINTER)
    assert [part.name for part in parts] == ["outer", "inner"]


def test_both_pieces_print_upright():
    parts, _ = build(FlangeParams(), PRINTER)
    outer_part, inner_part = parts
    on_bed = to_bed(outer_part.shape, outer_part.rotation)
    assert not on_bed.isInside(V(39 + 3, 39 + 32, 3.5), 1e-6, False)  # head seats are at the top
    assert on_bed.isInside(V(39 + 3, 39 + 32, 0.5), 1e-6, False)
    on_bed = to_bed(inner_part.shape, inner_part.rotation)
    assert not on_bed.isInside(V(39 + 3, 39 + 32, 0.5), 1e-6, False)  # pockets are on the bed
    assert on_bed.isInside(V(39 + 3, 39 + 32, 4), 1e-6, False)


def test_forced_problems_reach_the_notes():
    _, notes = build(FlangeParams(mesh="grid", mesh_rib=0.3, force=True), PRINTER)
    assert any(n.startswith("forced:") and "mesh_rib" in n for n in notes)


CENTRE = dict(fixing="centre_bolt")


@pytest.mark.parametrize("build_piece,mid_z", [(build_outer, 2.5), (build_inner, -4.5)])
def test_centre_round_has_one_bolt_through_hubs(build_piece, mid_z):
    piece = build_piece(resolved(**CENTRE), CLEAR)
    assert solid_at(piece, 5, 0, mid_z)
    assert solid_at(piece, 12, 0, mid_z)
    assert not solid_at(piece, 0, 0, mid_z)
    assert not solid_at(piece, 12, 12, mid_z)
    assert (piece.BoundBox.XLength, piece.BoundBox.YLength) == pytest.approx((66, 66), abs=0.01)
    assert solid_at(piece, 29, 0, mid_z)  # no rim bolts


def test_hub_stop_sets_the_gap():
    p = resolved(**CENTRE)
    inner_piece = build_inner(p, CLEAR)
    assert solid_at(inner_piece, 5, 0, -0.7)
    assert not solid_at(inner_piece, 5, 0, -0.3)
    assert build_outer(p, CLEAR).BoundBox.ZMin == pytest.approx(0.5)


def test_smaller_hub_stop_leaves_a_bigger_gap():
    inner_piece = build_inner(resolved(hub_stop=0.5, **CENTRE), CLEAR)
    assert not solid_at(inner_piece, 5, 0, -1.2)
    assert solid_at(inner_piece, 5, 0, -1.7)


def test_no_stop_when_zero():
    assert not solid_at(build_inner(resolved(hub_stop=0, **CENTRE), CLEAR), 5, 0, -1.9)


def test_centre_slot_has_three_hubs_with_cross_bars():
    p = resolved(shape="slot", **CENTRE)
    for piece, mid in ((build_outer(p, CLEAR), 2.5), (build_inner(p, CLEAR), -4.5)):
        assert (piece.BoundBox.XLength, piece.BoundBox.YLength) == pytest.approx((206, 37), abs=0.01)
        assert solid_at(piece, 190 / 3 + 3, 8, mid)
        assert not solid_at(piece, 95 / 3, 0, mid)
        for x in (-190 / 3, 0, 190 / 3):
            assert not solid_at(piece, x, 0, mid)
    inner_piece = build_inner(p, CLEAR)
    for x in (-190 / 3, 0, 190 / 3):
        assert not solid_at(inner_piece, x + 3, 0, -6.5)  # nut pocket
        assert solid_at(inner_piece, x + 3, 0, -3)


def test_centre_bolt_has_a_collar():
    inner_piece = build_inner(resolved(**CENTRE), CLEAR)
    assert solid_at(inner_piece, 25.8 * 0.7071, 25.8 * 0.7071, -1)
    assert not solid_at(inner_piece, 27.2 * 0.7071, 27.2 * 0.7071, -1)


@pytest.mark.parametrize("bars", [2, 3])
def test_two_and_three_bars_build(bars):
    p = resolved(bars=bars, **CENTRE)
    assert build_outer(p, CLEAR).isValid() and build_inner(p, CLEAR).isValid()


@pytest.mark.parametrize("bars", [2, 3, 4])
@pytest.mark.parametrize("mesh", ["wire", "grid"])
def test_round_bars_stay_full_width_from_hub_to_rim(bars, mesh):
    """A flat bar end set at the hub's edge leaves a wedge-shaped gap at each corner, against the hub's curve."""
    p = resolved(bars=bars, mesh=mesh, **CENTRE)
    pieces = ((build_outer(p, CLEAR), outer_z0(p) + outer_height(p) - 1),
              (build_inner(p, CLEAR), -p.wall_thickness - p.inner_thickness / 2))
    r, half = p.opening_d / 2, p.bar_width / 2 - 0.1
    joined = math.sqrt((p.hub_d / 2) ** 2 - half ** 2)  # where the hub's curve meets a line just inside the bar's edge
    for shape, z in pieces:
        for _, (x1, y1) in bar_segments(p):
            ax, ay = x1 / r, y1 / r
            for side in (-1, 1):
                for k in range(21):
                    d = joined + (r - joined) * k / 20
                    x, y = ax * d - ay * side * half, ay * d + ax * side * half
                    assert solid_at(shape, x, y, z), (bars, mesh, round(d, 2), side)


@pytest.mark.parametrize("opening_d", [155, 165, 170, 195, 225])
def test_large_round_flanges_build(opening_d):
    p = resolved(opening_d=opening_d)
    assert build_outer(p, CLEAR).isValid() and build_inner(p, CLEAR).isValid()


def test_first_layer_is_pulled_in_around_the_outline(outer, inner):
    assert not solid_at(outer, 38.9, 0, 0.55)
    assert solid_at(outer, 38.9, 0, 1.5)
    assert not solid_at(inner, 38.9, 0, -6.95)
    assert solid_at(inner, 38.9, 0, -6)


def test_no_hubs_without_a_centre_bolt(outer):
    assert not solid_at(outer, 0, 0, 2)
