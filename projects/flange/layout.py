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


def mesh_cells(p: FlangeParams) -> list[Point]:
    """Centres of the whole holes that fit. A cell that would cross an edge is left out, not clipped, so no
    slivers or loose fragments can form, and there's always at least a rib's width of plastic beside each hole."""
    if p.mesh not in ("grid", "honeycomb") or p.mesh_hole <= 0 or p.mesh_rib < 0:
        return []
    r, s = spine(p)
    margin = cell_circumradius(p) + p.mesh_rib
    angle = math.radians(p.mesh_angle)
    c, sn = math.cos(angle), math.sin(angle)
    hubs = hub_xy(p) if p.fixing == "centre_bolt" else []
    bars = bar_segments(p)
    keep = []
    for u, v in _lattice(p, r + s):
        x, y = u * c - v * sn, u * sn + v * c
        if spine_distance(x, y, s) + margin > r:
            continue
        if any(math.hypot(x - hx, y - hy) < p.hub_d / 2 + margin for hx, hy in hubs):
            continue
        if any(_segment_distance(x, y, seg) < p.bar_width / 2 + margin for seg in bars):
            continue
        keep.append((x, y))
    return keep


def open_area(p: FlangeParams) -> float:
    """Area left for air. Wire mesh and slicer infill aren't counted: they're estimated in the notes."""
    if p.mesh in ("grid", "honeycomb"):
        return len(mesh_cells(p)) * _cell_area(p)
    return area_after_bars(p)
