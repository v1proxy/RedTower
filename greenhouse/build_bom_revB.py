from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment

wb = Workbook()
F = "Arial"
H = Font(name=F, bold=True, color="FFFFFF")
HF = PatternFill("solid", fgColor="2F4F4F")
INP = Font(name=F, color="0000FF")
BODY = Font(name=F)
BOLD = Font(name=F, bold=True)
LINK = Font(name=F, color="008000")
URLF = Font(name=F, color="0563C1", underline="single")
YEL = PatternFill("solid", fgColor="FFFF00")
ALT = PatternFill("solid", fgColor="FFF2CC")
USD = '$#,##0.00;($#,##0.00);"-"'
USD0 = '$#,##0;($#,##0);"-"'


def header(ws, row, cols, widths):
    for i, (c, w) in enumerate(zip(cols, widths), 1):
        cell = ws.cell(row=row, column=i, value=c)
        cell.font, cell.fill = H, HF
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


# ---------------- Cut list ----------------
cl = wb.create_sheet("Cut list")
cl["A1"] = "Profile cut list (mm). Frame outside 1397 W x 457 D x 1829 H (55 x 18 x 72 in). Order 8020 cut to length: no sawing."
cl["A1"].font = BOLD
header(cl, 3, ["Profile", "Member", "Length (mm)", "Length (in)", "Qty", "Total (m)", "Notes"], [10, 42, 12, 12, 7, 11, 52])
cuts = [
    ("40-4040", "Uprights", 1829, 4, "Full height corners"),
    ("40-4040", "Front/back longitudinals (levels 0, 12, 38, 55, 72 in)", 1317, 10, "1397 - 2 x 40"),
    ("40-4040", "Shelf front rails, Tiers A/B/C", 1317, 3, "203 mm plant zone edge"),
    ("40-4040", "Side depth members (5 levels x 2 sides)", 377, 10, "457 - 2 x 40"),
    ("40-4040", "Gantry rail mounts / roof guide standoffs", 240, 4, "Carry the C-Beam rails in the lane"),
    ("40-2020", "Door frame verticals, lower doors", 660, 4, "8020 20-2020, overlay doors Tier A"),
    ("40-2020", "Door frame verticals, upper doors", 864, 4, "Overlay doors Tiers B+C"),
    ("40-2020", "Door frame horizontals", 658, 8, "698 door width - 2 x 20"),
    ("C-Beam", "Gantry X rail", 1250, 1, "OpenBuilds C-Beam, cut from 1500 stock"),
    ("C-Beam", "Z mast", 1380, 1, "OpenBuilds C-Beam, cut from 1500 stock"),
]
r0 = 4
for i, (p, m, L, q, n) in enumerate(cuts):
    r = r0 + i
    cl.cell(row=r, column=1, value=p).font = BODY
    cl.cell(row=r, column=2, value=m).font = BODY
    cl.cell(row=r, column=3, value=L).font = INP
    c = cl.cell(row=r, column=4, value=f"=C{r}/25.4")
    c.font, c.number_format = BODY, "0.00"
    cl.cell(row=r, column=5, value=q).font = INP
    c = cl.cell(row=r, column=6, value=f"=C{r}*E{r}/1000")
    c.font, c.number_format = BODY, "0.00"
    cl.cell(row=r, column=7, value=n).font = BODY
rl = r0 + len(cuts) - 1
tr = rl + 2
cl.cell(row=tr, column=2, value="Waste / kerf allowance").font = BODY
c = cl.cell(row=tr, column=6, value=0.05)
c.font, c.number_format, c.fill = INP, "0%", YEL
order_rows = {}
for j, prof in enumerate(["40-4040", "40-2020", "C-Beam"]):
    r = tr + 1 + j
    cl.cell(row=r, column=2, value=f"Order length {prof}").font = BOLD
    c = cl.cell(row=r, column=6, value=f'=ROUNDUP(SUMIF($A${r0}:$A${rl},"{prof}",$F${r0}:$F${rl})*(1+$F${tr}),1)')
    c.font, c.number_format = BOLD, "0.0"
    cl.cell(row=r, column=7, value="metres").font = BODY
    order_rows[prof] = r
c = cl.cell(row=tr + 5, column=2, value="8020 prices by the inch, so total inches of 40-4040:")
c.font = BODY
c = cl.cell(row=tr + 5, column=6, value=f"=ROUNDUP(F{order_rows['40-4040']}*1000/25.4,0)")
c.font, c.number_format = BOLD, "0"
IN4040 = f"'Cut list'!F{tr+5}"
ORDER = {k: f"'Cut list'!F{v}" for k, v in order_rows.items()}
cl.cell(row=tr + 7, column=2, value="8020 cut-to-length holds +/-0.5 mm and will tap the ends. C-Beam ships in 250 mm steps up to 1500 and cuts on a chop saw.").font = BODY

