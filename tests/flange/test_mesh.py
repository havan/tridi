import math

import pytest

import tridi  # noqa: F401
import Mesh
import Part
from FreeCAD import Vector as V

from projects.flange import build
from projects.flange.layout import area_after_bars, mesh_cells, open_area, opening_area
from projects.flange.params import FlangeParams, effective
from projects.flange.parts import build_mesh_zone, build_outer
from tridi.export import export
from tridi.features import GeometryError
from tests.flange.test_params import REFUSED
from tridi.printers import get_printer, load_printers

CLEAR = 0.2
PRINTER = get_printer("mk3s", load_printers())


def resolved(**kw):
    return effective(FlangeParams(**kw))[0]


def solid_at(shape, x, y, z):
    return shape.isInside(V(x, y, z), 1e-6, False)


@pytest.fixture(scope="module")
def grid():
    return build_outer(resolved(mesh="grid"), CLEAR)


def test_grid_prints_flat_on_the_wall_side(grid):
    assert grid.BoundBox.ZMin == pytest.approx(0)
    q = (1.5 + 0.8) * math.sqrt(0.5)
    assert (0, 0) in [(round(x, 9), round(y, 9)) for x, y in mesh_cells(resolved(mesh="grid"))]
    assert not solid_at(grid, 0, 0, 0.6)
    assert solid_at(grid, q / 2, q / 2, 0.6)
    assert not solid_at(grid, q / 2, q / 2, 1.5)


def test_grid_volume_matches_cell_count(grid):
    plain = build_outer(resolved(mesh="slicer"), CLEAR)
    assert plain.Volume - grid.Volume == pytest.approx(open_area(resolved(mesh="grid")) * 1.2, rel=0.005)


def test_honeycomb_cells_are_hexagons():
    comb = build_outer(resolved(mesh="honeycomb"), CLEAR)
    assert not solid_at(comb, 0.7 * 0.75, 0, 0.6)
    assert solid_at(comb, 0.75 + 0.1, 0, 0.6)
    assert not solid_at(comb, 0, 0.75 + 0.1, 0.6)  # towards a vertex it's still open: the point sits at 0.866


# every fixing, mesh and shape, without building all 18: the slot's meshes take a while to check
COMBINATIONS = [
    ("round", "two_piece", "grid"), ("round", "one_piece", "grid"), ("round", "centre_bolt", "grid"),
    ("round", "centre_bolt", "honeycomb"), ("round", "two_piece", "slicer"), ("round", "centre_bolt", "slicer"),
    ("slot", "two_piece", "honeycomb"), ("slot", "centre_bolt", "grid"), ("slot", "one_piece", "slicer"),
    ("slot", "centre_bolt", "slicer"),
]


@pytest.mark.parametrize("shape,fixing,mesh", COMBINATIONS)
def test_combinations_build_as_one_solid(shape, fixing, mesh):
    parts, _ = build(FlangeParams(shape=shape, fixing=fixing, mesh=mesh), PRINTER)  # refuses anything else
    assert all(len(part.shape.Solids) == 1 for part in parts if part.modifier_of is None)


def test_bars_stay_full_thickness_over_the_mesh():
    piece = build_outer(resolved(mesh="grid", fixing="centre_bolt"), CLEAR)
    assert solid_at(piece, 12, 0, 3)
    assert not solid_at(piece, 12, 12, 3)


@pytest.mark.parametrize("mesh", ["grid", "slicer"])
def test_a_mesh_as_thin_as_the_chamfer_builds(mesh):
    assert build_outer(resolved(mesh=mesh, mesh_thickness=0.4), CLEAR).isValid()


def test_slicer_leaves_the_opening_solid():
    piece = build_outer(resolved(mesh="slicer"), CLEAR)
    assert solid_at(piece, 0, 0, 0.6)
    assert not solid_at(piece, 0, 0, 1.5)


@pytest.mark.parametrize("mesh", ["slicer", "grid"])
def test_flat_plug(mesh):
    p = resolved(mesh=mesh, mesh_thickness=4)
    piece = build_outer(p, CLEAR)
    assert piece.isValid() and len(piece.Solids) == 1
    assert solid_at(piece, 0, 0, 3.5) == (mesh == "slicer")
    assert piece.BoundBox.ZLength == pytest.approx(4)


def test_slicer_exports_a_zone_only_on_slicer():
    parts, _ = build(FlangeParams(mesh="slicer"), PRINTER)
    zone = next(part for part in parts if part.name == "mesh_zone")
    assert zone.modifier_of == "outer"
    for mesh in ("wire", "grid", "honeycomb"):
        parts, _ = build(FlangeParams(mesh=mesh), PRINTER)
        assert "mesh_zone" not in [part.name for part in parts]


def test_zone_matches_the_opening():
    p = resolved(mesh="slicer")
    assert build_mesh_zone(p).Volume == pytest.approx(opening_area(p) * 1.2, rel=0.001)


def test_zone_leaves_out_bars_and_hubs():
    p = resolved(mesh="slicer", fixing="centre_bolt")
    zone = build_mesh_zone(p)
    assert zone.Volume == pytest.approx(area_after_bars(p) * 1.2, rel=0.03)
    assert not solid_at(zone, 0, 0, 0.6)
    assert not solid_at(zone, 12, 0, 0.6)
    assert solid_at(zone, 12, 12, 0.6)


def test_zone_with_no_opening_left_is_refused():
    p = resolved(mesh="slicer", fixing="centre_bolt", opening_d=12, bar_width=13, force=True)
    with pytest.raises(GeometryError, match="mesh zone"):
        build_mesh_zone(p)


def test_slot_zone_has_four_regions():
    p = resolved(mesh="slicer", fixing="centre_bolt", shape="slot")
    assert len(build_mesh_zone(p).Solids) == 4


def test_zone_lines_up_on_the_bed(tmp_path):
    parts, _ = build(FlangeParams(mesh="slicer"), PRINTER)
    export(parts, tmp_path, title="t", params={}, printer=PRINTER, notes=[])
    outer = Mesh.Mesh(str(tmp_path / "outer.stl")).BoundBox
    zone = Mesh.Mesh(str(tmp_path / "mesh_zone.stl")).BoundBox
    assert (zone.Center.x, zone.Center.y) == pytest.approx((outer.Center.x, outer.Center.y), abs=0.01)
    assert zone.ZMin == pytest.approx(outer.ZMin, abs=0.01)
    assert zone.XLength == pytest.approx(50, abs=0.01)


def test_forced_mesh_with_no_holes_still_builds():
    p = resolved(shape="slot", mesh="grid", mesh_hole=6, slot_width=10, slot_length=30, force=True)
    assert build_outer(p, CLEAR).isValid()


REFUSED_BUILDABLE = [v for k, v in REFUSED.items() if k != "too_many_cells"]


@pytest.mark.parametrize("kw,field", REFUSED_BUILDABLE)
def test_every_forced_refusal_builds_or_fails_cleanly(kw, field):
    try:
        build(FlangeParams(force=True, **kw), PRINTER)
    except (GeometryError, Part.OCCError):
        pass  # nothing to print, and run.py reports these as errors
