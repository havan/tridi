import pytest

import tridi  # noqa: F401
import Part
from FreeCAD import Vector as V

from projects.shelf.clip import CLIP_ROTATION, build_clip, clip_grip_depth, ring_axis
from projects.shelf.params import ShelfParams
from tridi.export import to_bed


def inside(shape, x, y, z):
    return shape.isInside(V(x, y, z), 1e-6, True)


def test_lip_height(build):
    body = build(front_lip=6)
    assert body.isValid() and len(body.Solids) == 1
    assert body.optimalBoundingBox().ZMax == pytest.approx(6, abs=0.01)
    assert inside(body, 100, 99, 5)
    assert not inside(body, 100, 100 - 8.5, 5)  # beyond the 45° inner face
    assert inside(body, 100, 100 - 7.5, 0.5)  # the lip's base


def test_lip_follows_rounded_corners(build):
    body = build(front_lip=6)
    assert not inside(body, 0.1, 99.9, 3)


def test_clip_gap():
    clip = build_clip(ShelfParams(), 0.2)
    g = clip_grip_depth(ShelfParams())
    # channel from z = -4 - 0.1 to z = 0.1, closed by the jaws just outside it
    assert not inside(clip, 5, g / 2, 0.1 - 0.05) and not inside(clip, 5, g / 2, -4.1 + 0.05)
    assert inside(clip, 5, g / 2, 0.1 + 0.05) and inside(clip, 5, g / 2, -4.1 - 0.05)


def test_clip_grip_depth_vs_rim():
    assert clip_grip_depth(ShelfParams(solid_rim=6)) == 4
    assert clip_grip_depth(ShelfParams()) == 6


def test_clip_cable_ring():
    p = ShelfParams()
    clip = build_clip(p, 0.2)
    assert clip.isValid() and len(clip.Solids) == 1
    (x, z), (y0, y1) = ring_axis(p, 0.2)
    cable = Part.makeCylinder(p.clip_cable_d / 2, y1 - y0 + 2, V(x, y0 - 1, z), V(0, 1, 0))
    assert clip.common(cable).Volume == pytest.approx(0, abs=1e-6)
    # the ring is closed except for its entry gap on top
    assert inside(clip, x, (y0 + y1) / 2, z - p.clip_cable_d / 2 - 0.15 - 0.8)


def test_clip_prints_on_its_spine():
    bed = to_bed(build_clip(ShelfParams(), 0.2), CLIP_ROTATION)
    bed_area = sum(f.Area for f in bed.Faces if f.BoundBox.ZMax < 1e-6)
    assert bed_area > 10 * 6
