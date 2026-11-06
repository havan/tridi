"""Every fanbox parameter, with its default and range, and the rules that tie parameters together.

Values marked auto follow the fan: `effective` fills them in, and the geometry only ever sees a resolved copy.
"""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass

from tridi.params import ParamError, param

TOP_FLANGE = 6.0  # the straight part of the duct under the fan seat
NUT_CEILING = 5.0  # plastic between a fan bolt's nut and the fan
HOLE_TAIL = 7.0  # the fan bolt hole's run past the nut, for the bolt's tip
SINK = 0.5  # how far a bolt head's seat sits below the surface
NUT_ROOM = 0.2  # extra height for a nut in its pocket
CORNER_R = 6.0  # outer corner radius of the duct's base and the plate
MIN_LAND = 1.0  # plastic left under a countersink
STOCK_BOLTS = (8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100)
# distance between the bolt holes of standard square fans
FAN_HOLE_SPACING = {60: 50, 70: 60, 80: 71.5, 92: 82.5, 120: 105, 140: 124.5, 200: 154}


@dataclass(frozen=True)
class FanboxParams:
    # lid
    lid_thickness: float = param(2, "thickness of the box lid, mm", min=0.5, max=15)
    lid_flat_width: float = param(95, "flat area of the lid, short side, mm", min=20, max=1000)
    lid_flat_length: float = param(230, "flat area of the lid, long side, mm", min=20, max=1000)
    # fan
    fan_size: float = param(140, "fan's outside size, mm", min=60, max=200)
    fan_thickness: float = param(25, "fan thickness, mm", min=10, max=60)
    fan_hole_spacing: float | None = param(None, "distance between the fan's bolt holes, mm (auto: the standard for "
                                           "fan_size)", min=40, max=190)
    fan_corner_r: float = param(3, "corner radius of the fan, and of the socket's inside corners, mm", min=0.5, max=20)
    # socket
    fan_fit: float = param(0.3, "gap around the fan in its socket, each side, mm", min=0, max=2)
    socket_wall: float = param(2.4, "socket wall around the fan, mm", min=1.2, max=6)
    mesh_lift: float = param(0, "how far the socket's rim stands above the fan, for a cable that stands proud, mm",
                             min=0, max=10)
    cable_side: str = param("right", "side of the socket with the cable notch, seen from above with the long side "
                            "left to right", choices=("right", "left", "back", "front"))
    cable_offset: float | None = param(None, "cable notch's distance from the middle of that side, mm (auto: "
                                       "fan_size / 4 toward the front or left)", min=-100, max=100)
    cable_notch_width: float = param(6, "cable notch width, mm (0: no notch)", min=0, max=30)
    cable_notch_depth: float = param(5, "cable notch depth from the rim, mm", min=1, max=30)
    # duct
    base_width: float = param(90, "outside of the duct at the lid, short side, mm", min=30, max=300)
    base_length: float | None = param(None, "outside of the duct at the lid, long side, mm (auto: fan_size)",
                                      min=30, max=300)
    wall: float = param(3, "duct wall at the lid, and the rim of the lid opening, mm", min=2, max=5)
    duct_height: float = param(55, "lid to the fan's seat, mm", min=25, max=300)
    fan_bore: float | None = param(None, "round opening under the fan, mm (auto: fan_size - 4)", min=40, max=196)
    flange_thickness: float = param(6, "thickness of the duct's foot on the lid, mm", min=3, max=15)
    ear_length: float = param(18, "how far the bolt ears stick out past the duct, mm", min=5, max=40)
    ear_width: float = param(20, "bolt ear width, mm", min=12, max=60)
    plate_ledge: float = param(3, "plastic between the nuts and the lid in the underside plate, mm", min=1.5, max=10)
    # mesh frame
    frame_thickness: float = param(5, "mesh frame thickness, mm", min=2, max=15)
    frame_opening: float | None = param(None, "round opening of the mesh frame, mm (auto: fan_size - 8)",
                                        min=30, max=196)
    mesh_thickness: float = param(0.5, "wire mesh thickness, mm (bolt length only)", min=0, max=3)
    # hardware
    bolt_d: float = param(4, "bolt diameter, mm", min=2, max=6)
    head_d: float = param(8, "countersunk bolt head diameter, mm", min=4, max=14)
    nut_af: float = param(7, "nut across its flats, mm", min=3, max=12)
    nut_height: float = param(3.2, "nut height, mm", min=1, max=6)
    # printing
    bed_chamfer: float = param(0.4, "chamfer where a part touches the print bed, mm", min=0, max=1)


