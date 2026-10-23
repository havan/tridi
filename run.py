"""Build a project: python run.py build <project> [--preset NAME] [--printer KEY|WxDxH] [--out DIR] [options]

Usually run as `pixi run build <project> ...`. Add --help after the project name for its options.
"""
from __future__ import annotations

import argparse
import dataclasses
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

import tridi  # noqa: E402,F401
import Part  # noqa: E402
from tridi.export import export  # noqa: E402
from tridi.features import GeometryError  # noqa: E402
from tridi.params import ParamError, add_cli_arguments, cli_overrides, load_presets, resolve, variant_name  # noqa: E402
from tridi.printers import DEFAULT_PRINTER, FitError, get_printer, load_printers  # noqa: E402


def _projects() -> list[str]:
    return sorted(d.name for d in (ROOT / "projects").iterdir() if (d / "__init__.py").exists())


def build(argv: list[str]) -> int:
    first = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    first.add_argument("project")
    known, _ = first.parse_known_args(argv)
    if known.project not in _projects():
        print(f"error: unknown project {known.project!r}; available: {', '.join(_projects())}", file=sys.stderr)
        return 2
    project = importlib.import_module(f"projects.{known.project}")

    parser = argparse.ArgumentParser(prog=f"build {known.project}", description=project.TITLE, allow_abbrev=False)
    parser.add_argument("project")
    parser.add_argument("--preset", help="preset from presets.toml or local.toml")
    parser.add_argument("--printer", default=DEFAULT_PRINTER,
                        help=f"printer profile from printers.toml, or a size like 300x300x300 (default {DEFAULT_PRINTER})")
    parser.add_argument("--out", type=Path, help="output folder (default out/<project>/<variant>)")
    add_cli_arguments(project.Params, parser)
    args = parser.parse_args(argv)

    printer = get_printer(args.printer, load_printers())
    presets = load_presets(ROOT / "projects" / known.project / "presets.toml", ROOT / "local.toml", known.project)
    overrides = cli_overrides(project.Params, args)
    params = resolve(project.Params, presets, args.preset, overrides)
    variant = variant_name(args.preset, overrides)
    parts, notes = project.build(params, printer)
    out = args.out or ROOT / "out" / known.project / variant
    summary = export(parts, out, title=variant, params=dataclasses.asdict(params), printer=printer, notes=notes)
    print(summary.read_text(), end="")
    print(f"\nwrote {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] != "build":
        print(__doc__.strip(), file=sys.stderr)
        return 2
    try:
        return build(argv[1:])
    except (ParamError, FitError, GeometryError) as e:  # projects raise subclasses of these
        print(f"error: {e}", file=sys.stderr)
        return 2
    except Part.OCCError as e:
        print(f"error: the geometry kernel failed ({e}); try less extreme values", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
