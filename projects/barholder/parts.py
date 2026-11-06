"""The printed parts, in use coordinates: z = 0 is the box wall's inside face, +z points into the box along the bars,
x runs along the wall and y points up, with y = 0 at the bars' centres. Builders take resolved parameters (see
`params.effective`).
"""
from __future__ import annotations

import math

import Part
from FreeCAD import Vector

from tridi.features import assert_single_solid, countersunk_hole, fuse_all, hex_prisms, rounded_rect, rounded_slot

from .params import (NUT_ROOM, NUT_SLIDE, SINK, BarholderParams, blind_hole_depth, bolt_xs, bolt_y, bore_r, cradle_xs, end_bolt_x,
                     flare_top, foot_y, hole_d, lip_angle, outer_r, rib_span, rib_top_y, strip_bottom, strip_top)

FOOT_MARGIN = 3.0  # how far a bracket's foot reaches past its ribs
FOOT_R = 2.0
EPS = 1e-6


def _x_prism(points: list[tuple[float, float]], x0: float, x1: float) -> Part.Shape:
    """A polygon of (y, z) points, extruded along x from x0 to x1."""
    wire = Part.makePolygon([Vector(x0, y, z) for y, z in [*points, points[0]]])
    return Part.Face(wire).extrude(Vector(x1 - x0, 0, 0))


def _cradle_prism(p: BarholderParams) -> Part.Shape:
    """The U seen end-on: an arc around the bar, opening into a flared mouth, extruded out from the wall. Centred on
    x = 0, and as simple as an extrusion so that its layers follow the arms when printed on its back."""
    a = math.radians(lip_angle(p))
    r, o = bore_r(p), outer_r(p)
    top_x, top_y = flare_top(p)

    def side(sign: float) -> tuple[Vector, Vector, Vector, Vector]:
        return (Vector(sign * (top_x + p.cradle_wall), top_y, 0), Vector(sign * o * math.cos(a), o * math.sin(a), 0),
                Vector(sign * r * math.cos(a), r * math.sin(a), 0), Vector(sign * top_x, top_y, 0))

    lo, lq, li, lt = side(-1)
    ro, rq, ri, rt = side(1)
    edges = [Part.LineSegment(lo, lq).toShape(),
             Part.Arc(lq, Vector(0, -o, 0), rq).toShape(),
             Part.LineSegment(rq, ro).toShape(),
             Part.LineSegment(ro, rt).toShape(),
             Part.LineSegment(rt, ri).toShape(),
             Part.Arc(ri, Vector(0, -r, 0), li).toShape(),
             Part.LineSegment(li, lt).toShape(),
             Part.LineSegment(lt, lo).toShape()]
    return Part.Face(Part.Wire(edges)).extrude(Vector(0, 0, p.cradle_depth))


def _arm_relief(p: BarholderParams) -> Part.Shape:
    """Clears the arms off the strip on a 45° slope. Rooted to the strip all along their depth, they'd be far too
    stiff to snap near the wall; the slope prints without supports."""
    top_x, top_y = flare_top(p)
    half = top_x + p.cradle_wall + 1
    y0, far = strip_top(p), top_y + 1
    t = p.strip_thickness
    return _x_prism([(y0, -1), (y0, t), (far, t + far - y0), (far, -1)], -half, half)


def _footprint(p: BarholderParams, z0: float, height: float) -> Part.Shape:
    """The outline on the wall, shared by the strip and the backplate: a strip with rounded tabs, the cradle's lower
    part where it hangs below the strip, and the brackets' feet."""
    y, end = bolt_y(p), end_bolt_x(p)
    shapes = [rounded_slot((-end, y), (end, y), p.strip_height, z0, height)]
    below = -outer_r(p) < strip_bottom(p)
    foot = foot_y(p)
    _, rib_b = rib_span(p)
    for x in cradle_xs(p):
        if below:
            disc = Part.makeCylinder(outer_r(p), height, Vector(x, 0, z0))
            keep = Part.makeBox(2 * outer_r(p) + 2, outer_r(p) + strip_top(p) + 1, height,
                                Vector(x - outer_r(p) - 1, -outer_r(p) - 1, z0))
            shapes.append(disc.common(keep))
        if p.bracket and foot < strip_bottom(p):
            half = rib_b + FOOT_MARGIN
            shapes.append(rounded_rect(x - half, foot, x + half, y, FOOT_R, z0, height))
    return fuse_all(shapes)


