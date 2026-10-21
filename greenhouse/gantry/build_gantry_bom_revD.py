#!/usr/bin/env python3
"""Maag - GANTRY SUBSYSTEM bill of materials.

Rev D (design 0.7.0): Rev C with one line changed. R02, the adaptive gripper, goes to
quantity 0: the Herb Snip (greenhouse/snip, its own BOM) replaces it. Nothing else moves.

Scope: everything needed to assemble the X/Z gantry, mount the robot arm on it,
power it, wire it and bench-test it BEFORE it goes into the greenhouse frame.
Out of scope: the 4040 frame itself, trays, lighting, irrigation, sensing.

Sourcing note, October 2026: OpenBuilds wound down and its part store is gone,
so every OpenBuilds line from BOM Rev E has been re-sourced. Maker Store USA
(makerstore.cc) manufactures the same V-slot geometry and ships from a US
warehouse; silver SKUs carry the -S suffix.

STATUS column:
  Verified   price and availability read off the live listing
  Estimate   product confirmed live, exact price behind a variant selector
  To source  commodity part, pick any that meets the spec in NOTES

Rev C (booklet Rev E): every OpenBuilds part re-checked against OpenBuilds' own
drawings as modelled in bd_warehouse. Changes: eccentric spacers are 10 mm hex;
each wheel stack carries a 1 mm precision shim; the nut block takes its own
spacers, screws and nuts; the mast top is the C-Beam End Mount (80 x 50 x 12);
the X rail hangs on four bent SendCutSend brackets instead of cast corners;
the arm plate is Rev B (tapped M3 for the G base, M4 for the bare arm,
countersunk M5 to the XL plate); a manual-reset button for the safety relay;
the fastener list is complete and counted off the model.
"""
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

REV = "Gantry Rev D"
DATE = "2026-10-21"

MS = "https://makerstore.cc"

