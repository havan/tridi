import math

import pytest

import tridi  # noqa: F401
from FreeCAD import Vector as V

from projects.shelf.layout import plan
from projects.shelf.params import ShelfParams, effective


def single(shape):
    assert shape.isValid() and len(shape.Solids) == 1
    return shape


def test_volume_ordering(build):
    full, windowed, pads = (single(build(plate_style=s)) for s in ("full", "windowed", "pads"))
    assert pads.Volume < windowed.Volume < full.Volume
    honey = single(build(surface="honeycomb"))
    assert honey.Volume < full.Volume


def test_windows_keep_hole_rims(build):
    body = build(plate_style="windowed")
    p = effective(ShelfParams(plate_style="windowed"))[0]
    r = p.screw_head_d / 2 + 2
    for x, z in plan(p).holes:
        for k in range(8):
            a = k * math.pi / 4
            assert body.isInside(V(x + r * math.cos(a), 2, z + r * math.sin(a)), 1e-6, True)


def test_windows_open(build):
    body = build(plate_style="windowed")
    p = effective(ShelfParams(plate_style="windowed"))[0]
    x0, z0, x1, z1 = plan(p).windows[0]
    # a point in the window away from the hole keep-disks
    assert not body.isInside(V((x0 + x1) / 2, 2, (z0 + z1) / 2), 1e-6, True)


def test_pads_leave_gaps(build):
    body = build(plate_style="pads")
    assert not body.isInside(V(100, 2, -40), 1e-6, True)  # between the pads, below the rail
    assert body.isInside(V(100, 2, -8), 1e-6, True)  # the rail under the slab


def test_pads_with_keyhole(build):
    single(build(plate_style="pads", mount="keyhole"))


def test_windowed_keyhole_keeps_boss(build):
    body = single(build(plate_style="windowed", mount="keyhole"))
    p = effective(ShelfParams(plate_style="windowed", mount="keyhole"))[0]
    for x, z in plan(p).holes:
        assert body.isInside(V(x, 4 + 3.5 + 0.8, z), 1e-6, True)  # boss skin intact


def test_honeycomb_cleat_notches(build):
    single(build(surface="honeycomb", mount="cleat", notches=("back-right", "back@100")))


def test_honeycomb_holes_open(build):
    p = effective(ShelfParams(surface="honeycomb"))[0]
    body = build(surface="honeycomb")
    x, y = plan(p).hexes[len(plan(p).hexes) // 2]
    assert not body.isInside(V(x, y, -2), 1e-6, True)
