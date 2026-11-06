"""Every flange parameter, with its default and range, and the rules that tie parameters together.

Values marked auto follow the shape and fixing: `effective` fills them in, and the geometry only ever sees a
resolved copy. Coordinates: z = 0 is the wall's outside face, and +z points out of the box.
"""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass

from tridi.params import ParamError, param
from tridi.printers import Printer

from . import layout

SINK = 0.5  # how far a bolt head's seat sits below the surface
NUT_ROOM = 0.2  # extra height for a nut in its pocket
MIN_LAND = 1.0  # plastic left under a countersink or a nut
HUB_GAP = 0.5  # gap the auto hub stop leaves between the hubs
COLLAR_GAP = 0.3  # how far the auto collar stops short of the wall's other side
MAX_CELLS = 4000  # more printed holes than this take too long to build
FLY_HOLE = 2.0  # an estimate: printed holes wider than this may let flies through
STOCK_BOLTS = (8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100)
FORCE_HINT = "--force builds it anyway"


@dataclass(frozen=True)
class FlangeParams:
    # what kind
    shape: str = param("round", "outline of the flange", choices=("round", "slot"))
    fixing: str = param("two_piece", "two pieces bolted through the rim, one piece on the wall, or two pieces with "
                        "bolts through central hubs", choices=("two_piece", "one_piece", "centre_bolt"))
    mesh: str = param("wire", "what keeps insects out: wire mesh you add, a printed grid or honeycomb, or a solid "
                      "area for the slicer's infill to replace", choices=("wire", "grid", "honeycomb", "slicer"))
    # box
    wall_thickness: float = param(2, "thickness of the box wall, mm", min=0.5, max=15)
    # size
    opening_d: float = param(50, "round opening's diameter, mm", min=10, max=300)
    slot_length: float = param(190, "slot opening's length, mm", min=20, max=600)
    slot_width: float = param(21, "slot opening's width, mm", min=10, max=150)
    rim: float | None = param(None, "rim's width beside the opening, mm (auto: 14, or 8 on centre_bolt)", min=4, max=60)
    outer_thickness: float = param(4, "outer piece's thickness, mm", min=2, max=15)
    inner_thickness: float = param(5, "inner piece's thickness, mm", min=3, max=15)
    # bolts
    rim_bolts: int | None = param(None, "bolts through the rim (auto: 4 on round, 8 on slot)", min=3, max=32)
    hubs: int | None = param(None, "bolts through hubs on centre_bolt (auto: 1 on round, 3 on slot)", min=1, max=12)
    bars: int = param(4, "bars to the rim on a round centre_bolt flange", choices=(2, 3, 4))
    hub_d: float = param(14, "hub's diameter, mm", min=8, max=40)
    bar_width: float = param(8, "bar's width, mm", min=2, max=30)
    # collar and hub stop
    collar_height: float | None = param(None, "lip into the wall hole, mm (auto: wall_thickness - 0.3, 0: none)",
                                        min=0, max=15)
    collar_wall: float = param(1.6, "collar's wall, mm", min=0.8, max=6)
    collar_fit: float = param(0.2, "gap between the collar and the wall hole, each side, mm", min=0, max=1)
    hub_stop: float | None = param(None, "boss on the inner hub, mm: smaller lets the bolt squeeze harder (auto: leaves "
                                   "a 0.5 mm gap between the hubs, 0: none)", min=0, max=20)
    # mesh
    mesh_hole: float = param(1.5, "printed mesh hole's size, across the flats, mm", min=0.5, max=6)
    mesh_rib: float = param(0.8, "printed mesh rib's width, mm", min=0.2, max=5)
    mesh_thickness: float = param(1.2, "thickness of the printed mesh or the slicer's solid area, mm", min=0.4, max=15)
    mesh_angle: float | None = param(None, "printed mesh's angle, degrees (auto: 45 on grid, 0 on honeycomb)",
                                     min=0, max=90)
    wire_thickness: float = param(0.5, "wire mesh's thickness, mm", min=0, max=3)
    seal_thickness: float = param(0, "foam tape under the rim, mm: bolt lengths allow for it", min=0, max=5)
    # hardware
    washer_thickness: float = param(0.8, "washer's thickness on one_piece, mm", min=0, max=3)
    bolt_d: float = param(4, "bolt diameter, mm", min=2, max=6)
    head_d: float = param(8, "countersunk bolt head diameter, mm", min=4, max=14)
    nut_af: float = param(7, "nut across its flats, mm", min=3, max=12)
    nut_height: float = param(3.2, "nut height, mm", min=1, max=6)
    # printing
    bed_chamfer: float = param(0.4, "chamfer where a part touches the print bed, mm", min=0, max=1)
    # overruling
    force: bool = param(False, "build anyway when a size check, range or printer fit would refuse; each one overruled "
                        "is listed in the summary")