# ---------------- BOM ----------------
bom = wb.create_sheet("BOM", 0)
bom["A1"] = "Herb Tower BOM Rev B, commercial off-the-shelf parts. Blue = editable input. Amber rows are alternates, set their Qty to use them."
bom["A1"].font = BOLD
cols = ["ID", "Subsystem", "Item", "Manufacturer", "Part number / SKU", "Vendor", "Link", "Qty", "Unit",
        "Unit price", "Ext price", "Price basis", "Notes"]
header(bom, 3, cols, [7, 16, 30, 20, 26, 16, 12, 7, 6, 12, 12, 20, 46])

S, L, IR, BS, CC, MO, PW, AR = ("Structure", "Lighting & air", "Irrigation", "Biosensing",
                                "Control & compute", "Motion", "Power & safety", "Robot arm")
V = "vendor page, Sep 2026"
T = "typical retail, verify"
A = "alternate"

items = [
    # ---- Structure ----
    (S, "Profile 40-4040, cut to length", "80/20 Inc", "40-4040", "8020.net", "https://8020.net/40-4040.html",
     IN4040, "in", 1.12, V, "Qty links to Cut list inches. 40 series, 8 mm slot, clear anodize"),
    (S, "Profile 20-2020 for door frames", "80/20 Inc", "20-2020", "8020.net", "https://8020.net/20-2020.html",
     f"=ROUNDUP({ORDER['40-2020']}*1000/25.4,0)", "in", 0.55, T, "Lighter 20 series is enough for doors"),
    (S, "ALTERNATE: generic EU 4040, 1 m sticks", "ZYLtech", "4040 T-slot 1 m", "zyltech.com", "https://www.zyltech.com/",
     0, "m", 25.0, A, "Saves roughly $700 but you cut all 27 members yourself"),
    (S, "Corner brackets, 40 series", "80/20 Inc", "40 series corner bracket + hardware", "8020.net", "https://8020.net/",
     64, "pc", 4.5, T, "Confirm exact PN at order: 2-hole inside corner, black"),
    (S, "Drop-in T-nuts M8 + BHCS", "80/20 Inc", "40 series M8 drop-in T-nut kit", "8020.net", "https://8020.net/",
     250, "pc", 0.6, T, "Panels, trays, rail mounts, sensor brackets"),
    (S, "End-tap service, 40-4040", "80/20 Inc", "Machining: end tap M8", "8020.net", "https://8020.net/",
     54, "pc", 1.6, T, "One tap per butt joint end, avoids most brackets"),
    (S, "Leveling feet M8", "80/20 Inc", "40 series leveling foot", "8020.net", "https://8020.net/",
     4, "pc", 12.0, T, ""),
    (S, "Polycarbonate sheet 4 mm clear", "Palram", "PALSUN 4 mm 48 x 96 in", "Piedmont Plastics / Home Depot",
     "https://www.palram.com/us/product/palsun/", 3, "sheet", 175.0, T, "Sides, top, 4 doors; 3rd sheet covers nesting waste"),
    (S, "ACM panel 3 mm white", "Falken Design", "ACM-WT-3mm-4896", "Falken Design / Amazon",
     "https://www.falkendesign.com/", 2, "sheet", 95.0, T, "White back wall, reflective face inward"),
    (S, "Panel seal gasket, slot 8", "Fath / 80/20", "Slot 8 panel retainer, 4 mm", "8020.net", "https://8020.net/",
     40, "m", 1.4, T, ""),
    (S, "Door hinges, 40 series", "80/20 Inc", "40 series hinge", "8020.net", "https://8020.net/",
     8, "pc", 14.0, T, ""),
    (S, "Magnetic catches + handles", "80/20 Inc", "40 series magnetic catch, pull handle", "8020.net", "https://8020.net/",
     4, "set", 18.0, T, ""),
    (S, "Drip trays, laser cut and bent", "SendCutSend", "5052 aluminum 1.5 mm, 1317 x 203 x 25", "sendcutsend.com",
     "https://sendcutsend.com/", 3, "pc", 62.0, T, "Upload the DXF from the drawing set; one per tier"),
    (S, "Base drip pan", "SendCutSend", "5052 aluminum 1.5 mm, 1317 x 377 x 25", "sendcutsend.com",
     "https://sendcutsend.com/", 1, "pc", 85.0, T, "Under the reservoir and electrical bay"),
    (S, "Anti-tip wall brackets", "Simpson Strong-Tie", "A34 / A21 angle + lag screws", "Home Depot",
     "https://www.homedepot.com/", 1, "kit", 24.0, T, "Two studs. Mandatory with a moving gantry"),

    # ---- Lighting & air ----
    (L, "LED bar, LM301H class", "Kingbrite", "560 mm LM301H + 660 nm bar, 36 V", "Kingbrite (AliExpress)",
     "https://kingbrite.aliexpress.com/", 6, "pc", 28.0, T, "2 per tier in series, ~72 V string"),
    (L, "ALTERNATE: quantum board", "Horticulture Lighting Group", "QB120 V2", "hlgshop.com",
     "https://horticulturelightinggroup.com/", 0, "pc", 59.0, A, "Use if you prefer a US supplier and 3500K white"),
    (L, "LED driver Tier A", "Mean Well", "HLG-80H-C1050B", "TRC Electronics",
     "https://www.trcelectronics.com/", 1, "pc", 55.0, T, "Constant current 1050 mA, 3-in-1 dimming"),
    (L, "LED driver Tiers B and C", "Mean Well", "HLG-60H-C700B", "Jameco / DigiKey",
     "https://www.digikey.com/en/products/detail/mean-well-usa-inc/HLG-60H-C700B/7704169",
     2, "pc", 48.0, V, "700 mA, dimmed to about 80 %"),
    (L, "LED driver AC relay module", "SunFounder", "3.3 V 1-channel relay, 10 A", "Amazon",
     "https://www.amazon.com/", 3, "pc", 6.0, T, "Cuts each driver at night; B-type dims to minimum, not off"),
    (L, "Dim interface parts", "onsemi", "2N2222A + 1 k resistor", "DigiKey", "https://www.digikey.com/",
     3, "set", 2.0, T, "Open collector across DIM+/DIM-"),
    (L, "Exhaust fan 120 mm", "Noctua", "NF-F12 PWM", "Amazon / Noctua", "https://noctua.at/en/nf-f12-pwm",
     2, "pc", 27.0, T, "12 V PWM, roof extract"),
    (L, "Circulation fan 80 mm", "Noctua", "NF-A8 PWM", "Amazon / Noctua", "https://noctua.at/en/nf-a8-pwm",
     3, "pc", 20.0, T, "One per tier, across the canopy"),
    (L, "Fan grills and screws", "Noctua", "NA-FG1-12 / NA-FG1-8", "Amazon", "https://noctua.at/", 2, "set", 12.0, T, ""),
    (L, "Intake dust filter 120 mm", "DEMCiflex", "Magnetic dust filter 120 mm", "demciflex.com",
     "https://demciflex.com/", 1, "pc", 17.0, T, "Low on the Tier A side panel"),

    # ---- Irrigation ----
    (IR, "Reservoir, low profile", "Class A Customs", "8 gal RV fresh water tank, 30 x 10 x 7 in", "classacustoms.com",
     "https://www.classacustoms.com/", 1, "pc", 79.0, T, "30 L, fits the 225 mm utility bay, has moulded bungs"),
    (IR, "Pump 24 V", "SEAFLO", "21 Series 24 V, 1.2 GPM, 35 psi", "seaflousa.com",
     "https://www.seaflousa.com/product/21-series-diaphragm-pumps/", 1, "pc", 49.0, T, "Internal pressure switch"),
    (IR, "Pressure regulator", "DIG", "1/4 in 25 psi regulator", "Drip Depot", "https://www.dripdepot.com/",
     1, "pc", 9.0, T, "Protects the PC emitters"),
    (IR, "Inline filter 150 mesh", "DIG", "1/4 in inline filter", "Drip Depot", "https://www.dripdepot.com/",
     1, "pc", 8.0, T, ""),
    (IR, "Check valve 1/4 in", "DIG", "1/4 in check valve", "Drip Depot", "https://www.dripdepot.com/",
     1, "pc", 7.0, T, "Keeps the lines primed"),
    (IR, "Zone solenoid valve 24 V DC", "U.S. Solid", "1/4 in NC brass, 24 V DC, Viton", "ussolid.com",
     "https://ussolid.com/", 3, "pc", 22.0, T, "Flyback diode on each coil"),
    (IR, "PC emitters 0.5 GPH", "Netafim", "Woodpecker Jr. PC 2 L/h", "Drip Depot", "https://www.dripdepot.com/",
     40, "pc", 0.6, T, "34 in use: 1 per herb, 2 per pepper"),
    (IR, "Tubing, tees, stakes", "DIG", "1/4 in poly tubing 100 ft + fittings kit", "Drip Depot",
     "https://www.dripdepot.com/", 1, "kit", 34.0, T, ""),
    (IR, "MOSFET driver board", "HiLetgo", "4-channel IRF540 MOSFET module", "Amazon", "https://www.amazon.com/",
     1, "pc", 12.0, T, "Pump + 3 valves, logic level"),

    # ---- Biosensing ----
    (BS, "Soil moisture probe", "DFRobot", "SEN0193 (Gravity capacitive v2)", "DFRobot / Adafruit",
     "https://www.dfrobot.com/product-1385.html", 30, "pc", 7.9, T, "27 plants + 3 spares. Coat the electronics"),
    (BS, "ADC, 4-channel 16-bit", "Adafruit", "1085 (ADS1115 breakout)", "Adafruit",
     "https://www.adafruit.com/product/1085", 10, "pc", 14.95, T, "3 per tier + spare; addresses 0x48-0x4A"),
    (BS, "Air temperature / humidity", "Adafruit", "5665 (Sensirion SHT45)", "Adafruit",
     "https://www.adafruit.com/product/5665", 3, "pc", 12.5, V, "One per tier"),
    (BS, "CO2 sensor", "Adafruit", "5190 (Sensirion SCD-41)", "Adafruit",
     "https://www.adafruit.com/product/5190", 1, "pc", 49.95, T, "Tier C node"),
    (BS, "Spectral light sensor", "Adafruit", "4698 (AS7341)", "Adafruit",
     "https://www.adafruit.com/product/4698", 3, "pc", 15.95, T, "Detects a failed bar or driver"),
    (BS, "Canopy IR thermometer", "Adafruit", "1748 (MLX90614, 3 V)", "Adafruit",
     "https://www.adafruit.com/product/1748", 3, "pc", 29.95, T, "Leaf-to-air delta, earliest stress signal"),
    (BS, "Reservoir level, time of flight", "Adafruit", "3317 (VL53L0X)", "Adafruit",
     "https://www.adafruit.com/product/3317", 1, "pc", 14.95, T, "Aim at a float puck in a clear tube"),
    (BS, "Water temperature probe", "Adafruit", "381 (DS18B20 waterproof)", "Adafruit",
     "https://www.adafruit.com/product/381", 1, "pc", 9.95, T, ""),
    (BS, "Low-water float switch", "Madison", "M8000 vertical float, NO", "Grainger / Amazon",
     "https://www.amazon.com/", 1, "pc", 18.0, T, "Hard pump cutoff, independent of the ToF"),
    (BS, "Leak probe modules", "HiLetgo", "Water leak / rain sensor module (digital out)", "Amazon",
     "https://www.amazon.com/", 4, "pc", 5.0, T, "Base pan + 3 tier trays"),
    (BS, "Door reed switches", "Honeywell", "7939WG-WH surface contact", "Amazon / SecurityCameraWarehouse",
     "https://www.amazon.com/", 4, "pc", 6.0, T, "Series chain: ESP input and safety relay"),
    (BS, "I/O expander", "Adafruit", "5346 (MCP23017)", "Adafruit",
     "https://www.adafruit.com/product/5346", 1, "pc", 9.95, T, "8 utility inputs, keeps them off strapping pins"),
    (BS, "STEMMA QT cable set", "Adafruit", "4210 / 4399 assorted lengths", "Adafruit",
     "https://www.adafruit.com/product/4210", 12, "pc", 1.5, T, "I2C chaining inside each tier"),
    (BS, "Conformal coating + heat shrink", "MG Chemicals", "422B acrylic conformal coating", "Amazon",
     "https://www.amazon.com/", 1, "kit", 22.0, T, "Probe electronics live in 60-70 % RH"),

    # ---- Control & compute ----
    (CC, "PoE controller node", "Olimex", "ESP32-POE-ISO", "Mouser / DigiKey",
     "https://www.digikey.com/en/products/detail/olimex-ltd/ESP32-POE-ISO/10258716",
     5, "pc", 33.0, T, "3 tiers + utility + 1 spare. Isolated PoE, wired Ethernet"),
    (CC, "PoE switch, VLAN capable", "TP-Link", "TL-SG108PE", "Amazon / Micro Center",
     "https://www.tp-link.com/us/business-networking/poe-switch/tl-sg108pe/",
     1, "pc", 74.0, T, "8 ports, 4 PoE+, 802.1Q tagging so it can carry VLAN 10 itself"),
    (CC, "Compute node", "NVIDIA", "Jetson Orin Nano Super Developer Kit", "Seeed / Arrow / NVIDIA",
     "https://marketplace.nvidia.com/en-us/enterprise/robotics-edge/jetson-orin-nano-super-developer-kit/",
     1, "pc", 249.0, T, "Vision, ROS 2, robot supervisor"),
    (CC, "NVMe SSD", "Crucial", "P3 500 GB M.2 2280", "Amazon / Newegg", "https://www.crucial.com/",
     1, "pc", 45.0, T, ""),
    (CC, "Tier camera", "Arducam", "B020201 (1080p IMX291, 160 deg, metal case)", "Arducam / Amazon",
     "https://www.arducam.com/b020201-arducam-1080p-low-light-wdr-usb-camera-module-with-metal-case-2mp-1-2-8-cmos-imx291-160-degree-ultra-wide-angle-mini-uvc-webcam-board-with-microphones.html",
     3, "pc", 45.0, T, "UVC, works with OpenCV out of the box. Undistort in software"),
    (CC, "Wrist camera", "Arducam", "B0196 mini UVC 1080p", "Arducam / Amazon", "https://www.arducam.com/",
     1, "pc", 32.0, T, "Plugs into the arm's own Raspberry Pi"),
    (CC, "Patch cables Cat6", "Monoprice", "SlimRun Cat6, assorted", "Monoprice", "https://www.monoprice.com/",
     8, "pc", 4.0, T, "One high-flex run for the cable chain"),
    (CC, "Electronics enclosure", "Polycase", "YQ-060806 IP65 300 x 200 x 120", "polycase.com",
     "https://www.polycase.com/", 1, "pc", 48.0, T, "DIN rail inside, in the utility bay"),

    # ---- Motion ----
    (MO, "C-Beam linear rail, X axis", "OpenBuilds", "C-Beam Linear Rail 1500 mm (cut to 1250)", "OpenBuilds",
     "https://us.openbuilds.com/c-beam-linear-rail/", 1, "pc", 72.0, T, "40 x 80 V-slot profile: V wheels need V-slot, plain 4080 T-slot will not work"),
    (MO, "C-Beam linear rail, Z mast", "OpenBuilds", "C-Beam Linear Rail 1500 mm (cut to 1380)", "OpenBuilds",
     "https://us.openbuilds.com/c-beam-linear-rail/", 1, "pc", 72.0, T, ""),
    (MO, "Gantry set, XLarge", "OpenBuilds", "C-Beam XLarge Gantry Set (Xtreme Solid V wheels)", "OpenBuilds",
     "https://us.openbuilds.com/", 2, "set", 95.0, T, "One rides X, one carries the arm on Z"),
    (MO, "Belt and pinion drive, X", "OpenBuilds", "Belt & Pinion Drive Set + 3 m GT3 belt", "OpenBuilds",
     "https://us.openbuilds.com/", 1, "set", 78.0, T, "Belt on X for speed; screw on Z for holding"),
    (MO, "Lead screw kit, Z", "OpenBuilds", "8 mm Acme screw 1400 mm + anti-backlash nut block + bearing + coupler",
     "OpenBuilds", "https://us.openbuilds.com/", 1, "set", 88.0, T, "2 mm pitch keeps it close to self-locking"),
    (MO, "Stepper, Z, with brake", "StepperOnline", "23HS22-4004D-B280", "omc-stepperonline.com",
     "https://www.omc-stepperonline.com/nema-23-stepper-motor-1-2nm-169-93oz-in-with-24v-4-5w-electromagnetic-brake-23hs22-4004d-b280",
     1, "pc", 36.08, V, "1.2 Nm, 24 V 4.5 W brake holds 2.8 Nm with power off"),
    (MO, "Stepper, X", "StepperOnline", "23HS22-2804S", "omc-stepperonline.com",
     "https://www.omc-stepperonline.com/", 1, "pc", 25.0, T, "1.2 Nm, 2.8 A, fits TMC2226 current limit"),
    (MO, "Motion controller", "V1 Engineering", "Jackpot3 CNC Controller (FluidNC, 6x TMC2226)", "v1e.com",
     "https://www.v1e.com/products/jackpot3-cnc-controller", 1, "pc", 75.99, V, "USB to the Jetson, 7 inputs for limits and the door chain"),
    (MO, "Limit switch kit", "OpenBuilds", "Xtension Limit Switch Kit", "OpenBuilds", "https://us.openbuilds.com/",
     4, "pc", 9.0, T, "Home and overtravel on both axes"),
    (MO, "Cable chain", "Igus", "E14 series, 15 x 20, 1.5 m", "igus.com / Amazon", "https://www.igus.com/",
     2, "pc", 26.0, T, "X and Z"),
    (MO, "High flex cable set", "Igus", "chainflex motor + Ethernet + 12 V", "igus.com / Amazon",
     "https://www.igus.com/", 1, "set", 48.0, T, "Everything that moves with the carriage"),
    (MO, "Arm mounting plate", "SendCutSend", "6 mm 6061, M4 pattern for the myCobot base", "sendcutsend.com",
     "https://sendcutsend.com/", 1, "pc", 42.0, T, "Cut after measuring the delivered arm base"),

    # ---- Power & safety ----
    (PW, "Inline GFCI cord", "Tower Manufacturing", "30438006 15 A inline GFCI", "Amazon / Grainger",
     "https://www.amazon.com/", 1, "pc", 42.0, T, "Mandatory: water inside the cabinet"),
    (PW, "Fused IEC inlet with switch", "Schurter", "KD14 series fused inlet module", "DigiKey",
     "https://www.digikey.com/", 1, "pc", 14.0, T, "8 A fuse"),
    (PW, "24 V power supply", "Mean Well", "LRS-350-24", "TRC Electronics / DigiKey",
     "https://www.trcelectronics.com/mean-well-lrs-350-24", 1, "pc", 45.0, T, "14.6 A, about 30 % loaded"),
    (PW, "24 V to 12 V converter", "Mean Well", "DDR-15G-12", "DigiKey", "https://www.digikey.com/",
     1, "pc", 26.0, T, "DIN mount, feeds all five Noctua fans"),
    (PW, "DIN rail and terminals", "Wago", "221 series + DIN mounting carriers", "Amazon / DigiKey",
     "https://www.wago.com/", 1, "set", 38.0, T, ""),
    (PW, "Fuse block, 6 way", "Blue Sea Systems", "5045 ST blade fuse block", "Amazon / West Marine",
     "https://www.bluesea.com/products/5045/", 1, "pc", 32.0, T, "One fuse per 24 V branch"),
    (PW, "E-stop, 22 mm", "Eaton", "M22-PV/KC02/IY (mushroom, 2 NC)", "DigiKey / Automation Direct",
     "https://www.digikey.com/", 1, "pc", 38.0, T, "Front of the utility bay"),
    (PW, "Safety relay, dual channel", "Omron", "G9SE-201 24 VDC", "DigiKey / Automation Direct",
     "https://www.digikey.com/", 1, "pc", 152.0, T, "Doors + E-stop cut gantry and arm power"),
    (PW, "Energy meter", "Peacefair", "PZEM-004T v3.0 with 100 A CT", "Amazon", "https://www.amazon.com/",
     1, "pc", 16.0, T, "UART to the utility node, no Wi-Fi needed"),
    (PW, "Wire, ferrules, glands, labels", "Various", "18-14 AWG, PG9 glands, ferrule kit", "Amazon",
     "https://www.amazon.com/", 1, "set", 46.0, T, ""),

    # ---- Robot arm ----
    (AR, "Robot arm", "Elephant Robotics", "myCobot 280 Pi", "Elephant Robotics Americas",
     "https://americas.shop.elephantrobotics.com/", 1, "pc", 799.0, T,
     "6 axis, 280 mm reach, 250 g payload, 860 g, 12 V 5 A, ROS 2 and Python"),
    (AR, "Gripper", "Elephant Robotics", "myCobot Adaptive Gripper", "Elephant Robotics Americas",
     "https://americas.shop.elephantrobotics.com/", 1, "pc", 150.0, T, "Confirm price and the flange it needs"),
    (AR, "Second arm (optional)", "Elephant Robotics", "myCobot 280 Pi", "Elephant Robotics Americas",
     "https://americas.shop.elephantrobotics.com/", 0, "pc", 799.0, A, "Bimanual on the same Z carriage: set Qty to 1"),
]

