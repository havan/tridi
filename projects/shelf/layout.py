"""Where everything goes on the shelf, and the collision checks. Pure Python: no FreeCAD here.

Use coordinates: X along the wall (0..width), Y out from the wall (wall at 0), Z up, shelf top at z=0.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .params import ShelfParams, wall_offset

MAX_BRACKET_GAP = 160.0
EDGE_MARGIN = 10.0  # holes from plate edges, window frames
SPACER_HEIGHT = 15.0  # cleat mode: spacer at the bottom of the plate


class LayoutError(ValueError):
    """The options don't fit together on a shelf of this size."""


@dataclass(frozen=True)
class Notch:
    label: str
    kind: str  # "corner" or "slot"
    x0: float
    x1: float
    r: float  # corner radius, or half the slot width


@dataclass(frozen=True)
class Layout:
    slab_z: tuple[float, float]
    plate_z: tuple[float, float]
    brackets: tuple[float, ...]
    holes: tuple[tuple[float, float], ...]
    pads: tuple[tuple[float, float], ...]
    windows: tuple[tuple[float, float, float, float], ...]
    notches: tuple[Notch, ...]
    hexes: tuple[tuple[float, float], ...]
    hex_vertex_axis: str
    hook_height: float


def keyhole_extent(p: ShelfParams, z: float) -> tuple[float, float]:
    """Vertical extent of a keyhole boss whose screw ends at height z (entry hole hd below it)."""
    hd = p.screw_head_d
    return z - 1.5 * hd - 4, z + hd / 2 + 4


def _plate_z(p: ShelfParams) -> tuple[float, float]:
    extra = p.adhesive_extra if p.mount == "adhesive" else 0.0
    if p.supports == "below":
        top = p.strip_height if (p.top_screws == "strip" and p.mount in ("screws", "keyhole")) else 0.0
        return -p.slab_thickness - p.bracket_height - extra, top
    return -p.slab_thickness, p.bracket_height + extra


def _notches(p: ShelfParams) -> list[Notch]:
    out = []
    W, w = p.width, p.notch_width
    for label in p.notches:
        if label in ("back-left", "back-right"):
            r = wall_offset(p) + p.corner_notch_r
            x0, x1 = (0.0, r) if label == "back-left" else (W - r, W)
            out.append(Notch(label, "corner", x0, x1, r))
        else:
            x = float(label.split("@")[1])
            if x - w / 2 < 0 or x + w / 2 > W:
                raise LayoutError(f"notch {label} ({x - w / 2:.1f}–{x + w / 2:.1f} mm) is outside the "
                                  f"{W:g} mm shelf")
            out.append(Notch(label, "slot", x - w / 2, x + w / 2, w / 2))
    return out


def _brackets(p: ShelfParams, notches: list[Notch]) -> list[float]:
    W, t = p.width, p.bracket_thickness
    if p.supports == "below":
        lo, hi = W / 6, 5 * W / 6
    else:
        lo, hi = t / 2, W - t / 2
        for n in notches:  # an end bracket moves inward to clear a corner notch
            if n.label == "back-left":
                lo = n.r + 2 + t / 2
            elif n.label == "back-right":
                hi = W - n.r - 2 - t / 2
    n = p.bracket_count or max(2, math.ceil((hi - lo) / MAX_BRACKET_GAP) + 1)
    xs = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    if hi - lo < (n - 1) * (t + 10):
        raise LayoutError(f"too many brackets for this width: {n} brackets in {W:g} mm")
    return xs