def hole_d(p: FanboxParams) -> float:
    return p.bolt_d + 0.5


def socket_size(p: FanboxParams) -> float:
    return p.fan_size + 2 * p.fan_fit + 2 * p.socket_wall


def lid_bolt_xy(p: FanboxParams) -> tuple[float, float]:
    return p.base_length / 2 + p.ear_length / 2, p.base_width / 2 - p.ear_width / 2


def plate_thickness(p: FanboxParams) -> float:
    return p.plate_ledge + p.nut_height + NUT_ROOM


def _stock(length: float) -> int:
    for stock in STOCK_BOLTS:
        if stock >= length:
            return stock
    raise ParamError(f"no stock bolt is long enough: {length:g} mm needed")


def lid_bolt_length(p: FanboxParams) -> int:
    """A countersunk bolt's length includes its head. The tip should clear the nut by 1 mm."""
    return _stock(p.flange_thickness + p.lid_thickness + p.plate_ledge + p.nut_height + 1 - SINK)


def fan_bolt_length(p: FanboxParams) -> int:
    return _stock(p.frame_thickness + p.mesh_thickness + p.mesh_lift + p.fan_thickness + NUT_CEILING + p.nut_height
                  + 1 - SINK)


def _resolve_auto(p: FanboxParams) -> FanboxParams:
    spacing = p.fan_hole_spacing
    if spacing is None:
        spacing = FAN_HOLE_SPACING.get(p.fan_size)
        if spacing is None:
            known = ", ".join(map(str, FAN_HOLE_SPACING))
            raise ParamError(f"a {p.fan_size:g} mm fan isn't a standard size ({known}); "
                             f"give its fan_hole_spacing")
    return dataclasses.replace(
        p,
        fan_hole_spacing=spacing,
        base_length=p.fan_size if p.base_length is None else p.base_length,
        fan_bore=p.fan_size - 4 if p.fan_bore is None else p.fan_bore,
        frame_opening=p.fan_size - 8 if p.frame_opening is None else p.frame_opening,
        cable_offset=-p.fan_size / 4 if p.cable_offset is None else p.cable_offset,
    )


def _check_fit_on_lid(p: FanboxParams) -> None:
    overall = p.base_length + 2 * p.ear_length
    if p.base_width > p.lid_flat_width or overall > p.lid_flat_length:
        raise ParamError(f"the {overall:g} × {p.base_width:g} mm base doesn't fit the lid's flat area of "
                         f"{p.lid_flat_length:g} × {p.lid_flat_width:g} mm")


def _check_fan(p: FanboxParams) -> None:
    if p.fan_bore > p.fan_size - 3:
        raise ParamError(f"fan_bore ({p.fan_bore:g}) leaves no seat for a {p.fan_size:g} mm fan")
    if p.frame_opening > p.fan_bore:
        raise ParamError(f"frame_opening ({p.frame_opening:g}) must not be wider than fan_bore ({p.fan_bore:g})")
    if p.frame_opening > p.fan_size - 6:
        raise ParamError(f"frame_opening ({p.frame_opening:g}) leaves too narrow a rim on a {p.fan_size:g} mm fan")
    seat_r = p.head_d / 2 + 0.2
    if p.fan_hole_spacing / 2 * math.sqrt(2) - seat_r < p.frame_opening / 2:
        raise ParamError(f"frame_opening ({p.frame_opening:g}) reaches the bolt heads at "
                         f"{p.fan_hole_spacing:g} mm spacing")
    if p.fan_hole_spacing / 2 + seat_r > socket_size(p) / 2 - 1:
        raise ParamError(f"fan_hole_spacing ({p.fan_hole_spacing:g}) puts the bolt heads off the frame's edge")


def _check_cable(p: FanboxParams) -> None:
    if p.cable_notch_width <= 0:
        return
    flat = p.fan_size / 2 + p.fan_fit - p.fan_corner_r
    if abs(p.cable_offset) + p.cable_notch_width / 2 > flat:
        raise ParamError(f"a {p.cable_notch_width:g} mm cable notch at {p.cable_offset:g} mm runs into the socket's "
                         f"corner; the side is flat for {flat:g} mm either way")
    if p.cable_notch_depth > p.fan_thickness + p.mesh_lift:
        raise ParamError(f"cable_notch_depth ({p.cable_notch_depth:g}) is deeper than the socket")


