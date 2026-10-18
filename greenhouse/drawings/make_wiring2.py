#!/usr/bin/env python3
"""Sheet E-02: network, and the typical tier node (A / B / C).

GPIO numbers are copied from esphome/common/tier.yaml and common/exhaust.yaml.
I2C addresses are the ones the ESPHome components are configured with.
Probe-to-channel mapping is read out of greenhouse-tier-a/b/c.yaml.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schem import *   # noqa: F401,F403

X1, Y1 = 1400, 940
COL = 1206
fig, ax = sheet(22.4, 15.0, (0, X1), (0, Y1),
                "NETWORK & TIER NODE", "VLAN 10, PoE, and the A / B / C node "
                "typical", "E-02")
ax.plot([COL - 12, COL - 12], [70, Y1 - 16], color=RULE, lw=1.0, zorder=0)

ax.text(22, Y1 - 20, "Herb Tower  ·  network and tier-node wiring",
        fontsize=18, fontweight="bold", color=INK, va="top")
ax.text(22, Y1 - 46,
        "Tiers A, B and C run identical hardware and the same ESPHome packages. "
        "Only the probe count and the Tier C exhaust block differ, both called out below.",
        fontsize=9.4, color=DIM, va="top")

# ================================================================ network
house = Box(ax, 30, 790, 214, 76, "HOUSE LAN",
            "pfSense 192.168.10.1\nVLAN 10 (IoT), tagged\nalso the NTP server the\n"
            "nodes fall back on", kind="net")
house.port("out", "r", 0.5)

sw = Box(ax, 300, 782, 560, 92, "PoE SWITCH   TP-Link TL-SG108PE",
         "8 port gigabit, 4 x 802.3af PoE, VLAN capable", tag="G052", kind="net")
sw.port("up", "l", 0.5)
wire(ax, [house.p("out"), sw.p("up")], color=NET, lw=2.0, label="uplink, VLAN 10 tagged")

ports = [("P1 PoE", "greenhouse-tier-a", ".11"), ("P2 PoE", "greenhouse-tier-b", ".12"),
         ("P3 PoE", "greenhouse-tier-c", ".13"), ("P4 PoE", "greenhouse-utility", ".14"),
         ("P5", "Jetson Orin Nano", ".20"), ("P6", "FluidNC controller", ".21"),
         ("P7", "myCobot 280 Pi", ".22"), ("P8", "uplink to the house", "trunk")]
for i, (p, who, ip) in enumerate(ports):
    xx = 300 + 560 * (i + 0.5) / 8
    ax.plot([xx, xx], [782, 768], color=NET, lw=1.4, zorder=4)
    ax.text(xx, 764, p.split()[0], ha="center", va="top", fontsize=7.0,
            fontweight="bold", color=NET, zorder=5)

ax.add_patch(Rectangle((884, 752), 306, 124, facecolor="#fbfcfc",
                       edgecolor=RULE, lw=0.8, zorder=4))
ax.text(892, 866, "PORT ASSIGNMENT", fontsize=7.6, fontweight="bold", color=INK,
        va="top", zorder=5)
for i, (p, who, ip) in enumerate(ports):
    yy = 851 - i * 12.4
    ax.text(892, yy, p, fontsize=6.9, color=NET, va="top", zorder=5,
            fontweight="bold")
    ax.text(936, yy, who, fontsize=6.9, color=INK, va="top", zorder=5)
    ax.text(1182, yy, ip, fontsize=6.9, color=DIM, va="top", ha="right", zorder=5)

# ================================================================ the node
nd = Box(ax, 452, 280, 302, 400, "ESP32-POE-ISO     greenhouse-tier-{A|B|C}",
         "Olimex, isolated 802.3af PoE\nESP-IDF framework, ESPHome\n"
         "LAN8720 PHY on board:\nMDC 23 · MDIO 18 · CLK 17 · PWR 12",
         tag="G051", kind="node", title_fs=9.6)
nd.port("eth", "t", 0.5)
nd.left("GPIO33", "GPIO4", "GPIO32", "GPIO36", "GPIO14", "GPIO39",
        fs=7.4, start=322, span=258)
nd.right("GPIO13  SDA", "GPIO16  SCL", fs=7.4, start=560, span=60)
wire(ax, [(nd.p("eth")[0], 680), (nd.p("eth")[0], 726), (335, 726), (335, 768)],
     color=NET, lw=2.0, label="Cat6A + 48 V PoE")

ax.text(603, 298,
        "3V3 and GND reach every I2C board over STEMMA QT (G049)\n\n"
        "WHAT THIS NODE PUBLISHES TO HOME ASSISTANT\n"
        "air temperature  ·  humidity  ·  VPD  ·  leaf VPD  ·  leaf-to-air delta\n"
        "canopy temperature  ·  light 515 / 680 / clear / NIR  ·  fan RPM\n"
        "one moisture % and one raw probe voltage per pot  ·  median moisture\n"
        "driest-plant moisture  ·  grow light  ·  circulation fan  ·  uptime\n\n"
        "CONFIG ENTITIES IT KEEPS LOCALLY\n"
        "lights-on hour  ·  photoperiod  ·  light intensity %  ·  fan duty %\n"
        "light schedule on / off",
        ha="center", va="bottom", fontsize=7.0, color=DIM, linespacing=1.5)

# ---------------------------------------------------------------- left side
acr = Box(ax, 40, 612, 250, 76, "AC RELAY  →  LED DRIVER",
          "1-ch opto relay, 3.3 V coil\ncuts the driver's mains at night\nsee sheet E-01",
          tag="G020", kind="act")
acr.port("i", "r", 0.5)
wire(ax, [nd.p("GPIO33"), (360, nd.p("GPIO33")[1]), (360, acr.p("i")[1]), acr.p("i")],
     color=SIG, lw=1.3)

dimb = Box(ax, 40, 512, 250, 76, "DIM INTERFACE",
           "1 k → 2N2222A base; C-E across\nDIM+ / DIM- of the HLG driver\n"
           "ledc 1 kHz, inverted, min 10 %", tag="G021", kind="act")
dimb.port("i", "r", 0.5)
wire(ax, [nd.p("GPIO4"), (348, nd.p("GPIO4")[1]), (348, dimb.p("i")[1]), dimb.p("i")],
     color=SIG, lw=1.3)

cfan = Box(ax, 40, 392, 250, 94, "CIRCULATION FAN",
           "Noctua NF-A8 PWM, 12 V\npin 4 PWM ← GPIO32, 25 kHz\n"
           "pin 3 tach → GPIO36 (input only)\n2 pulses per rev, x0.5 in ESPHome",
           tag="G023", kind="load")
cfan.port("pwm", "r", 0.68); cfan.port("tach", "r", 0.30)
wire(ax, [nd.p("GPIO32"), (336, nd.p("GPIO32")[1]), (336, cfan.p("pwm")[1]),
          cfan.p("pwm")], color=SIG, lw=1.3)
wire(ax, [nd.p("GPIO36"), (324, nd.p("GPIO36")[1]), (324, cfan.p("tach")[1]),
          cfan.p("tach")], color=SIG, lw=1.3)

efan = Box(ax, 40, 258, 250, 100, "EXHAUST FANS     TIER C ONLY",
           "2 x Noctua NF-F12 PWM, 12 V\nwired in parallel on one PWM\npin 4 ← GPIO14, 25 kHz\n"
           "one tach → GPIO39 (input only)", tag="G022", kind="load")
efan.port("pwm", "r", 0.68); efan.port("tach", "r", 0.30)
wire(ax, [nd.p("GPIO14"), (312, nd.p("GPIO14")[1]), (312, efan.p("pwm")[1]),
          efan.p("pwm")], color=SIG, lw=1.3, ls=(0, (5, 3)))
wire(ax, [nd.p("GPIO39"), (300, nd.p("GPIO39")[1]), (300, efan.p("tach")[1]),
          efan.p("tach")], color=SIG, lw=1.3, ls=(0, (5, 3)))
ax.text(165, 246, "dashed = Tier C node only (common/exhaust.yaml)",
        ha="center", va="top", fontsize=7.0, color=DIM, style="italic")

# ---------------------------------------------------------------- I2C chain
BUSX = 844
wire(ax, [nd.p("GPIO13  SDA"), (BUSX, nd.p("GPIO13  SDA")[1])], color=I2C, lw=1.5)
wire(ax, [nd.p("GPIO16  SCL"), (BUSX - 10, nd.p("GPIO16  SCL")[1])], color=I2C, lw=1.5)
ax.plot([BUSX, BUSX], [140, nd.p("GPIO13  SDA")[1]], color=I2C, lw=2.4, zorder=2)
ax.plot([BUSX - 10, BUSX - 10], [140, nd.p("GPIO16  SCL")[1]], color=I2C, lw=2.4,
        zorder=2)
ax.text(BUSX + 4, 736, "I2C  100 kHz\nSTEMMA QT daisy chain\nscan: true at boot",
        fontsize=7.2, color=I2C, va="top", fontweight="bold")

i2c_parts = [
    (636, "AIR  T / RH", "Sensirion SHT45", "0x44", "G039", "sense",
     "drives VPD and leaf VPD"),
    (556, "SPECTRAL LIGHT", "AMS AS7341", "0x39", "G041", "sense",
     "F4 515 nm, F8 680 nm, clear, NIR"),
    (476, "CANOPY IR", "Melexis MLX90614", "0x5A", "G042", "sense",
     "leaf temperature, non-contact"),
    (396, "CO2     TIER C ONLY", "Sensirion SCD-41", "0x62", "G040", "sense",
     "true NDIR CO2, not a VOC proxy"),
]
for y, t, s, addr, tag, kind, extra in i2c_parts:
    b = Box(ax, 892, y, 250, 66, t, f"{s}\n{extra}", tag=f"{tag}  ·  {addr}", kind=kind)
    b.port("i", "l", 0.5)
    ls = (0, (5, 3)) if "TIER C" in t else "-"
    wire(ax, [(BUSX, b.p("i")[1]), b.p("i")], color=I2C, lw=1.4, ls=ls)
    ax.add_patch(Circle((BUSX, b.p("i")[1]), 2.1, facecolor=I2C, edgecolor="none",
                        zorder=5))
    ax.add_patch(Circle((BUSX - 10, b.p("i")[1] - 5), 2.1, facecolor=I2C,
                        edgecolor="none", zorder=5))

ads = []
for i, (y, addr) in enumerate([(300, "0x48"), (224, "0x49"), (148, "0x4A")]):
    b = Box(ax, 892, y, 192, 62, f"ADC  ads_{i+1}", f"Adafruit ADS1115, 16 bit\ngain 4.096 V",
            tag=f"G038  ·  {addr}", kind="sense")
    b.port("i", "l", 0.5)
    b.right("A0", "A1", "A2", "A3", fs=6.6, start=y + 6, span=34)
    ads.append(b)
    wire(ax, [(BUSX, b.p("i")[1]), b.p("i")], color=I2C, lw=1.4)
    ax.add_patch(Circle((BUSX, b.p("i")[1]), 2.1, facecolor=I2C, edgecolor="none",
                        zorder=5))
    ax.add_patch(Circle((BUSX - 10, b.p("i")[1] - 5), 2.1, facecolor=I2C,
                        edgecolor="none", zorder=5))

probes = Box(ax, 1104, 148, 84, 214, "PROBES",
             "DFRobot\nSEN0193\ncapacitive\n\n3V3 / GND\n+ analog\nout\n\n10 per tier\n7 on Tier A",
             tag="G037", kind="sense", fs=7.0, title_fs=8.6)
for b in ads:
    for ch in ("A0", "A1", "A2", "A3"):
        p = b.p(ch)
        wire(ax, [p, (1104, p[1])], color=SIG, lw=1.0)

note(ax, 868, 134,
     "PROBE TO CHANNEL MAP, straight out of the node YAML\n"
     "Tier A (7 pots):  A01-A04 → ads_1 A0..A3   ·   A05-A07 → ads_2 A0..A2\n"
     "Tier B (10 pots): B01-B04 → ads_1 A0..A3   ·   B05-B08 → ads_2 A0..A3   ·   B09-B10 → ads_3 A0..A1\n"
     "Tier C (10 pots): C01-C04 → ads_1 A0..A3   ·   C05-C08 → ads_2 A0..A3   ·   C09-C10 → ads_3 A0..A1\n"
     "Every probe carries its own dry_v / wet_v calibration pair in the node file. Watering decisions use\n"
     "the MEDIAN of the tier, so one failed or mis-seated probe cannot flood a shelf.", fs=7.4)

# =============================================================== notes col
legend(ax, COL, Y1 - 36, [
    (NET, "ethernet + PoE"),
    (I2C, "I2C bus (SDA / SCL)"),
    (SIG, "logic / analog signal"),
], title="Nets")

note(ax, COL, Y1 - 100,
     "THE PORT COUNT IS THE CONSTRAINT\n\n"
     "Four PoE ports, four nodes. There is no fifth PoE\n"
     "port, so the BOM's spare ESP32-POE-ISO (G051 is\n"
     "quantity 5) cannot be brought online without a PoE\n"
     "injector or a bigger switch. Worth settling before\n"
     "you cable: a TL-SG1016PE leaves room to grow.\n\n"
     "Everything greenhouse sits on VLAN 10 with no route\n"
     "to the house LAN except through pfSense. Home\n"
     "Assistant reaches the nodes over the ESPHome native\n"
     "API with an encryption key, not MQTT.", fs=7.6)

note(ax, COL, 688,
     "WHY PoE AND NOT WIFI\n\n"
     "An aluminium frame full of LED drivers and\n"
     "stepper cable is a poor place for 2.4 GHz.\n"
     "The ESP32-POE-ISO is galvanically isolated,\n"
     "which also keeps the PHY out of the ground\n"
     "loop between the LED drivers and the pump.\n"
     "One cable per tier carries power and data.", fs=7.6)

note(ax, COL, 548,
     "PINS THAT ARE INPUT-ONLY\n\n"
     "GPIO36 and GPIO39 can only read. That is fine,\n"
     "they are both fan tachometers, but it means\n"
     "neither can ever be repurposed as an output.\n"
     "GPIO34, 35, 37 and 38 are the remaining input-\n"
     "only pins if more tachs are added.\n\n"
     "GPIO12 is the PHY power pin and GPIO17 the\n"
     "50 MHz clock out. Do not use either, and do not\n"
     "hang anything on GPIO0 during flashing.", fs=7.6)

note(ax, COL, 380,
     "LOCAL AUTONOMY\n\n"
     "Each tier node keeps its own SNTP clock and\n"
     "runs its own 30-minute sunrise and sunset ramp.\n"
     "Tier C additionally runs a local thermostat on\n"
     "the exhaust fans: minimum duty, plus 25 % per\n"
     "degree over setpoint, with a humidity override\n"
     "at 80 %, and full ventilation if the temperature\n"
     "sensor stops reporting.\n\n"
     "Pull the network out and the greenhouse keeps\n"
     "lighting, ventilating and sensing. Only the agent\n"
     "and the dashboards go away.", fs=7.6)

note(ax, COL, 180,
     "WIRING PRACTICE\n\n"
     "• Probe leads and the 12 V fan pairs run in\n"
     "  separate bundles from the LED driver output.\n"
     "• All I2C in STEMMA QT, one chain per tier, total\n"
     "  length under about 1 m at 100 kHz.\n"
     "• Ferrule every stranded conductor (G081).\n"
     "• Conformal coat the ADS1115 boards before they\n"
     "  go anywhere near the trays (G050).", fs=7.6)

out = "/home/claude/outputs/wiring_E02_network.png"
os.makedirs("/home/claude/outputs", exist_ok=True)
fig.savefig(out, dpi=150, facecolor="white")
print("saved", out)
