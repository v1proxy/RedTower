#!/usr/bin/env python3
"""Maag - HERB SNIP bill of materials, Rev A.

Scope: the cut-and-hold tool on the myCobot 280's flange, through to commissioning (Herb Snip
booklet Rev A). Where it puts what it cuts, the dead-leaf tray and the feeder, is Harvest Rev B's. It replaces the adaptive gripper, line R02
of the gantry BOM, which is no longer bought. The arm, the D405 and the 12 V rail are in the
gantry and greenhouse BOMs already.

STATUS column, as in the gantry BOM:
  Verified   price read off the live listing (2026-10-21)
  Estimate   product confirmed live, exact price behind a selector or not readable from here
  To source  commodity part, pick any that meets the spec in NOTES
  Printed    printed from greenhouse/snip/print/ in white PETG at $20 a kilogram, the pads in TPU 95A
             at $35 a kilogram
"""
import json
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

REV = "Herb Snip Rev A"
DATE = "2026-10-21"
HERE = os.path.dirname(os.path.abspath(__file__))
PETG_PER_G = 0.020
TPU_PER_G = 0.035

MASS = {"body": 49.2, "ring": 15.7, "mj_a": 2.0, "mj_b": 3.2, "link": 0.4, "crank": 0.4, "anvil": 0.3, "pad": 0.7}
_ck = os.path.join(HERE, "build", "checks.json")
if os.path.exists(_ck):                                    # the model's own masses, when built here
    MASS.update({k: v["g"] for k, v in json.load(open(_ck))["mass"]["printed"].items()})


def printed(ref, item, key, note, qty=1, tpu=False):
    g = MASS[key]
    what = f"{g:.1f} g TPU 95A, solid" if tpu else f"{g:.1f} g white PETG, like the arm"
    return (ref, "Printed", item, f"print/{PRINT[key]}.stl", "your printer", "", qty, "pc",
            round(g * 1.1 * (TPU_PER_G if tpu else PETG_PER_G), 2), "Printed",
            f"{what} (plus about 10 % for purge and skirt). {note}")


PRINT = {"body": "snip_body", "ring": "snip_camera_ring", "mj_a": "snip_jaw_A", "mj_b": "snip_jaw_B", "link": "snip_link",
         "crank": "snip_crank", "anvil": "snip_anvil", "pad": "snip_pad_TPU_x2"}

