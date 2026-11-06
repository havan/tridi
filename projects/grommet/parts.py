"""The grommet's solids, in assembled position: see params.py for the coordinates. The print rotation is identity for
all four, since the disc and the nut's wall face already point down."""
from __future__ import annotations

import functools
import math

import Part
from FreeCAD import Vector as V

from tridi.features import assert_single_solid, fuse_all, threaded_rod

from .params import (JOINT_FIT, JOINT_HEAD, JOINT_NECK, SLOT_HEIGHT_PLAY, GrommetParams, grip_span, joint_centre_r,
                     nut_z0, root_d, slot_height, slot_width, stem_end, thread_d, thread_start, wire_h)

MOUTH_FLARE = 1.5  # how far the slot's mouth opens, each side
MOUTH_RADIUS = 2.0  # the curve blending it into the slot
THREAD_LEAD = 1.0  # chamfer where a thread starts
SCALLOP_R = 1.0
SCALLOP_SPACING = 5.5
FLAT_CORNER = 0.5  # a flat wire's slot corners
RIB_BASE = 1.2
RIB_TIP = 0.4
KEY_LENGTH = 1.6
KEY_FIT = 0.15
BIG = 200.0
SOCKET_ROOF = 1.0
TAB_STOP_GAP = 0.05  # small, because the tab stopping against the roof is what lines the thread up
CORE_INSET = 0.2  # the plain core, under the thread's root
CORE_OVERLAP = 0.2  # how far the thread's tube reaches into the core


def _rounded_outline(half_w: float, half_h: float, r: float, z: float) -> Part.Wire:
    """A rounded rectangle centred on the axis. Its edges keep the same order at any size, so outlines can be lofted."""
    x, y = half_w - r, half_h - r
    k = r * math.sqrt(0.5)
    edges = [Part.LineSegment(V(-x, half_h, z), V(x, half_h, z)).toShape(),
             Part.Arc(V(x, half_h, z), V(x + k, y + k, z), V(half_w, y, z)).toShape()]
    if y > 1e-6:
        edges.append(Part.LineSegment(V(half_w, y, z), V(half_w, -y, z)).toShape())
    edges += [Part.Arc(V(half_w, -y, z), V(x + k, -y - k, z), V(x, -half_h, z)).toShape(),
              Part.LineSegment(V(x, -half_h, z), V(-x, -half_h, z)).toShape(),
              Part.Arc(V(-x, -half_h, z), V(-x - k, -y - k, z), V(-half_w, -y, z)).toShape()]
    if y > 1e-6:
        edges.append(Part.LineSegment(V(-half_w, -y, z), V(-half_w, y, z)).toShape())
    edges.append(Part.Arc(V(-half_w, y, z), V(-x - k, y + k, z), V(-x, half_h, z)).toShape())
    return Part.Wire(edges)


def _outline(p: GrommetParams, grow: float, z: float) -> Part.Wire:
    """The slot's section at height z, `grow` larger than the clear zone all round."""
    half_w, half_h = slot_width(p) / 2 + grow, slot_height(p) / 2 + grow
    if p.wire_shape == "round":
        return Part.Wire(Part.makeCircle(half_h, V(0, 0, z)))
    return _rounded_outline(half_w, half_h, half_h if p.wire_shape == "twin" else FLAT_CORNER + grow, z)


def _prism(p: GrommetParams, grow: float, z0: float, z1: float) -> Part.Shape:
    return Part.Face(_outline(p, grow, z0)).extrude(V(0, 0, z1 - z0))


def _mouth_grow(depth: float) -> float:
    """How far the mouth is open at a depth from its face: 45° at the face so it prints on the bed, then blending in."""
    straight = MOUTH_FLARE - MOUTH_RADIUS * (1 - math.sqrt(0.5))
    if depth <= straight:
        return MOUTH_FLARE - depth
    along = depth - straight
    return MOUTH_RADIUS - math.sqrt(max(MOUTH_RADIUS ** 2 - (MOUTH_RADIUS * math.sqrt(0.5) - along) ** 2, 0))


def _mouth_length() -> float:
    return MOUTH_FLARE - MOUTH_RADIUS * (1 - math.sqrt(0.5)) + MOUTH_RADIUS * math.sqrt(0.5)


def _mouth(p: GrommetParams, face_z: float, inward: float) -> Part.Shape:
    length = _mouth_length()
    depths = [-0.2, 0, length * 0.4, length * 0.6, length * 0.8, length]
    wires = [_outline(p, _mouth_grow(d) if d >= 0 else MOUTH_FLARE - d, face_z + inward * d) for d in depths]
    return Part.makeLoft(wires, True, False)


