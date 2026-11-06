"""Every grommet parameter, with its default and range, and the rules that tie them together.

Values marked auto follow the wire and hole: `effective` fills them in, and the geometry only ever sees a resolved
copy. Coordinates: the axis is z, z = 0 is the disc's outside face and +z points into the box. The halves split at
y = 0, and a twin or flat wire's width runs along x.
"""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass

from tridi.params import ParamError, param, range_problems

THREAD_DEPTH = 1.0  # from the thread's root to its crest
HOLE_PLAY = 0.5  # hole's diameter over the thread's
DISC_OVER_HOLE = 11.5  # auto disc's diameter over the hole's
MIN_LIP = 2.0  # disc beyond the hole, each side
NUT_OVER_THREAD = 8.0  # auto nut's diameter over the thread's
SPARE_THREAD = 1.5  # stem past the nut
SLOT_HEIGHT_PLAY = 0.1  # clear zone's height over the wire's
SLOT_WIDTH_PLAY = 0.2  # clear zone's width over the wire's
MIN_RIDGE_RADIUS = 1.0  # no tighter than this where a ridge touches the wire
MAX_SQUEEZE = 0.15  # of the wire's height
JOINT_NECK = 1.2  # the nut's T tab, across the radius
JOINT_HEAD = 2.2
JOINT_FIT = 0.2  # gap around the tab, each side
JOINT_WALL = 0.8  # plastic each side of a socket
FORCE_HINT = "--force builds it anyway"


@dataclass(frozen=True)
class GrommetParams:
    # what you measure
    wire_shape: str = param("twin", "wire's shape: two round cores side by side, round, or rectangular",
                            choices=("twin", "round", "flat"))
    wire_width: float = param(5, "width of a twin or flat wire, mm", min=1, max=30)
    wire_height: float = param(2.5, "height of a twin or flat wire, mm", min=0.5, max=15)
    wire_d: float = param(6, "diameter of a round wire, mm", min=1, max=30)
    wall_thickness: float = param(2, "thickness of the wall, mm", min=0.5, max=60)
    # sizes
    hole_d: float | None = param(None, "hole to cut in the wall, mm: set it larger so a connector fits through (auto: "
                                 "the smallest half millimetre that fits the wire)", min=5, max=100)
    disc_d: float | None = param(None, "disc's diameter, mm (auto: hole + 11.5)", min=8, max=130)
    disc_thickness: float = param(2.5, "disc's thickness, mm", min=1.5, max=10)
    nut_d: float | None = param(None, "nut's diameter, mm (auto: thread + 8, or what its joint needs)", min=8, max=130)
    nut_height: float = param(7, "nut's height, mm: the grip runs under the nut, so a taller nut grips more wire",
                              min=4, max=40)
    body_wall: float = param(2.5, "plastic from the wire's slot to the thread's root, mm", min=2, max=10)
    # grip
    grip_squeeze: float = param(0.2, "how much smaller than the wire the slot is at a ridge's top, mm", min=0, max=3)
    grip_wave: float = param(0.2, "how far each ridge shifts the wire off centre, mm", min=0, max=2)
    grip_pitch: float | None = param(None, "spacing of the ridges on one face, mm (auto: about twice the wire's height)",
                                     min=2, max=40)
    groove_rib: float = param(0.3, "rib into a twin wire's groove, mm (0: none)", min=0, max=5)
    # thread
    thread_pitch: float = param(2.5, "thread's pitch, mm", min=2.2, max=8)
    thread_clearance: float | None = param(None, "gap between nut and body threads, each side, mm (auto: the printer's "
                                           "clearance)", min=0, max=1)
    # printing
    bed_chamfer: float = param(0.4, "chamfer where a part touches the print bed, mm", min=0, max=1)
    # overruling
    force: bool = param(False, "build anyway when a size check, range or printer fit would refuse; each one overruled "
                        "is listed in the summary")


def wire_h(p: GrommetParams) -> float:
    """The wire's size across the split, which is the direction the grip squeezes."""
    return p.wire_d if p.wire_shape == "round" else p.wire_height


def slot_height(p: GrommetParams) -> float:
    return wire_h(p) + SLOT_HEIGHT_PLAY


def slot_width(p: GrommetParams) -> float:
    return slot_height(p) if p.wire_shape == "round" else p.wire_width + SLOT_WIDTH_PLAY


def _smallest_thread(p: GrommetParams) -> float:
    return max(slot_width(p), slot_height(p)) + 2 * p.body_wall + 2 * THREAD_DEPTH


def thread_d(p: GrommetParams) -> float:
    return p.hole_d - HOLE_PLAY


def root_d(p: GrommetParams) -> float:
    return thread_d(p) - 2 * THREAD_DEPTH


def nut_z0(p: GrommetParams) -> float:
    """The nut's wall face."""
    return p.disc_thickness + p.wall_thickness


def thread_start(p: GrommetParams) -> float:
    """Right down to the disc on a thin wall. On a thick one the stem is plain until just before the nut's position."""
    return max(p.disc_thickness, nut_z0(p) - 2 * p.thread_pitch)


def stem_end(p: GrommetParams) -> float:
    return nut_z0(p) + p.nut_height + SPARE_THREAD


def clearance(p: GrommetParams) -> float:
    return 0.2 if p.thread_clearance is None else p.thread_clearance


def _bore_d(p: GrommetParams) -> float:
    return thread_d(p) + 2 * clearance(p)


def joint_centre_r(p: GrommetParams) -> float:
    """The joint sits midway between the bore's deepest point and the nut's edge."""
    return (_bore_d(p) / 2 + p.nut_d / 2) / 2


