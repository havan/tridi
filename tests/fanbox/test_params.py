import pytest

import tridi  # noqa: F401
from projects.fanbox.params import (FanboxParams, effective, fan_bolt_length, lid_bolt_length, lid_bolt_xy,
                                    socket_size)
from tridi.params import ParamError


def resolved(**kw):
    return effective(FanboxParams(**kw))[0]


def test_defaults_match_the_agreed_140_mm_layout():
    p = resolved()
    assert (p.fan_size, p.fan_thickness, p.fan_hole_spacing) == (140, 25, 124.5)
    assert (p.base_width, p.base_length) == (90, 140)
    assert (p.base_width - 2 * p.wall, p.base_length - 2 * p.wall) == (84, 134)
    assert socket_size(p) == pytest.approx(145.4)
    assert p.base_length + 2 * p.ear_length == 176
    assert lid_bolt_xy(p) == (79, 35)


def test_base_length_follows_the_fan_when_not_given():
    assert resolved(fan_size=120).base_length == 120
    assert resolved(fan_size=92).base_length == 92


def test_explicit_base_length_wins_over_the_fan_size():
    assert resolved(base_length=150).base_length == 150
    assert resolved(fan_size=120, base_length=125).base_length == 125


@pytest.mark.parametrize("size, spacing", [(80, 71.5), (92, 82.5), (120, 105), (140, 124.5), (200, 154)])
def test_hole_spacing_follows_the_standard_fan_sizes(size, spacing):
    assert resolved(fan_size=size, lid_flat_length=400, duct_height=80).fan_hole_spacing == spacing


def test_explicit_hole_spacing_wins():
    assert resolved(fan_hole_spacing=120).fan_hole_spacing == 120


def test_non_standard_fan_needs_its_hole_spacing():
    with pytest.raises(ParamError, match="fan_hole_spacing"):
        resolved(fan_size=130)
    assert resolved(fan_size=130, fan_hole_spacing=115).fan_hole_spacing == 115


def test_bore_and_frame_opening_follow_the_fan():
    p = resolved(fan_size=120)
    assert (p.fan_bore, p.frame_opening) == (116, 112)


def test_cable_notch_position_follows_the_fan():
    assert resolved().cable_offset == -35
    assert resolved(fan_size=80).cable_offset == -20


def test_explicit_cable_offset_wins():
    assert resolved(cable_offset=0).cable_offset == 0


def test_resolving_twice_changes_nothing():
    p = resolved(fan_size=120)
    assert effective(p)[0] == p


def test_default_bolts_are_stock_lengths():
    p = FanboxParams()
    assert lid_bolt_length(p) == 16
    assert fan_bolt_length(p) == 40


def test_thicker_fan_takes_longer_bolts():
    assert fan_bolt_length(FanboxParams(fan_thickness=38)) == 55


def test_mesh_lift_takes_longer_bolts():
    assert fan_bolt_length(FanboxParams(mesh_lift=1)) == 45


def test_thicker_lid_takes_longer_bolts():
    assert lid_bolt_length(FanboxParams(lid_thickness=6)) == 20


def test_notes_list_the_hardware_and_the_resolved_sizes():
    notes = " ".join(effective(FanboxParams(fan_size=120))[1])
    assert "4 × M4×16" in notes and "4 × M4×40" in notes and "8 × M4 nuts" in notes
    assert "120 × 90" in notes and "105" in notes


def test_base_wider_than_the_flat_lid_area_is_refused():
    with pytest.raises(ParamError, match="flat area"):
        resolved(base_width=96)


def test_base_longer_than_the_flat_lid_area_is_refused():
    with pytest.raises(ParamError, match="flat area"):
        resolved(lid_flat_length=170)


def test_duct_too_short_to_print_without_supports_is_refused():
    with pytest.raises(ParamError, match="45°"):
        resolved(base_width=50, duct_height=30)


def test_bolt_head_under_the_socket_is_refused():
    # the hex key comes straight down from above, so the head has to clear the socket's outside
    with pytest.raises(ParamError, match="hex key"):
        resolved(ear_length=6)
    with pytest.raises(ParamError, match="hex key"):
        resolved(base_length=120)


def test_flange_too_thin_for_the_countersink_is_refused():
    with pytest.raises(ParamError, match="countersink"):
        resolved(frame_thickness=3)


def test_frame_opening_wider_than_the_fan_bore_is_refused():
    with pytest.raises(ParamError, match="frame_opening"):
        resolved(frame_opening=137)


def test_bore_leaving_no_seat_for_the_fan_is_refused():
    with pytest.raises(ParamError, match="fan_bore"):
        resolved(fan_bore=138)


def test_cable_notch_off_the_flat_of_the_side_is_refused():
    with pytest.raises(ParamError, match="cable"):
        resolved(cable_offset=-68)


def test_cable_notch_deeper_than_the_socket_is_refused():
    with pytest.raises(ParamError, match="cable"):
        resolved(cable_notch_depth=30)


def test_frame_bolts_landing_in_the_frame_opening_are_refused():
    with pytest.raises(ParamError, match="frame_opening"):
        resolved(fan_hole_spacing=90)
