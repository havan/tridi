# Cable grommet: design

Date: 2026-11-07. Status: draft, awaiting the user's approval.

## Intent

A printed grommet for one wire through a thin wall. The first use is a heater sheet's wire entering a biltong box near
the bottom of its side wall. The wall is plastic and 2 mm thick, the heater is 30 W, and the air inside stays under
35 °C.

It does two jobs, both from the user:

- Stop the wire rubbing on the edge of the hole, which would damage it over time.
- Hold the wire tight so it can't be pulled out. "Anything can end up pulling on it."

The user measures their wire and generates a grommet to fit. Their first wire is 5 × 2.5 mm: two round cores joined
side by side, with a groove between them. They also have round cables. They don't recall ever seeing a truly
rectangular one, but want it available as an option.

The idea comes from *Parametric Cable Grommet* by theo.fieber (BY-NC-SA), which the user likes for its split halves and
two-piece nut, because they fit around a wire that's already in place. The printable version suits thick walls only:
measured on the 15 mm 3MF, its threads start about 14 mm above the flange, so on a 2 mm wall the nut can't reach the
wall. The Fusion 360 files do have a hole-depth setting, but their author warns of glitches at other sizes, and they
need Fusion to change.

This is a new parametric model in FreeCAD, following the same idea. It doesn't use that model's files.

## Goals

- One command produces print-ready parts for a measured wire and a given wall thickness.
- The nut clamps the wall directly on a 2 mm wall, and the same design still works on a thick wall such as a table.
- The whole grommet fits around a wire with both ends already attached.
- Every part prints on a common FDM printer without supports.
- A hard pull from either side doesn't move the wire, and doesn't damage it.

## Non-goals

- Waterproofing.
- More than one wire through a grommet.
- Curved walls. The wall is treated as flat where the disc and nut sit.
- Electrical certification. This is a printed household part, not a rated strain relief.

## Anti-goals

Any of these makes the design a failure even if it builds:

- A grip that cuts or crushes the wire's insulation, or that squeezes harder the more the nut is tightened.
- Sharp teeth or edges touching the wire.
- A gap a fly can get through at default settings.
- A default build that needs supports.
- A setting that silently produces a grommet whose nut can't clamp the wall. With `--force`, it's reported in the summary.

## Layout

The user chose this layout from to-scale mockups: **short, with a flat disc outside and the nut inside.**

```
 outside │ wall │ inside
   disc  │      │  nut
         │      │
 ════════╪══════╪═════════ wire, held between the two halves
```

From the outside face inward, at the user's size:

| Section | Length |
|---|---|
| Disc | 2.5 mm |
| Wall | 2 mm |
| Nut | 7 mm |
| Spare thread past the nut | 1.5 mm |
| **Total** | **13 mm, about 2.5 mm outside and 8.5 mm inside** |

The threads run all the way down to the disc on a thin wall. That is the change that makes a thin wall work. *Changed
while building:* on a thick wall the stem is plain until two pitches before the nut's position, because a long thread
is slow to build and the nut never needs it there. The parts could also be
fitted the other way round, nut outside, with no change to the model.

## Parts

Four parts, with no hardware to buy:

- **`body_a`, `body_b`:** the two halves of the disc and threaded stem. The split runs along the wire's flat side,
  through the axis, so the wire lies in the split plane.
- **`nut_a`, `nut_b`:** the two pieces of the ring nut, with a scalloped edge for fingers.

### How it goes together

1. Lay the wire in one body half, close the other over it, and push the closed body through the hole from outside.
2. Inside the box, join the nut's two pieces around the wire, just past the end of the body.
3. Screw the nut onto the body by hand until it's tight against the wall, holding the disc so the body doesn't turn.

The nut is joined before it meets the threads, so the two pieces never have to line up with a thread while being put
together. Once on the threads, they can't slide apart.

**The wire still has to get through the hole.** The split lets the grommet close around a connected wire, but one end
of that wire must have passed through the wall first. The user's current wire has one free end, so any hole works. But
they also want to handle a cable with a connector on each end without cutting it, by making the hole bigger: that's
what `hole_d` is for, rather than always being worked out from the wire.

## Parameters

Each has a range, a CLI flag and preset support, as in `flange`. Everything marked auto can be overridden.

### What you measure

| Parameter | Default | Meaning |
|---|---|---|
| `wire_shape` | `twin` | `twin` (two round cores joined side by side), `round`, or `flat` (rectangular) |
| `wire_width`, `wire_height` | 5, 2.5 | size of a `twin` or `flat` wire, mm |
| `wire_d` | 6 | round wire's diameter, mm |
| `hole_d` | auto | the hole to cut. Set it larger so a connector fits through; see below |
| `wall_thickness` | 2 | the wall, mm. The minimum is whatever the thread needs to engage fully; the builder sets it |

### Sizes worked out from those