def _smallest_nut(p: GrommetParams) -> float:
    return _bore_d(p) + 2 * (JOINT_HEAD + 2 * JOINT_FIT + 2 * JOINT_WALL)


def _tightest_pitch(p: GrommetParams) -> float:
    """The wire's centre line bends no tighter than its own height, and ridge tops stay round."""
    bend = p.grip_wave * wire_h(p)
    ridge = (p.grip_wave + p.grip_squeeze + SLOT_HEIGHT_PLAY) * MIN_RIDGE_RADIUS
    return 2 * math.pi * math.sqrt(max(bend, ridge))


def grip_span(p: GrommetParams) -> tuple[float, float, int]:
    """Where the ridges sit, centred under the nut: (start, end, how many)."""
    ridges = max(1, math.floor(2 * p.nut_height / p.grip_pitch))
    length = ridges * p.grip_pitch / 2
    z0 = nut_z0(p) + (p.nut_height - length) / 2
    return z0, z0 + length, ridges


def _resolve_auto(p: GrommetParams, printer_clearance: float) -> GrommetParams:
    if p.thread_clearance is None:
        p = dataclasses.replace(p, thread_clearance=printer_clearance)
    if p.hole_d is None:
        p = dataclasses.replace(p, hole_d=math.ceil((_smallest_thread(p) + HOLE_PLAY) * 2 - 1e-9) / 2)
    if p.disc_d is None:
        p = dataclasses.replace(p, disc_d=p.hole_d + DISC_OVER_HOLE)
    if p.nut_d is None:
        need = max(thread_d(p) + NUT_OVER_THREAD, _smallest_nut(p))
        p = dataclasses.replace(p, nut_d=math.ceil(need * 2 - 1e-9) / 2)
    if p.grip_pitch is None:
        p = dataclasses.replace(p, grip_pitch=max(_tightest_pitch(p), min(2 * wire_h(p), p.nut_height)))
    return p


def _problems(p: GrommetParams) -> list[str]:
    out = []
    if p.wire_shape != "round" and p.wire_width < p.wire_height:
        out.append(f"wire_width ({p.wire_width:g}) is under wire_height ({p.wire_height:g}): measure the wide side as "
                   f"its width")
    if thread_d(p) < _smallest_thread(p) - 1e-9:
        out.append(f"hole_d ({p.hole_d:g}) is too small for this wire and body_wall: it needs at least "
                   f"{_smallest_thread(p) + HOLE_PLAY:g}")
    if p.disc_d < p.hole_d + 2 * MIN_LIP:
        out.append(f"disc_d ({p.disc_d:g}) is too small to cover a {p.hole_d:g} mm hole: it needs at least "
                   f"{p.hole_d + 2 * MIN_LIP:g}")
    if p.nut_d < _smallest_nut(p) - 1e-9:
        out.append(f"nut_d ({p.nut_d:g}) is too small to hold its joint: it needs at least {_smallest_nut(p):g}")
    if p.grip_squeeze > MAX_SQUEEZE * wire_h(p) + 1e-9:
        out.append(f"grip_squeeze ({p.grip_squeeze:g}) is over {MAX_SQUEEZE:.0%} of the wire's height, which risks "
                   f"crushing it")
    if p.grip_pitch < _tightest_pitch(p) - 1e-9:
        out.append(f"grip_pitch ({p.grip_pitch:g}) bends the wire too tightly: it needs at least "
                   f"{_tightest_pitch(p):.1f}")
    if p.wire_shape == "twin" and p.groove_rib > (slot_height(p) - 0.5) / 2:
        out.append(f"groove_rib ({p.groove_rib:g}) reaches the middle of the wire: it can't be over "
                   f"{(slot_height(p) - 0.5) / 2:g}")
    if p.thread_pitch <= 2 * THREAD_DEPTH:
        out.append(f"thread_pitch ({p.thread_pitch:g}) leaves no flats on a {THREAD_DEPTH:g} mm deep thread")
    return out


def _settle(p: GrommetParams, problems: list[str]) -> list[str]:
    """Refuse, or with `force` hand the problems back as notes for the summary."""
    if problems and not p.force:
        raise ParamError(f"{'; '.join(problems)} ({FORCE_HINT})")
    return [f"forced: {m}" for m in problems]


def _summary(p: GrommetParams) -> list[str]:
    tightest = wire_h(p) - p.grip_squeeze
    return [f"cut: a {p.hole_d:g} mm hole in the {p.wall_thickness:g} mm wall",
            f"flat wall needed: {p.disc_d:g} mm across outside for the disc, {p.nut_d:g} mm inside for the nut",
            f"how low: the hole's centre at least {p.nut_d / 2 + 1:g} mm above the inside floor, and {p.disc_d / 2:g} mm "
            f"clear of any curve in the wall outside",
            f"grip: {wire_h(p):g} mm wire, {tightest:g} mm slot at a ridge, {grip_span(p)[2]} ridges under the nut",
            "hardware: nothing to buy"]


def effective(p: GrommetParams, printer_clearance: float = 0.2) -> tuple[GrommetParams, list[str]]:
    """Fill in the auto values, refuse sizes that can't work, and list what to cut."""
    given = p
    p = _resolve_auto(p, printer_clearance)
    notes = _settle(p, [*range_problems(given), *_problems(p)])
    ridges = grip_span(p)[2]
    if ridges < 2:
        notes.append(f"grip: only {ridges} ridge fits under a {p.nut_height:g} mm nut with this wire; a taller nut "
                     f"(nut_height) gives more")
    notes += _summary(p)
    return p, notes