def hole_d(p: FlangeParams) -> float:
    return p.bolt_d + 0.5


def _seat_r(p: FlangeParams) -> float:
    return p.head_d / 2 + 0.2


def outer_z0(p: FlangeParams) -> float:
    """The outer piece's wall side: it stands off the wall by whatever is clamped between them."""
    return (p.wire_thickness if p.mesh == "wire" else 0) + p.seal_thickness


def nut_ledge(p: FlangeParams) -> float:
    return p.inner_thickness - p.nut_height - NUT_ROOM


def _bolt_need(p: FlangeParams) -> float:
    """A countersunk bolt's length includes its head. The tip should clear the nut by 1 mm."""
    backing = p.washer_thickness if p.fixing == "one_piece" else nut_ledge(p)
    return p.outer_thickness + outer_z0(p) + p.wall_thickness + backing + p.nut_height + 1 - SINK


def bolt_length(p: FlangeParams) -> int:
    need = _bolt_need(p)
    return next((stock for stock in STOCK_BOLTS if stock >= need), math.ceil(need))


def bolt_count(p: FlangeParams) -> int:
    return p.hubs if p.fixing == "centre_bolt" else p.rim_bolts


def wall_hole(p: FlangeParams) -> tuple[float, float]:
    r, s = layout.spine(p)
    grow = p.collar_wall + p.collar_fit if p.collar_height > 0 else 0
    return 2 * (r + s + grow), 2 * (r + grow)


def _resolve_auto(p: FlangeParams) -> FlangeParams:
    round_ = p.shape == "round"
    centre = p.fixing == "centre_bolt"
    resolved = dataclasses.replace(
        p,
        rim=(8 if centre else 14) if p.rim is None else p.rim,
        rim_bolts=(4 if round_ else 8) if p.rim_bolts is None else p.rim_bolts,
        hubs=(1 if round_ else 3) if p.hubs is None else p.hubs,
        mesh_angle=(0 if p.mesh == "honeycomb" else 45) if p.mesh_angle is None else p.mesh_angle,
        collar_height=max(p.wall_thickness - COLLAR_GAP, 0) if p.collar_height is None else p.collar_height,
    )
    if p.fixing == "one_piece":
        resolved = dataclasses.replace(resolved, collar_height=0)
    stop = 0
    if centre:
        stop = max(outer_z0(resolved) + resolved.wall_thickness - HUB_GAP, 0) if p.hub_stop is None else p.hub_stop
    return dataclasses.replace(resolved, hub_stop=stop)


def _shape_problems(p: FlangeParams) -> list[str]:
    out = []
    if p.shape == "slot" and p.slot_length <= p.slot_width:
        out.append(f"slot_length ({p.slot_length:g}) must be longer than slot_width ({p.slot_width:g})")
    if p.shape == "round" and p.hubs != 1:
        out.append(f"hubs ({p.hubs}) only applies to a slot: a round flange has one hub")
    return out


