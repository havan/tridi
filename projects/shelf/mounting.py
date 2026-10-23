"""How the shelf meets the wall: extra solids added to the back plate, and the cutters for its holes."""
from __future__ import annotations

import Part
from FreeCAD import Vector

from tridi.features import countersunk_hole, fuse_all, teardrop_hole

from .layout import SPACER_HEIGHT, Layout, keyhole_extent
from .params import ShelfParams, wall_offset

KEYHOLE_CHANNEL = 3.5  # depth of the pocket the screw head slides in
KEYHOLE_SKIN = 1.6  # closed front of the keyhole boss
GROOVE_W, GROOVE_D, GROOVE_PITCH = 2.0, 1.0, 6.0


def yz_prism(points: list[tuple[float, float]], x0: float, length: float) -> Part.Shape:
    """A profile given as (y, z) points, extruded along +X from x0."""
    pts = [Vector(x0, y, z) for y, z in points]
    return Part.Face(Part.makePolygon(pts + pts[:1])).extrude(Vector(length, 0, 0))


def _y_cylinder(r: float, x: float, z: float, y0: float, y1: float) -> Part.Shape:
    return Part.makeCylinder(r, y1 - y0, Vector(x, y0, z), Vector(0, 1, 0))


def _stadium_y(x: float, z0: float, z1: float, width: float, y0: float, y1: float) -> Part.Shape:
    """Vertical slot with round ends from z0 to z1, through y0..y1."""
    r = width / 2
    box = Part.makeBox(width, y1 - y0, z1 - z0, Vector(x - r, y0, z0))
    return box.fuse([_y_cylinder(r, x, z0, y0, y1), _y_cylinder(r, x, z1, y0, y1)])


def _keyhole_boss(p: ShelfParams, x: float, z: float) -> Part.Shape:
    front = wall_offset(p) + p.plate_thickness
    w = p.screw_head_d + 8
    lo, hi = keyhole_extent(p, z)
    boss = Part.makeBox(w, KEYHOLE_CHANNEL + KEYHOLE_SKIN, hi - lo, Vector(x - w / 2, front, lo))
    return boss.makeFillet(2, [e for e in boss.Edges if e.BoundBox.YLength > 1])


def _keyhole_cutter(p: ShelfParams, x: float, z: float) -> Part.Shape:
    front = wall_offset(p) + p.plate_thickness
    hd = p.screw_head_d
    entry_z = z - hd
    if p.orientation == "side":
        entry = teardrop_hole(Vector(x, -1, entry_z), Vector(0, 1, 0), front + 1 + KEYHOLE_CHANNEL,
                              hd + 1, Vector(1, 0, 0))
    else:
        entry = _y_cylinder((hd + 1) / 2, x, entry_z, -1, front + KEYHOLE_CHANNEL)
    slot = _stadium_y(x, entry_z, z, p.screw_d + 0.5, -1, front + 0.01)
    channel = _stadium_y(x, entry_z, z, hd + 1, front, front + KEYHOLE_CHANNEL)
    return entry.fuse([slot, channel])


def _hook_and_spacer(p: ShelfParams, lay: Layout) -> list[Part.Shape]:
    off, (bottom, top) = wall_offset(p), lay.plate_z
    # the hook's underside slopes down toward the wall: its tip drops behind the wall cleat's bevel
    hook = yz_prism([(0, top), (off, top), (off, top - lay.hook_height + off),
                     (0, top - lay.hook_height)], 0, p.width)
    spacer = Part.makeBox(p.width, off, SPACER_HEIGHT, Vector(0, 0, bottom))
    return [hook, spacer]


def add(p: ShelfParams, lay: Layout, plate: Part.Shape) -> Part.Shape:
    """The back plate with anything the mount adds to it."""
    if p.mount == "keyhole":
        return fuse_all([plate] + [_keyhole_boss(p, x, z) for x, z in lay.holes])
    if p.mount == "cleat":
        return fuse_all([plate] + _hook_and_spacer(p, lay))
    return plate


def _grooves(p: ShelfParams, lay: Layout) -> list[Part.Shape]:
    bottom, top = lay.plate_z
    out, z = [], bottom + 5
    while z + GROOVE_W <= top - 5:
        out.append(Part.makeBox(p.width - 10, GROOVE_D + 1, GROOVE_W, Vector(5, -1, z)))
        z += GROOVE_PITCH
    return out


def cutters(p: ShelfParams, lay: Layout) -> list[Part.Shape]:
    front = wall_offset(p) + p.plate_thickness
    if p.mount == "screws":
        up = Vector(1, 0, 0) if p.orientation == "side" else None
        return [countersunk_hole(Vector(x, front, z), Vector(0, 1, 0), p.plate_thickness, p.screw_d + 0.5,
                                 p.screw_head_d + 0.5, teardrop_up=up) for x, z in lay.holes]
    if p.mount == "keyhole":
        return [_keyhole_cutter(p, x, z) for x, z in lay.holes]
    if p.mount == "adhesive" and p.glue_grooves:
        return _grooves(p, lay)
    return []