first = 4
subsystems = []
for i, (sub, item, mfr, mpn, vendor, url, qty, unit, cost, basis, note) in enumerate(items):
    r = first + i
    if sub not in subsystems:
        subsystems.append(sub)
    bom.cell(row=r, column=1, value=f"G{i+1:03d}").font = BODY
    bom.cell(row=r, column=2, value=sub).font = BODY
    bom.cell(row=r, column=3, value=item).font = BODY
    bom.cell(row=r, column=4, value=mfr).font = BODY
    bom.cell(row=r, column=5, value=mpn).font = BODY
    bom.cell(row=r, column=6, value=vendor).font = BODY
    c = bom.cell(row=r, column=7, value="link")
    c.hyperlink, c.font = url, URLF
    q = bom.cell(row=r, column=8, value=(f"={qty}" if isinstance(qty, str) else qty))
    q.font = LINK if isinstance(qty, str) else INP
    bom.cell(row=r, column=9, value=unit).font = BODY
    c = bom.cell(row=r, column=10, value=cost)
    c.font, c.number_format = INP, USD
    e = bom.cell(row=r, column=11, value=f"=H{r}*J{r}")
    e.font, e.number_format = BODY, USD
    bom.cell(row=r, column=12, value=basis).font = BODY
    bom.cell(row=r, column=13, value=note).font = BODY
    if basis == A:
        for col in range(1, 14):
            bom.cell(row=r, column=col).fill = ALT

