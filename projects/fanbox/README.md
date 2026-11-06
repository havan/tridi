# Fanbox

A PC fan on the lid of a drying box, such as a biltong box. Three printed parts: a duct that widens from the
lid into a drop-in socket for the fan, a plate that goes under the lid, and a frame that clamps wire mesh onto
the socket's rim to keep flies out. Everything is held by M4 countersunk hex-socket (Allen) bolts and nuts.

The defaults fit a Corsair A1425L12S-2: 140 × 25 mm with holes 124.5 mm apart.

```
pixi run build fanbox                                 # 140 mm fan, 2 mm lid, 230 × 95 mm of flat lid
pixi run build fanbox --fan-size 120                  # a 120 mm fan: everything marked auto below follows
pixi run build fanbox --fan-size 130 --fan-hole-spacing 115   # a non-standard fan
pixi run build fanbox --cable-side left --cable-offset 20     # where your fan's cable leaves
pixi run build fanbox --preset thick_fan              # 38 mm fan
pixi run build fanbox --help                          # every option
```

Output goes to `out/fanbox/<variant>/`: `duct`, `lid_plate` and `mesh_frame` as STL and 3MF, already rotated
for printing, plus `assembly.step`, an `.FCStd` and `summary.txt`. The summary lists the sizes it worked out,
the bolt lengths and the holes to make in the lid.

## What to buy

With the default sizes:

| Qty | Part | Used for |
|---|---|---|
| 4 | M4×16 countersunk hex-socket bolt (ISO 10642 / DIN 7991) | duct to lid |
| 4 | M4×40 countersunk hex-socket bolt | mesh frame and fan to duct |
| 8 | M4 hex nut (DIN 934: 7 mm across flats, 3.2 mm high) | all of them |
| 1 | 146 × 146 mm wire fly mesh | mesh frame |

The heads take a 2.5 mm hex key. A countersunk bolt's length is measured including its head. If your heads
aren't 8 mm across, set `--head-d`.

## Printing

No supports, no brim. Each part is exported the way it should print:

- **Duct:** standing on the lid end, socket up. The flare leans about 33° from vertical at most, and the only
  overhangs are short bridges over the four nut slots. The build refuses anything steeper than 45°.
- **Plate:** lid side down, nut pockets up.
- **Frame:** fan side down, bolt seats up.

Suggested settings: PETG, or ASA if there's a heat source in the box, since PLA softens at around 55–60 °C. Use a
0.2 mm layer height, 4 walls and 20% infill. The summary's weights are for solid parts, so the real ones are
much lower.

Holes are sized for how FDM prints them: 4.5 mm for an M4 bolt, 8.4 mm for the head, 7.2 mm for a nut pressed
into the plate and 7.4 mm for one slid into the duct. Edges on the bed have a 0.4 mm chamfer against elephant's
foot. If your printer runs tight or loose, the `clearance` in [`printers.toml`](../../printers.toml) scales the
head seat and the plate's nut pocket, and `--fan-fit` sets the gap around the fan.

## Assembly

1. **Mark the lid.** Hold the plate against the lid's flat area, trace its opening and mark its four holes.
2. **Cut the lid.** Cut the 134 × 84 mm opening and drill the four holes at 4.5 mm. A 6 mm drill makes the corners.
3. **Nuts into the plate.** Press four nuts into the pockets. If one is loose, a dab of glue holds it.
4. **Bolt it to the lid.** Plate under the lid with its pockets facing into the box, duct on top with the ears
   over the holes, then the four M4×16 bolts from above. A strip of foam tape or a bead of food-safe silicone
   under the duct's foot closes any gap a fly could use.
5. **Nuts into the duct.** Slide four nuts into the slots on the duct's long sides, flats against the slot's
   walls, until they stop.
6. **Fan.** Drop the fan into the socket with its airflow arrow pointing up, away from the box. Turn it so the
   cable leaves at the notch, and lay the cable in the notch.
7. **Mesh and frame.** Lay the mesh on the rim, poke the bolts through it and add the frame.
8. **Bolt it together.** Tighten the four M4×40 bolts from above until snug. Don't crush the fan's frame.
9. **Close the notch.** Fill what's left of the cable notch with foam or silicone, so flies can't use it.

The lid bolts stay reachable from above with everything fitted, so you can take the whole unit off the lid
in one piece.

