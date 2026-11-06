"""The three printed parts, in use coordinates: z = 0 is the top of the box lid, +z points up and away from
the box, x runs along the long side of the lid's flat area and y across it. Builders take resolved parameters
(see `params.effective`).
"""
from __future__ import annotations

import math

import Part
from FreeCAD import Vector

from tridi.features import assert_single_solid, countersunk_hole, fuse_all, hex_prisms, rounded_rect

from tridi.params import ParamError

from .params import (CORNER_R, HOLE_TAIL, NUT_CEILING, NUT_ROOM, SINK, TOP_FLANGE, FanboxParams, hole_d, lid_bolt_xy,
                     plate_thickness, socket_size)

__all__ = ["NUT_CEILING", "build_duct", "build_frame", "build_plate", "frame_z", "rim_z"]

CORNERS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
EAR_R = 5.0
EAR_FILLET = 2.0  # where an ear meets the duct: an inside corner sharp enough to start a crack otherwise
EPS = 1e-6


def rim_z(p: FanboxParams) -> float:
    """Top of the socket's walls. The fan sits on its seat at duct_height."""
    return p.duct_height + p.fan_thickness + p.mesh_lift


def frame_z(p: FanboxParams) -> float:
    return rim_z(p) + p.mesh_thickness


def _socket_corner_r(p: FanboxParams) -> float:
    return p.fan_corner_r + p.socket_wall


def _rect_points(width: float, height: float, r: float, z: float) -> list[Vector]:
    """Eight points around a rounded rectangle, counter-clockwise: where its lines meet its corner arcs."""
    w, h = width / 2, height / 2
    return [Vector(*xy, z) for xy in ((w, -h + r), (w, h - r), (w - r, h), (-w + r, h),
                                      (-w, h - r), (-w, -h + r), (-w + r, -h), (w - r, -h))]