def _grip_band(p: GrommetParams, z0: float, z1: float) -> Part.Shape:
    """The room left for the wire across the grip zone, as a side profile extruded across its width."""
    pitch = p.grip_pitch
    samples = max(8, round((z1 - z0) / pitch * 24))
    squeeze = slot_height(p) - (wire_h(p) - p.grip_squeeze)
    upper, lower = [], []
    for i in range(samples + 1):
        z = z0 + (z1 - z0) * i / samples
        phase = 2 * math.pi * (z - z0) / pitch
        centre = -p.grip_wave * math.sin(phase)
        gap = slot_height(p) - squeeze * math.sin(phase) ** 2
        upper.append(V(0, centre + gap / 2, z))
        lower.append(V(0, centre - gap / 2, z))
    top, bottom = Part.BSplineCurve(), Part.BSplineCurve()
    top.interpolate(upper)
    bottom.interpolate(lower)
    wire = Part.Wire([top.toShape(), Part.LineSegment(upper[-1], lower[-1]).toShape(), bottom.toShape(),
                      Part.LineSegment(lower[0], upper[0]).toShape()])
    x = slot_width(p) + 2
    face = Part.Face(wire)
    face.translate(V(-x / 2, 0, 0))
    return face.extrude(V(x, 0, 0))


def _ribs(p: GrommetParams, z0: float, z1: float) -> Part.Shape:
    """Low ribs along the slot's faces, sitting in a twin wire's groove."""
    wall = slot_height(p) / 2 + 0.2
    tip = slot_height(p) / 2 - p.groove_rib
    shapes = []
    for sign in (1, -1):
        pts = [V(-RIB_BASE / 2, sign * wall, z0), V(RIB_BASE / 2, sign * wall, z0),
               V(RIB_TIP / 2, sign * tip, z0), V(-RIB_TIP / 2, sign * tip, z0)]
        shapes.append(Part.Face(Part.makePolygon([*pts, pts[0]])).extrude(V(0, 0, z1 - z0)))
    return Part.makeCompound(shapes)


def _slot(p: GrommetParams) -> Part.Shape:
    """Everything cut for the wire: clear zones, the grip zone, and a mouth at each end."""
    end = stem_end(p)
    z0, z1, _ = grip_span(p)
    dip = max(0.0, p.grip_wave - p.grip_squeeze / 2 - SLOT_HEIGHT_PLAY / 2) + 0.02
    grip = _prism(p, dip, z0, z1).common(_grip_band(p, z0, z1))
    shapes = [_prism(p, 0, -1, z0), grip, _prism(p, 0, z1, end + 1)]
    cutter = fuse_all(shapes)
    if p.wire_shape == "twin" and p.groove_rib > 0:
        length = _mouth_length()
        cutter = cutter.cut(_ribs(p, length, end - length))
    return fuse_all([cutter, _mouth(p, 0, 1), _mouth(p, end, -1)])


def _revolved(points: list[tuple[float, float]]) -> Part.Shape:
    """A solid of revolution from (radius, z) points."""
    pts = [V(r, 0, z) for r, z in points]
    return Part.Face(Part.makePolygon([*pts, pts[0]])).revolve(V(0, 0, 0), V(0, 0, 1), 360)


def _chamfered_cylinder(d: float, z0: float, z1: float, chamfer: float) -> Part.Shape:
    r = d / 2
    return _revolved([(0, z0), (r - chamfer, z0), (r, z0 + chamfer), (r, z1), (0, z1)])


def _scallops(d: float, z0: float, z1: float, avoid: tuple[float, ...]) -> Part.Shape:
    """Finger grips round an edge. There are always a multiple of 4, set half a step off the axes, and none near the
    `avoid` angles."""
    r = d / 2
    count = max(4, 4 * round(2 * math.pi * r / SCALLOP_SPACING / 4))
    step = 360 / count
    out = []
    for i in range(count):
        angle = (i + 0.5) * step
        if any(abs((angle - a + 180) % 360 - 180) < 22 for a in avoid):
            continue
        a = math.radians(angle)
        out.append(Part.makeCylinder(SCALLOP_R, z1 - z0 + 2, V(r * math.cos(a), r * math.sin(a), z0 - 1)))
    return Part.makeCompound(out)


@functools.lru_cache(maxsize=4)
def _whole_body(p: GrommetParams) -> Part.Shape:
    t = p.disc_thickness
    disc = _chamfered_cylinder(p.disc_d, 0, t, p.bed_chamfer).cut(_scallops(p.disc_d, 0, t, ()))
    end = stem_end(p)
    start = thread_start(p)
    rod = threaded_rod(root_d(p), thread_d(p), p.thread_pitch, start - 0.5, end)
    outer = thread_d(p) / 2 + 1
    rod = rod.common(_revolved([(0, start - 0.5), (outer, start - 0.5), (outer, end - THREAD_LEAD - 1),
                                (root_d(p) / 2, end), (0, end)]))
    # The slot only ever touches a plain core, since cutting it through the thread's surface is very slow.
    core_r = root_d(p) / 2 - CORE_INSET
    rod = rod.cut(Part.makeCylinder(core_r - CORE_OVERLAP, end - start + 2, V(0, 0, start - 1)))
    core = Part.makeCylinder(core_r, end - t + 0.5, V(0, 0, t - 0.5))
    shapes = [disc, core]
    if start > t:
        # A little under the thread's crest, since a surface shared with it would break the fuse.
        shapes.append(Part.makeCylinder(thread_d(p) / 2 - 0.15, start - t + 0.5, V(0, 0, t - 0.5)))
    return fuse_all(shapes).cut(_slot(p)).fuse(rod)  # no removeSplitter here: it spoils the thread's surface