last = first + len(items) - 1
tot = last + 2
bom.cell(row=tot, column=10, value="Total").font = BOLD
t = bom.cell(row=tot, column=11, value=f"=SUM(K{first}:K{last})")
t.font, t.number_format = BOLD, USD0
bom.cell(row=tot + 1, column=10, value="Contingency").font = BODY
cg = bom.cell(row=tot + 1, column=11, value=0.10)
cg.font, cg.number_format, cg.fill = INP, "0%", YEL
bom.cell(row=tot + 2, column=10, value="Budget").font = BOLD
b = bom.cell(row=tot + 2, column=11, value=f"=K{tot}*(1+K{tot+1})")
b.font, b.number_format = BOLD, USD0
bom.cell(row=tot + 4, column=1,
         value='Price basis: "vendor page" = read off that vendor in Sep 2026. "typical retail, verify" = current market level, confirm at order. "alternate" = not in the total unless you set Qty.').font = BODY
bom.cell(row=first, column=10).comment = Comment(
    "8020 sells 40-4040 by the inch ($1.12/in list). The Cut list tab drives this quantity.", "Claude")
bom.auto_filter.ref = f"A3:M{last}"

# ---------------- Summary ----------------
sm = wb.create_sheet("Summary", 0)
sm["A1"] = "Herb Tower Rev B, cost by subsystem"
sm["A1"].font = BOLD
header(sm, 3, ["Subsystem", "Cost (USD)", "Share"], [22, 16, 10])
for j, sub in enumerate(subsystems):
    r = 4 + j
    sm.cell(row=r, column=1, value=sub).font = BODY
    c = sm.cell(row=r, column=2, value=f'=SUMIF(BOM!$B${first}:$B${last},A{r},BOM!$K${first}:$K${last})')
    c.font, c.number_format = LINK, USD0
    s = sm.cell(row=r, column=3, value=f"=IF($B${4+len(subsystems)}=0,0,B{r}/$B${4+len(subsystems)})")
    s.font, s.number_format = BODY, "0.0%"