# ref, group, item, mfr/part, supplier, link, qty, unit, unit_price, status, note
ROWS = [
    printed("P01", "Body", "body", "One housing: the collar above the band, the servo's pocket, the regulator's "
            "bay, the fixed jaw. Stands on its flat base: no supports. 4 walls, 25 % gyroid, bridging on for the "
            "servo pocket's roof."),
    printed("P10", "Camera ring", "ring", "The collar's foot below the band and the D405's chin, one piece, "
            "between the flange and the body on the same four LEGO pins. Prints lying on its flat side (the "
            "collar's, the chin's and the plate's, one plane): no supports, a 5 mm brim, since it stands 42 tall. 4 walls, 25 % gyroid."),
    printed("P02", "Jaw A", "mj_a", "Camera side half of the moving jaw: the blade's pocket and the clamp screw's "
            "countersink. Outer face down."),
    printed("P03", "Jaw B", "mj_b", "Servo side half: the pad rib, the tail lug with the pivot's counterbore, the "
            "clamp insert's hole. Jaw face down."),
    printed("P04", "Link", "link", "Crank to jaw tail."),
    printed("P05", "Crank", "crank", "Fits the servo's single-arm horn: print it FIRST and fit-check it "
            "(booklet step 2). TowerPro publishes no drawing of the horn."),
    printed("P06", "Anvil", "anvil", "The strip the blade closes on. A wear part: one fitted, one spare.", qty=2),
    printed("P09", "Pad", "pad", "One on each jaw: a comb of 11 fins on a one-way dovetail, sliding into the rib "
            "from the servo side. Print lying on its side, solid, about 20 mm/s. A wear part: two fitted, two "
            "spare.", qty=4, tpu=True),

    ("M01", "Mechanism", "Micro servo, metal gear, 180 deg", "TowerPro MG90S", "Waveshare",
     "https://www.waveshare.com/MG90S-Servo.htm", 2, "pc", 2.59, "Verified",
     "ONE IS FITTED, ONE IS THE SPARE: a servo held stalled for long can strip. 2.8 kg cm at 6 V on the "
     "listing; the design assumes only 0.15 N m (1.5 kg cm) and still cuts at 34 N. Comes with the "
     "single-arm horn the crank fits."),
    ("M02", "Mechanism", "Snap-off blades, 9 mm, 10 pack", "OLFA AB-10B", "Toolup",
     "https://toolup.com/products/olfa-ab10b-standard-blades-10-pk", 1, "pack", 4.92, "Verified",
     "One 34 mm piece is the blade (booklet step 3). The pack is years of spares: snap a fresh piece when "
     "stems start to crush instead of cut."),
    ("M03", "Mechanism", "TPU 95A filament, 1.75 mm", "any maker", "any", "", 0, "spool", 0.0, "To source",
     "For the pads (P09): about 3 g for four. Any 95A TPU; a softer one holds a little less. Priced in P09."),
    ("M04", "Mechanism", "Dowel pin, 2 x 6, hardened", "ISO 8734", "any", "", 1, "pc", 0.50, "To source",
     "Link to jaw B's lug."),
    ("M05", "Mechanism", "Dowel pin, 2 x 5, hardened", "ISO 8734", "any", "", 1, "pc", 0.50, "To source",
     "Crank to link. A small pack of 2 mm pins covers both."),
    ("M06", "Mechanism", "LEGO Technic pin with friction", "LEGO 2780", "BrickOwl or Pick a Brick",
     "https://www.brickowl.com/catalog/33899-38", 4, "pc", 0.10, "To source",
     "How the tool goes on the 280's flange, no screws: the same pins the adaptive gripper used. If you "
     "already have the gripper's, use those."),

    ("F01", "Fasteners", "Shoulder screw, 4 mm shoulder x 6, M3, A2", "ISO 7379 pattern; e.g. ELESA+GANTER "
     "ISO 7379-4-M3-6-NI", "TME, or any", "https://www.tme.eu/dk/en/katalog/shoulder-screws_113391/params/b532_thread/p1448207_m3/",
     1, "pc", 3.00, "To source",
     "The jaw pivot, from the lug side: head 7 x 3 flush in jaw B's counterbore, 2 mm hex. Tighten fully: the "
     "shoulder's end bears on the cheek's insert, so the jaw keeps 0.2 of play. Shoulder 6 exactly; the "
     "cheek's blind bore takes a thread up to 7 long."),
    ("F02", "Fasteners", "Heat-set insert, M3 x 5.7, 4.6 OD", "CNC Kitchen M3 Standard (or Ruthex, same size)",
     "3DJake", "https://www.3djake.com/cnc-kitchen/threaded-inserts-m3-standard", 1, "pc", 0.11, "Verified",
     "Into the cheek from the jaw side, flush (booklet step 4). $11.21 per 100 on the listing."),
    ("F03", "Fasteners", "Heat-set insert, M2 x 3, 3.6 OD", "CNC Kitchen M2 Standard", "3DJake",
     "https://www.3djake.com/cnc-kitchen/threaded-inserts-m3-standard", 1, "pc", 0.12, "Estimate",
     "Into jaw B from its outer face, flush, for the blade clamp (booklet step 3). Hole 3.2."),
    ("F04", "Fasteners", "M2 x 6 countersunk socket, A2", "ISO 10642", "any", "", 2, "pc", 0.20, "To source",
     "ONE is the blade clamp, flush in jaw A, into jaw B's insert. ONE is the crank into the servo's spline: "
     "countersunk because the link swings 0.4 mm from the shaft axis. The screw in the servo's bag does NOT "
     "fit there. 1.3 mm hex."),
    ("F05", "Fasteners", "M3 x 5 countersunk socket, A2", "ISO 10642", "any", "", 2, "pc", 0.15, "To source",
     "The D405 onto its bracket, heads flush in the plate, 2 of thread in the camera. Five long, no longer: "
     "the camera's threads are shallow. 2 mm hex."),

    ("E01", "Electronics", "Step-down regulator, 6 V 1 A", "Pololu D24V10F6 (#2832)", "Pololu",
     "https://www.pololu.com/product/2832", 1, "pc", 12.95, "Verified",
     "12 V wrist line in, 6 V to the servo. The arm's own 5 V pin is rated in tens of mA and the servo stalls "
     "at 0.7 A, so the servo never runs from the arm."),
    ("E02", "Electronics", "ALTERNATE: 6-channel USB servo controller", "Pololu Micro Maestro (#1350)", "Pololu",
     "https://www.pololu.com/product/1350", 0, "pc", 24.95, "Estimate",
     "ONLY IF the end connector's G22 will not give a steady 50 Hz (commissioning, step 12). It drives the "
     "same servo lead from a USB port on the Jetson."),

    ("W01", "Wiring", "Servo extension lead, 3-pin, 1 m", "JR / Futaba style", "any", "", 1, "pc", 3.00,
     "To source", "From the servo along the arm to the end connector: signal to G22, ground to GND. The "
     "red wire goes to the regulator, not to the arm."),
    ("W02", "Wiring", "Silicone wire, 22 AWG, red and black, 2 m each", "any", "any", "", 1, "set", 6.00,
     "To source", "The 12 V wrist line from the cabinet's 12 V rail (sheet E-01), along the arm with the "
     "D405's USB cable."),
    ("W03", "Wiring", "Heat-shrink, small zip ties, double-sided foam tape", "any", "any", "", 1, "set", 6.00,
     "To source", "Sleeve the regulator and stick it into its bay with a 12 mm square of the tape; tie the leads "
     "under the bar below the bay, and the three cables at each link with one loose loop at the wrist for "
     "J6's +/-180 deg."),

    ("X01", "Not bought", "Adaptive gripper (gantry BOM R02)", "Elephant Robotics", "",
     "https://americas.shop.elephantrobotics.com/collections/end-effectors/products/adaptive-gripper",
     0, "pc", 129.99, "Verified",
     "NO LONGER NEEDED. The Herb Snip cuts and holds in one closing, so a second tool and a tool change "
     "are not needed. Gantry BOM Rev D carries it at quantity 0."),
    ("X02", "Not bought", "RealSense D405", "Intel", "", "", 0, "pc", 0.0, "Owned",
     "Already in the greenhouse BOM (G056) and on the bench. It moves onto the Herb Snip's bracket."),
]

