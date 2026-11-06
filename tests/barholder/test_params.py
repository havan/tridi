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
    assert bolt_length(BarholderParams()) == 10  # 4 + 2 + 3.2 + 1 - 0.5 = 9.7 -> stock 10
    assert bolt_length(BarholderParams(box_wall=3)) == 12


def test_without_a_backplate_the_bolt_only_spans_washer_wall_and_nut():
    assert bolt_length(BarholderParams(backplate=False)) == 8  # 1 + 2 + 3.2 + 1 = 7.2 -> stock 8


def test_notes_list_the_hardware_for_a_full_strip():
    text = notes()
    assert "4 × M4×10 countersunk" in text and "4 × M4 nuts" in text


def test_notes_ask_for_washers_when_the_backplate_is_off():
    text = notes(backplate=False)
    assert "M4×8" in text and "washer" in text and "countersunk" not in text


def test_notes_give_the_drilling_size_and_template():
    assert "4.5 mm" in notes() and "template" in notes()


def test_notes_give_the_bar_length_range_from_the_cradle_depth():
    text = notes(cradle_depth=25)
    assert "14 mm" in text and "30 mm" in text  # 2 × 7 mm strip; 2 × (25 - 10) mm


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
        effective(BarholderParams(box_wall=5))  # needs M4×16: tip 7.5 mm into a 7 mm strip


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
