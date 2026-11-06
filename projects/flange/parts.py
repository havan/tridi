"""The printed parts, in use coordinates: z = 0 is the wall's outside face, +z points out of the box, and the wall
runs down to z = -wall_thickness. The slot's long side runs along x. Builders take resolved parameters (see
`params.effective`). Both pieces print the way they're modelled, so z up is print up.
"""
from __future__ import annotations

import math

import Part
from FreeCAD import Vector

from tridi.features import GeometryError, assert_single_solid, countersunk_hole, hex_prisms

from .layout import bar_segments, cell_corners, clipped_cells, hub_xy, mesh_cells, rim_bolt_xy, spine, spine_distance
from .params import NUT_ROOM, SINK, FlangeParams, hole_d, outer_height, outer_z0

EPS = 1e-6


def stadium_wire(r: float, s: float, z: float) -> Part.Wire:
    """Counter-clockwise outline around a spine of half-length s along x. A full circle is two arcs, not one closed
    edge: a face with holes cut into it comes out invalid on a one-edge circle."""
    if r <= 0:
        raise GeometryError(f"an outline of radius {r:g} mm has nothing to print")
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


def _hubs_and_bars(p: FlangeParams, z0: float, height: float) -> list[Part.Shape]:
    """The centre-bolt web. Bars run 0.5 mm into the rim and hub, so the fuse doesn't rest on touching faces."""
    if p.fixing != "centre_bolt":
        return []
    shapes = [Part.makeCylinder(p.hub_d / 2, height, Vector(x, y, z0)) for x, y in hub_xy(p)]
    for (x0, y0), (x1, y1) in bar_segments(p):
        along = Vector(x1 - x0, y1 - y0, 0)
        if along.Length < EPS:  # a hub as wide as the opening leaves no bar to draw
            continue
        along.normalize()
        side = Vector(-along.y, along.x, 0) * (p.bar_width / 2)
        start = Vector(x0, y0, z0) - along * 0.5
        end = Vector(x1, y1, z0) + along * 0.5
        outline = Part.makePolygon([start + side, end + side, end - side, start - side, start + side])
        shapes.append(Part.Face(outline).extrude(Vector(0, 0, height)))
    return shapes


def _bolts(p: FlangeParams) -> list[tuple[float, float]]:
    return hub_xy(p) if p.fixing == "centre_bolt" else rim_bolt_xy(p)


def _chamfer(shape: Part.Shape, edges: list, size: float) -> Part.Shape:
    return shape.makeChamfer(size, edges) if size > 0 and edges else shape


def _bed_edges(shape: Part.Shape, z: float) -> list:
    return [e for e in shape.Edges if abs(e.BoundBox.ZMin - z) < EPS and abs(e.BoundBox.ZMax - z) < EPS]


def _chamfer_outline(shape: Part.Shape, z: float, radius: float, s: float, size: float, height: float) -> Part.Shape:
    """Pull in the first layer around the outside. Done on the first layer alone, before anything else joins it: the
    kernel can't chamfer a round outline after removeSplitter at some sizes, and can't chamfer one beside the seams a
    fuse leaves either. Never takes the whole layer, however thin it is."""
    edges = [e for e in _bed_edges(shape, z) if _on_outline(e, radius, s)]
    return _chamfer(shape, edges, min(size, height / 2))


def _on_outline(edge, radius: float, s: float) -> bool:
    mid = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2)
    return abs(spine_distance(mid.x, mid.y, s) - radius) < EPS


def _near(edge, centre: tuple[float, float], reach: float) -> bool:
    mid = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2)
    return math.hypot(mid.x - centre[0], mid.y - centre[1]) <= reach


def _cell_wire(p: FlangeParams, x: float, y: float, z: float) -> Part.Wire:
    """One mesh hole, clockwise: `cutHoles` only cuts wires wound against the face's outline."""
    corners = cell_corners(p, x, y)
    return Part.makePolygon([Vector(cx, cy, z) for cx, cy in [*corners, corners[0]]])


def _mesh_layer(p: FlangeParams, z0: float, height: float) -> Part.Shape:
    """The part's whole footprint with the holes in it, or solid for the slicer. Faces with holes are far quicker than
    a boolean cut per hole."""
    r, s = spine(p)
    face = Part.Face(stadium_wire(r + p.rim, s, z0))
    cells = mesh_cells(p)
    if cells:
        face.cutHoles([_cell_wire(p, x, y, z0) for x, y in cells])
    return face.extrude(Vector(0, 0, height))


def _opening(p: FlangeParams, z0: float, height: float) -> Part.Shape:
    """The opening as a solid, less any bars and hubs."""
    r, s = spine(p)
    zone = Part.Face(stadium_wire(r, s, z0)).extrude(Vector(0, 0, height))
    web = _hubs_and_bars(p, z0, height)
    return zone.cut(web).removeSplitter() if web else zone


