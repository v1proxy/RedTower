# Herb Tower

An indoor smart greenhouse: 27 plants on three tiers in a 1397 × 457 × 1829 mm 4040 T-slot
cabinet, with per-pot moisture probes, per-tier climate sensing, dimmable LED bars, drip
irrigation, a camera pair and a robot arm on a gantry. Claude decides the tending strategy;
Home Assistant is the interface and the record.

Part of the RedTower house project, Houston.

## Layout

```
esphome/          node firmware: three tier nodes + one utility node. Hard interlocks
                  live here and refuse regardless of what anything upstream asks.
homeassistant/    the package: entities, scripts, dashboard
jetson/           the agents and the robot stack (Jetson Orin Nano Super)
drawings/         the sheet-metal and frame drawings, generated not drawn
sendcutsend/      the DXFs that go to the cutter, and the unfolder that makes them
build_bom_*.py    the bill of materials, each rev a full generator
opex_model.py     daily running cost: electricity + tokens
```

## The three control layers

Each layer has exactly one job, and the separation is deliberate: adding a second actuator
would mean two things could water the same zone.

| layer | cadence | may actuate? |
| --- | --- | --- |
| `esphome/` node firmware | continuous | hard interlocks, refuses regardless of what is asked |
| `jetson/rule_loop.py` | every 5 min | **no** — watches the bands and escalates only |
| `jetson/claude_gardener.py` | hourly, and on escalation | yes, clamped to `LIMITS` |
| `jetson/plant_tender.py` | 27 plants/day | proposes; `robot_supervisor.py` gates motion |

Kill switch: `input_boolean.gh_claude_autonomy` in Home Assistant. Off means the gardener
still thinks and journals but executes nothing.

## Running cost

$1.03/day, about $376/year: $0.56 electricity (3.625 kWh/day, 70% of it lighting) and
$0.47 of tokens. `python3 opex_model.py` recomputes both and prints the breakdown.

The agent side started at $765/year and came down 78% through four changes: the static
prompt head on a 1 h cache breakpoint, the journal trimmed from 24 h of raw rows to 6 h of
digested lines, hourly instead of half-hourly with `rule_loop.py` covering the gap, and
Haiku on the routine loop with Sonnet kept for the per-plant vision pass.

## Sheet metal

The trays and base pan are 1.6 mm 5052 H32, laser cut and bent by SendCutSend. They are not
drawn by hand: `sendcutsend/unfold.py` is a generic unfolder that takes a floor polygon plus
which edges are flanged and emits the flat pattern, with bend deduction, bend relief arcs,
and mitred relief at re-entrant corners. `sendcutsend/make_dxf_rev4.py` defines the parts and
checks every one against the cutter's size and bend-length limits before writing the DXF.

Because the cabinet is 1397 mm wide and the largest bendable blank is 44 in, each tray and
the pan are two pieces with a 40 mm shingle lap over a middle rail.

`drawings/` regenerates every drawing from the same model, and `make_slotplan.py` parses the
shipped DXFs rather than the model, so it cannot show a hole the cutter will not make.

## Setup

Secrets are never committed. Copy each `.example` file, fill it in, and keep the copy out of
git (`.gitignore` already covers the real names):

```
esphome/secrets.example.yaml  ->  secrets.yaml      in the ESPHome config folder
jetson/gardener.example.json  ->  /opt/greenhouse/gardener.json
jetson/robot.example.json     ->  /opt/greenhouse/robot.json
```

Then on the Jetson:

```
sudo cp jetson/*.py /opt/greenhouse/
sudo cp jetson/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now greenhouse-gardener greenhouse-rule-loop
```

`claude_gardener.py` checks its configured model id against the API at boot, so a wrong id
fails on `systemctl start` rather than silently at 3 a.m.

## Watching it

The gardener publishes over MQTT discovery:

- `sensor.greenhouse_claude_last_decision`
- `sensor.greenhouse_claude_actions`
- `sensor.greenhouse_claude_cost` — USD since process start
- `sensor.greenhouse_claude_cache_hit` — % of input tokens served from cache

If the cache hit rate stays near zero after the first run of an hour, the cached prefix is
not being hit and something upstream of the breakpoint is changing between calls. That is
the one thing worth watching.
