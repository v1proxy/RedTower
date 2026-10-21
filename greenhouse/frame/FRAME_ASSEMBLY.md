# Maag: frame and trays assembly

Maag is the Modular Agentic Autonomous Greenhouse.

**Frame Rev A · design 0.4.0 · 2026-10-20 · all dimensions mm**

Read alongside the booklet `Maag_Frame_Assembly_Instructions_RevA.pdf` (step
numbers below are the booklet's). The booklet opens with a rendered cover, the
parts, the fasteners, a tools page and a page that shows every joint and what
holds it, then 21 steps. Steps 1 to 4 happen on the bench and at the printer,
5 to 15 build the frame, 16 to 21 put the sheet metal and the drains in. The
gantry booklet (Gantry Rev E) starts from the finished cabinet at its step 21.

Every drawing is generated from `cabinet.py`, the same model the gantry's
cabinet shares its numbers with. Regenerate with:

```
python greenhouse/frame/make_frame_booklet.py          # whole booklet into greenhouse/frame/build
python greenhouse/frame/make_frame_booklet.py s7 s13   # just those pages, PNG only
python greenhouse/frame/cabinet.py                     # cut list, joints and every check
```

The fonts are the house style's: IBM Plex Mono from `$MAAG_FONTS` or
`greenhouse-esphome/_fonts`, Inter from the system or the same folder.

---

## What changed from the Rev 5 bracket schedule, and why

**Rev 5 had an M8 end tap on all 54 member ends, plus 30 brackets. Rev 6 (this
booklet) drops the end taps and puts a bracket on every joint.**

An end-tap joint puts a screw head in the mating member's slot, and a head can
only enter a slot from that slot's open end. In this cabinet the shelf rails
tie the left and right side rails together, and the side rails close against
the posts, so every tier would have to go in as a six-headed unit lowered 1.8 m
down four free-standing posts. No practical order of assembly exists. The end
tap also needs a centre bore cored for M8, and the profile's bore has never
been measured. With a bracket on every joint and every nut a drop-in nut, any
bracket goes on in any order, nothing needs machining and the bore only
matters to the feet.

| Rev 5 | Rev 6 | Consequence |
|---|---|---|
| End tap M8 on 54 ends (G006), 54 access holes | None | No tapping, no drilling of the frame |
| 20 PETOX gussets, 10 TOCLUX hidden connectors | **44 gussets**, 10 hidden connectors | Buy **two more PETOX sets** ($59.98); 16 gussets spare |
| Slide-in M8 nuts from the PETOX boxes | **Drop-in** M8 slot-8 nuts throughout | Buy **150**: 88 gussets, 60 sheets, 2 spare |
| Hidden connectors at the shelf and mid rail ends | Hidden connectors at the **8 floor corners** and the **2 top side rails' back ends** | Gussets cannot go where there is no room below (the floor) or where the X rail runs (top back corners) |
| 80/20 levelling feet (G007) | **Printed TPU feet**, 40 × 40 × 20, barbed pin into the post's bore | `tpu_foot.py --profile 4040` |
| Trays and pan flat | Every tray and the pan **fall 5 mm** to the left end | Right-hand posts marked 5 higher on levels 0 to 3 (BOM G090) |
| Tiers into the pan, the pan to a 5 gal bucket | Each tray drains into **one riser zip-tied to the FL post**, the riser into a **2 gal lidded bucket**; the pan has no drain | The pan's outlet would sit 38 above the floor, below any bucket's rim. No tray takes another's runoff. One bulkhead fewer |

The placement rule is unchanged: **no bracket on a top face**, and **nothing
behind the tray line (y = 203) between the posts**, which is the gantry's
corridor. `cabinet.py` checks both: the corridor is clear, and the closest any
bracket comes to a sheet fastener is 50 (Rev 5's tightest was 16, at the tier
mid rail, where Rev 6 has its gusset on the rail's side face instead).

### Every joint

| Joints | Bracket | Where |
|---|---|---|
| 16 | gusset | under each front and back rail end, levels 1 to 4, leg down the post |
| 14 | gusset | under each side rail end, levels 1 to 4, leg down the post |
| 12 | gusset | on edge, front side of each shelf rail end and left side of each tier mid rail end |
| 2 | gusset | on edge, left side of the base mid rail, each end |
| 8 | hidden connector | every floor corner: in the rail's top slot and the post's face slot |
| 2 | hidden connector | the top side rails' back ends, in the rail's bottom slot and the post's front slot |

## Corrections found while building the model

- **The base pan DXFs in the repo were still the 457-deep pan.** `make_dxf_rev4.py`
  already had the 559 depth, but `basepan_DOWN.dxf` and `basepan_UP.dxf` had never
  been regenerated: their back holes sat at y = 437, 102 short of the back rail.
  Both are regenerated (flat 604 × 723 and 604 × 760, inside SendCutSend's
  30 × 44 in). The tray DXFs were already right. BOM G014 said to re-upload; it
  now has the right files to upload.
- **The gantry cabinet model drew the base mid rail at mid-span** (x 678.5), 18.5
  off the pan's lap bolt at 680, and left out the three 123 tier mid rails that its
  own cut list counted. `greenhouse/gantry/frame.py` now draws both at x 660 to 700
  and its cut report reads 30.07 m and 17 sticks, matching the gantry booklet's
  step 21 text. The Rev E PDF is unchanged; its step 21 drawing picks the fix up
  at its next rebuild.
- **The base pan could not drain into a bucket.** Its bulkhead would hang 38
  above the floor and a 5 gal bucket's rim is 370 up, so the BOM's "base pan to a
  floor bucket" ran uphill. Now each tray drains on its own: a bulkhead at
  (66, 95), an elbow, a short branch under its left rail and out of the side into
  one riser zip-tied to the outside of the FL post. Tier C joins it at an elbow,
  B and A at tees. The riser leaves the post 285 above the floor and drops into
  the lid of a 2 gal bucket (rim about 250) beside the cabinet. The pan becomes
  the dry catch tray under everything, with the leak sensor at its low, left end.
  `basepan_DOWN.dxf` no longer has a drain pilot, and the tray drain pilot moves
  from (60, 150) to (66, 95): at the old spot the bulkhead nut hit the shelf rail.
  Bulkheads 3, not 4.
- **The sheet screws were all M8 × 16.** Through a single sheet on an EU slot-8
  profile 12.25 deep that reaches 12.8 into the slot and bottoms: tight, clamping
  nothing. Now M8 × 12 through one sheet (3.5 clear of the slot floor, 4.5 of
  thread past the lips) and M8 × 16 through two layers (UP piece on its shim, and
  the lap), 1.1 clear. Step 1 measures the real slot depth; if it is shallower,
  shorten both.

## Before you start

**Tools** (booklet tools page): calipers; 5 m tape; 300 combination square; a
mitre saw with a non-ferrous blade, or hacksaw and mitre box; ball-end hex keys
3, 5 and 6; 600 spirit level; two 300 F-clamps; a flat bar and a wood block; a
step drill; a caulking gun and neutral-cure silicone. And a 3D printer for the
feet, a helper for steps 7 to 9, and three 5 mm packers.

**The profile** (step 1): EU slot 8, one slot per face. Measure the slot opening
(8.0 to 8.2, or the brackets do not fit), the slot depth (the sheet screws), the
centre bore (which feet to print) and the corner radius.

## The steps, in brief

| Step | What | The thing that matters |
|---|---|---|
| 1 | Know your profile | Slot 8.0 to 8.2, or stop |
| 2 | Cut and label 31 pieces | Square to 0.5, deburr, label both ends |
| 3 | Mark the levels on the posts | From the bottom end; right posts 5 higher on levels 0 to 3 |
| 4 | Print the feet | Fit-test coupons for 6.8, 8.4 and 10.5 first |
| 5 | Base: F0, B0, M0 | M0's left face 620 from F0's end, under the pan's lap |
| 6 | Hidden connectors, 8 floor ends | Upright leg 11 clear of the rail end |
| 7 | Stand the posts | Right end of the base on 5 mm packers |
| 8 | Top ledges | 6 gussets; hidden connectors in L4, R4 |
| 9 | Top ring | L4 and R4 back ends slide down into BL and BR |
| 10 | Square it, then tighten | Diagonals within 2: 2301.5, 1912.5, 1504.7 |
| 11 to 13 | Tier A ledges, rails, tray rails | S1's back face on the tray line, 203 |
| 14 | Tiers B and C | Bottom up |
| 15 | The feet | Lift 25, no more |
| 16 | Sheets: check, drill, seal | Silicone in every inside corner |
| 17, 18 | Base pan DOWN, then UP | Shims under the UP piece's seven other slots |
| 19 | Trays, three times | Back lip on the tray line |
| 20 | Drains | Each tray into one riser on the FL post, the riser into a lidded 2 gal bucket; the pan stays dry |
| 21 | Before you load it | Anchored to the wall, water test |

## Buy list, frame and trays

| Item | Qty | Note |
|---|---|---|
| 4040 EU slot 8, 2000 sticks or cut to length | 17 sticks / 31 pieces | already bought |
| PETOX 3540 gusset set of 20 (B0BS6LNVS9) | 2 more | 20 owned |
| TOCLUX hidden connector set of 10 (B0F18V8KTS) | owned | |
| M8 drop-in T-nut, slot 8 | 150 | 88 gussets, 60 sheets |
| M8 × 12 button head, ISO 7380 | 28 | single sheet |
| M8 × 16 button head, ISO 7380 | 32 | UP pieces and laps |
| M8 washer, DIN 125 | 88 | 60 under heads, 28 shims |
| SUNLU TPU 95A Clear (B0BXP1LWJK) | 160 g | four feet |
| Sheets G013 × 3 + 3, G014 × 1 + 1 | | SendCutSend, from the DXFs |
| Bulkhead 1/2 in, EPDM washers (G090) | 3 | BOM says 4: the pan has no drain now |
| Elbow 90°, 1/2 in MNPT × 1/2 in barb | 3 | one under each bulkhead |
| Barbed elbow 1/2 in | 1 | top of the riser, tier C |
| Barbed tee 1/2 in | 2 | tiers B and A |
| Drain tube 1/2 in ID, 10 ft (G090b) | 1 | about 2 m used |
| Zip tie, 300 | 5 | the riser to FL |
| Bucket, 2 gal, with lid (G090c) | 1 | BOM says 5 gal: too tall, the rim must be under 300 |
| Neutral-cure silicone | 1 tube | |

Dropped: G006 end-tap service, G007 levelling feet.

## Open items

- **The profile's centre bore is unmeasured.** It decides only the feet now.
- **The TOCLUX connector's exact section is not drawn from a manufacturer's
  drawing**: it is modelled from its listing (an L, 38 reach, 7.8 wide, two M6
  grubs). Check its legs sit fully inside the slot before relying on step 6's
  "11 clear" figure.
- **Tray drains sit under the first pot station** at x 60. Keep the first pot of
  each tray off the bulkhead flange, or stand it on pot feet.
- **The left side panel** (next booklet): the riser stays outside it, so each
  tier's branch needs a 20 mm grommet hole, about 18 under that tier's left rail
  and 90 back from the front face.
- **Bucket capacity**: 2 gal is about 7.5 L of runoff. Check it weekly until the
  irrigation volumes are known; the leak sensor beside it is the backstop. If it
  overfills, the riser backs up into tier A first.
- **Anti-tip anchoring** (BOM G015) is called for in step 21 but its brackets
  are not drawn: they belong with the panels, in the next booklet.
- The TOCLUX and PETOX quantities assume the boxes hold what their listings say;
  count them before step 5.
