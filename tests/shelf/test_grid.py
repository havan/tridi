import itertools

import pytest

import tridi  # noqa: F401
from projects.shelf import build
from projects.shelf.params import ShelfParams
from tridi.export import to_bed
from tridi.printers import check_fit, load_printers

MK3S = load_printers()["mk3s"]
COMBOS = [c for c in itertools.product(("below", "above"), ("screws", "keyhole", "cleat", "adhesive"),
                                       ("full", "windowed", "pads"), ("solid", "honeycomb"))
          if not (c[1] == "cleat" and c[2] == "pads")]


def check_parts(parts):
    for part in parts:
        assert part.shape.isValid(), part.name
        assert all(s.isValid() for s in part.shape.Solids)
        if part.name != "cleat":  # a back notch may split the cleat into pieces
            assert len(part.shape.Solids) == 1, part.name
        bb = to_bed(part.shape, part.rotation).optimalBoundingBox()
        check_fit(part.name, (bb.XLength, bb.YLength, bb.ZLength), MK3S)


@pytest.mark.parametrize("supports,mount,plate_style,surface", COMBOS)
def test_grid(supports, mount, plate_style, surface):
    p = ShelfParams(supports=supports, mount=mount, plate_style=plate_style, surface=surface,
                    notches=("back-right",), front_lip=6)
    parts, _ = build(p, MK3S)
    check_parts(parts)


def test_everything_on():
    p = ShelfParams(supports="above", mount="cleat", plate_style="windowed", surface="honeycomb",
                    notches=("back-left", "back@150"), front_lip=6, clips=2)
    parts, _ = build(p, MK3S)
    assert [x.name for x in parts] == ["shelf", "cleat", "clip"]
    assert parts[2].count == 2
    check_parts(parts)


def test_side_orientation():
    parts, _ = build(ShelfParams(orientation="side"), MK3S)
    assert to_bed(parts[0].shape, parts[0].rotation).optimalBoundingBox().ZLength == pytest.approx(200, abs=0.01)


def test_notes_passed_on():
    _, notes = build(ShelfParams(mount="adhesive", plate_style="pads"), MK3S)
    assert any("full back plate" in n for n in notes)
