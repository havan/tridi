"""Every shelf parameter, with its default and range, and the rules that tie parameters together."""
from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass

from tridi.params import ParamError, param

NOTCH_RE = re.compile(r"^(back-left|back-right|back@\d+(\.\d+)?)$")


@dataclass(frozen=True)
class ShelfParams:
    # size
    width: float = param(200, "shelf width along the wall, mm", min=40, max=1000)
    depth: float = param(100, "from the wall to the front edge, mm", min=30, max=400)
    slab_thickness: float = param(4, "shelf surface thickness, mm", min=2, max=12)
    plate_thickness: float = param(4, "back plate thickness, mm", min=2, max=12)
    # brackets
    supports: str = param("below", "brackets under the shelf or above it", choices=("below", "above"))
    bracket_count: int | None = param(None, "number of brackets (auto: gaps of at most 160 mm)", min=2, max=20)
    bracket_depth: float | None = param(None, "how far a bracket reaches along the shelf, mm (auto: 0.75 × depth)",
                                        min=10, max=400)
    bracket_height: float = param(55, "how far a bracket reaches along the back plate, mm", min=15, max=300)
    bracket_thickness: float = param(5, "bracket thickness, mm", min=2, max=20)
    bracket_web: float = param(6, "width of the bracket's strip along shelf and plate, mm", min=2, max=30)
    # finish
    edge_radius: float = param(2, "rounding of exposed edges, mm", min=0, max=5)
    bed_chamfer: float = param(0.4, "chamfer on the edge touching the print bed, mm", min=0, max=2)
    # mounting
    mount: str = param("screws", "how the shelf goes on the wall", choices=("screws", "keyhole", "cleat", "adhesive"))
    top_screws: str = param("under", "top screws under the shelf, or in a strip above it", choices=("under", "strip"))
    strip_height: float = param(18, "height of the strip above the shelf, mm", min=10, max=60)
    max_reach: float = param(150, "deepest shelf a screwdriver reaches under, mm", min=50, max=500)
    screw_d: float = param(4, "screw diameter, mm", min=2.5, max=8)
    screw_head_d: float = param(8, "countersunk screw head diameter, mm", min=5, max=16)
    dowel_d: float = param(6, "wall dowel diameter, mm (instructions only)", min=4, max=14)
    cleat_thickness: float = param(8, "wall cleat thickness, mm", min=5, max=20)
    cleat_height: float = param(30, "wall cleat height, mm", min=15, max=80)
    adhesive_extra: float = param(25, "extra back plate length for tape or glue, mm", min=0, max=100)
    glue_grooves: bool = param(False, "grooves on the wall side for hot glue")
    # material saving
    plate_style: str = param("full", "back plate: solid, with windows, or pads only",
                             choices=("full", "windowed", "pads"))
    surface: str = param("solid", "shelf surface", choices=("solid", "honeycomb"))
    hex_cell: float = param(10, "honeycomb cell across flats, mm", min=5, max=40)
    hex_wall: float = param(2, "honeycomb wall, mm", min=1, max=10)
    solid_rim: float = param(8, "solid border around a honeycomb surface, mm", min=4, max=30)
    # cables
    notches: tuple[str, ...] = param((), "cable cutout: back-left, back-right or back@<x mm from the left>")
    notch_width: float = param(14, "width of a back cable notch, mm", min=6, max=40)
    corner_notch_r: float = param(15, "radius of a corner cable notch, mm", min=6, max=40)
    front_lip: float = param(0, "height of a lip along the front edge, mm (0: none)", min=0, max=30)
    clips: int = param(0, "number of cable-tip clips to export", min=0, max=50)
    clip_cable_d: float = param(4, "cable diameter the clips grip, mm", min=2, max=10)
    # printing
    orientation: str = param("flat", "print lying on the back plate, or on its end (stronger)",
                             choices=("flat", "side"))


def wall_offset(p: ShelfParams) -> float:
    """Distance from the wall to the back plate: the cleat sits in between."""
    return p.cleat_thickness if p.mount == "cleat" else 0.0


def bracket_depth(p: ShelfParams) -> float:
    return p.bracket_depth if p.bracket_depth is not None else 0.75 * p.depth


def effective(p: ShelfParams) -> tuple[ShelfParams, list[str]]:
    """Apply the rules between parameters: adjust what can be adjusted (with a note), refuse the rest."""
    notes: list[str] = []
    if p.mount == "adhesive" and p.plate_style != "full":
        p = dataclasses.replace(p, plate_style="full")
        notes.append("adhesive mounting needs the full back plate; plate_style set to full")
    if p.mount == "cleat" and p.plate_style == "pads":
        raise ParamError("pads plate style is not supported with the cleat; use windowed or full")
    # keyhole and cleat screws go into the wall before the shelf, so only plain screws need reach
    reach = p.depth + p.front_lip
    if p.mount == "screws" and reach > p.max_reach:
        if p.supports == "below" and p.top_screws == "under":
            raise ParamError(f"a screwdriver can't reach under a {reach:g} mm deep shelf (max_reach "
                             f"{p.max_reach:g}); use --top-screws strip, --mount keyhole or --mount cleat")
        if p.supports == "above":
            raise ParamError(f"a screwdriver can't reach across a {reach:g} mm deep shelf (max_reach "
                             f"{p.max_reach:g}); use --mount keyhole or --mount cleat")
    if p.orientation == "side" and (p.plate_style == "pads" or p.mount == "keyhole"):
        what = "the pads" if p.plate_style == "pads" else "keyholes"
        raise ParamError(f"--orientation side can't print {what} without supports; use --orientation flat")
    if p.screw_head_d < p.screw_d + 1:
        raise ParamError(f"screw_head_d ({p.screw_head_d:g}) must be at least screw_d + 1 ({p.screw_d + 1:g})")
    bd = bracket_depth(p)
    if 2 * p.bracket_web >= min(bd, p.bracket_height):
        raise ParamError(f"bracket_web ({p.bracket_web:g}) is too wide for a {bd:g} × {p.bracket_height:g} mm bracket")
    room = p.depth - wall_offset(p) - p.plate_thickness
    if bd > room:
        raise ParamError(f"bracket_depth ({bd:g}) is more than the shelf's {room:g} mm in front of the plate")
    seen = set()
    for n in p.notches:
        if not NOTCH_RE.match(n):
            raise ParamError(f"notch {n!r} is not back-left, back-right or back@<x>")
        if n in seen:
            raise ParamError(f"notch {n!r} is given twice")
        seen.add(n)
    return p, notes
