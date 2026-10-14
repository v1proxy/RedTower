#!/usr/bin/env python3
"""Build the Rev D BOM: every line carries a real buying link checked on 2026-10-03.

Rev C priced the build from vendor pages read in September. Rev D re-checked every line
against the live stores, which turned up parts that do not exist as specified, prices that
moved, and one electrical mismatch that would have stopped the lights working. The
confidence column says how far to trust each link:

    Verified   the product page was opened and the part and price read off it
    Search     the vendor's own search, pre-filled: the part is real, the page was not
               readable from here (Amazon and DigiKey render prices in JavaScript)
    Alternate  the specified part does not exist or is unavailable, this is the substitute
    Quote      custom work, priced only after uploading geometry
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

SRC, OUT = "greenhouse_BOM_revC.xlsx", "/home/claude/greenhouse_BOM_revE.xlsx"

HEAD = PatternFill("solid", fgColor="1F3A2E")
BAND = PatternFill("solid", fgColor="EEF3EF")
WARN = PatternFill("solid", fgColor="FCE8E6")
ALT_F = PatternFill("solid", fgColor="FFF6E0")
TITLE = Font(bold=True, size=14, color="1F3A2E")
HF = Font(bold=True, color="FFFFFF", size=10)
LINK = Font(color="0B6BCB", underline="single", size=10)
THIN = Side(style="thin", color="C8D3CC")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

# id, subsystem, item, manufacturer, part no, vendor, url, qty, unit, unit price, confidence, note
R = [
 # ---------------------------------------------------------------- Structure
 ("G001", "Structure", "Profile 40-4040, cut to length", "80/20 Inc", "40-4040", "8020.net",
  "https://8020.net/40-4040.html", 1221, "in", 1.12, "Verified",
  "31 m from the cut list including 5 % waste. Price confirmed at $0.0441/mm."),
 ("G001b", "Structure", "Cut charge, 40-4040", "80/20 Inc", "Machining: cut to length", "8020.net",
  "https://8020.net/40-4040.html", 31, "cut", 3.00, "Verified",
  "$3.00 a cut, 31 pieces. Not in Rev C, and it is not optional if you order cut."),
 ("G002", "Structure", "Profile 20-2020 for door frames", "80/20 Inc", "20-2020", "8020.net",
  "https://8020.net/20-2020.html", 473, "in", 0.333, "Verified",
  "12 m. Rev C carried $0.55/in, the real price is $0.333."),
 ("G002b", "Structure", "Cut charge, 20-2020", "80/20 Inc", "Machining: cut to length", "8020.net",
  "https://8020.net/20-2020.html", 16, "cut", 3.00, "Verified", "16 door members."),
 ("G003", "Structure", "ALTERNATE: generic 4040 V-groove, 1 m", "ZYLtech", "4040 V-groove 1 m", "zyltech.com",
  "https://www.zyltech.com/zyltech-4040-v-groove-extrusion-1m/", 0, "m", 37.74, "Alternate",
  "ZYLtech stocks V-groove only, not plain T-slot, and at $37.74/m it no longer undercuts 80/20. "
  "The cut-it-yourself saving Rev C promised is gone. Set Qty to use it."),
 ("G004", "Structure", "Corner brackets, 40 series", "80/20 Inc", "40-4302", "8020.net",
  "https://8020.net/40-4302.html", 64, "pc", 5.31, "Verified",
  "Bracket only. Fastener hardware is the next two lines."),
 ("G005", "Structure", "T-nuts, slide-in M8", "80/20 Inc", "3838", "8020.net",
  "https://8020.net/3838.html", 250, "pc", 0.53, "Alternate",
  "The true drop-in nut 40-1988 is $4.10 each, which would add $890. Slide-in works if you "
  "thread it in before closing a frame; drop-in is what you want for later changes."),
 ("G006", "Structure", "End-tap service M8", "80/20 Inc", "Machining: end tap M8x1.25", "8020.net",
  "https://8020.net/40-4040.html", 54, "pc", 3.00, "Verified", "Single-hole end tap, ordered on the profile page."),
 ("G007", "Structure", "Leveling feet M8", "80/20 Inc", "65-2195", "8020.net",
  "https://8020.net/65-2195.html", 4, "pc", 2.60, "Verified",
  "Economy foot. The deluxe 65-2212 is $26.64 and not worth it here."),
 ("G008", "Structure", "Polycarbonate glazing, clear", "Falken Design", "PC-1/8-4896", "Home Depot",
  "https://www.homedepot.com/p/Falken-Design-48-in-x-96-in-x-1-8-in-Clear-Polycarbonate-Sheet-PC-1-8-4896/316713219",
  3, "sheet", 166.99, "Alternate",
  "Palram PALSUN 4 mm is not sold online in 48x96. This is 1/8 in (3.2 mm). Check the slot "
  "gasket suits 3 mm rather than 4 mm before ordering."),
 ("G009", "Structure", "ACM panel 3 mm white", "C-TEK", "W01-06884", "Curbell Plastics",
  "https://www.curbellplastics.com/product/w01-06884/", 2, "sheet", 64.64, "Alternate",
  "Falken does not make white ACM in 48x96. Cheaper than the Rev C estimate."),
 ("G010", "Structure", "Panel seal gasket, slot 8", "80/20 Inc", "40-2115", "8020.net",
  "https://8020.net/40-2115.html", 40, "m", 2.81, "Verified",
  "Economy gasket. Confirm the panel thickness it grips once you settle G008."),
 ("G011", "Structure", "Door hinges, 40 series", "80/20 Inc", "40-2840", "8020.net",
  "https://8020.net/40-2840.html", 8, "pc", 23.15, "Verified",
  "Lift-off hinge, right hand. 65 % over the Rev C estimate, the single biggest price miss."),
 ("G012", "Structure", "Magnetic catches", "80/20 Inc", "65-2090", "8020.net",
  "https://8020.net/65-2090.html", 4, "pc", 12.07, "Verified", "Catch only."),
 ("G012b", "Structure", "Door pull handles", "80/20 Inc", "40-2760", "8020.net",
  "https://8020.net/40-2760.html", 4, "pc", 6.53, "Verified", "Pairs with the catch above."),
 ("G013", "Structure", "Drip trays, laser cut and bent", "SendCutSend", "5052 aluminium 0.063 in, 1317x203x25",
  "sendcutsend.com", "https://app.sendcutsend.com/customer", 3, "pc", 62.00, "Quote",
  "They stock 0.063 in (1.6 mm), not 1.5 mm. Price is quoted on upload, so the figure is still the estimate."),
 ("G014", "Structure", "Base drip pan", "SendCutSend", "5052 aluminium 0.063 in, 1317x377x25",
  "sendcutsend.com", "https://app.sendcutsend.com/customer", 1, "pc", 85.00, "Quote", "Same, quote on upload."),
 ("G015", "Structure", "Anti-tip wall brackets", "Simpson Strong-Tie", "A34", "Home Depot",
  "https://www.homedepot.com/p/100375340", 8, "pc", 0.83, "Verified", "Add lag screws, about $12."),

 # ---------------------------------------------------------------- Lighting & air
 ("G016", "Lighting & air", "LED bar, LM301H class 560 mm", "Kingbrite", "W55 560 mm LM301H + 660 nm",
  "Kingbrite (AliExpress)", "https://www.aliexpress.com/item/1005002877218762.html", 6, "pc", 23.98, "Search",
  "CHECK BEFORE ORDERING DRIVERS: the seller does not publish forward voltage or current. "
  "If it is really a 70 W bar its Vf is nearer 60 V than 36 V, which changes how many go in series."),
 ("G017", "Lighting & air", "ALTERNATE: quantum board", "Horticulture Lighting Group", "QB120 V2", "Amazon",
  "https://www.amazon.com/Horticulture-Lighting-Group-Quantum-Boards/dp/B07TMNVM9V", 0, "pc", 59.00, "Alternate",
  "hlgshop.com no longer exists. HLG publishes real numbers for this board, 21.8 to 22.64 V at "
  "1050 to 2800 mA, which is why it is the safer choice if the Kingbrite seller will not confirm Vf."),
 ("G018", "Lighting & air", "LED driver Tier A", "Mean Well", "HLG-80H-C700B", "TRC Electronics",
  "https://www.trcelectronics.com/products/mean-well-hlg-80h-c700b", 1, "pc", 57.02, "Alternate",
  "HLG-80H-C1050B does not exist: that family is made in 350 and 700 mA only. This is 700 mA, 84 to 129 V."),
 ("G019", "Lighting & air", "LED driver Tiers B and C", "Mean Well", "HLG-60H-C700B", "Jameco",
  "https://www.jameco.com/z/HLG-60H-C700B-MEAN-WELL-700mA-50V-100V-70W-Constant-Current-LED-Driver-Power-Supply-3-in-1-Dimming_2172201.html",
  2, "pc", 36.90, "Verified", "700 mA, 50 to 100 V. Three week lead time, so order these early."),
 ("G020", "Lighting & air", "Driver AC relay module, 3.3 V coil", "Generic", "1-channel 10 A opto-isolated relay",
  "Walmart", "https://www.walmart.com/ip/17537422620", 3, "pc", 9.99, "Verified", "3 V / 3.3 V coil, 10 A contacts."),
 ("G021", "Lighting & air", "Dim interface parts", "Diotec", "2N2222A + 1 k resistor", "DigiKey",
  "https://www.digikey.com/en/products/detail/diotec-semiconductor/2N2222A/13164037", 3, "set", 2.00, "Search",
  "DigiKey renders price in JavaScript. Jameco has the 2N2222A at $1.49."),
 ("G022", "Lighting & air", "Exhaust fan 120 mm", "Noctua", "NF-F12 PWM", "Newegg (Noctua direct)",
  "https://www.newegg.com/p/N82E16835608026", 2, "pc", 21.95, "Alternate", "Sold by Noctua, in stock. Cheaper than Rev C."),
 ("G023", "Lighting & air", "Circulation fan 80 mm", "Noctua", "NF-A8 PWM", "Newegg (Noctua direct)",
  "https://www.newegg.com/noctua-nf-a8-pwm-case-fan/p/N82E16835608069", 3, "pc", 17.95, "Alternate",
  "Noctua direct, plus about $7 shipping."),
 ("G024", "Lighting & air", "Fan grills, 120 and 80 mm", "Noctua", "NA-FG1-12 / NA-FG1-8", "Newegg",
  "https://www.newegg.com/Noctua-Case-Accessories/BrandSubCat/ID-12454-255", 2, "set", 13.90, "Verified",
  "NA-FG1-8 Sx2 at $12.90, NA-FG1-12 Sx2 at $14.90, both in stock."),
 ("G025", "Lighting & air", "Humidifier, mechanical dial", "Crane", "EE-5301 Drop", "eBay",
  "https://www.ebay.com/p/2164340591", 1, "pc", 39.99, "Alternate",
  "The Levoit Classic 200 fails the requirement: its manual confirms a tap button that defaults "
  "to low mist, so it will not resume after a power cut. This one has a real mechanical dial."),
 ("G026", "Lighting & air", "Humidifier duct, 50 mm", "Rubber-Cal", "Aluminum Flex 400, 2 in x 5 ft", "Home Depot",
  "https://homedepot.com/p/Rubber-Cal-Aluminum-Flex-400-Hi-Temp-Flexible-Ventilation-Duct-Hose-2-in-ID-x-5-ft-01-W145-2/322306073",
  1, "pc", 18.00, "Verified", "Its relay is the same module as G020."),
 ("G027", "Lighting & air", "Intake dust filter 120 mm", "DEMCiflex", "Magnetic dust filter 120 mm", "MemoryC",
  "https://www.memoryc.com/64778-demciflex-120mm-square-computer-dust-filter.html", 1, "pc", 18.41, "Alternate",
  "demciflex.com is unreachable. This reseller has 9 in stock, about 12 days."),

 # ---------------------------------------------------------------- Irrigation
 ("G028", "Irrigation", "Reservoir, low profile", "Class A Customs", "T-0700, 7 gal", "classacustoms.com",
  "https://www.classacustoms.com/7-Gallon-Fresh-Gray-Water-Holding-Tank-T-0700_p_43.html", 1, "pc", 79.00, "Alternate",
  "No 8 gal tank is made. This is 7 gal (26.5 L) at 23.75 x 7 x 9.75 in. The bay has 225 mm of "
  "clear height, so the 7 in face has to sit vertical. Confirm before ordering."),
 ("G029", "Irrigation", "Pump 24 V diaphragm", "SEAFLO", "SFDP2-012-035-21", "Hydrobuilder",
  "https://hydrobuilder.com/products/seaflo-21-series-diaphragm-water-pump-24vdc-1-2-gpm", 1, "pc", 34.99, "Verified",
  "1.2 GPM, 35 psi. Backordered, ships in 2 to 3 days."),
 ("G030", "Irrigation", "Pressure regulator, 25 psi", "DIG", "3/4 in GHT 25 psi", "Drip Depot",
  "https://www.dripdepot.com/three-quarter-inch-ght-pressure-regulator-psi-25-psi", 1, "pc", 5.44, "Alternate",
  "No 1/4 in regulator exists in drip irrigation. Fit this at the pump outlet, then reduce to 1/4 in."),
 ("G031", "Irrigation", "Inline filter, 150 mesh", "DIG", "3/4 in MPT Y-filter 150 mesh", "Drip Depot",
  "https://www.dripdepot.com/heavy-duty-y-filter-three-quarter-inch-mpt-filtration-150-mesh", 1, "pc", 18.47, "Alternate",
  "Same reason: 150 mesh is made in 3/4 in only. Goes upstream of the regulator."),
 ("G032", "Irrigation", "Check valve", "Hendrickson Bros", "1/2 in FPT x MPT check valve", "Drip Depot",
  "https://www.dripdepot.com/product/hendrickson-bros-half-inch-check-valve", 1, "pc", 5.72, "Alternate",
  "Opens at 17 psi. No 1/4 in check valve is stocked."),
 ("G033", "Irrigation", "Zone solenoid valve 24 V DC", "U.S. Solid", "JFSV00052", "ussolid.com",
  "https://ussolid.com/products/u-s-solid-electric-solenoid-valve-1-4-24v-dc-solenoid-valve-brass-body-normally-closed-viton-seal-html",
  3, "pc", 15.94, "Verified", "1/4 in brass, normally closed, Viton. 1123 in stock, under the estimate."),
 ("G034", "Irrigation", "PC emitters 0.5 GPH", "Netafim", "Woodpecker Jr CNL 0.5 GPH", "Drip Depot",
  "https://www.dripdepot.com/woodpecker-jr-cnl-dripper-flow-rate-half-gph", 40, "pc", 0.25, "Verified",
  "0.5 GPH is the same as 2 L/h. Less than half the Rev C price."),
 ("G035", "Irrigation", "Tubing 1/4 in, 100 ft", "Drip Depot", "0.170 x 0.250 in poly tubing", "Drip Depot",
  "https://www.dripdepot.com/white-polyethylene-tubing-size-quarter-inch-0-170-inch-inside-diameter-by-0-250-inch-od-length-100-feet",
  1, "roll", 7.44, "Verified", "Tubing only. Stakes about $0.30 each, barbed couplings $0.65."),
 ("G035b", "Irrigation", "Stakes, tees and couplings", "Drip Depot", "assorted 1/4 in fittings", "Drip Depot",
  "https://www.dripdepot.com/drip-irrigation-fittings", 1, "kit", 30.00, "Search",
  "Budget line: 40 stakes plus tees and couplings, priced individually on the site."),
 ("G036", "Irrigation", "MOSFET driver board, 4 channel", "Generic", "IRF540 4-channel module", "Amazon",
  "https://www.amazon.com/Channel-MOSFET-Button-IRF540-Switch/dp/B07RBKTBVF", 1, "pc", 12.00, "Search",
  "HiLetgo branding unconfirmed on this listing. Any 4-channel IRF540 module works."),

 # ---------------------------------------------------------------- Biosensing
 ("G037", "Biosensing", "Soil moisture probe, capacitive", "DFRobot", "SEN0193", "DigiKey",
  "https://www.digikey.com/en/products/detail/dfrobot/SEN0193/6588605", 30, "pc", 7.90, "Search",
  "SEN0193 is the corrosion-resistant v1. The waterproof version is a different part, SEN0308, "
  "and is worth considering given these sit in wet soil for years."),
 ("G038", "Biosensing", "ADC, 4-channel 16-bit", "Adafruit", "1085 (ADS1115)", "Adafruit",
  "https://www.adafruit.com/product/1085", 10, "pc", 14.95, "Verified", "In stock."),
 ("G039", "Biosensing", "Air temperature and humidity", "Adafruit", "5665 (Sensirion SHT45)", "Adafruit",
  "https://www.adafruit.com/product/5665", 3, "pc", 12.50, "Verified", "In stock. Drives the VPD calculation."),
 ("G040", "Biosensing", "CO2 sensor", "Adafruit", "5190 (Sensirion SCD-41)", "Adafruit",
  "https://www.adafruit.com/product/5190", 1, "pc", 49.95, "Verified", "True CO2, not a VOC proxy. In stock."),
 ("G041", "Biosensing", "Spectral light sensor", "Adafruit", "4698 (AS7341)", "Adafruit",
  "https://www.adafruit.com/product/4698", 3, "pc", 18.95, "Verified", "Now $18.95, up from the $15.95 in Rev C."),
 ("G042", "Biosensing", "Canopy IR thermometer", "SparkFun", "SEN-10740 (MLX90614)", "SparkFun",
  "https://www.sparkfun.com/sparkfun-ir-thermometer-evaluation-board-mlx90614.html", 3, "pc", 30.95, "Alternate",
  "Adafruit 1747 and 1748 are both discontinued. This feeds leaf VPD, so it is not optional."),
 ("G043", "Biosensing", "Reservoir level, time of flight", "Adafruit", "3317 (VL53L0X)", "Adafruit",
  "https://www.adafruit.com/product/3317", 1, "pc", 14.95, "Verified", "30 to 1000 mm. In stock."),
 ("G044", "Biosensing", "Water temperature probe", "Adafruit", "381 (DS18B20 waterproof)", "Adafruit",
  "https://www.adafruit.com/product/381", 1, "pc", 9.95, "Verified", "In stock."),
 ("G045", "Biosensing", "Low-water float switch", "Madison", "M8000 normally open", "madisonsensor.com",
  "https://www.madisonsensor.com/std-min-lls-pp-flt-pp-stm-normally-open", 1, "pc", 27.00, "Verified",
  "Direct from Madison. $27, not the $18 in Rev C."),
 ("G046", "Biosensing", "Leak probe modules", "Generic", "Water leak sensor, digital out", "Amazon",
  "https://www.amazon.com/s?k=HiLetgo+rain+water+sensor+module", 4, "pc", 5.00, "Search",
  "Commodity module, many sellers, no single ASIN worth pinning."),
 ("G047", "Biosensing", "Door reed switches", "Honeywell", "7939WG-WH", "Amazon",
  "https://www.amazon.com/s?k=Honeywell+7939WG-WH", 4, "pc", 6.00, "Search",
  "Real part, but special order at the distributors, 0 to 1 week."),
 ("G048", "Biosensing", "I/O expander", "Adafruit", "5346 (MCP23017)", "Adafruit",
  "https://www.adafruit.com/product/5346", 1, "pc", 5.95, "Verified", "$5.95, cheaper than the Rev C estimate."),
 ("G049", "Biosensing", "STEMMA QT cable set", "Adafruit", "4210 / 4399", "Adafruit",
  "https://www.adafruit.com/product/4210", 12, "pc", 0.95, "Verified", "100 mm and 50 mm, both $0.95."),
 ("G050", "Biosensing", "Conformal coating", "MG Chemicals", "422B-340G", "Master Electronics",
  "https://www.masterelectronics.com/en/mg-chemicals/422b340g-36085085.html", 1, "can", 48.10, "Alternate",
  "422B is an acrylic-silicone blend and is manufacturer-discontinued, though 683 remain in stock. "
  "MG 419D is their current true acrylic if you would rather buy something still in production."),

 # ---------------------------------------------------------------- Control & compute
 ("G051", "Control & compute", "PoE controller node", "Olimex", "ESP32-POE-ISO", "Olimex",
  "https://www.olimex.com/Products/IoT/ESP32/ESP32-POE-ISO/", 5, "pc", 26.50, "Verified",
  "EUR 24.95 each, EUR 22.46 at qty 10. Priced here at about $26.50 including the rate."),
 ("G052", "Control & compute", "PoE switch, VLAN capable", "TP-Link", "TL-SG108PE", "Connection",
  "https://www.connection.com/product/tp-link-8-port-gigabit-easy-smart-switch-w-4xpoe/tl-sg108pe/31582541",
  1, "pc", 89.99, "Verified", "In stock, 1 to 2 days. Amazon is likely cheaper if you check."),
 ("G053", "Control & compute", "Compute node", "NVIDIA", "Jetson Orin Nano Super Dev Kit", "Arrow",
  "https://www.arrow.com/en/products/945-13766-0005-000/nvidia", 1, "pc", 249.00, "Verified", "Matches the estimate."),
 ("G054", "Control & compute", "NVMe SSD 500 GB", "Crucial", "CT500P3SSD8", "Amazon",
  "https://www.amazon.com/s?k=Crucial+P3+500GB+CT500P3SSD8", 1, "pc", 45.00, "Search",
  "Avoid the Newegg listing: third-party import at $145."),
 ("G055", "Control & compute", "Overview camera", "Arducam", "UB020201", "Arducam",
  "https://www.arducam.com/ub020201-arducam-1080p-low-light-wdr-usb-camera-module-with-metal-case-2mp-1-2-8-cmos-imx291-160-degree-ultra-wide-angle-mini-uvc-webcam-board-with-microphones.html",
  1, "pc", 45.00, "Search", "The part number is UB020201, not B020201 as Rev C had it."),
 ("G056", "Control & compute", "Wrist depth camera", "Intel RealSense", "D405", "store.realsenseai.com",
  "https://store.intelrealsense.com/buy-intel-realsense-depth-camera-d405.html", 1, "pc", 294.00, "Verified",
  "Already bought. SparkFun has retired theirs, so the official store is the route now."),
 ("G057", "Control & compute", "High-flex USB-C cable, 2 m", "Generic", "USB 3.1 Gen1 high flex", "Amazon",
  "https://www.amazon.com/s?k=high+flex+USB-C+3.1+Gen1+cable+2m+robotic", 1, "pc", 24.00, "Search",
  "It rides the cable chain, so insist on a continuous-flex rating, not just 'braided'."),
 ("G058", "Control & compute", "Patch cables Cat6A", "Monoprice", "SlimRun Cat6A 3 ft, 10 pack", "Monoprice",
  "https://www.monoprice.com/product?p_id=15156", 1, "pack", 32.00, "Search",
  "SlimRun is a Cat6A line, not Cat6. A 10 pack covers the 8 runs."),
 ("G059", "Control & compute", "Electronics enclosure, IP65", "Polycase", "ZQ-121004", "polycase.com",
  "https://www.polycase.com/zq-series", 1, "pc", 47.63, "Alternate",
  "There is no YQ series. ZQ-121004 is 305 x 254 x 132 mm, slightly larger than Rev C assumed."),

 # ---------------------------------------------------------------- Motion
 ("G060", "Motion", "C-Beam linear rail, X axis", "OpenBuilds", "05-LP, 1500 mm", "us.openbuilds.com",
  "https://us.openbuilds.com/c-beam-linear-rail/", 1, "pc", 72.00, "Search",
  "In stock. The 1500 mm price sits behind a JavaScript dropdown, so the estimate stands."),
 ("G061", "Motion", "C-Beam linear rail, Z mast", "OpenBuilds", "05-LP, 1500 mm", "us.openbuilds.com",
  "https://us.openbuilds.com/c-beam-linear-rail/", 1, "pc", 72.00, "Search", "Same SKU, order quantity 2."),
 ("G062", "Motion", "Gantry set, XLarge", "OpenBuilds", "2672-Set", "us.openbuilds.com",
  "https://us.openbuilds.com/xlarge-c-beam-gantry-kit/", 2, "set", 35.99, "Verified",
  "Includes 4 Xtreme Solid V wheels. Down from $59.99."),
 ("G063", "Motion", "Belt and pinion drive, X", "OpenBuilds", "NEMA 17 Belt & Pinion Actuator", "us.openbuilds.com",
  "https://us.openbuilds.com/nema-17-belt-and-pinion-bundle/", 1, "set", 87.99, "Alternate",
  "The standalone drive set was renamed and currently shows unavailable. Check stock before relying on it."),
 ("G063b", "Motion", "Timing belt", "OpenBuilds", "3GT (GT2-3M) 5 mm", "us.openbuilds.com",
  "https://us.openbuilds.com/3gt-gt2-3m-timing-belt/", 10, "ft", 3.49, "Verified",
  "OpenBuilds does not sell a 9 mm GT3 belt. This is 5 mm wide, which is adequate for this load."),
 ("G064", "Motion", "Lead screw 8 mm, Z", "OpenBuilds", "25-LP, 1400 mm", "us.openbuilds.com",
  "https://us.openbuilds.com/8mm-metric-lead-screw/", 1, "pc", 35.00, "Search", "Length priced in a dropdown."),
 ("G064b", "Motion", "Anti-backlash nut block", "OpenBuilds", "1055", "us.openbuilds.com",
  "https://us.openbuilds.com/anti-backlash-nut-block-for-8mm-metric-lead-screw/", 1, "pc", 9.99, "Verified",
  "Tr8x8(p2) acme, in stock."),
 ("G064c", "Motion", "Thrust bearing", "OpenBuilds", "3030", "us.openbuilds.com",
  "https://us.openbuilds.com/thrust-bearing/", 2, "pc", 1.99, "Alternate",
  "OpenBuilds sells no 'bearing block' as such. This is the part that takes the axial load."),
 ("G064d", "Motion", "Shaft coupler 5 to 8 mm", "OpenBuilds", "222", "us.openbuilds.com",
  "https://us.openbuilds.com/5mm-8mm-flexible-coupling/", 1, "pc", 6.99, "Verified", "In stock."),
 ("G065", "Motion", "Stepper, Z, with brake", "StepperOnline", "23HS22-4004D-B280", "omc-stepperonline.com",
  "https://www.omc-stepperonline.com/nema-23-stepper-motor-1-2nm-169-93oz-in-with-24v-4-5w-electromagnetic-brake-23hs22-4004d-b280",
  1, "pc", 36.07, "Verified",
  "Part number unchanged, 200 in stock. The brake is what holds the mast up when power drops."),
 ("G066", "Motion", "Stepper, X", "StepperOnline", "NEMA 23, 2.8 A", "omc-stepperonline.com",
  "https://www.omc-stepperonline.com/nema-23-stepper-motor", 1, "pc", 25.00, "Search",
  "23HS22-2804S returns no hits on their search and has probably been renamed. Pick an equivalent "
  "NEMA 23 at 2.8 A from this category."),
 ("G067", "Motion", "Motion controller", "Elecrow", "4-axis FluidNC controller, 4x TMC2209", "elecrow.com",
  "https://www.elecrow.com/4x-cnc-controller-integrated-esp32-and-tmc2209.html", 1, "pc", 49.00, "Alternate",
  "The V1E Jackpot3 is sold out everywhere. This is Bart Dring's board too, runs the same FluidNC, "
  "4 axes rather than 6, which is more than this gantry needs."),
 ("G068", "Motion", "Limit switch kit", "OpenBuilds", "2805-Kit", "us.openbuilds.com",
  "https://us.openbuilds.com/xtension-limit-switch-kit", 4, "pc", 7.99, "Verified", "In stock."),
 ("G069", "Motion", "Cable chain", "Igus", "E14.1.028.0", "igus.com",
  "https://www.igus.com/product/series-E14?c=US&l=en", 2, "run", 82.00, "Verified",
  "$1.22 a link, so about $82 for a 1.5 m run. Rev C carried $26, which was well short."),
 ("G070", "Motion", "High flex cable set", "Igus", "chainflex motor + Ethernet + 12 V", "igus.com",
  "https://www.igus.com/cables/cable-price-check", 1, "set", 48.00, "Quote",
  "chainflex is quote-only. The G057 note applies here too: continuous-flex rating or nothing."),
 ("G071", "Motion", "Arm mounting plate", "SendCutSend", "6061-T6, 0.250 in", "sendcutsend.com",
  "https://app.sendcutsend.com/customer", 1, "pc", 42.00, "Quote",
  "They stock 0.250 in (6.35 mm), not 6.0 mm. Measure the myCobot base before uploading."),

 # ---------------------------------------------------------------- Power & safety
 ("G072", "Power & safety", "Inline GFCI cord, MANUAL reset", "Woodhead", "15050-3TTM", "Platt / Grainger",
  "https://www.amazon.com/s?k=Woodhead+15050-3TTM+inline+GFCI+manual+reset", 1, "pc", 80.70, "Search",
  "Tower 30438006 is not in any catalogue. Manual reset is the point: an auto-reset unit "
  "re-energises the cabinet by itself once a fault clears, which is the wrong behaviour with a "
  "robot inside. $80.70 seen at Platt, 3 in stock; search the part number to buy."),
 ("G072b", "Power & safety", "ALTERNATE: auto-reset GFCI cord", "Tower Manufacturing", "30438024", "Empire Rigging",
  "https://empirerigging.com/tower-manufacturing-30438024", 0, "pc", 31.80, "Alternate",
  "Half the price and verified in stock, but auto-reset. Listed only so the trade-off is visible. "
  "Do not set Qty on this one unless you have decided to accept that behaviour."),
 ("G073", "Power & safety", "Fused IEC inlet with switch", "Schurter", "KD14-1101-151", "DigiKey",
  "https://www.digikey.com/en/products/detail/schurter-inc/KD14-1101-151/569952", 1, "pc", 14.00, "Search",
  "C14 inlet, 2-pole fuseholder, 2-pole rocker, 10 A."),
 ("G074", "Power & safety", "24 V power supply, 350 W", "Mean Well", "LRS-350-24", "DigiKey",
  "https://www.digikey.com/en/products/detail/mean-well-usa-inc/LRS-350-24/7705034", 1, "pc", 45.00, "Search",
  "DigiKey 1866-3346-ND. HitLights has the same part at $57.95 in stock if DigiKey is slow."),
 ("G075", "Power & safety", "24 V to 12 V converter", "Mean Well", "DDR-15G-12", "DigiKey",
  "https://www.digikey.com/en/products/detail/mean-well-usa-inc/DDR-15G-12/8681196", 1, "pc", 26.00, "Search",
  "Watch availability: one distributor shows a 16 week factory lead. This feeds every 12 V fan."),
 ("G076", "Power & safety", "Wago 221 lever connectors", "Wago", "887-0408 combo kit", "Home Depot",
  "https://www.homedepot.com/p/WAGO-221-Lever-Nut-Combo-Kit-40-pack-887-0408/336511597", 1, "kit", 31.47, "Verified",
  "Genuine Wago, 40 pieces, mixed 2/3/5 way."),
 ("G076b", "Power & safety", "DIN rail carriers for 221", "Wago", "221-500", "DigiKey",
  "https://www.digikey.com/en/products/detail/wago-corporation/221-500/13549311", 8, "pc", 2.50, "Search",
  "Each carrier holds four connectors."),
 ("G077", "Power & safety", "Fuse block, 6 circuit", "Blue Sea Systems", "5025", "Thorne Bros",
  "https://thornebros.com/products/blue-sea-systems-st-blade-fuse-block-6-circuits-with-negative-bus-and-cover-5025",
  1, "pc", 59.99, "Alternate",
  "5045 is a 4-circuit block, not 6. 5025 is 6 circuits with a negative bus and a cover, which is "
  "what a cabinet with a shared 24 V return actually needs."),
 ("G078", "Power & safety", "E-stop head, 40 mm mushroom", "Eaton", "M22-PV", "DigiKey",
  "https://www.digikey.com/en/products/detail/eaton-electrical/M22-PV/25845301", 1, "pc", 30.59, "Search",
  "Maintained, twist to release. Price from Zoro."),
 ("G078b", "Power & safety", "E-stop contact block, 1 NC", "Eaton", "M22-K01", "DigiKey",
  "https://www.digikey.com/en/products/detail/eaton-electrical/M22-K01/25845193", 2, "pc", 12.59, "Search",
  "BUY TWO. The safety relay is dual channel and needs two independent NC contacts."),
 ("G078c", "Power & safety", "E-stop mounting collar", "Eaton", "M22-A", "DigiKey",
  "https://www.digikey.com/en/products/detail/eaton-electrical/M22-A/25844210", 1, "pc", 6.00, "Search",
  "Carries the contact blocks. Some M22-PV listings include it, so check before buying separately."),
 ("G079", "Power & safety", "Safety relay, dual channel", "Omron", "G9SE-201 24 VDC", "DigiKey",
  "https://www.digikey.com/en/products/detail/omron-automation-and-safety/G9SE-201/7495167", 1, "pc", 217.00, "Verified",
  "Still current, not superseded. $217 at RAMCO with 5 in stock, against the $152 Rev C assumed."),
 ("G080", "Power & safety", "Energy meter", "Peacefair", "PZEM-004T v3.0 + CT", "ShillehTek",
  "https://shillehtek.com/products/pzem-004t-ac-energy-meter-current-transformer", 1, "pc", 14.99, "Alternate",
  "US seller, ships same day. Confirm it is the 100 A CT variant."),
 ("G081", "Power & safety", "Ferrule kit with crimp tool", "Newhouse Electric", "FTK1200", "Home Depot",
  "https://www.homedepot.com/p/NEWHOUSE-ELECTRIC-Ferrule-Crimping-Tool-Kit-with-Wire-Crimper-Tool-Wire-Ferrule-Container-and-1-200-Electrical-Wire-Connectors-FTK1200/325371315",
  1, "kit", 36.47, "Verified", "1200 ferrules, tool and case."),
 ("G081b", "Power & safety", "Cable glands PG9", "Generic", "PG9 nylon gland", "Amazon",
  "https://www.amazon.com/s?k=PG9+cable+gland+nylon", 1, "kit", 12.00, "Search", "Commodity part."),
 ("G081c", "Power & safety", "Hook-up wire 18 to 14 AWG", "Generic", "stranded wire kit", "Amazon",
  "https://www.amazon.com/s?k=18+AWG+stranded+hookup+wire+kit", 1, "kit", 25.00, "Search", "Commodity part."),
 ("G081d", "Power & safety", "Wire label kit", "Generic", "self-laminating labels", "Amazon",
  "https://www.amazon.com/s?k=self+laminating+wire+label+kit", 1, "kit", 15.00, "Search",
  "Worth doing properly: 40-odd conductors land in one enclosure."),

 # ---------------------------------------------------------------- Robot arm
 ("G082", "Robot arm", "Robot arm, 6 DOF", "Elephant Robotics", "myCobot 280 Pi", "Elephant Robotics Americas",
  "https://americas.shop.elephantrobotics.com/products/mycobot-280-pi-worlds-smallest-and-lightest-six-axis-collaborative-robot",
  1, "pc", 759.00, "Verified", "In stock, on sale from $799."),
 ("G083", "Robot arm", "Gripper, adaptive", "Elephant Robotics", "myCobot Adaptive Gripper", "Elephant Robotics Americas",
  "https://americas.shop.elephantrobotics.com/collections/end-effectors/products/adaptive-gripper",
  1, "pc", 129.99, "Verified",
  "In stock, and the page lists the 280 Pi explicitly, so no adapter plate. Cheaper than the Rev C placeholder."),
 ("G084", "Robot arm", "Second arm (optional)", "Elephant Robotics", "myCobot 280 Pi", "Elephant Robotics Americas",
  "https://americas.shop.elephantrobotics.com/products/mycobot-280-pi-worlds-smallest-and-lightest-six-axis-collaborative-robot",
  0, "pc", 759.00, "Alternate", "Not in the total. Set Qty to 1 to add it."),

 # ---------------------------------------------------------------- Consumables & plants
 ("G085", "Consumables", "Nursery pots, 4.5 in square deep", "HC Companies", "Square Black Form Pot, 4.5 Deep",
  "Greenhouse Megastore", "https://www.greenhousemegastore.com/square-black-form-pots-cn--sqv",
  2, "pack of 15", 6.00, "Search",
  "THE MISSING LINE: Rev A through D had no pots at all. 30 pots covers 27 plants plus 3 spares. "
  "9 per tier across the 1317 mm plant zone is a 146 mm pitch, so a 114 mm pot leaves about 32 mm "
  "between rims, which is the clearance the arm wants. Black matte PP is also the right surface for "
  "the D405: no specular highlights to break stereo depth, and near-zero excess green so the pot "
  "wall rejects cleanly in the plant mask. The listing does not publish the depth, so confirm you "
  "are getting the 4.5 in DEEP form and not the shallow one."),
 ("G085b", "Consumables", "ALTERNATE: pots, 5.125 in square x 6 in", "True Leaf Market",
  "5 in square heavy duty reusable", "trueleafmarket.com",
  "https://trueleafmarket.com/products/plastic-nursery-pots-5-inch-square-heavy-duty-reusable",
  0, "pack of 32", 47.99, "Alternate",
  "Dimensions published and verified: 5.125 in top, 3.75 in base, 6 in tall, about 1.9 L. More root "
  "volume, but 130 mm rims on a 146 mm pitch leaves only 16 mm of gap, and 152 mm of pot eats the "
  "canopy headroom on Tiers B and C, which have only 432 mm between levels. Set Qty to 1 to use it."),
 ("G086", "Consumables", "Growing medium, washed coco/perlite 70/30", "FloraFlex",
  "Washed 50L Loosefill 70/30", "floraflex.com",
  "https://www.floraflex.com/products/washed-50l-loosefill-bag-70-30-coco-perlite",
  2, "bag 50 L", 7.99, "Search",
  "Coco rather than peat on purpose: peat shrinks away from a capacitive probe as it dries and "
  "reports false dry. Washed, EC under 0.5, pH 5.5 to 6.5, no buffering needed. 27 pots at about "
  "0.9 L is 25 L, so two bags covers the fill plus one repot cycle. CAUTION: the product page shows "
  "two conflicting prices, $7.99 per unit against a $19,176 line price, so confirm in the cart."),
 ("G086b", "Consumables", "ALTERNATE: coco/perlite 70/30, 2 cu ft", "FoxFarm", "70/30 Coco Coir & Perlite",
  "HTG Supply", "https://www.htgsupply.com/?p=83028", 0, "bag 2 cu ft", 29.95, "Alternate",
  "57 L in a brand with a stable price page, if the FloraFlex listing stays broken."),
 ("G087", "Consumables", "Coco nutrient, 2 part A+B", "Generic", "coco-specific A+B, 1 L each", "Amazon",
  "https://www.amazon.com/s?k=coco+coir+nutrients+part+A+B+1L", 1, "kit", 45.00, "Search",
  "Coco holds no nutrition of its own and binds calcium and magnesium, so it needs a complete feed "
  "from day one. A coco-specific A+B already carries the extra Ca and Mg."),
 ("G087b", "Consumables", "CalMag supplement", "Generic", "Cal-Mag 1 L", "Amazon",
  "https://www.amazon.com/s?k=cal+mag+supplement+hydroponics+1L", 1, "pc", 18.00, "Search",
  "Insurance for the first few weeks while the coco finishes binding."),
 ("G088", "Biosensing", "pH and EC meter", "Generic", "combo pH/EC/TDS pen with calibration sachets",
  "Amazon", "https://www.amazon.com/s?k=ph+ec+tds+meter+hydroponics+calibration", 1, "pc", 45.00, "Search",
  "ALSO MISSING FROM REV D. You cannot run coco blind. Feed pH wants 5.8 to 6.2 and the reservoir "
  "drifts, and nothing in the sensor package reads either number: the probes measure moisture in "
  "the pot, not the solution in the tank."),
 ("G088b", "Consumables", "pH up and down", "Generic", "pH up/down pair, 500 mL", "Amazon",
  "https://www.amazon.com/s?k=ph+up+down+hydroponics+500ml", 1, "kit", 20.00, "Search",
  "Houston tap runs hard and alkaline, so expect to use the down bottle."),
 ("G089", "Consumables", "Herb seed, 9 varieties", "True Leaf Market", "culinary herb seed, individual packets",
  "trueleafmarket.com", "https://trueleafmarket.com/collections/herb-seeds", 9, "packet", 3.49, "Search",
  "Basil, parsley, cilantro, dill, thyme, oregano, sage, chives, mint. Three of each fills 27 "
  "stations. Mint will try to take the tier, so keep it in its own pot and prune hard."),
 ("G089b", "Consumables", "ALTERNATE: live herb starts", "local nursery", "4 in herb starts",
  "local", "https://www.google.com/maps/search/garden+nursery+near+me",
  0, "pc", 4.50, "Alternate",
  "Skips six weeks of germination and gives the vision stack real canopy to look at on day one, "
  "which is worth a lot while you are calibrating. Set Qty to 27 to use it."),
 ("G089c", "Consumables", "Germination plugs", "Generic", "coco or peat plugs, 50 count", "Amazon",
  "https://www.amazon.com/s?k=coco+coir+seed+starting+plugs+50", 1, "pack", 20.00, "Search",
  "Only needed if you go the seed route."),

 # ---------------------------------------------------------------- Tray drainage
 ("G090", "Irrigation", "Bulkhead drain fitting, 1/2 in", "Generic", "1/2 in NPT bulkhead, EPDM washers",
  "Amazon", "https://www.amazon.com/s?k=1%2F2+inch+bulkhead+fitting+tank+EPDM", 4, "pc", 8.00, "Search",
  "BLOCKING GAP FOUND WHILE ADDING THE POTS: nothing in Rev D takes runoff out of the drip trays. "
  "Three tier trays and the base pan each need a bulkhead at one end, with the tray shimmed about "
  "5 mm low at that end. Without it the 25 mm lip turns into a standing sump under the pots, which "
  "is root rot and a mosquito nursery in a Houston garage."),
 ("G090b", "Irrigation", "Drain tubing 1/2 in ID, 10 ft", "Generic", "1/2 in ID vinyl tubing", "Amazon",
  "https://www.amazon.com/s?k=1%2F2+inch+ID+clear+vinyl+tubing+10+ft", 1, "pc", 14.00, "Search",
  "Tier trays cascade into the base pan, base pan to a floor bucket. Do not plumb runoff back into "
  "the reservoir: coco runoff carries salts and the EC climbs every cycle."),
 ("G090c", "Irrigation", "Runoff bucket, 5 gal with lid", "Generic", "5 gal bucket and lid", "Home Depot",
  "https://www.homedepot.com/b/Paint-Paint-Tools-Buckets/N-5yc1vZcl8c", 1, "pc", 8.00, "Search",
  "Lidded, because an open bucket of nutrient runoff in a warm room grows things. The existing water "
  "leak sensor line (G074) should get one in the drip pan and one beside this bucket."),
]

CHANGES = [
 ("Consumables", "Rev D had no pots, no medium, no plants",
  "The BOM built a cabinet and a robot but never bought anything to grow in or anything to grow. "
  "Added as G085 to G089c: 30 square pots, 100 L of washed coco/perlite, a coco A+B feed, and seed "
  "or starts for 27 stations.", "Fixed"),
 ("Irrigation", "Nothing drained the drip trays",
  "Pots sit in a 25 mm-lip aluminium tray with no outlet, so every irrigation cycle leaves standing "
  "runoff under the root balls. Added bulkhead fittings, cascade tubing and a lidded catch bucket as "
  "G090 to G090c, and the trays now need a 5 mm shim at the drain end.", "Blocking"),
 ("Biosensing", "No way to read feed pH or EC",
  "Coco is an inert medium on a liquid feed, and the capacitive probes read moisture in the pot, not "
  "chemistry in the tank. Added a combo pH/EC pen and pH up/down as G088 and G088b.", "Fixed"),
 ("Consumables", "Pot size trades root volume against canopy headroom",
  "Tiers B and C have only 432 mm between levels, minus the LED bar and its gap. A 114 mm x 114 mm "
  "pot leaves about 250 mm of canopy; the 152 mm-tall 5 in pot leaves about 200 mm. Rev E carries the "
  "smaller pot and lists the taller one as the alternate.", "Decide"),
 ("Lighting", "HLG-80H-C1050B does not exist",
  "That driver family is made in 350 and 700 mA only. Swapped to HLG-80H-C700B.", "Blocking"),
 ("Lighting", "The drivers cannot light a single 36 V bar",
  "HLG-C drivers are high-voltage constant current: the 60H-C700B spans 50 to 100 V and the "
  "80H-C700B spans 84 to 129 V. One 36 V bar sits far below either floor and simply will not "
  "light. Bars have to be wired in SERIES: two at 36 V give 72 V, which suits the 60H; three "
  "give 108 V, which suits the 80H.", "Blocking"),
 ("Lighting", "Kingbrite does not publish forward voltage",
  "So the series count above cannot be fixed yet. Ask the seller for Vf and If, or switch to the "
  "HLG QB120 V2, which publishes 21.8 to 22.64 V at 1050 to 2800 mA.", "Decide"),
 ("Lighting", "The Levoit humidifier fails the always-on requirement",
  "Its manual confirms a tap button that defaults to low mist, so it does not resume after a "
  "power cut. Replaced with the Crane EE-5301, which has a mechanical dial.", "Fixed"),
 ("Power", "The cheap inline GFCI is auto-reset",
  "Auto-reset re-energises the cabinet once a fault clears, which is the wrong behaviour with a "
  "robot inside. Priced a manual-reset cordset instead, at $80.70 rather than $42.", "Fixed"),
 ("Power", "Blue Sea 5045 is a 4-circuit block, not 6",
  "Changed to 5025, 6 circuits with a negative bus and cover.", "Fixed"),
 ("Power", "The E-stop needs three part numbers, not one",
  "M22-PV head, M22-A collar, and TWO M22-K01 contact blocks to feed both channels of the safety "
  "relay. Rev C carried a single European order code.", "Fixed"),
 ("Power", "The Omron safety relay is $217, not $152", "Still current, not superseded.", "Price"),
 ("Irrigation", "No 1/4 in regulator, filter or check valve exists",
  "Drip irrigation makes these in 1/2 and 3/4 in only. All three moved to 3/4 or 1/2 in at the "
  "pump outlet, reducing to 1/4 in downstream.", "Fixed"),
 ("Irrigation", "Class A Customs makes no 8 gallon tank",
  "The T-0700 is 7 gal at 23.75 x 7 x 9.75 in. The bay has 225 mm of clear height, so the 7 in "
  "face must sit vertical. Confirm the orientation before ordering.", "Decide"),
 ("Motion", "The V1E Jackpot3 is sold out everywhere",
  "Substituted the Elecrow 4-axis FluidNC board at $49, same designer, same firmware.", "Fixed"),
 ("Motion", "Igus E14 cable chain is about $82 a run, not $26",
  "Priced at $1.22 a link for 1.5 m.", "Price"),
 ("Motion", "OpenBuilds no longer sells a standalone belt and pinion drive set",
  "It became the NEMA 17 Belt & Pinion Actuator and currently shows unavailable. There is no 9 mm "
  "GT3 belt either, only 3GT at 5 mm, which is adequate here.", "Decide"),
 ("Motion", "SendCutSend stocks 0.250 in, not 6.0 mm",
  "6.35 mm for the arm plate. Fine structurally, but it changes the screw lengths.", "Fixed"),
 ("Structure", "80/20 cut charges were missing from Rev C",
  "$3.00 a cut, 47 cuts across both profiles, so $141 that was simply absent.", "Price"),
 ("Structure", "The generic-extrusion saving has evaporated",
  "ZYLtech is now $37.74/m and V-groove only. Cutting it yourself no longer saves the $700 Rev C "
  "claimed, so order from 80/20 cut to length.", "Decide"),
 ("Structure", "80/20 hinges are $23.15, not $14", "The largest single price miss in the structure group.", "Price"),
 ("Structure", "Palram PALSUN 4 mm is not sold online in 48x96",
  "Nearest stocked clear polycarbonate is 1/8 in (3.2 mm). Check the slot gasket grips 3 mm.", "Decide"),
 ("Biosensing", "Adafruit discontinued both MLX90614 breakouts",
  "Moved to the SparkFun SEN-10740 at $30.95. Leaf VPD depends on it.", "Fixed"),
 ("Biosensing", "MG 422B is manufacturer-discontinued",
  "Stock remains. MG 419D is their current acrylic if you prefer something in production.", "Decide"),
 ("Compute", "Polycase has no YQ series",
  "ZQ-121004 at 305 x 254 x 132 mm is the comparable IP65 box, slightly larger than assumed.", "Fixed"),
 ("Compute", "The Arducam part is UB020201, not B020201", "A wrong part number buys the wrong camera.", "Fixed"),
 ("Robot arm", "The arm and gripper are both cheaper than Rev C assumed",
  "$759 on sale and $129.99, and the gripper page lists the 280 Pi explicitly, so no adapter.", "Price"),
]


def build():
    wb = openpyxl.load_workbook(SRC)
    for name in ("BOM", "Summary", "Sheet"):
        if name in wb.sheetnames:
            del wb[name]

    # ---------------------------------------------------------------- BOM
    ws = wb.create_sheet("BOM", 1)
    ws["A1"] = "Herb Tower BOM Rev E, with buying links checked 2026-10-10"
    ws["A1"].font = TITLE
    ws["A2"] = ("Click any Link cell to open the product page. Confidence: Verified = page opened and price read; "
                "Search = real part, vendor search pre-filled; Alternate = the specified part does not exist or is "
                "unavailable; Quote = custom work, priced on upload.")
    ws["A2"].font = Font(size=9, italic=True, color="4A5A4E")
    ws.merge_cells("A2:M2")
    ws.row_dimensions[2].height = 28
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")

    cols = ["ID", "Subsystem", "Item", "Manufacturer", "Part number", "Vendor", "Link",
            "Qty", "Unit", "Unit price", "Ext price", "Confidence", "Note"]
    hr = 4
    for i, c in enumerate(cols, 1):
        cell = ws.cell(hr, i, c)
        cell.fill, cell.font, cell.border = HEAD, HF, BOX
        cell.alignment = Alignment(horizontal="center", vertical="center")

    r = hr + 1
    for (pid, sub, item, mfr, pn, vendor, url, qty, unit, price, conf, note) in R:
        vals = [pid, sub, item, mfr, pn, vendor, "open", qty, unit, price, f"=H{r}*J{r}", conf, note]
        for i, v in enumerate(vals, 1):
            cell = ws.cell(r, i, v)
            cell.border = BOX
            cell.font = Font(size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=(i in (3, 13)))
        link = ws.cell(r, 7)
        link.hyperlink = url
        link.font = LINK
        link.alignment = Alignment(horizontal="center", vertical="top")
        ws.cell(r, 10).number_format = '"$"#,##0.00'
        ws.cell(r, 11).number_format = '"$"#,##0.00'
        if conf == "Alternate":
            ws.cell(r, 12).fill = ALT_F
        elif conf in ("Search", "Quote"):
            ws.cell(r, 12).fill = BAND
        if qty == 0:
            for i in range(1, 14):
                ws.cell(r, i).font = Font(size=10, italic=True, color="8A8A8A")
        r += 1

    last = r - 1
    ws.cell(r + 1, 10, "Subtotal").font = Font(bold=True)
    ws.cell(r + 1, 11, f"=SUM(K{hr+1}:K{last})").font = Font(bold=True)
    ws.cell(r + 2, 10, "Shipping and tax, 12 %")
    ws.cell(r + 2, 11, f"=K{r+1}*0.12")
    ws.cell(r + 3, 10, "Contingency, 10 %")
    ws.cell(r + 3, 11, f"=K{r+1}*0.10")
    ws.cell(r + 4, 10, "Budget").font = Font(bold=True, size=12)
    ws.cell(r + 4, 11, f"=SUM(K{r+1}:K{r+3})").font = Font(bold=True, size=12)
    for rr in range(r + 1, r + 5):
        ws.cell(rr, 11).number_format = '"$"#,##0.00'
    totals = {"subtotal": r + 1, "budget": r + 4}

    for col, w in zip("ABCDEFGHIJKLM", [8, 17, 34, 18, 26, 20, 7, 7, 7, 11, 12, 12, 62]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "C5"
    ws.auto_filter.ref = f"A{hr}:M{last}"

    # ---------------------------------------------------------------- Order by vendor
    vs = wb.create_sheet("Order by vendor", 2)
    vs["A1"] = "One checkout per vendor"
    vs["A1"].font = TITLE
    vs["A2"] = ("Work down this sheet and the build arrives in 20-odd parcels rather than 90 separate decisions. "
                "Vendors are ordered by spend. Lead times worth knowing: the Mean Well HLG-60H-C700B is three weeks "
                "from Jameco, and the DDR-15G-12 shows a long factory lead at one distributor, so place those first.")
    vs["A2"].font = Font(size=9, italic=True, color="4A5A4E")
    vs.merge_cells("A2:E2")
    vs.row_dimensions[2].height = 30
    vs["A2"].alignment = Alignment(wrap_text=True, vertical="top")

    by = {}
    for (pid, sub, item, mfr, pn, vendor, url, qty, unit, price, conf, note) in R:
        if qty == 0:
            continue
        by.setdefault(vendor, []).append((pid, item, qty, unit, price, url))
    order = sorted(by, key=lambda v: -sum(q * p for _, _, q, _, p, _ in by[v]))

    for i, c in enumerate(["Vendor / Item", "ID", "Qty", "Unit price", "Ext price"], 1):
        cell = vs.cell(4, i, c)
        cell.fill, cell.font, cell.border = HEAD, HF, BOX
    rr = 5
    for vendor in order:
        items = by[vendor]
        sub_total = sum(q * p for _, _, q, _, p, _ in items)
        c = vs.cell(rr, 1, f"{vendor}")
        c.font = Font(bold=True, size=11, color="1F3A2E")
        c.fill = BAND
        for k in range(2, 6):
            vs.cell(rr, k).fill = BAND
        tc = vs.cell(rr, 5, sub_total)
        tc.font = Font(bold=True)
        tc.number_format = '"$"#,##0.00'
        rr += 1
        for pid, item, qty, unit, price, url in items:
            vs.cell(rr, 1, f"    {item}")
            lc = vs.cell(rr, 2, pid)
            lc.hyperlink = url
            lc.font = LINK
            vs.cell(rr, 3, f"{qty} {unit}")
            vs.cell(rr, 4, price).number_format = '"$"#,##0.00'
            vs.cell(rr, 5, qty * price).number_format = '"$"#,##0.00'
            rr += 1
        rr += 1
    vs.cell(rr, 1, "Total").font = Font(bold=True, size=12)
    tot = vs.cell(rr, 5, sum(q * p for v in by for _, _, q, _, p, _ in by[v]))
    tot.font = Font(bold=True, size=12)
    tot.number_format = '"$"#,##0.00'
    for col, w in zip("ABCDE", [52, 9, 11, 12, 13]):
        vs.column_dimensions[col].width = w
    vs.freeze_panes = "A5"

    # ---------------------------------------------------------------- Changes
    cs = wb.create_sheet("Changes", 3)
    cs["A1"] = "What changed since Rev C"
    cs["A1"].font = TITLE
    cs["A2"] = ("Blocking means it will not work as drawn. Decide means a choice is waiting on you. "
                "Fixed means Rev D already carries the substitute. Price means the part is right and the number moved.")
    cs["A2"].font = Font(size=9, italic=True, color="4A5A4E")
    cs.merge_cells("A2:D2")
    for i, c in enumerate(["Area", "Finding", "What it means", "Status"], 1):
        cell = cs.cell(4, i, c)
        cell.fill, cell.font, cell.border = HEAD, HF, BOX
    rr = 5
    for area, finding, detail, status in sorted(CHANGES, key=lambda x: {"Blocking": 0, "Decide": 1, "Fixed": 2, "Price": 3}[x[3]]):
        cs.cell(rr, 1, area).border = BOX
        cs.cell(rr, 2, finding).border = BOX
        cs.cell(rr, 3, detail).border = BOX
        sc = cs.cell(rr, 4, status)
        sc.border = BOX
        if status == "Blocking":
            sc.fill = WARN
            sc.font = Font(bold=True, color="A3281E")
        elif status == "Decide":
            sc.fill = ALT_F
        for i in (2, 3):
            cs.cell(rr, i).alignment = Alignment(wrap_text=True, vertical="top")
        cs.cell(rr, 1).alignment = Alignment(vertical="top")
        rr += 1
    for col, w in zip("ABCD", [16, 48, 78, 11]):
        cs.column_dimensions[col].width = w
    cs.freeze_panes = "A5"

    # ---------------------------------------------------------------- Summary
    sm = wb.create_sheet("Summary", 0)
    sm["A1"] = "Herb Tower Rev E"
    sm["A1"].font = Font(bold=True, size=16, color="1F3A2E")
    sm["A2"] = "Cost by subsystem. Links checked 2026-10-03, consumables and tray drainage added 2026-10-10"
    sm["A2"].font = Font(size=10, italic=True, color="4A5A4E")
    for i, c in enumerate(["Subsystem", "Cost", "Share"], 1):
        cell = sm.cell(4, i, c)
        cell.fill, cell.font, cell.border = HEAD, HF, BOX
    subs = sorted({x[1] for x in R})
    first_sub = 5
    last_sub = first_sub + len(subs) - 1
    trow = last_sub + 1
    for off, s in enumerate(subs):
        rr = first_sub + off
        sm.cell(rr, 1, s).border = BOX
        sm.cell(rr, 2, f"=SUMIF(BOM!$B$5:$B${last},A{rr},BOM!$K$5:$K${last})").border = BOX
        sm.cell(rr, 2).number_format = '"$"#,##0'
        sm.cell(rr, 3, f"=IF($B${trow}=0,0,B{rr}/$B${trow})").border = BOX
        sm.cell(rr, 3).number_format = "0.0%"
    sm.cell(trow, 1, "Total").font = Font(bold=True)
    sm.cell(trow, 2, f"=SUM(B{first_sub}:B{last_sub})").font = Font(bold=True)
    sm.cell(trow, 2).number_format = '"$"#,##0'
    sm.cell(trow + 1, 1, "Budget incl. shipping and contingency").font = Font(bold=True)
    sm.cell(trow + 1, 2, f"=BOM!K{totals['budget']}").font = Font(bold=True)
    sm.cell(trow + 1, 2).number_format = '"$"#,##0'
    sm.cell(trow + 2, 1, "Check against BOM subtotal")
    sm.cell(trow + 2, 2, f'=IF(ABS(B{trow}-BOM!K{totals["subtotal"]})<0.01,"OK","MISMATCH")')
    nblock = sum(1 for c in CHANGES if c[3] == "Blocking")
    sm.cell(trow + 4, 1, f"Read the Changes sheet before ordering: {nblock} findings are blocking.").font = \
        Font(bold=True, color="A3281E")
    for col, w in zip("ABC", [40, 14, 10]):
        sm.column_dimensions[col].width = w

    # ---------------------------------------------------------------- Power sheet correction
    pw = wb["Power"]
    for row in pw.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and "HLG-80H-C1050B" in cell.value:
                cell.value = cell.value.replace("HLG-80H-C1050B", "HLG-80H-C700B, bars in series")

    wb.move_sheet("Summary", offset=-wb.sheetnames.index("Summary"))
    wb.save(OUT)
    return OUT, len(R), last


if __name__ == "__main__":
    path, n, last = build()
    print(f"wrote {path}: {n} lines, last BOM row {last}")
