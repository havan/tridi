"""Cable-tip clip: pushes onto an edge of the shelf and holds a cable just behind its plug.

Local coordinates: x along the edge (0..CLIP_WIDTH), y = 0 at the shelf's edge face with +y into the
shelf, and the slab occupying z = -slab_thickness..0, as in use coordinates.
"""
from __future__ import annotations

import FreeCAD
import Part
from FreeCAD import Vector

from tridi.features import assert_single_solid, fuse_all

from .params import ShelfParams

CLIP_WIDTH = 10.0
WALL = 1.6
CLIP_ROTATION = FreeCAD.Rotation(Vector(1, 0, 0), 90)  # spine on the bed, jaws and ring standing up


def clip_grip_depth(p: ShelfParams) -> float:
    """How far the jaws reach onto the shelf: less than the solid rim, so never over a honeycomb hole."""
    return min(6.0, p.solid_rim - 2)


def _ring(p: ShelfParams, clearance: float) -> tuple[float, float, float]:
    """(z of the ring axis, inner radius, outer radius)."""
    r_in = (p.clip_cable_d + 0.3) / 2
    r_out = r_in + WALL
    jaw_top = clearance / 2 + WALL
    return jaw_top + r_out - WALL / 2, r_in, r_out


def ring_axis(p: ShelfParams, clearance: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """((x, z) of the cable ring's axis, (y0, y1) of its length)."""
    z, _, _ = _ring(p, clearance)
    return (CLIP_WIDTH / 2, z), (-WALL, clip_grip_depth(p))


def build_clip(p: ShelfParams, clearance: float) -> Part.Shape:
    g, t, c = clip_grip_depth(p), p.slab_thickness, clearance
    lo, hi = -t - c / 2, c / 2  # the channel the slab slides into
    spine = Part.makeBox(CLIP_WIDTH, WALL, hi - lo + 2 * WALL, Vector(0, -WALL, lo - WALL))
    top = Part.makeBox(CLIP_WIDTH, g + WALL, WALL, Vector(0, -WALL, hi))
    bottom = Part.makeBox(CLIP_WIDTH, g + WALL, WALL, Vector(0, -WALL, lo - WALL))
    z, r_in, r_out = _ring(p, c)
    (x, _), (y0, y1) = ring_axis(p, c)
    ring = Part.makeCylinder(r_out, y1 - y0, Vector(x, y0, z), Vector(0, 1, 0))
    body = fuse_all([spine, top, bottom, ring])
    bore = Part.makeCylinder(r_in, y1 - y0 + 2, Vector(x, y0 - 1, z), Vector(0, 1, 0))
    gap = 0.75 * p.clip_cable_d  # the cable snaps in through a slit on top
    slit = Part.makeBox(gap, y1 - y0 + 2, r_out + 1, Vector(x - gap / 2, y0 - 1, z))
    return assert_single_solid(body.cut([bore, slit]).removeSplitter(), "clip")
