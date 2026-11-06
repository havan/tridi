import itertools

import pytest

from projects.flange.layout import mesh_cells
from projects.flange.params import (FlangeParams, bolt_count, bolt_length, check_printer, effective, outer_z0,
                                    wall_hole)
from tridi.params import ParamError
from tridi.printers import Printer

NOZZLE_04 = Printer("t", "Test", 300, 300, 300, nozzle=0.4)


def resolved(**kw):
    return effective(FlangeParams(**kw))[0]


def notes(**kw):
    return effective(FlangeParams(**kw))[1]


@pytest.mark.parametrize("shape,fixing,mesh", list(itertools.product(("round", "slot"),
                                                                     ("two_piece", "one_piece", "centre_bolt"),
                                                                     ("wire", "grid", "honeycomb", "slicer"))))
def test_every_default_combination_resolves(shape, fixing, mesh):
    resolved(shape=shape, fixing=fixing, mesh=mesh)


def test_auto_values():
    assert resolved().collar_height == pytest.approx(1.7)
    assert resolved(fixing="centre_bolt").hub_stop == pytest.approx(2.0)
    assert resolved(fixing="centre_bolt", mesh="grid").hub_stop == pytest.approx(1.5)
    assert resolved(fixing="one_piece").collar_height == 0
    assert resolved().hub_stop == 0
    assert resolved(mesh="grid").mesh_angle == 45
    assert resolved(mesh="honeycomb").mesh_angle == 0


@pytest.mark.parametrize("fixing", ["two_piece", "one_piece", "centre_bolt"])
@pytest.mark.parametrize("mesh", ["wire", "grid"])
def test_bolt_lengths(fixing, mesh):
    assert bolt_length(resolved(fixing=fixing, mesh=mesh)) == 12


def test_thick_wall_follows():
    p = resolved(wall_thickness=6)
    assert p.collar_height == pytest.approx(5.7)
    assert bolt_length(p) == 16
    assert resolved(wall_thickness=6, fixing="centre_bolt").hub_stop == pytest.approx(6.0)


def test_seal_adds_to_the_stack():
    assert outer_z0(resolved(seal_thickness=2)) == pytest.approx(2.5)
    assert resolved(fixing="centre_bolt", seal_thickness=2).hub_stop == pytest.approx(4.0)
    assert bolt_length(resolved(seal_thickness=2)) == 16


def test_wall_hole():
    assert wall_hole(resolved()) == pytest.approx((53.6, 53.6))
    assert wall_hole(resolved(collar_height=0)) == pytest.approx((50, 50))
    assert wall_hole(resolved(fixing="one_piece")) == pytest.approx((50, 50))
    assert wall_hole(resolved(shape="slot")) == pytest.approx((193.6, 24.6))


def test_bolt_count():
    assert bolt_count(resolved()) == 4
    assert bolt_count(resolved(shape="slot")) == 8
    assert bolt_count(resolved(fixing="centre_bolt")) == 1
    assert bolt_count(resolved(shape="slot", fixing="centre_bolt")) == 3


REFUSED = {
    "odd_bolts_on_slot": (dict(shape="slot", rim_bolts=7), "rim_bolts"),
    "two_bolts_on_round": (dict(rim_bolts=2), "rim_bolts"),
    "collar_as_tall_as_the_wall": (dict(collar_height=2), "collar_height"),
    "hub_stop_with_no_gap": (dict(fixing="centre_bolt", hub_stop=2.5), "hub_stop"),
    "hubs_on_round": (dict(hubs=2), "hubs"),
    "hubs_that_overlap": (dict(shape="slot", fixing="centre_bolt", hubs=12), "hubs"),
    "hub_wider_than_slot": (dict(shape="slot", fixing="centre_bolt", hub_d=20), "hub_d"),
    "hub_filling_the_opening": (dict(fixing="centre_bolt", opening_d=14), "opening_d"),
    "slot_not_longer_than_wide": (dict(shape="slot", slot_length=21), "slot_length"),
    "rim_too_narrow_for_head": (dict(rim=8), "rim"),
    "rim_too_narrow_for_collar": (dict(fixing="centre_bolt", rim=5, collar_wall=3.5), "rim"),
    "bolts_too_close": (dict(rim_bolts=32), "rim_bolts"),
    "outer_too_thin_for_seat": (dict(outer_thickness=3), "outer_thickness"),
    "inner_too_thin_for_nut": (dict(inner_thickness=3.5), "inner_thickness"),
    "mesh_thicker_than_piece": (dict(mesh="grid", mesh_thickness=5), "mesh_thickness"),
    "no_holes": (dict(shape="slot", mesh="grid", mesh_hole=6, slot_width=10, slot_length=30), "mesh_hole"),
    "bars_leaving_no_room_for_holes": (dict(fixing="centre_bolt", mesh="grid", opening_d=20), "mesh_hole"),
    "too_many_cells": (dict(mesh="grid", opening_d=300, mesh_hole=0.5, mesh_rib=0.4), "mesh_hole"),
}