| Parameter | Rule | Your wire |
|---|---|---|
| `body_wall` | plastic from the slot to the thread's root, default 2.5 mm, at least 2 mm so the mouths stay inside it | 2.5 mm |
| `hole_d` | when auto: smallest whole or half millimetre that fits the thread's minimum size + 0.5 mm | 13 mm |
| `disc_d` | hole + 11.5 mm | 24.5 mm |
| `disc_thickness` | default 2.5 mm | 2.5 mm |
| `nut_d` | thread's outside diameter + 8 mm, or more if the joint needs it, rounded up to a half millimetre | 21.5 mm |
| `nut_height` | default 7 mm. The grip runs under the nut, so a taller nut is what lengthens the grip | 7 mm |

The minimum thread size is the slot's largest size plus twice `body_wall` at the root, and 2 mm more at the outside:
for the user's wire, a 5.2 mm slot gives 10.2 mm and 12.2 mm, so the hole rounds up to 13 mm. The thread's actual
outside diameter is then always `hole_d` − 0.5 mm, 12.5 mm here. Rounding to a half millimetre means the hole can be
cut with a common drill bit.

Setting `hole_d` larger makes the thread, disc and nut grow with it, with the slot unchanged. The summary reports what
that does to the flat wall needed and the lowest position on the wall, since a big grommet can't sit as near the floor.

Stem length past the disc is `wall_thickness` + `nut_height` + 1.5 mm, so a thicker wall gets a longer body
automatically.

## The grip

This is the riskiest part of the design and has not been tested. All the numbers here are *my call*, chosen to be
tuned on a real print.

The slot has two zones.

- **Grip zone, only under the nut.** This is the one stretch where something forces the halves together. Separate
  rounded ridges on both faces, staggered so a ridge on one side faces a dip on the other. Between ridges the slot
  relaxes back to the wire's full height, so the insulation has room to move and the halves need much less force to
  close than if the whole face were squeezed. The wire is pressed locally and takes a small wave.
- **Clear zone, everywhere else.** The slot is the wire's size plus 0.1 mm of height in total, with no ridges. This
  includes the stretch through the disc and wall, and past the nut. Nothing pushes the halves open here, so nothing
  needs to hold them shut except the locating features and the hole. On a thick wall, this zone simply gets longer and
  the grip stays the same.

| Parameter | Default | Meaning |
|---|---|---|
| `grip_squeeze` | 0.2 mm | how much smaller than the wire the slot is at a ridge's top, measured square to the wire |
| `grip_wave` | 0.2 mm | how far each ridge and dip shifts the wire off centre |
| `grip_pitch` | auto, about twice the wire's height | spacing of ridges on one face |

Rules the geometry must keep:

- **Ridge tops are rounded,** with a radius of at least 1 mm. No sharp edges anywhere the wire touches.
- **The squeeze has a hard limit.** The halves close face to face. Nothing about tightening the nut can make the slot
  smaller than the wire by more than `grip_squeeze`.
- **The wave stays gentle.** The wire's centre line doesn't bend tighter than a radius of about its own thickness. The
  wave in the mockup was drawn stronger than this allows. On the short layout the grip therefore comes mostly from
  friction and the ridges pressing in, not from the wave.
- **Width:** on `twin` and `flat` wire, the slot is 0.2 mm wider than the wire in total. On round wire, the slot is a
  round channel with the same two zones.
- **Mouths:** both ends of the slot flare open, by at least 1.5 mm, so a sideways pull doesn't bend the wire over an
  edge. The disc-side flare must stay printable: see Printing.

**How the halves get closed.** The nut's load on the wall pushes on the thread's angled flanks, which pushes the
halves together under the nut. This is what must overcome the wire's resistance at the ridges, so it needs checking
first on the test print. If the halves don't close by hand, tell the user rather than quietly weakening the grip.

**What to expect from the short layout.** The user chose it over a longer one. The grip zone is about 7 mm, so it holds
only two or three ridges. `nut_height` is there if the pull test shows it needs more, at the cost of sticking further
into the box.

### Slot shape for each wire

*My calls,* since the wire's exact shape varies between makers:

- **`twin`:** rounded ends matching the cores, with a low rib along each face that sits in the wire's groove. The rib
  closes the fly route along the groove and stops the wire twisting in its slot. It must not press on the wire: it's
  kept short of the groove's bottom, because the insulation between the cores is the thinnest and easiest to tear.
  `groove_rib` sets its height, default 0.3 mm, and 0 leaves it out.
- **Where a `twin` is gripped:** the ridges run across both cores, so they do press over the conductors. That is why
  `grip_squeeze` is small and the tops are rounded. The inspection step below checks it on the real wire.
- **`round`:** a plain round channel.
- **`flat`:** a rectangle with small rounded corners, about 0.5 mm radius.

## Threads and nut

*My calls,* to be confirmed on the test print:

- Single-start trapezoidal thread, 2.5 mm pitch and 1 mm deep, with flanks at 45° so both the stem and the nut print
  without supports. That leaves 0.5 mm of flats per turn, and about 2.8 turns in the nut. Pitch is adjustable as
  `thread_pitch`.
