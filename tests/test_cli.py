import subprocess
import sys

from tridi import REPO_ROOT


def run(tmp_path, *args):
    out = tmp_path / "variant"
    r = subprocess.run([sys.executable, "run.py", "build", "shelf", "--out", str(out), *args], cwd=REPO_ROOT,
                       capture_output=True, text=True)
    return r, out


def test_cli_default(tmp_path):
    r, out = run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert (out / "shelf.stl").exists() and (out / "summary.txt").exists()
    assert "Prusa i3 MK3S" in (out / "summary.txt").read_text()


def test_cli_options(tmp_path):
    r, out = run(tmp_path, "--width", "180", "--supports", "above", "--mount", "cleat", "--notch", "back-left",
                 "--clips", "3")
    assert r.returncode == 0, r.stderr
    for name in ("shelf.stl", "cleat.stl", "clip.stl", "assembly.step"):
        assert (out / name).exists(), name
    assert "clip ×3" in (out / "summary.txt").read_text()


def test_cli_too_big_exit_code(tmp_path):
    r, out = run(tmp_path, "--width", "300")
    assert r.returncode == 2
    assert r.stderr.startswith("error:") and "over by" in r.stderr
    assert "Traceback" not in r.stderr
    assert not out.exists()


def test_cli_bad_param(tmp_path):
    r, out = run(tmp_path, "--supports", "side")
    assert r.returncode == 2 and "not one of" in r.stderr
    assert not out.exists()


def test_cli_layout_error(tmp_path):
    r, out = run(tmp_path, "--width", "60")
    assert r.returncode == 2 and r.stderr.startswith("error:")
    assert not out.exists()


def test_cli_preset(tmp_path):
    r, out = run(tmp_path, "--preset", "corner")
    assert r.returncode == 0, r.stderr
    assert "notches = back-left" in (out / "summary.txt").read_text()


def test_cli_custom_printer(tmp_path):
    r, _ = run(tmp_path, "--printer", "400x400x400", "--width", "300")
    assert r.returncode == 0, r.stderr


def test_cli_unknown_project():
    r = subprocess.run([sys.executable, "run.py", "build", "nope"], cwd=REPO_ROOT, capture_output=True, text=True)
    assert r.returncode == 2 and "shelf" in r.stderr


def test_cli_help_lists_options():
    r = subprocess.run([sys.executable, "run.py", "build", "shelf", "--help"], cwd=REPO_ROOT, capture_output=True,
                       text=True)
    assert r.returncode == 0 and "--plate-style" in r.stdout and "--notch" in r.stdout


def test_cli_fanbox(tmp_path):
    out = tmp_path / "fanbox"
    r = subprocess.run([sys.executable, "run.py", "build", "fanbox", "--out", str(out)], cwd=REPO_ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for name in ("duct.stl", "lid_plate.3mf", "mesh_frame.stl", "assembly.step"):
        assert (out / name).exists(), name
    summary = (out / "summary.txt").read_text()
    assert "M4×16" in summary and "M4×40" in summary


def test_cli_fanbox_base_length_follows_fan_size(tmp_path):
    out = tmp_path / "fanbox"
    r = subprocess.run([sys.executable, "run.py", "build", "fanbox", "--out", str(out), "--fan-size", "120"],
                       cwd=REPO_ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    summary = (out / "summary.txt").read_text()
    assert "lid_plate ×1" in summary and "print size 156.0 × 90.0" in summary
    assert "base_length = auto" in summary


def test_cli_fanbox_explicit_base_length(tmp_path):
    out = tmp_path / "fanbox"
    r = subprocess.run([sys.executable, "run.py", "build", "fanbox", "--out", str(out), "--base-length", "150"],
                       cwd=REPO_ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "print size 186.0 × 90.0" in (out / "summary.txt").read_text()
