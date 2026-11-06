"""The printed parts, in use coordinates: z = 0 is the box wall's inside face, +z points out of the wall into the box,
x runs along the wall and y points up the wall, with y = 0 at the bars' centres at the strip's front. On a
leaning wall these axes lean with it, and the bars run level, slightly down in y as z grows. Builders take resolved
parameters (see `params.effective`).
"""
from __future__ import annotations

import math

import Part
from FreeCAD import Vector

from tridi.features import assert_single_solid, countersunk_hole, fuse_all, hex_prisms, rounded_rect, rounded_slot

from .params import (NUT_ROOM, NUT_SLIDE, SINK, BarholderParams, blind_hole_depth, bolt_xs, bolt_y, bore_r, cradle_xs, end_bolt_x,
                     flare_top, foot_y, hole_d, lip_angle, outer_r, rib_span, rib_tip_y, rib_top_y, strip_bottom, strip_top, tilt_drop)

FOOT_MARGIN = 3.0  # how far a bracket's foot reaches past its ribs
FOOT_R = 2.0
EPS = 1e-6


def _x_prism(points: list[tuple[float, float]], x0: float, x1: float) -> Part.Shape:
    """A polygon of (y, z) points, extruded along x from x0 to x1."""
    wire = Part.makePolygon([Vector(x0, y, z) for y, z in [*points, points[0]]])
    return Part.Face(wire).extrude(Vector(x1 - x0, 0, 0))


def _cradle_prism(p: BarholderParams) -> Part.Shape:
    """The U seen end-on: an arc around the bar, opening into a flared mouth, extruded out from the wall. Centred on
    x = 0, and as simple as an extrusion so that its layers follow the arms when printed on its back.

    On a leaning wall the wall's normal points up into the box, so the extrusion tilts down by the same angle to keep
    the bar level. It pivots at the strip's front, and is trimmed flat for the bed and at the front."""
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
    # Whatever stands on the strip starts above its bed chamfer, so as not to fill it. Only straight arms reach the bed.
    z0 = p.bed_chamfer if p.arm_slope > 0 else 0
    face = Part.Face(Part.Wire(edges))
    if p.wall_angle == 0:
        prism = face.extrude(Vector(0, 0, p.cradle_depth - z0))
        prism.translate(Vector(0, 0, z0))
        return prism
    prism = face.extrude(Vector(0, 0, 3 * p.cradle_depth))
    prism.translate(Vector(0, 0, -p.cradle_depth))
    prism.rotate(Vector(0, 0, p.strip_thickness), Vector(1, 0, 0), p.wall_angle)
    reach = 2 * (top_x + p.cradle_wall + o + p.cradle_depth)
    return prism.common(Part.makeBox(2 * reach, 2 * reach, p.cradle_depth - z0, Vector(-reach, -reach, z0)))


def _seat_cutters(p: BarholderParams) -> list[Part.Shape]:
    """The seat, carried on through the strip to the wall. Past the strip's front a cutter is only ever in the seat's
    open space, so it runs right through: a tilted end there would leave a wedge of strip under the bar.

    Each has a cone at the bed to chamfer the seat's edge, upright as the bed is flat. It runs on past the edge at both
    ends, so that it meets the tilted seat at a clean angle all the way round."""
    r, c = bore_r(p), p.bed_chamfer
    centre_y = -tilt_drop(p, 0)
    out = []
    for x in cradle_xs(p):
        seat = Part.makeCylinder(r, 3 * p.cradle_depth, Vector(x, 0, -p.cradle_depth))
        seat.rotate(Vector(x, 0, p.strip_thickness), Vector(1, 0, 0), p.wall_angle)
        out.append(seat)
        if c > 0:
            out.append(Part.makeCone(r + c + 1, r - 1, c + 2, Vector(x, centre_y, -1)))
    return out


def _arm_relief(p: BarholderParams) -> Part.Shape:
    """Clears the arms off the strip on a slope, starting at the strip's front edge. Rooted to the strip all along their
    depth, they'd be far too stiff to snap near the wall. Steeper prints more easily, but leaves less of the lip."""
    top_x, top_y = flare_top(p)
    half = top_x + p.cradle_wall + 1
    t = p.strip_thickness
    y0, far = strip_top(p), top_y + 1 - tilt_drop(p, 0)  # a tilted arm stands a little higher at the wall
    rise = (far - y0) * math.tan(math.radians(p.arm_slope))
    return _x_prism([(y0, -1), (y0, t), (far, t + rise), (far, -1)], -half, half)


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
    foot, top = foot_y(p), rib_top_y(p)
    z0, depth = p.bed_chamfer, p.cradle_depth
    return _x_prism([(foot, z0), (foot, p.strip_thickness), (rib_tip_y(p), depth), (top - tilt_drop(p, depth), depth),
                     (top - tilt_drop(p, z0), z0)], x0, x1)


def _drain(p: BarholderParams, x: float) -> Part.Shape:
    """A short gap through the floor just past the strip's front, where drips running along the bar fall through. The
    ring stays closed in front of it."""
    half, floor = p.drain_width / 2, -outer_r(p) - 1 - tilt_drop(p, p.strip_thickness + p.drain_length)
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
    """Against the inside of the wall.

    The bed chamfer goes on before the cradles join: with no arm slope the arms meet the strip's edge at angles too
    sharp to chamfer. The seat is only cut once they have, because a chamfer's edge on a tilted seat would land almost
    on the cradle's flat base, and leave a seam that a valid shape can still mesh open."""
    body = _footprint(p, 0, p.strip_thickness).cut(_bolt_cutters(p, clearance)).removeSplitter()
    shapes = [_chamfer_bed(body, 0, p.bed_chamfer)]
    prism = _cradle_prism(p)
    if p.arm_slope > 0:
        prism = prism.cut(_arm_relief(p))
    cutters = _seat_cutters(p) if p.through_cut else []
    rib_a, rib_b = rib_span(p)
    for x in cradle_xs(p):
        cradle = prism.copy()
        cradle.translate(Vector(x, 0, 0))
        shapes.append(cradle)
        if p.bracket:
            shapes += [_rib(p, x + rib_a, x + rib_b), _rib(p, x - rib_b, x - rib_a)]
        if p.drain:
            cutters.append(_drain(p, x))
    shape = fuse_all(shapes)
    if cutters:
        shape = shape.cut(cutters).removeSplitter()
    return assert_single_solid(shape, "strip")


def build_plate(p: BarholderParams, clearance: float) -> Part.Shape:
    """Against the outside of the wall, with the bolt heads sunk into its outer face."""
    inner, outer = -p.box_wall, -p.box_wall - p.plate_thickness
    seats = [countersunk_hole(Vector(x, bolt_y(p), outer + SINK), Vector(0, 0, -1), p.plate_thickness - SINK, hole_d(p),
                              p.head_d + 2 * clearance) for x in bolt_xs(p)]
    shape = _footprint(p, outer, p.plate_thickness).cut(seats).removeSplitter()
    return assert_single_solid(_chamfer_bed(shape, inner, p.bed_chamfer), "backplate")
