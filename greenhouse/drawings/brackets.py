#!/usr/bin/env python3
"""SUPERSEDED at 0.4.0 by greenhouse/frame/cabinet.py (bracket schedule Rev 6: a bracket
on every joint, no end taps). Kept for the record of Rev 5.

Rev 5: the two T-slot brackets Vittorio bought, placed on the frame.

Bracket A, TOCLUX B0F18V8KTS, $16.99 for 10 sets
    40-series HIDDEN inside connector. An L-shaped block that drops into the 8 mm
    slot of both profiles and locks with two grub screws. Nothing shows outside the
    profile, and nothing projects past the profile face. 10 brackets, 20 grub
    screws, 1 ball-end wrench.

Bracket B, PETOX B0BS6LNVS9, $29.99 for 20 sets
    40-series EXTERNAL 3540 gusset: 40 mm wide, 35 mm legs, bolt centres 20 mm from
    the inside corner, which puts them on the slot centreline of both profiles.
    20 brackets, 40 M8x16 bolts, 40 slide-in T-nuts, 40 washers, 1 wrench.

The placement rule that the whole allocation follows:

    NO BRACKET EVER MOUNTS ON A TOP FACE.

Every top face in this cabinet is either a tray bearing surface or the slot the
tray's T-nut slides in. A gusset on a top face lifts the sheet 6 mm over 35 mm of
its run and takes the slot the fastener needs. So every external gusset hangs under
its horizontal member, in the concave corner below it, and the hidden connectors
live inside the slot where they take no room at all.

That rule has one consequence: level 0 sits on the floor, so there is nothing below
it to bolt to, and its eight perimeter joints get no gusset. They do not need one.
The base pan is 1397 x 559 of 1.6 mm sheet with a 25 mm upstand on every edge,
bolted down at sixteen points. That is a shear diaphragm, and it braces the bottom
of the cabinet better than eight gussets would.
"""

W, D, H = 1397.0, 559.0, 1829.0   # 0.2.0: depth 457 -> 559, see CHANGELOG
SER = 40.0
LEVELS = [0.0, 304.8, 965.2, 1397.0, 1789.0]
TIERS = LEVELS[1:4]
SHELF = 163.0
MID = (660.0, 700.0)

# ---------------------------------------------------------------- brackets
GUSSET = dict(name="external 3540 gusset", leg=35.0, width=40.0, hole=20.0,
              plate=6.0, qty=20, each=29.99 / 20,
              asin="B0BS6LNVS9", brand="PETOX")
HIDDEN = dict(name="hidden inside connector", leg=38.0, width=7.8, hole=None,
              plate=0.0, qty=10, each=16.99 / 10,
              asin="B0F18V8KTS", brand="TOCLUX")

# Reach of each bracket measured along the slot from the joint face. This is the
# number that has to clear the sheet-metal fasteners.
REACH = {"gusset": GUSSET["leg"], "hidden": HIDDEN["leg"]}


# ---------------------------------------------------------------- the frame
def members():
    """Every horizontal member, as (id, level, axis, a0, a1, cross-coord, kind)."""
    M = []
    for z in LEVELS:
        M.append((f"L{z:.0f}-FRONT", z, "x", SER, W - SER, 0.0, "longitudinal"))
        M.append((f"L{z:.0f}-BACK", z, "x", SER, W - SER, D - SER, "longitudinal"))
        M.append((f"L{z:.0f}-LEFT", z, "y", SER, D - SER, 0.0, "side member"))
        M.append((f"L{z:.0f}-RIGHT", z, "y", SER, D - SER, W - SER, "side member"))
        if z in TIERS:
            M.append((f"L{z:.0f}-SHELF", z, "x", SER, W - SER, SHELF, "shelf rail"))
            M.append((f"L{z:.0f}-MID", z, "y", SER, SHELF, MID[0], "mid rail"))
        if z == LEVELS[0]:
            M.append((f"L{z:.0f}-MID", z, "y", SER, D - SER, MID[0], "mid rail"))
    return M


def joints():
    """Both ends of every horizontal member. 54 of them."""
    J = []
    for mid_, z, axis, a0, a1, c, kind in members():
        meets = {"longitudinal": "upright", "side member": "longitudinal",
                 "shelf rail": "side member", "mid rail": "longitudinal/shelf rail"}[kind]
        for end, a in (("lo", a0), ("hi", a1)):
            J.append(dict(member=mid_, kind=kind, level=z, axis=axis, end=end,
                          at=a, cross=c, meets=meets,
                          room_below=(z > 0.0)))
    return J


