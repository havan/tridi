"""Project parameters as frozen dataclasses: defaults, ranges, presets and command-line options.

A project declares its parameters with `param(...)` fields. Values are resolved as
defaults < preset < overrides (command line), and every value is checked against its range or choices.
"""
from __future__ import annotations

import argparse
import dataclasses
import re
import tomllib
import types
import typing
from pathlib import Path


class ParamError(ValueError):
    """A parameter value, name or combination the build refuses."""


def param(default, help: str, *, min: float | None = None, max: float | None = None,
          choices: tuple | None = None) -> dataclasses.Field:
    return dataclasses.field(default=default,
                             metadata={"help": help, "min": min, "max": max, "choices": choices})


def _kind(tp) -> tuple[type, bool]:
    """(base type, optional) for the supported annotations."""
    origin = typing.get_origin(tp)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(tp) if a is not type(None)]
        return args[0], True
    if origin is tuple:
        return tuple, False
    return tp, False


def _fields(cls) -> dict[str, tuple[dataclasses.Field, type, bool]]:
    hints = typing.get_type_hints(cls)
    return {f.name: (f, *_kind(hints[f.name])) for f in dataclasses.fields(cls)}


def _fmt(v) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def validate(obj) -> None:
    for name, (f, base, _optional) in _fields(type(obj)).items():
        value = getattr(obj, name)
        if value is None:
            continue
        meta = f.metadata
        if meta.get("choices") is not None and value not in meta["choices"]:
            raise ParamError(f"{name} = {value!r} is not one of: {', '.join(map(str, meta['choices']))}")
        if base in (int, float):
            if meta.get("min") is not None and value < meta["min"]:
                raise ParamError(f"{name} = {_fmt(value)} is below the minimum {_fmt(meta['min'])}")
            if meta.get("max") is not None and value > meta["max"]:
                raise ParamError(f"{name} = {_fmt(value)} is above the maximum {_fmt(meta['max'])}")


def _convert(name: str, base: type, optional: bool, value):
    if value is None or (optional and value == "auto"):
        if not optional:
            raise ParamError(f"{name} needs a value")
        return None
    try:
        if base is tuple:
            return tuple(str(v) for v in ([value] if isinstance(value, str) else value))
        if base is bool:
            if isinstance(value, bool):
                return value
            raise ValueError
        if base is int:
            if isinstance(value, float) and not value.is_integer():
                raise ValueError
            return int(value)
        if base is float:
            return float(value)
        return str(value)
    except (TypeError, ValueError):
        raise ParamError(f"{name} = {value!r} is not a valid {base.__name__}") from None


def load_presets(project_file: Path, local_file: Path, project: str) -> dict[str, dict]:
    presets: dict[str, dict] = {}
    if project_file.exists():
        presets.update(tomllib.loads(project_file.read_text()))
    if local_file.exists():
        for name, values in tomllib.loads(local_file.read_text()).get(project, {}).items():
            presets[name] = {**presets.get(name, {}), **values}
    return presets


def resolve(cls, presets: dict[str, dict], preset: str | None, overrides: dict):
    fields = _fields(cls)
    values: dict = {}
    if preset is not None:
        if preset not in presets:
            raise ParamError(f"unknown preset {preset!r}; available: {', '.join(sorted(presets)) or 'none'}")
        values.update(presets[preset])
    values.update(overrides)
    converted = {}
    for name, value in values.items():
        if name not in fields:
            raise ParamError(f"unknown parameter {name!r}; valid: {', '.join(fields)}")
        _f, base, optional = fields[name]
        converted[name] = _convert(name, base, optional, value)
    obj = cls(**converted)
    validate(obj)
    return obj


def _option(name: str, base: type) -> str:
    if base is tuple:  # a repeatable option is named in the singular: notches -> --notch
        name = re.sub(r"(ch|sh|ss|x)es$", r"\1", name) if re.search(r"(ch|sh|ss|x)es$", name) else name.removesuffix("s")
    return "--" + name.replace("_", "-")


def add_cli_arguments(cls, parser: argparse.ArgumentParser) -> None:
    for name, (f, base, optional) in _fields(cls).items():
        meta = f.metadata
        help_ = meta.get("help", "")
        if meta.get("choices"):
            help_ += f" ({'/'.join(map(str, meta['choices']))})"
        elif meta.get("min") is not None or meta.get("max") is not None:
            help_ += f" [{_fmt(meta.get('min'))}..{_fmt(meta.get('max'))}]"
        default = "auto" if f.default is None else f.default
        help_ += f", default {default if base is not tuple else ', '.join(default) or 'none'}"
        help_ = help_.replace("%", "%%")
        kw = {"dest": name, "default": argparse.SUPPRESS, "help": help_}
        if base is bool:
            parser.add_argument(_option(name, base), action=argparse.BooleanOptionalAction, **kw)
        elif base is tuple:
            parser.add_argument(_option(name, base), action="append", metavar="VALUE", **kw)
        else:
            parser.add_argument(_option(name, base), metavar="VALUE", **kw)


def cli_overrides(cls, ns: argparse.Namespace) -> dict:
    out = {}
    for name, (_f, base, optional) in _fields(cls).items():
        if not hasattr(ns, name):
            continue
        raw = getattr(ns, name)
        if base in (int, float) and isinstance(raw, str) and raw != "auto":
            try:
                raw = float(raw)
            except ValueError:
                raise ParamError(f"{name} = {raw!r} is not a number") from None
        out[name] = _convert(name, base, optional, raw)
    return out


def variant_name(preset: str | None, overrides: dict) -> str:
    parts = [preset or "default"]
    for key in sorted(overrides):
        value = overrides[key]
        if isinstance(value, tuple):
            text = "+".join(map(str, value)) or "none"
        elif value is None:
            text = "auto"
        else:
            text = _fmt(value)
        parts.append(f"{key}-{text}")
    return re.sub(r"[^a-z0-9_.+@-]", "-", "_".join(parts).lower())
