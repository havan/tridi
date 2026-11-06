import subprocess
import sys
import tomllib

import pytest

from projects.flange.params import FlangeParams, effective
from tridi import REPO_ROOT

PRESETS = tomllib.loads((REPO_ROOT / "projects/flange/presets.toml").read_text())


def test_there_are_presets():
    assert len(PRESETS) >= 6


@pytest.mark.parametrize("name", sorted(PRESETS))
def test_presets_all_resolve(name):
    effective(FlangeParams(**PRESETS[name]))


def _run(out, *args):
    return subprocess.run([sys.executable, "run.py", "build", "flange", "--out", str(out), *args], cwd=REPO_ROOT,
                          capture_output=True, text=True)


def test_cli_force_builds_what_would_be_refused(tmp_path):
    out = tmp_path / "variant"
    refused = _run(out, "--shape", "slot", "--slot-length", "400")
    assert refused.returncode == 2 and not out.exists()
    forced = _run(out, "--shape", "slot", "--slot-length", "400", "--force")
    assert forced.returncode == 0, forced.stderr
    assert "forced: outer" in (out / "summary.txt").read_text()


def test_cli_force_overrules_a_size_check_and_a_range(tmp_path):
    out = tmp_path / "variant"
    assert _run(out, "--shape", "slot", "--rim-bolts", "7").returncode == 2
    assert _run(out, "--opening-d", "400").returncode == 2
    assert not out.exists()
    forced = _run(out, "--shape", "slot", "--rim-bolts", "7", "--force")
    assert forced.returncode == 0, forced.stderr
    assert "forced: rim_bolts (7)" in (out / "summary.txt").read_text()


def test_cli_force_does_not_overrule_a_bad_choice(tmp_path):
    assert _run(tmp_path / "variant", "--shape", "square", "--force").returncode == 2
