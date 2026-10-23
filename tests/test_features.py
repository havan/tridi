import math

import pytest

import tridi  # noqa: F401
import Part
from FreeCAD import Vector as V

from tridi.features import (GeometryError, assert_single_solid, countersunk_hole, fuse_all, hex_prisms,
                            rounded_rect, rounded_slot, teardrop_hole)


def _section_diameter(shape: Part.Shape, z: float) -> float:
    """Width along X of `shape` cut by the plane at height z."""
    plane = Part.makePlane(100, 100, V(-50, -50, z))
    return shape.common(plane).BoundBox.XLength


def test_countersunk_dims():
    box = Part.makeBox(10, 10, 10)
    cutter = countersunk_hole(at=V(5, 5, 10), axis=V(0, 0, 1), depth=10, hole_d=4.5, head_d=8.5)
    removed = box.common(cutter)
    assert _section_diameter(removed, 9.99) == pytest.approx(8.5, abs=0.1)
    assert _section_diameter(removed, 5) == pytest.approx(4.5, abs=0.1)
    assert box.cut(cutter).isValid()
    # the shaft goes all the way through
    assert removed.BoundBox.ZMin == pytest.approx(0, abs=1e-6)


def test_teardrop_points_up():
    tear = teardrop_hole(at=V(0, 0, 0), axis=V(0, 1, 0), length=5, d=4, up=V(0, 0, 1))
    bb = tear.optimalBoundingBox()
    assert bb.ZMax == pytest.approx(2.0, abs=1e-6)
    assert bb.ZMin == pytest.approx(-2.0, abs=1e-6)
    assert bb.XLength == pytest.approx(4.0, abs=1e-6)
    assert tear.Volume > math.pi * 2 ** 2 * 5  # more than the plain circle


def test_countersunk_teardrop_shaft():
    plain = countersunk_hole(V(0, 0, 0), V(0, 1, 0), 10, 4.5, 8.5)
    tear = countersunk_hole(V(0, 0, 0), V(0, 1, 0), 10, 4.5, 8.5, teardrop_up=V(1, 0, 0))
    assert tear.Volume > plain.Volume


def test_rounded_slot_volume():
    slot = rounded_slot((0, 0), (10, 0), 4, 0, 1)
    assert slot.Volume == pytest.approx(10 * 4 + math.pi * 2 ** 2, abs=0.5)
    assert slot.BoundBox.XMin == pytest.approx(-2, abs=1e-6)


def test_rounded_rect():
    r = rounded_rect(0, 0, 20, 10, 2, 0, 1)
    assert r.Volume == pytest.approx(20 * 10 - (4 - math.pi) * 4, abs=0.01)


def test_hex_vertex_axis():
    hy = hex_prisms([(0, 0)], 10, 0, 1, "y")
    assert hy.BoundBox.YLength == pytest.approx(2 * 10 / math.sqrt(3), abs=1e-6)
    assert hy.BoundBox.XLength == pytest.approx(10, abs=1e-6)
    hx = hex_prisms([(0, 0)], 10, 0, 1, "x")
    assert hx.BoundBox.XLength == pytest.approx(2 * 10 / math.sqrt(3), abs=1e-6)
    assert hx.BoundBox.YLength == pytest.approx(10, abs=1e-6)


def test_fuse_all_single():
    s = fuse_all([Part.makeBox(1, 1, 1), Part.makeBox(1, 1, 1, V(1, 0, 0))])
    assert len(s.Solids) == 1 and len(s.Faces) == 6


def test_assert_single_solid():
    two = Part.makeCompound([Part.makeBox(1, 1, 1), Part.makeBox(1, 1, 1, V(5, 0, 0))])
    with pytest.raises(GeometryError, match="thing"):
        assert_single_solid(two, "thing")
    one = assert_single_solid(Part.makeBox(1, 1, 1), "thing")
    assert one.Volume == pytest.approx(1)
