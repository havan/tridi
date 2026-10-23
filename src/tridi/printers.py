"""Printer profiles and the build-volume fit check."""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from . import REPO_ROOT
from .params import ParamError

DEFAULT_PRINTER = "mk3s"


class FitError(ValueError):
    """A part is larger than the printer's build volume."""


@dataclass(frozen=True)
class Printer:
    key: str
    name: str
    x: float
    y: float
    z: float
    nozzle: float = 0.4
    clearance: float = 0.2


def load_printers(path: Path = REPO_ROOT / "printers.toml") -> dict[str, Printer]:
    return {key: Printer(key=key, **values) for key, values in tomllib.loads(path.read_text()).items()}


def get_printer(spec: str, printers: dict[str, Printer]) -> Printer:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", spec)
    if m:
        x, y, z = map(float, m.groups())
        return Printer("custom", f"custom {spec} mm", x, y, z)
    if spec not in printers:
        raise ParamError(f"unknown printer {spec!r}; known: {', '.join(printers)}, or a size like 300x300x300")
    return printers[spec]


def _mm(v: float) -> str:
    return f"{v:g}"


def check_fit(part: str, size: tuple[float, float, float], printer: Printer) -> None:
    x, y, z = size
    if z <= printer.z and ((x <= printer.x and y <= printer.y) or (y <= printer.x and x <= printer.y)):
        return
    overs = [f"{axis} over by {v - lim:.1f} mm"
             for axis, v, lim in (("X", x, printer.x), ("Y", y, printer.y), ("Z", z, printer.z)) if v > lim]
    raise FitError(f"{part}: {x:.1f} × {y:.1f} × {z:.1f} mm does not fit {printer.name} "
                   f"({_mm(printer.x)} × {_mm(printer.y)} × {_mm(printer.z)} mm): {', '.join(overs)}")
