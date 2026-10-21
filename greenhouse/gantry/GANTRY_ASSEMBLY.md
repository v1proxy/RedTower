# Maag: gantry assembly

Maag is the Modular Agentic Autonomous Greenhouse (the project was called Herb Tower
up to design 0.2.0).

**Gantry Rev E · design 0.3.0 · 2026-10-20 · all dimensions mm**

Read alongside the booklet `Gantry_Assembly_Instructions_RevE.pdf` (step
numbers below are the booklet's) and `Maag_Gantry_BOM_RevD.xlsx`.
Steps 1 to 20 happen on a bench. Steps 21 to 27 put it in the cabinet. The
booklet now opens with a rendered cover, the parts, the fasteners and a tools
page, and carries two wiring pages between steps 16 and 17.

---

## What changed, and why

**Rev D → Rev E: the drawings were mirror images, and the OpenBuilds parts
are now OpenBuilds' own geometry.**

Every Rev D view was drawn with a left-handed projection, so each one was the
mirror image of the real assembly: what the page showed on the left is on the
right. The renderer's view matrix is fixed and every page was re-checked. If you
marked up a Rev D page, re-read it in Rev E.

The OpenBuilds hardware is now modelled from bd_warehouse's transcription of
OpenBuilds' drawings rather than from photos:

| Rev D drew | Rev E (OpenBuilds' drawings) | Consequence |
|---|---|---|
| Wheels on a diagonal of the plate | **Fixed** wheels on one edge (5.1 holes), **eccentrics** on the other (7.2 holes) | Steps 1 to 4 redone |
| Eccentric 8 mm hex | **10 mm** hex, 2.5 mm boss into the 7.2 hole | Thin **10 mm** spanner, BOM C03 note |
| Stack: plate, spacer, wheel | Plate 6, spacer 6, **precision shim 1**, wheel 11, nyloc; plate **2.5** off the beam | BOM C07 shims ×8; each carriage is **8.5** deep, not 7.115 |
| Plate with a centre window | XL plate as drawn: counterbored wheel holes, tapped M5 grid, nut recess, no window | |
| Nut block on two M5 × 12 | Block 34 × 33 × 12 on **two 6 mm spacers**, M5 × 25 low profile, hex nuts in its pockets | BOM C04 spacers 4 → 6 |
| End plate 40 × 80 × 6 | **C-Beam End Mount 80 × 50 × 12**, 16.1 bearing recess, M5 × 25 into the end taps | BOM D15 |
| Low profile heads 2.8 tall | **1.5**: that is what fits the 2.5 mm gap to the beam | Do not substitute DIN 7984 |
| Cast corner brackets on the rail's top face at each end | The top depth rails sit on that face. **Bent 5052 brackets**, TOP and BOTTOM at each end | SendCutSend, BOM X03, X04 |
| Arm plate Rev A: radial slots | **Rev B**: tapped M3 for the G base, tapped M4 on the 44 square, countersunk M5 to the XL plate | `arm_plate_revB.dxf`, BOM R03 |
| No reset button | The G9SE-201 is wired for **manual reset**: an NO button T31 to T32, 24 V on T33 | BOM S07 |
| 13/14 fed the controller and the brake | **13-14** the controller, **23-24** the brake coil, low side through the controller's MOSFET 1 | Wiring pages |

**Numbers that moved with the carriage stack.** J1 axis 385.65 from the front
(was 388.4); the folded arm clears the tray line by **20.0** (was 22.8); X travel
**1086** (carriage centre 163.5 to 1249.75). `design/params.py` carries
`CARR_STACK = 8.5` and `TRANSIT_CLEAR = 20.0`, and `solve.py` still passes the
559 reference build with 0.05 mm to spare: there is no slack left in the depth.

**Rev C → Rev D** fixed the C-Beam mechanics (wheels straddle the beam, belt in
the channel, screw hung from the top). **Rev B → Rev C** made the cabinet 559 deep
(booklet step 22 has the table).

---

## Before you start

**Tools** (booklet tools page): ball-end hex keys 2, 2.5 (one long), 3 and 4;
thin 8 × 10 open spanner; 5.5 nut driver; drill, 5.2 bit and centre punch;
M5 tap and wrench; hacksaw and mitre box or a mitre saw with a non-ferrous
blade; 600 mm spirit level; calipers; tape; multimeter; ferrule crimper;
2.5 and 3.5 flat terminal screwdrivers.

**Check on arrival:** the X motor's shaft is 6.35 mm; the C-Beam is `LR-C-S`;
the wheel screws are 30 mm low profile with 1.5 mm heads; the eccentrics are
10 mm hex.

**Cut the X rail to 1397.** The Z mast keeps its full 1500.

---

## Carriages (steps 1 to 5)

1. Fixed wheels on one edge of the XL plate (outer two 5.1 holes), eccentrics
   on the other (outer two 7.2 holes). On the X carriage the fixed edge goes UP.
2. Fixed wheels: M5 × 30 low profile in the counterbore, plate, 6 mm spacer,
   1 mm shim, wheel, nyloc. Snug.
3. Eccentrics: boss into the 7.2 hole, the 10 mm hex is the spacer, then shim,
   wheel, nyloc. Set both at their loosest.
4. Slide on from the end. Preload with a thin 10 mm spanner: just grips, back
   off to light finger drag, lock, re-check, run the length by hand.
5. Build the second carriage on the mast, then slide it off again for step 11.

## X drive (steps 6 to 10)

6. Motor onto its plate: four M5 × 10 from the motor side. Tap the plate M5 if plain.
7. Pulley on the shaft now; boss toward the motor; first grub on the flat.
8. Motor assembly on the rail's left end, plate on the front lips, four
   M5 × 10 into T-nuts.
9. Idler: drill 5.2 through the web 50 from the end; M5 × 40, washer, idler,
   washer, nyloc.
10. Belt in the channel, teeth in; both ends in clamps on the carriage back
    (M5 × 25 low profile).

## Z drive (steps 11 to 14)

11. Nut block on the back of the Z carriage, carriage off the mast: two 6 mm
    spacers, two M5 × 25 low profile from the front, hex nuts in the block's pockets.
12. Lead screw through the nut by hand.
13. Top: C-Beam End Mount on the mast end (four M5 × 25 low profile), one thrust
    bearing in its recess with a collar above, one underneath with a collar below.
14. Foot: motor plate, braked NEMA 23 outside, coupler inside, 2 mm shaft gap.
    Test the brake before coupling.

## Electronics, wiring, first motion, arm (steps 15 to 20)

15. Limit switches in the back top groove, NC, min and max in series per axis.
16. Controller on M3 standoffs on its panel; board ground off the frame.
    **Wiring pages:** power and safety relay; controller, motors, brake, limits.
17. First motion: driver current (X 1.5 A, Z 1.8 A), jog, steps/mm (X 80,
    Z 400 at 16 µsteps), home.
18. Arm plate: four M5 × 10 flat head into the XL plate's tapped holes, flush.
19. Arm on its G base: four M3 × 35 into the plate's M3 taps. Side mounted, own
    brick, TCP check first.
20. Safety: both E-stop channels, 13-14 controller, 23-24 brake, manual reset,
    E-stop, power-cut, limit and backlash tests.

## Into the cabinet (steps 21 to 27)

21. The cabinet: 1397 × 559 × 1829.
22. Why it is 559 deep.
23. X rail on the rear uprights with two bent brackets at each end: TOP
    (leg on the rail's top face just inboard, leg up the top back rail) and
    BOTTOM (under the rail, leg down the upright). All M5 × 10. **Level it.**
24. Hang the mast: six M5 × 10 low profile through the X plate at
    (±30, −30 / 0 / +30) into T-nuts in the mast's outer back grooves. Top
    1789, foot 289. Plumb both ways.
25. Z drive in place, seen from the right with the front to the left.
26. Z carriage, arm plate, arm. Fold before the first Z move: J2 −110,
    J3 −80, J4 −140, J5 −90.
27. Commission.

### Envelope

| | |
|---|---|
| X travel | 1086, carriage centre 163.5 to 1249.75 |
| Z travel | 1350 usable; tiers at 345, 1005, 1437 |
| J1 axis | 385.65 from the front |
| Flange reach | 292.6 from J1, forward to y = 93 |
| With the Herb Snip | its cut zone forward to y = 3.3 (`ARM_TOOL` 89.7 past the flange): the whole 203 mm tray |
| Folded transit | 162.6 long, 20.0 clear of the tray line |
| Working height | 263, inside the 341 tier opening |

### Commissioning checks

- [ ] Home, power-cycle, home again: same zero.
- [ ] Fold the arm, run Z full travel: nothing touches.
- [ ] E-stop mid-move: motion stops, brake grips, no restart until reset.
- [ ] Pull the plug mid-travel: the mast holds.
- [ ] Each tier: the arm reaches the back row of pots.
- [ ] Hand-eye calibrate at the tier it works at.

---

## SendCutSend parts

`greenhouse/sendcutsend/make_gantry_revE.py` writes the cut files from the same
`parts.py` the booklet draws:

| file | material | ops |
|---|---|---|
| `arm_plate_revB.dxf` | 6061-T6 0.250 | tap M3 ×4 (2.60 drawn), tap M4 ×4 (3.41), countersink M5 90° ×4 on the arm side (5.00 drawn) |
| `rail_bracket_top.dxf` | 5052-H32 0.125 | flat 40 × 69.38, bend 90° at 37.19 from leg A, ×2 |
| `rail_bracket_bottom.dxf` | 5052-H32 0.125 | flat 40 × 84.38, bend 90° at 37.19 from leg A, ×2 |

The `_bends.dxf` files show the bend line for reference only; upload the plain ones.

## Where the geometry comes from

| | |
|---|---|
| `parts.py` | every part at real dimensions; OpenBuilds parts from bd_warehouse's models of OpenBuilds' drawings |
| `assy.py` | the carriage, X drive and Z drive sub-assemblies |
| `frame.py` | the cabinet, the gantry's place in it, `clearances()`, `cut_report()` |
| `arm280.py`, `dae.py` | the 280 Pi from Elephant Robotics' URDF and meshes |
| `collide.py` | link-pair self-collision; how the fold was found |
| `kit3d.py`, `earcut.py` | modelling, constrained triangulation and the hidden-line renderer |
| `make_steps4.py`, `wiring_pages.py`, `tools_page.py` | the Rev E booklet |
| `cover/` | the cover scene (`cover_scene.py`) and its Blender render script |
