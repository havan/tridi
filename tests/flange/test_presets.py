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


def test_cli_force_lists_an_overruled_range(tmp_path):
    out = tmp_path / "variant"
    forced = _run(out, "--seal-thickness", "8", "--force")
    assert forced.returncode == 0, forced.stderr
    assert "forced: seal_thickness = 8 is above" in (out / "summary.txt").read_text()


@pytest.mark.parametrize("args", [("--opening-d", "400"), ("--shape", "slot", "--slot-length", "400")])
def test_range_and_fit_refusals_mention_force(tmp_path, args):
    refused = _run(tmp_path / "variant", *args)
    assert refused.returncode == 2 and "--force" in refused.stderr


def test_projects_without_force_do_not_mention_it(tmp_path):
    refused = subprocess.run([sys.executable, "run.py", "build", "fanbox", "--out", str(tmp_path / "v"), "--wall", "99"],
                             cwd=REPO_ROOT, capture_output=True, text=True)
    assert refused.returncode == 2 and "--force" not in refused.stderr


FORCED_ODDITIES = [
    ("--fixing", "centre_bolt", "--opening-d", "14"),
    ("--fixing", "centre_bolt", "--opening-d", "14", "--mesh", "slicer"),
    ("--outer-thickness", "0"),
    ("--outer-thickness", "-1"),
    ("--opening-d", "0", "--mesh", "grid"),
    ("--shape", "slot", "--slot-width", "0", "--mesh", "grid"),
    ("--fixing", "centre_bolt", "--mesh", "slicer", "--opening-d", "12", "--bar-width", "13"),
    ("--fixing", "centre_bolt", "--hubs", "0"),
]


@pytest.mark.parametrize("args", FORCED_ODDITIES, ids=lambda a: " ".join(a))
def test_forced_oddities_exit_cleanly(tmp_path, args):
    run = _run(tmp_path / "variant", *args, "--force")
    assert run.returncode in (0, 2)
    assert "Traceback" not in run.stderr


def test_cli_nan_refused_cleanly(tmp_path):
    run = _run(tmp_path / "variant", "--mesh", "grid", "--mesh-hole", "nan")
    assert run.returncode == 2 and "Traceback" not in run.stderr


def test_a_failed_zone_writes_nothing(tmp_path):
    out = tmp_path / "variant"
    run = _run(out, "--fixing", "centre_bolt", "--mesh", "slicer", "--opening-d", "12", "--bar-width", "13", "--force")
    assert run.returncode == 2 and not out.exists()


def test_cli_force_does_not_overrule_a_bad_choice(tmp_path):
    assert _run(tmp_path / "variant", "--shape", "square", "--force").returncode == 2


def test_mesh_to_edge_reaches_the_build(tmp_path):
    out = tmp_path / "variant"
    run = _run(out, "--mesh", "grid", "--mesh-to-edge")
    assert run.returncode == 0, run.stderr
    assert "mesh_to_edge = True" in (out / "summary.txt").read_text()


def test_add_wire_reaches_the_build(tmp_path):
    out = tmp_path / "variant"
    run = _run(out, "--mesh", "grid", "--add-wire")
    assert run.returncode == 0, run.stderr
    summary = (out / "summary.txt").read_text()
    assert "add_wire = True" in summary and "of wire mesh" in summary
