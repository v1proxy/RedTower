# Herb Tower: gantry assembly

**Gantry Rev D · 2026-10-20 · all dimensions mm**

Read alongside the 29-page booklet `Gantry_Assembly_Instructions_RevD.pdf`
(step numbers below are the booklet's) and `HerbTower_Gantry_BOM_RevB.xlsx`.
Steps 1 to 20 happen on a bench. Steps 21 to 27 put it in the cabinet.

---

## What changed, and why

**Rev C → Rev D: the gantry mechanics, redrawn from how C-Beam hardware
actually goes together.**

| Rev C drew | Correct | Consequence |
|---|---|---|
| Wheels on the beam's front-face grooves, 60 apart | Wheels **straddle** the 80 mm beam and ride the grooves on its **top and bottom** faces, **100.6** apart | Every carriage drawing redone |
| Plate 16 mm off the beam | Screw, plate 6, spacer 6, wheel 10.23, **nyloc**: plate back **1.1 mm** off the beam | Transit clearance at 559 deep is **22.8 mm**, not 25 |
| Wheel screws M5 × 27, no nut | **M5 × 30 + M5 nyloc**: 27 never reaches the nyloc's nylon ring | BOM C05 changed, C06 added |
| X motor mid-rail, belt loose in front of the rail, two idlers | Motor at the rail's **left end**, belt **inside the channel**, width along the pulley axis, **one** idler at the far end | Carriage can travel; D03 qty 2 → 1 |
| Pulley 8 mm bore | **6.35 mm**, to match the X motor's shaft | BOM D02 |
| Motor screws from the plate side | **From the motor side**: NEMA 23 flanges are drilled through; the plate's motor holes are tapped M5 | |
| Thrust bearing at each screw end | **Both at the top end plate**, one each side, locked by collars: the screw hangs; the coupler carries only torque | BOM D15 end plate + D16 collars added |
| Mast foot at 309 | **289**: at 309 the top collar was 0.5 mm under the cabinet top | |

**Rev B → Rev C: the cabinet is 559 deep, not 457.** The arm crosses a tray
plane on every tier change. The shortest fold it can reach without one link
touching another is **162.6 mm** long (set by its own shoulder housing,
found by collision-checking 83,607 poses on Elephant Robotics' mesh). At
457 deep it overlaps the tray by 79 mm. Booklet step 22 has the table.

---

## Before you start

**Tools.** 2, 2.5, 3 and 4 mm hex keys; a thin 8 mm spanner for the
eccentrics; a 5.2 mm drill; an M5 tap; a spirit level; a miter saw with a
non-ferrous blade; a multimeter; a ferrule crimper.

**Check on arrival:** the X motor's shaft is 6.35 mm (it decides the pulley
bore and the coupler); the C-Beam is `LR-C-S` (silver); the wheel screws are
30 mm, not 27.

**Cut the X rail to 1397.** The Z mast keeps its full 1500.

---

## Carriages (steps 1 to 5)

1. The XL plate's two **5.1** holes on one diagonal take the fixed wheels;
   the two **7.2** holes take the eccentric spacers.
2. Fixed wheels: M5 × 30 low profile through the plate, 6 mm spacer, wheel,
   nyloc. Snug, not torqued.
3. Eccentrics: the spacer's round boss drops into the 7.2 hole and its 8 mm
   hex is the spacer. Wheel, nyloc. Set both at their **loosest**.
4. Slide the carriage onto the rail from the end: the wheels straddle the
   beam and ride its top and bottom grooves. **Set preload** with a thin
   8 mm spanner on each hex, from the side, between plate and wheel: just
   grips the groove, then back off to light finger drag. Lock the nylocs,
   re-check, run the full length by hand.
5. Build the second carriage the same way, on the Z mast.

## X drive (steps 6 to 10)

6. **Motor onto its plate.** Four M5 × 10 **from the motor side**, heads on
   the back of the flange, threads into the plate. Tap the plate's motor
   holes M5 first if they are plain.
7. **Pulley onto the shaft, now.** Boss toward the motor; the toothed hub
   finishes 22 to 32 mm behind the plate. First grub screw on the shaft flat.
   After step 8 these grubs are inside the rail's channel and out of reach.
8. **Motor assembly onto the rail's left end**, flush with the end, plate
   on the two front lips: four M5 × 10 into T-nuts in the lip grooves. The
   pulley goes into the channel.
9. **Idler at the far end.** Drill 5.2 through the web, 50 from the end, at
   mid-height. M5 × 40 from the back; then in the channel: washer, idler,
   washer, nyloc (snug, the idler must spin).
10. **Belt and clamps.** Two clamp blocks on the back of the X carriage
    reach into the channel. Clamp one end, run the belt left round the
    pulley, back along the bottom of the channel, round the idler, into the
    second clamp. Tension: a low clear note when plucked.

## Z drive (steps 11 to 14)

11. Nut block on the back of the Z carriage, bore along the mast, two
    M5 × 12 from the front. Do not crush the anti-backlash spring.
12. Thread the lead screw through the nut along the channel centreline.
    Turn it by hand end to end.
13. **Top end:** end plate into the mast's end taps (4 × M5 × 12), a thrust
    bearing each side of it, a lock collar each side. The screw hangs here.
14. **Foot:** motor plate across the mast end, braked NEMA 23 outside,
    coupler inside with a 2 mm gap between the shaft ends. Test the brake
    before coupling: 24 V releases, no power grips.

## Electronics, first motion, safety, arm (steps 15 to 20)

15. Limit switches in the rail's **back** top groove (the front one is the
    wheels'). Trip 5 to 10 mm before the hard stop. **Normally closed**, in
    series per axis. Same on the mast.
16. Controller on M3 standoffs, off the frame.
17. Driver current, jog 5 mm, calibrate steps/mm, home, run full travel ten
    times.
18. Arm plate onto the Z carriage, four M5 × 12, central in its slots.
19. Arm onto the plate, four M4 × 10, **side mounted** (J1 horizontal). Own
    power brick. Confirm TCP before coordinated motion.
20. Safety circuit: E-stop both channels into the G9SE-201, 13/14 feeds
    motion only. E-stop mid-move, power-cut, limit and backlash tests.

## Into the cabinet (steps 21 to 27)

21. The cabinet is **1397 × 559 × 1829**. Nothing of the frame sits behind
    the tray line at y = 203.
22. Why it is 559 deep (table: 457 / 533 / 559).
23. X rail against the front faces of the rear uprights, channel forward,
    bottom edge at 1709; brackets on its top and bottom faces at each end.
    **Level it**: tilt becomes height error across the 1126 mm of travel.
24. X carriage and X drive on, then hang the mast: six bolts into the
    mast's back face. Top at **1789**, foot at **289**. Check plumb both
    ways at mid-rail and at each end.
25. Z drive in place: top collar 20.5 under the cabinet top; motor bottom
    at 164.
26. Z carriage, arm plate, arm. **Fold before the first Z move**: J2 −110,
    J3 −80, J4 −140, J5 −90. Collision checked.
27. Commission (below).

### Envelope

| | |
|---|---|
| X travel | 1126, carriage centre 163.5 to 1290 (motor plate to idler) |
| Z travel | 1350 usable; tiers at 345, 1005, 1437 |
| Flange reach | 292.6 from J1, forward to y = 96 |
| With the gripper | forward to y = 6: the whole 203 mm tray |
| Folded transit | 162.6 long, 22.8 clear of the tray line |
| Working height | 263, inside the 341 tier opening |

The arm's ±150 lateral reach covers the full tray width from anywhere in
that X travel.

### Commissioning checks

- [ ] Home, power-cycle, home again: same zero.
- [ ] Fold the arm, run Z full travel: nothing touches.
- [ ] E-stop mid-move: motion stops, brake grips, no reset until released.
- [ ] Pull the plug mid-travel: the mast holds.
- [ ] Each tier: the arm reaches the back row of pots.
- [ ] Hand-eye calibrate at the tier it works at.

The mast is a 1.5 m cantilever off four V wheels: expect 1 to 2 mm of
forward lean at the foot. If worse, gang a second XL plate onto the X
carriage.

---

## Where the geometry comes from

| | |
|---|---|
| `parts.py` | every part at real dimensions, with sources |
| `assy.py` | the carriage, X drive and Z drive sub-assemblies, in one place |
| `frame.py` | the cabinet, the gantry's place in it, `clearances()`, `cut_report()` |
| `arm280.py`, `dae.py` | the 280 Pi from Elephant Robotics' URDF and meshes |
| `collide.py` | link-pair self-collision; how the fold was found |
| `kit3d.py` | modelling, and a z-buffered, hidden-line renderer |
| `make_steps3.py` | the booklet |

The booklet and the cabinet model both build from `assy.py`, so they cannot
disagree. Re-run `python3 make_steps3.py` after any change.
