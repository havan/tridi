import math

import pytest

from projects.shelf.layout import LayoutError, plan
from projects.shelf.params import ShelfParams, effective


def lay(**kw):
    return plan(effective(ShelfParams(**kw))[0])


def test_default_brackets():
    assert lay().brackets == pytest.approx((200 / 6, 1000 / 6))


def test_default_holes():
    holes = [v for h in sorted(lay().holes) for v in h]
    expected = [v for h in sorted([(77.78, -14), (122.22, -14), (77.78, -49), (122.22, -49)]) for v in h]
    assert holes == pytest.approx(expected, abs=0.01)


def test_default_plate_and_slab():
    l = lay()
    assert l.slab_z == (-4, 0)
    assert l.plate_z == (-59, 0)
    assert l.hook_height == 0


def test_wide_shelf_brackets():
    b = lay(width=500).brackets
    assert len(b) == 4
    assert max(b2 - b1 for b1, b2 in zip(b, b[1:])) <= 160


def test_explicit_bracket_count():
    assert len(lay(bracket_count=3).brackets) == 3
    with pytest.raises(LayoutError, match="too many brackets"):
        lay(width=60, bracket_count=6)


def test_above_end_brackets():
    # the 195 mm span between end brackets is over the 160 mm gap rule, so a middle bracket is added
    l = lay(supports="above")
    assert l.brackets == pytest.approx((2.5, 100, 197.5))
    assert lay(supports="above", width=160).brackets == pytest.approx((2.5, 157.5))
    assert l.plate_z == (-4, 55)


def test_above_corner_notch_nudges():
    assert lay(supports="above", notches=("back-left",)).brackets[0] == pytest.approx(19.5)


def test_strip_rows():
    l = lay(top_screws="strip")
    assert l.plate_z[1] == 18
    assert max(z for _, z in l.holes) == pytest.approx(9)


def test_notch_collides_with_bracket():
    with pytest.raises(LayoutError, match=r"notch back@33 \(26.0–40.0 mm\) collides with bracket 1"):
        lay(notches=("back@33",))


def test_notch_outside_shelf():
    with pytest.raises(LayoutError, match="back@195"):
        lay(notches=("back@195",))


def test_notches_overlap():
    with pytest.raises(LayoutError, match="collides with notch"):
        lay(width=300, notches=("back-left", "back@20"))


def test_narrow_shelf_refuses_cleanly():
    with pytest.raises(LayoutError):
        lay(width=60)


def test_short_plate_refuses():
    with pytest.raises(LayoutError, match="too short"):
        lay(bracket_height=15)


def test_pads_columns():
    l = lay(plate_style="pads")
    assert len(l.pads) == 2
    xs = sorted({x for x, _ in l.holes})
    assert xs == pytest.approx([200 / 6 + 10.5, 1000 / 6 - 10.5])
    for (a, b), c in zip(l.pads, l.brackets):
        assert a < c - 2.5 and b > c + 2.5


def test_windowed_has_windows():
    l = lay(plate_style="windowed")
    assert l.windows
    for x0, z0, x1, z1 in l.windows:
        assert x1 - x0 >= 20 and z1 - z0 >= 20
        for c in l.brackets:
            assert x1 <= c - 2.5 or x0 >= c + 2.5


def test_windows_avoid_notches():
    l = lay(plate_style="windowed", notches=("back@100",))
    for x0, _, x1, _ in l.windows:
        assert x1 <= 93 - 10 or x0 >= 107 + 10


def test_windows_clear_cleat_hook():
    l = lay(plate_style="windowed", mount="cleat")
    assert all(z1 <= -(14 + 4) for _, _, _, z1 in l.windows)


def test_honeycomb_respects_rim():
    l = lay(surface="honeycomb")
    half_x, half_y = 5, 10 / math.sqrt(3)  # vertex along y
    assert len(l.hexes) > 50
    assert l.hex_vertex_axis == "y"
    for x, y in l.hexes:
        assert x - half_x >= 8 - 1e-9 and x + half_x <= 192 + 1e-9
        assert y - half_y >= 12 - 1e-9 and y + half_y <= 92 + 1e-9
        for c in l.brackets:
            assert x + half_x <= c - 6.5 + 1e-9 or x - half_x >= c + 6.5 - 1e-9


def test_honeycomb_side_orientation_axis():
    assert lay(surface="honeycomb", orientation="side").hex_vertex_axis == "x"


def test_honeycomb_clears_corner_notch():
    l = lay(surface="honeycomb", notches=("back-left",))
    half = 10 / math.sqrt(3)
    for x, y in l.hexes:
        nx, ny = max(x - 5, 0), max(y - half, 0)  # nearest point of the hex box to the corner (0, 0)
        assert math.hypot(nx, ny) >= 15 + 6 - 1e-9


def test_cleat_offset():
    l = lay(mount="cleat", notches=("back-left",))
    assert l.hook_height == 14
    assert l.holes == ()
    assert l.notches[0].r == 23


def test_adhesive_plate_longer():
    l = lay(mount="adhesive")
    assert l.plate_z == (-84, 0)
    assert l.holes == ()


def test_keyhole_rows_leave_room():
    l = lay(mount="keyhole")
    zs = sorted({z for _, z in l.holes})
    assert zs == pytest.approx([-41, -14])
    with pytest.raises(LayoutError, match="strip"):
        lay(mount="keyhole", top_screws="strip")
    assert lay(mount="keyhole", top_screws="strip", strip_height=26).holes


def test_above_corner_notch_clears_pad():
    l = lay(supports="above", plate_style="pads", notches=("back-right",))
    assert l.pads[-1][1] <= 200 - 15