rt = 4 + len(subsystems)
sm.cell(row=rt, column=1, value="Total").font = BOLD
c = sm.cell(row=rt, column=2, value=f"=SUM(B4:B{rt-1})")
c.font, c.number_format = BOLD, USD0
sm.cell(row=rt + 1, column=1, value="Budget incl. contingency").font = BOLD
c = sm.cell(row=rt + 1, column=2, value=f"=BOM!K{tot+2}")
c.font, c.number_format = LINK, USD0
sm.cell(row=rt + 2, column=1, value="Check against BOM total").font = BODY
sm.cell(row=rt + 2, column=2, value=f'=IF(ABS(B{rt}-BOM!K{tot})<0.01,"OK","MISMATCH")').font = BODY
sm.cell(row=rt + 4, column=1, value="Biggest lever: generic 4040 instead of 8020 cut-to-length").font = BODY
c = sm.cell(row=rt + 4, column=2, value=f"=BOM!K{first}-{29.7*25.0}")
c.font, c.number_format = BODY, USD0
sm.cell(row=rt + 4, column=3, value="saving if you cut it yourself").font = BODY

# ---------------- Power ----------------
pw = wb.create_sheet("Power")
pw["A1"] = "Electrical load budget, Rev B. Single 15 A, 120 V circuit."
pw["A1"].font = BOLD
header(pw, 3, ["Load", "Rail", "Steady W", "Peak W", "Hours/day", "Wh/day", "Notes"], [34, 10, 11, 10, 11, 11, 50])
pw["I3"], pw["J3"] = "Driver efficiency", 0.92
pw["I4"], pw["J4"] = "Electricity rate (USD/kWh)", 0.14
pw["I5"], pw["J5"] = "Mains voltage", 120
for a in ("I3", "I4", "I5"):
    pw[a].font = BODY
