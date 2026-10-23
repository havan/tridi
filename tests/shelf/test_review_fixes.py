"""Inputs found by the final review: each must build a valid part or be refused with a message."""
import pytest

import tridi  # noqa: F401
import Part

from projects.shelf import build
from projects.shelf.layout import LayoutError, plan
from projects.shelf.params import ShelfParams, effective
from tridi.export import to_bed
from tridi.params import ParamError, load_presets
from tridi.printers import load_printers

MK3S = load_printers()["mk3s"]


def single(shape):
    assert shape.isValid() and len(shape.Solids) == 1
    return shape


@pytest.mark.parametrize("kw", [dict(plate_thickness=2), dict(edge_radius=3.6), dict(edge_radius=4),
                                dict(edge_radius=5, slab_thickness=12), dict(front_lip=0.5)])
def test_thin_or_round_values_build(build, kw):
    single(build(**kw))


def test_keyhole_not_limited_by_reach():
    effective(ShelfParams(mount="keyhole", depth=200))


def test_above_pads_stay_within_width():
    for a, b in plan(effective(ShelfParams(supports="above", plate_style="pads"))[0]).pads:
        assert a >= 0 and b <= 200


def _clip_clear(p):
    parts, _ = build(p, MK3S)
    shelf = parts[0].shape
    clip = next(x for x in parts if x.name == "clip").shape
    return shelf.common(clip).Volume


@pytest.mark.parametrize("kw", [dict(), dict(front_lip=6), dict(supports="above"), dict(supports="above", front_lip=6),
                                dict(depth=50, supports="above"), dict(notches=("back-right",), front_lip=6)])
def test_clip_assembly_fits_shelf(kw):
    assert _clip_clear(ShelfParams(clips=1, **kw)) < 0.01


def test_clip_no_free_edge_refused():
    with pytest.raises(LayoutError, match="clip"):
        build(ShelfParams(clips=1, supports="above", depth=60, front_lip=6), MK3S)


@pytest.mark.parametrize("text", ["[shelf]\nwidth = 180\n", "[desk]\nwidth = 180\n", "[shelf.desk\nwidth=1\n"])
def test_malformed_local_toml(tmp_path, text):
    local = tmp_path / "local.toml"
    local.write_text(text)
    with pytest.raises(ParamError, match="local.toml"):
        load_presets(tmp_path / "none.toml", local, "shelf")


def test_above_screws_reach_refused():
    with pytest.raises(ParamError, match="reach"):
        effective(ShelfParams(supports="above", depth=250))


def test_above_tall_lip_moves_bottom_holes_up():
    l = plan(effective(ShelfParams(supports="above", front_lip=12))[0])
    assert min(z for _, z in l.holes) >= 12 + 4


def test_side_orientation_no_flat_ceilings():
    parts, _ = build(ShelfParams(orientation="side"), MK3S)
    bed = to_bed(parts[0].shape, parts[0].rotation)
    overhang = 0.0
    for f in bed.Faces:
        u0, u1, v0, v1 = f.ParameterRange
        n = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
        if n.z < -0.75 and f.BoundBox.ZMin > 0.5:  # facing down steeper than ~45°, off the bed
            overhang += f.Area
    assert overhang < 50


@pytest.mark.parametrize("kw", [dict(plate_style="pads"), dict(mount="keyhole")])
def test_side_orientation_refuses_unprintable(kw):
    with pytest.raises(ParamError, match="side"):
        effective(ShelfParams(orientation="side", **kw))
