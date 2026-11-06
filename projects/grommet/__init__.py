"""Cable grommet for a thin wall: a split body and two-piece nut that fit around a wire already in place."""
from __future__ import annotations

import tridi  # noqa: F401  (FreeCAD on sys.path)
import FreeCAD

from tridi.export import PrintPart
from tridi.printers import Printer

from .params import GrommetParams, effective
from .parts import build_body, build_nut

NAME = "grommet"
TITLE = "Cable grommet for a thin wall"
Params = GrommetParams


def build(p: GrommetParams, printer: Printer) -> tuple[list[PrintPart], list[str]]:
    p, notes = effective(p, printer.clearance)
    upright = FreeCAD.Rotation()
    parts = [PrintPart(f"body_{s}", build_body(p, s), upright, orientation="standing on the disc") for s in "ab"]
    parts += [PrintPart(f"nut_{s}", build_nut(p, s), upright, orientation="wall side down") for s in "ab"]
    return parts, notes