def _thickness_problems(p: FlangeParams) -> list[str]:
    out = []
    seat = SINK + (p.head_d + 0.4 - hole_d(p)) / 2 + MIN_LAND
    if p.outer_thickness < seat:
        out.append(f"outer_thickness ({p.outer_thickness:g}) must be at least {seat:g} mm to hold the head's seat")
    if p.fixing != "one_piece" and nut_ledge(p) < MIN_LAND:
        out.append(f"inner_thickness ({p.inner_thickness:g}) leaves under {MIN_LAND:g} mm behind a "
                   f"{p.nut_height:g} mm nut")
    if _bolt_need(p) > STOCK_BOLTS[-1]:
        out.append(f"wall_thickness ({p.wall_thickness:g}) needs a bolt over {STOCK_BOLTS[-1]} mm long")
    return out


def _collar_problems(p: FlangeParams) -> list[str]:
    if p.collar_height >= p.wall_thickness:
        return [f"collar_height ({p.collar_height:g}) must be under wall_thickness ({p.wall_thickness:g}): the pieces "
                f"would meet before gripping the wall"]
    return []


def _rim_problems(p: FlangeParams) -> list[str]:
    out = []
    grow = p.collar_wall + p.collar_fit if p.collar_height > 0 else 0
    if p.rim < grow + 2:
        out.append(f"rim ({p.rim:g}) leaves under 2 mm of grip on the wall beside a {grow:g} mm collar")
    if p.fixing == "centre_bolt":
        return out
    if p.rim / 2 < _seat_r(p) + 1:
        out.append(f"rim ({p.rim:g}) is too narrow for a {p.head_d:g} mm bolt head")
    if p.rim / 2 - hole_d(p) / 2 - grow < 1:
        out.append(f"rim ({p.rim:g}) leaves under 1 mm of wall between the wall hole and the bolt holes")
    if p.shape == "round" and p.rim_bolts < 3:
        out.append(f"rim_bolts ({p.rim_bolts}) must be at least 3 on a round flange")
    if p.shape == "slot" and (p.rim_bolts < 4 or p.rim_bolts % 2):
        out.append(f"rim_bolts ({p.rim_bolts}) must be an even number from 4 on a slot, or the flange is lopsided")
    bolts = layout.rim_bolt_xy(p)
    closest = min((math.dist(a, b) for a, b in zip(bolts, bolts[1:] + bolts[:1])), default=math.inf)
    if closest < p.head_d + 1.4:
        out.append(f"rim_bolts ({p.rim_bolts}) puts bolt heads {closest:.1f} mm apart: too close to fit")
    return out


def _hub_problems(p: FlangeParams) -> list[str]:
    if p.fixing != "centre_bolt":
        return []
    out = []
    if p.hub_d < p.head_d + 2:
        out.append(f"hub_d ({p.hub_d:g}) is too small for a {p.head_d:g} mm bolt head")
    if p.bar_width >= p.hub_d:
        out.append(f"bar_width ({p.bar_width:g}) must be under hub_d ({p.hub_d:g})")
    r, _ = layout.spine(p)
    if p.hubs < 1:
        out.append(f"hubs ({p.hubs}) leaves nothing holding the pieces together")
    elif p.shape == "slot":
        if p.hub_d > 2 * r - 2:
            out.append(f"hub_d ({p.hub_d:g}) is too wide for a {2 * r:g} mm slot")
        if p.slot_length / p.hubs < p.hub_d + 2:
            out.append(f"hubs ({p.hubs}) are too close together along a {p.slot_length:g} mm slot")
    if layout.area_after_bars(p) <= 0:
        size = "opening_d" if p.shape == "round" else "slot_width"
        out.append(f"{size} is so small the hub and bars fill the opening")
    gap = outer_z0(p) + p.wall_thickness - p.hub_stop
    if gap <= 0:
        out.append(f"hub_stop ({p.hub_stop:g}) leaves no gap between the hubs, so they'd touch before the rim grips")
    return out