def _key(p: GrommetParams, x: float, fit: float) -> Part.Shape:
    """A V along x at the disc's mid height, on the y > 0 side of the split: it holds the halves level."""
    half = min(0.7, p.disc_thickness / 2 - 0.2) + fit
    mid = p.disc_thickness / 2
    pts = [V(x - KEY_LENGTH / 2 - fit, -0.1, mid - half - 0.1), V(x - KEY_LENGTH / 2 - fit, -0.1, mid + half + 0.1),
           V(x - KEY_LENGTH / 2 - fit, half, mid)]
    return Part.Face(Part.makePolygon([*pts, pts[0]])).extrude(V(KEY_LENGTH + 2 * fit, 0, 0))


def build_body(p: GrommetParams, side: str) -> Part.Shape:
    """One half of the disc and threaded stem: `a` at y >= 0, with sockets, or `b` at y <= 0, with keys."""
    y0 = 0 if side == "a" else -BIG
    half = _whole_body(p).common(Part.makeBox(2 * BIG, BIG, 2 * BIG, V(-BIG, y0, -BIG)))
    x = (p.hole_d + p.disc_d) / 4
    if side == "a":
        half = half.cut(Part.makeCompound([_key(p, s * x, KEY_FIT) for s in (1, -1)]))
    else:
        half = half.fuse(Part.makeCompound([_key(p, x, 0), _key(p, -x, 0)]))
    return assert_single_solid(half, f"body_{side}")


def _joint(p: GrommetParams, sign: int, fit: float, z0: float, z1: float) -> Part.Shape:
    """The T on nut_a that reaches past x = 0 into nut_b, or with `fit` the socket for it."""
    y = sign * joint_centre_r(p)
    neck = JOINT_NECK / 2 + fit
    head = JOINT_HEAD / 2 + fit
    root_x = 0.1 if fit == 0 else 0.0
    step = -1.0 + fit
    tip = -2.2 - fit
    pts = [V(root_x, y - neck, z0), V(step, y - neck, z0), V(step, y - head, z0), V(tip, y - head, z0),
           V(tip, y + head, z0), V(step, y + head, z0), V(step, y + neck, z0), V(root_x, y + neck, z0)]
    return Part.Face(Part.makePolygon([*pts, pts[0]])).extrude(V(0, 0, z1 - z0))


def build_nut(p: GrommetParams, side: str) -> Part.Shape:
    """One piece of the nut: `a` at x >= 0, carrying the tabs, or `b` at x <= 0, with sockets that are open on the
    wall side and closed at the far end, so the tab starts on the bed and only the socket's short roof is bridged."""
    z0 = nut_z0(p)
    z1 = z0 + p.nut_height
    gap = p.thread_clearance
    ring = _chamfered_cylinder(p.nut_d, z0, z1, p.bed_chamfer)
    bore_r = thread_d(p) / 2 + gap
    bore = threaded_rod(root_d(p) + 2 * gap, thread_d(p) + 2 * gap, p.thread_pitch, z0 - 1, z1 + 1)
    lead = _revolved([(0, z0 - 1), (bore_r + 0.2 + 1, z0 - 1), (bore_r + 0.2, z0), (bore_r + 0.2 - THREAD_LEAD, z0 + THREAD_LEAD),
                      (0, z0 + THREAD_LEAD)])
    # Bore last and split after it: cutting the thread from an already split ring spoils its surface.
    whole = ring.cut(_scallops(p.nut_d, z0, z1, (90, 270))).cut(lead).cut(bore)
    if side == "a":
        piece = whole.common(Part.makeBox(BIG, 2 * BIG, 2 * BIG, V(0, -BIG, -BIG)))
        piece = piece.fuse(Part.makeCompound([_joint(p, s, 0, z0, z1 - SOCKET_ROOF - TAB_STOP_GAP) for s in (1, -1)]))
    else:
        piece = whole.common(Part.makeBox(BIG, 2 * BIG, 2 * BIG, V(-BIG, -BIG, -BIG)))
        sockets = [_joint(p, s, JOINT_FIT, z0 - 0.1, z1 - SOCKET_ROOF) for s in (1, -1)]
        relief = [_joint(p, s, 2 * JOINT_FIT, z0 - 0.1, z0 + 0.3) for s in (1, -1)]  # against elephant's foot
        piece = piece.cut(Part.makeCompound([*sockets, *relief]))
    return assert_single_solid(piece, f"nut_{side}")