@pytest.mark.parametrize("kw,field", REFUSED.values(), ids=REFUSED.keys())
def test_refused(kw, field):
    with pytest.raises(ParamError, match=field):
        effective(FlangeParams(**kw))


def test_too_many_cells_names_the_count():
    p = FlangeParams(mesh="grid", opening_d=300, mesh_hole=0.5, mesh_rib=0.4)
    with pytest.raises(ParamError, match=r"\d{5,} holes"):
        effective(p)


def test_refusal_message_mentions_force():
    with pytest.raises(ParamError, match="--force"):
        effective(FlangeParams(shape="slot", rim_bolts=7))


@pytest.mark.parametrize("kw,field", REFUSED.values(), ids=REFUSED.keys())
def test_force_turns_refusals_into_notes(kw, field):
    _, out = effective(FlangeParams(force=True, **kw))
    assert any(n.startswith("forced:") and field in n for n in out)


def test_no_forced_notes_without_a_problem():
    assert not any(n.startswith("forced:") for n in notes(force=True))


def test_rib_thinner_than_nozzle_refused():
    with pytest.raises(ParamError, match="mesh_rib"):
        check_printer(resolved(mesh="grid", mesh_rib=0.3), NOZZLE_04)
    assert check_printer(resolved(mesh="grid"), NOZZLE_04) == []
    assert check_printer(resolved(mesh_rib=0.3), NOZZLE_04) == []


def test_force_overrules_the_nozzle_check():
    out = check_printer(resolved(mesh="grid", mesh_rib=0.3, force=True), NOZZLE_04)
    assert len(out) == 1 and out[0].startswith("forced:") and "mesh_rib" in out[0]


def test_large_hole_builds_with_a_note():
    assert any("flies" in n for n in notes(mesh="grid", mesh_hole=2.5))
    assert not any("flies" in n for n in notes(mesh="grid"))


@pytest.mark.parametrize("kw", [dict(shape="slot", fixing="centre_bolt", hubs=0), dict(rim_bolts=0),
                                dict(shape="slot", rim_bolts=0)])
def test_forced_silly_counts_become_notes_not_crashes(kw):
    _, out = effective(FlangeParams(force=True, **kw))
    assert any(n.startswith("forced:") for n in out)


def test_forced_no_cells_still_resolves():
    p = resolved(shape="slot", mesh="grid", mesh_hole=6, slot_width=10, slot_length=30, force=True)
    assert mesh_cells(p) == []


def _note(key, **kw):
    return next(n for n in notes(**kw) if n.startswith(key))


def test_notes_list_what_to_cut():
    wall = _note("wall:")
    assert "53.6 mm" in wall and "4 × 4.5 mm" in wall
    assert "193.6 × 24.6 mm" in _note("wall:", shape="slot")
    assert "8 × 4.5 mm" in _note("wall:", shape="slot")
    assert "no bolt holes" in _note("wall:", fixing="centre_bolt")


def test_notes_list_what_to_buy():
    buy = _note("hardware:")
    assert "4 × M4×12" in buy and "4 × M4 nuts" in buy and "washers" not in buy and "76 × 76 mm" in buy
    assert "4 × M4 washers" in _note("hardware:", fixing="one_piece")
    assert "3 × M4×12" in _note("hardware:", shape="slot", fixing="centre_bolt")
    assert "216 × 47 mm" in _note("hardware:", shape="slot")
    assert "wire mesh" not in _note("hardware:", mesh="grid")


def test_notes_report_air():
    air = _note("air:", mesh="grid")
    assert "1963 mm²" in air and "731 mm²" in air and "37%" in air
    assert "1234 mm²" in _note("air:", fixing="centre_bolt")
    assert "60–70%" in _note("air:")
    assert "infill" in _note("air:", mesh="slicer")
