"""The printed parts, in use coordinates: z = 0 is the wall's outside face, +z points out of the box, and the wall
runs down to z = -wall_thickness. The slot's long side runs along x. Builders take resolved parameters (see
`params.effective`). Both pieces print the way they're modelled, so z up is print up.
"""
from __future__ import annotations

import Part
from FreeCAD import Vector

from tridi.features import assert_single_solid, countersunk_hole, hex_prisms

from .layout import hub_xy, rim_bolt_xy, spine, spine_distance
from .params import NUT_ROOM, SINK, FlangeParams, hole_d, outer_z0

EPS = 1e-6


def stadium_wire(r: float, s: float, z: float) -> Part.Wire:
    """Counter-clockwise outline around a spine of half-length s along x. A full circle is two arcs, not one closed
    edge: a face with holes cut into it comes out invalid on a one-edge circle."""
    if s == 0:
        return Part.Wire([Part.Arc(Vector(r, 0, z), Vector(0, r, z), Vector(-r, 0, z)).toShape(),
                          Part.Arc(Vector(-r, 0, z), Vector(0, -r, z), Vector(r, 0, z)).toShape()])
    return Part.Wire([Part.LineSegment(Vector(s, r, z), Vector(-s, r, z)).toShape(),
                      Part.Arc(Vector(-s, r, z), Vector(-s - r, 0, z), Vector(-s, -r, z)).toShape(),
                      Part.LineSegment(Vector(-s, -r, z), Vector(s, -r, z)).toShape(),
                      Part.Arc(Vector(s, -r, z), Vector(s + r, 0, z), Vector(s, r, z)).toShape()])


def _ring_face(r_out: float, r_in: float, s: float, z: float) -> Part.Shape:
    return Part.makeFace([stadium_wire(r_out, s, z), stadium_wire(r_in, s, z)], "Part::FaceMakerBullseye")


def _ring(r_out: float, r_in: float, s: float, z0: float, height: float) -> Part.Shape:
    return _ring_face(r_out, r_in, s, z0).extrude(Vector(0, 0, height))


def _bolts(p: FlangeParams) -> list[tuple[float, float]]:
    return hub_xy(p) if p.fixing == "centre_bolt" else rim_bolt_xy(p)


def _chamfer(shape: Part.Shape, edges: list, size: float) -> Part.Shape:
    return shape.makeChamfer(size, edges) if size > 0 and edges else shape


def _bed_edges(shape: Part.Shape, z: float) -> list:
    return [e for e in shape.Edges if abs(e.BoundBox.ZMin - z) < EPS and abs(e.BoundBox.ZMax - z) < EPS]


def _on_outline(edge, radius: float, s: float) -> bool:
    mid = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2)
    return abs(spine_distance(mid.x, mid.y, s) - radius) < EPS


def build_outer(p: FlangeParams, clearance: float) -> Part.Shape:
    """The visible piece. Bolt heads seat flush in its outside face. It prints wall side down."""
    r, s = spine(p)
    z0 = outer_z0(p)
    top = z0 + p.outer_thickness
    shape = _ring(r + p.rim, r, s, z0, p.outer_thickness)
    seats = [countersunk_hole(Vector(x, y, top - SINK), Vector(0, 0, 1), p.outer_thickness - SINK, hole_d(p),
                              p.head_d + 2 * clearance) for x, y in _bolts(p)]
    if seats:
        shape = shape.cut(seats)
    shape = shape.removeSplitter()
    outline = [e for e in _bed_edges(shape, z0) if _on_outline(e, r + p.rim, s)]
    return assert_single_solid(_chamfer(shape, outline, p.bed_chamfer), "outer piece")


def build_inner(p: FlangeParams, clearance: float) -> Part.Shape:
    """Backs the wall from inside. Nuts press into pockets on its inside face, which prints on the bed; the collar
    faces up, into the wall hole."""
    r, s = spine(p)
    face = -p.wall_thickness
    bed = face - p.inner_thickness
    shape = _ring(r + p.rim, r, s, bed, p.inner_thickness)
    if p.collar_height > 0:
        shape = shape.fuse(_ring(r + p.collar_wall, r, s, face, p.collar_height))
    bolts = _bolts(p)
    holes = [Part.makeCylinder(hole_d(p) / 2, p.inner_thickness + 2, Vector(x, y, bed - 1)) for x, y in bolts]
    pockets = [hex_prisms([xy], p.nut_af + clearance, bed - 1, p.nut_height + NUT_ROOM + 1, "y") for xy in bolts]
    if bolts:
        shape = shape.cut(holes + pockets)
    shape = shape.removeSplitter()
    return assert_single_solid(_chamfer(shape, _bed_edges(shape, bed), p.bed_chamfer), "inner piece")
