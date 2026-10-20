#!/usr/bin/env python3
"""Sheet E-04: motion, vision, compute and the arm.

Service names come from jetson/*.service; the authority ceiling and kill switch
come from homeassistant/packages/greenhouse.yaml.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schem import *   # noqa: F401,F403

X1, Y1 = 1400, 940
COL = 1206
fig, ax = sheet(22.4, 15.0, (0, X1), (0, Y1),
                "MOTION, VISION & COMPUTE", "Gantry, arm, cameras, Jetson and the "
                "authority chain", "E-04")
ax.plot([COL - 12, COL - 12], [70, Y1 - 16], color=RULE, lw=1.0, zorder=0)

ax.text(22, Y1 - 20, "Herb Tower  ·  motion, vision and compute",
        fontsize=18, fontweight="bold", color=INK, va="top")
ax.text(22, Y1 - 46,
        "The gantry carries the arm along the long face of the cabinet, in the 254 mm "
        "corridor between the tray fronts and the back of the frame.",
        fontsize=9.4, color=DIM, va="top")

# ============================================================== the network
swr = Box(ax, 440, 812, 420, 58, "PoE SWITCH  ·  non-PoE half",
          "TP-Link TL-SG108PE, ports P5 / P6 / P7 on VLAN 10", tag="G052", kind="net")
for t, nm in ((0.22, "P5"), (0.5, "P6"), (0.78, "P7")):
    swr.port(nm, "b", t)
    ax.text(swr.p(nm)[0], 806, nm, ha="center", va="top", fontsize=7.0,
            fontweight="bold", color=NET)

# ================================================================== compute
jet = Box(ax, 380, 540, 320, 226, "JETSON ORIN NANO SUPER",
          "NVIDIA dev kit, 19 V OEM brick\n192.168.10.20 on VLAN 10\n"
          "Ubuntu + systemd services:\n"
          "greenhouse-gardener.service\ngreenhouse-rule-loop.service\n\n"
          "plant_perception · plant_vision\nplant_tender · robot_supervisor\n"
          "handeye_calibrate (one shot)", tag="G053", kind="node", title_fs=10.0)
jet.port("eth", "t", 0.22)
jet.port("nvme", "l", 0.70)
jet.port("usb1", "l", 0.34)
jet.port("usbc", "r", 0.52)
jet.port("api", "b", 0.32)
jet.port("arm", "r", 0.22)
wire(ax, [jet.p("eth"), (jet.p("eth")[0], 812)], color=NET, lw=1.8)

ssd = Box(ax, 56, 668, 224, 86, "NVMe SSD",
          "Crucial P3 500 GB (CT500P3SSD8) in the M.2 Key-M slot\n"
          "holds the image log and the model cache; format it on the\n"
          "Jetson, a prior Windows partition table is no obstacle",
          tag="G054", kind="plain")
ssd.port("o", "r", 0.5)
wire(ax, [ssd.p("o"), (348, ssd.p("o")[1]), (348, jet.p("nvme")[1]), jet.p("nvme")],
     color=SIG, lw=1.4, label="PCIe")

cam = Box(ax, 56, 548, 224, 92, "OVERVIEW CAMERA",
          "Arducam UB020201, IMX291\n1080p low-light WDR, 160 deg\nUVC over USB, fixed to the\n"
          "frame looking down the lane", tag="G055", kind="sense")
cam.port("o", "r", 0.5)
wire(ax, [cam.p("o"), (336, cam.p("o")[1]), (336, jet.p("usb1")[1]), jet.p("usb1")],
     color=SIG, lw=1.4, label="USB 2.0")

ha = Box(ax, 310, 404, 420, 94, "HOME ASSISTANT  ·  authority chain",
         "input_boolean.gh_kill  —  agent kill switch, default off\n"
         "input_select.gh_authority  —  Off / Manual / Auto / Agent proposes / Agent autonomous\n"
         "The gardener reads the ceiling every loop and will not exceed it. The kill switch is\n"
         "checked before any motion command leaves the Jetson.", tag="packages/greenhouse.yaml",
         kind="safe")
ha.port("i", "t", 0.32)
wire(ax, [jet.p("api"), (jet.p("api")[0], 520), (ha.p("i")[0], 520), ha.p("i")],
     color=SIG, lw=1.6, label="ESPHome native API + HA websocket", lpos=0.5)

# =================================================================== motion
fnc = Box(ax, 380, 196, 320, 180, "MOTION CONTROLLER",
          "Elecrow 4-axis FluidNC\nESP32 + 4 x TMC2209, 24 V\n192.168.10.21\n"
          "X and Z only; 2 drivers spare\nG-code over wifi or USB", tag="G067", kind="node")
fnc.port("eth", "t", 0.18)
fnc.port("x", "r", 0.74); fnc.port("z", "r", 0.48); fnc.port("lim", "r", 0.22)
fnc.port("pwr", "l", 0.5)
wire(ax, [fnc.p("eth"), (fnc.p("eth")[0], 390), (292, 390), (292, 812)],
     color=NET, lw=1.6)
wire(ax, [fnc.p("pwr"), (300, fnc.p("pwr")[1])], color=SAFE, lw=1.8)
ax.text(294, fnc.p("pwr")[1], "24 V MOTION\nvia G9SE 13/14\n(sheet E-01)", ha="right",
        va="center", fontsize=7.2, color=SAFE)

xax = Box(ax, 760, 300, 300, 76, "X AXIS  ·  long travel",
          "OpenBuilds C-Beam 1500 mm (05-LP) + NEMA 17 belt and pinion drive\n"
          "NEMA 23 2.8 A motor, XLarge C-Beam gantry set with Xtreme solid V wheels",
          tag="G060 / G062 / G063 / G066", kind="act")
xax.port("i", "l", 0.5)
dogleg(ax, fnc.p("x"), xax.p("i"), x=730, color=V24, lw=1.5)

zax = Box(ax, 760, 212, 300, 76, "Z AXIS  ·  mast",
          "C-Beam 1500 mm mast, Tr8x8(p2) lead screw, anti-backlash nut block\n"
          "23HS22-4004D-B280 with a 24 V fail-safe brake: no power, mast held",
          tag="G061 / G064 / G065", kind="act")
zax.port("i", "l", 0.5)
dogleg(ax, fnc.p("z"), zax.p("i"), x=730, color=V24, lw=1.5)

lim = Box(ax, 760, 140, 300, 60, "LIMIT SWITCHES  x4",
          "OpenBuilds Xtension 2805-Kit: X min, X max, Z min, Z max\n"
          "homed on every power-up before the arm is allowed to move",
          tag="G068", kind="sense")
lim.port("i", "l", 0.5)
dogleg(ax, fnc.p("lim"), lim.p("i"), x=730, color=SIG, lw=1.4)

# ====================================================================== arm
arm = Box(ax, 790, 540, 300, 226, "myCobot 280 Pi",
          "Elephant Robotics, 6 DOF\n280 mm working radius, 250 g payload\n"
          "192.168.10.22 on VLAN 10\nits own OEM power brick\n\n"
          "Bolted to the SendCutSend arm plate\n(G071, 6061-T6 0.250 in) on the\n"
          "XLarge gantry carriage",
          tag="G082", kind="node", title_fs=10.0)
arm.port("eth", "t", 0.26)
arm.port("grip", "b", 0.30)
arm.port("cam", "b", 0.72)
arm.port("i", "l", 0.22)
wire(ax, [arm.p("eth"), (arm.p("eth")[0], 812)], color=NET, lw=1.8)
wire(ax, [jet.p("arm"), arm.p("i")], color=NET, lw=1.5, label="TCP, pymycobot")

grip = Box(ax, 744, 420, 200, 84, "ADAPTIVE GRIPPER",
           "Elephant Robotics\nmyCobot Adaptive Gripper\nmounts to the 280 flange\nwith no adapter plate",
           tag="G083", kind="act")
grip.port("i", "t", 0.5)
wire(ax, [arm.p("grip"), (arm.p("grip")[0], 522), (grip.p("i")[0], 522),
          grip.p("i")], color=SIG, lw=1.4)

d405 = Box(ax, 966, 420, 212, 84, "WRIST DEPTH CAMERA",
           "Intel RealSense D405\nshort range stereo, 7 to 50 cm\nUSB-C to the Jetson\n"
           "hand-eye calibrated once", tag="G056", kind="sense")
d405.port("i", "t", 0.5)
d405.port("o", "r", 0.4)
wire(ax, [arm.p("cam"), (arm.p("cam")[0], 522), (d405.p("i")[0], 522),
          d405.p("i")], color=SIG, lw=1.4)
wire(ax, [jet.p("usbc"), (716, jet.p("usbc")[1]), (716, 528), (1186, 528),
          (1186, d405.p("o")[1]), d405.p("o")], color=SIG, lw=1.5,
     label="high-flex USB-C 3.1 Gen1, 2 m (G057)", lpos=0.42)

# ============================================================== cable chain
ch = Box(ax, 300, 50, 760, 76, "CABLE CHAIN  ·  Igus E14.1.028.0, two 1.5 m runs",
         "X run and Z run. Carried: stepper phases (X, Z), the Z brake pair, 12 V for the wrist light, "
         "Cat6A to the arm,\nthe high-flex USB-C to the D405, and the arm's own DC lead.  "
         "NO MAINS IN THE CHAIN.  Keep the motor pairs and the\nCat6A on opposite sides of the "
         "chain divider, and specify continuous-flex rating on every conductor (G069 / G070).",
         tag="G069 / G070", kind="plain")

# =============================================================== notes col
legend(ax, COL, Y1 - 36, [
    (NET, "ethernet (VLAN 10)"),
    (SIG, "USB / logic / G-code"),
    (V24, "24 V motor drive"),
    (SAFE, "safety-switched 24 V"),
])

note(ax, COL, Y1 - 112,
     "WHERE THE ARM ACTUALLY SITS\n\n"
     "The gantry runs along the LONG face of the\n"
     "cabinet, 1397 mm wide, not across the 559 mm\n"
     "depth. Trays are 203 mm deep in a 559 mm\n"
     "cabinet, which leaves a 254 mm corridor for the\n"
     "carriage, the plate and the arm base.\n\n"
     "Joint 1 must sit at least 177 mm behind the front\n"
     "face for the gripper to reach the back edge of a\n"
     "tray. The arm is 437 mm tall stowed, which is\n"
     "more than the 431 and 392 mm of headroom on\n"
     "the upper two tiers, so it travels FOLDED and\n"
     "only unfolds once the mast has it at the right\n"
     "tier. That constraint belongs in the motion\n"
     "planner, not in a comment.", fs=7.5)

note(ax, COL, 480,
     "AUTHORITY, IN FIVE STEPS\n\n"
     "Off              nothing moves\n"
     "Manual           you drive it from the dashboard\n"
     "Auto             rule loop only: schedules,\n"
     "                 thermostat, moisture thresholds\n"
     "Agent proposes   the gardener suggests, you\n"
     "                 approve each action\n"
     "Agent autonomous the gardener acts inside the\n"
     "                 interlocks\n\n"
     "The ceiling is an input_select in Home Assistant\n"
     "and is read every loop. gh_kill is a separate\n"
     "input_boolean checked immediately before any\n"
     "motion command, so flipping it stops the arm\n"
     "without having to agree on a state machine.", fs=7.5)

note(ax, COL, 232,
     "WHAT STILL HAS TO BE PROVEN\n\n"
     "• Hand-eye calibration between the D405 and\n"
     "  the gantry frame (handeye_calibrate.py).\n"
     "• Whether 250 g payload is enough once the\n"
     "  gripper and a wet 1 gal pot are included. It\n"
     "  is not, for lifting pots; it is, for leaf work\n"
     "  and harvesting. Plan the tasks accordingly.\n"
     "• The two spare TMC2209 channels are an\n"
     "  obvious home for a future tray shuttle.", fs=7.5)

out = "wiring_E04_motion.png"
os.makedirs(".", exist_ok=True)
fig.savefig(out, dpi=150, facecolor="white")
print("saved", out)
