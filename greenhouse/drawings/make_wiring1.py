#!/usr/bin/env python3
"""Sheet E-01: Herb Tower power distribution and safety circuit.

Every part number and rating comes from build_bom_revE.py. Every GPIO comes
from the pin-map headers in esphome/common/*.yaml and greenhouse-utility.yaml.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schem import *   # noqa: F401,F403

X1, Y1 = 1400, 940
COL = 1212                     # left edge of the notes column
fig, ax = sheet(22.4, 15.0, (0, X1), (0, Y1),
                "POWER & SAFETY", "Single line: 120 V AC, 24 V DC, 12 V DC, "
                "E-stop chain", "E-01")
ax.plot([COL - 14, COL - 14], [70, Y1 - 16], color=RULE, lw=1.0, zorder=0)

ax.text(22, Y1 - 20, "Herb Tower  ·  electrical single line",
        fontsize=18, fontweight="bold", color=INK, va="top")
ax.text(22, Y1 - 46,
        "Part numbers and ratings from BOM Rev E; GPIO assignments from the ESPHome "
        "pin maps. Where a rating is still unconfirmed the note says so.",
        fontsize=9.4, color=DIM, va="top")

# ===================================================================== AC in
ROWA, HA_ = 800, 54
wall = Box(ax, 20, ROWA, 104, HA_, "WALL OUTLET", "120 V AC · 20 A\nkitchen branch",
           kind="ac").right("L", "N", "PE", fs=6.6, pad=7)
gfci = Box(ax, 152, ROWA, 146, HA_, "GFCI CORD",
           "Woodhead 15050-3TTM\nMANUAL reset · 15 A", tag="G072", kind="ac") \
    .left("L", "N", "PE", fs=6.6, pad=7).right("L", "N", "PE", fs=6.6, pad=7)
inlet = Box(ax, 326, ROWA, 156, HA_, "FUSED INLET + SWITCH",
            "Schurter KD14-1101-151\n2-pole switch · 5x20 fuse", tag="G073", kind="ac") \
    .left("L", "N", "PE", fs=6.6, pad=7).right("L", "N", "PE", fs=6.6, pad=7)
pzem = Box(ax, 510, ROWA, 152, HA_, "ENERGY METER",
           "Peacefair PZEM-004T v3\nCT on L · 100 A variant", tag="G080", kind="ac") \
    .left("L", "N", fs=6.6, pad=11).right("L", "N", fs=6.6, pad=11)

for a, b in ((wall, gfci), (gfci, inlet), (inlet, pzem)):
    for pin in ("L", "N"):
        wire(ax, [a.p(pin), b.p(pin)], color=AC, lw=1.6)
wire(ax, [wall.p("PE"), gfci.p("PE")], color=GND, lw=1.4)
wire(ax, [gfci.p("PE"), inlet.p("PE")], color=GND, lw=1.4)
pe = inlet.p("PE")
wire(ax, [pe, (492, pe[1]), (492, ROWA - 24)], color=GND, lw=1.4)
gnd(ax, 492, ROWA - 24, size=4.4)
ax.text(500, ROWA - 30, "PE bonded to the 40-series frame, 14 AWG green,\n"
                        "one star point at the base bay",
        fontsize=7.0, color=GND, va="center")

wire(ax, [(662, ROWA + 38), (700, ROWA + 38), (700, ROWA + 66)], color=SIG, lw=1.2)
ax.text(706, ROWA + 66, "TTL UART → utility node GPIO5 TX / GPIO36 RX  (sheet E-02)",
        fontsize=7.2, color=SIG, va="center")

# ================================================================== AC bus
ACY = 762
bus(ax, 56, 1176, ACY, color=AC, lw=3.6, label="120 V AC  L / N", lx=52)
wire(ax, [(586, ROWA), (586, ACY)], color=AC, lw=1.6)
ax.add_patch(Circle((586, ACY), 2.4, facecolor=AC, edgecolor="none", zorder=5))

# =============================================================== relay row
ROWB, HB = 656, 70
relays = []
for i, (lbl, gp) in enumerate([("TIER A", "GPIO33"), ("TIER B", "GPIO33"),
                               ("TIER C", "GPIO33"), ("HUMIDIFIER", "GPIO15")]):
    bx = 40 + i * 154
    r = Box(ax, bx, ROWB, 134, HB, f"AC RELAY  {lbl}",
            "1-channel opto relay\n3.3 V coil · 10 A NO\nswitches the driver's mains",
            tag=f"G020  ·  {gp}", kind="act")
    r.port("acin", "t", 0.28); r.port("acout", "b", 0.28); r.port("sig", "r", 0.22)
    relays.append(r)
    tap(ax, bx + 134 * 0.28, ACY, ROWB + HB, color=AC, lw=1.5)
    wire(ax, [r.p("sig"), (bx + 148, ROWB + HB * 0.22)], color=SIG, lw=1.1)

ax.text(40, ROWB - 10,
        "Four identical opto relays. Three cut the mains to the LED drivers at night; "
        "the fourth is the humidifier, hard-capped by a 30-minute watchdog in ESPHome.",
        fontsize=7.4, color=DIM, va="top")

# =============================================================== AC loads
ROWC, HC = 530, 92
drivers = []
spec = [("LED DRIVER  TIER A", "Mean Well HLG-80H-C700B\n700 mA CC · 84 to 129 V", "G018"),
        ("LED DRIVER  TIER B", "Mean Well HLG-60H-C700B\n700 mA CC · 50 to 100 V", "G019"),
        ("LED DRIVER  TIER C", "Mean Well HLG-60H-C700B\n700 mA CC · 50 to 100 V", "G019")]
for i, (t, s, tag) in enumerate(spec):
    bx = 40 + i * 154
    d = Box(ax, bx, ROWC, 134, HC, t, s, tag=tag, kind="psu")
    d.port("acin", "t", 0.28)
    d.left("DIM+", "DIM-", fs=6.6, start=ROWC + 9, span=24)
    d.port("out", "b", 0.52)
    drivers.append(d)
    wire(ax, [relays[i].p("acout"), d.p("acin")], color=AC, lw=1.5)

hum = Box(ax, 502, ROWC, 134, HC, "HUMIDIFIER",
          "Crane EE-5301 Drop\nmechanical dial, so it\nresumes after a power cut\n"
          "ducted 50 mm into the lane", tag="G025", kind="load")
hum.port("acin", "t", 0.28)
wire(ax, [relays[3].p("acout"), hum.p("acin")], color=AC, lw=1.5)

lrs = Box(ax, 664, ROWC, 150, HC, "24 V SUPPLY",
          "Mean Well LRS-350-24\n350 W · 14.6 A\nthe only DC source", tag="G074", kind="psu")
lrs.port("acin", "t", 0.24); lrs.right("V+", "V-", fs=7.0, start=ROWC + 12, span=26)
tap(ax, 664 + 150 * 0.24, ACY, ROWC + HC, color=AC, lw=1.7)

sw = Box(ax, 840, ROWC, 152, HC, "PoE SWITCH",
         "TP-Link TL-SG108PE\n8 port · 4 x 802.3af\nVLAN 10 · 192.168.10.x",
         tag="G052", kind="net")
sw.port("acin", "t", 0.24); sw.port("poe", "b", 0.5)
tap(ax, 840 + 152 * 0.24, ACY, ROWC + HC, color=AC, lw=1.5)

jet = Box(ax, 1016, ROWC, 160, HC, "JETSON + ARM PSUs",
          "Orin Nano Super, 19 V brick\nmyCobot 280 Pi, own brick\nboth OEM, straight off AC",
          tag="G053 / G082", kind="psu")
jet.port("acin", "t", 0.24)
tap(ax, 1016 + 160 * 0.24, ACY, ROWC + HC, color=AC, lw=1.5)

wire(ax, [sw.p("poe"), (sw.p("poe")[0], ROWC - 26)], color=NET, lw=2.2)
ax.text(sw.p("poe")[0] + 8, ROWC - 14,
        "4 x PoE 802.3af, 48 V over Cat6A → the four ESP32-POE-ISO nodes (sheet E-02).\n"
        "The nodes have no local supply: pull a patch cable and that tier goes dark.\n"
        "PORT BUDGET IS FULL. 4 PoE to the nodes, then uplink, Jetson, FluidNC and one\n"
        "spare on the non-PoE half. A fifth node means a bigger switch.",
        fontsize=7.3, color=NET, va="top")

# =============================================================== LED strings
ROWD, HD = 412, 76
for i in range(3):
    bx = 40 + i * 154
    s = Box(ax, bx, ROWD, 134, HD, f"LED BARS  TIER {'ABC'[i]}",
            "2 x Kingbrite W55 560 mm\nLM301H + 660 nm\nWIRED IN SERIES",
            tag="G016", kind="load")
    s.port("in", "t", 0.52)
    wire(ax, [drivers[i].p("out"), s.p("in")], color=AC, lw=1.8,
         label="constant-current string" if i == 0 else None, lfs=6.6)

note(ax, 40, ROWD - 14,
     "LIGHTING, STILL OPEN (BOM Rev E): the Kingbrite seller publishes no forward voltage. Two 560 mm bars in series must land inside\n"
     "the driver window (84 to 129 V for the 80H, 50 to 100 V for the 60H) at 700 mA. Get Vf and If from the seller before ordering the\n"
     "drivers, or substitute the HLG QB120 V2 (G017), which publishes 21.8 to 22.64 V at 1050 to 2800 mA. The series count on this sheet\n"
     "is therefore provisional. Everything else on E-01 is confirmed.", fs=7.5)

dim = Box(ax, 664, ROWD - 2, 196, HD + 2, "DIM INTERFACE  x3",
          "GPIO4 → 1 k → 2N2222A base\ncollector-emitter across\nDIM+ / DIM- of the driver\n"
          "ESPHome ledc 1 kHz, inverted,\nmin_power 0.10 = driver floor",
          tag="G021", kind="node")
dim.port("toDim", "l", 0.70)
RAIL = drivers[0].p("DIM+")[1] - 8
wire(ax, [dim.p("toDim"), (648, dim.p("toDim")[1]), (648, RAIL),
          (drivers[0].p("DIM+")[0] - 12, RAIL)], color=SIG, lw=1.2)
for d in drivers:
    wire(ax, [(d.p("DIM+")[0] - 12, RAIL), (d.p("DIM+")[0] - 12, d.p("DIM+")[1]),
              d.p("DIM+")], color=SIG, lw=1.0)
    wire(ax, [(d.p("DIM-")[0] - 6, d.p("DIM-")[1]), d.p("DIM-")], color=SIG, lw=1.0)
    gnd(ax, d.p("DIM-")[0] - 6, d.p("DIM-")[1], size=3.4)

note(ax, 880, ROWD + HD - 26,
     "WHY A TRANSISTOR AND NOT A 0 TO 10 V OUTPUT\n"
     "The HLG \"B\" types dim by resistance or PWM across DIM+ / DIM-.\n"
     "Shorting those two pins is MINIMUM output, which is why the ESPHome\n"
     "output carries inverted: true. Full light is the transistor fully off,\n"
     "so a dead or unplugged ESP32 fails to FULL LIGHT, never to dark.\n"
     "That is exactly why GPIO33 switching the driver's mains, one row up,\n"
     "is the authoritative off and the dimmer is only a dimmer.", fs=7.5)

# ================================================================= 24 V
fb = Box(ax, 664, 330, 206, 64, "FUSE BLOCK",
         "Blue Sea 5025 · 6 circuit ATO\ncommon 24 V return bar", tag="G077", kind="psu")
fb.port("in", "t", 0.20); fb.port("out", "b", 0.20)
wire(ax, [lrs.p("V+"), (834, lrs.p("V+")[1]), (834, 414), (fb.p("in")[0], 414),
          fb.p("in")], color=V24, lw=2.0)
wire(ax, [lrs.p("V-"), (824, lrs.p("V-")[1]), (824, 404), (640, 404), (640, 290)],
     color=GND, lw=1.6)

V24Y, V0Y = 306, 290
bus(ax, 56, 1176, V24Y, color=V24, lw=3.6, label="24 V DC +", lx=52)
bus(ax, 56, 1176, V0Y, color=GND, lw=2.4, label="0 V", lx=52)
wire(ax, [fb.p("out"), (fb.p("out")[0], V24Y)], color=V24, lw=2.2)
ax.add_patch(Circle((fb.p("out")[0], V24Y), 2.4, facecolor=V24, edgecolor="none",
                    zorder=5))

# ============================================================== 24 V row
ROWE, HE = 168, 84
es = Box(ax, 40, ROWE, 152, HE, "E-STOP",
         "Eaton M22-PV head + M22-A collar\n2 x M22-K01 NC blocks\n"
         "terminals 11-12 and 21-22", tag="G078 / b / c", kind="safe")
estop(ax, 62, ROWE + 24, "")

sr = Box(ax, 208, ROWE, 152, HE, "SAFETY RELAY",
         "Omron G9SE-201 · 24 VDC\ndual channel\nmanual reset", tag="G079", kind="safe")
sr.port("A1", "t", 0.16)
sr.left("T11", "T12", "T21", "T22", fs=6.6, start=ROWE + 8, span=52)
sr.right("13", "14", "41", "42", fs=6.6, start=ROWE + 8, span=52)
for nm in ("T11", "T12", "T21", "T22"):
    yy = sr.p(nm)[1]
    wire(ax, [(es.x + es.w, yy), sr.p(nm)], color=SAFE, lw=1.3)
fuse(ax, 208 + 152 * 0.16, V24Y - 24, label="1 A")
tap(ax, 208 + 152 * 0.16, V24Y, V24Y - 24, color=V24, lw=1.4)
wire(ax, [(208 + 152 * 0.16, V24Y - 24), sr.p("A1")], color=SAFE, lw=1.5)

ddr = Box(ax, 376, ROWE, 140, HE, "24 → 12 V",
          "Mean Well DDR-15G-12\n15 W · 1.25 A\nfeeds every fan", tag="G075", kind="psu")
ddr.port("in", "t", 0.22); ddr.port("out", "b", 0.5)
fuse(ax, 376 + 140 * 0.22, V24Y - 24, label="3 A")
tap(ax, 376 + 140 * 0.22, V24Y, V24Y - 24, color=V24, lw=1.5)
wire(ax, [(376 + 140 * 0.22, V24Y - 24), ddr.p("in")], color=V24, lw=1.5)

mos = Box(ax, 532, ROWE, 166, HE, "MOSFET BOARD  4 ch",
          "IRF540 module\nch1 pump  GPIO32\nch2 / 3 / 4 valves\nGPIO33 / GPIO4 / GPIO2",
          tag="G036", kind="act")
mos.port("in", "t", 0.18); mos.port("o1", "b", 0.24); mos.port("o2", "b", 0.70)
fuse(ax, 532 + 166 * 0.18, V24Y - 24, label="7.5 A")
tap(ax, 532 + 166 * 0.18, V24Y, V24Y - 24, color=V24, lw=1.5)
wire(ax, [(532 + 166 * 0.18, V24Y - 24), mos.p("in")], color=V24, lw=1.5)

fnc = Box(ax, 714, ROWE, 162, HE, "MOTION CONTROLLER",
          "Elecrow 4-axis FluidNC\nESP32 + 4 x TMC2209\nX and Z axes used\nUSB / wifi to the Jetson",
          tag="G067", kind="node")
fnc.port("in", "t", 0.22); fnc.port("x", "b", 0.30); fnc.port("sig", "b", 0.72)

brk = Box(ax, 892, ROWE, 132, HE, "Z BRAKE",
          "24 V 4.5 W coil inside\n23HS22-4004D-B280\npower off = mast held",
          tag="G065", kind="safe")
brk.port("in", "t", 0.24)

# motion 24 V through the safety contact
tap(ax, 1112, V24Y, 278, color=V24, lw=1.6)
fuse(ax, 1112, 278, label="10 A")
contact(ax, 1112, 262, label="G9SE 13/14", color=SAFE, w=17)
wire(ax, [(1095, 262), (fnc.p("in")[0], 262), fnc.p("in")], color=SAFE, lw=1.7,
     label="24 V MOTION, safety-switched", lpos=0.62)
wire(ax, [(brk.p("in")[0], 262), brk.p("in")], color=SAFE, lw=1.7, dots=(0,))
wire(ax, [sr.p("13"), (370, sr.p("13")[1]), (370, 276), (1112, 276)],
     color=SAFE, lw=1.0, ls=(0, (4, 3)))
ax.text(560, 270, "13 / 14 contact, drawn at the load", fontsize=6.8, color=SAFE,
        ha="center", va="top")

wire(ax, [sr.p("41"), (370, sr.p("41")[1]), (370, 146), (690, 146)],
     color=SIG, lw=1.3)
ax.text(696, 146, "aux 41 / 42 → MCP23017 pin A6, \"Safety circuit tripped\".\n"
                  "ESPHome stops watering the instant this opens.",
        fontsize=7.2, color=SIG, va="center")

# ================================================================= 12 V + loads
V12Y = 128
bus(ax, 86, 470, V12Y, color=V12, lw=3.0, label="12 V DC", lx=82)
wire(ax, [ddr.p("out"), (ddr.p("out")[0], V12Y)], color=V12, lw=1.8)
ax.add_patch(Circle((ddr.p("out")[0], V12Y), 2.3, facecolor=V12, edgecolor="none",
                    zorder=5))

ROWF, HF = 42, 66
fans = Box(ax, 40, ROWF, 148, HF, "FANS  12 V",
           "3 x Noctua NF-A8  circulation\n2 x Noctua NF-F12  exhaust\n"
           "4-wire: PWM + tach to the nodes", tag="G022 / G023", kind="load")
fans.port("in", "t", 0.46)
wire(ax, [(fans.p("in")[0], V12Y), fans.p("in")], color=V12, lw=1.6)

pump = Box(ax, 204, ROWF, 148, HF, "PUMP  24 V",
           "SEAFLO SFDP2-012-035-21\n1.2 GPM diaphragm\nflyback diode at the pump",
           tag="G029", kind="act")
pump.port("in", "t", 0.5)
wire(ax, [mos.p("o1"), (mos.p("o1")[0], 116), (pump.p("in")[0], 116), pump.p("in")],
     color=V24, lw=1.5)

valves = Box(ax, 368, ROWF, 166, HF, "ZONE VALVES  24 V  x3",
             "U.S. Solid JFSV00052, 1/4 in\nnormally closed, Viton\nzone A / B / C",
             tag="G033", kind="act")
valves.port("in", "t", 0.5)
wire(ax, [mos.p("o2"), (mos.p("o2")[0], 106), (valves.p("in")[0], 106), valves.p("in")],
     color=V24, lw=1.5)

steps = Box(ax, 550, ROWF, 190, HF, "STEPPERS + LIMITS",
            "X  NEMA 23 2.8 A, belt and pinion\nZ  23HS22-4004D-B280 with brake\n"
            "4 x OpenBuilds Xtension limits", tag="G065 / G066 / G068", kind="act")
steps.port("in", "t", 0.30); steps.port("lim", "t", 0.76)
wire(ax, [fnc.p("x"), (fnc.p("x")[0], 122), (steps.p("in")[0], 122), steps.p("in")],
     color=V24, lw=1.5)
wire(ax, [fnc.p("sig"), (fnc.p("sig")[0], 112), (steps.p("lim")[0], 112), steps.p("lim")],
     color=SIG, lw=1.3)

note(ax, 760, 112,
     "CABLE CHAIN (Igus E14.1.028.0, two runs): stepper phases, the Z brake pair,\n"
     "12 V for the wrist light, Cat6A to the arm and the high-flex USB-C to the D405.\n"
     "Mains never enters the chain. Keep the motor pair and the Cat6A on opposite\n"
     "sides of the chain divider.", fs=7.4)

# ================================================================= notes col
legend(ax, COL, Y1 - 36, [
    (AC, "120 V AC mains"),
    (V24, "24 V DC"),
    (V12, "12 V DC"),
    (SAFE, "safety circuit"),
    (SIG, "logic / signal"),
    (NET, "ethernet + PoE"),
    (GND, "0 V / protective earth"),
])

note(ax, COL, Y1 - 150,
     "FAIL-SAFE BEHAVIOUR, BY DESIGN\n\n"
     "• The zone valves are normally closed and the\n"
     "  pump needs a MOSFET actively held on, so a\n"
     "  dead controller cannot water anything.\n\n"
     "• The Z stepper's brake is released BY 24 V, so\n"
     "  a power cut parks the mast instead of dropping\n"
     "  it through the trays.\n\n"
     "• The grow-light dim input fails to full light, so\n"
     "  GPIO33 cutting the driver's mains is the real off.\n\n"
     "• The GFCI is MANUAL reset. After a trip it stays\n"
     "  off until somebody walks over and pushes it.\n"
     "  Deliberate, for a cabinet holding water and mains.\n\n"
     "• Leak, door, float and safety-relay inputs are all\n"
     "  read locally by the utility node, which refuses\n"
     "  any watering request while one is active. Home\n"
     "  Assistant can REQUEST water through the\n"
     "  water_zone action; it can never switch the pump.",
     fs=7.5)

note(ax, COL, 416,
     "DUAL-CHANNEL E-STOP\n\n"
     "One M22-K01 NC block per channel. The G9SE-201\n"
     "cross-monitors the two, so a single welded or\n"
     "shorted contact is detected and the relay refuses\n"
     "to reset. That is why the BOM carries TWO contact\n"
     "blocks and not one.\n\n"
     "The 13/14 contact switches 24 V to the motion\n"
     "controller and the Z brake only. Sensing, lighting\n"
     "and the nodes stay alive through an E-stop, so the\n"
     "cabinet still reports what it sees.", fs=7.5)

note(ax, COL, 232,
     "NOT ON THE 24 V BUS\n\n"
     "The four ESP32-POE-ISO nodes (PoE, 48 V), the\n"
     "Jetson Orin Nano (19 V OEM brick), the myCobot\n"
     "280 Pi (its own brick) and the PoE switch itself.\n"
     "All four sit on the AC bus upstream of the 24 V\n"
     "supply, so a 24 V fault leaves compute and\n"
     "telemetry running.", fs=7.5)

out = "wiring_E01_power.png"
os.makedirs(".", exist_ok=True)
fig.savefig(out, dpi=150, facecolor="white")
print("saved", out)