# ref, group, item, mfr/part, supplier, link, qty, unit, unit_price, status, note
ROWS = [
    # ---------------------------------------------------------------- structure
    ("X01", "Structure", "C-Beam linear rail, 1500 mm, SILVER",
     "Maker Store LR-C-S", "Maker Store USA", f"{MS}/product/c-beam/",
     2, "pc", 80.00, "Estimate",
     "THE X RAIL AND THE Z MAST. SKU LR-C-S is the silver one; LR-C-B is black. "
     "Listed range $11.15 to $130.00 across 250 to 2400 mm, so confirm the 1500 mm "
     "price in the selector. Ships from their US warehouse. Custom cutting is "
     "temporarily unavailable, so buy 1500 mm: the Z mast uses its full length, the "
     "X rail is CUT to 1397 so it finishes flush with the cabinet sides."),

    ("X02", "Structure", "ALTERNATE: C-Beam HEAVY, 1500 mm, silver",
     "Maker Store LR-CHV-S", "Maker Store USA", f"{MS}/product/us-lr-chv-s/",
     0, "pc", 110.00, "Estimate",
     "Walls about 2.7x thicker, roughly 72 percent stiffer for 60 percent more "
     "weight. NOT required: standard C-Beam already deflects only 0.17 mm under "
     "the 2.6 kg moving load. Buy it only if you want margin for a heavier future "
     "end effector."),

    ("X03", "Structure", "Rail bracket TOP, 5052-H32 0.125 in, one 90 deg bend",
     "SendCutSend custom, rail_bracket_top.dxf", "SendCutSend", "https://sendcutsend.com/",
     2, "pc", 9.00, "Estimate",
     "REPLACES the cast corner brackets: the rail's last 40 mm at each end sit UNDER the "
     "top depth rails, so nothing can bolt to its top face there. Flat 40 x 69.38, legs "
     "40 x 35, bend at 37.19 from the leg-A end. Leg A: 2 x M5 into the rail's front top "
     "groove; leg B: 2 x M5 into the top back rail's slot."),

    ("X04", "Structure", "Rail bracket BOTTOM, 5052-H32 0.125 in, one 90 deg bend",
     "SendCutSend custom, rail_bracket_bottom.dxf", "SendCutSend", "https://sendcutsend.com/",
     2, "pc", 9.00, "Estimate",
     "Under the rail at each end. Flat 40 x 84.38, legs 40 x 50. Leg A: 2 x M5 into the "
     "rail's front bottom groove; leg B: 2 x M5 into the rear upright's slot."),

    # ---------------------------------------------------------------- carriages
    ("C01", "Carriage", "C-Beam gantry plate, XL",
     "PLATE-C-GANTRY-XL", "Maker Store USA", f"{MS}/product/bun-cbeam-xlgantry/",
     2, "pc", 18.15, "Verified",
     "One carriage on X, one on the Z mast. The XL bundle (SKU BUN-CBEAM-XLGANTRY, "
     "$44.23) shows INSUFFICIENT STOCK, so buy the pieces individually: the plate, "
     "wheels and eccentrics are each listed in stock."),

    ("C02", "Carriage", "Solid V wheel kit",
     "WHEEL-SOLIDV-KIT", "Maker Store USA", f"{MS}/product/bun-cbeam-xlgantry/",
     8, "kit", 4.93, "Verified",
     "Four per gantry plate. Solid, not the moulded V wheel: the solid wheel is "
     "what gives the carriage its rigidity under a cantilevered arm."),

    ("C03", "Carriage", "Eccentric spacer, 10 mm hex, 6 mm",
     "SHIM-ECCENTRIC-8-6", "Maker Store USA", f"{MS}/product/bun-cbeam-xlgantry/",
     4, "pc", 2.45, "Verified",
     "Two per plate. These are how you preload the wheels against the rail. "
     "Preload is the single biggest influence on gantry slop, so set it carefully. "
     "10 mm ACROSS FLATS (Rev B said 8): a thin 10 mm spanner turns them."),

    ("C04", "Carriage", "Aluminium spacer, 6 mm",
     "SHIM-SPAC-6MM", "Maker Store USA", f"{MS}/product-category/hardware/",
     6, "pc", 1.20, "Estimate",
     "Two per plate under the FIXED wheels, and two between the nut block and the Z "
     "carriage. Rev B had 4."),

    ("C07", "Carriage", "Precision shim, 10 x 5 x 1 mm",
     "SHIM-PREC-10-5-1", "Maker Store USA", f"{MS}/product-category/hardware/",
     8, "pc", 0.40, "Estimate",
     "NEW. One in every wheel stack, between the spacer (or eccentric) and the wheel, "
     "so the bearing's inner race is clamped and the outer race spins free."),

    ("C05", "Carriage", "M5 low profile screws, 30 mm, 10 pack",
     "SCREWS-M5-LP-30", "Maker Store USA", f"{MS}/product-category/hardware/",
     1, "pack", 8.00, "Estimate",
     "Plate 6 + spacer 6 + shim 1 + wheel 11 + nyloc 5 is 29, so 30 it is. Four per "
     "plate, heads in the plate's 1.6 mm counterbores. OpenBuilds low profile heads "
     "are 1.5 mm: DIN 7984 heads (2.8 to 3.5) do not fit the 2.5 mm gap to the beam."),

    ("C06", "Carriage", "M5 nyloc nut, 10 pack",
     "Nyloc M5 DIN 985", "Maker Store USA", f"{MS}/product-category/hardware/",
     1, "pack", 3.00, "To source",
     "MISSING FROM REV A. Every wheel stack ends in one: screw, plate, spacer, "
     "wheel, nyloc. Eight for the wheels, one for the idler axle."),

    # ------------------------------------------------------------------ X drive
    ("D01", "X drive", "GT2 timing belt, 9 mm wide, open ended",
     "GT2-9mm", "Amazon", "https://www.amazon.com/s?k=GT2+9mm+open+timing+belt+5m",
     4, "m", 4.00, "To source",
     "REPLACES the discontinued OpenBuilds NEMA 17 Belt and Pinion set (G063). "
     "The loop runs inside the X rail's channel, pulley to idler, about 2.75 m "
     "plus tails into the clamps: buy 4 m. 9 mm belt for a 2.6 kg moving mass."),

    ("D02", "X drive", "GT2 timing pulley, 20 tooth, 9 mm belt, 6.35 mm bore",
     "GT2-20T-9", "Amazon", "https://www.amazon.com/s?k=GT2+20+tooth+pulley+9mm+belt+6.35mm+bore",
     1, "pc", 9.00, "To source",
     "CHANGED FROM 8 mm. The bore must match the X motor's shaft, and the M02 "
     "NEMA 23 is specified with a 6.35 mm shaft. 20 T on GT2 is 40 mm per rev, "
     "about 0.025 mm per step at 1/8 microstepping."),

    ("D03", "X drive", "Smooth idler pulley, 9 mm belt, 5 mm bore",
     "Idler-9mm", "Amazon", "https://www.amazon.com/s?k=smooth+idler+pulley+9mm+belt+5mm+bore",
     1, "pc", 5.00, "To source",
     "CHANGED FROM 2. The motor's pulley turns the belt at one end, so one idler "
     "at the other end is all the loop needs. It rides on an M5 x 40 through a "
     "5.2 mm hole drilled in the rail's web, washer each side, nyloc."),

    ("D04", "X drive", "Belt clamp / tensioner block pair",
     "Belt clamp", "Amazon", "https://www.amazon.com/s?k=GT2+belt+clamp+tensioner+CNC",
     1, "set", 12.00, "To source",
     "Two blocks on the BACK of the X carriage, reaching into the rail's channel, "
     "each gripping one end of the loop's top run. A loose belt shows up as "
     "backlash and will defeat hand-eye calibration."),

    # ------------------------------------------------------------------ Z drive
    ("D10", "Z drive", "Acme lead screw, 8 mm, Tr8x8(p2), 1500 mm",
     "Maker Store", "Maker Store USA", f"{MS}/product-category/lead-screw/",
     1, "pc", 35.00, "Estimate",
     "4-start, 8 mm lead. Matches the anti-backlash block below. Mark the actual "
     "travel you need before cutting: the mast is 1500 mm but usable travel is less."),

    ("D11", "Z drive", "Anti-backlash nut block, 8 mm Acme",
     "Maker Store", "Maker Store USA", f"{MS}/product/anti-backlash-nut-block/",
     1, "pc", 9.99, "Estimate",
     "Spring-loaded split nut. Without it the mast sags into the backlash every "
     "time the arm's weight reverses the load direction."),

    ("D12", "Z drive", "Thrust bearing, 8 mm",
     "Maker Store", "Maker Store USA", f"{MS}/product-category/hardware/",
     2, "pc", 1.99, "Estimate",
     "BOTH at the top end plate, one each side of it, so the screw hangs from the "
     "top and the coupler at the foot carries only torque. Thrust, not radial."),

    ("D15", "Z drive", "C-Beam End Mount, 80 x 50 x 12, 16.1 bearing recess",
     "Maker Store", "Maker Store USA", f"{MS}/product-category/plates/",
     1, "pc", 9.00, "To source",
     "Caps the mast top: four M5 x 25 low profile into the beam's end taps. One "
     "thrust bearing sits in its 16.1 recess, the other underneath."),

    ("D16", "Z drive", "Shaft lock collar, 8 mm",
     "Generic", "Amazon", "https://www.amazon.com/s?k=8mm+shaft+lock+collar",
     2, "pc", 2.00, "To source",
     "MISSING FROM REV A. Clamp the two thrust bearings to the screw at the top "
     "end plate."),

    ("D13", "Z drive", "Flexible shaft coupler, 6.35 to 8 mm",
     "Maker Store", "Maker Store USA", f"{MS}/product-category/hardware/",
     1, "pc", 6.99, "Estimate",
     "CHECK YOUR MOTOR SHAFT. NEMA 23 is usually 6.35 mm (1/4 in), not 5 mm. "
     "BOM Rev E carried a 5 to 8 mm coupler, which was wrong for a NEMA 23."),

    ("D14", "Z drive", "NEMA 23 motor mount plate",
     "PLATE-MOTOR-MOUNT", "Maker Store USA", f"{MS}/product/plate-motor-mount/",
     2, "pc", 12.00, "Estimate",
     "X: flat on the X rail's front lips at its left end, four M5 x 10 into T-nuts "
     "in the lip grooves. Z: across the mast's foot. The four MOTOR holes must be "
     "threaded M5: the motor screws go in from the motor side through the NEMA "
     "flange's through-holes. Tap them if they are plain."),

    # ------------------------------------------------------------------- motors
    ("M01", "Motors", "Stepper, Z axis, WITH electromagnetic brake",
     "StepperOnline 23HS22-4004D-B280", "omc-stepperonline.com",
     "https://www.omc-stepperonline.com/nema-23-stepper-motor-1-2nm-169-93oz-in-with-24v-4-5w-electromagnetic-brake-23hs22-4004d-b280",
     1, "pc", 36.07, "Verified",
     "THE BRAKE IS NOT OPTIONAL. It is released by 24 V, so a power cut parks the "
     "mast instead of dropping the arm through the trays. 1.2 Nm, 24 V 4.5 W coil."),

    ("M02", "Motors", "Stepper, X axis, NEMA 23, 2.8 A",
     "StepperOnline NEMA 23", "omc-stepperonline.com",
     "https://www.omc-stepperonline.com/nema-23-stepper-motor",
     1, "pc", 25.00, "To source",
     "Any NEMA 23 at about 2.8 A and 1.2 Nm. Pick a 6.35 mm shaft to match the "
     "coupler and pulley above."),

    # --------------------------------------------------------------- electronics
    ("E01", "Electronics", "Motion controller, 4 axis FluidNC",
     "Elecrow ESP32 + 4x TMC2209", "elecrow.com",
     "https://www.elecrow.com/4x-cnc-controller-integrated-esp32-and-tmc2209.html",
     1, "pc", 49.00, "Verified",
     "Bart Dring's FluidNC on an ESP32. Four axes, two used, two spare. Takes "
     "G-code over USB or wifi. This is the piece you bench-test against first."),

    ("E02", "Electronics", "24 V DC power supply, 350 W",
     "Mean Well LRS-350-24", "DigiKey",
     "https://www.digikey.com/en/products/detail/mean-well-usa-inc/LRS-350-24/7705034",
     1, "pc", 45.00, "Estimate",
     "Shared with the greenhouse build. For bench testing the gantry alone, any "
     "24 V 5 A supply will drive both steppers and the brake."),

    ("E03", "Electronics", "Fuse block, 6 circuit ATO",
     "Blue Sea 5025", "Amazon", "https://www.amazon.com/s?k=Blue+Sea+5025+fuse+block",
     1, "pc", 28.00, "To source",
     "ATO: 5 A motion (ahead of 13/14), 1 A Z brake (ahead of 23/24), 1 A relay "
     "supply and reset. Omron caps the fuse ahead of each contact at 8 A."),

    ("E04", "Electronics", "Hook-up wire, 18 AWG stranded, assorted",
     "Generic", "Amazon", "https://www.amazon.com/s?k=18+AWG+stranded+hookup+wire+kit",
     1, "kit", 22.00, "To source", "Motor and brake runs."),

    ("E05", "Electronics", "Ferrule kit with crimp tool",
     "Newhouse FTK1200", "Home Depot",
     "https://www.homedepot.com/s/ferrule%2520crimp%2520kit",
     1, "kit", 35.00, "To source",
     "Ferrule every stranded conductor into the controller's screw terminals. "
     "Bare stranded wire in a screw terminal works loose with gantry vibration."),

    # -------------------------------------------------------------- limits/safety
    ("S01", "Limits & safety", "Mechanical limit switch with lead, NO/NC",
     "Generic microswitch endstop", "Amazon",
     "https://www.amazon.com/s?k=mechanical+endstop+limit+switch+CNC+with+cable",
     4, "pc", 3.00, "To source",
     "REPLACES the discontinued OpenBuilds Xtension kit (G068). X min, X max, "
     "Z min, Z max. Wire them NORMALLY CLOSED so a cut wire reads as a trip."),

    ("S02", "Limits & safety", "Limit switch mounting plate",
     "PLATE-LIMIT-SWITCH", "Maker Store USA", f"{MS}/product/limit-switch-plate/",
     4, "pc", 4.00, "Estimate", "Mounts a microswitch into the V-slot."),

    ("S03", "Limits & safety", "E-stop head, 40 mm mushroom",
     "Eaton M22-PV", "DigiKey", "https://www.digikey.com/en/products/filter/emergency-stop/",
     1, "pc", 28.00, "Estimate", "Latching, twist to release."),

    ("S04", "Limits & safety", "E-stop contact block, 1 NC",
     "Eaton M22-K01", "DigiKey", "https://www.digikey.com/en/products/filter/emergency-stop/",
     2, "pc", 11.00, "Estimate",
     "BUY TWO. The safety relay is dual channel and cross-monitors them, so one "
     "welded contact is detected."),

    ("S05", "Limits & safety", "E-stop mounting collar",
     "Eaton M22-A", "DigiKey", "https://www.digikey.com/en/products/filter/emergency-stop/",
     1, "pc", 9.00, "Estimate", ""),

    ("S07", "Limits & safety", "Reset pushbutton, flush, black, with 1 NO block and collar",
     "Eaton M22-D-B + M22-K10 + M22-A", "DigiKey",
     "https://www.digikey.com/en/products/filter/pushbutton-switches/",
     1, "set", 24.00, "Estimate",
     "NEW. The G9SE-201 is wired for MANUAL reset, which needs a momentary NO button "
     "between T31 and T32. Rev B had none."),

    ("S06", "Limits & safety", "Safety relay, dual channel, 24 VDC",
     "Omron G9SE-201", "DigiKey",
     "https://www.digikey.com/en/products/detail/omron-automation-and-safety/G9SE-201/7495167",
     1, "pc", 217.00, "Verified",
     "The expensive line. 13/14 switches 24 V to the motion controller, 23/24 "
     "switches the Z brake coil (low side through the controller's MOSFET 1), so an "
     "E-stop limps the motors and locks the mast but leaves sensing alive. Manual "
     "reset: 24 V on T33, the S07 button from T31 to T32. X1 is a status output only. "
     "You CAN bench-test the gantry without it; do not run the arm without it."),

    # --------------------------------------------------------------- fasteners
    ("H01", "Fasteners", "M5 x 25 low profile, 10 pack", "SCREWS-M5-LP-25", "Maker Store USA",
     f"{MS}/product-category/hardware/", 1, "pack", 8.00, "Estimate",
     "Nut block (2), belt clamps (4), End Mount (4)."),
    ("H02", "Fasteners", "M5 x 10 low profile, 10 pack", "SCREWS-M5-LP-10", "Maker Store USA",
     f"{MS}/product-category/hardware/", 1, "pack", 6.00, "Estimate",
     "Mast back to the X carriage plate, 6, into T-nuts in the mast's outer back grooves."),
    ("H03", "Fasteners", "M5 x 10 socket cap ISO 4762, 50 pack", "Generic A2", "Amazon",
     "https://www.amazon.com/s?k=M5+x+10+socket+head+cap+screw+stainless", 1, "pack", 9.00, "To source",
     "Motors (8), X motor plate to the rail (4), rail brackets (16)."),
    ("H04", "Fasteners", "M5 socket caps: 12 (x4) and 40 (x1)", "Generic A2", "Amazon",
     "https://www.amazon.com/s?k=M5+socket+head+cap+screw+assortment", 1, "set", 8.00, "To source",
     "M5 x 12 for the Z foot plate into the mast's end taps; M5 x 40 is the idler axle."),
    ("H05", "Fasteners", "M5 x 10 flat head ISO 10642, 90 deg", "Generic A2", "Amazon",
     "https://www.amazon.com/s?k=M5+x+10+flat+head+socket+screw", 4, "pc", 0.50, "To source",
     "Arm plate into the XL plate's tapped holes, heads flush in SendCutSend's countersinks."),
    ("H06", "Fasteners", "M5 drop-in T-nut, 20 series (C-Beam), 25 pack", "TNUT-M5-DROP", "Maker Store USA",
     f"{MS}/product-category/hardware/", 1, "pack", 9.00, "Estimate",
     "14: mast to carriage (6), rail brackets into the C-Beam (8)."),
    ("H07", "Fasteners", "M5 T-nut, slot 8 (40 series 4040)", "Generic", "Amazon",
     "https://www.amazon.com/s?k=M5+T-nut+slot+8+40+series", 8, "pc", 0.40, "To source",
     "Rail brackets into the top back rails and the rear uprights. NOT the C-Beam size."),
    ("H08", "Fasteners", "M5 hex nut (2), M5 washer (2)", "Generic A2", "Amazon",
     "https://www.amazon.com/s?k=M5+hex+nut+washer+assortment", 1, "set", 3.00, "To source",
     "Nuts in the nut block's pockets; washers either side of the idler."),
    ("H09", "Fasteners", "M3 x 35 socket cap ISO 4762", "Generic A2", "Amazon",
     "https://www.amazon.com/s?k=M3+x+35+socket+head+cap+screw", 4, "pc", 0.40, "To source",
     "The arm's G base onto the arm plate's M3 taps, through its 32 mm."),
    ("H10", "Fasteners", "M3 x 10 + M3 T-nut, limit switches; M3 standoffs, controller", "Generic", "Amazon",
     "https://www.amazon.com/s?k=M3+standoff+kit", 1, "set", 12.00, "To source",
     "8 screws and T-nuts for the four switches; 4 standoffs, nuts and M3 x 6 for the board."),

    # ---------------------------------------------------------------- robot arm
    ("R01", "Robot arm", "Robot arm, 6 DOF",
     "Elephant Robotics myCobot 280 Pi", "Elephant Robotics Americas",
     "https://americas.shop.elephantrobotics.com/products/mycobot-280-pi-worlds-smallest-and-lightest-six-axis-collaborative-robot",
     1, "pc", 759.00, "Verified",
     "The Pi version, NOT the M5. The Pi runs its own Linux and is controlled over "
     "TCP, which is what the arm module in the software stack expects. $759 at 5 "
     "percent off, US warehouse, in stock."),

    ("R02", "Robot arm", "Adaptive gripper",
     "Elephant Robotics myCobot Adaptive Gripper", "Elephant Robotics Americas",
     "https://americas.shop.elephantrobotics.com/collections/end-effectors/products/adaptive-gripper",
     0, "pc", 129.99, "Verified",
     "NOT BOUGHT from design 0.7.0: the Herb Snip (greenhouse/snip, Maag_Herb_Snip_BOM_RevA.xlsx) "
     "cuts and holds in one tool and replaces it. Kept here, at quantity 0, so a Rev C build can see "
     "what changed."),

    ("R03", "Robot arm", "Arm mounting plate, 6061-T6, 0.250 in",
     "SendCutSend custom, DXF in repo", "SendCutSend",
     "https://sendcutsend.com/",
     1, "pc", 85.00, "Estimate",
     "Rev B, from arm_plate_revB.dxf. 160 square, 22 bore. TAPPED M3 x 4 at (+/-46, "
     "+/-65) for the arm's G base, TAPPED M4 x 4 on the 44 mm square for the bare arm, "
     "COUNTERSUNK M5 90 deg x 4 at (+/-30, +/-50.3) on the arm side: flat heads into "
     "the XL plate's tapped holes, flush under the base. Rev A's radial slots fitted "
     "no published pattern. Tapping and countersinking add to the $70.71 cut price."),

    # ------------------------------------------------------------------- cables
    ("K01", "Cables", "Cable chain, 15 x 30 mm inner, 1.5 m run",
     "Igus E14.1.028.0 or equivalent", "igus.com",
     "https://www.igus.com/product/series-E14?c=US&l=en",
     2, "run", 82.00, "Estimate",
     "One run for X, one for Z. Carries stepper phases, the brake pair, 12 V and "
     "the USB-C. NO MAINS IN THE CHAIN."),

    ("K02", "Cables", "Continuous-flex motor cable, 4 core shielded",
     "Igus chainflex or equivalent", "igus.com",
     "https://www.igus.com/cables/cable-price-check",
     10, "m", 4.80, "Estimate",
     "Ordinary stranded wire work-hardens and breaks inside a drag chain. Insist "
     "on a continuous-flex rating, not just 'braided'."),

    ("K03", "Cables", "High-flex USB-C cable, 3.1 Gen 1, 2 m",
     "Generic high flex", "Amazon",
     "https://www.amazon.com/s?k=high+flex+USB-C+3.1+Gen1+cable+2m+robotic",
     1, "pc", 24.00, "To source", "Jetson to the D405 wrist camera, through the chain."),

    ("K04", "Cables", "Cat6A patch cable, 3 m",
     "Monoprice SlimRun", "Monoprice", "https://www.monoprice.com/product?p_id=15156",
     2, "pc", 4.00, "To source",
     "Controller and arm onto the VLAN. If the Pi's RJ45 turns out to be enclosed "
     "in the arm base, the arm joins over wifi instead and you need only one."),

    ("K05", "Cables", "Cable glands, PG9, and spiral wrap",
     "Generic", "Amazon", "https://www.amazon.com/s?k=PG9+cable+gland+assortment",
     1, "kit", 18.00, "To source", "Strain relief where cables leave the chain."),
]

