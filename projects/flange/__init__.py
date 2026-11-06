"""Air vent flange for a drying box's side wall: round or long slot, with wire or printed mesh."""
from __future__ import annotations

import tridi  # noqa: F401  (FreeCAD on sys.path)
import FreeCAD

from tridi.export import PrintPart
from tridi.printers import Printer

from .params import FlangeParams, check_printer, effective
from .parts import build_inner, build_mesh_zone, build_outer

NAME = "flange"
TITLE = "Air vent flange for a box wall"
Params = FlangeParams


def build(p: FlangeParams, printer: Printer) -> tuple[list[PrintPart], list[str]]:
    p, notes = effective(p)
    notes += check_printer(p, printer)
    upright = FreeCAD.Rotation()
    parts = [PrintPart("outer", build_outer(p, printer.clearance), upright, orientation="wall side down, head seats up")]
    if p.fixing != "one_piece":
        parts.append(PrintPart("inner", build_inner(p, printer.clearance), upright,
                               orientation="wall side up, nut pockets on the bed"))
    if p.mesh == "slicer":
        parts.append(PrintPart("mesh_zone", build_mesh_zone(p), upright, orientation="slicer modifier for outer",
                               modifier_of="outer"))
    return parts, notes