## Fitting another fan

Measure the fan and set these. Only `--fan-size` is needed for a standard fan.

- `--fan-size`: the outside size. Standard sizes (60, 70, 80, 92, 120, 140, 200) get their usual hole spacing,
  and other sizes must give `--fan-hole-spacing`. 200 mm fans vary, so check yours: 154 mm is assumed.
- `--fan-thickness`: the bolt length and socket depth follow it.
- `--fan-corner-r`: the socket's inside corners. If the fan's corners are squarer than 3 mm and it won't drop in,
  lower this.
- `--cable-side`, `--cable-offset`, `--cable-notch-width`, `--cable-notch-depth`: seen from above with the long
  side left to right. Offset is along that side from its middle: toward the right on `back` and `front`,
  toward the back on `left` and `right`. `--cable-notch-width 0` leaves the notch out.
- `--mesh-lift`: raises the rim above the fan if the cable stands proud of the fan's top, so the mesh clears it.
  Add washers of the same thickness on the bolts between the mesh and the fan, so the fan stays clamped.

`--base-length` follows `--fan-size` unless you set it. A longer base gives the air a bigger opening, as long as
it fits your lid's flat area.

## Options

Sizes are in mm.

| Option | Default | Range or choices | What it does |
|---|---|---|---|
| `--lid-thickness` | 2 | 0.5–15 | thickness of the box lid (sets the bolt length) |
| `--lid-flat-width` | 95 | 20–1000 | flat area of the lid, short side |
| `--lid-flat-length` | 230 | 20–1000 | flat area of the lid, long side |
| `--fan-size` | 140 | 60–200 | fan's outside size |
| `--fan-thickness` | 25 | 10–60 | fan thickness |
| `--fan-hole-spacing` | auto | 40–190 | distance between the fan's bolt holes (auto: the standard for the fan size) |
| `--fan-corner-r` | 3 | 0.5–20 | corner radius of the fan, and of the socket's inside corners |
| `--fan-fit` | 0.3 | 0–2 | gap around the fan in its socket, each side |
| `--socket-wall` | 2.4 | 1.2–6 | socket wall around the fan |
| `--mesh-lift` | 0 | 0–10 | how far the rim stands above the fan |
| `--cable-side` | right | right, left, back, front | side of the socket with the cable notch |
| `--cable-offset` | auto | −100–100 | notch's distance from the middle of that side (auto: fan size ÷ 4 toward the front or left) |
| `--cable-notch-width` | 6 | 0–30 | notch width (0: no notch) |
| `--cable-notch-depth` | 5 | 1–30 | notch depth from the rim |
| `--base-width` | 90 | 30–300 | outside of the duct at the lid, short side |
| `--base-length` | auto | 30–300 | outside of the duct at the lid, long side (auto: the fan size) |
| `--wall` | 3 | 2–5 | duct wall at the lid, and the rim of the lid opening |
| `--duct-height` | 55 | 25–300 | lid to the fan's seat |
| `--fan-bore` | auto | 40–196 | round opening under the fan (auto: fan size − 4) |
| `--flange-thickness` | 6 | 3–15 | thickness of the duct's foot on the lid |
| `--ear-length` | 18 | 5–40 | how far the bolt ears stick out past the duct |
| `--ear-width` | 20 | 12–60 | bolt ear width |
| `--plate-ledge` | 3 | 1.5–10 | plastic between the nuts and the lid in the plate |
| `--frame-thickness` | 5 | 2–15 | mesh frame thickness |
| `--frame-opening` | auto | 30–196 | round opening of the mesh frame (auto: fan size − 8) |
| `--mesh-thickness` | 0.5 | 0–3 | wire mesh thickness (bolt length only) |
| `--bolt-d` | 4 | 2–6 | bolt diameter |
| `--head-d` | 8 | 4–14 | countersunk bolt head diameter |
| `--nut-af` | 7 | 3–12 | nut across its flats |
| `--nut-height` | 3.2 | 1–6 | nut height |
| `--bed-chamfer` | 0.4 | 0–1 | chamfer where a part touches the print bed |

The build refuses sizes that don't work and says why: a base wider than the lid's flat area, a flare too
steep to print without supports, lid bolts a hex key can't reach under the socket, a cable notch in a corner,
and so on. Nothing is written in that case.