def _hole_rows(p: ShelfParams, plate_z: tuple[float, float]) -> list[float]:
    hd, slab_bottom = p.screw_head_d, -p.slab_thickness
    bottom, top = plate_z
    if p.mount == "keyhole":
        if p.supports == "below":
            if p.top_screws == "strip":
                z_top = top - 1 - hd / 2 - 4
                if keyhole_extent(p, z_top)[0] < 1:
                    raise LayoutError(f"keyholes need a taller strip: use --strip-height "
                                      f"{2 * hd + 10:g} or more, or --top-screws under")
            else:
                z_top = slab_bottom - hd / 2 - 6
            z_bottom = bottom + 1.5 * hd + 6
        else:
            z_top, z_bottom = top - hd / 2 - 6, 1.5 * hd + 6
        if keyhole_extent(p, z_top)[0] < keyhole_extent(p, z_bottom)[1] + 2:
            raise LayoutError("the back plate is too short for two rows of keyholes; "
                              "raise --bracket-height or use --mount screws")
        return [z_top, z_bottom]
    if p.supports == "below":
        z_top = top / 2 if top > 0 else slab_bottom - EDGE_MARGIN
        z_bottom = bottom + EDGE_MARGIN
    else:
        z_top, z_bottom = top - EDGE_MARGIN, EDGE_MARGIN
    if z_top - z_bottom < hd + 4:
        raise LayoutError("the back plate is too short for two rows of screw holes; "
                          "raise --bracket-height or use --mount cleat/adhesive")
    return [z_top, z_bottom]


def _hole_columns(p: ShelfParams, brackets: list[float]) -> list[float]:
    W, t, hd = p.width, p.bracket_thickness, p.screw_head_d
    if p.plate_style == "pads":
        return [c + (1 if c <= W / 2 else -1) * (t / 2 + hd / 2 + 4) for c in brackets]
    cols = []
    for a, b in zip(brackets, brackets[1:]):
        gap = b - a
        if gap - t - 2 * (hd / 2 + 3) <= 0:
            continue
        cols += [a + gap / 3, a + 2 * gap / 3] if gap >= 80 else [a + gap / 2]
    if len(cols) < 2:
        raise LayoutError("no room for screw holes between the brackets; widen the shelf or use "
                          "--mount cleat/adhesive")
    return cols


def _check_collisions(p: ShelfParams, notches: list[Notch], brackets: list[float],
                      holes: list[tuple[float, float]], pads: list[tuple[float, float]]) -> None:
    t, hd = p.bracket_thickness, p.screw_head_d
    keep = hd / 2 + (4 if p.mount == "keyhole" else 2)
    things = [(f"bracket {i + 1}", c - t / 2 - 1, c + t / 2 + 1) for i, c in enumerate(brackets)]
    things += [(f"screw hole at x={x:.1f}", x - keep, x + keep) for x in sorted({x for x, _ in holes})]
    things += [(f"pad {i + 1}", a, b) for i, (a, b) in enumerate(pads)]
    for i, n in enumerate(notches):
        others = things + [(f"notch {m.label}", m.x0, m.x1) for m in notches[i + 1:]]
        for name, a, b in others:
            if n.x0 < b and a < n.x1:
                raise LayoutError(f"notch {n.label} ({n.x0:.1f}–{n.x1:.1f} mm) collides with {name} "
                                  f"({a:.1f}–{b:.1f} mm)")


def _windows(p: ShelfParams, plate_z, brackets, notches, hook_height) -> list[tuple[float, float, float, float]]:
    W, t, f = p.width, p.bracket_thickness, EDGE_MARGIN
    bottom, top = plate_z
    if p.supports == "below":
        z0 = bottom + (max(f, SPACER_HEIGHT + 4) if p.mount == "cleat" else f)
        z1 = -p.slab_thickness - f
        if hook_height:
            z1 = min(z1, top - hook_height - 4)
        spans = [(0.0, brackets[0])] + list(zip(brackets, brackets[1:])) + [(brackets[-1], W)]
    else:
        z0 = f
        z1 = top - (max(f, hook_height + 4) if hook_height else f)
        spans = list(zip(brackets, brackets[1:]))
    out = []
    for a, b in spans:
        x0 = a + (t / 2 if a > 0 else 0) + f
        x1 = b - (t / 2 if b < W else 0) - f
        pieces = [(x0, x1)]
        for n in notches:  # keep a frame between windows and notches
            pieces = [piece for lo, hi in pieces
                      for piece in ((lo, min(hi, n.x0 - f)), (max(lo, n.x1 + f), hi))]
        out += [(lo, z0, hi, z1) for lo, hi in pieces if hi - lo >= 20 and z1 - z0 >= 20]
    return out


