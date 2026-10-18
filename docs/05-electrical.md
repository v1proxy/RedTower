# 5. Electrical

Four sheets, all generated from the BOM and the firmware pin maps:

- `greenhouse/drawings/wiring_E01_power.png` — 120 V AC, 24 V, 12 V, E-stop
- `greenhouse/drawings/wiring_E02_network.png` — VLAN/PoE and the tier node
- `greenhouse/drawings/wiring_E03_utility.png` — utility node and water
- `greenhouse/drawings/wiring_E04_motion.png` — gantry, arm, cameras, compute

Regenerate them after any BOM or pin change:

```bash
cd greenhouse/drawings
python3 make_wiring1.py && python3 make_wiring2.py
python3 make_wiring3.py && python3 make_wiring4.py
```

## Fail-safe behaviour, by design

- Zone valves are normally closed and the pump needs a MOSFET actively held on,
  so a dead controller cannot water anything.
- The Z brake is released **by** 24 V, so a power cut parks the mast rather than
  dropping it through the trays.
- The GFCI is **manual** reset. After a trip it stays off until somebody pushes
  it. That is deliberate in a cabinet holding water and mains.
- The grow-light dim input fails to **full light**. See below.

## The dimming trap

Mean Well HLG "B" type drivers dim by resistance or PWM across DIM+ / DIM−.
Shorting those two pins is **minimum** output. So the transistor that dims the
light is off at full brightness, and a dead or unplugged ESP32 leaves the lights
**on at 100 %**, not off.

That is why a relay cutting the driver's mains is in the design and is not
optional. The dimmer is only a dimmer; the relay is the off switch.

## Open: the LED part number

Both lighting options in BOM Rev E are currently dead ends.

**G016, Kingbrite W55 560 mm LM301H.** The AliExpress listing 404s. The product
still exists under a new listing, but it never published a forward voltage, which
was already flagged as the open risk: the specified drivers are constant-current
at 700 mA with a 84–129 V window (80H) or 50–100 V (60H), and whether two bars in
series land inside that window is unknown.

**G017, HLG QB120 V2.** The 4-pack is unavailable, and more importantly it is
**not electrically compatible** with the specified drivers: the QB120 V2 runs at
**1050 to 2800 mA**, and the BOM's drivers deliver 700 mA. It is also a
280 × 240 mm board, so it intrudes 37 mm into the gantry corridor. It was never
a drop-in alternate.

Published QB120 V2 figures, for anyone recalculating: 21.8 to 22.64 V, 1050 to
2800 mA, 120 × LM301H, up to 70 W, 280 × 240 mm.

Until this resolves, pick a bar whose vendor states Vf and If, compute the series
string voltage at your chosen current, and confirm it sits inside the driver
window with margin at both ends of the dimming range.
