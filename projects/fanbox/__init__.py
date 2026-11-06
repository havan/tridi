"""Fan duct for a drying box: a PC fan in a drop-in socket on a box lid, with a wire mesh frame to keep flies out."""
from __future__ import annotations

import tridi  # noqa: F401  (FreeCAD on sys.path)
import FreeCAD
from FreeCAD import Vector

from tridi.export import PrintPart
from tridi.printers import Printer

from .params import FanboxParams, effective
from .parts import build_duct, build_frame, build_plate

NAME = "fanbox"
TITLE = "Fan socket, duct and mesh frame for a box lid"
Params = FanboxParams


def build(p: FanboxParams, printer: Printer) -> tuple[list[PrintPart], list[str]]:
    p, notes = effective(p)
    clearance = printer.clearance
    upright = FreeCAD.Rotation()
    flipped = FreeCAD.Rotation(Vector(1, 0, 0), 180)
    parts = [
        PrintPart("duct", build_duct(p, clearance), upright, orientation="standing on the lid end"),
        PrintPart("lid_plate", build_plate(p, clearance), flipped, orientation="lid side down, nut pockets up"),
        PrintPart("mesh_frame", build_frame(p, clearance), upright, orientation="fan side down"),
    ]
    return parts, notes
