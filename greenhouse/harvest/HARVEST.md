# Maag: harvest

Maag is the Modular Agentic Autonomous Greenhouse.

**Harvest Rev B · design 0.6.1 · 2026-10-21 · all dimensions mm**

Rev B reshapes the feeder (taller and shallower, a 45° lid flush with the walls,
a finger scoop to lift it, a sloped skirt underneath) and prints each
compartment in three parts. The dead-leaf tray is unchanged.

Where the Herb Snip puts what it cuts. Dead leaves go **down**, into a tray in
the base bay that slides out of the bottom-left door. Leaves and veggies go
**out**, through the right panel, into a feeder on the outside of the cabinet at
tier B, built after the side feeders of a bird cage: the arm fills it from the
inside, you empty it from the outside, and the doors stay shut.

Read alongside the booklet `Maag_Harvest_Assembly_Instructions_RevB.pdf` (step
numbers below are the booklet's). It starts from the finished enclosure
(Enclosure Rev A, step 18).

Every drawing, every cut file, both prints and the arm's drop poses come from
one model, `harvest.py`, built on `enclosure.py` and `cabinet.py`:

```
python greenhouse/harvest/harvest.py                 # every check, as a report
python greenhouse/harvest/make_harvest_files.py      # DXFs and STLs
MAAG_ARM_NPZ=... SNIP_STL=... python greenhouse/harvest/reach.py      # the drop poses: drops.yaml
MAAG_ARM_NPZ=... SNIP_STL=... python greenhouse/harvest/make_harvest_booklet.py
python greenhouse/enclosure/make_enclosure_files.py  # the right panel, with the feeder's openings
```

`reach.py` and the booklet's arm pages need two meshes that are not in the repo:
the myCobot 280 Pi's links (`MYCOBOT_MESH`, Elephant Robotics' .dae folder,
which the booklet draws undecimated as the gantry booklet does; `MAAG_ARM_NPZ`, a
decimated .npz, is enough for the checks) and the Herb Snip's printed body
(`SNIP_STL`, `snip_body.stl`). The printed parts need `manifold3d`.

---

## What it is

| | |
|---|---|
| Dead-leaf tray | 5052 0.063 bent by SendCutSend: 457 × 480 × 50 outside, about 10.5 L. The two side walls end in rims that turn outward: the tray **hangs by its rims** on the rails |
| Guide rails | Two 5052 0.063 C-channels, 544 long, bolted to the base pan with the pan's own bolts at x 150 and x 650, front and back (M8 × 12 become M8 × 16). A tab at the back of each web is the stop |
| Handle | Printed, bolted to the tray's front wall with three M5 × 10 into nylocs sunk in hex pockets. It stands 172 up off the wall: a 120 × 42 slot the whole hand goes through, a rounded bar over it |
| Feeder | Two printed compartments side by side, leaves (front) and veggies (back), 152.4 wide, 132 deep, 307 tall from the skirt's foot to the hinge, on the right panel's outside at tier B. Each is three prints: a **basin** (floor, back plate on the rail line, the walls' lower 85), a **hood** (back plate with the arm's opening, the walls under the lid) that drops into the basin's 1.5 × 4 lip, and a **skirt**, a hollow wedge taped under the floor whose slope runs back down to the panel. Each has its own lift-out printed tray, 108 × 142 × 124, 1.7 L |
| Arm openings | One 80 × 160 opening per compartment, through the right panel and the module's back plate, corners R25 |
| Lid | One clear 4.5 polycarbonate lid over both (SendCutSend, the doors' sheet), 304.8 × 173.6, falling 45° away from the panel, on one 1 ft McMaster 1658A15 piano hinge on VHB. Its lower edge is flush with the walls' outer faces, against a ridge on the outer wall's top; a finger scoop 28 wide in the outer wall, at the divider, lifts it. Lifted, it turns 138° and leans on the panel |
| Fixing | Two M5 × 20 per basin into the T-nuts in tier B's side rail (the panel's own screw line), two M4 × 20 per hood into rubber well nuts set in the panel above the openings; the skirts on VHB |
| Safety | A reed switch for the lid (7939WG, as on the doors) on the veggies hood's back plate, under the hinge, its magnet on the lid's underside; in series with the door chain: lid open, the safety relay cuts the gantry and the arm |
| Parametric | `Feeder(side="right", tier="B")`. The modular cabinet's left-hand feeder is `side="left"`: every part mirrors about x = 698.5 |

## Why it is built this way

**Third shelf: tier B.** Counting the base pan as the first shelf, tier B is the
third; its rail line is at 985 above the frame's foot, so the feeder's trays sit
at waist height, 1.0 m from the floor. Tier B's bay on the right panel has
nothing else in it (the glands are in bays A and C).