def _clipped_holes(p: FlangeParams, z0: float, height: float) -> list[Part.Shape]:
    """The holes crossing an edge, trimmed to it. They run clear through the piece's height, as there's only air over
    the mesh, so that they don't end on the layer's own faces."""
    cells = clipped_cells(p)
    if not cells:
        return []
    room = _opening(p, z0 - 1, height + 2)
    holes = [Part.Face(_cell_wire(p, x, y, z0 - 1)).extrude(Vector(0, 0, height + 2)).common(room) for x, y in cells]
    return [hole for hole in holes if hole.Volume > EPS]


def build_outer(p: FlangeParams, clearance: float) -> Part.Shape:
    """The visible piece. Bolt heads seat flush in its outside face. It prints wall side down, so a printed mesh lies
    flat on the bed, with the rest of the piece standing as a frame around it."""
    r, s = spine(p)
    z0 = outer_z0(p)
    layer = 0 if p.mesh == "wire" else p.mesh_thickness
    thick = outer_height(p)
    top = z0 + thick
    pieces = []
    if layer > 0:
        pieces.append(_chamfer_outline(_mesh_layer(p, z0, layer), z0, r + p.rim, s, p.bed_chamfer, layer))
    if thick > layer and layer <= 0:
        pieces += [_chamfer_outline(_ring(r + p.rim, r, s, z0, thick), z0, r + p.rim, s, p.bed_chamfer, thick),
                   *_hubs_and_bars(p, z0, thick)]
    elif thick > layer:
        pieces += [_ring(r + p.rim, r, s, z0 + layer, thick - layer), *_hubs_and_bars(p, z0 + layer, thick - layer)]
    if not pieces:
        raise GeometryError(f"outer piece: outer_thickness ({p.outer_thickness:g}) leaves nothing to print")
    shape = pieces[0].fuse(pieces[1:]) if len(pieces) > 1 else pieces[0]
    seats = [countersunk_hole(Vector(x, y, top - SINK), Vector(0, 0, 1), thick - SINK, hole_d(p),
                              p.head_d + 2 * clearance) for x, y in _bolts(p)]
    cutters = seats + _clipped_holes(p, z0, thick)
    if cutters:
        shape = shape.cut(cutters)
    return assert_single_solid(shape.removeSplitter(), "outer piece")


def build_mesh_zone(p: FlangeParams) -> Part.Shape:
    """Where the slicer should replace the solid with infill: the opening, less any bars and hubs. Load it as a
    modifier. It stays one shape with several regions when bars divide the opening."""
    zone = _opening(p, outer_z0(p), p.mesh_thickness)
    if not zone.Solids:
        raise GeometryError("mesh zone: the hubs and bars fill the opening")
    return zone


def build_inner(p: FlangeParams, clearance: float) -> Part.Shape:
    """Backs the wall from inside. Nuts press into pockets on its inside face, which prints on the bed; the collar
    faces up, into the wall hole."""
    r, s = spine(p)
    face = -p.wall_thickness
    bed = face - p.inner_thickness
    shape = _chamfer_outline(_ring(r + p.rim, r, s, bed, p.inner_thickness), bed, r + p.rim, s, p.bed_chamfer,
                             p.inner_thickness)
    extras = _hubs_and_bars(p, bed, p.inner_thickness)
    if p.collar_height > 0:
        extras.append(_ring(r + p.collar_wall, r, s, face, p.collar_height))
    if p.hub_stop > 0:
        extras += [Part.makeCylinder(p.hub_d / 2, p.hub_stop, Vector(x, y, face)) for x, y in hub_xy(p)]
    if extras:
        shape = shape.fuse(extras)
    bolts = _bolts(p)
    holes = [Part.makeCylinder(hole_d(p) / 2, p.inner_thickness + p.hub_stop + 2, Vector(x, y, bed - 1))
             for x, y in bolts]
    pockets = [hex_prisms([xy], p.nut_af + clearance, bed - 1, p.nut_height + NUT_ROOM + 1, "y") for xy in bolts]
    if bolts:
        shape = shape.cut(holes + pockets)
    shape = shape.removeSplitter()
    # the nut pockets, where a spread first layer would stop a nut going in. Not the air openings: their corners against
    # the bars are too tight for the kernel to chamfer, and nothing fits there anyway.
    reach = (p.nut_af + clearance) / 2 / math.cos(math.pi / 6) + EPS
    edges = [e for e in _bed_edges(shape, bed) if any(_near(e, xy, reach) for xy in bolts)]
    return assert_single_solid(_chamfer(shape, edges, p.bed_chamfer), "inner piece")
