"""Bar holder for a drying box: a strip of snap-in cradles bolted through the box's thin wall to a backplate."""
from __future__ import annotations

import tridi  # noqa: F401  (FreeCAD on sys.path)
import FreeCAD
from FreeCAD import Vector

from tridi.export import PrintPart
from tridi.printers import Printer

from .params import BarholderParams, effective
from .parts import build_plate, build_strip

NAME = "barholder"
TITLE = "Snap-in bar holder strip and backplate for a thin box wall"
Params = BarholderParams


def build(p: BarholderParams, printer: Printer) -> tuple[list[PrintPart], list[str]]:
    p, notes = effective(p)
    clearance = printer.clearance
    parts = [PrintPart("strip", build_strip(p, clearance), FreeCAD.Rotation(),
                       orientation="wall side down, cradles up")]
    if p.backplate:
        parts.append(PrintPart("backplate", build_plate(p, clearance), FreeCAD.Rotation(Vector(1, 0, 0), 180),
                               orientation="wall side down, bolt seats up"))
    return parts, notes
