"""Where things go on a flange, as plain numbers: no solids here, so it's quick to test.

Both shapes are stadiums, described by a radius r around a spine of half-length s along x. Round has s = 0.
Everything takes resolved parameters (see `params.effective`).
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .params import FlangeParams

Point = tuple[float, float]
Segment = tuple[Point, Point]

MIN_CLIPPED = 0.2  # a clipped hole with less of itself left than this is a sliver, and stays solid
CELL_SAMPLES = 12  # per side, when measuring how much of a clipped hole is left


def spine(p: FlangeParams) -> tuple[float, float]:
    if p.shape == "round":
        return p.opening_d / 2, 0.0
    return p.slot_width / 2, (p.slot_length - p.slot_width) / 2


def spine_distance(x: float, y: float, s: float) -> float:
    return math.hypot(max(abs(x) - s, 0.0), y)


def outer_size(p: FlangeParams) -> tuple[float, float]:
    r, s = spine(p)
    return 2 * (r + s + p.rim), 2 * (r + p.rim)


def opening_area(p: FlangeParams) -> float:
    r, s = spine(p)
    return math.pi * r * r + 4 * s * r


def rim_bolt_xy(p: FlangeParams) -> list[Point]:
    r, s = spine(p)
    rho = r + p.rim / 2
    n = p.rim_bolts
    if s == 0:
        angles = (math.radians(90 + k * 360 / n) for k in range(n))
        return [(rho * math.cos(a), rho * math.sin(a)) for a in angles]
    return [_on_stadium(k * (4 * s + 2 * math.pi * rho) / n, rho, s) for k in range(n)]


def _on_stadium(d: float, rho: float, s: float) -> Point:
    """The point d along a stadium's outline, counter-clockwise from the +x apex."""
    quarter = math.pi * rho / 2
    if d <= quarter:
        return _on_arc(s, rho, d / rho)
    d -= quarter
    if d <= 2 * s:
        return s - d, rho
    d -= 2 * s
    if d <= 2 * quarter:
        return _on_arc(-s, rho, math.pi / 2 + d / rho)
    d -= 2 * quarter
    if d <= 2 * s:
        return -s + d, -rho
    return _on_arc(s, rho, -math.pi / 2 + (d - 2 * s) / rho)


def _on_arc(cx: float, rho: float, angle: float) -> Point:
    return cx + rho * math.cos(angle), rho * math.sin(angle)


def hub_xy(p: FlangeParams) -> list[Point]:
    if p.shape == "round":
        return [(0.0, 0.0)]
    n = p.hubs
    if n < 1:  # only reachable with force
        return []
    pitch = p.slot_length / n
    return [((i + 0.5 - n / 2) * pitch, 0.0) for i in range(n)]


def bar_segments(p: FlangeParams) -> list[Segment]:
    if p.fixing != "centre_bolt":
        return []
    r, _ = spine(p)
    if p.shape == "slot":
        return [((x, -r), (x, r)) for x, _ in hub_xy(p)]
    first = 0 if p.bars == 2 else 90
    # a bar starts where the hub's curve meets its edges, not on the centre line, so its flat end is buried in the hub
    start = math.sqrt(max((p.hub_d / 2) ** 2 - (p.bar_width / 2) ** 2, 0.0))
    out = []
    for k in range(p.bars):
        a = math.radians(first + k * 360 / p.bars)
        c, sn = math.cos(a), math.sin(a)
        out.append(((start * c, start * sn), (r * c, r * sn)))
    return out


def area_after_bars(p: FlangeParams) -> float:
    area = opening_area(p)
    if p.fixing != "centre_bolt":
        return area
    r, _ = spine(p)
    hub = math.pi * p.hub_d ** 2 / 4
    if p.shape == "round":
        left = area - hub - p.bars * p.bar_width * max(r - p.hub_d / 2, 0)
    else:
        left = area - p.hubs * (hub + p.bar_width * max(2 * r - p.hub_d, 0))
    return max(left, 0.0)


def cell_circumradius(p: FlangeParams) -> float:
    return p.mesh_hole * math.sqrt(0.5) if p.mesh == "grid" else p.mesh_hole / math.sqrt(3)


def _cell_area(p: FlangeParams) -> float:
    return p.mesh_hole ** 2 if p.mesh == "grid" else p.mesh_hole ** 2 * math.sqrt(3) / 2


def _lattice(p: FlangeParams, reach: float) -> list[Point]:
    q = p.mesh_hole + p.mesh_rib
    n = int(reach / q) + 3
    if p.mesh == "grid":
        return [(i * q, j * q) for i in range(-n, n + 1) for j in range(-n, n + 1)]
    rows = int(n / (math.sqrt(3) / 2)) + 1
    return [((i + (j % 2) / 2) * q, j * q * math.sqrt(3) / 2) for i in range(-n, n + 1) for j in range(-rows, rows + 1)]


