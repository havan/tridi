"""Export print parts: STL and 3MF in print orientation, STEP and FCStd in use coordinates, and a summary."""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import FreeCAD
import MeshPart
import Part
from FreeCAD import Vector

from .printers import FitError, Printer, check_fit

PLA_DENSITY = 1.24  # g/cm³
GAP = 4.0  # mm between copies of a part on the bed


@dataclass
class PrintPart:
    name: str
    shape: Part.Shape  # in use coordinates
    rotation: FreeCAD.Rotation  # use coordinates -> print orientation
    count: int = 1
    orientation: str = ""
    modifier_of: str | None = None  # a slicer modifier for the named part: placed in its bed frame, not a printed part


def _bed_offset(shape: Part.Shape, rotation: FreeCAD.Rotation) -> Vector:
    s = shape.copy()
    s.transformShape(rotation.toMatrix())
    bb = s.optimalBoundingBox()  # the plain BoundBox is loose on curves and would lift the part off the bed
    return Vector(-bb.XMin, -bb.YMin, -bb.ZMin)


def to_bed(shape: Part.Shape, rotation: FreeCAD.Rotation) -> Part.Shape:
    s = shape.copy()
    s.transformShape(rotation.toMatrix())
    s.translate(_bed_offset(shape, rotation))
    return s


def _modifier_on_bed(part: PrintPart, parent: PrintPart) -> Part.Shape:
    """Where the modifier belongs on its parent's bed, so the two line up when loaded together."""
    s = part.shape.copy()
    s.transformShape(part.rotation.toMatrix())
    s.translate(_bed_offset(parent.shape, parent.rotation))
    return s


def _size(shape: Part.Shape) -> tuple[float, float, float]:
    bb = shape.optimalBoundingBox()
    return bb.XLength, bb.YLength, bb.ZLength


def _plate(part: PrintPart, printer: Printer, parts: list[PrintPart], fit=check_fit) -> Part.Shape:
    """All copies of a part laid out in rows along X, checked against the build volume."""
    if part.modifier_of is not None:
        return _modifier_on_bed(part, next(p for p in parts if p.name == part.modifier_of))
    single = to_bed(part.shape, part.rotation)
    x, y, z = _size(single)
    fit(part.name, (x, y, z), printer)
    if part.count == 1:
        return single
    per_row = max(1, int((printer.x + GAP) // (x + GAP)))
    rows = math.ceil(part.count / per_row)
    width = min(part.count, per_row) * (x + GAP) - GAP
    fit(f"{part.name} ×{part.count}", (width, rows * (y + GAP) - GAP, z), printer)
    copies = []
    for i in range(part.count):
        c = single.copy()
        c.translate(Vector((i % per_row) * (x + GAP), (i // per_row) * (y + GAP), 0))
        copies.append(c)
    return Part.makeCompound(copies)


def _value(v) -> str:
    if v is None:
        return "auto"
    if isinstance(v, tuple):
        return ", ".join(map(str, v)) or "none"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def export(parts: list[PrintPart], out_dir: Path, *, title: str, params: dict, printer: Printer,
           notes: list[str], force: bool = False) -> Path:
    forced: list[str] = []

    def fit(name: str, size: tuple[float, float, float], on: Printer) -> None:
        try:
            check_fit(name, size, on)
        except FitError as e:
            if not force:
                raise
            forced.append(f"forced: {e}")

    plates = [_plate(p, printer, parts, fit) for p in parts]  # raises before anything is written
    notes = [*notes, *forced]

    out_dir.mkdir(parents=True, exist_ok=True)
    for part, plate in zip(parts, plates):
        mesh = MeshPart.meshFromShape(Shape=plate, LinearDeflection=0.05, AngularDeflection=0.2618)
        mesh.write(str(out_dir / f"{part.name}.stl"))
        mesh.write(str(out_dir / f"{part.name}.3mf"))
    Part.makeCompound([p.shape for p in parts if p.modifier_of is None]).exportStep(str(out_dir / "assembly.step"))

    doc = FreeCAD.newDocument("tridi_export", hidden=True)
    try:
        for part in parts:
            doc.addObject("Part::Feature", part.name).Shape = part.shape
        doc.recompute()
        doc.saveAs(str(out_dir / f"{title}.FCStd"))
    finally:
        FreeCAD.closeDocument(doc.Name)

    lines = [title, f"printer: {printer.name} ({printer.x:g} × {printer.y:g} × {printer.z:g} mm)", "",
             "parameters:"]
    lines += [f"  {k} = {_value(params[k])}" for k in sorted(params)]
    lines += ["", "parts:"]
    total = 0.0
    for part in parts:
        if part.modifier_of is not None:
            x, y, z = _size(part.shape)
            lines.append(f"  {part.name} ×{part.count}: slicer modifier for {part.modifier_of}, "
                         f"size {x:.1f} × {y:.1f} × {z:.1f} mm")
            continue
        cm3 = part.shape.Volume / 1000
        grams = cm3 * PLA_DENSITY
        total += grams * part.count
        x, y, z = _size(to_bed(part.shape, part.rotation))
        lines.append(f"  {part.name} ×{part.count}: {cm3:.1f} cm³, ~{grams:.0f} g each (solid), "
                     f"print size {x:.1f} × {y:.1f} × {z:.1f} mm, {part.orientation}")
    lines.append(f"total: ~{total:.0f} g")
    if notes:
        lines += ["", "notes:"] + [f"  {n}" for n in notes]
    summary = out_dir / "summary.txt"
    summary.write_text("\n".join(lines) + "\n")
    return summary
