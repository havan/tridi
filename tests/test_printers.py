import pytest

from tridi.params import ParamError
from tridi.printers import DEFAULT_PRINTER, FitError, check_fit, get_printer, load_printers


def test_load_has_default():
    printers = load_printers()
    assert DEFAULT_PRINTER == "mk3s"
    assert printers["mk3s"].x == 250


def test_custom_spec():
    p = get_printer("300x200x100", {})
    assert (p.key, p.x, p.y, p.z) == ("custom", 300, 200, 100)


def test_unknown_printer():
    with pytest.raises(ParamError, match="mk3s"):
        get_printer("nope", load_printers())


def test_fits_and_swap():
    p = load_printers()["mk3s"]
    check_fit("shelf", (200, 100, 100), p)
    check_fit("shelf", (200, 240, 100), p)


def test_too_big_message():
    p = load_printers()["mk3s"]
    with pytest.raises(FitError, match=r"shelf: 270.0 × 60.0 × 100.0 mm does not fit Prusa i3 MK3S/MK3S\+ "
                                       r"\(250 × 210 × 210 mm\): X over by 20.0 mm"):
        check_fit("shelf", (270, 60, 100), p)


def test_too_tall_lists_z():
    p = load_printers()["mk3s"]
    with pytest.raises(FitError, match="Z over by 10.0 mm"):
        check_fit("shelf", (100, 100, 220), p)