def _segment_distance(x: float, y: float, seg: Segment) -> float:
    (x0, y0), (x1, y1) = seg
    dx, dy = x1 - x0, y1 - y0
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / length2))
    return math.hypot(x - x0 - t * dx, y - y0 - t * dy)


def cell_corners(p: FlangeParams, x: float, y: float) -> list[Point]:
    """One mesh hole's corners, clockwise, with its flats square to its lattice neighbours."""
    sides, offset = (4, 45) if p.mesh == "grid" else (6, 30)
    radius = cell_circumradius(p)
    angles = [math.radians(p.mesh_angle + offset - k * 360 / sides) for k in range(sides)]
    return [(x + radius * math.cos(a), y + radius * math.sin(a)) for a in angles]


def _has_mesh_cells(p: FlangeParams) -> bool:
    return p.mesh in ("grid", "honeycomb") and p.mesh_hole > 0 and p.mesh_rib >= 0


def _lattice_points(p: FlangeParams) -> list[Point]:
    r, s = spine(p)
    angle = math.radians(p.mesh_angle)
    c, sn = math.cos(angle), math.sin(angle)
    return [(u * c - v * sn, u * sn + v * c) for u, v in _lattice(p, r + s)]


def _clear_of_web(p: FlangeParams, x: float, y: float, margin: float) -> bool:
    if p.fixing != "centre_bolt":
        return True
    return (all(math.hypot(x - hx, y - hy) >= p.hub_d / 2 + margin for hx, hy in hub_xy(p))
            and all(_segment_distance(x, y, seg) >= p.bar_width / 2 + margin for seg in bar_segments(p)))


def _clear_of_edges(p: FlangeParams, x: float, y: float, margin: float) -> bool:
    r, s = spine(p)
    return spine_distance(x, y, s) + margin <= r and _clear_of_web(p, x, y, margin)


def _whole_margin(p: FlangeParams) -> float:
    """How far a whole hole's centre stays from any edge. Running to the edge it needs no rib of its own beside the
    edge, because what's past the edge is solid."""
    return cell_circumradius(p) + (0 if p.mesh_to_edge else p.mesh_rib)


def mesh_cells(p: FlangeParams) -> list[Point]:
    """Centres of the whole holes that fit. A hole that would cross an edge isn't one of these, so no slivers or loose
    fragments can form, and there's always at least a rib's width of plastic beside each hole. `clipped_cells` has the
    ones that cross, for a mesh running to the edge."""
    if not _has_mesh_cells(p):
        return []
    margin = _whole_margin(p)
    return [(x, y) for x, y in _lattice_points(p) if _clear_of_edges(p, x, y, margin)]


def clipped_share(p: FlangeParams, x: float, y: float) -> float:
    """How much of the hole at (x, y) is left inside the opening, by sampling it: good to a few percent."""
    corners = cell_corners(p, x, y)
    pairs = list(zip(corners, corners[1:] + corners[:1]))
    x0, x1 = min(c[0] for c in corners), max(c[0] for c in corners)
    y0, y1 = min(c[1] for c in corners), max(c[1] for c in corners)
    inside = kept = 0
    for i in range(CELL_SAMPLES):
        for j in range(CELL_SAMPLES):
            px = x0 + (i + 0.5) / CELL_SAMPLES * (x1 - x0)
            py = y0 + (j + 0.5) / CELL_SAMPLES * (y1 - y0)
            if any((bx - ax) * (py - ay) - (by - ay) * (px - ax) > 0 for (ax, ay), (bx, by) in pairs):
                continue  # clockwise, so anything to the left of a side is outside the hole
            inside += 1
            kept += _clear_of_edges(p, px, py, 0)
    return kept / inside if inside else 0.0


def clipped_cells(p: FlangeParams) -> list[Point]:
    """Centres of the holes that cross an edge, for a mesh running to the edge: the kernel clips them there. Slivers are
    left out. Every piece of rib still ends in something solid, so none can come loose."""
    if not _has_mesh_cells(p) or not p.mesh_to_edge:
        return []
    r, s = spine(p)
    radius = cell_circumradius(p)
    return [(x, y) for x, y in _lattice_points(p)
            if spine_distance(x, y, s) - radius < r and not _clear_of_edges(p, x, y, radius)
            and clipped_share(p, x, y) >= MIN_CLIPPED]


def open_area(p: FlangeParams) -> float:
    """Area left for air. Wire mesh and slicer infill aren't counted: they're estimated in the notes."""
    if p.mesh in ("grid", "honeycomb"):
        whole = len(mesh_cells(p))
        return (whole + sum(clipped_share(p, x, y) for x, y in clipped_cells(p))) * _cell_area(p)
    return area_after_bars(p)
