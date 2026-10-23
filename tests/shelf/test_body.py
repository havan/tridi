import pytest

import tridi  # noqa: F401
import Part
from FreeCAD import Vector as V

from projects.shelf.body import PRINT_ROTATION
from projects.shelf.layout import plan
from projects.shelf.params import ShelfParams, effective
from tridi.export import to_bed


def _bb(shape):
    b = shape.optimalBoundingBox()
    return b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax


def inside(shape, x, y, z):
    return shape.isInside(V(x, y, z), 1e-6, True)


def test_body_single_valid_solid(build):
    body = build()
    assert body.isValid() and len(body.Solids) == 1


def test_default_volume_matches_spike_scale(build):
    assert 100_000 < build().Volume < 160_000


def test_default_bbox(build):
    assert _bb(build()) == pytest.approx((0, 200, 0, 100, -59, 0), abs=0.01)


def test_above_bbox(build):
    b = _bb(build(supports="above"))
    assert (b[4], b[5]) == pytest.approx((-4, 55), abs=0.01)


def test_strip_bbox(build):
    assert _bb(build(top_screws="strip"))[5] == pytest.approx(18, abs=0.01)


def test_screw_holes_through(build):
    p = effective(ShelfParams())[0]
    body = build()
    for x, z in plan(p).holes:
        probe = Part.makeCylinder(0.5, 6, V(x, -1, z), V(0, 1, 0))
        assert body.common(probe).Volume == pytest.approx(0, abs=1e-6)


def test_screw_holes_countersunk(build):
    body = build()
    # just inside the plate's front face, the hole is nearly head-sized
    assert not inside(body, 77.78 + 3.9, 3.9, -14)
    # at the wall face, only the shaft is open
    assert inside(body, 77.78 + 3.9, 0.2, -14)


def test_corner_notch_clear(build):
    assert not inside(build(notches=("back-left",)), 5, 2, -10)
    assert inside(build(), 5, 2, -10)


def test_back_notch_clear(build):
    body = build(notches=("back@100",))
    assert not inside(body, 100, 2, -10)
    assert not inside(body, 100, 15, -2)  # into the slab
    assert inside(body, 100, 20, -2)  # the slot ends 14 mm in front of the plate


def test_brackets_curved(build):
    body = build()
    c = 200 / 6
    assert inside(body, c, 4 + 3, -4 - 50)  # along the plate
    assert inside(body, c, 4 + 72, -4 - 3)  # along the slab
    assert not inside(body, c, 4 + 40, -4 - 40)  # the curved cut-out


def test_front_edges_rounded(build):
    body = build()
    assert not inside(body, 100, 99.9, -0.1)
    assert inside(body, 100, 98, -2)


def test_flat_print_no_supports_proxy(build):
    bed = to_bed(build(), PRINT_ROTATION["flat"])
    assert bed.optimalBoundingBox().ZLength == pytest.approx(100, abs=0.01)
    bed_area = sum(f.Area for f in bed.Faces if f.BoundBox.ZMax < 1e-6)
    assert bed_area >= 0.9 * 200 * 59
