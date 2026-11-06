# Grommet

A printed cable grommet for a thin wall, such as a biltong box's side. It stops a wire rubbing on the edge of the hole
and holds it against a pull. The body and nut both split in two, so the grommet closes around a wire that's already
connected. You measure your wire, and the sizes follow from that. There's nothing to buy.

It follows [Parametric Cable Grommet](LICENSE) by theo.fieber, whose threads stop too far from the flange to clamp a
thin wall. This is a new model with threads that reach the flange, and a grip designed not to crush the wire.

```
pixi run build grommet                                               # 5 × 2.5 mm twin wire, 2 mm wall
pixi run build grommet --wire-shape round --wire-d 6                 # a round wire
pixi run build grommet --wire-shape flat --wire-width 6 --wire-height 3   # a rectangular wire
pixi run build grommet --wall-thickness 20                           # a table top
pixi run build grommet --hole-d 20                                   # a bigger hole, so a connector fits through
pixi run build grommet --help                                        # every option
```

Output goes to `out/grommet/<variant>/`: `body_a`, `body_b`, `nut_a` and `nut_b` as STL and 3MF, already rotated for
printing, plus `assembly.step`, an `.FCStd` and `summary.txt`. The summary gives the hole to cut, how low on the wall it
can sit, and how tight the slot is at a ridge. A build takes a minute or so, and the threaded parts are the slow ones.

## Measuring your wire

| Wire | Shape | Measure |
|---|---|---|
| Two round cores side by side, with a groove between them | `twin` | `--wire-width` across both cores, `--wire-height` across one |
| Round | `round` | `--wire-d` |
| Rectangular | `flat` | `--wire-width`, `--wire-height` |

## The hole

The wire has to pass through the wall before the grommet closes around it. If one end of your wire is free, the default
hole is fine. If there's a connector on each end and you don't want to cut the wire, measure the smaller connector and
set `--hole-d` to fit it. The thread, disc and nut grow to match, so the grommet needs more flat wall and can't sit as
near the floor. The summary gives both.

## Printing

No supports, no brim. Print all four parts as exported: body halves standing on the disc, nut pieces on their wall face.
PETG is recommended. PLA should do in a box below about 35 °C, as long as the grommet doesn't touch a heater, since it
softens at around 55–60 °C.

## Fitting it

1. Cut the hole and feed the wire through.
2. Lay the wire in one body half and close the other over it, with the keys in the disc in their sockets.
3. Push the closed body through the hole from outside.
4. Inside, slide `nut_a`'s tabs into `nut_b`'s sockets around the wire, just past the end of the body, with the flat
   wall faces level. Join them from the wall face side, until the tabs stop.
5. Screw the nut on by hand, wall face first, holding the disc so the body doesn't turn and twist the wire. Stop when
   it's tight against the wall.

It can also be fitted with the nut outside, using the same parts.

## Check it on a real print first

None of the grip's numbers have been tested yet. The grommet is small enough to be its own test, so try it on a scrap of
your actual wire before fitting it:

1. **Nut:** it should screw on by hand. If it binds, raise `--thread-clearance`.
2. **Halves:** with the nut tight, the two halves should close together. If they stay apart, lower `--grip-squeeze`.
3. **Pull:** hang about 3 kg from the wire for a minute, in each direction. The wire shouldn't move.
4. **Insulation:** take it apart and look. Light marks are fine, but cuts or flattening aren't. If it's marked, lower
   `--grip-squeeze`. If the wire slipped, raise `--nut-height` first, since the grip runs under the nut, and then
   `--grip-squeeze`.

## Safety

This is a printed household part, not a certified strain relief. On mains, use it only with double-insulated wire. On a
`twin` wire the grip's ridges press over the conductors, so don't skip the insulation check.

## Options

Run `pixi run build grommet --help` for every option and its range. The ones you're most likely to want:

| Option | Default | What it does |
|---|---|---|
| `--wire-shape` | `twin` | `twin`, `round` or `flat` |
| `--wire-width`, `--wire-height` | 5, 2.5 | a `twin` or `flat` wire's size |
| `--wire-d` | 6 | a round wire's diameter |
| `--wall-thickness` | 2 | the wall |
| `--hole-d` | auto | the hole to cut |
| `--nut-height` | 7 | a taller nut grips more wire and sticks further into the box |
| `--grip-squeeze` | 0.2 | how much smaller than the wire the slot is at a ridge |
| `--thread-clearance` | printer's | gap between the nut and body threads |
| `--force` | off | build anyway when a check would refuse, and list it in the summary |

## Credit and licence

The idea comes from *Parametric Cable Grommet* by theo.fieber. This folder is [CC BY-NC-SA 4.0](LICENSE), unlike the rest
of the repo.