GROUP_ORDER = ["Structure", "Carriage", "X drive", "Z drive", "Motors",
               "Electronics", "Limits & safety", "Fasteners", "Robot arm", "Cables"]

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
    ws.title = "Gantry BOM"

    ws["A1"] = f"MAAG  ·  GANTRY SUBSYSTEM BOM  ·  {REV}"
    ws["A1"].font = Font(size=15, bold=True, color=INK)
    ws["A2"] = (f"Generated {DATE}. Scope: the X/Z gantry, the arm on it, its "
                "electronics and cabling, through to a bench test. "
                "Frame, trays, lighting, irrigation and sensing are NOT in this list.")
    ws["A2"].font = Font(size=10, color="5B6770")
    ws["A3"] = ("SOURCING: OpenBuilds wound down in 2025 and its store is gone. Every "
                "OpenBuilds line from BOM Rev E is re-sourced here, mostly to Maker "
                "Store USA, which makes the same V-slot geometry and ships from a US "
                "warehouse. Silver SKUs end in -S.")
    ws["A3"].font = Font(size=10, color="B91C1C", bold=True)
    ws.merge_cells("A1:L1"); ws.merge_cells("A2:L2"); ws.merge_cells("A3:L3")
    ws.row_dimensions[2].height = 28
    ws.row_dimensions[3].height = 42
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

    grand = 0.0
    group_totals = {}
    for grp in GROUP_ORDER:
        rows = [x for x in ROWS if x[1] == grp]
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
            vals = [ref, g, item, part, sup, link, qty, unit, up, ext, status, note]
            for c, v in enumerate(vals, 1):
                cell = ws.cell(r, c, v)
                cell.border = BORDER
                cell.alignment = Alignment(vertical="top", wrap_text=(c in (3, 12)))
                if c in (9, 10):
                    cell.number_format = '"$"#,##0.00'
                if c == 7:
                    cell.alignment = Alignment(horizontal="center", vertical="top")
            if link:
                lc = ws.cell(r, 6)
                lc.hyperlink = link
                lc.value = "open"
                lc.font = Font(color="1D4ED8", underline="single", size=9)
                lc.alignment = Alignment(horizontal="center", vertical="top")
            sc = ws.cell(r, 11)
            sc.fill = OK_FILL if status == "Verified" else (
                WARN_FILL if status == "To source" else PatternFill())
            sc.font = Font(size=9, bold=(status == "Verified"))
            if qty == 0:
                for c in range(1, len(HDR) + 1):
                    ws.cell(r, c).font = Font(italic=True, color="8A9299", size=10)
            r += 1
        group_totals[grp] = sub
        grand += sub
        tc = ws.cell(r, 9, f"{grp} subtotal")
        tc.font = Font(bold=True, size=9, color="5B6770")
        tc.alignment = Alignment(horizontal="right")
        v = ws.cell(r, 10, sub)
        v.number_format = '"$"#,##0.00'
        v.font = Font(bold=True, size=10)
        for c in range(1, len(HDR) + 1):
            ws.cell(r, c).border = BORDER
        r += 2

    ws.cell(r, 9, "GANTRY TOTAL").font = Font(bold=True, size=12, color=INK)
    ws.cell(r, 9).alignment = Alignment(horizontal="right")
    g = ws.cell(r, 10, grand)
    g.number_format = '"$"#,##0.00'
    g.font = Font(bold=True, size=13, color="B91C1C")
    r += 2

    notes = [
        "WHAT YOU CAN TEST WITHOUT THE REST OF THE GREENHOUSE",
        "1. Controller alone: flash FluidNC on the Elecrow board, connect over USB or wifi, confirm it answers $$ and reports its config.",
        "2. Motors on the bench: wire X and Z to the driver, set current limits, jog both. Do this BEFORE anything is bolted to a rail.",
        "3. Brake: the Z brake releases at 24 V. Confirm it holds with power off and releases with power on, by hand, motor uncoupled.",
        "4. One axis assembled: mount the X rail on a bench, fit the carriage, set eccentric preload, home against the limit switches.",
        "5. Z mast: assemble and jog the full travel, checking the anti-backlash nut has no slop at either end.",
        "6. Arm last: bolt the arm plate to the carriage, power the arm separately, confirm it answers over TCP before any coordinated motion.",
        "",
        "THINGS THAT WILL BITE",
        "The eccentric spacers set wheel preload. Too loose gives slop that defeats hand-eye calibration; too tight wears flats on the wheels. Snug, then back off until the wheel turns with light finger drag.",
        "Wire limit switches NORMALLY CLOSED. A broken wire then reads as a trip, instead of silently disabling the limit.",
        "Check the NEMA 23 shaft diameter before ordering the coupler. It is usually 6.35 mm, not 5 mm. BOM Rev E had this wrong.",
        "The arm must travel FOLDED between tiers: J2 -110, J3 -80, J4 -140, J5 -90, the shortest fold that does not hit itself, 162.6 mm long. With the real carriage stack (8.5 per carriage) it clears the tray line by 20.0 mm. That belongs in the motion planner, not in a comment.",
        "Do not run the arm under power without the safety relay and E-stop wired. Bench-testing the gantry alone without them is fine.",
        "",
        "PRICE CONFIDENCE",
        "Verified: read off the live listing on 2026-10-20.",
        "Estimate: product confirmed live, but the exact price sits behind a length or variant selector.",
        "To source: commodity part. Any item meeting the spec in the Notes column will do; the price is a realistic placeholder.",
    ]
    for line in notes:
        c = ws.cell(r, 1, line)
        if line.isupper() and line:
            c.font = Font(bold=True, size=11, color=INK)
        else:
            c.font = Font(size=10, color="3A4248")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(HDR))
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if len(line) > 110:
            ws.row_dimensions[r].height = 30
        r += 1

    widths = [7, 16, 42, 30, 22, 7, 6, 7, 10, 11, 11, 76]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # ---------------------------------------------------------- summary sheet
    s = wb.create_sheet("Summary")
    s["A1"] = "GANTRY BOM SUMMARY"
    s["A1"].font = Font(size=14, bold=True, color=INK)
    s["A3"] = "Group"; s["B3"] = "Subtotal"
    for c in ("A3", "B3"):
        s[c].font = Font(bold=True, color="FFFFFF")
        s[c].fill = HDR_FILL
    rr = 4
    for grp in GROUP_ORDER:
        if grp in group_totals:
            s.cell(rr, 1, grp)
            v = s.cell(rr, 2, group_totals[grp])
            v.number_format = '"$"#,##0.00'
            rr += 1
    s.cell(rr, 1, "TOTAL").font = Font(bold=True, size=12)
    tv = s.cell(rr, 2, grand)
    tv.number_format = '"$"#,##0.00'
    tv.font = Font(bold=True, size=12, color="B91C1C")
    rr += 2
    hw = grand - group_totals.get("Robot arm", 0.0) - 217.00
    s.cell(rr, 1, f"Biggest single line is the arm at $759. Everything else except the "
                  f"arm and the $217 safety relay comes to ${hw:,.2f}.").font = \
        Font(size=10, color="5B6770")
    s.column_dimensions["A"].width = 30
    s.column_dimensions["B"].width = 16

    wb.save(path)
    return grand, group_totals


if __name__ == "__main__":
    out = "Maag_Gantry_BOM_RevD.xlsx"
    total, groups = build(out)
    print(f"saved {out}")
    for g, v in groups.items():
        print(f"  {g:<18} ${v:>9,.2f}")
    print(f"  {'TOTAL':<18} ${total:>9,.2f}")
