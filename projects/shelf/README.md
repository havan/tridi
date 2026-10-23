# Shelf

A small wall shelf for phones, game controllers and chargers, with cable management. Every size and
option is a parameter; the build prints in PLA without support material.

```
pixi run build shelf                                         # 200 × 100, brackets below, screw holes
pixi run build shelf --preset corner                         # a preset from presets.toml or local.toml
pixi run build shelf --width 180 --supports above --mount cleat --notch back-left
pixi run build shelf --printer mk4                           # another printer profile
pixi run build shelf --help                                  # every option
```

Output goes to `out/shelf/<variant>/`: `shelf.stl` / `.3mf` (and `cleat`, `clip` when used), already
rotated for printing, plus `assembly.step`, an `.FCStd` and `summary.txt` with the volume and estimated
weight of each part.

## Options

Sizes are in mm.

| Option | Default | Range or choices | What it does |
|---|---|---|---|
| `--width` | 200 | 40–1000 | width along the wall |
| `--depth` | 100 | 30–400 | from the wall to the front edge |
| `--slab-thickness` | 4 | 2–12 | shelf surface thickness |
| `--plate-thickness` | 4 | 2–12 | back plate thickness |
| `--supports` | below | below, above | brackets under the shelf, or above it as bookends |
| `--bracket-count` | auto | 2–20 | auto keeps the gaps between brackets at 160 mm or less |
| `--bracket-depth` | auto | 10–400 | how far a bracket reaches along the shelf (auto: 0.75 × depth) |
| `--bracket-height` | 55 | 15–300 | how far a bracket reaches along the back plate |
| `--bracket-thickness` | 5 | 2–20 | |
| `--bracket-web` | 6 | 2–30 | width of the bracket's strip along shelf and plate |
| `--edge-radius` | 2 | 0–5 | rounding of exposed edges |
| `--bed-chamfer` | 0.4 | 0–2 | chamfer where the part touches the bed |
| `--mount` | screws | screws, keyhole, cleat, adhesive | how it goes on the wall (see below) |
| `--top-screws` | under | under, strip | top screws under the shelf, or in a strip above it |
| `--strip-height` | 18 | 10–60 | height of that strip |
| `--max-reach` | 150 | 50–500 | deepest shelf a screwdriver reaches under |
| `--screw-d` | 4 | 2.5–8 | screw diameter |
| `--screw-head-d` | 8 | 5–16 | countersunk head diameter |
| `--dowel-d` | 6 | 4–14 | wall dowel (for the instructions only) |
| `--cleat-thickness` | 8 | 5–20 | wall cleat thickness |
| `--cleat-height` | 30 | 15–80 | wall cleat height |
| `--adhesive-extra` | 25 | 0–100 | extra back plate for tape or glue |
| `--glue-grooves` | off | | grooves on the wall side for hot glue |
| `--plate-style` | full | full, windowed, pads | back plate: solid, with windows, or a pad per bracket |
| `--surface` | solid | solid, honeycomb | shelf surface |
| `--hex-cell` | 10 | 5–40 | honeycomb cell, across flats |
| `--hex-wall` | 2 | 1–10 | honeycomb wall |
| `--solid-rim` | 8 | 4–30 | solid border around a honeycomb surface |
| `--notch` | none | back-left, back-right, back@*x* | cable cutout; repeat for more (*x*: mm from the left) |
| `--notch-width` | 14 | 6–40 | back notch width: wide enough for a USB plug to pass |
| `--corner-notch-r` | 15 | 6–40 | corner notch radius |
| `--front-lip` | 0 | 0–30 | lip along the front edge (0: none; 6 works well) |
| `--clips` | 0 | 0–50 | number of cable-tip clips |
| `--clip-cable-d` | 4 | 2–10 | cable diameter the clips grip |
| `--orientation` | flat | flat, side | print lying on the back plate, or on its end (stronger, but width ≤ printer height) |

The build refuses combinations that don't work and says why: a notch through a bracket, a shelf too
narrow for its screw holes, a part too big for the printer, and so on. Nothing is written in that case.

## Presets

`presets.toml` has a few examples (`corner`, `lean`, `hanging`). Keep your own in `local.toml` at the repo
root, which git ignores:

```toml
[shelf.desk]
width = 180
notches = ["back-right"]
front_lip = 6
```

## Mounting

- **Screws** (`--mount screws`): drill for `dowel-d` (6 mm) plastic dowels and use countersunk
  `screw-d` (4 mm) screws. With the brackets below, the top screws sit just under the shelf: use a long
  screwdriver. For deeper shelves, `--top-screws strip` moves them into a strip above the shelf.
- **Keyholes** (`--mount keyhole`): set the screws so their heads stand about 4 mm proud of the wall, then
  hang the shelf over them and push it down.
- **Cleat** (`--mount cleat`): screw the cleat (`cleat.stl`) to the wall first, level, then hook the shelf
  over it. A back notch splits the cleat into two pieces, each with its own screws.
- **Adhesive** (`--mount adhesive`): a taller, hole-free back plate for double-sided tape or hot glue
  (`--glue-grooves` gives glue something to grip). Tape and glue only hold as well as the paint under
  them, so keep this for light things.

## Cables

- `--notch back-left` / `back-right` cuts a quarter circle in a back corner, for a shelf in a room
  corner. `--notch back@100` cuts a slot at 100 mm from the left. Both go through the back plate too,
  so the cable runs straight up the wall.
- Clips push onto an edge of the shelf and hold a cable just behind its plug, so the plug stays on the
  shelf when you unplug the device. They fit the side edges always, and the front edge only without a
  front lip. Their grip is shorter than the honeycomb's solid rim, so they never land on a hole.

## Printing

PLA, no supports. Each part is exported in its print orientation: the shelf lies on its back plate (or
on its end with `--orientation side`), the cleat lies on its back, and the clips stand on their backs.
