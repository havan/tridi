import pytest

import tridi  # noqa: F401
from projects.barholder.params import (BarholderParams, bolt_length, bolt_xs, bolt_y, cradle_xs, effective,
                                       mouth_width, overall_length, strip_bottom, strip_top)
from tridi.params import ParamError


def notes(**kw):
    return "\n".join(effective(BarholderParams(**kw))[1])


def test_default_layout_is_the_agreed_three_bars_70_mm_apart():
    p = BarholderParams()
    assert cradle_xs(p) == [-70, 0, 70]
    assert bolt_xs(p) == pytest.approx([-88.5, -35, 35, 88.5])
    assert overall_length(p) == pytest.approx(193)


def test_a_single_cradle_has_only_the_two_end_bolts():
    p = BarholderParams(count=1)
    assert cradle_xs(p) == [0]
    assert bolt_xs(p) == pytest.approx([-18.5, 18.5])


def test_two_cradles_sit_either_side_of_a_middle_bolt():
    p = BarholderParams(count=2, pitch=60)
    assert cradle_xs(p) == [-30, 30]
    assert bolt_xs(p) == pytest.approx([-48.5, 0, 48.5])


def test_strip_hangs_below_the_bars_centre_with_bolts_on_its_midline():
    p = BarholderParams()
    assert (strip_top(p), strip_bottom(p), bolt_y(p)) == (-3, -19, -11)


@pytest.mark.parametrize("wrap, mouth", [(180, 20.6), (225, 19.03), (240, 17.84)])
def test_mouth_narrows_as_the_wrap_grows(wrap, mouth):
    assert mouth_width(BarholderParams(wrap=wrap)) == pytest.approx(mouth, abs=0.01)


def test_mouth_follows_the_bar_and_its_fit():
    assert mouth_width(BarholderParams(bar_d=30, bar_fit=0.5, wrap=180)) == pytest.approx(31)


def test_bolt_runs_through_plate_wall_and_nut_with_its_tip_inside_the_strip():
    assert bolt_length(BarholderParams()) == 12  # 4 + 2 + 2 + 3.2 + 1 - 0.5 = 11.7 -> stock 12
    assert bolt_length(BarholderParams(box_wall=3)) == 16


def test_without_a_backplate_the_bolt_only_spans_washer_wall_and_nut():
    assert bolt_length(BarholderParams(backplate=False)) == 10  # 1 + 2 + 2 + 3.2 + 1 = 9.2 -> stock 10


def test_notes_list_the_hardware_for_a_full_strip():
    text = notes()
    assert "4 × M4×12 countersunk" in text and "4 × M4 nuts" in text


def test_notes_ask_for_washers_when_the_backplate_is_off():
    text = notes(backplate=False)
    assert "M4×10" in text and "washer" in text and "countersunk" not in text


def test_notes_give_the_drilling_size_and_template():
    assert "4.5 mm" in notes() and "template" in notes()


def test_notes_give_the_bar_length_range_from_the_cradle_depth():
    text = notes(cradle_depth=25)
    assert "16 mm" in text and "30 mm" in text  # 2 × 8 mm strip; 2 × (25 - 10) mm


def test_notes_say_how_much_the_snap_squeezes_the_bar():
    assert "1.0 mm narrower" in notes()


@pytest.mark.parametrize("kw", [dict(wrap=180), dict(wrap=190, bar_fit=0.5)])
def test_notes_say_when_there_is_no_snap(kw):
    assert "no snap" in notes(**kw)


def test_a_pitch_too_tight_for_a_bolt_between_cradles_is_refused():
    with pytest.raises(ParamError, match="pitch"):
        effective(BarholderParams(pitch=30))


def test_pitch_does_not_matter_for_a_single_cradle():
    effective(BarholderParams(count=1, pitch=10))


def test_a_cradle_too_shallow_to_hold_the_bar_is_refused():
    with pytest.raises(ParamError, match="cradle_depth"):
        effective(BarholderParams(cradle_depth=15))


def test_a_bolt_that_would_poke_through_the_strip_is_refused():
    with pytest.raises(ParamError, match="strip_thickness"):
        effective(BarholderParams(box_wall=5))  # needs M4×16: tip 7.5 mm into an 8 mm strip, leaving no cap


def test_thick_walls_work_with_a_thicker_strip():
    effective(BarholderParams(box_wall=5, strip_thickness=9))


def test_a_strip_too_thin_for_the_nut_and_bolt_tip_is_refused():
    with pytest.raises(ParamError, match="strip_thickness"):
        effective(BarholderParams(strip_thickness=4))


def test_a_strip_too_narrow_for_the_nuts_and_heads_is_refused():
    with pytest.raises(ParamError, match="strip_height"):
        effective(BarholderParams(strip_height=11))


