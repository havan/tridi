"""tridi: parametric 3D-printable household items, built with FreeCAD.

Importing this package puts FreeCAD's Python modules (FreeCAD, Part, Mesh, ...) on sys.path, so plain
Python inside the pixi environment can use FreeCAD as a library.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _bootstrap_freecad() -> None:
    prefix = Path(sys.prefix)
    for candidate in (prefix / "lib", prefix / "Library" / "bin", prefix / "Library" / "lib"):
        if (candidate / "FreeCAD.so").exists() or (candidate / "FreeCAD.pyd").exists():
            if str(candidate) not in sys.path:
                sys.path.append(str(candidate))
            # FreeCAD must be initialised before any of its modules: `import Part` alone segfaults.
            import FreeCAD  # noqa: F401
            return
    raise ImportError(f"FreeCAD not found in {prefix}; run inside `pixi run`")


_bootstrap_freecad()
