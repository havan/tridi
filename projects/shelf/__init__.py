"""Parametric wall shelf for small devices, with cable management."""
from __future__ import annotations

import tridi  # noqa: F401  (FreeCAD on sys.path)
import FreeCAD
from FreeCAD import Vector

from tridi.export import PrintPart
from tridi.printers import Printer

from .body import PRINT_ROTATION, build_body
from .cleat import build_cleat
from .clip import CLIP_ROTATION, build_clip, clip_spot
from .layout import plan
from .params import ShelfParams, effective

NAME = "shelf"
TITLE = "Parametric wall shelf"
Params = ShelfParams

ORIENTATION_LABEL = {"flat": "lying on its back plate", "side": "on its end (side)"}


def build(p: ShelfParams, printer: Printer) -> tuple[list[PrintPart], list[str]]:
    p, notes = effective(p)
    lay = plan(p)
    parts = [PrintPart("shelf", build_body(p, lay), PRINT_ROTATION[p.orientation],
                       orientation=ORIENTATION_LABEL[p.orientation])]
    if p.mount == "cleat":
        parts.append(PrintPart("cleat", build_cleat(p, lay), FreeCAD.Rotation(Vector(1, 0, 0), 90),
                               orientation="lying on its back"))
    if p.clips:
        spot = clip_spot(p, lay)  # refuses when no edge is free; the assembly shows the clip there
        clip = build_clip(p, printer.clearance)
        clip.transformShape(spot.toMatrix())
        parts.append(PrintPart("clip", clip, CLIP_ROTATION.multiply(spot.Rotation.inverted()), count=p.clips,
                               orientation="standing on its back"))
    return parts, notes