**The tray hangs by its rims.** Its floor has to ride over the base pan's front
lip (65 high) to slide straight out, and the rails have to guide it sideways. A
bent rail cannot carry a ledge under the floor *and* a wall beside it without
covering its own bolt, so the tray carries the ledge instead: its rims ride on
the rails' top flanges, its side walls run between the rails' webs. The rails'
bottom flanges sit round the pan's own bolts, so nothing is drilled.

**Only the left door.** The tray, 457 wide plus rims, clears the right door's
astragal by 37, so the bottom-left door alone lets it out.

**Printed compartments, two of them, in three parts each.** The bird-feeder
shape (an inclined lid, a sill, deep trays) is easy to print and awkward to
bend: SendCutSend's boxes stop at 5 in walls. Two compartments of 152.4 make
exactly the 12 in hinge, and the two walls where they meet are the leaves /
veggies divider. At 307 tall a compartment no longer fits the P2S's 256 bed in
one piece, so it splits where the work splits: the basin takes the rail screws
and the weight, the hood carries the opening, the well nuts and the hinge, and
the skirt only closes the shape. The joint sits 15 over the rail line, under the
openings' sills, and the basin's lip keeps it from showing a gap.

**A flush lid at 45°.** The lid's square-cut lower edge would leave a notch at
the outer wall; instead the wall's outer face runs up to the lid's top face in a
small ridge, and the lid's end sits against it with 0.5 to spare. Opening, the
lid's end slides along the ridge's face (it moves along its own normal), so the
ridge never holds it. A 28 × 14 scoop in the outer wall under the lid's edge
takes a fingertip.

**The switch sits on the back plate, under the hinge.** The trays lift straight
up 169 before they can come out over the outer wall, so anything above a tray is
in its way. The back plate's top band, between the M4 heads and under the
hinge's fixed leaf, is outside that column; the trays start 2 in front of the
switch. Its magnet rides on the lid's underside 2 in front of it, and moves 15
away by the time the lid is 20° open.

**The openings are sized to the snip, not the arm.** The Herb Snip's printed body
is wide only for its first 60 along the tool axis (the servo); past that it is a
slim jaw finger. reach.py keeps the servo end inside the cabinet (17 to spare),
so only the finger goes through: 80 × 160 is the finger, its swing to the
release, and a leaf hanging from the jaws.

**The two drops sit 91 apart, close to the divider.** With the arm at the end of
its X travel the snip reaches the panel from y 275 to about 385: further back,
the arm meets its own carriage (1.6 at y 410). The leaves drop is at y 285, the
veggies at y 376.

**Well nuts above the openings.** There is no frame behind the panel there, and
nothing to hold a nut with from inside. A well nut pushes in from outside and
grips the panel when its screw is turned.

## The checks (`python harvest.py`, `python reach.py`)

