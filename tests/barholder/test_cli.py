import subprocess
import sys

from tridi import REPO_ROOT


def run(tmp_path, *args):
    out = tmp_path / "barholder"
    r = subprocess.run([sys.executable, "run.py", "build", "barholder", "--out", str(out), *args], cwd=REPO_ROOT,
                       capture_output=True, text=True)
    return r, out


def test_default_build_writes_print_files_and_summary(tmp_path):
    r, out = run(tmp_path)
    assert r.returncode == 0, r.stderr
    for name in ("strip.stl", "strip.3mf", "backplate.stl", "backplate.3mf", "assembly.step"):
        assert (out / name).exists(), name
    assert "M4×12" in (out / "summary.txt").read_text()


def test_no_backplate_flag_drops_the_part(tmp_path):
    r, out = run(tmp_path, "--no-backplate")
    assert r.returncode == 0, r.stderr
    assert (out / "strip.stl").exists() and not (out / "backplate.stl").exists()


def test_a_strip_longer_than_the_bed_is_refused(tmp_path):
    r, out = run(tmp_path, "--count", "4")
    assert r.returncode == 2 and "does not fit" in r.stderr
    assert not out.exists()


def test_a_bigger_printer_takes_the_longer_strip(tmp_path):
    r, _ = run(tmp_path, "--count", "4", "--printer", "300x300x300")
    assert r.returncode == 0, r.stderr


def test_preset_for_a_single_test_cradle(tmp_path):
    r, out = run(tmp_path, "--preset", "test_fit")
    assert r.returncode == 0, r.stderr
    assert "count = 1" in (out / "summary.txt").read_text()


def test_nut_entry_option_reaches_the_build(tmp_path):
    r, out = run(tmp_path, "--nut-entry", "front")
    assert r.returncode == 0, r.stderr
    assert "nut_entry = front" in (out / "summary.txt").read_text()


def test_unknown_nut_entry_is_refused(tmp_path):
    r, _ = run(tmp_path, "--nut-entry", "side")
    assert r.returncode == 2 and "top" in r.stderr


def test_arm_slope_option_reaches_the_build(tmp_path):
    r, out = run(tmp_path, "--arm-slope", "0")
    assert r.returncode == 0, r.stderr
    assert "arm_slope = 0" in (out / "summary.txt").read_text()


def test_wall_angle_option_reaches_the_build(tmp_path):
    r, out = run(tmp_path, "--wall-angle", "3.9")
    assert r.returncode == 0, r.stderr
    assert "wall_angle = 3.9" in (out / "summary.txt").read_text()


def test_through_cut_can_be_turned_off(tmp_path):
    r, out = run(tmp_path, "--no-through-cut")
    assert r.returncode == 0, r.stderr
    assert "through_cut = False" in (out / "summary.txt").read_text()