- Radial clearance between the threads follows the printer's `clearance` by default, adjustable as `thread_clearance`.
- The nut's two pieces join with a T-shaped tab sliding along the axis, as on the original. `nut_a` carries both tabs
  and `nut_b` both sockets. Tabs start on the bed and sockets are closed at the far end with a short bridged roof, so
  the tab stops where the thread lines up. *Changed while building:* sockets closed at the bed end would have left the
  tab overhanging in mid-air.
- At 4 mm of radial wall, the joint is tight at a 0.4 mm nozzle. The builder must check that the tab's neck and the
  walls around the socket are printable, and grow `nut_d` to suit, up to about 23 mm for the user's wire.
- The two body halves must line up along the axis to within about 0.2 mm, or the thread won't run across the split and
  the ridges won't stagger properly. Some locating feature on the split faces has to do that without supports. Which
  one is left to the builder.
- The disc's edge is textured for fingers, since the body must not spin while the nut is tightened or it will twist
  the wire.

## Flies

*My call,* carrying over the rule from `flange`: at default settings, no route into the box wider than 0.5 mm. The hole
is covered by the disc on one side and the nut on the other. The split line closes face to face, and the slot is closed
by the wire, whose width has only 0.2 mm of play in total. On `twin`, the rib in the groove keeps the channel along it
under the limit.

## Printing

No supports and no brim. Each part is exported rotated for printing:

- **Body halves:** standing up, disc on the bed, as on the original. The split face is vertical, so the ridges and
  thread stay within 45° of vertical.
- **The disc-side mouth** flares toward the bed, so it's an overhang. Its curve must stay within about 45°, even if it
  ends up less rounded than the other mouth.
- **Nut pieces:** flat on the bed.
- The bed's first-layer chamfer works as in `flange` (`bed_chamfer`, 0.4 mm), except on faces that close together, such
  as the body's split faces and the nut's joints.

Material advice in the README: PETG recommended. PLA should do at 35 °C as long as the grommet doesn't touch the heater
sheet, since it softens at about 55–60 °C.

Layer lines run across the stem, which is its weakest direction under a pull. The pull test below has to cover that.

## Checking on a real print

*My call:* there's no special test part. The grommet is small enough that the real parts are the test. The README
explains how to:

1. Check the nut screws on by hand. If it binds, raise `thread_clearance`.
2. Fit it to a scrap of the real wire and check the halves close.
3. Hang about 3 kg from the wire for a minute, in each direction. The wire shouldn't move.
4. Take it apart and look at the insulation: light marks are fine, but cuts or flattening aren't. If it's marked, lower
   `grip_squeeze`. If the wire slipped, raise `nut_height` first, then `grip_squeeze`.

The 3 kg is *my call*, a stand-in for a firm yank.

The README also says, because the voltage hasn't been given: this printed part isn't a certified strain relief. On
mains, use it only with double-insulated wire.

## Sizing checks

As in `flange`: a clear refusal naming the parameter, with nothing written, overruled by `--force` and reported in the
summary. *My call* to include `--force`, for consistency. Examples:

- `hole_d` too small for the wire and `body_wall`.
- `disc_d` too small to cover the hole with a usable lip.
- `nut_d` too small for the joint at the printer's nozzle.
- `grip_squeeze` over about 15% of the wire's height, since that risks crushing it.
- The wall too thin or thick for the nut to clamp it.
- `grip_wave` or `grip_pitch` that would bend the wire too tightly.
- `groove_rib` tall enough to reach the middle of a `twin` wire.

## Output

`pixi run build grommet ...` as a new `projects/grommet/`, with presets, README and tests as in `flange`, and a line in
the repo's README.

The defaults are the user's 5 × 2.5 mm `twin` wire on a 2 mm wall. Example presets include a round wire, a rectangular
wire, a thick wall, and a bigger hole for a connector.
*My call:* the builder adds a `[grommet.biltong]` table to the user's untracked `local.toml`, as with their flange.

`summary.txt` adds:

- The hole to cut.
- How close the hole's centre can be to the inside floor: nut radius + 1 mm, about 11.75 mm for the user's wire.
- How much flat wall is needed: `disc_d` outside and `nut_d` inside. If the box's outside corner curves, the disc needs
  to clear that too.
- The tightest slot size next to the wire size, so the squeeze can be checked at a glance.
- That there is nothing to buy.

## Credit and licence

The README credits *Parametric Cable Grommet* by theo.fieber. The user agreed to put the `projects/grommet/` folder
under BY-NC-SA, matching the original, though the rest of the repo stays CC BY-NC. The README and the repo's licence
notes say so.

## Left to the builder

- Module layout and internal names, following `flange`.
- How to build the thread. The repo has no thread helper yet. It might be a helical sweep, or lofted sections if the
  sweep proves slow or fragile in FreeCAD. If it's reusable, it belongs in `src/tridi/features.py`.
- How to build the slot. Stacking cross-sections along the wire's path, or extruding a wavy side profile for `flat`,
  are both reasonable, as long as the shapes and limits above hold.
- How tall the T-tab is and where it sits around the nut, as long as the rules above hold.
- Exact wording of messages and summaries, preset names and the test split.