def test_a_plate_too_thin_for_the_countersink_is_refused():
    with pytest.raises(ParamError, match="plate_thickness"):
        effective(BarholderParams(plate_thickness=3))


def test_a_thin_plate_is_fine_when_there_is_no_plate():
    effective(BarholderParams(plate_thickness=3, backplate=False))


def test_a_strip_top_too_low_to_hold_the_cradle_is_refused():
    with pytest.raises(ParamError, match="strip_drop"):
        effective(BarholderParams(strip_drop=9))


def test_bracket_ribs_that_miss_the_cradle_are_refused():
    with pytest.raises(ParamError, match="bracket"):
        effective(BarholderParams(bar_d=8, bracket_rib=6, bracket=True))


def test_rib_limits_do_not_apply_when_the_bracket_is_off():
    effective(BarholderParams(bar_d=8, bracket_rib=6, bracket=False))


def test_a_drain_as_long_as_the_seat_is_refused():
    with pytest.raises(ParamError, match="drain_length"):
        effective(BarholderParams(drain_length=18))


def test_a_drain_as_wide_as_the_bar_is_refused():
    with pytest.raises(ParamError, match="drain_width"):
        effective(BarholderParams(bar_d=8, drain_width=9))


def test_drain_limits_do_not_apply_when_the_drain_is_off():
    effective(BarholderParams(bar_d=8, drain_width=9, drain=False))


def test_notes_say_how_the_nut_goes_in():
    assert "top edge" in notes()
    assert "front" in notes(nut_entry="front")


def test_notes_warn_that_open_nuts_need_securing_near_food():
    assert "threadlock" in notes(nut_entry="front")
    assert "threadlock" not in notes()


def test_an_open_front_pocket_only_has_to_hide_the_bolt_tip():
    effective(BarholderParams(strip_thickness=7, nut_entry="front"))  # tip 6.5 + 0.5, no cap needed
    with pytest.raises(ParamError, match="strip_thickness"):
        effective(BarholderParams(strip_thickness=7))  # the slot needs a 1 mm cap as well


def test_a_nut_wider_than_the_head_still_clears_the_cradle():
    wide = BarholderParams(nut_af=10)
    assert bolt_xs(wide)[-1] > bolt_xs(BarholderParams())[-1]


@pytest.mark.parametrize("slope", [1, 15, 29])
def test_a_slope_too_flat_to_print_or_to_mean_much_is_refused(slope):
    with pytest.raises(ParamError, match="arm_slope"):
        effective(BarholderParams(arm_slope=slope))


def test_a_steep_slope_needs_a_deep_enough_cradle_to_keep_a_lip():
    effective(BarholderParams(arm_slope=60))  # lip starts at 8 + 6.94 × tan 60° = 20 mm of 25
    with pytest.raises(ParamError, match="cradle_depth"):
        effective(BarholderParams(arm_slope=70))  # would start at 27 mm, past the front
    effective(BarholderParams(arm_slope=70, cradle_depth=32))


def test_zero_slope_only_needs_the_seat_depth():
    effective(BarholderParams(arm_slope=0, cradle_depth=18, drain=False))  # 8 mm strip + 10 mm seat
    with pytest.raises(ParamError, match="cradle_depth"):
        effective(BarholderParams(arm_slope=0, cradle_depth=17, drain=False))


def test_notes_warn_that_straight_arms_snap_stiffer():
    assert "stiffer" in notes(arm_slope=0)
    assert "stiffer" not in notes()


def test_straight_arms_do_not_warn_about_a_snap_they_do_not_have():
    assert "stiffer" not in notes(arm_slope=0, wrap=180)


@pytest.mark.parametrize("slope", [30, 44])
def test_notes_warn_when_a_slope_will_need_supports(slope):
    assert "supports" in notes(arm_slope=slope)


@pytest.mark.parametrize("slope", [0, 45, 60])
def test_notes_stay_quiet_about_supports_on_a_printable_slope(slope):
    assert "supports" not in notes(arm_slope=slope)


def test_notes_warn_about_leaning_walls_when_no_angle_is_given():
    text = notes()
    assert "wall_angle" in text and "lean" in text


def test_notes_stop_warning_once_an_angle_is_given():
    assert "measure" not in notes(wall_angle=3.9)
    assert "3.9" in notes(wall_angle=3.9)


def test_a_bracket_whose_foot_is_above_its_tilted_tip_is_refused():
    # at z = 80 the floor has dropped 72 × tan 15° = 19 mm, well below a foot 5 mm under the cradle's back
    with pytest.raises(ParamError, match="bracket_height"):
        effective(BarholderParams(wall_angle=15, cradle_depth=80, bracket=True, bracket_height=5))


def test_the_same_short_bracket_is_fine_on_a_straight_wall():
    effective(BarholderParams(cradle_depth=80, bracket=True, bracket_height=5))
