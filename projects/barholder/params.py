"""Every barholder parameter, with its default and range, and the rules that tie parameters together.

Geometry helpers here use the same coordinates as `parts`: x along the wall, y up, z out of the wall into the box,
with the bar's centre at x = cradle position, y = 0.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from tridi.params import ParamError, param

SINK = 0.5  # how far a bolt head's seat sits below the plate's surface
NUT_ROOM = 0.2  # extra height for a nut in its pocket
NUT_SLIDE = 0.4  # how much wider than the nut a slot is, for a sliding fit
MIN_LAND = 1.0  # plastic left under a countersink
BOLT_CAP = 0.5  # plastic left between a slot's bolt hole and the strip's front: it only covers the tip
TIP_ROOM = 0.5  # room past a bolt's tip in its blind hole
WASHER = 1.0  # thickness of a washer under a pan head, when there's no backplate
HEAD_MARGIN = 1.0  # plastic between a bolt head's seat and the cradle's outside, along the strip
MIN_SEAT = 10.0  # how much of a bar has to rest in a cradle
MOUTH_OPEN = 1.5  # how much wider than the bar's radius each side of the mouth opens at its top
FLARE_ANGLE = 30.0  # the mouth's slope from vertical
MIN_FLARE = 2.0  # the mouth's shortest flare, mm
STOCK_BOLTS = (8, 10, 12, 16, 20, 25, 30, 35, 40)


@dataclass(frozen=True)
class BarholderParams:
    # bar
    bar_d: float = param(20, "bar diameter: measure yours, wood varies, mm", min=6, max=60)
    bar_fit: float = param(0.3, "gap around the bar in its seat, mm", min=0, max=1.5)
    wrap: float = param(225, "how far the cradle wraps round the bar, degrees: 180 is a plain half circle with no "
                        "snap, more makes a tighter snap", min=180, max=240)
    # cradles
    count: int = param(3, "cradles on one strip", min=1, max=20)
    pitch: float = param(70, "distance between bars, centre to centre, mm", min=10, max=250)
    cradle_depth: float = param(25, "how far a cradle stands out from the wall, mm; deeper forgives shorter bars",
                                min=10, max=80)
    cradle_wall: float = param(3, "cradle wall thickness, mm; thinner makes a softer snap", min=1.6, max=8)
    # strip
    strip_height: float = param(16, "height of the strip, mm", min=8, max=60)
    strip_thickness: float = param(8, "thickness of the strip against the wall, mm", min=3, max=20)
    strip_drop: float = param(3, "how far the strip's top edge sits below the bar's centre, mm; lower makes a softer "
                              "snap", min=0, max=30)
    # box
    box_wall: float = param(2, "thickness of the box wall, mm", min=0.5, max=15)
    # backplate
    backplate: bool = param(True, "plate on the outside of the wall, spreads the load over the thin plastic")
    plate_thickness: float = param(4, "backplate thickness, mm", min=2, max=15)
    # support bracket
    bracket: bool = param(False, "ribs under each cradle, down to a foot on the wall")
    bracket_height: float = param(20, "how far the foot reaches below the cradle, mm", min=5, max=80)
    bracket_rib: float = param(3, "thickness of each bracket rib, mm", min=1.2, max=6)
    # drain
    drain: bool = param(True, "gap in the cradle's floor by the wall, so drips don't pool against the wood")
    drain_width: float = param(4, "drain width, mm", min=1, max=20)
    drain_length: float = param(6, "drain length along the bar, mm", min=1, max=60)
    # hardware
    nut_entry: str = param("top", "how the nuts go in: top is a slot from the strip's top edge with the meat side "
                           "closed, front is a pocket open toward the meat", choices=("top", "front"))
    nut_ledge: float = param(2, "plastic between a nut and the wall, which the bolt clamps, mm", min=1.2, max=10)
    bolt_d: float = param(4, "bolt diameter, mm", min=2, max=6)
    head_d: float = param(8, "countersunk bolt head diameter, mm", min=4, max=14)
    nut_af: float = param(7, "nut across its flats, mm", min=3, max=12)
    nut_height: float = param(3.2, "nut height, mm", min=1, max=6)
    # printing
    bed_chamfer: float = param(0.4, "chamfer where a part touches the print bed, mm", min=0, max=1)


def hole_d(p: BarholderParams) -> float:
    return p.bolt_d + 0.5


def bore_r(p: BarholderParams) -> float:
    return p.bar_d / 2 + p.bar_fit


def outer_r(p: BarholderParams) -> float:
    return bore_r(p) + p.cradle_wall


def lip_angle(p: BarholderParams) -> float:
    """Where the seat's arc ends, in degrees above the bar's centre."""
    return p.wrap / 2 - 90


def mouth_width(p: BarholderParams) -> float:
    """The narrowest gap a bar has to pass on its way into the seat."""
    return 2 * bore_r(p) * math.cos(math.radians(lip_angle(p)))


def flare_top(p: BarholderParams) -> tuple[float, float]:
    """Half the mouth's width at the top of the cradle, and that top's height above the bar's centre."""
    a = math.radians(lip_angle(p))
    r, t = bore_r(p), math.tan(math.radians(FLARE_ANGLE))
    wanted = p.bar_d / 2 + MOUTH_OPEN
    y = max(r * math.sin(a) + max(MIN_FLARE, (wanted - r * math.cos(a)) / t), outer_r(p) * math.sin(a) + 1)
    return r * math.cos(a) + (y - r * math.sin(a)) * t, y