def _rib(p: BarholderParams, x0: float, x1: float) -> Part.Shape:
    """A triangle from the foot on the wall up to the underside of the cradle's front edge. Every layer sits inside
    the one below, so no supports. The top runs inside the cradle's wall, to fuse with it."""
    foot, tip, top = foot_y(p), -outer_r(p) - 2, rib_top_y(p)
    return _x_prism([(foot, 0), (foot, p.strip_thickness), (tip, p.cradle_depth), (top, p.cradle_depth), (top, 0)],
                    x0, x1)


def _drain(p: BarholderParams, x: float) -> Part.Shape:
    """A short gap through the floor against the stop, where drips collect: a box wall that leans outward tips the
    bar's wall end down. The ring stays closed in front of it."""
    half, floor = p.drain_width / 2, -outer_r(p) - 1
    return Part.makeBox(p.drain_width, -bore_r(p) + 0.5 - floor, p.drain_length,
                        Vector(x - half, floor, p.strip_thickness))


def _bolt_cutters(p: BarholderParams, clearance: float) -> list[Part.Shape]:
    """A hole through a ledge against the wall, and the nut's place past it. Tightening pulls the nut toward the bolt's
    head, so the ledge is what clamps the strip to the wall.

    With a slot, the nut drops in from the strip's top edge and comes to rest centred on the hole, its point in the
    slot's V. The hole stops short of the front, so no metal shows on the meat side. With a front pocket, the nut
    presses in from the meat side, a firm push fit."""
    out = []
    y, depth = bolt_y(p), blind_hole_depth(p)
    height = p.nut_height + NUT_ROOM
    for x in bolt_xs(p):
        out.append(Part.makeCylinder(hole_d(p) / 2, depth + 1, Vector(x, y, -1)))
        if p.nut_entry == "top":
            af = p.nut_af + NUT_SLIDE
            out.append(hex_prisms([(x, y)], af, p.nut_ledge, height, "y"))
            out.append(Part.makeBox(af, strip_top(p) + 1 - y, height, Vector(x - af / 2, y, p.nut_ledge)))
        else:
            out.append(hex_prisms([(x, y)], p.nut_af + clearance, p.nut_ledge,
                                  p.strip_thickness - p.nut_ledge + 1, "y"))
    return out


def _chamfer_bed(shape: Part.Shape, z: float, size: float) -> Part.Shape:
    """Pull in the part's first layer, which spreads when squashed onto the bed (elephant's foot)."""
    if size <= 0:
        return shape
    edges = [e for e in shape.Edges if abs(e.BoundBox.ZMin - z) < EPS and abs(e.BoundBox.ZMax - z) < EPS]
    return shape.makeChamfer(size, edges)


def build_strip(p: BarholderParams, clearance: float) -> Part.Shape:
    """Against the inside of the wall. The seat stops at the strip's front, so a bar can't reach the wall."""
    prism = _cradle_prism(p).cut(_arm_relief(p))
    shapes = [_footprint(p, 0, p.strip_thickness)]
    cutters = _bolt_cutters(p, clearance)
    rib_a, rib_b = rib_span(p)
    for x in cradle_xs(p):
        cradle = prism.copy()
        cradle.translate(Vector(x, 0, 0))
        shapes.append(cradle)
        if p.bracket:
            shapes += [_rib(p, x + rib_a, x + rib_b), _rib(p, x - rib_b, x - rib_a)]
        if p.drain:
            cutters.append(_drain(p, x))
    shape = fuse_all(shapes).cut(cutters).removeSplitter()
    return assert_single_solid(_chamfer_bed(shape, 0, p.bed_chamfer), "strip")


def build_plate(p: BarholderParams, clearance: float) -> Part.Shape:
    """Against the outside of the wall, with the bolt heads sunk into its outer face."""
    inner, outer = -p.box_wall, -p.box_wall - p.plate_thickness
    seats = [countersunk_hole(Vector(x, bolt_y(p), outer + SINK), Vector(0, 0, -1), p.plate_thickness - SINK, hole_d(p),
                              p.head_d + 2 * clearance) for x in bolt_xs(p)]
    shape = _footprint(p, outer, p.plate_thickness).cut(seats).removeSplitter()
    return assert_single_solid(_chamfer_bed(shape, inner, p.bed_chamfer), "backplate")
