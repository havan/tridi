import pytest

import tridi  # noqa: F401
import Part
from FreeCAD import Vector as V

from projects.shelf.cleat import build_cleat, cleat_holes
from projects.shelf.layout import LayoutError, plan
from projects.shelf.params import ShelfParams, effective


def inside(shape, x, y, z):
    return shape.isInside(V(x, y, z), 1e-6, True)


def _p(**kw):
    p = effective(ShelfParams(**kw))[0]
    return p, plan(p)


def test_keyhole_valid_and_slot(build):
    body = build(mount="keyhole")
    assert body.isValid() and len(body.Solids) == 1
    _, lay = _p(mount="keyhole")
    for x, z in lay.holes:
        assert not inside(body, x, 1, z)  # the slot is open through the plate
        assert not inside(body, x, 1, z - 8)  # entry hole, head diameter below the screw
        assert not inside(body, x + 4, 4 + 1.5, z - 4)  # head channel in front of the plate
        assert inside(body, x, 4 + 3.5 + 0.8, z)  # closed front skin
        assert inside(body, x + 3, 2, z)  # plate material beside the slot holds the screw head


def test_adhesive_no_holes_taller(build):
    body = build(mount="adhesive")
    assert body.optimalBoundingBox().ZMin == pytest.approx(-84, abs=0.01)
    for x, z in _p()[1].holes:
        assert body.common(Part.makeCylinder(0.5, 6, V(x, -1, z), V(0, 1, 0))).Volume > 0


def test_glue_grooves_reduce_volume(build):
    plain, grooved = build(mount="adhesive"), build(mount="adhesive", glue_grooves=True)
    assert grooved.Volume < plain.Volume
    assert any(not inside(grooved, 100, 0.5, z / 2) for z in range(-80, -66))  # a groove within 7 mm


def test_cleat_parts_mate(build):
    p, lay = _p(mount="cleat")
    body, cleat = build(mount="cleat"), build_cleat(p, lay)
    assert cleat.isValid() and len(cleat.Solids) == 1
    assert body.common(cleat).Volume < 0.01
    # midway along the bevel (y = 4) the hook sits just above the cleat
    top = lay.plate_z[1]
    bevel_z = top - lay.hook_height + (8 - 4)
    assert inside(body, 100, 4, bevel_z + 0.3)
    assert inside(cleat, 100, 4, bevel_z - 0.6)
    assert not inside(body, 100, 4, bevel_z - 0.1) and not inside(cleat, 100, 4, bevel_z - 0.1)


def test_cleat_wall_offset(build):
    body = build(mount="cleat")
    assert body.optimalBoundingBox().YMin == pytest.approx(0, abs=0.01)
    assert not inside(body, 100, 4, -20)  # nothing behind the plate between hook and spacer...
    assert inside(body, 100, 9, -20)  # ...the plate starts 8 mm out


def test_cleat_holes():
    assert len(cleat_holes(*_p(mount="cleat"))) == 3
    assert len(cleat_holes(*_p(mount="cleat", width=400))) >= 4


def test_cleat_holes_avoid_notches():
    p, lay = _p(mount="cleat", notches=("back@100",))
    for x in cleat_holes(p, lay):
        assert abs(x - 100) >= 7 + 4.25


def test_cleat_cut_by_notch():
    p, lay = _p(mount="cleat", notches=("back@100",))
    cleat = build_cleat(p, lay)
    assert len(cleat.Solids) == 2 and all(s.isValid() for s in cleat.Solids)
    z_mid = cleat.optimalBoundingBox().Center.z
    assert not any(inside(s, 100, 4, z_mid) for s in cleat.Solids)
    holes = cleat_holes(p, lay)
    assert sum(x < 100 for x in holes) >= 2 and sum(x > 100 for x in holes) >= 2


def test_cleat_corner_notch_trims_end():
    p, lay = _p(mount="cleat", notches=("back-left",))
    cleat = build_cleat(p, lay)
    assert len(cleat.Solids) == 1
    assert min(cleat_holes(p, lay)) >= 23 + 4.25


def test_cleat_plate_too_short():
    with pytest.raises(LayoutError, match="cleat"):
        _p(mount="cleat", bracket_height=30)