for a in ("J3", "J4", "J5"):
    pw[a].font, pw[a].fill = INP, YEL
pw.column_dimensions["I"].width = 26
loads = [
    ("Grow lights Tier A, at the wall", "AC", "=65/$J$3", "=65/$J$3", 16, "HLG-80H-C1050B"),
    ("Grow lights Tier B", "AC", "=40/$J$3", "=40/$J$3", 16, "HLG-60H-C700B"),
    ("Grow lights Tier C", "AC", "=40/$J$3", "=40/$J$3", 16, "HLG-60H-C700B"),
    ("Fans, 5 x Noctua via DDR-15G-12", "12 V", 6, 11, 24, "2 x NF-F12 + 3 x NF-A8, average 50 % duty"),
    ("ESP32 nodes + sensors", "PoE", 8, 10, 24, "4 x ESP32-POE-ISO"),
    ("PoE switch TL-SG108PE", "AC", 6, 9, 24, ""),
    ("Jetson Orin Nano Super", "AC", 12, 25, 24, "7 W and 15 W power modes available"),
    ("Tier cameras (3)", "USB", 4, 5, 24, "Powered from the Jetson"),
    ("Pump + one valve", "24 V", 46, 46, 0.17, "SEAFLO 21 series + U.S. Solid valve"),
    ("Gantry X + Z", "24 V", 28, 55, 1, "2 x NEMA 23 at TMC2226 current limit"),
    ("Z brake", "24 V", 4.5, 4.5, 1, "Released only while moving"),
    ("myCobot 280 Pi idle", "12 V", 5, 5, 23, "Its own Raspberry Pi"),
    ("myCobot 280 Pi moving", "12 V", 15, 60, 1, "12 V 5 A supply"),
]
for i, (n, rail, w, pk, h, note) in enumerate(loads):
    r = 4 + i
    pw.cell(row=r, column=1, value=n).font = BODY
    pw.cell(row=r, column=2, value=rail).font = BODY
    for col, v in ((3, w), (4, pk), (5, h)):
        c = pw.cell(row=r, column=col, value=v)
        c.font = BODY if isinstance(v, str) else INP
        c.number_format = "0.0" if col < 5 else "0.00"
    c = pw.cell(row=r, column=6, value=f"=C{r}*E{r}")
    c.font, c.number_format = BODY, "0"
    pw.cell(row=r, column=7, value=note).font = BODY
