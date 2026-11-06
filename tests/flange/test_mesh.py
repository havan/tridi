import math

import pytest

import tridi  # noqa: F401
import Mesh
import MeshPart
import Part
from FreeCAD import Vector as V

from projects.flange import build
from projects.flange.layout import area_after_bars, mesh_cells, open_area, opening_area
from projects.flange.params import FlangeParams, effective
from projects.flange.parts import build_inner, build_mesh_zone, build_outer
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


# ---- a mesh that runs to the edge


@pytest.fixture(scope="module")
def to_edge():
    return build_outer(resolved(mesh="grid", mesh_to_edge=True), CLEAR)


def lattice_point(u, v):
    """A point in the default grid's own axes, which sit at 45°."""
    return (u - v) * math.sqrt(0.5), (u + v) * math.sqrt(0.5)


def test_a_clipped_hole_opens_right_up_to_the_edge(to_edge, grid):
    # the hole 11 lattice steps out, at v = 25.3, spans v = 24.55 to 26.05: the edge at 25 clips it
    x, y = lattice_point(0, 24.9)
    assert not solid_at(to_edge, x, y, 0.6)
    assert solid_at(grid, x, y, 0.6)


def test_the_rim_is_solid_just_past_a_clipped_hole(to_edge):
    x, y = lattice_point(0, 25.1)
    assert solid_at(to_edge, x, y, 0.6)


def test_the_ribs_reach_the_edge(to_edge):
    # the rib between holes runs along u = 1.15
    x, y = lattice_point(1.15, math.sqrt(24.9 ** 2 - 1.15 ** 2))
    assert solid_at(to_edge, x, y, 0.6)


def test_a_clipped_hole_is_only_in_the_mesh_layer_so_the_rim_stays_whole(to_edge):
    x, y = lattice_point(0, 25.1)
    assert solid_at(to_edge, x, y, 3)


def test_the_volume_taken_out_matches_the_open_area(to_edge):
    plain = build_outer(resolved(mesh="slicer"), CLEAR)
    p = resolved(mesh="grid", mesh_to_edge=True)
    assert plain.Volume - to_edge.Volume == pytest.approx(open_area(p) * 1.2, rel=0.01)


def test_clipped_holes_leave_the_bars_and_hubs_whole():
    piece = build_outer(resolved(mesh="grid", fixing="centre_bolt", mesh_to_edge=True), CLEAR)
    assert solid_at(piece, 12, 3.9, 0.6) and solid_at(piece, 12, 3.9, 3)  # a bar, 8 mm wide
    assert solid_at(piece, 6.9, 0, 0.6) and solid_at(piece, 6.9, 0, 3)  # the hub, 14 mm wide


@pytest.mark.parametrize("kw", [
    dict(mesh="grid"), dict(mesh="honeycomb"), dict(mesh="grid", fixing="centre_bolt"),
    dict(mesh="honeycomb", fixing="centre_bolt"), dict(mesh="grid", fixing="one_piece"),
    dict(mesh="grid", shape="slot"), dict(mesh="honeycomb", shape="slot", fixing="centre_bolt"),
    dict(mesh="grid", mesh_angle=0), dict(mesh="grid", mesh_angle=17), dict(mesh="honeycomb", mesh_angle=30),
    dict(mesh="grid", mesh_hole=4, mesh_rib=1.5),
    dict(mesh="grid", mesh_hole=6, mesh_rib=1, fixing="centre_bolt", force=True),
    dict(mesh="grid", mesh_thickness=4), dict(mesh="grid", bed_chamfer=0), dict(mesh="grid", seal_thickness=2),
])
def test_a_mesh_to_the_edge_is_one_watertight_solid(kw):
    shape = build_outer(resolved(mesh_to_edge=True, **kw), CLEAR)
    assert shape.isValid() and len(shape.Solids) == 1
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.2618)
    assert mesh.isSolid() and not mesh.hasNonManifolds()  # a valid shape can still mesh with a seam left open


# ---- wire mesh clamped behind a printed mesh


@pytest.mark.parametrize("kw", [dict(mesh="grid"), dict(mesh="grid", mesh_to_edge=True),
                                dict(mesh="honeycomb", fixing="centre_bolt", mesh_to_edge=True), dict(mesh="slicer")])
def test_added_wire_moves_the_outer_piece_without_changing_its_shape(kw):
    plain = build_outer(resolved(**kw), CLEAR)
    lifted = build_outer(resolved(add_wire=True, **kw), CLEAR)
    assert lifted.BoundBox.ZMin == pytest.approx(0.5)
    assert lifted.Volume == pytest.approx(plain.Volume, rel=1e-6)
    lifted.translate(V(0, 0, -0.5))
    assert lifted.cut(plain).Volume == pytest.approx(0, abs=1e-3)


def test_added_wire_leaves_the_inner_piece_as_it_was():
    for kw in (dict(mesh="grid"), dict(mesh="grid", fixing="centre_bolt")):
        plain = build_inner(resolved(**kw), CLEAR)
        wired = build_inner(resolved(add_wire=True, **kw), CLEAR)
        assert wired.Volume == pytest.approx(plain.Volume, rel=1e-9)
        assert wired.BoundBox.ZMax == pytest.approx(plain.BoundBox.ZMax)


def test_the_slicer_zone_moves_with_the_outer_piece():
    assert build_mesh_zone(resolved(mesh="slicer", add_wire=True)).BoundBox.ZMin == pytest.approx(0.5)


def test_hubs_leave_their_gap_with_the_wire_in_place():
    # outer hub at z = 0.5, inner hub's top at -2 + 1.5 = -0.5: 1 mm apart, less the 0.5 mm wire leaves the 0.5 mm gap
    p = resolved(mesh="grid", fixing="centre_bolt", add_wire=True)
    assert build_outer(p, CLEAR).BoundBox.ZMin == pytest.approx(0.5)
    assert build_inner(p, CLEAR).BoundBox.ZMax == pytest.approx(-0.3)  # the collar stands above the hub stop
    assert solid_at(build_inner(p, CLEAR), 5, 0, -0.6) and not solid_at(build_inner(p, CLEAR), 5, 0, -0.4)


@pytest.mark.parametrize("kw", [dict(mesh="grid", mesh_to_edge=True), dict(mesh="honeycomb"),
                                dict(mesh="grid", fixing="centre_bolt", mesh_to_edge=True),
                                dict(mesh="grid", fixing="one_piece", mesh_to_edge=True)])
def test_a_mesh_with_added_wire_is_one_watertight_solid(kw):
    shape = build_outer(resolved(add_wire=True, **kw), CLEAR)
    assert shape.isValid() and len(shape.Solids) == 1
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.2618)
    assert mesh.isSolid() and not mesh.hasNonManifolds()


def test_added_wire_prints_on_the_bed_all_the_same(tmp_path):
    parts, _ = build(FlangeParams(mesh="grid", add_wire=True), PRINTER)
    export(parts, tmp_path, title="t", params={}, printer=PRINTER, notes=[])
    assert Mesh.Mesh(str(tmp_path / "outer.stl")).BoundBox.ZMin == pytest.approx(0, abs=0.01)


REFUSED_BUILDABLE = [v for k, v in REFUSED.items() if k != "too_many_cells"]


@pytest.mark.parametrize("kw,field", REFUSED_BUILDABLE)
def test_every_forced_refusal_builds_or_fails_cleanly(kw, field):
    try:
        build(FlangeParams(force=True, **kw), PRINTER)
    except (GeometryError, Part.OCCError):
        pass  # nothing to print, and run.py reports these as errors