# ------------------------------------------------------- bracket allocation
def allocate():
    """Where the 30 brackets he owns actually go, and why."""
    J = joints()
    for j in J:
        j["bracket"] = None
        j["note"] = ""

    def pick(pred, kind, note, limit):
        n = 0
        for j in J:
            if n >= limit:
                break
            if j["bracket"] is None and pred(j):
                j["bracket"], j["note"] = kind, note
                n += 1
        return n

    # 16 gussets: under every longitudinal end that has room below it.
    pick(lambda j: j["kind"] == "longitudinal" and j["room_below"],
         "gusset", "under the longitudinal, leg down the upright", 16)
    # 4 gussets: under the mid rails of the two upper tiers, which carry the lap.
    pick(lambda j: j["kind"] == "mid rail" and j["level"] in TIERS[1:],
         "gusset", "under the mid rail, carries the tray lap", 4)
    # 6 hidden: the shelf-rail ends. Interior, and a gusset here would sit in the
    # tray's own footprint even hanging below, because the tray laps over it.
    pick(lambda j: j["kind"] == "shelf rail", "hidden",
         "inside the slot, clear of the tray above", 6)
    # 2 hidden: bottom tier mid rail.
    pick(lambda j: j["kind"] == "mid rail" and j["level"] == TIERS[0],
         "hidden", "inside the slot", 2)
    # 2 hidden: the level 0 mid rail, which has no room below it.
    pick(lambda j: j["kind"] == "mid rail" and j["level"] == 0.0,
         "hidden", "inside the slot, no room below at floor level", 2)
    for j in J:
        if j["bracket"] is None:
            j["note"] = ("end tap + M8 only; base pan is the diaphragm here"
                         if j["level"] == 0.0 else "end tap + M8 only")
    return J


# ------------------------------------------- do the brackets foul the sheets?
#
# The 64 sheet-metal fasteners, in frame coordinates, taken from the shipped DXFs.
# Each is (x, y, which member it lands on).
TRAY_FASTENERS = [
    # DOWN piece, local x == frame x
    (150, 20, "FRONT"), (400, 20, "FRONT"), (650, 20, "FRONT"),
    (150, 183, "SHELF"), (400, 183, "SHELF"), (650, 183, "SHELF"),
    (20, 130, "LEFT"), (680, 100, "MID"),
    # UP piece
    (800, 20, "FRONT"), (1050, 20, "FRONT"), (1260, 20, "FRONT"),
    (800, 183, "SHELF"), (1050, 183, "SHELF"), (1260, 183, "SHELF"),
    (1377, 130, "RIGHT"), (680, 100, "MID"),
]
PAN_FASTENERS = [
    (150, 20, "FRONT"), (400, 20, "FRONT"), (650, 20, "FRONT"),
    (150, 437, "BACK"), (400, 437, "BACK"), (650, 437, "BACK"),
    (20, 228.5, "LEFT"), (680, 228.5, "MID"),
    (800, 20, "FRONT"), (1050, 20, "FRONT"), (1260, 20, "FRONT"),
    (800, 437, "BACK"), (1050, 437, "BACK"), (1260, 437, "BACK"),
    (1377, 228.5, "RIGHT"), (680, 228.5, "MID"),
]
SLOT_L = 18.0           # the mounting hole is a 9 x 18 slot, so use its far end


def clearances():
    """For every sheet fastener, the gap from the nearest bracket on that member.

    A bracket reaches `leg` mm along the slot from the joint face. The fastener is
    a slot 18 mm long, so the edge that matters is 9 mm nearer the joint than its
    centre. Positive gap = clear.
    """
    out = []
    for level, fasteners, piece in (
            (TIERS[0], TRAY_FASTENERS, "tray"),
            (LEVELS[0], PAN_FASTENERS, "base pan")):
        for x, y, member in fasteners:
            if member in ("FRONT", "BACK", "SHELF"):
                run, lo, hi = x, SER, W - SER
            elif member in ("LEFT", "RIGHT"):
                run, lo, hi = y, SER, D - SER
            else:                                   # MID rail, runs in y
                run, lo = y, SER
                hi = SHELF if piece == "tray" else D - SER
            # which bracket, if any, sits at each end of that member
            reach = {"FRONT": REACH["gusset"], "BACK": REACH["gusset"],
                     "SHELF": REACH["hidden"], "LEFT": 0.0, "RIGHT": 0.0,
                     "MID": REACH["gusset"] if piece == "tray" else REACH["hidden"]}[member]
            if piece == "base pan" and member in ("FRONT", "BACK"):
                reach = 0.0                          # level 0 has no gusset
            gap = min(run - SLOT_L / 2 - lo - reach, hi - run - SLOT_L / 2 - reach)
            out.append((piece, member, x, y, reach, gap))
    return out


