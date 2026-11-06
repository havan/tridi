import subprocess
import sys
import tomllib

import pytest

from projects.grommet.params import GrommetParams, effective
from tridi import REPO_ROOT

PRESETS = tomllib.loads((REPO_ROOT / "projects/grommet/presets.toml").read_text())


def test_there_are_presets():
    assert {"round_6", "rectangular", "table", "connector"} <= set(PRESETS)


@pytest.mark.parametrize("name", sorted(PRESETS))
def test_presets_all_resolve(name):
    effective(GrommetParams(**PRESETS[name]))


def test_default_build_writes_four_parts_and_a_summary(tmp_path):
    done = subprocess.run([sys.executable, "run.py", "build", "grommet", "--out", str(tmp_path)], cwd=REPO_ROOT,
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert all((tmp_path / f"{name}.stl").exists() for name in ("body_a", "body_b", "nut_a", "nut_b"))
    assert "13 mm hole" in (tmp_path / "summary.txt").read_text()
