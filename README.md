# Herb Tower

A smart indoor greenhouse you can build in the space you actually have, from a
600 mm closet bay to a 3 m room wall. Per-pot moisture sensing, per-tier climate,
dimmable horticultural lighting and interlocked drip irrigation in every size.
A gantry and a robot arm if you want them.

**Design version: see [`VERSION`](VERSION). Changes are in [`CHANGELOG.md`](CHANGELOG.md).**

This started as one greenhouse in one house in Houston. It is now a parametric
design: you describe your space, the design solves itself, and the solver tells
you what will not fit and why rather than letting you find out with a cut list.

---

## Start here

```bash
git clone https://github.com/v1proxy/RedTower.git
cd RedTower/design
python3 solve.py m          # the reference build
python3 solve.py xs s m l xl   # every preset, side by side
```

That prints a complete design: frame bays, shelf heights, headroom, how many
pots fit, how many moisture probes and ADCs that needs, LED watts per tier,
irrigation flow, reservoir size, how many nodes, which network switch, and the
robot arm's reach geometry. Plus every constraint your envelope violates.

To describe your own space, edit an `Envelope`:

```python
from params import Envelope
from solve import solve

mine = Envelope(
    name="kitchen-alcove",
    width=820.0, depth=380.0, height=1600.0,
    tiers=3,
    pot_size="4.5in",
    modules=(),              # core only: sense, light, water
    series=20,
)
print(solve(mine, "0.1.0").report())
```

If it cannot be built, you get a sentence telling you how short you are and
which three things would fix it.

---

## The five presets

| preset | space | tiers | pots | modules | what it is |
|---|---|---|---|---|---|
| `xs` | 600 × 360 × 1100 | 2 | ~12 | core only | A closet bay. Hand-tended. |
| `s` | 900 × 400 × 1500 | 3 | ~18 | + climate | A wardrobe, run with the doors shut. |
| `m` | 1397 × 457 × 1829 | 3 | ~28 | all | **The Red Tower reference build.** |
| `l` | 2100 × 560 × 2200 | 4 | ~48 | all | A garage wall. Needs an interior upright. |
| `xl` | 3000 × 610 × 2400 | 5 | ~110 | all | A full room wall. Two nodes per tier. |

Every drawing, DXF and BOM revision committed so far is the `m` build. The other
sizes are solved, not yet drawn.

---

## Modules

**Core, in every build.** Per-pot capacitive moisture probes, per-tier air
temperature and humidity, VPD and leaf VPD from a canopy IR sensor, spectral
light sensing, dimmable LED with a local photoperiod schedule, drip irrigation
with per-tier zones, leak detection, and hard interlocks that live on the node
and refuse regardless of what asks.

| module | adds | costs you | needs |
|---|---|---|---|
| `climate` | CO2 sensing, exhaust fans with a local thermostat, humidifier | ~$150, one more node pin | — |
| `gantry` | C-Beam rail, carriage, stepper motion | a 254 mm corridor out of your depth | — |
| `arm` | myCobot 280, gripper, depth camera, Jetson | ~$800, and the reach constraint below | `gantry` |

The arm is the one that reaches back into the architecture. It needs 254 mm of
corridor, which comes out of your tray depth, and its 280 mm reach then has to
cross that corridor to get to the pots. The solver computes the margin and tells
you if it is negative.

---

## Control layers

Each layer has exactly one job. The separation is deliberate: two things that
can both open a valve will eventually both open a valve.

| layer | cadence | may actuate? |
|---|---|---|
| `esphome/` node firmware | continuous | hard interlocks, refuses regardless of what is asked |
| `homeassistant/` | seconds | requests only, through a named action |
| `jetson/` agents | minutes | proposes; bounded by an authority ceiling and a kill switch |

Home Assistant can *ask* for water. It cannot switch the pump: those entities are
`internal: true` and never reach the API.

---

## Repository layout

```
VERSION              the design version. Everything generated is stamped with it.
CHANGELOG.md         what changed, and what it breaks
design/
  params.py          the Envelope, the physical limits, the presets
  solve.py           envelope -> complete checked design
docs/                the build guide, in order
greenhouse/
  esphome/           node firmware: tier nodes + utility node
  homeassistant/     package: entities, scripts, dashboard card
  jetson/            tending agents and the robot stack
  drawings/          frame, sheet metal and wiring, generated not drawn
  sendcutsend/       DXFs for the cutter, and the unfolder that makes them
  model/             the greenhouse as real 3D geometry
  build_bom_*.py     bill of materials, each revision a full generator
  opex_model.py      daily running cost: electricity and tokens
```

Nothing in `drawings/` is drawn by hand. Each file is a generator: run it and it
re-derives the sheet from the member table and the pin maps, so a drawing cannot
drift from the thing it documents.

---

## Build guide

1. [Choose your size](docs/01-choose-your-size.md)
2. [Bill of materials](docs/02-bill-of-materials.md)
3. [Frame assembly](docs/03-frame-assembly.md)
4. [Sheet metal](docs/04-sheet-metal.md)
5. [Electrical](docs/05-electrical.md)
6. [Firmware](docs/06-firmware.md)
7. [Home Assistant](docs/07-home-assistant.md)
8. Modules: [gantry](docs/08-gantry.md) · [arm and vision](docs/08-arm.md) · [climate](docs/08-climate.md)
9. [Commissioning](docs/09-commissioning.md)

---

## Honest status

This is a design under construction, not a finished kit. Known open items are in
`CHANGELOG.md` under the current version. The largest one right now: **the LED
part number is unresolved.** Both options in BOM Rev E are dead, one of them for
an electrical reason worth knowing about before you buy drivers.

Part of the [Red Tower](https://github.com/v1proxy/RedTower) house project, Houston.
