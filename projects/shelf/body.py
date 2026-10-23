"""The shelf body: slab, back plate and brackets as one solid, in use coordinates."""
from __future__ import annotations

import FreeCAD
import Part
from FreeCAD import Vector

from tridi.features import assert_single_solid, fuse_all, hex_prisms, rounded_slot

from . import mounting
from .layout import Layout, keyhole_extent
from .params import ShelfParams, bracket_depth, wall_offset

PRINT_ROTATION = {
    "flat": FreeCAD.Rotation(Vector(1, 0, 0), 90),  # lying on the back plate: wall face down
    "side": FreeCAD.Rotation(Vector(0, 1, 0), -90),  # on its end: every layer is a full L profile
}


def _edges(shape: Part.Shape, **at) -> list:
    """Straight edges lying entirely on the given coordinates, e.g. _edges(box, y=100, z=0)."""
    out = []
    for e in shape.Edges:
        bb = e.BoundBox
        if all(abs(getattr(bb, f"{k.upper()}Min") - v) < 1e-6 and abs(getattr(bb, f"{k.upper()}Max") - v) < 1e-6
               for k, v in at.items()):
            out.append(e)
    return out


def _slab(p: ShelfParams, lay: Layout) -> Part.Shape:
    z0, z1 = lay.slab_z
    slab = Part.makeBox(p.width, p.depth - wall_offset(p), z1 - z0, Vector(0, wall_offset(p), z0))
    r = min(p.edge_radius, 0.45 * (z1 - z0))
    if r > 0:
        slab = slab.makeFillet(r, _edges(slab, y=p.depth))
    return slab


def _plate_piece(p: ShelfParams, x0: float, x1: float, z0: float, z1: float, free_ends: list[float],
                 chamfer: bool) -> Part.Shape:
    off, t = wall_offset(p), p.plate_thickness
    piece = Part.makeBox(x1 - x0, t, z1 - z0, Vector(x0, off, z0))
    if chamfer and p.bed_chamfer > 0 and off == 0:
        piece = piece.makeChamfer(p.bed_chamfer, _edges(piece, y=0))
    r = min(p.edge_radius, 0.9 * t)
    if r > 0 and free_ends:
        piece = piece.makeFillet(r, [e for z in free_ends for e in _edges(piece, y=off + t, z=z)])
    return piece


def _plate(p: ShelfParams, lay: Layout) -> Part.Shape:
    z0, z1 = lay.plate_z
    free_ends = [z0] if p.supports == "below" else [z1]
    if p.supports == "below" and z1 > 0:
        free_ends.append(z1)  # the strip above the shelf
    if p.plate_style != "pads":
        return _plate_piece(p, 0, p.width, z0, z1, free_ends, chamfer=True)
    # pads: a mounting pad per bracket, joined by a rail along the slab
    if p.supports == "below":
        rail = (lay.slab_z[0] - 10, z1)
    else:
        rail = (z0, lay.slab_z[1] + 10)
    pieces = [_plate_piece(p, 0, p.width, *rail, [], chamfer=False)]
    pieces += [_plate_piece(p, a, b, z0, z1, free_ends, chamfer=False) for a, b in lay.pads]
    return fuse_all(pieces)


def _window_cutters(p: ShelfParams, lay: Layout) -> list[Part.Shape]:
    if not lay.windows:
        return []
    off, t, hd = wall_offset(p), p.plate_thickness, p.screw_head_d
    windows = []
    for x0, z0, x1, z1 in lay.windows:
        w = Part.makeBox(x1 - x0, t + 2, z1 - z0, Vector(x0, off - 1, z0))
        windows.append(w.makeFillet(5, [e for e in w.Edges if e.BoundBox.YLength > t]))
    keep = []
    for x, z in lay.holes:  # leave material around every hole
        if p.mount == "keyhole":
            lo, hi = keyhole_extent(p, z)
            w = hd + 8 + 6
            keep.append(Part.makeBox(w, t + 4, hi - lo + 6, Vector(x - w / 2, off - 2, lo - 3)))
        else:
            keep.append(Part.makeCylinder(hd / 2 + 5, t + 4, Vector(x, off - 2, z), Vector(0, 1, 0)))
    cutter = fuse_all(windows)
    if keep:
        cutter = cutter.cut(keep)
    return [cutter]


def _hex_cutters(p: ShelfParams, lay: Layout) -> list[Part.Shape]:
    if not lay.hexes:
        return []
    z0, z1 = lay.slab_z
    return [hex_prisms(list(lay.hexes), p.hex_cell, z0 - 1, z1 - z0 + 2, lay.hex_vertex_axis)]


def _bracket_profile(depth: float, height: float, web: float) -> Part.Shape:
    """The spike's curved bracket in (u, v): a depth × height rectangle minus an ellipse centred on its
    far corner, leaving a `web` wide strip along both edges."""
    rect = Part.makePlane(depth, height)
    c = Vector(depth, height, 0)
    a, b = depth - web, height - web
    major, minor = (c + Vector(a, 0, 0), c + Vector(0, b, 0)) if a >= b else (c + Vector(0, b, 0), c + Vector(a, 0, 0))
    ellipse = Part.Face(Part.Wire(Part.Ellipse(major, minor, c).toShape()))
    return rect.cut(ellipse)


def _brackets(p: ShelfParams, lay: Layout) -> list[Part.Shape]:
    profile = _bracket_profile(bracket_depth(p), p.bracket_height, p.bracket_web)
    solid = profile.extrude(Vector(0, 0, p.bracket_thickness))
    y0 = wall_offset(p) + p.plate_thickness
    out = []
    for c in lay.brackets:
        x0 = c - p.bracket_thickness / 2
        if p.supports == "below":  # u -> +Y, v -> down from the slab underside, extrusion -> +X
            m = FreeCAD.Matrix(0, 0, 1, x0, 1, 0, 0, y0, 0, -1, 0, lay.slab_z[0], 0, 0, 0, 1)
        else:  # v -> up from the slab top
            m = FreeCAD.Matrix(0, 0, 1, x0, 1, 0, 0, y0, 0, 1, 0, lay.slab_z[1], 0, 0, 0, 1)
        out.append(solid.transformGeometry(m))
    return out


def notch_cutters(p: ShelfParams, lay: Layout) -> list[Part.Shape]:
    z0 = lay.plate_z[0] - 10
    h = lay.plate_z[1] + p.front_lip + 10 - z0
    out = []
    for n in lay.notches:
        if n.kind == "corner":
            x = 0.0 if n.label == "back-left" else p.width
            out.append(Part.makeCylinder(n.r, h, Vector(x, 0, z0)))
        else:
            x = (n.x0 + n.x1) / 2
            end = wall_offset(p) + p.plate_thickness + p.notch_width - n.r  # round end reaches notch_width in front of the plate
            out.append(rounded_slot((x, -n.r - 1), (x, end), p.notch_width, z0, h))
    return out


def build_body(p: ShelfParams, lay: Layout) -> Part.Shape:
    plate = mounting.add(p, lay, _plate(p, lay))
    body = fuse_all([_slab(p, lay), plate, *_brackets(p, lay)])
    cutters = mounting.cutters(p, lay) + notch_cutters(p, lay) + _window_cutters(p, lay) + _hex_cutters(p, lay)
    if cutters:
        body = body.cut(cutters).removeSplitter()
    return assert_single_solid(body, "shelf")
