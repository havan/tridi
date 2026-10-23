import argparse
from dataclasses import dataclass

import pytest

from tridi.params import (ParamError, add_cli_arguments, cli_overrides, load_presets, param, resolve,
                          variant_name)


@dataclass(frozen=True)
class Toy:
    width: float = param(200, "w", min=40, max=1000)
    side: str = param("below", "s", choices=("below", "above"))
    count: int | None = param(None, "c", min=2)
    grooves: bool = param(False, "g")
    notches: tuple[str, ...] = param((), "n")


def test_defaults():
    assert resolve(Toy, {}, None, {}) == Toy()


def test_precedence():
    t = resolve(Toy, {"a": {"width": 300}}, "a", {"side": "above"})
    assert (t.width, t.side) == (300, "above")


def test_range_error():
    with pytest.raises(ParamError, match="width = 20 is below the minimum 40"):
        resolve(Toy, {}, None, {"width": 20})


def test_choice_error():
    with pytest.raises(ParamError, match="not one of: below, above"):
        resolve(Toy, {}, None, {"side": "side"})


def test_unknown_key_lists_valid():
    with pytest.raises(ParamError, match=r"unknown parameter 'widht'.*width"):
        resolve(Toy, {}, None, {"widht": 1})


def test_unknown_preset_lists_available():
    with pytest.raises(ParamError, match="available: a"):
        resolve(Toy, {"a": {}}, "b", {})


def test_preset_lists_become_tuples():
    assert resolve(Toy, {"a": {"notches": ["back-left"]}}, "a", {}).notches == ("back-left",)


def test_load_presets_local_overrides(tmp_path):
    proj = tmp_path / "presets.toml"
    proj.write_text("[a]\nwidth = 300\n")
    local = tmp_path / "local.toml"
    local.write_text("[toy.a]\nwidth = 250\n[other.a]\nwidth = 1\n")
    assert load_presets(proj, local, "toy") == {"a": {"width": 250}}


def test_load_presets_missing_files(tmp_path):
    assert load_presets(tmp_path / "nope.toml", tmp_path / "nope2.toml", "toy") == {}


def _parse(argv):
    parser = argparse.ArgumentParser()
    add_cli_arguments(Toy, parser)
    return cli_overrides(Toy, parser.parse_args(argv))


def test_cli_roundtrip():
    got = _parse(["--width", "300", "--notch", "back-left", "--notch", "back@60", "--count", "auto",
                  "--grooves"])
    assert got == {"width": 300.0, "notches": ("back-left", "back@60"), "count": None, "grooves": True}


def test_cli_int_value():
    assert _parse(["--count", "3"]) == {"count": 3}


def test_cli_omitted_not_overridden():
    assert _parse([]) == {}


def test_variant_name():
    assert variant_name(None, {"width": 300.0, "notches": ("back-left",)}) == "default_notches-back-left_width-300"


def test_variant_name_preset_only():
    assert variant_name("corner", {}) == "corner"
