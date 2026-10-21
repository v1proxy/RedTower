# Greenhouse

The greenhouse subsystem of [Red Tower](../README.md). Three parts, each usable
on its own.

| directory | layer | what it is |
|---|---|---|
| `esphome/` | **firmware** | Node firmware, one per tier plus a utility node. The hard interlocks live here and refuse regardless of what anything upstream asks. |
| `jetson/` | **software** | The containerized agent stack: a module bus, a safety governor, hardware links for the gantry and the arm, perception, and the language-model gateway. Has its own tests and CI. |
| `homeassistant/` | **interface** | The package, entities, scripts and dashboard card. |
| `drawings/` `sendcutsend/` `model/` | **hardware** | Frame, sheet metal and wiring, every file a generator rather than a drawing. The 3D model the drawings are rendered from. |
| `frame/` `gantry/` `enclosure/` `harvest/` | **assembly** | One model and one Maag assembly booklet each: the cabinet, the gantry, the panels and doors, and where the harvest goes (the dead-leaf tray and the side feeder). Cut files and prints come from the same models. |
| `build_bom_*.py` `opex_model.py` | **cost** | Bill of materials, one generator per revision, and the daily running-cost model. |
| `pfsense/` | **network** | The Jetson's place on the IoT VLAN. |

Start with [`COMMISSIONING.md`](COMMISSIONING.md) when you have hardware in
front of you, and with [`../docs/`](../docs/) when you are still deciding what
to build.

## The two software generations

`jetson/` is the engineered stack: modules with manifests, a governor with hard
limits, unit tests on an in-memory bus, Docker images and a GitHub Actions
workflow. This is the one to run.

`jetson/prototype/` holds the earlier loose scripts that proved the ideas
(`claude_gardener.py`, `rule_loop.py`, `plant_tender.py` and the systemd units).
They are kept because the tending logic in them is readable in a way the module
version is not, and because nothing that worked should be deleted silently.
They are superseded; do not deploy them alongside the stack, since both would
want to act on the same zones.
