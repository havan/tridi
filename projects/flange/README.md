# Flange

An air vent for the side wall of a drying box, such as a biltong box. It bolts over a hole in the wall to let air
in or out and keep insects out. Use it with the [`fanbox`](../fanbox/) on the lid.

```
pixi run build flange                                   # round, two pieces, 4 bolts, for wire mesh
pixi run build flange --shape slot                      # long slot, 8 bolts
pixi run build flange --fixing centre_bolt              # no bolt holes in the wall
pixi run build flange --mesh grid                       # printed mesh, no wire needed
pixi run build flange --shape slot --mesh honeycomb --mesh-hole 1.2
pixi run build flange --preset slot_centre
pixi run build flange --help                            # every option
```

Output goes to `out/flange/<variant>/`: `outer` and `inner` as STL and 3MF, already placed for printing, plus
`assembly.step`, an `.FCStd` and `summary.txt`. The summary lists the hole to cut, what to buy and how much air
gets through.

## Options

Choose one of each. Every combination works.

| `--shape` | Opening | Outside, bolted through the rim | Outside, centre bolt |
|---|---|---|---|
| `round` | 50 mm | 78 mm | 66 mm |
| `slot` | 190 × 21 mm | 218 × 49 mm | 206 × 37 mm |

| `--fixing` | How it holds | The wall needs |
|---|---|---|
| `two_piece` | Outer and inner pieces squeeze the wall, with bolts through the rim | The big hole, and a hole per bolt |
| `one_piece` | Outer piece only, with nuts and washers inside. Uses the least plastic | The big hole, and a hole per bolt |
| `centre_bolt` | Both pieces, with bars across the opening to a hub and a bolt through each hub. Uses the fewest bolts | The big hole only |

| `--mesh` | What keeps insects out |
|---|---|
| `wire` | Wire fly mesh, clamped between the outer piece and the wall |
| `grid` | A square lattice printed into the outer piece |
| `honeycomb` | The same, with hexagonal holes |
| `slicer` | The opening prints solid, and your slicer's infill becomes the mesh. See below |

## What to buy

The summary gives the exact list for your variant. With default sizes, every variant uses M4×12 countersunk
hex-socket bolts (ISO 10642 / DIN 7991) and M4 hex nuts (DIN 934: 7 mm across flats, 3.2 mm high).

| | Bolts and nuts |
|---|---|
| Round, rim bolts | 4 of each |
| Slot, rim bolts | 8 of each |
| Round, centre bolt | 1 of each |
| Slot, centre bolt | 3 of each |

`one_piece` also needs one M4 washer per bolt. `wire` needs wire fly mesh: start from the sheet size in the summary,
which is 2 mm smaller than the outside size, and trim it to the outer piece's outline so no cut edges show.

## Printing

No supports, no brim. Each part is exported the way it should print:

- **Outer piece:** wall side down, head seats up. Printed mesh lies flat on the bed, so from outside it sits
  recessed inside a raised frame.
- **Inner piece:** wall side up. The collar and hub stop face up, and the nut pockets are on the bed with short
  bridges over them.

Suggested settings: PETG, or ASA if there's a heat source in the box, since PLA softens at around 55–60 °C. Use a
0.2 mm layer height, 4 walls and 20% infill. The summary's weights are for solid parts, so the real ones are lower.

## Assembly

1. **Cut the wall.** The summary gives the hole's size. For a slot, drill a hole at each end and cut between them.
2. **Drill the bolt holes,** unless it's `centre_bolt`. Use the outer piece as a template.
3. **Nuts.** Press them into the inner piece's pockets. If one is loose, a dab of glue holds it.
4. **Wire mesh,** if you're using it. Lay it over the hole on the outside of the wall and poke the bolts through.
5. **Bolt it together.** Outer piece outside, inner piece inside with its collar in the hole, and tighten from
   outside until snug. On `one_piece`, put a washer and nut on each bolt inside instead.

On `one_piece`, and on `centre_bolt` where the rim is only held through the bars, put foam tape or food-safe silicone
under the rim. If you use tape, set `--seal-thickness` so the bolt lengths allow for it.

## Adjusting the fit

- `--wall-thickness`: everything that depends on the wall follows, including the bolt length.
- `--collar-height`, `--collar-wall`, `--collar-fit`: the lip that fits into the wall hole, centres the flange and
  covers the cut edge. `--collar-height 0` leaves it out.
- `--hub-stop`: on `centre_bolt`, the boss on the inner hub that stops overtightening from bending the bars. By default
  it leaves a 0.5 mm gap between the hubs, with any wire mesh in place. Make it smaller and the bolt can squeeze the pieces harder. `0` leaves it out.
- `--rim-bolts`, `--hubs`, `--bars`, `--hub-d`, `--bar-width`, `--rim`: fewer bars or narrower ones let more air through.
- `--mesh-hole`, `--mesh-rib`, `--mesh-thickness`, `--mesh-angle`: the printed mesh.

## Air

Printed mesh blocks a lot of air. Holes are always whole, never clipped at an edge, so the plastic beside each hole is
at least one rib wide. With 1.5 mm holes and 0.8 mm ribs:

| Variant, with printed grid | Open area | Flanges to match a 140 mm fan's full 13,000 mm² |
|---|---|---|
| Round, rim bolts | about 730 mm² (37%) | about 18 |
| Slot, rim bolts | about 1,390 mm² (36%) | about 10 |
| Slot, centre bolt | about 1,040 mm² (27%) | about 13 |
| Round, centre bolt, four bars | about 330 mm² (17%) | about 39 |

A drying box doesn't have to match the fan's full capacity, so treat this as a comparison. For more air, use wire mesh,
a larger opening or fewer bars.

## Slicer mesh

`--mesh slicer` exports `outer` with the opening solid, and a `mesh_zone` shape marking where the mesh should be.

1. Select `outer` and `mesh_zone` together and open them at once. If the slicer offers to treat them as one object
   with several parts, accept, because that keeps them lined up. Then change `mesh_zone`'s type to a modifier.
2. If it doesn't offer that, load `outer`, then right-click it and add `mesh_zone` as a modifier from a file. Some
   slicers then place it by their own rule, so move it into the opening's centre, flat on the bed.
3. Give the modifier these settings, with a line width of 0.45 mm. About 45% density should give holes of about 1.5 mm.

| Setting | PrusaSlicer | Orca Slicer, Bambu Studio |
|---|---|---|
| No solid layers | Top and bottom solid layers: 0 | Top and bottom shell layers: 0 |
| No outline | Perimeters: 0 | Wall loops: 0 |
| Pattern | Fill pattern: Grid | Sparse infill pattern: Grid |
| Density | Fill density: 45% | Sparse infill density: 45% |

Check in the slicer's preview that the mesh appears only inside the opening. These steps are from memory, not tested
in a slicer yet.

## Check on a first build

None of this has been printed yet. Sizes come from calculation, so on a first build check:

- whether insects stay out. The 1.5 mm hole and its 2 mm warning limit are estimates: tiny fruit flies can get through.
- whether enough air moves.
- how the parts fit. The slicer settings above are also untested.
- on a long `centre_bolt` slot, whether the rim's ends stay tight against the wall, 35 mm past the last bar.

## Overruling a check

The build refuses a size that shouldn't work, and writes nothing. If you know better, `--force` builds it anyway and
lists what it overruled in the summary. It overrules the size checks, the mesh hole limit, the nozzle check, parameter
ranges and the printer fit check.

It can't overrule an unknown parameter, a value that isn't a number or a listed choice, or a shape the geometry
kernel can't make into one valid solid. Those still stop the build, because there's nothing to print.
