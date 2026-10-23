import pytest

from projects.shelf.params import ShelfParams, bracket_depth, effective, wall_offset
from tridi import REPO_ROOT
from tridi.params import ParamError, load_presets, resolve


def test_defaults_match_spec():
    p = ShelfParams()
    assert (p.width, p.depth, p.slab_thickness) == (200, 100, 4)
    assert (p.supports, p.mount, p.top_screws) == ("below", "screws", "under")


def test_adhesive_forces_full():
    p, notes = effective(ShelfParams(mount="adhesive", plate_style="pads"))
    assert p.plate_style == "full"
    assert any("full back plate" in n for n in notes)


def test_pads_cleat_refused():
    with pytest.raises(ParamError, match="not supported with the cleat"):
        effective(ShelfParams(mount="cleat", plate_style="pads"))


def test_max_reach():
    with pytest.raises(ParamError, match="top-screws strip"):
        effective(ShelfParams(depth=160))
    effective(ShelfParams(depth=160, top_screws="strip"))
    effective(ShelfParams(depth=160, supports="above"))


def test_max_reach_counts_lip():
    with pytest.raises(ParamError, match="top-screws strip"):
        effective(ShelfParams(depth=145, front_lip=6))


def test_bad_notch():
    with pytest.raises(ParamError, match="back@x"):
        effective(ShelfParams(notches=("back@x",)))
    with pytest.raises(ParamError, match="back-left"):
        effective(ShelfParams(notches=("back-left", "back-left")))


def test_head_smaller_than_screw():
    with pytest.raises(ParamError, match="screw_head_d"):
        effective(ShelfParams(screw_d=6, screw_head_d=6))


def test_web_too_wide():
    with pytest.raises(ParamError, match="bracket_web"):
        effective(ShelfParams(bracket_web=28))


def test_bracket_too_deep():
    with pytest.raises(ParamError, match="bracket_depth"):
        effective(ShelfParams(bracket_depth=99))


def test_derived_values():
    assert bracket_depth(ShelfParams()) == 75
    assert wall_offset(ShelfParams()) == 0
    assert wall_offset(ShelfParams(mount="cleat")) == 8


def test_presets_resolve():
    presets = load_presets(REPO_ROOT / "projects/shelf/presets.toml", REPO_ROOT / "missing.toml", "shelf")
    assert set(presets) == {"corner", "lean", "hanging"}
    for name in presets:
        effective(resolve(ShelfParams, presets, name, {}))