GROUP_ORDER = ["Printed", "Mechanism", "Fasteners", "Electronics", "Wiring", "Not bought"]
HDR = ["Ref", "Group", "Item", "Mfr / Part", "Supplier", "Link",
       "Qty", "Unit", "Unit $", "Ext $", "Status", "Notes"]

INK = "1D2326"
HDR_FILL = PatternFill("solid", fgColor="1D2326")
GRP_FILL = PatternFill("solid", fgColor="E8EEFC")
WARN_FILL = PatternFill("solid", fgColor="FDECEC")
OK_FILL = PatternFill("solid", fgColor="EAFAF1")
THIN = Side(style="thin", color="C8D0D6")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def build(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Herb Snip BOM"
    ws["A1"] = f"MAAG  ·  HERB SNIP BOM  ·  {REV}"
    ws["A1"].font = Font(size=15, bold=True, color=INK)
    ws["A2"] = (f"Generated {DATE}. Scope: the cut-and-hold tool for the myCobot 280, through to commissioning; "
                "the dead-leaf tray and the feeder are on the Harvest Rev B buy list. The arm, the D405 and the 12 V rail are in the gantry and "
                "greenhouse BOMs.")
    ws["A2"].font = Font(size=10, color="5B6770")
    ws["A3"] = ("REPLACES the adaptive gripper (gantry BOM R02, $129.99). Print the crank first and check it "
                "against your servo's horn before printing anything else.")
    ws["A3"].font = Font(size=10, color="B91C1C", bold=True)
    for a in ("A1:L1", "A2:L2", "A3:L3"):
        ws.merge_cells(a)
    ws.row_dimensions[2].height = 28
    ws.row_dimensions[3].height = 30
    for r in (2, 3):
        ws.cell(r, 1).alignment = Alignment(wrap_text=True, vertical="top")

    r = 5
    for c, h in enumerate(HDR, 1):
        cell = ws.cell(r, c, h)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = HDR_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
    ws.freeze_panes = "A6"
    r += 1
    grand, totals = 0.0, {}
    for grp in GROUP_ORDER:
        rows = [x for x in ROWS if x[1] == grp or (grp == "Printed" and x[9] == "Printed")]
        if not rows:
            continue
        ws.cell(r, 1, grp.upper()).font = Font(bold=True, size=10, color=INK)
        for c in range(1, len(HDR) + 1):
            ws.cell(r, c).fill = GRP_FILL
            ws.cell(r, c).border = BORDER
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(HDR))
        r += 1
        sub = 0.0
        for (ref, g, item, part, sup, link, qty, unit, up, status, note) in rows:
            ext = qty * up
            sub += ext
            for c, v in enumerate([ref, grp if status == "Printed" else g, item, part, sup, link, qty, unit, up,
                                   ext, status, note], 1):
                cell = ws.cell(r, c, v)
                cell.border = BORDER
                cell.alignment = Alignment(vertical="top", wrap_text=(c in (3, 4, 12)))
                if c in (9, 10):
                    cell.number_format = '"$"#,##0.00'
                if c == 7:
                    cell.alignment = Alignment(horizontal="center", vertical="top")
            if link:
                lc = ws.cell(r, 6)
                lc.hyperlink, lc.value = link, "open"
                lc.font = Font(color="1D4ED8", underline="single", size=9)
                lc.alignment = Alignment(horizontal="center", vertical="top")
            sc = ws.cell(r, 11)
            sc.fill = OK_FILL if status == "Verified" else (WARN_FILL if status == "To source" else PatternFill())
            sc.font = Font(size=9, bold=(status == "Verified"))
            if qty == 0:
                for c in range(1, len(HDR) + 1):
                    ws.cell(r, c).font = Font(italic=True, color="8A9299", size=10)
            r += 1
        totals[grp] = sub
        grand += sub
        ws.cell(r, 9, f"{grp} subtotal").font = Font(bold=True, size=9, color="5B6770")
        ws.cell(r, 9).alignment = Alignment(horizontal="right")
        v = ws.cell(r, 10, sub)
        v.number_format = '"$"#,##0.00'
        v.font = Font(bold=True, size=10)
        for c in range(1, len(HDR) + 1):
            ws.cell(r, c).border = BORDER
        r += 2
    ws.cell(r, 9, "HERB SNIP TOTAL").font = Font(bold=True, size=12, color=INK)
    ws.cell(r, 9).alignment = Alignment(horizontal="right")
    g = ws.cell(r, 10, grand)
    g.number_format = '"$"#,##0.00'
    g.font = Font(bold=True, size=13, color="B91C1C")
    r += 2

    notes = [
        "WHAT IT CAN DO",
        "Cut a stem up to a chili's and hold the cut piece: the pads close a moment before the blade, so a leaf or a "
        "tip rides in the closed jaws to the feeder, a dead leaf to the dead-leaf tray. 34 N at the cut point with the servo derated to 0.15 N m.",
        "Pick a pepper by cutting its stem. It does not grip a loose object presented side-on: the pads are on one "
        "side of the blade only.",
        "On the flange: 95.9 g of tool and 58 g of D405, 153.9 g of the 280's 250 g payload, 96 g left for what it "
        "carries.",
        "Every printed part lies on a flat face: no supports. The camera ring wants a 5 mm brim (it stands 42 tall).",
        "",
        "THINGS THAT WILL BITE",
        "The crank must fit the horn in YOUR servo's bag. Print it first (step 2); if it rocks, change HORN in "
        "snip_cad.py and reprint the crank, a few minutes.",
        "Fit the crank with the servo at its closed end (step 6), or the jaw closes in mid-air and the servo pushes "
        "against nothing at the far end of its travel.",
        "The end connector's PWM has 256 steps in 20 ms: 78 us, about 7 degrees of servo a step. Open and closed are "
        "all it needs; tools_snip_check.py finds the two pulses.",
        "The servo runs from its own 6 V regulator on the 12 V wrist line, never from the arm: the arm's pins are "
        "rated in tens of mA.",
        "Doors, the feeder's lid and the E-stop cut the arm's power: no pulses, the servo goes limp, the jaw can be "
        "pushed open by hand.",
        "Setting the pivot insert: the deck is 4 under its axis, so the iron must be under 8 thick for its first 50. "
        "The servo's tab screws want a driver under 5 thick.",
    ]
    for line in notes:
        c = ws.cell(r, 1, line)
        c.font = Font(bold=True, size=11, color=INK) if (line.isupper() and line) else Font(size=10, color="3A4248")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(HDR))
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if len(line) > 110:
            ws.row_dimensions[r].height = 30
        r += 1
    for i, w in enumerate([7, 14, 40, 30, 22, 7, 6, 7, 10, 11, 11, 80], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    s = wb.create_sheet("Summary")
    s["A1"] = "HERB SNIP BOM SUMMARY"
    s["A1"].font = Font(size=14, bold=True, color=INK)
    s["A3"], s["B3"] = "Group", "Subtotal"
    for c in ("A3", "B3"):
        s[c].font = Font(bold=True, color="FFFFFF")
        s[c].fill = HDR_FILL
    rr = 4
    for grp in GROUP_ORDER:
        if grp in totals:
            s.cell(rr, 1, grp)
            s.cell(rr, 2, totals[grp]).number_format = '"$"#,##0.00'
            rr += 1
    s.cell(rr, 1, "TOTAL").font = Font(bold=True, size=12)
    tv = s.cell(rr, 2, grand)
    tv.number_format = '"$"#,##0.00'
    tv.font = Font(bold=True, size=12, color="B91C1C")
    s.cell(rr + 2, 1, f"Against the adaptive gripper it replaces ($129.99), the Herb Snip saves "
                      f"${129.99 - grand:,.2f} and adds a cutter.").font = Font(size=10, color="5B6770")
    s.column_dimensions["A"].width = 30
    s.column_dimensions["B"].width = 16
    wb.save(path)
    return grand, totals


if __name__ == "__main__":
    out = os.path.join(HERE, "Maag_Herb_Snip_BOM_RevA.xlsx")
    total, groups = build(out)
    print(f"saved {out}")
    for g, v in groups.items():
        print(f"  {g:<12} ${v:>8,.2f}")
    print(f"  {'TOTAL':<12} ${total:>8,.2f}")
