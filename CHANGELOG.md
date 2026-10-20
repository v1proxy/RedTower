# Changelog

This repository is a buildable design, so it is versioned like one. The version
in `VERSION` describes the *design*, not the code, and every generated artifact
is stamped with it.

- **MAJOR**: a change that makes an already-built unit wrong: a frame dimension,
  a pin reassignment, a part that is not a drop-in for the one it replaces.
- **MINOR**: a new module, a new size preset, a new capability. Existing builds
  stay valid.
- **PATCH**: corrections, better documentation, a part substitution that is a
  genuine drop-in, generator fixes that change no output.

Anyone who built against an older version should be able to read down to their
version and see exactly what would have to change.

## 0.3.0 – 2026-10-20

**The project is now Maag, the Modular Agentic Autonomous Greenhouse.** It was
Herb Tower up to 0.2.0. Display names only: titles, drawings, BOMs, the Home
Assistant panel title and the MQTT device model. Entity IDs, hostnames, file
paths and the `greenhouse` names in code are unchanged, so nothing that is
already deployed breaks.

**Gantry Rev E. Every Rev D drawing was a mirror image, and the OpenBuilds
parts are now OpenBuilds' own geometry.** Two purchased parts change: the arm
plate (Rev A's slots fit no published pattern) and the X rail's end brackets
(cast corners cannot sit where the top depth rails already are). The cabinet,
the cut list and every pin are unchanged.

### The mirror

`kit3d.iso_matrix` was left-handed, so every Rev D page showed the assembly
reflected: what sat on the left was on the right. Fixed, and every page was
re-rendered and re-checked. Anyone who marked up Rev D should re-read Rev E.

### OpenBuilds hardware from OpenBuilds' drawings

Modelled from bd_warehouse's transcription of OpenBuilds' drawings instead of
photographs:

- **XL plate**: fixed wheels on one edge (5.1 holes, counterbored), eccentrics
  on the other (7.2); tapped M5 grid; nut recess; no centre window.
- **Wheel stack**: plate 6, spacer 6, **1 mm precision shim**, wheel 11, nyloc;
  the plate sits **2.5** off the beam, so each carriage is **8.5** deep, not
  7.115. Eccentrics are **10 mm** hex. Low profile heads are 1.5 mm.
- **Nut block** 34 × 33 × 12 on two 6 mm spacers, M5 × 25 low profile, hex nuts
  in its pockets. **C-Beam End Mount** 80 × 50 × 12 at the mast top.
- `design/params.py`: `CARR_STACK = 8.5`, `TRANSIT_CLEAR = 20.0`. J1 moves to
  385.65 from the front; the folded arm clears the tray line by **20.0**
  (was 22.8); X travel **1086**. `solve.py` still passes the 559 reference
  build, with no depth to spare.

### Purchased parts that change

- **Arm plate Rev B** (`arm_plate_revB.dxf`): tapped M3 × 4 for the G base,
  tapped M4 × 4 on the bare arm's 44 mm square, countersunk M5 × 4 into the XL
  plate's tapped holes. SendCutSend drawing sizes. Rev A should not be cut.
- **Rail brackets**, bent 5052-H32 0.125 in, TOP and BOTTOM at each end of the
  X rail (`rail_bracket_*.dxf`). Replaces four cast corner brackets.
- **Reset button** for the G9SE-201's manual reset (BOM S07). Rev D had none.

### Safety wiring

- **13-14** feeds the controller; **23-24** feeds the Z brake coil, switched on
  its low side by the controller's MOSFET output, so software releases the
  brake only for a Z move and an E-stop or power cut always sets it.
- Manual reset: 24 V on T33, the NO button from T31 to T32.
- X1 is the G9SE-201's PNP status output (100 mA, not a safety output) to the
  utility node's A6, through an opto input.
- **Sheet E-01 corrected**: it drew an aux "41/42" contact the G9SE-201 does
  not have, fed the brake from 13/14, and put a 10 A fuse ahead of 13/14, above
  both the contact's 5 A rating and Omron's 8 A fuse limit. Now 5 A ahead of
  13-14, 1 A ahead of 23-24, X1 to A6.

### Booklet

Rendered cover; parts and fasteners counted off the model; a tools page; two
wiring pages (power and safety; controller, motors, brake, limits); step 11
rebuilt around the real nut block; step 16 exploded; step 23 shows where each
bracket leg lands; step 19 mounts the arm on its G base; step 27 recentred.
Gantry BOM **Rev C**: shims, spacer count, End Mount, brackets, arm plate Rev B,
reset button and a complete, counted fastener list.

Type: titles, step numbers, wiring box headings and tool names are IBM Plex
Mono, everything else Inter. That is the Maag house style for every booklet,
sheet and deck from here on. The fonts are not in the repo: the generator reads
them from `$MAAG_FONTS` or from `greenhouse-esphome/_fonts` beside the repo,
and falls back to DejaVu Sans Mono without them.

## 0.2.0 – 2026-10-20

**The reference build changed depth: 1397 × 457 × 1829 becomes 1397 × 559 × 1829.**
Anyone who has cut extrusion to the 0.1.x cut list needs eleven new depth
members. Nothing else about an existing build is wrong.

This is the first revision drawn from the real robot. Up to 0.1.3 the myCobot
280 Pi was a cylinder with datasheet numbers attached. 0.2.0 loads Elephant
Robotics' own `mycobot_280_pi.urdf` and its eight link meshes and poses them
through the URDF chain, and four of those numbers turned out to be wrong.

### The blocking one

The arm crosses a tray plane every time it changes tier. Folded as tightly as
its joint limits allow it is **162.6 mm** long, and behind it sits 88.35 mm of
carriage stack plus the X rail and the rear upright. In a 457 mm cabinet the
folded arm **overlaps the tray by 77 mm**, so it cannot change tier at all.

At 559 it clears by 22.8 mm. The alternative, if the floor space is not
available, is to cut the trays back from 203 to 127 deep and keep 457, which
costs 37 percent of the growing area. `solve.py` now refuses the impossible
case outright instead of warning about the wrong thing.

### Gantry Rev D: the mechanics redrawn as C-Beam hardware actually works

- **Carriages.** The wheels straddle the 80 mm beam and ride the grooves on
  its top and bottom faces, 100.6 mm apart (Rev C had them on the front
  face, which a V-wheel cannot do). Stack: M5 × 30 low profile, plate,
  6 mm spacer, wheel, **nyloc**. The plate's back sits 1.115 mm off the
  beam, so each carriage adds 7.115 to the stack-up, and the transit
  clearance at 559 is **22.8 mm**, not the 25 first quoted.
- **X drive.** Motor at the X rail's left end on the front lips; GT2 belt
  inside the rail's channel, width along the pulley axis, teeth in; one
  idler at the far end on an M5 × 40 through the web; both belt ends
  clamped to the back of the X carriage. Rev C had the motor mid-rail,
  where the carriage could not pass it.
- **Z drive.** The screw hangs from a top end plate between two thrust
  bearings locked by collars; the coupler at the foot carries only torque.
- **Mast foot 309 → 289.** At 309 the top collar finished 0.5 mm under the
  cabinet's top plane.
- **X travel** is 1126 mm (163.5 to 1290), set by the motor plate and the
  idler. The arm's ±150 lateral reach still covers the whole tray width.
- `greenhouse/gantry/assy.py`: one module for the sub-assemblies, used by
  both the booklet and the cabinet model, so they cannot disagree.
- Gantry BOM Rev B ($2,186.07): C05 wheel screws 27 → 30 mm; C06 M5
  nylocs added; D02 pulley bore 8 → 6.35; D03 idlers 2 → 1; D15 mast-top
  end plate and D16 lock collars added; motor-plate motor holes tapped M5.
- `design/params.py`: `CARR_STACK = 7.115`, `ARM_SETBACK` 170.58,
  `TRANSIT_CLEAR` 22.5.

### Changed

- **Frame depth 457 → 559.** Eleven depth members 377 → 479. Uprights, width
  members, tray width, tier heights and pot count are all unchanged: still
  4 × 1829, 13 × 1317, and still 17 sticks of 2000 mm.
- **Base drip pan 1317 × 377 → 1317 × 479** (G014). It spans the full frame
  depth, so it is the one sheet-metal part the change touches. **The growing
  trays are unchanged** at 1317 × 203 (G013).
- `design/params.py`: arm constants replaced with measured ones.
  `ARM_REACH` 280 → **292.6** (flange, radial from J1), plus `ARM_GRIPPER`
  90. `ARM_STOWED_H = 437` was wrong in kind, not just in value: 437 mm is
  the arm **extended**. It is now `ARM_EXTENDED_H`, joined by `ARM_FOLD_L`
  162.6, `ARM_WORK_H` 263 and `ARM_TIGHT_Q`. New `CORRIDOR_MIN_ARM` (356)
  and `CORRIDOR_MIN_GANTRY` (160.35) replace the single 230.
- `design/solve.py`: the arm is **side mounted**, so J1 is horizontal and the
  base radius no longer eats 80 mm of reach. J1 is now derived as
  `depth − ARM_SETBACK`. The headroom-vs-stowed warning is replaced by a
  transit check that raises `DesignError`, and reach is checked against the
  gripper rather than the bare flange.
- `greenhouse/drawings/brackets.py`, `make_axo5.py`, `make_section.py`,
  `render3d.py`, `make_wiring4.py`, `greenhouse/model/tower3d.py` and
  `make_views.py`: depth propagated, and `tower3d.py`'s hand-typed
  `Y_PLATE = 150` replaced by the design rule, which had the mast sitting
  inside the tray footprint.
- Generators no longer write to hard-coded `/home/claude/...` paths; they
  write next to themselves and take the mesh directory from `$MYCOBOT_MESH`.

### Added

- `greenhouse/gantry/`: the gantry subsystem. `dae.py` (COLLADA reader),
  `arm280.py` (the URDF chain), `collide.py` (link-pair self-collision),
  `parts.py`, `assy.py`, `frame.py` (the cabinet, `clearances()`,
  `cut_report()`), `kit3d.py` (modelling and the renderer) and
  `make_steps3.py`, which generates the 29-page assembly booklet.
- `Gantry_Assembly_Instructions_RevD.pdf`, `GANTRY_ASSEMBLY.md`, and the
  gantry BOM: `build_gantry_bom_revB.py` and its spreadsheet.
- `greenhouse/build_bom_revF.py`: Rev E with the three structural lines
  corrected. It still needs `greenhouse_BOM_revC.xlsx` beside it to run.

### Fixed

- **The fold is collision checked.** The first shortest fold found,
  J2 −135 / J3 −150 / J4 −150, sits inside the joint limits and drives J4
  through the base. `greenhouse/gantry/collide.py` voxel-checks every link
  pair two or more apart in the chain on the real meshes; ranking 83,607
  poses by length and checking in order gives J2 −110 / J3 −80 / J4 −140 /
  J5 −90, confirmed on the full 226,670-face mesh. It is also 162.6 mm,
  because the length is set by the shoulder housing, so the depth decision
  stands.
- **Renderer rewritten.** Fills come from a real per-pixel z-buffer
  (vectorised scanline, smooth crease-aware shading) and every edge is
  hidden-line tested against it. The old depth-sliced
  painter's algorithm drew a slice's edges over every face in that slice,
  so anything within one slice depth (28 mm on a cabinet page) showed
  through. Neither step now depends on face winding, which matters because
  the CAD arm meshes are open shells.
- `extrude()` and `revolve()` emitted caps and walls with separate vertex
  copies, so a gantry plate was twelve disconnected open sheets and some
  rendered hollow. `weld()` joins them into closed solids.
- The arm is drawn from Elephant's full-resolution mesh. The vertex
  clustering used before left the links lumpy.
- The axonometric view matrix had world +Z pointing **down** the page. Every
  generated axonometric was vertically inverted.
- Z motor moves from the top of the mast to the foot: the mast top is at 1809
  and a 76 mm NEMA 23 above it stands 56 mm proud of the cabinet. A NEMA 23
  is also 56.4 mm square and the C-Beam channel is 20 mm deep, so it was
  never going inside the channel either.
- The X rail must be **cut to 1397**. 0.1.x said both C-Beams were used at
  their full 1500.

### Still open

- The mast is a 1500 mm cantilever off four V wheels. Expect 1 to 2 mm of
  forward lean at the bottom, so hand-eye calibration is per tier. If it
  measures worse, a second XL gantry plate ganged onto the X carriage (+$18,
  not in gantry BOM Rev A) doubles the pitch stiffness.
- `make_dxf_rev4.py` carries the new pan width but needs `ezdxf`; regenerate
  the base-pan DXF before ordering G014.
- G016, the LED bar, is still unresolved: both sourced options are dead.

## 0.1.3 – 2026-10-18

No design change. No generated output changes.

### Changed
- README: a rewritten opening. Why the project exists, an invitation to get in
  touch by email, and credit to the AutonCorp Biodome Project for the
  inspiration. The comparison with other smart-garden products is gone.

### Added
- `LICENSE`: the whole repository is MIT licensed. Build it, change it, share
  it; keep the copyright notice.
- `docs/08-arm.md`: Jetson bring-up, from the box to a running core layer.
  JetPack 7.2.1 from a USB stick, the QSPI firmware prompt that must be answered,
  the missing SSH host keys, base settings, the RealSense SDK with its new
  signing key, the Mosquitto logins, and starting the four core services.

### Found while bringing up the core layer
- The core layer runs on the reference build. Supervisor, safety governor, store
  and bridge publish about 220 entities to Home Assistant, pass all six broker
  checks against the Mosquitto app, and are back about 40 seconds after a reboot.
  The 145 unit tests pass on the Jetson.
- Home Assistant now has two authority selectors and two kill switches: the
  package's `input_select.gh_authority` and `input_boolean.gh_kill`, which the
  panel card drives, and the bridge's `select.greenhouse_authority` and
  `switch.greenhouse_kill`, which the supervisor obeys. They are not linked, and
  at the time of writing they disagree: the panel's kill switch is on, the
  supervisor's is off. Harmless while no agent container exists; it must be
  resolved before any agent is started.
- `binary_sensor.greenhouse_robot_busy` did not exist until the bridge ran, so
  "Greenhouse - zone watering" logged a warning on every evaluation. The bridge
  now provides it.

### Open
- `mosquitto-acl.sample` is not applied, so both broker users can write every
  topic.

## 0.1.2 – 2026-10-18

No design change. No generated output changes.

### Added
- `greenhouse/jetson/prototype/d405_leaf.py`: close-range depth quality on a
  real plant. Keeps the frame with the most pixels inside a working band and
  reports fill (valid pixels over the object's filled silhouette), per-pixel
  temporal noise over 15 frames, and range. Saves a depth map scaled to the
  band, a side-by-side with colour, and the raw depth.

### Found
- The D405 works at the arm's distance. On a snake plant under ordinary room
  light: 94 % fill and 0.79 mm temporal noise at 225-333 mm; 97 % fill and
  2.26 mm at 339-525 mm. Noise scales close to distance squared, as stereo
  should. October's Windows result (2 % valid) was the camera aimed at a room
  with nothing inside its range.
- Textureless surfaces such as a plain wall return no depth, because the D405
  has no IR projector. A plain cabinet back will drop out of the depth image,
  which isolates the plants rather than hurting.
## 0.1.1 – 2026-10-18

No design change. No generated output changes.

### Added
- `greenhouse/jetson/prototype/d405_fps.py`: separates the D405's real frame
  rate from Python processing cost. Streams depth and colour at 848x480 @ 30,
  reads the camera's own frame-rate and exposure metadata, then times
  `rs.align` on the same frames.

### Found while bringing up the Jetson
- First run on the Jetson Orin Nano Super (JetPack 7.2.1, Ubuntu 24.04,
  librealsense 2.59.1 from the RealSense apt repository, `pyrealsense2`
  2.59.1 wheel in a venv): the D405 enumerates at USB 3.2 and delivers a true
  30 fps with depth aligned to colour.
- The ~20 fps that `d405_check.py` reports, here and on Windows in October, is
  the script counting its own pipeline start-up, not the camera or the cable.
## 0.1.0 – 2026-10-17

First parametric release. Up to here the repository described exactly one
greenhouse, 1397 × 457 × 1829 mm, and every dimension was a constant somebody
had typed into `brackets.py`.

### Added
- `design/params.py`: one `Envelope` describing the space you have, plus five
  presets spanning 600 mm to 3000 mm of wall.
- `design/solve.py`: derives the whole design from the envelope: bay count and
  intermediate uprights, shelf levels and headroom, the pot grid, probe and ADC
  allocation, LED wattage from a PPFD target, zone flow rates, reservoir size,
  node count and switch selection, and the arm's reach geometry.
- Module system. Core is sensing, lighting and irrigation, and every size has
  it. `gantry`, `arm` and `climate` are optional; the solver enforces that `arm`
  requires `gantry`, and reports what each one costs in depth and headroom.
- Hard limits that the solver refuses to violate rather than silently produce a
  design that cannot be built: shelf span before ponding, the four ADS1115
  addresses, PoE port budget, gantry corridor, pot fit in the tray.

### Found while building it
- **The arm's reach is the binding constraint on depth.** With a 280 mm myCobot
  on a C-Beam carriage, joint 1 ends up 359 mm behind the front face in the
  reference build, and its reach stops 79 mm short of it. The pots have to sit
  against the *back* of the tray. At the reference size the margin is +3 mm. Go
  deeper than about 460 mm and the arm can no longer reach the front of its own
  pot row, which is why `l` at 560 mm deep reports a 17 mm shortfall.
- **Four PoE ports is a design limit, not a detail.** Any build with more than
  three tiers needs a bigger switch than the TL-SG108PE in the BOM.
- **Sixteen probes per tier is the ceiling.** Four ADS1115 on four addresses.
  A 3 m wall fits 22 pots per tier, so that size needs two nodes per tier or
  zone-level moisture for the surplus.

### Unresolved, carried forward
- The LED line. The Kingbrite listing in BOM Rev E (G016) now 404s, and the
  HLG QB120 V2 alternate (G017) is both unavailable as a 4-pack and electrically
  incompatible: its minimum drive current is 1050 mA and the specified drivers
  are 700 mA. See `docs/05-electrical.md`.
- `greenhouse/` still holds the hand-written reference build. The generators in
  it are not yet driven by `design/`. That is the 0.2.0 work.