def cradle_xs(p: BarholderParams) -> list[float]:
    return [(i - (p.count - 1) / 2) * p.pitch for i in range(p.count)]


def _head_clearance(p: BarholderParams) -> float:
    """From a cradle's outside to the nearest bolt, along the strip: past the bolt head and the nut's slot."""
    return max(p.head_d / 2 + 0.2, (p.nut_af + NUT_SLIDE) / 2) + HEAD_MARGIN


def end_bolt_x(p: BarholderParams) -> float:
    return (p.count - 1) / 2 * p.pitch + outer_r(p) + _head_clearance(p)


def bolt_xs(p: BarholderParams) -> list[float]:
    xs = cradle_xs(p)
    return [-end_bolt_x(p), *((a + b) / 2 for a, b in zip(xs, xs[1:])), end_bolt_x(p)]


def overall_length(p: BarholderParams) -> float:
    return 2 * end_bolt_x(p) + p.strip_height


def strip_top(p: BarholderParams) -> float:
    return -p.strip_drop


def strip_bottom(p: BarholderParams) -> float:
    return strip_top(p) - p.strip_height


def bolt_y(p: BarholderParams) -> float:
    return strip_top(p) - p.strip_height / 2


def foot_y(p: BarholderParams) -> float:
    return -outer_r(p) - p.bracket_height


def rib_span(p: BarholderParams) -> tuple[float, float]:
    """A bracket rib's sides, as distances from the cradle's centre. The drain runs between the two ribs."""
    return p.drain_width / 2, p.drain_width / 2 + p.bracket_rib


def rib_top_y(p: BarholderParams) -> float:
    """Where the ribs end, inside the cradle's wall all the way across their thickness."""
    a, b = rib_span(p)
    return (-math.sqrt(outer_r(p) ** 2 - b ** 2) - math.sqrt(bore_r(p) ** 2 - a ** 2)) / 2


def _stock(length: float) -> int:
    for stock in STOCK_BOLTS:
        if stock >= length:
            return stock
    raise ParamError(f"no stock bolt is long enough: {length:g} mm needed")


def bolt_length(p: BarholderParams) -> int:
    """A countersunk bolt's length includes its head, a pan head's doesn't. The tip should clear the nut by 1 mm."""
    clamped = p.box_wall + p.nut_ledge + p.nut_height + 1
    if p.backplate:
        return _stock(p.plate_thickness + clamped - SINK)
    return _stock(WASHER + clamped)


def bolt_tip_z(p: BarholderParams) -> float:
    if p.backplate:
        return bolt_length(p) - (p.plate_thickness + p.box_wall - SINK)
    return bolt_length(p) - (WASHER + p.box_wall)


def blind_hole_depth(p: BarholderParams) -> float:
    return bolt_tip_z(p) + TIP_ROOM


def min_cradle_depth(p: BarholderParams) -> float:
    """The arms start on a 45° slope above the strip, and the seat has to hold the bar past the strip."""
    _, top = flare_top(p)
    return max(p.strip_thickness + MIN_SEAT, p.strip_thickness + top - strip_top(p) + 2)


def _check_layout(p: BarholderParams) -> None:
    if p.count > 1 and p.pitch < 2 * (outer_r(p) + _head_clearance(p)):
        raise ParamError(f"pitch ({p.pitch:g}) leaves no room for a bolt between {2 * outer_r(p):g} mm wide cradles; "
                         f"use at least {2 * (outer_r(p) + _head_clearance(p)):g}")
    if p.strip_drop > 0.7 * bore_r(p):
        raise ParamError(f"strip_drop ({p.strip_drop:g}) leaves too little of the strip beside the cradle; "
                         f"use at most {0.7 * bore_r(p):g}")
    if p.cradle_depth < min_cradle_depth(p):
        raise ParamError(f"cradle_depth ({p.cradle_depth:g}) is too shallow to hold the bar; "
                         f"use at least {min_cradle_depth(p):g}")