le = 4 + len(loads) - 1
s = le + 2
rows = [
    ("Daytime steady load (W)", f"=SUM(C4:C11)+C{le-1}", "0"),
    ("Night load, lights off (W)", f"=SUM(C7:C11)+C{le-1}", "0"),
    ("Worst-case peak (W)", f"=SUM(D4:D{le})-D{le-1}", "0"),
    ("Worst-case peak current (A)", f"=B{s+2}/$J$5", "0.00"),
    ("Utilization of the 12 A continuous limit", f"=B{s+3}/12", "0%"),
    ("Energy per day (kWh)", f"=SUM(F4:F{le})/1000", "0.00"),
    ("Energy per month (kWh)", f"=B{s+5}*30", "0"),
    ("Cost per month (USD)", f"=B{s+6}*$J$4", USD),
    ("Lighting share of energy", f"=SUM(F4:F6)/SUM(F4:F{le})", "0%"),
]
for k, (lab, f, fmt) in enumerate(rows):
    pw.cell(row=s + k, column=1, value=lab).font = BOLD
    c = pw.cell(row=s + k, column=2, value=f)
    c.font, c.number_format = BOLD, fmt
r24 = s + len(rows) + 1
pw.cell(row=r24, column=1, value="24 V rail peak (W) vs LRS-350-24 rating").font = BODY
c = pw.cell(row=r24, column=6, value="=D12+D13+D14")
c.font, c.number_format = BODY, "0"
c = pw.cell(row=r24, column=7, value=f"=F{r24}/350")
c.font, c.number_format = BODY, "0%"

wb.save("/home/claude/greenhouse_BOM_revB.xlsx")
print("saved. BOM rows", first, last, "total row", tot)