# ------------------------------------------------------- fastener schedule
#
# 64 slots, but NOT 64 fasteners. Over the 40 mm lap the UP piece lies on top of
# the DOWN piece and both are pierced at the same point, x = 680 on the tray, so
# one bolt clamps the lap through two sheets into one T-nut. One shared bolt per
# pair, four pairs, so 60 fasteners for 64 slots.
#
# The UP piece is propped 1.6 mm proud by the sheet under it, so each of its other
# seven fasteners gets an M8 flat washer (DIN 125, 1.6 mm) as a shim. Four UP
# pieces, 28 shims.
PAIRS = 4                      # 3 tray pairs + 1 base pan pair
SLOTS = 8 * 2 * PAIRS          # 64
SHARED = PAIRS                 # 4 lap bolts serve 2 slots each
BOLTS = SLOTS - SHARED         # 60
SHIMS = 7 * PAIRS              # 28


def hardware():
    """Everything that has to be on hand, and whether he already owns it."""
    return [
        ("external 3540 gusset", 20, "owned", PETOX := GUSSET["asin"], 29.99,
         "20 of 20 used"),
        ("hidden inside connector", 10, "owned", HIDDEN["asin"], 16.99,
         "10 of 10 used"),
        ("M8 x 16 bolt, gussets", 40, "owned", PETOX, 0.0, "in the PETOX set"),
        ("M8 T-nut, gussets", 40, "owned", PETOX, 0.0,
         "in the PETOX set, EU slot 8, see the fit note"),
        ("M8 washer, gussets", 40, "owned", PETOX, 0.0, "in the PETOX set"),
        ("M6 grub screw, hidden", 20, "owned", HIDDEN["asin"], 0.0,
         "in the TOCLUX set"),
        ("M8 x 16 BHSCS, sheets", BOLTS, "to buy", "", 0.0,
         f"{SLOTS} slots, {SHARED} of them lap bolts through two sheets"),
        ("M8 T-nut, sheets", BOLTS, "to buy", "", 0.0,
         "drop-in, so a tray can come out for cleaning"),
        ("M8 flat washer, sheets", BOLTS + SHIMS, "to buy", "", 0.0,
         f"{BOLTS} under the heads, {SHIMS} as the 1.6 mm shim under the UP pieces"),
    ]


if __name__ == "__main__":
    J = allocate()
    print(f"{len(members())} horizontal members, {len(J)} joints\n")

    from collections import Counter
    c = Counter((j["kind"], j["bracket"]) for j in J)
    print(f"{'joint type':24} {'bracket':26} {'count'}")
    print("-" * 60)
    for (kind, br), n in sorted(c.items(), key=lambda t: (t[0][0], str(t[0][1]))):
        print(f"{kind:24} {br or 'none (end tap only)':26} {n:>5}")
    used = Counter(j["bracket"] for j in J if j["bracket"])
    print(f"\ngussets used {used['gusset']} of {GUSSET['qty']}   "
          f"hidden used {used['hidden']} of {HIDDEN['qty']}   "
          f"unbraced joints {sum(1 for j in J if not j['bracket'])}")

    print(f"\n{'piece':10} {'member':8} {'fastener':>16} {'bracket reach':>14} {'clearance':>10}")
    print("-" * 64)
    worst = 1e9
    for piece, member, x, y, reach, gap in clearances():
        worst = min(worst, gap)
        print(f"{piece:10} {member:8} {str((x, y)):>16} {reach:>12.0f} mm {gap:>8.1f} mm")
    print(f"\nworst clearance between any bracket and any sheet fastener: {worst:.1f} mm")
    assert worst > 0, "a bracket fouls a sheet fastener"
    print("no bracket touches a sheet fastener")
