"""How the shelf meets the wall: extra solids added to the back plate, and the cutters for its holes."""
from __future__ import annotations

import Part
from FreeCAD import Vector

from tridi.features import countersunk_hole

from .layout import Layout
from .params import ShelfParams, wall_offset


def add(p: ShelfParams, lay: Layout, plate: Part.Shape) -> Part.Shape:
    """The back plate with anything the mount adds to it."""
    return plate


def cutters(p: ShelfParams, lay: Layout) -> list[Part.Shape]:
    front = wall_offset(p) + p.plate_thickness
    up = Vector(1, 0, 0) if p.orientation == "side" else None
    if p.mount == "screws":
        return [countersunk_hole(Vector(x, front, z), Vector(0, 1, 0), p.plate_thickness, p.screw_d + 0.5,
                                 p.screw_head_d + 0.5, teardrop_up=up) for x, z in lay.holes]
    return []
