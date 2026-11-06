import pytest

from projects.grommet.params import (GrommetParams, effective, grip_span, root_d, slot_height, slot_width, stem_end,
                                     thread_d)
from tridi.params import ParamError


def resolved(**kw):
    return effective(GrommetParams(**kw))[0]


def test_default_sizes_follow_the_users_wire():
    p = resolved()
    assert (p.wire_shape, p.wire_width, p.wire_height, p.wall_thickness) == ("twin", 5, 2.5, 2)
    assert slot_width(p) == pytest.approx(5.2)
    assert slot_height(p) == pytest.approx(2.6)
    assert p.hole_d == 13
    assert thread_d(p) == pytest.approx(12.5)
    assert root_d(p) == pytest.approx(10.5)
    assert p.disc_d == pytest.approx(24.5)
    assert stem_end(p) == pytest.approx(13)


def test_nut_grows_to_hold_its_joint():
    assert resolved().nut_d == 21.5


def test_bigger_hole_grows_everything_but_the_slot():
    p = resolved(hole_d=20)
    assert thread_d(p) == pytest.approx(19.5)
    assert p.disc_d == pytest.approx(31.5)
    assert p.nut_d >= 27.5
    assert slot_width(p) == pytest.approx(5.2)


def test_thick_wall_lengthens_the_stem_only():
    p = resolved(wall_thickness=20)
    assert stem_end(p) == pytest.approx(2.5 + 20 + 7 + 1.5)
    assert p.hole_d == 13


def test_grip_sits_under_the_nut():
    p = resolved()
    z0, z1, ridges = grip_span(p)
    assert ridges == 2
    assert z0 >= 4.5 and z1 <= 11.5


@pytest.mark.parametrize("kw, name", [
    (dict(hole_d=10), "hole_d"),
    (dict(disc_d=14), "disc_d"),
    (dict(nut_d=16), "nut_d"),
    (dict(grip_squeeze=0.5), "grip_squeeze"),
    (dict(groove_rib=1.2), "groove_rib"),
    (dict(grip_pitch=3), "grip_pitch"),
    (dict(wire_width=2), "wire_width"),
])
def test_bad_sizes_are_refused_by_name(kw, name):
    with pytest.raises(ParamError, match=name):
        resolved(**kw)


def test_force_reports_a_refusal():
    _, notes = effective(GrommetParams(grip_squeeze=0.5, force=True))
    assert any(n.startswith("forced:") and "grip_squeeze" in n for n in notes)


def test_thick_round_wire_notes_too_few_ridges():
    p, notes = effective(GrommetParams(wire_shape="round", wire_d=10))
    assert grip_span(p)[2] == 1
    assert any("ridge" in n for n in notes)