def _hexes(p: ShelfParams, brackets, notches) -> tuple[list[tuple[float, float]], str]:
    axis = "y" if p.orientation == "flat" else "x"
    af, R = p.hex_cell, p.hex_cell / math.sqrt(3)
    hx, hy = (af / 2, R) if axis == "y" else (R, af / 2)
    off, t = wall_offset(p), p.bracket_thickness
    x_lo, x_hi = p.solid_rim, p.width - p.solid_rim
    y_lo = off + p.plate_thickness + p.solid_rim
    y_hi = p.depth - p.solid_rim - (p.front_lip + 2 if p.front_lip else 0)
    pitch = af + p.hex_wall
    row = pitch * math.sqrt(3) / 2
    # rows run across the vertex axis: pitch along the flats, offset rows along the vertices
    step_x, step_y = (pitch, row) if axis == "y" else (row, pitch)
    cx, cy = (x_lo + x_hi) / 2, (y_lo + y_hi) / 2
    ni = int((x_hi - x_lo) / step_x) + 2
    nj = int((y_hi - y_lo) / step_y) + 2

    def blocked(x, y):
        if x - hx < x_lo or x + hx > x_hi or y - hy < y_lo or y + hy > y_hi:
            return True
        for c in brackets:
            if x - hx < c + t / 2 + 4 and c - t / 2 - 4 < x + hx:
                return True
        for n in notches:
            if n.kind == "corner":
                corner_x = 0.0 if n.label == "back-left" else p.width
                nx = min(max(corner_x, x - hx), x + hx)
                ny = max(0.0, y - hy)
                if math.hypot(nx - corner_x, ny) < n.r + 6:
                    return True
            elif (x - hx < n.x1 + 6 and n.x0 - 6 < x + hx
                  and y - hy < off + p.plate_thickness + p.notch_width + 6):
                return True
        return False

    out = []
    for j in range(-nj, nj + 1):
        for i in range(-ni, ni + 1):
            if axis == "y":
                x, y = cx + (i + (0.5 if j % 2 else 0)) * step_x, cy + j * step_y
            else:
                x, y = cx + i * step_x, cy + (j + (0.5 if i % 2 else 0)) * step_y
            if not blocked(x, y):
                out.append((x, y))
    return sorted(out), axis


def plan(p: ShelfParams) -> Layout:
    """Lay out a shelf. `p` must already have been through `effective`."""
    plate_z = _plate_z(p)
    hook_height = p.cleat_thickness + 6 if p.mount == "cleat" else 0.0
    notches = _notches(p)
    brackets = _brackets(p, notches)
    holes: list[tuple[float, float]] = []
    pads: list[tuple[float, float]] = []
    if p.mount in ("screws", "keyhole"):
        rows = _hole_rows(p, plate_z)
        cols = _hole_columns(p, brackets)
        holes = [(x, z) for z in rows for x in cols]
    if p.plate_style == "pads":
        t, hd = p.bracket_thickness, p.screw_head_d
        cols = _hole_columns(p, brackets)
        pads = [(min(c - t / 2 - 4, x - hd / 2 - 6), max(c + t / 2 + 4, x + hd / 2 + 6))
                for c, x in zip(brackets, cols)]
    if p.mount == "cleat":
        cleat_bottom = plate_z[1] - hook_height + p.cleat_thickness - p.cleat_height
        if cleat_bottom < plate_z[0] + SPACER_HEIGHT + 2:
            raise LayoutError("the back plate is too short for the cleat and its spacer; raise "
                              "--bracket-height or lower --cleat-height")
    _check_collisions(p, notches, brackets, holes, pads)
    windows = _windows(p, plate_z, brackets, notches, hook_height) if p.plate_style == "windowed" else []
    hexes, axis = _hexes(p, brackets, notches) if p.surface == "honeycomb" else ([], "y" if p.orientation == "flat" else "x")
    return Layout(slab_z=(-p.slab_thickness, 0.0), plate_z=plate_z, brackets=tuple(brackets), holes=tuple(holes),
                  pads=tuple(pads), windows=tuple(windows), notches=tuple(notches), hexes=tuple(hexes),
                  hex_vertex_axis=axis, hook_height=hook_height)
