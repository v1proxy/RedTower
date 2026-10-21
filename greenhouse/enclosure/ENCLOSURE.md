# Maag: enclosure assembly

Maag is the Modular Agentic Autonomous Greenhouse.

**Enclosure Rev A · design 0.6.1 · 2026-10-21 · all dimensions mm**

0.6.0 added the harvest feeder's openings and holes to the right panel (see
`greenhouse/harvest/HARVEST.md`). 0.6.1 hangs the two exhaust fans inside,
under the top panel, with a grill on each side; moves the tier A cable gland
down from 900 to 780, clear of the feeder's new skirt; and moves the feeder's
switch-cable hole with its switch.

Read alongside the booklet `Maag_Enclosure_Assembly_Instructions_RevA.pdf` (step
numbers below are the booklet's). It opens with the Maag cover render, an
overview, parts, fasteners, tools, two pages of face maps (every hole, every
strip of tape), a true-scale section of the door, then 18 steps. It starts from
the finished cabinet (Frame Rev A, step 21) with the gantry in (Gantry Rev E).

Every drawing, every DXF and the printed part come from one model,
`enclosure.py`, built on `greenhouse/frame/cabinet.py`. Regenerate with:

```
python greenhouse/enclosure/enclosure.py                 # every check, as a report
python greenhouse/enclosure/make_enclosure_files.py      # DXFs, the A&C drawing, the STL
python greenhouse/enclosure/make_enclosure_booklet.py    # the booklet into greenhouse/enclosure/build
python greenhouse/enclosure/make_enclosure_booklet.py s7 s13   # just those pages, PNG only
```

Fonts: IBM Plex Mono from `$MAAG_FONTS`; Inter if installed (it is not on the PC,
so body text falls back to DejaVu Sans there).

---

## What it is

| | |
|---|---|
| Back, sides, top | 1/8 in (3.175) frosted polycarbonate, TUFFAK GP Matte. Six panels from three 48 × 96 in sheets, cut and drilled by A&C Plastics (Houston) |
| Doors | Four, two stacked pairs. 4.5 clear polycarbonate (0.177 in), SendCutSend |
| Mounting | Surface mounted on the frame's outer faces: EPDM foam strip on the land beside each slot, M5 × 16 button head and DIN 9021 washer through an 8 mm hole into a drop-in M5 T-nut, never more than 300 apart |
| Back seams | Three back panels meet over B1 and B2 with a 6 mm gap on the slot line; a 1 × 1/8 in 5052 batten over each seam (two pieces, SendCutSend), M5 × 20 through the batten and the gap |
| Hinges | Two McMaster 1658A15 piano hinges (304 SS, 1 1/2 in open, 0.042 leaf) per door, 1 ft each. Frame leaf on a 3.0 clear PC spacer into drop-in M3 T-nuts in the post's front slot; door leaf on VHB 4905 |
| Catch and seal | Cup magnets Ø16 × 4.5 on the front rails' slot lines (bottom pair F0 and F1, top pair F3 and F4), steel discs on the doors; Frost King V25BK EPDM weatherstrip on the post and rail lands |
| Centre | The right door of each pair carries a 40 wide astragal behind the left door's edge: open the left door first |
| Air | Two Noctua NF-F12 exhaust fans hung inside under the top panel at x 420 and 977, 310 from the front, blowing up and out; a grill under each fan and one on the panel's outer face over it; passive intake low on the right through a 120 grill and a DEMCiflex magnetic filter |
| Water, power, data | Humidifier duct through a printed collar (right, tier A bay); three PG21 glands (right, back edge); the drain riser outside the left panel on five P-clips, each branch through a grommet |
| Harvest feeder | On the right panel at tier B: two 80 × 160 openings for the arm, four Ø10 holes for its well nuts, a Ø8 hole for its lid switch's cable (u 432, v 1192). Its four M5 holes on tier B's rail line carry ordinary panel screws until the feeder goes on (greenhouse/harvest) |
| Safety | A reed switch per door (7939WG, BOM G047) in the door chain; two anti-tip kits into wall studs through B4 |

## Why it is built this way

**Surface mounted, not in the slots.** A panel in the slots has to go in before
the frame closes, and the frame and the gantry are already built. On the outer
faces any panel comes off with a 3 mm key, and the slots stay free for T-nuts.

**Tape on the land, not over the slot.** The slot mouth is 8.2 wide; a strip
centred on it would bridge it on 1.9 of land each side. A 1/2 in strip fits the
13.5 land beside the slot, on the side toward the bay, so the loop of strips
round each face is the seal and every screw sits outside it.

**8 mm holes for 5 mm screws.** Polycarbonate moves 0.0675 mm per metre per
degree: the back's 1397 grows 1.9 for 20 °C. The 1.5 each way covers it if the
screws are centred in their holes at install.

**The back is three panels** because no stock sheet is 1397 × 1829. The seams
sit on rails, so each edge has its own land and strip; the batten clamps both.

**Doors on spacers.** The spacer makes the 5.63 gap that a cup magnet and its
disc need (4.5 + 1.0 leaves 0.13 of air). The weatherstrip, 6.35 thick, is only
squeezed 11 % at that gap, deliberately: a hard seal would push the doors off
their magnets.

**Fans inside, over the folded arm.** Hung under the top panel they reach 25 +
1.6 of grill + the M4 heads down into the top bay, to 1802.9. At y 310 their
footprints (y 250 to 370) stay in front of the gantry's mast and X drive, which
never come forward of y 388, so nothing on the gantry passes under
them. The arm, folded for travel with J1 at the top of its stroke, tops out at
1763.0 in that band: 39.9 under the fans' lowest point, over the whole X
travel (`fan_clearance()`). The screws go in from inside, heads under the inner
grill and nylocs on the outer one, which keeps the heads 5.6 higher than the
other way round. Outside the cabinet only the two grills show.

**The riser moves off the post.** The left panel's strip and screws run on FL's
left face, where the frame booklet zip-tied the riser. It now hangs on five
P-clips that are also panel screws, 2.3 clear of the panel (vinyl against
polycarbonate clouds it), and each branch comes out through a 7/8 in grommet 18
under its tier's rail. Each branch ends up 8 shorter: trim it.

## The checks (`python enclosure.py`)

| Check | Result |
|---|---|
| Nest, three 48 × 96 sheets | A: back bottom + back upper, 53 spare across. B: back middle + top, 6.6 spare across. C: both sides, 98 spare |
| Hole centre to any edge | 18 or more everywhere (16 needed, two diameters); top panel 18 front and back, the rest 20 |
| Cutouts open into bays | Tightest: the C grommet's flange, 3.7 under L3; the feeder's openings 9.8 over tier B's right rail |
| Gantry to the panels' inner faces | left 2.0 (two X-rail screw heads stand 1.5 proud of the frame face), right 3.5, back 38.5, top 8.5 |
| Panel screw, M5 × 16 | stack 7.9, reaches 8.1 below the face: 3.8 past the lips, 4.1 short of the slot floor |
| Batten screw, M5 × 20 | stack 9.9, 5.9 past the lips, 2.1 short of the floor |
| P-clip and anti-tip screws, M5 × 16 | 3.4 and 3.0 past the lips |
| M4 through-bolts past their nylocs | fans (M4 × 40, two grills) 2.0, grill (M4 × 16) 4.6, collar (M4 × 16) 3.2 |
| Fans inside, over the gantry and the folded arm | heads at 1802.9; gantry: nothing under a fan; the arm folded at the top of its travel 1763.0: 39.9 clear |
| Door gap | hinge stack 5.63; magnet + disc 5.5; astragal 2.13 clear of the rails, 0.5 under the left door |
| Door swing | 152° on every door before it meets the post or the side panel |
| Tape | 28.7 m of panel strip (buy three 50 ft rolls), 8.9 m of weatherstrip (two 17 ft rolls) |

## Files

| File | For | What |
|---|---|---|
| `acplastics/panel_*.dxf` (6) | A&C Plastics | Outline, every hole and the right panel's two feeder openings, mm, each drawn as seen from outside |
| `acplastics/Maag_Enclosure_Panels_RevA.pdf` | A&C Plastics | The nest and a page per panel with its hole table: attach with the DXFs to their quote form |
| `sendcutsend/door_{bottom,top}_{L,R}.dxf` | SendCutSend | Polycarbonate 0.177 in clear, qty 1 each |
| `sendcutsend/hinge_spacer.dxf` | SendCutSend | Polycarbonate 0.118 in clear, qty 8 (one part: flip it for the right doors) |
| `sendcutsend/astragal_{bottom,top}.dxf` | SendCutSend | Polycarbonate 0.118 in clear, qty 1 each |
| `sendcutsend/seam_batten.dxf` | SendCutSend | 5052 aluminium 0.125 in, qty 4 (one part: turned end for end for the right half) |
| `print/duct_collar.stl` | your printer | PETG, 4 walls, 30 % infill, flange down |

All 14 DXFs pass the closed-loop and self-crossing check that caught 0.4.0's
sheet DXFs.

## Buy list

| Item | Qty | Source |
|---|---|---|
| TUFFAK GP Matte polycarbonate, 1/8 in, cut and drilled | 3 sheets, 6 panels | A&C Plastics, Houston (quote from the DXFs and the PDF) |
| Doors, spacers, astragals, battens | 4 + 8 + 2 + 4 | SendCutSend (quote on upload) |
| Piano hinge, 304 SS, 1 1/2 in open, 0.042, with holes, 1 ft | 8 | McMaster 1658A15 |
| EPDM foam strip, 3/16 × 1/2 in, 50 ft, acrylic adhesive | 3 | Presbond 2A1 |
| EPDM weatherstrip, 5/16 W × 1/4 T in, 17 ft | 2 | Frost King V25BK, Home Depot 202844545 |
| 3M VHB 4905, 1/2 in | 1 roll | |
| Cup magnet Ø16 × 4.5, M3 countersunk; steel disc Ø16 × 1, adhesive | 8 + 8 | |
| Door pull, 96 mm centres | 4 | |
| Fan grill NA-FG1-12 Sx2 | 2 more packs (G024 has one): five grills, two per fan and the intake's | Noctua |
| Cable gland PG21, nylon, with locknut | 3 | |
| Rubber grommet, 7/8 in hole, 5/8 in bore, 1/8 in panel | 3 | |
| Cushioned P-clip, 5/8 in | 5 | |
| Furniture anti-tip kit, steel cable | 2 | e.g. SIMPLE MOUNT 9976524, Home Depot |
| M5 × 16 button head; M5 × 20 button head; DIN 9021 M5 | 100; 20; 100 | |
| M5 drop-in T-nut, slot 8, hammer head (turns in as you tighten) | 120 | |
| M3 × 12 flat head; M3 drop-in T-nut, slot 8 | 50; 50 | |
| M4 × 40, M4 × 16, M4 × 10 button heads; M4 nyloc; M4 washer | 8, 7, 8; 15; 30 | |

Already on BOM Rev E: NF-F12 ×2 (G022), DEMCiflex filter (G027), 2 in duct
(G026), humidifier (G025), reed switches (G047).

**Superseded on BOM Rev E**: G002 and G002b (2020 door frames and cuts), G008
(clear glazing), G009 (ACM), G010 (slot gasket), G011 (80/20 hinges), G012 and
G012b (80/20 catches and pulls), G015 (Simpson A34: its 36.5 leg cannot reach a
wall behind 6.7 of panel and a batten; a cable kit takes any gap).

## Open items

- **The hinge's hole line is not published.** Drawn at 9.5 from the pin; the
  spacer's slot takes 8 to 11. Step 1 measures it. Each mm off moves the doors
  and changes the centre gap by 2.
- **The reed switch and its magnet are drawn as blocks**, sized from no
  drawing (Honeywell publishes a 1 1/4 in gap, not dimensions).
- **The fan and grill are drawn from their datasheet sizes**, not Noctua CAD.
- **A&C may cut to size and not drill.** If their quote says so, the face maps
  and hole tables are the template; a step drill and a backing board do it.
- **BOM Rev F** should fold in the buy list above and drop the superseded rows.
- **The gantry's two X-rail end screws** stand 1.5 proud of the left face: the
  left panel clears them by 2.0. Do not use thinner tape on the left face.
