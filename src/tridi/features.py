"""Reusable geometry: hole cutters, slots, rounded rectangles, hexagons, and a solid check. Units are mm."""
from __future__ import annotations

import math

import FreeCAD
import Part
from FreeCAD import Vector


class GeometryError(RuntimeError):
    """The geometry kernel produced something that isn't one valid solid."""


def _frame(axis: Vector, up: Vector) -> FreeCAD.Matrix:
    """Matrix mapping local (x=side, y=up, z=axis) to world."""
    a = Vector(axis).normalize()
    u = Vector(up).normalize()
    s = u.cross(a)
    m = FreeCAD.Matrix()
    m.A11, m.A21, m.A31 = s.x, s.y, s.z
    m.A12, m.A22, m.A32 = u.x, u.y, u.z
    m.A13, m.A23, m.A33 = a.x, a.y, a.z
    return m


def teardrop_hole(at: Vector, axis: Vector, length: float, d: float, up: Vector) -> Part.Shape:
    """A hole that prints without supports when its axis is horizontal: a circle with a 45° point
    toward `up`, cut flat at d/2 from the centre. Starts at `at` and runs `length` along `axis`."""
    r = d / 2
    c = r * math.sqrt(0.5)
    flat = r * (math.sqrt(2) - 1)
    tip = Part.Face(Part.makePolygon([Vector(0, 0, 0), Vector(c, c, 0), Vector(flat, r, 0),
                                      Vector(-flat, r, 0), Vector(-c, c, 0), Vector(0, 0, 0)]))
    disk = Part.Face(Part.Wire(Part.makeCircle(r)))
    solid = disk.fuse(tip).removeSplitter().extrude(Vector(0, 0, length))
    solid = solid.transformGeometry(_frame(axis, up))
    solid.translate(at)
    return solid


def countersunk_hole(at: Vector, axis: Vector, depth: float, hole_d: float, head_d: float,
                     teardrop_up: Vector | None = None) -> Part.Shape:
    """Cutter for a countersunk screw. `at` lies on the face where the head sits; `axis` is that face's
    outward normal. The shaft runs from 1 mm outside the face to `depth` + 1 mm into the material."""
    a = Vector(axis).normalize()
    start = at - a * (depth + 1)
    if teardrop_up is None:
        shaft = Part.makeCylinder(hole_d / 2, depth + 2, start, a)
    else:
        shaft = teardrop_hole(start, a, depth + 2, hole_d, teardrop_up)
    sink_h = (head_d - hole_d) / 2  # 90° countersink
    sink = Part.makeCone(hole_d / 2, head_d / 2, sink_h, at - a * sink_h, a)
    head = Part.makeCylinder(head_d / 2, 1, at, a)
    return shaft.fuse([sink, head]).removeSplitter()


def rounded_slot(p0: tuple[float, float], p1: tuple[float, float], width: float, z0: float,
                 height: float) -> Part.Shape:
    """Stadium-shaped prism (semicircular ends) from p0 to p1 in XY, extruded along +Z from z0."""
    a, b = Vector(*p0, z0), Vector(*p1, z0)
    d = (b - a).normalize()
    n = Vector(-d.y, d.x, 0) * (width / 2)
    r = width / 2
    edges = [Part.LineSegment(a + n, b + n).toShape(),
             Part.Arc(b + n, b + d * r, b - n).toShape(),
             Part.LineSegment(b - n, a - n).toShape(),
             Part.Arc(a - n, a - d * r, a + n).toShape()]
    return Part.Face(Part.Wire(edges)).extrude(Vector(0, 0, height))


def rounded_rect(x0: float, y0: float, x1: float, y1: float, r: float, z0: float,
                 height: float) -> Part.Shape:
    """Rectangle with corner radius r in XY, extruded along +Z from z0."""
    box = Part.makeBox(x1 - x0, y1 - y0, height, Vector(x0, y0, z0))
    if r <= 0:
        return box
    vertical = [e for e in box.Edges if abs(e.BoundBox.ZLength - height) < 1e-9]
    return box.makeFillet(r, vertical)


def hex_prisms(centres: list[tuple[float, float]], across_flats: float, z0: float, height: float,
               vertex_axis: str) -> Part.Shape:
    """Compound of hexagonal prisms along +Z; `vertex_axis` ("x" or "y") is the axis a vertex points along."""
    R = across_flats / math.sqrt(3)
    start = 0 if vertex_axis == "x" else 90
    pts = [Vector(R * math.cos(math.radians(start + 60 * k)), R * math.sin(math.radians(start + 60 * k)), 0)
           for k in range(7)]
    prism = Part.Face(Part.makePolygon(pts)).extrude(Vector(0, 0, height))
    out = []
    for x, y in centres:
        p = prism.copy()
        p.translate(Vector(x, y, z0))
        out.append(p)
    return Part.makeCompound(out)


def fuse_all(shapes: list[Part.Shape]) -> Part.Shape:
    if len(shapes) == 1:
        return shapes[0]
    return shapes[0].fuse(shapes[1:]).removeSplitter()


def assert_single_solid(shape: Part.Shape, what: str) -> Part.Shape:
    n = len(shape.Solids)
    if not shape.isValid() or n != 1:
        problem = "an invalid shape" if not shape.isValid() else f"{n} solids"
        raise GeometryError(f"{what}: geometry kernel produced {problem}")
    return shape.Solids[0]
