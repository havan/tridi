import math

import pytest

import tridi  # noqa: F401
import MeshPart
import Part
from FreeCAD import Vector as V

from projects.grommet import build
from projects.grommet.params import GrommetParams, effective, grip_span, nut_z0
from projects.grommet.parts import build_body, build_nut
from tridi.export import to_bed
from tridi.printers import get_printer, load_printers

PRINTER = get_printer("mk3s", load_printers())


def resolved(**kw):
    return effective(GrommetParams(**kw))[0]


@pytest.fixture(scope="module")
def parts():
    built, _ = build(GrommetParams(), PRINTER)
    return {part.name: part for part in built}


def test_four_valid_single_solids(parts):
    assert sorted(parts) == ["body_a", "body_b", "nut_a", "nut_b"]
    for part in parts.values():
        assert part.shape.isValid() and len(part.shape.Solids) == 1, part.name


def test_exported_mesh_matches_the_solid(parts):
    for part in parts.values():
        mesh = MeshPart.meshFromShape(Shape=part.shape, LinearDeflection=0.05, AngularDeflection=0.2618)
        assert mesh.isSolid(), part.name
        assert mesh.Volume == pytest.approx(part.shape.Volume, rel=0.01), part.name


def test_nut_pieces_carry_the_same_thread(parts):
    def thread_area(part):
        return sum(f.Area for f in part.shape.Faces if type(f.Surface).__name__ == "BSplineSurface")
    assert thread_area(parts["nut_a"]) == pytest.approx(thread_area(parts["nut_b"]), rel=0.05)


def test_assembled_parts_do_not_collide(parts):
    nut_volume = parts["nut_a"].shape.Volume
    for body, nut in (("body_a", "nut_a"), ("body_b", "nut_b")):
        assert parts[body].shape.common(parts[nut].shape).Volume < 0.01 * nut_volume, (body, nut)
    assert parts["body_a"].shape.common(parts["body_b"].shape).Volume < 0.5


def test_disc_and_nut_clamp_the_wall(parts):
    p = resolved()
    assert parts["nut_a"].shape.optimalBoundingBox(False, False).ZMin == pytest.approx(4.5, abs=1e-3)
    assert parts["nut_b"].shape.optimalBoundingBox(False, False).ZMin == pytest.approx(4.5, abs=1e-3)
    r = (p.hole_d + p.disc_d) / 4
    assert parts["body_a"].shape.isInside(V(0, r, 2.4), 1e-6, False)
    assert not parts["body_a"].shape.isInside(V(0, r, 2.6), 1e-6, False)
    assert nut_z0(p) - p.disc_thickness == 2


def _gap_at(body_a, body_b, x, z):
    """How far apart the two faces of the slot are, measured along y."""
    line = Part.makeLine(V(x, -6, z), V(x, 6, z))
    return line.common(body_a).BoundBox.YMin - line.common(body_b).BoundBox.YMax


def test_slot_squeezes_at_ridges_and_is_clear_elsewhere(parts):
    p = resolved()
    a, b = parts["body_a"].shape, parts["body_b"].shape
    z0, _, _ = grip_span(p)
    assert _gap_at(a, b, 1.5, z0 + p.grip_pitch / 4) == pytest.approx(2.3, abs=0.05)
    assert _gap_at(a, b, 1.5, z0 - 1) == pytest.approx(2.6, abs=0.05)


def test_twin_has_a_rib_in_the_groove(parts):
    a = parts["body_a"].shape
    assert a.isInside(V(0, 1.2, 3.5), 1e-6, False)
    assert not a.isInside(V(1.25, 1.2, 3.5), 1e-6, False)


@pytest.mark.parametrize("kw", [dict(hole_d=20), dict(wall_thickness=20), dict(wire_shape="round", wire_d=6),
                                dict(wire_shape="flat")])
def test_other_sizes_build(kw):
    p = resolved(**kw)
    for shape in (build_body(p, "a"), build_nut(p, "b")):
        assert shape.isValid() and len(shape.Solids) == 1


def _overhang_area(shape):
    """Area of mesh facing down more steeply than 50° from vertical, away from the bed."""
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.2618)
    zmin = shape.BoundBox.ZMin
    limit = -math.cos(math.radians(40))
    return sum(f.Area for f in mesh.Facets if f.Normal.z < limit and min(p[2] for p in f.Points) > zmin + 0.01)


# nut_b's two socket roofs are short bridges of about 5.5 mm² each, with 0.2 mm first-layer relief ledges around them.
@pytest.mark.parametrize("name, allowed", [("body_a", 5), ("nut_a", 5), ("nut_b", 18)])
def test_no_large_overhangs(parts, name, allowed):
    part = parts[name]
    assert _overhang_area(to_bed(part.shape, part.rotation)) < allowed
