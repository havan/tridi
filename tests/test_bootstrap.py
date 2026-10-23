def test_freecad_importable():
    import tridi  # noqa: F401
    import Part
    assert Part.makeBox(1, 2, 3).Volume == 6.0


def test_repo_root():
    import tridi
    assert (tridi.REPO_ROOT / "pixi.toml").exists()