def _check_hardware(p: BarholderParams) -> None:
    if p.head_d < p.bolt_d + 1 or p.nut_af < p.bolt_d + 1:
        raise ParamError(f"head_d ({p.head_d:g}) and nut_af ({p.nut_af:g}) must be at least bolt_d + 1 "
                         f"({p.bolt_d + 1:g})")
    needed = max(p.head_d + 0.4, (p.nut_af + 0.2) * 2 / math.sqrt(3)) + 4.8
    if p.strip_height < needed:
        raise ParamError(f"strip_height ({p.strip_height:g}) is too narrow for the nuts and bolt heads; "
                         f"use at least {needed:g}")
    seat = SINK + (p.head_d + 0.4 - hole_d(p)) / 2 + MIN_LAND
    if p.backplate and p.plate_thickness < seat:
        raise ParamError(f"plate_thickness ({p.plate_thickness:g}) must be at least {seat:g} mm to hold the "
                         f"countersink")
    cap = BOLT_CAP if p.nut_entry == "top" else 0
    thick = bolt_tip_z(p) + TIP_ROOM + cap
    if p.strip_thickness < thick:
        raise ParamError(f"strip_thickness ({p.strip_thickness:g}) is too thin to hide an "
                         f"M{p.bolt_d:g}×{bolt_length(p)} bolt's tip; use at least {thick:g}")


def _check_drain(p: BarholderParams) -> None:
    if not p.drain:
        return
    if p.drain_width > 0.7 * p.bar_d:
        raise ParamError(f"drain_width ({p.drain_width:g}) is too wide for a {p.bar_d:g} mm bar to rest on; "
                         f"use at most {0.7 * p.bar_d:g}")
    room = p.cradle_depth - p.strip_thickness - MIN_SEAT / 2
    if p.drain_length > room:
        raise ParamError(f"drain_length ({p.drain_length:g}) leaves too little of the ring closed; "
                         f"use at most {room:g}")


def _check_bracket(p: BarholderParams) -> None:
    if not p.bracket:
        return
    a, b = rib_span(p)
    reach = outer_r(p) ** 2 - b ** 2
    if reach <= 0 or math.sqrt(reach) <= math.sqrt(max(bore_r(p) ** 2 - a ** 2, 0)):
        raise ParamError(f"the bracket's ribs, {a:g} to {b:g} mm from the centre, miss a {2 * outer_r(p):g} mm wide "
                         f"cradle; use a thinner bracket_rib or a narrower drain_width")


def _snap_note(p: BarholderParams) -> str:
    mouth = mouth_width(p)
    if mouth >= p.bar_d:
        return f"no snap: the mouth is {mouth:.1f} mm, so a {p.bar_d:g} mm bar lifts straight out"
    return (f"snap: the mouth is {p.bar_d - mouth:.1f} mm narrower than a {p.bar_d:g} mm bar; if it's too stiff, lower "
            f"wrap or cradle_wall, and print a single cradle (--count 1) to try it on your wood first")


def effective(p: BarholderParams) -> tuple[BarholderParams, list[str]]:
    """Refuse combinations that can't work, and list the hardware to buy."""
    _check_layout(p)
    _check_hardware(p)
    _check_drain(p)
    _check_bracket(p)
    m, n = f"M{p.bolt_d:g}", p.count + 1
    if p.backplate:
        bolts = f"{n} × {m}×{bolt_length(p)} countersunk hex-socket bolts, {n} × {m} nuts (ISO 10642 / DIN 7991 bolts)"
        drill = "the backplate is the template"
    else:
        bolts = f"{n} × {m}×{bolt_length(p)} pan-head bolts, {n} × {m} nuts, {n} × {m} washers on the outside"
        drill = "use the strip's bolt holes as the template"
    if p.nut_entry == "top":
        nuts = "nuts: drop one into each slot from the strip's top edge, where it centres itself on the hole"
    else:
        nuts = ("nuts: press one into each pocket from the front. They face the meat, so use stainless steel and "
                "threadlock so one can't work loose")
    spacing = ", ".join(f"{x:g}" for x in bolt_xs(p))
    notes = [
        f"sizes: strip {overall_length(p):g} mm long, {p.count} cradles {p.pitch:g} mm apart, standing "
        f"{p.cradle_depth:g} mm off the wall",
        f"hardware for one strip: {bolts}. Print one set for each wall",
        f"wall: drill {hole_d(p):g} mm holes at {spacing} mm from the strip's middle; {drill}, and drill both walls "
        f"at the same height so the bars sit level",
        nuts,
        f"bar length: at most the distance between the walls minus {2 * p.strip_thickness:g} mm, at least that "
        f"distance minus {2 * (p.cradle_depth - MIN_SEAT):g} mm (keeps {MIN_SEAT:g} mm in each cradle)",
        _snap_note(p),
    ]
    return p, notes