def _mesh_problems(p: FlangeParams) -> list[str]:
    if p.mesh == "wire":
        return []
    out = []
    if p.mesh_thickness > p.outer_thickness:
        out.append(f"mesh_thickness ({p.mesh_thickness:g}) is thicker than outer_thickness ({p.outer_thickness:g})")
    if p.mesh == "slicer":
        return out
    cells = len(layout.mesh_cells(p))
    if cells == 0:
        out.append(f"mesh_hole ({p.mesh_hole:g}) leaves no holes that fit in this opening")
    if cells > MAX_CELLS:
        out.append(f"mesh_hole ({p.mesh_hole:g}) makes {cells} holes, over the {MAX_CELLS} that build in reasonable "
                   f"time; use a larger hole or rib")
    return out


def _problems(p: FlangeParams) -> list[str]:
    return [*_shape_problems(p), *_thickness_problems(p), *_collar_problems(p), *_rim_problems(p), *_hub_problems(p),
            *_mesh_problems(p)]


def _settle(p: FlangeParams, problems: list[str]) -> list[str]:
    """Refuse, or with `force` hand the problems back as notes for the summary."""
    if problems and not p.force:
        raise ParamError(f"{'; '.join(problems)} ({FORCE_HINT})")
    return [f"forced: {m}" for m in problems]


def check_printer(p: FlangeParams, printer: Printer) -> list[str]:
    problems = []
    if p.mesh in ("grid", "honeycomb") and p.mesh_rib < printer.nozzle:
        problems.append(f"mesh_rib ({p.mesh_rib:g}) is thinner than {printer.name}'s {printer.nozzle:g} mm nozzle")
    return _settle(p, problems)


def effective(p: FlangeParams) -> tuple[FlangeParams, list[str]]:
    """Fill in the auto values, refuse combinations that can't work, and list what to buy and cut."""
    p = _resolve_auto(p)
    notes = _settle(p, _problems(p))
    width, height = layout.outer_size(p)
    notes += [f"sizes: {width:g} × {height:g} mm outside, {_opening_text(p)} opening", _wall_note(p),
              _hardware_note(p, width, height), _air_note(p)]
    if p.mesh in ("grid", "honeycomb") and p.mesh_hole > FLY_HOLE:
        notes.append(f"mesh: {p.mesh_hole:g} mm holes are over the estimated {FLY_HOLE:g} mm limit, so flies may get "
                     f"through")
    return p, notes


def _wall_note(p: FlangeParams) -> str:
    x, y = wall_hole(p)
    hole = f"a {x:g} mm hole" if p.shape == "round" else f"a {x:g} × {y:g} mm slot with fully rounded ends"
    if p.fixing == "centre_bolt":
        return f"wall: cut {hole}; no bolt holes are needed"
    return f"wall: cut {hole} and drill {bolt_count(p)} × {hole_d(p):g} mm holes; the outer piece is the template"


def _hardware_note(p: FlangeParams, width: float, height: float) -> str:
    n, m = bolt_count(p), f"M{p.bolt_d:g}"
    items = [f"{n} × {m}×{bolt_length(p)} countersunk hex-socket bolts (ISO 10642 / DIN 7991)", f"{n} × {m} nuts"]
    if p.fixing == "one_piece":
        items.append(f"{n} × {m} washers")
    if p.mesh == "wire":
        items.append(f"{width - 2:g} × {height - 2:g} mm of wire mesh")
    return f"hardware: {', '.join(items)}"


def _air_note(p: FlangeParams) -> str:
    opening = layout.opening_area(p)
    parts = [f"air: {opening:.0f} mm² opening"]
    if p.fixing == "centre_bolt":
        parts.append(f"{layout.area_after_bars(p):.0f} mm² after hubs and bars")
    if p.mesh in ("grid", "honeycomb"):
        area = layout.open_area(p)
        parts.append(f"{area:.0f} mm² through the mesh ({area / opening:.0%} of the opening)")
    elif p.mesh == "wire":
        parts.append("fly screen is typically 60–70% open")
    else:
        parts.append("what's left depends on the infill you choose")
    return ", ".join(parts)


def _opening_text(p: FlangeParams) -> str:
    return f"{p.opening_d:g} mm" if p.shape == "round" else f"{p.slot_length:g} × {p.slot_width:g} mm"
