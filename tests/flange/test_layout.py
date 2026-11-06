import math

import pytest

from projects.flange.layout import (area_after_bars, bar_segments, cell_circumradius, hub_xy, mesh_cells, open_area,
                                    opening_area, outer_size, rim_bolt_xy, spine, spine_distance)
from projects.flange.params import FlangeParams, effective


def resolved(**kw):
    return effective(FlangeParams(**kw))[0]


def test_default_sizes():
    assert outer_size(resolved()) == pytest.approx((78, 78))
    assert outer_size(resolved(shape="slot")) == pytest.approx((218, 49))
    assert outer_size(resolved(fixing="centre_bolt")) == pytest.approx((66, 66))
    assert outer_size(resolved(shape="slot", fixing="centre_bolt")) == pytest.approx((206, 37))


def test_opening_areas():
    assert opening_area(resolved()) == pytest.approx(math.pi * 625)
    assert opening_area(resolved(shape="slot")) == pytest.approx(3895, abs=1)


def test_round_bolts_are_evenly_spaced_starting_at_the_top():
    bolts = rim_bolt_xy(resolved(rim_bolts=3))
    assert len(bolts) == 3
    assert bolts[0] == pytest.approx((0, 32))
    assert all(math.hypot(x, y) == pytest.approx(32) for x, y in bolts)
    assert sum(x for x, _ in bolts) == pytest.approx(0, abs=1e-9)
    assert sum(y for _, y in bolts) == pytest.approx(0, abs=1e-9)


def test_default_slot_bolts_match_the_sketch():
    bolts = rim_bolt_xy(resolved(shape="slot"))
    assert len(bolts) == 8
    ends = sorted(x for x, y in bolts if abs(y) < 1e-6)
    assert ends == pytest.approx([-102, 102])
    for side in (17.5, -17.5):
        xs = sorted(x for x, y in bolts if abs(y - side) < 1e-6)
        assert xs == pytest.approx([-56, 0, 56], abs=0.1)


@pytest.mark.parametrize("n", [4, 6, 10, 12])
def test_slot_bolts_are_symmetric_and_on_the_rims_middle(n):
    p = resolved(shape="slot", rim_bolts=n)
    bolts = rim_bolt_xy(p)
    assert len(bolts) == n
    assert all(spine_distance(x, y, 84.5) == pytest.approx(17.5) for x, y in bolts)
    assert sorted(round(x, 6) for x, _ in bolts) == sorted(round(-x, 6) for x, _ in bolts)
    assert sorted(round(y, 6) for _, y in bolts) == sorted(round(-y, 6) for _, y in bolts)


def test_slot_hubs_use_equal_pitch():
    hubs = hub_xy(resolved(shape="slot", fixing="centre_bolt"))
    assert [x for x, _ in hubs] == pytest.approx([-190 / 3, 0, 190 / 3])
    assert all(y == 0 for _, y in hubs)


def test_round_has_one_hub_in_the_middle():
    assert hub_xy(resolved(fixing="centre_bolt")) == [(0, 0)]


def test_round_bars():
    four = bar_segments(resolved(fixing="centre_bolt"))
    ends = sorted((round(b[0], 6), round(b[1], 6)) for _, b in four)
    assert ends == sorted([(0.0, 25.0), (0.0, -25.0), (25.0, 0.0), (-25.0, 0.0)])
    assert four[0][0] == pytest.approx((0, 7))
    three = bar_segments(resolved(fixing="centre_bolt", bars=3))
    assert len(three) == 3 and three[0][1] == pytest.approx((0, 25))
    two = bar_segments(resolved(fixing="centre_bolt", bars=2))
    assert sorted(round(b[0], 6) for _, b in two) == [-25.0, 25.0]


def test_slot_bars_cross_the_short_side():
    bars = bar_segments(resolved(shape="slot", fixing="centre_bolt"))
    assert len(bars) == 3
    assert bars[1][0] == pytest.approx((0, -10.5))
    assert bars[1][1] == pytest.approx((0, 10.5))


def test_no_bars_without_a_centre_bolt():
    assert bar_segments(resolved()) == []


def test_area_after_bars_is_never_negative():
    assert area_after_bars(resolved(fixing="centre_bolt", opening_d=12, hub_d=40, bars=4, force=True)) == 0


def test_area_after_bars():
    assert area_after_bars(resolved()) == pytest.approx(math.pi * 625)
    assert area_after_bars(resolved(fixing="centre_bolt")) == pytest.approx(1233.6, abs=0.1)


@pytest.mark.parametrize("kw,cells,area", [
    (dict(mesh="grid"), 325, 731),
    (dict(mesh="honeycomb"), 367, 715),
    (dict(mesh="grid", shape="slot"), 617, 1388),
])
def test_open_area_matches_measured_defaults(kw, cells, area):
    p = resolved(**kw)
    assert len(mesh_cells(p)) == pytest.approx(cells, abs=2)
    assert open_area(p) == pytest.approx(area, rel=0.01)


@pytest.mark.parametrize("kw,area", [
    (dict(mesh="grid", fixing="centre_bolt"), 333),
    (dict(mesh="grid", fixing="centre_bolt", shape="slot"), 1044),
])
def test_open_area_with_bars(kw, area):
    assert open_area(resolved(**kw)) == pytest.approx(area, rel=0.01)


def test_wire_and_slicer_have_no_cells():
    assert mesh_cells(resolved()) == []
    assert mesh_cells(resolved(mesh="slicer")) == []
    assert open_area(resolved()) == pytest.approx(math.pi * 625)


def _segment_distance(x, y, seg):
    (x0, y0), (x1, y1) = seg
    dx, dy = x1 - x0, y1 - y0
    t = max(0, min(1, ((x - x0) * dx + (y - y0) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - x0 - t * dx, y - y0 - t * dy)


@pytest.mark.parametrize("shape", ["round", "slot"])
@pytest.mark.parametrize("mesh", ["grid", "honeycomb"])
def test_cells_keep_a_rib_from_every_edge(shape, mesh):
    p = resolved(shape=shape, mesh=mesh, fixing="centre_bolt")
    r, s = spine(p)
    margin = cell_circumradius(p) + p.mesh_rib
    assert mesh_cells(p)
    for x, y in mesh_cells(p):
        assert spine_distance(x, y, s) + margin <= r + 1e-9
        for hx, hy in hub_xy(p):
            assert math.hypot(x - hx, y - hy) >= p.hub_d / 2 + margin - 1e-9
        for seg in bar_segments(p):
            assert _segment_distance(x, y, seg) >= p.bar_width / 2 + margin - 1e-9
