# tridi

Parametric 3D-printable household items, generated with [FreeCAD](https://www.freecad.org/).
Every design is Python code: pick the options and sizes you need and get print-ready files.

## Projects

| Project | What it is |
|---|---|
| [`shelf`](projects/shelf/) | Small wall shelf for phones, controllers and chargers, with cable management |

## Quick start

Install [pixi](https://pixi.sh), then:

```
pixi run build shelf                          # default variant
pixi run build shelf --width 180 --mount cleat
pixi run build shelf --help                   # every option of a project
pixi run test                                 # run the tests
pixi run freecad                              # open the FreeCAD GUI
```

Output goes to `out/<project>/<variant>/`: STL and 3MF per part, already in print orientation, a STEP of
the assembly, an `.FCStd` for FreeCAD and a `summary.txt` with volume and estimated weight.

Choose your printer with `--printer` (see [`printers.toml`](printers.toml)) or give a build volume like
`--printer 300x300x300`. A part that doesn't fit is refused instead of exported.

## Your own presets

Each project ships a few example presets (`projects/<name>/presets.toml`, used with `--preset NAME`).
Put your own in `local.toml` at the repo root; it is not tracked by git:

```toml
[shelf.desk]
width = 180
notches = ["back-right"]
```

## Layout

```
src/tridi/         shared code: parameters, printers, geometry features, export
projects/<name>/   one project per folder
tests/             pytest
docs/              designs and plans
out/               generated files (not tracked)
```

## FreeCAD MCP

`.mcp.json` configures [freecad-mcp](https://pypi.org/project/freecad-mcp/) against the pixi FreeCAD, for
inspecting designs from an AI assistant. On Windows, change the `--freecadcmd` path to
`.pixi/envs/default/Library/bin/freecadcmd.exe`.

## Platforms

pixi resolves Linux, macOS (Apple silicon) and Windows, but only Linux is tested.

## Licence

[CC BY-NC 4.0](LICENSE): share and adapt with attribution, no commercial use.
