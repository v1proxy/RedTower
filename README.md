# Claude Agentic Greenhouse

**I am bad at keeping plants alive. So I turned it into an engineering project.**

An indoor greenhouse that an AI agent tends, written down so anyone can build
one. It scales from a 600 mm closet bay to a 3 m room wall: build the size your
space allows, with only the modules you want.

![design version](https://img.shields.io/badge/design-0.6.0-1d4ed8)
[![license](https://img.shields.io/badge/license-MIT-5b6770)](LICENSE)

---

## Why this exists

I am not good at growing plants. Left to me, they die: too much water, then
too little, then the wrong light, and I only notice when it is too late.

At some point the engineer in me stopped treating that as a personal failing
and started treating it as a requirements problem. If I cannot be trusted to
remember to water, measure the soil. If I cannot read a leaf, point a camera at
it. If I cannot decide what a plant needs, hand the decision to something that
reads every sensor, every day, and never forgets. The only way I was ever going
to keep plants alive was to make keeping them alive a complex engineering
project.

This repository is that project. I needed one place to keep the frame, the
firmware, the code and the drawings together, and while I was at it I wrote it
down carefully enough that someone else can build their own. It is a personal
build in my house in Houston, shared so it can be replicated anywhere, at
whatever size your space allows.

If anything is unclear, or you build one and get stuck, write to me at
**contact@vittorionetti.com**. I am happy to help.

### Inspiration

The starting point was the
[AutonCorp Biodome Project](https://autoncorp.com/biodome), where Claude grows
Sol, a tomato, inside a sensor-filled biodome and shares the readings and its
own decisions on a live dashboard. Watching an AI read VPD, soil moisture and
CO2 and act on them for one plant is what made me want to try it for a whole
shelf of herbs. The environmental variables this greenhouse tracks are modelled
on theirs. Thank you to the people behind it.

---

## What it does

The hard part of growing indoors, for me at least, was never switching a pump
on a schedule. It was deciding what the plants need. So that decision goes to
something that can look at the plants, read the history and reason about it,
while the hardware keeps it from doing anything dangerous.

That is why the greenhouse senses more than it strictly needs to. Every pot has its own
moisture probe. Every tier measures air temperature, humidity, canopy
temperature by infrared, and the spectrum actually landing on the leaves. From
those it computes VPD and leaf VPD, which is what a plant physically
experiences, rather than the room's humidity reading. A depth camera on a robot
arm looks at individual plants. An agent on a Jetson reads all of it, proposes a
tending strategy, and acts inside limits it cannot talk its way out of.

And then, deliberately, the agent is given almost no authority.

---

## The part that matters: three layers, one actuator

A greenhouse that can water itself can also flood itself. The architecture is
built around that, not around the agent.

| layer | runs on | cadence | may actuate? |
|---|---|---|---|
| node firmware | ESP32-POE-ISO, one per tier + one utility | continuous | **yes, and it is the only layer that can** |
| Home Assistant | wherever you run it | seconds | no. It may *request*, through one named action |
| the agent | Jetson Orin Nano | minutes | no. It proposes, bounded by an authority ceiling |

The pump and the three zone valves are `internal: true` in the node firmware.
They are never exposed to the API. Home Assistant can call
`water_zone(zone, seconds)`; the node decides whether to honour it, and refuses
outright if any tray is wet, if the reservoir float is down, if the leak lockout
is latched, or if the E-stop chain is open. The lockout is sticky across
reboots, so a flooded tray cannot be cleared by power-cycling.

The agent sits one layer further out again, under an explicit ceiling:

```
Off → Manual → Auto → Agent proposes → Agent autonomous
```

plus a kill switch checked immediately before any motion command leaves the
Jetson. Flipping it stops the arm without having to agree on a state machine.

The design assumption is that the agent will eventually be wrong, and that
nothing it can be wrong about should be able to drown a shelf of basil.

---

## Fail-safe by construction

Not by convention, by physics:

- Zone valves are **normally closed** and the pump needs a MOSFET actively held
  on, so a dead controller cannot water anything.
- The Z-axis brake is released **by** 24 V, so a power cut parks the mast rather
  than dropping it through the trays.
- The GFCI is **manual** reset. After a trip it stays off until a person pushes
  it. Deliberate, in a cabinet holding water and mains.
- The LED driver's dim input fails to **full light**, so a relay cutting its
  mains is the authoritative off. The dimmer is only a dimmer.
- Every tier node keeps its own clock and runs its own photoperiod ramp and
  thermostat. Pull the network out and the greenhouse keeps lighting,
  ventilating and sensing. Only the agent and the dashboards go away.

---

## Parametric

The only input is the space you have.

```bash
git clone https://github.com/v1proxy/RedTower.git
cd RedTower/design
python3 solve.py m          # the reference build
python3 solve.py xs s m l xl
```

That prints a complete design: frame bays and whether you need an interior
upright, shelf heights and headroom, how many pots fit and at what pitch, how
many moisture probes and ADCs that needs, LED watts per tier from a PPFD target,
irrigation flow per zone, reservoir size, node count, which network switch, and
the robot arm's reach geometry. Then it tells you every constraint you are close
to, and refuses outright on the ones you cannot build through.

| preset | space (mm) | tiers | pots | modules |
|---|---|---|---|---|
| `xs` | 600 × 360 × 1100 | 2 | ~12 | core only |
| `s` | 900 × 400 × 1500 | 3 | ~18 | + climate |
| `m` | 1397 × 457 × 1829 | 3 | ~28 | all — **the reference build** |
| `l` | 2100 × 560 × 2200 | 4 | ~48 | all |
| `xl` | 3000 × 610 × 2400 | 5 | ~110 | all |

Describe your own space instead:

```python
from params import Envelope
from solve import solve

print(solve(Envelope(
    name="kitchen-alcove",
    width=820.0, depth=380.0, height=1600.0,
    tiers=3, pot_size="4.5in",
    modules=(),            # core only: sense, light, water
    series=20,
), "0.1.0").report())
```

---

## Modular

**Core, in every build, at every size:** per-pot moisture, per-tier climate and
VPD, dimmable horticultural lighting on a local photoperiod schedule, zoned drip
irrigation, leak detection, and the interlocks above.

| module | adds | costs |
|---|---|---|
| `climate` | CO2 sensing, exhaust fans on a local thermostat, humidifier | ~$150 |
| `gantry` | C-Beam rail, carriage, stepper motion | 254 mm of your depth |
| `arm` | myCobot 280, gripper, depth camera, Jetson | ~$800, and requires `gantry` |

The smallest build is a few hundred dollars of sensing, light and water in a
closet, with no robot anywhere near it. The largest is 110 plants on a room wall
with an arm on a 2.5 m rail. Both run the same firmware and the same interlocks.

### One counterintuitive result

A **deeper** cabinet makes the robot's job **harder**. The gantry corridor sits
behind the trays, so a deeper tray pushes the pots further from an arm that is
already behind them. With a 280 mm reach, past roughly 460 mm of depth the arm
can no longer reach the front of its own pot row. The reference build clears it
by 3 mm. The solver computes that margin and tells you when it goes negative,
which is the sort of thing you want to learn before you buy extrusion.

---

## Everything is generated

Nothing in `drawings/` is drawn by hand. Each file is a generator: run it and it
re-derives the sheet from the member table, the BOM and the firmware pin maps.
A drawing cannot drift from the thing it documents, because it is not a drawing,
it is a function of the design.

The same is true of the bill of materials, the sheet-metal DXFs that go to the
laser cutter, and the running-cost model.

---

## Layout

```
VERSION              the design version; every generated artifact is stamped
CHANGELOG.md         what changed, and what it would break for an existing build
design/
  params.py          the Envelope, the physical limits, the presets
  solve.py           envelope -> complete, checked design
docs/                the build guide, in order
greenhouse/
  esphome/           node firmware: tier nodes + utility node
  homeassistant/     package: entities, scripts, dashboard card
  jetson/            tending agents and the robot stack
  drawings/          frame, sheet metal and wiring, generated
  sendcutsend/       DXFs for the cutter, and the unfolder that makes them
  model/             the greenhouse as real 3D geometry
  build_bom_*.py     bill of materials, each revision a full generator
  opex_model.py      daily running cost: electricity and tokens
```

---

## Build guide

1. [Choose your size](docs/01-choose-your-size.md)
2. [Bill of materials](docs/02-bill-of-materials.md)
3. [Frame assembly](docs/03-frame-assembly.md)
4. [Sheet metal](docs/04-sheet-metal.md)
5. [Electrical](docs/05-electrical.md)
6. [Firmware](docs/06-firmware.md)
7. [Home Assistant](docs/07-home-assistant.md)
8. Modules: [gantry](docs/08-gantry.md) · [arm, vision and the Jetson](docs/08-arm.md) · [climate](docs/08-climate.md)
9. [Commissioning](docs/09-commissioning.md)

---

## Versioning

This is a buildable design, so it is versioned like one. `VERSION` describes the
*design*, not the code.

- **MAJOR** — a change that makes an already-built unit wrong: a frame dimension,
  a pin reassignment, a part that is not a drop-in.
- **MINOR** — a new module, size preset or capability. Existing builds stay valid.
- **PATCH** — corrections, documentation, genuine drop-in substitutions.

Anyone who built against an older version can read down to their version and see
exactly what would have to change. See [`CHANGELOG.md`](CHANGELOG.md).

---

## Honest status

A design under construction, not a finished kit.

- The `m` build is fully drawn, specified and costed. The other four sizes are
  solved but not yet drawn.
- The generators still carry their own constants rather than reading from
  `design/`. Wiring them to the solver is the 0.2.0 work.
- **The LED part number is unresolved.** Both options in BOM Rev E are dead, and
  one of them was never electrically valid alongside the drivers specified next
  to it. [`docs/05-electrical.md`](docs/05-electrical.md) has the detail. Do not
  buy drivers until this closes.
- The Jetson is set up and its core layer (supervisor, safety governor, state
  store, Home Assistant bridge) runs on the reference build. The drivers,
  services and agents wait on the hardware they drive.
  [`docs/08-arm.md`](docs/08-arm.md) has the bring-up, including the steps that
  cost me an evening.

Open items live in `CHANGELOG.md` under the current version.

---

Built for [Red Tower](https://github.com/v1proxy/RedTower), a house in Houston,
and written down so it can be built somewhere else. Questions are welcome at
contact@vittorionetti.com.
