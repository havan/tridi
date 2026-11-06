# Bar holder

Snap-in holders for the bars in a drying box, such as a biltong box made from a plastic storage box. A strip of
U-shaped cradles bolts to the inside of the wall, with a backplate on the outside to spread the load over the thin
plastic. Bars press in from above and pull out by hand for cleaning. Print one set for each of two opposite walls.

```
pixi run build barholder                                   # 3 cradles for 20 mm bars, 70 mm apart, on a 2 mm wall
pixi run build barholder --preset test_fit                 # one cradle: try the snap on your wood first
pixi run build barholder --bar-d 25 --pitch 80 --count 2   # other bars, other spacing
pixi run build barholder --cradle-depth 40 --bracket       # deep cradles with a support bracket underneath
pixi run build barholder --wrap 180                        # a plain half circle, no snap
pixi run build barholder --no-backplate                    # washers instead of a plate
pixi run build barholder --no-drain                        # closed cradle floor
pixi run build barholder --help                            # every option
```

Output goes to `out/barholder/<variant>/`: `strip` and `backplate` as STL and 3MF, already rotated for printing,
plus `assembly.step`, an `.FCStd` and `summary.txt`. The summary lists the bolts to buy, where to drill and which bar
lengths fit.

## Sizing the fit

- **`--bar-d`:** measure your bars with calipers, since wood varies and swells. `--bar-fit` is the gap around the bar
  once it's seated.
- **`--wrap`:** how far the cradle wraps round the bar. At 180° the bar lifts straight out, and at the default 225°
  the mouth is about 1 mm narrower than the bar. The snap's stiffness is a calculated estimate, not a measured one,
  so print `--preset test_fit` first. If it's too stiff, lower `--wrap`, `--cradle-wall` or both.
- **`--cradle-depth`:** deeper cradles forgive shorter bars, and storage box walls usually lean outward, so the gap
  between them grows with height. The summary gives the range of bar lengths that fit.
- **`--count`:** a strip longer than your printer's bed is refused. Mount several strips side by side on a long wall.

## What to buy

For one default strip:

| Qty | Part |
|---|---|
| 4 | M4×10 countersunk hex-socket bolt (ISO 10642 / DIN 7991) |
| 4 | M4 hex nut (DIN 934: 7 mm across flats, 3.2 mm high) |

Without the backplate it's M4×8 pan-head bolts with a washer outside the wall. Use stainless steel near food.

## Fitting

1. Hold the backplate on the outside of the wall as a drilling template and mark the holes. Drill 4.5 mm. Keep both
   walls at the same height so the bars sit level, and check that the area is flat: no ribs or handles behind it.
2. Press a nut into each pocket on the strip's back.
3. Hold the strip inside and the plate outside, and tighten the bolts from outside the box.

## Printing

No supports, no brim. Each part is exported the way it should print, wall side down:

- **Strip:** the cradles stand up from the bed, so the layers follow the U and the snap arms flex along their layers
  rather than across them. Above the strip the arms rise on a 45° slope. Without it they'd be fused to the strip all
  along their depth and far too stiff to snap near the wall. The only overhangs are short bridges over the nut pockets,
  the bolt holes' ends and the drain.
- **Backplate:** bolt seats up.

Suggested settings: PETG, or ASA if there's a heat source in the box, since PLA softens at around 55–60 °C and doesn't
like sitting under load in the warm. Use a 0.2 mm layer height, 4 walls and 20% infill. The summary's weights are for
solid parts, so the real ones are lower. Meat touches the bars, not the holders.

## Details

- **The seat stops at the strip's front**, so a bar's end never reaches the wall.
- **Nothing metal shows inside.** The nuts sit between the strip and the wall, and the bolt holes are blind. A bolt
  long enough to break through is refused, with the strip thickness it would need.
- **The drain** is a short gap in the floor against the stop, where drips collect, since a wall leaning outward tips
  the bar's wall end down. The ring stays closed in front of it.
- **The bracket** is two ribs per cradle, either side of the drain, down to a foot on the wall. The foot pushes against
  the wall, so it needs no bolt of its own, and the backplate grows to back it up. You won't need it for 1–2 kg on a
  25 mm cradle. It's there for deep cradles.
