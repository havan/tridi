"""The French cleat: a beveled strip screwed to the wall first; the shelf's hook drops onto it."""
from __future__ import annotations

import math

import Part
from FreeCAD import Vector

from tridi.features import GeometryError, countersunk_hole

from .body import notch_cutters
from .layout import Layout, LayoutError
from .mounting import yz_prism
from .params import ShelfParams

GAP = 0.2  # between cleat and shelf, perpendicular to the bevel and at the front face
END_INSET = 10.0  # cleat ends in from the shelf ends
HOLE_INSET = 20.0  # first and last hole from the cleat ends
MAX_HOLE_SPACING = 120.0


def _profile(p: ShelfParams, lay: Layout) -> tuple[list[tuple[float, float]], float, float]:
    """(y, z) outline, z of the bottom and z of the top of the rectangular part."""
    top, t = lay.plate_z[1], p.cleat_thickness - GAP
    drop = GAP * math.sqrt(2)  # vertical offset for a perpendicular gap on a 45° bevel

    def bevel(y):  # z of the hook's underside at y, lowered by the gap
        return top - lay.hook_height + (p.cleat_thickness - y) - drop

    z_bottom = bevel(0) - p.cleat_height
    return [(0, z_bottom), (t, z_bottom), (t, bevel(t)), (0, bevel(0))], z_bottom, bevel(t)


def cleat_pieces(p: ShelfParams, lay: Layout) -> list[tuple[float, float]]:
    """x spans of the cleat: cable notches cut it, so a back notch splits it in two."""
    pieces = [(END_INSET, p.width - END_INSET)]
    for n in lay.notches:
        pieces = [piece for lo, hi in pieces for piece in ((lo, min(hi, n.x0)), (max(lo, n.x1), hi))
                  if piece[1] > piece[0]]
    return pieces


def cleat_holes(p: ShelfParams, lay: Layout) -> list[float]:
    """x of each screw hole: per cleat piece, evenly spaced, 20 mm in from its ends."""
    keep = (p.screw_head_d + 0.5) / 2 + 2
    out = []
    for a, b in cleat_pieces(p, lay):
        lo, hi = a + max(HOLE_INSET, keep), b - max(HOLE_INSET, keep)
        if hi - lo >= p.screw_head_d + 4:
            n = max(2, math.ceil((hi - lo) / MAX_HOLE_SPACING) + 1)
            out += [lo + (hi - lo) * i / (n - 1) for i in range(n)]
        elif b - a >= 2 * keep:
            out.append((a + b) / 2)
        else:
            raise LayoutError(f"a cable notch leaves a {b - a:.1f} mm piece of cleat, too short for a screw; "
                              "move the notch")
    return out


def build_cleat(p: ShelfParams, lay: Layout) -> Part.Shape:
    """The wall cleat in use coordinates: a compound of its pieces, each a single solid."""
    outline, z_bottom, z_rect_top = _profile(p, lay)
    cleat = yz_prism(outline, END_INSET, p.width - 2 * END_INSET)
    z_hole = (z_bottom + z_rect_top) / 2
    t = p.cleat_thickness - GAP
    cutters = [countersunk_hole(Vector(x, t, z_hole), Vector(0, 1, 0), t, p.screw_d + 0.5, p.screw_head_d + 0.5)
               for x in cleat_holes(p, lay)]
    cleat = cleat.cut(cutters + notch_cutters(p, lay)).removeSplitter()
    if not cleat.isValid() or len(cleat.Solids) != len(cleat_pieces(p, lay)):
        raise GeometryError(f"cleat: geometry kernel produced {len(cleat.Solids)} pieces, "
                            f"expected {len(cleat_pieces(p, lay))}")
    return Part.makeCompound(cleat.Solids)
