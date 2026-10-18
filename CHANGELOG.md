# Changelog

This repository is a buildable design, so it is versioned like one. The version
in `VERSION` describes the *design*, not the code, and every generated artifact
is stamped with it.

- **MAJOR** — a change that makes an already-built unit wrong: a frame dimension,
  a pin reassignment, a part that is not a drop-in for the one it replaces.
- **MINOR** — a new module, a new size preset, a new capability. Existing builds
  stay valid.
- **PATCH** — corrections, better documentation, a part substitution that is a
  genuine drop-in, generator fixes that change no output.

Anyone who built against an older version should be able to read down to their
version and see exactly what would have to change.

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
## 0.1.0 — 2026-10-17

First parametric release. Up to here the repository described exactly one
greenhouse, 1397 × 457 × 1829 mm, and every dimension was a constant somebody
had typed into `brackets.py`.

### Added
- `design/params.py` — one `Envelope` describing the space you have, plus five
  presets spanning 600 mm to 3000 mm of wall.
- `design/solve.py` — derives the whole design from the envelope: bay count and
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