| Check | Result |
|---|---|
| Tray floor over the pan's front lip | 5.0 |
| Rims and the rails' stop tabs under the gantry's lowest part (over the X travel) | 26.0 |
| Handle under rail F1; its bar behind the door's inside face | 12.8; 11.6 |
| Tray past the right door's astragal, left door open | 37.0 |
| Left rail off the leak sensor (x 125); right rail off the pan's UP piece | 16.0; 1.0 |
| Side play, each side | 1.5 |
| Rail bolt M8 × 16: stack, reach, spare to the slot floor | 4.8, 11.2, 1.05 (the pan's UP piece, the same) |
| Feeder M5 × 20: stack, past the lips, spare | 11.9, 3.8, 4.1 (every panel screw, the same) |
| Opening's sill over tier B's rail; tray rim over the sill | 9.8; 27.0 |
| Feeder to the next thing on the panel's outside | 48.7 (a panel screw on the back post) |
| Open lid's top edge under the gland above it | 184.2 |
| Reed switch to its magnet, lid down | 2.0 (the 7939WG works to 32) |
| Hood, basin, skirt, print bed 256 | 132 × 152.4 × 222; 132 × 152.4 × 89; 65 × 152.4 × 132 (on its back) |
| Lid flush with the walls' outer face | 0.35 (its 0.5 gap to the ridge) |
| Trays lift clear of the outer wall; of the switch | 169 up; 2.0 |
| Lid and hinge leaf against the printed parts, closed | 0.000 cm³ |

Drop poses (`drops.yaml`), the tightest gap at each, mm, with the arm's own
CAD meshes. **Provisional**: solved with the Herb Snip's first printed body,
without its D405; the housing version replaces it when its files land.

| Drop | Release point (x, y, z) | J1 height | Tightest |
|---|---|---|---|
| Leaves, inside, through, release | 1444.7, 285, 1070 | 916, 926, 893 (the elbow under the arm) | 8.1 to tier B's plants (y < 210) |
| Veggies, inside, through, release | 1444.7, 376, 1070 | 1298, 1299, 1268 | 12.8 to tier B's plants |
| Dead leaves, five along the tray | x 231.5 to 568.5, y 330, z 175 | 499 | 10.9 to the carriage |

The jaws release 28 over the feeder tray's rim (10 clear of it) and pass the
opening 30 higher: the 45° lid leaves no room for the 60 that Rev A used. Over
the dead-leaf tray they release 55 over the rim. The carriage sits at the end of its X travel (1249.75) for
the feeder; for the tray it moves with the drop.

## Files

| File | For | What |
|---|---|---|
| `sendcutsend/guide_rail_L.dxf`, `guide_rail_R.dxf` | SendCutSend | 5052 H32 0.063 in, qty 1 each: two bends, both 90° up (the dashed lines) |
| `sendcutsend/deadleaf_tray.dxf` | SendCutSend | 5052 H32 0.063 in, qty 1: four wall bends 90° up, the two rim bends 90° down |
| `sendcutsend/feeder_lid.dxf` | SendCutSend | Polycarbonate 0.177 in clear, qty 1 |
| `print/deadleaf_handle.stl` | your printer | Flat on its back. PETG or PLA, 4 walls, 20 % gyroid |
| `print/feeder_hood_leaves.stl`, `feeder_hood_veggies.stl` | your printer | Standing on the joint face. The veggies one has the switch cable's hole |
| `print/feeder_basin.stl`, `feeder_skirt.stl`, `feeder_tray.stl` | your printer | Print two of each. Basins and trays on their floors, skirts on their open back |
| `drops.yaml`, `drops.json` | the Herb Snip's software | Every drop: release point, carriage x, J1 height, joint angles, margins |

The right panel's two openings, four well-nut holes (10) and the switch's cable
hole (8) are in the enclosure's files: `greenhouse/enclosure/acplastics/panel_right.dxf`
and the A&C drawing. All four DXFs here pass the closed-loop, self-crossing and
bend-line checks.

## Buy list

| Item | Qty | Source |
|---|---|---|
| Guide rails L and R, the dead-leaf tray, the feeder lid | 1 each | SendCutSend (quote on upload) |
| Piano hinge, 304 SS, 1 1/2 in open, 0.042, with holes, 1 ft | 1 | McMaster 1658A15 |
| Reed switch Honeywell 7939WG-WH, with its magnet | 1 | as BOM G047 |
| M4 rubber well nut, 10 mm hole, 1 to 4 mm grip | 4 | |
| M8 × 16 button head | 4 | |
| M5 × 10 button head; M5 nyloc | 3; 3 | |
| M5 × 20 button head | 4 | |
| M4 × 20 button head | 4 | |
| Lever connector Wago 221-412; 2-core alarm cable; adhesive cable clips | 2; 3 m; 6 | |
| Filament, PETG or PLA | about 2 kg | the nine prints are 1.74 L if solid; their 2 to 4 mm walls print solid |

The four DIN 9021 washers and the VHB (both hinge leaves, two strips per skirt)
come from the enclosure's stock.

## What changed elsewhere

- **Enclosure, right panel**: two arm openings at tier B, four Ø10 well-nut holes
  and a Ø8 cable hole; tier B's middle panel screw on the rail line (u 279.5)
  gives way to the feeder's four M5 holes (u 208, 298, 360.4, 450.4), which carry
  ordinary M5 × 16 panel screws until the feeder goes on. The enclosure booklet's
  face map and step 8 show them.
- **ESPHome utility node**: the doors chain on MCP23017 A4 is now four door reeds
  and the feeder lid, in series. No pin changes.

**Supersedes**: the Herb Snip's harvest drawer (160 × 180 × 80 in the base bay,
in the Herb Snip chat's branch `herb-snip-0.5.0`, not yet in this repo) and its
keep-out zone. When that branch lands, its `to_bin` goes to the feeder's two
compartments and its `to_waste` to the tray's five drops, from `drops.yaml`.

## Open items

- **The snip is posed as printed**: mount face at z 8.5 on the flange, flange
  centre at (0, 12.7) in its STL, jaws as a 18 × 26 × 70 block past 70. Rerun
  `reach.py` with the Herb Snip's real assembly when its branch lands.
- **drops.yaml is in cabinet coordinates.** Commissioning jogs to each pose and
  writes the machine coordinates into `robot.yaml`, as for the plants.
- **The reed switch and magnet are drawn as blocks** (Honeywell publishes no
  drawing), as on the doors.
- **SendCutSend's bend tolerances** (about ±0.5) eat into the tray's 1.5 side
  play; if the tray binds, loosen a rail and slide it outward: the pan's holes
  under its bolts are 18 long slots across the cabinet.
- **Tiers A and C, and the left side**, are a parameter away but not checked by
  reach.py: a tier A feeder would sit on the right panel's duct collar.