def _rect_wire(width: float, height: float, r: float, z: float) -> Part.Wire:
    w, h = width / 2, height / 2
    pts = _rect_points(width, height, r, z)
    k = r * (1 - math.sqrt(0.5))
    mids = [Vector(w - k, h - k, z), Vector(-w + k, h - k, z), Vector(-w + k, -h + k, z), Vector(w - k, -h + k, z)]
    edges = []
    for i in range(8):
        a, b = pts[i], pts[(i + 1) % 8]
        if i % 2 == 0:
            edges.append(Part.LineSegment(a, b).toShape())
        else:
            edges.append(Part.Arc(a, mids[i // 2], b).toShape())
    return Part.Wire(edges)


def _footprint(p: FanboxParams, z0: float, height: float) -> Part.Shape:
    """The outline on the lid: the base with four bolt ears. Shared by the duct's foot and the plate."""
    l, w = p.base_length / 2, p.base_width / 2
    body = rounded_rect(-l, -w, l, w, CORNER_R, z0, height)
    ears = []
    for sx, sy in CORNERS:
        inner, outer = l - 2 * CORNER_R, l + p.ear_length  # the ear starts inside the body, on the same long edge
        x0, x1 = sorted((sx * inner, sx * outer))
        y0, y1 = sorted((sy * w, sy * (w - p.ear_width)))
        ears.append(rounded_rect(x0, y0, x1, y1, EAR_R, z0, height))
    outline = fuse_all([body, *ears])
    notch_y = w - p.ear_width
    notches = [e for e in outline.Edges
               if e.BoundBox.ZLength > height - EPS and abs(abs(e.BoundBox.XMin) - l) < EPS
               and abs(abs(e.BoundBox.XMax) - l) < EPS and abs(abs(e.BoundBox.YMin) - notch_y) < EPS]
    return outline.makeFillet(EAR_FILLET, notches)


def _opening(p: FanboxParams, z0: float, height: float) -> Part.Shape:
    """The air opening through the foot and the plate, also the cut in the lid."""
    l, w = p.base_length / 2 - p.wall, p.base_width / 2 - p.wall
    return rounded_rect(-l, -w, l, w, CORNER_R - p.wall, z0, height)


def _chamfer_bed(shape: Part.Shape, z: float, size: float) -> Part.Shape:
    """Pull in the part's first layer, which spreads when squashed onto the bed (elephant's foot)."""
    if size <= 0:
        return shape
    edges = [e for e in shape.Edges
             if abs(e.BoundBox.ZMin - z) < EPS and abs(e.BoundBox.ZMax - z) < EPS]
    return shape.makeChamfer(size, edges)


def _head_seat(p: FanboxParams, x: float, y: float, face_z: float, depth: float, clearance: float) -> Part.Shape:
    return countersunk_hole(Vector(x, y, face_z - SINK), Vector(0, 0, 1), depth - SINK, hole_d(p),
                            p.head_d + 2 * clearance)


def _duct_outside(p: FanboxParams) -> Part.Shape:
    loft_top = p.duct_height - TOP_FLANGE
    size, half, r = socket_size(p), socket_size(p) / 2, _socket_corner_r(p)
    loft = Part.makeLoft([_rect_wire(p.base_length, p.base_width, CORNER_R, p.flange_thickness),
                          _rect_wire(size, size, r, loft_top)], True, True)
    top = rounded_rect(-half, -half, half, half, r, loft_top, rim_z(p) - loft_top)
    return fuse_all([_footprint(p, 0, p.flange_thickness), loft, top])


def _duct_passage(p: FanboxParams) -> Part.Shape:
    """Rounded rectangle at the lid, turning into the fan's bore. The bore is a rounded square so close to a
    circle that it makes no difference to the air (0.4 mm on the diagonal), but its edges pair up one to one
    with the rectangle's, which is what keeps the lofted surface and the exported mesh clean."""
    loft_top = p.duct_height - TOP_FLANGE
    bore_r = p.fan_bore / 2 - 1
    half = p.fan_bore / 2
    loft = Part.makeLoft([_rect_wire(p.base_length - 2 * p.wall, p.base_width - 2 * p.wall, CORNER_R - p.wall,
                                     p.flange_thickness),
                          _rect_wire(p.fan_bore, p.fan_bore, bore_r, loft_top)], True, True)
    foot = _opening(p, -1, p.flange_thickness + 1)
    bore = rounded_rect(-half, -half, half, half, bore_r, loft_top, TOP_FLANGE + 1)
    return fuse_all([foot, loft, bore])


def _socket_pocket(p: FanboxParams) -> Part.Shape:
    """The fan drops in from the top and sits on the flange around the bore."""
    half = p.fan_size / 2 + p.fan_fit
    return rounded_rect(-half, -half, half, half, p.fan_corner_r, p.duct_height, rim_z(p) - p.duct_height + 1)


def _cable_notch(p: FanboxParams) -> list[Part.Shape]:
    """A cut down from the rim through one wall of the socket, closed from above by the mesh frame."""
    if p.cable_notch_width <= 0:
        return []
    inner = p.fan_size / 2 + p.fan_fit - 0.5
    depth = p.socket_wall + 1.5  # right through the wall, from just inside it to just outside
    w = p.cable_notch_width
    z = rim_z(p) - p.cable_notch_depth
    height = p.cable_notch_depth + 1
    at = {
        "right": (inner, p.cable_offset - w / 2, depth, w),
        "left": (-inner - depth, p.cable_offset - w / 2, depth, w),
        "back": (p.cable_offset - w / 2, inner, w, depth),
        "front": (p.cable_offset - w / 2, -inner - depth, w, depth),
    }
    x, y, dx, dy = at[p.cable_side]
    return [Part.makeBox(dx, dy, height, Vector(x, y, z))]


def _fan_nut_cutters(p: FanboxParams) -> list[Part.Shape]:
    """A bolt hole and a nut slot at each corner, under the fan's seat. The slot opens on the long side so nuts
    slide in from outside, with the nut's flats against the slot's sides so it can't turn. The nut pulls up against
    the flange."""
    fan = p.fan_hole_spacing / 2
    af = p.nut_af + 0.4  # sliding fit
    ceiling = p.duct_height - NUT_CEILING
    height = p.nut_height + NUT_ROOM
    floor = ceiling - height
    tail = floor - HOLE_TAIL
    reach = max(p.base_length, socket_size(p)) / 2 + 1  # past the wall, wherever it is at the slot's height
    out = []
    for sx, sy in CORNERS:
        x, y = sx * fan, sy * fan
        out.append(Part.makeCylinder(hole_d(p) / 2, p.duct_height + 1 - tail, Vector(x, y, tail)))
        x0, x1 = sorted((x, sx * reach))
        out.append(Part.makeBox(x1 - x0, af, height, Vector(x0, y - af / 2, floor)))
        out.append(hex_prisms([(x, y)], af, floor, height, "x"))
    return out


def build_duct(p: FanboxParams, clearance: float) -> Part.Shape:
    passage = _duct_passage(p)
    nut_cutters = _fan_nut_cutters(p)
    if any(c.common(passage).Volume > EPS for c in nut_cutters):
        raise ParamError(f"fan_hole_spacing ({p.fan_hole_spacing:g}) puts the fan bolts or their nuts in the air "
                         f"passage; lower fan_bore or raise the spacing")
    x, y = lid_bolt_xy(p)
    seats = [_head_seat(p, sx * x, sy * y, p.flange_thickness, p.flange_thickness, clearance) for sx, sy in CORNERS]
    shape = _duct_outside(p).cut([passage, _socket_pocket(p)])
    shape = shape.cut(seats + nut_cutters + _cable_notch(p)).removeSplitter()
    return assert_single_solid(_chamfer_bed(shape, 0, p.bed_chamfer), "duct")


def build_plate(p: FanboxParams, clearance: float) -> Part.Shape:
    """Goes under the lid. The nuts sit in pockets that open toward the box, a firm push fit so they stay put
    while you tighten from above."""
    thick = plate_thickness(p)
    top, bottom = -p.lid_thickness, -p.lid_thickness - thick
    x, y = lid_bolt_xy(p)
    shape = _footprint(p, bottom, thick).cut(_opening(p, bottom - 1, thick + 2))
    holes = [Part.makeCylinder(hole_d(p) / 2, thick + 2, Vector(sx * x, sy * y, bottom - 1)) for sx, sy in CORNERS]
    pockets = [hex_prisms([(sx * x, sy * y)], p.nut_af + clearance, bottom - 1, p.nut_height + NUT_ROOM + 1, "y")
               for sx, sy in CORNERS]
    shape = shape.cut(holes + pockets).removeSplitter()
    return assert_single_solid(_chamfer_bed(shape, top, p.bed_chamfer), "underside plate")


def build_frame(p: FanboxParams, clearance: float) -> Part.Shape:
    """Covers the whole socket and clamps the wire mesh onto its rim, so the mesh seals all the way round.
    The mesh isn't modelled: it's cut to the socket's size."""
    half, fan = socket_size(p) / 2, p.fan_hole_spacing / 2
    z0 = frame_z(p)
    top = z0 + p.frame_thickness
    shape = rounded_rect(-half, -half, half, half, _socket_corner_r(p), z0, p.frame_thickness)
    opening = Part.makeCylinder(p.frame_opening / 2, p.frame_thickness + 2, Vector(0, 0, z0 - 1))
    seats = [_head_seat(p, sx * fan, sy * fan, top, p.frame_thickness, clearance) for sx, sy in CORNERS]
    shape = shape.cut([opening, *seats]).removeSplitter()
    return assert_single_solid(_chamfer_bed(shape, z0, p.bed_chamfer), "mesh frame")