def _check_printable(p: FanboxParams) -> None:
    loft = p.duct_height - p.flange_thickness - TOP_FLANGE
    if loft <= 0:
        raise ParamError(f"duct_height ({p.duct_height:g}) leaves no room between the duct's two flanges")
    flares = (
        (socket_size(p) - p.base_width) / 2,
        (socket_size(p) - p.base_length) / 2,
        p.fan_bore / 2 - (p.base_width / 2 - p.wall),
        p.fan_bore / 2 - (p.base_length / 2 - p.wall),
    )
    if max(abs(f) for f in flares) > loft:
        raise ParamError(f"a {loft:g} mm tall flare of {max(abs(f) for f in flares):g} mm is steeper than 45° and "
                         f"would need supports; raise duct_height")


def _check_hardware(p: FanboxParams) -> None:
    if p.head_d < p.bolt_d + 1 or p.nut_af < p.bolt_d + 1:
        raise ParamError(f"head_d ({p.head_d:g}) and nut_af ({p.nut_af:g}) must be at least bolt_d + 1 ({p.bolt_d + 1:g})")
    seat = SINK + (p.head_d + 0.4 - hole_d(p)) / 2 + MIN_LAND
    if p.flange_thickness < seat or p.frame_thickness < seat:
        raise ParamError(f"flange_thickness and frame_thickness must be at least {seat:g} mm to hold the countersink")
    x, _ = lid_bolt_xy(p)
    if x - p.head_d / 2 - 0.2 < socket_size(p) / 2:
        raise ParamError(f"the lid bolts sit under the socket where a hex key can't reach them; raise ear_length "
                         f"above {p.ear_length:g} or base_length above {p.base_length:g}")
    if p.ear_width < p.head_d + 3:
        raise ParamError(f"ear_width ({p.ear_width:g}) is too narrow for a {p.head_d:g} mm bolt head")
    if 2 * p.ear_width > p.base_width:
        raise ParamError(f"two {p.ear_width:g} mm ears don't fit along a {p.base_width:g} mm base")
    # the nuts' slots and the bolt tips have to stay inside the wall as the duct narrows toward the lid
    loft = p.duct_height - p.flange_thickness - TOP_FLANGE
    fan = p.fan_hole_spacing / 2
    floor = p.duct_height - NUT_CEILING - p.nut_height - NUT_ROOM

    def edge_at(z: float) -> float:
        return p.base_width / 2 + (socket_size(p) - p.base_width) / 2 * (z - p.flange_thickness) / loft

    tail = floor - HOLE_TAIL
    if fan + (p.nut_af + 0.4) / 2 > edge_at(floor) - 1.2:
        raise ParamError(f"fan_hole_spacing ({p.fan_hole_spacing:g}) leaves no room for the nuts inside the wall")
    if tail < p.flange_thickness or edge_at(tail) < fan + hole_d(p) / 2 + 1:
        raise ParamError(f"duct_height ({p.duct_height:g}) is too short for the fan bolts to run inside the wall")


def effective(p: FanboxParams) -> tuple[FanboxParams, list[str]]:
    """Fill in the auto values, refuse combinations that can't work, and list the hardware to buy."""
    p = _resolve_auto(p)
    _check_fit_on_lid(p)
    _check_fan(p)
    _check_cable(p)
    _check_printable(p)
    _check_hardware(p)
    m = f"M{p.bolt_d:g}"
    x, y = lid_bolt_xy(p)
    mesh = math.ceil(socket_size(p))
    notes = [
        f"sizes: base {p.base_length:g} × {p.base_width:g} mm, fan {p.fan_size:g} × {p.fan_thickness:g} mm with holes "
        f"{p.fan_hole_spacing:g} mm apart, socket {socket_size(p):g} mm outside",
        f"hardware: 4 × {m}×{lid_bolt_length(p)} countersunk hex-socket bolts for the lid, "
        f"4 × {m}×{fan_bolt_length(p)} for the fan, 8 × {m} nuts (ISO 10642 / DIN 7991 bolts), "
        f"{mesh} × {mesh} mm of wire mesh",
        f"lid: cut a {p.base_length - 2 * p.wall:g} × {p.base_width - 2 * p.wall:g} mm opening and drill "
        f"{hole_d(p):g} mm holes {2 * x:g} × {2 * y:g} mm apart; the underside plate is the template",
    ]
    return p, notes
