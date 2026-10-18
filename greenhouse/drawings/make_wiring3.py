#!/usr/bin/env python3
"""Sheet E-03: the utility node, its field inputs, and the water path.

Pin assignments are copied from esphome/greenhouse-utility.yaml. The interlock
logic described here is the water_zone script in that same file.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schem import *   # noqa: F401,F403

X1, Y1 = 1400, 940
COL = 1206
fig, ax = sheet(22.4, 15.0, (0, X1), (0, Y1),
                "UTILITY NODE & WATER", "Reservoir, pump, zone valves, leak and "
                "safety inputs", "E-03")
ax.plot([COL - 12, COL - 12], [70, Y1 - 16], color=RULE, lw=1.0, zorder=0)

ax.text(22, Y1 - 20, "Herb Tower  ·  utility node and water path",
        fontsize=18, fontweight="bold", color=INK, va="top")
ax.text(22, Y1 - 46,
        "Every interlock on this sheet runs locally on the node. Home Assistant can "
        "call the water_zone action; it has no path to the pump or the valves.",
        fontsize=9.4, color=DIM, va="top")

# ================================================================ the node
nd = Box(ax, 420, 360, 300, 400, "ESP32-POE-ISO     greenhouse-utility",
         "Olimex, isolated 802.3af PoE\nbase bay, inside the ZQ-121004 enclosure (G059)",
         tag="G051", kind="node", title_fs=9.6)
nd.port("eth", "t", 0.5)
nd.left("GPIO32", "GPIO33", "GPIO4", "GPIO2", "GPIO15", fs=7.4, start=418, span=250)
nd.right("GPIO13  SDA", "GPIO16  SCL", "GPIO14  1-Wire", "GPIO5  TX",
         "GPIO36  RX", fs=7.4, start=418, span=250)
wire(ax, [(nd.p("eth")[0], 760), (nd.p("eth")[0], 806)], color=NET, lw=2.0)
ax.text(nd.p("eth")[0] + 8, 790,
        "Cat6A + 48 V PoE from switch port P4, 192.168.10.14  (sheet E-02)",
        fontsize=7.4, color=NET, va="center")

ax.text(570, 376,
        "LOCAL SCRIPTS\nwater_zone(zone, seconds) · stop_watering\n"
        "pump_watchdog 300 s · humidifier_watchdog 30 min\n"
        "daily reset of the per-zone run totals at midnight",
        ha="center", va="bottom", fontsize=7.2, color=DIM, linespacing=1.5)

# ---------------------------------------------------------------- outputs
mos = Box(ax, 40, 596, 300, 120, "MOSFET BOARD  4 channel",
          "HiLetgo / generic IRF540 module, low-side switching on the 24 V rail\n"
          "ch1  pump      ← GPIO32\nch2  valve A   ← GPIO33\n"
          "ch3  valve B   ← GPIO4\nch4  valve C   ← GPIO2\n"
          "flyback diode across every coil", tag="G036", kind="act")
for i, (gp, t) in enumerate((("GPIO32", 0.84), ("GPIO33", 0.63),
                             ("GPIO4", 0.42), ("GPIO2", 0.21))):
    mos.port(gp, "r", t)
    wire(ax, [nd.p(gp), (382 - i * 10, nd.p(gp)[1]), (382 - i * 10, mos.p(gp)[1]),
              mos.p(gp)], color=SIG, lw=1.2)

pump = Box(ax, 40, 486, 142, 92, "PUMP",
           "SEAFLO 21 series\nSFDP2-012-035-21\n24 V · 1.2 GPM\ndiaphragm, self priming",
           tag="G029", kind="act")
valv = Box(ax, 198, 486, 142, 92, "ZONE VALVES  x3",
           "U.S. Solid JFSV00052\n1/4 in brass, Viton\n24 V normally closed\nA / B / C",
           tag="G033", kind="act")
pump.port("i", "t", 0.5); valv.port("i", "t", 0.5)
wire(ax, [(mos.p("GPIO32")[0] - 290, 596), (pump.p("i")[0], 596), pump.p("i")],
     color=V24, lw=1.4)
wire(ax, [(250, 596), (valv.p("i")[0], 596), valv.p("i")], color=V24, lw=1.4)

hum = Box(ax, 40, 376, 300, 86, "HUMIDIFIER RELAY",
          "same 1-channel opto relay as the lighting (G020), 3.3 V coil\n"
          "switches mains to the Crane EE-5301, ducted 50 mm into the lane\n"
          "hard-capped by humidifier_watchdog at 30 minutes", tag="G020 · G025",
          kind="act")
hum.port("i", "r", 0.4)
wire(ax, [nd.p("GPIO15"), (372, nd.p("GPIO15")[1]), (372, hum.p("i")[1]), hum.p("i")],
     color=SIG, lw=1.2)

# ---------------------------------------------------------------- I2C side
BUSX = 806
for pin in ("GPIO13  SDA", "GPIO16  SCL"):
    wire(ax, [nd.p(pin), (BUSX if "SDA" in pin else BUSX - 10, nd.p(pin)[1])],
         color=I2C, lw=1.5)
ax.plot([BUSX, BUSX], [500, nd.p("GPIO13  SDA")[1]], color=I2C, lw=2.4, zorder=2)
ax.plot([BUSX - 10, BUSX - 10], [500, nd.p("GPIO16  SCL")[1]], color=I2C, lw=2.4,
        zorder=2)

mcp = Box(ax, 836, 560, 190, 170, "I/O EXPANDER",
          "Adafruit MCP23017\n8 inputs used\nall with internal pull-ups",
          tag="G048  ·  0x20", kind="sense")
mcp.port("i", "l", 0.86)
mcp.right("A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", fs=6.8,
          start=570, span=146)
wire(ax, [(BUSX, mcp.p("i")[1]), mcp.p("i")], color=I2C, lw=1.4, dots=(0,))

inputs = [("A0", "Leak probe, base tray", "G046", "wet = lockout"),
          ("A1", "Leak probe, Tier A tray", "G046", "wet = lockout"),
          ("A2", "Leak probe, Tier B tray", "G046", "wet = lockout"),
          ("A3", "Leak probe, Tier C tray", "G046", "wet = lockout"),
          ("A4", "4 door reeds IN SERIES", "G047", "any door open = on"),
          ("A5", "Reservoir low float, NO", "G045", "low = stop watering"),
          ("A6", "Safety relay aux 41/42", "G079", "open = stop watering"),
          ("A7", "spare", "", "")]
ax.add_patch(Rectangle((1058, 554), 132, 184, facecolor="#fbfcfc",
                       edgecolor=RULE, lw=0.8, zorder=3))
for nm, who, tag, eff in inputs:
    p = mcp.p(nm)
    wire(ax, [p, (1058, p[1])], color=SIG, lw=1.1)
    ax.text(1064, p[1] + 3.2, who, fontsize=6.8, color=INK, va="bottom", zorder=5)
    ax.text(1064, p[1] - 2.8, f"{tag}   {eff}" if tag else eff, fontsize=6.1,
            color=DIM, va="top", zorder=5)

vl = Box(ax, 836, 470, 190, 72, "RESERVOIR LEVEL",
         "Adafruit VL53L0X\ntime of flight, 30 to 1000 mm\nreads down to a float puck",
         tag="G043  ·  0x29", kind="sense")
vl.port("i", "l", 0.5)
wire(ax, [(BUSX, vl.p("i")[1]), vl.p("i")], color=I2C, lw=1.4, dots=(0,))

ds = Box(ax, 836, 382, 190, 72, "WATER TEMPERATURE",
         "Adafruit DS18B20, waterproof\n1-Wire on GPIO14\n4k7 pull-up to 3V3",
         tag="G044", kind="sense")
ds.port("i", "l", 0.5)
wire(ax, [nd.p("GPIO14  1-Wire"), (784, nd.p("GPIO14  1-Wire")[1]), (784, ds.p("i")[1]),
          ds.p("i")], color=SIG, lw=1.3)

pz = Box(ax, 836, 294, 190, 72, "ENERGY METER",
         "Peacefair PZEM-004T v3\nModbus over TTL UART\nwhole-cabinet AC, see E-01",
         tag="G080", kind="sense")
pz.port("tx", "l", 0.66); pz.port("rx", "l", 0.30)
wire(ax, [nd.p("GPIO5  TX"), (772, nd.p("GPIO5  TX")[1]), (772, pz.p("tx")[1]),
          pz.p("tx")], color=SIG, lw=1.3)
wire(ax, [nd.p("GPIO36  RX"), (760, nd.p("GPIO36  RX")[1]), (760, pz.p("rx")[1]),
          pz.p("rx")], color=SIG, lw=1.3)

# ============================================================== water path
ax.text(40, 290, "WATER PATH", fontsize=10.5, fontweight="bold", color=INK,
        va="top")
ax.plot([40, 1188], [282, 282], color=RULE, lw=0.9, zorder=0)

WY, WH = 176, 92
res = Box(ax, 40, WY, 168, WH, "RESERVOIR",
          "Class A Customs T-0700\n7 gal = 26.5 L\n603 x 178 x 248 mm\n"
          "float switch + ToF puck", tag="G028", kind="sense")
res.port("o", "r", 0.4)
pmp = Box(ax, 236, WY, 150, WH, "PUMP",
          "SEAFLO 24 V\n1.2 GPM\nbypass diaphragm", tag="G029", kind="act")
pmp.port("i", "l", 0.4); pmp.port("o", "r", 0.4)
reg = Box(ax, 414, WY, 166, WH, "REGULATOR + FILTER",
          "1/2 in pressure regulator\nat the pump outlet, then\nreduced to 1/4 in line",
          tag="G032", kind="plain")
reg.port("i", "l", 0.4); reg.port("o", "r", 0.4)
man = Box(ax, 608, WY, 150, WH, "ZONE MANIFOLD",
          "3 x 1/4 in NC\nsolenoid valves\nA / B / C", tag="G033", kind="act")
man.port("i", "l", 0.4)
for t, nm in ((0.76, "zA"), (0.48, "zB"), (0.20, "zC")):
    man.port(nm, "r", t)

for a, b in ((res.p("o"), pmp.p("i")), (pmp.p("o"), reg.p("i")),
             (reg.p("o"), man.p("i"))):
    wire(ax, [a, b], color="#0891b2", lw=2.4)

zones = [("TIER A  ·  7 pots", "14 emitters x 0.5 GPH = 441 mL/min", 0.76),
         ("TIER B  ·  10 pots", "10 emitters x 0.5 GPH = 315 mL/min", 0.48),
         ("TIER C  ·  10 pots", "10 emitters x 0.5 GPH = 315 mL/min", 0.20)]
for i, (t, s, tt) in enumerate(zones):
    b = Box(ax, 800, WY + WH - 32 - i * 32, 270, 28, "", "", kind="load")
    ax.text(810, WY + WH - 32 - i * 32 + 18, t, fontsize=7.6, fontweight="bold",
            color=INK, va="center", zorder=5)
    ax.text(810, WY + WH - 32 - i * 32 + 8, s, fontsize=6.8, color=DIM,
            va="center", zorder=5)
    p = man.p(("zA", "zB", "zC")[i])
    wire(ax, [p, (800, WY + WH - 32 - i * 32 + 14)], color="#0891b2", lw=1.8)

note(ax, 40, 164,
     "DRAINAGE: every tray is a 25 mm-lip aluminium pan with no outlet, so each cycle leaves standing water. The leak probe in each tray is the\n"
     "last line of defence, not the first. Run the zones short and often rather than long and seldom.", fs=7.4)

note(ax, 790, 164,
     "VOLUME READING IS 13 % OPTIMISTIC\n"
     "greenhouse-utility.yaml still carries reservoir_litres: 30 and a comment about an 8 gal\n"
     "tank. BOM Rev E established that no 8 gal tank is made and substituted the 7 gal T-0700,\n"
     "which is 26.5 L. Change the substitution to 26.5 before you trust \"Reservoir volume\".\n"
     "dist_empty_mm 260 and dist_full_mm 40 still have to be measured after the tank is in.", fs=7.4)

# =============================================================== notes col
legend(ax, COL, Y1 - 36, [
    (NET, "ethernet + PoE"),
    (I2C, "I2C bus"),
    (SIG, "logic signal"),
    (V24, "24 V DC switched"),
    ("#0891b2", "water"),
])

note(ax, COL, Y1 - 124,
     "THE WATERING INTERLOCK, IN ORDER\n\n"
     "water_zone refuses outright if any of these\n"
     "is true, and logs the refusal:\n\n"
     "  · leak_lockout latched\n"
     "  · any_leak (A0..A3) currently wet\n"
     "  · reservoir_low float tripped\n"
     "  · safety_tripped (E-stop chain open)\n"
     "  · zone outside 1..3, or seconds <= 0\n\n"
     "If it passes:\n"
     "  1. close all three valves\n"
     "  2. open the requested valve\n"
     "  3. wait 500 ms, so the valve is open\n"
     "     before the pump builds pressure\n"
     "  4. run the pump for min(seconds, max_run_s)\n"
     "  5. stop the pump, wait 2 s to bleed through\n"
     "     the emitters, then close the valve\n"
     "  6. add the elapsed seconds to that zone's\n"
     "     daily total\n\n"
     "pump_watchdog kills the pump at 300 s no\n"
     "matter what the script thinks it is doing.", fs=7.5)

note(ax, COL, 396,
     "LEAK LOCKOUT IS STICKY\n\n"
     "Any wet probe latches leak_lockout in a\n"
     "restore_value global, so it survives a reboot.\n"
     "Clearing it needs the \"Clear leak lockout\"\n"
     "button AND every probe dry. A soaked tray\n"
     "cannot be cleared by power-cycling the node,\n"
     "which is the point.", fs=7.5)

note(ax, COL, 244,
     "WHAT HOME ASSISTANT CAN AND CANNOT DO\n\n"
     "CAN:  call esphome.greenhouse_utility_water_zone\n"
     "with a zone and a duration, call stop_watering,\n"
     "set the config numbers, read everything.\n\n"
     "CANNOT:  switch the pump or any valve. Those\n"
     "four switch entities are marked internal: true,\n"
     "so they are not exposed to the API at all.", fs=7.5)

out = "/home/claude/outputs/wiring_E03_utility.png"
os.makedirs("/home/claude/outputs", exist_ok=True)
fig.savefig(out, dpi=150, facecolor="white")
print("saved", out)
