import pytest

import tridi  # noqa: F401
import FreeCAD
import Mesh
import Part
from FreeCAD import Vector as V

from tridi.export import PrintPart, export, to_bed
from tridi.printers import FitError, Printer

ROT = FreeCAD.Rotation(V(1, 0, 0), 90)
PRINTER = Printer("t", "Test", 100, 100, 100)


def _block(count=1):
    return PrintPart("block", Part.makeBox(20, 10, 5, V(3, 4, 5)), ROT, count=count, orientation="flat")


def _export(tmp_path, parts, printer=PRINTER):
    out = tmp_path / "out"
    return out, export(parts, out, title="thing", params={"width": 200.0, "notches": ("a", "b"),
                                                          "count": None}, printer=printer, notes=["a note"])


def test_to_bed_min_zero():
    bb = to_bed(_block().shape, ROT).BoundBox
    assert (bb.XMin, bb.YMin, bb.ZMin) == pytest.approx((0, 0, 0), abs=1e-9)
    assert bb.ZLength == pytest.approx(10)


def test_export_files(tmp_path):
    out, summary = _export(tmp_path, [_block()])
    for name in ("block.stl", "block.3mf", "assembly.step", "thing.FCStd", "summary.txt"):
        assert (out / name).exists(), name
    text = summary.read_text()
    assert "block ×1: 1.0 cm³, ~1 g each" in text
    assert "print size 20.0 × 5.0 × 10.0 mm" in text
    assert "printer: Test (100 × 100 × 100 mm)" in text
    assert "  notches = a, b" in text and "  count = auto" in text
    assert "a note" in text


def test_stl_on_bed(tmp_path):
    out, _ = _export(tmp_path, [_block()])
    assert Mesh.Mesh(str(out / "block.stl")).BoundBox.ZMin == pytest.approx(0, abs=1e-6)


def test_count_layout(tmp_path):
    printer = Printer("t", "Test", 50, 100, 100)
    out, summary = _export(tmp_path, [_block(count=6)], printer)
    bb = Mesh.Mesh(str(out / "block.stl")).BoundBox
    assert bb.XLength <= 50
    assert bb.YLength > 10
    assert "block ×6" in summary.read_text()


def test_too_big_writes_nothing(tmp_path):
    with pytest.raises(FitError):
        _export(tmp_path, [_block()], Printer("t", "Tiny", 10, 10, 10))
    assert not (tmp_path / "out").exists()


def test_count_too_many_for_bed(tmp_path):
    with pytest.raises(FitError):
        _export(tmp_path, [_block(count=40)], Printer("t", "Small", 50, 50, 50))
    assert not (tmp_path / "out").exists()


def _base_and_zone():
    base = PrintPart("base", Part.makeBox(50, 50, 4, V(-25, -25, 7)), FreeCAD.Rotation(), orientation="flat")
    zone = PrintPart("zone", Part.makeBox(10, 10, 4, V(-5, -5, 7)), FreeCAD.Rotation(), modifier_of="base",
                     orientation="slicer modifier")
    return base, zone


def test_modifier_part_shares_its_parents_bed_frame_and_is_left_out_of_totals(tmp_path):
    out, summary = _export(tmp_path, list(_base_and_zone()))
    bb = Mesh.Mesh(str(out / "zone.stl")).BoundBox
    assert (bb.XMin, bb.XMax, bb.YMin, bb.YMax) == pytest.approx((20, 30, 20, 30), abs=1e-6)
    alone, summary_alone = _export(tmp_path / "alone", [_base_and_zone()[0]])
    total = [line for line in summary.read_text().splitlines() if line.startswith("total:")]
    assert total == [line for line in summary_alone.read_text().splitlines() if line.startswith("total:")]
    assert "zone ×1: slicer modifier" in summary.read_text()
    assert len(Part.read(str(out / "assembly.step")).Solids) == 1


def test_force_exports_a_part_that_does_not_fit(tmp_path):
    out = tmp_path / "out"
    summary = export([_block()], out, title="thing", params={}, printer=Printer("t", "Tiny", 10, 10, 10), notes=[],
                     force=True)
    assert (out / "block.stl").exists()
    assert "forced: block: 20.0 × 5.0 × 10.0 mm does not fit Tiny" in summary.read_text()
