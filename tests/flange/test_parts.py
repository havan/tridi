import pytest

import tridi  # noqa: F401
from FreeCAD import Vector as V

from projects.flange import build
from projects.flange.layout import rim_bolt_xy
from projects.flange.params import FlangeParams, effective
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
