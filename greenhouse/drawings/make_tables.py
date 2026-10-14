#!/usr/bin/env python3
"""Rev 5 drawing tables: the bracket schedule, the hardware, and what it does to the BOM."""
from collections import OrderedDict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import brackets as BK

INK, LINE, DIM, WARN, OK = "#1B2629", "#5E6E70", "#1F6F8B", "#B3261E", "#2E7D5B"
BAND, RULE = "#EEF2F1", "#C6D0CE"
MONO = "DejaVu Sans Mono"
USD = r"\$"


def esc(s):
    return str(s).replace("$", USD)


class Sheet:
    """Stacks tables down one figure, measuring in rows rather than in fractions."""

    def __init__(self, fig, left=.045, right=.965, top=.922, row=.0148, gap=1.9):
        self.fig, self.L, self.R, self.y = fig, left, right, top
        self.row, self.gap = row, gap

    def table(self, title, cols, xs, rows, note="", colours=None, fs=7.9):
        nl = note.count("\n") + 1 if note else 0
        h = (len(rows) + 3.0 + nl * .9) * self.row
        ax = self.fig.add_axes([self.L, self.y - h, self.R - self.L, h])
        self.y -= h + self.gap * self.row
        ax.axis("off")
        ax.set_xlim(0, 1)
        ax.set_ylim(-(len(rows) + 1.0 + nl * .9), 2.0)
        ax.text(0, 1.15, title, fontsize=10.5, fontweight="bold", color=INK, va="bottom")
        right = [c.startswith("#") for c in cols]
        ax.plot([0, 1], [.42, .42], color=INK, lw=1.1)
        for x, c, r in zip(xs, cols, right):
            ax.text(x, .62, c.lstrip("#"), fontsize=fs, color=LINE, va="bottom",
                    ha="right" if r else "left")
        for i, rw in enumerate(rows):
            y = -i
            if i % 2 == 1:
                ax.add_patch(plt.Rectangle((0, y - .42), 1, .9, fc=BAND, ec="none",
                                           zorder=0))
            for j, (x, cell) in enumerate(zip(xs, rw)):
                ax.text(x, y, esc(cell), fontsize=fs,
                        color=(colours or {}).get((i, j), INK), va="center",
                        ha="right" if right[j] else "left",
                        family=MONO if right[j] else None)
        ax.plot([0, 1], [-len(rows) + .42, -len(rows) + .42], color=RULE, lw=.9)
        if note:
            ax.text(0, -len(rows) + .05, esc(note), fontsize=7.4, color=LINE,
                    va="top", linespacing=1.55)
        return ax


J = BK.allocate()

NAME = {"gusset": "3540 external gusset", "hidden": "hidden inside connector",
        None: "none, end tap + M8 only"}
FACE = {"gusset": "hangs under the rail, leg down the mating face",
        "hidden": "inside the 8 mm slot of both profiles", None: "-"}
REACH = {"gusset": "35", "hidden": "38", None: "-"}
WHERE = {
    ("longitudinal", "gusset"): "levels 304.8 / 965.2 / 1397 / 1789",
    ("longitudinal", None): "level 0, on the floor",
    ("mid rail", "gusset"): "levels 965.2 / 1397",
    ("mid rail", "hidden"): "level 0 and level 304.8",
    ("shelf rail", "hidden"): "all three tiers, both ends",
    ("side member", None): "all five levels, both ends",
}

grp = OrderedDict()
for j in J:
    k = (j["kind"], j["bracket"])
    grp[k] = grp.get(k, 0) + 1
t1 = [(kind, NAME[br], n, FACE[br], REACH[br], WHERE[(kind, br)])
      for (kind, br), n in grp.items()]
t1.sort(key=lambda r: (r[1] == NAME[None], r[0]))
c1 = {(i, 1): (LINE if r[1] == NAME[None] else INK) for i, r in enumerate(t1)}

t2 = [("3540 external gusset", "PETOX", "B0BS6LNVS9", 20, "$29.99",
       "40 wide, 35 legs, 6 plate, holes 20 from the inside corner",
       "40 M8x16, 40 T-nut, 40 washer"),
      ("hidden inside connector", "TOCLUX", "B0F18V8KTS", 10, "$16.99",
       "L block 7.8 across, sits 11 to 19 mm deep in the slot",
       "20 M6 grub screw, wrench")]

t3 = [(name, n, state, note) for name, n, state, _, _, note in BK.hardware()]
c3 = {(i, 2): (OK if r[2] == "owned" else WARN) for i, r in enumerate(t3)}

cl = sorted(BK.clearances(), key=lambda r: r[5])[:7]
t4 = [(p, m.lower(), f"({x:.0f}, {y:.0f})", f"{r:.0f}" if r else "none",
       f"{g:.1f}") for p, m, x, y, r, g in cl]
c4 = {(i, 4): (WARN if float(r[4]) < 25 else INK) for i, r in enumerate(t4)}

t5 = [("G004", "Corner brackets 40-4302, 64 off at $5.31", "-339.84", "drop",
       "replaced by the 30 brackets already delivered"),
      ("G004a", "PETOX 3540 gusset, 20 off", "+29.99", "add", "owned"),
      ("G004b", "TOCLUX hidden connector, 10 off", "+16.99", "add", "owned"),
      ("G005", "T-nuts, was 250 off at $0.53", "-79.50", "revise",
       "100 needed: 60 sheets + 40 gussets"),
      ("", "net against Rev E", "-372.36", "", "before the two decisions below"),
      ("G004c", "2 more PETOX sets, braces the last 24 joints", "+59.98", "decide",
       "40 more gussets, all 54 joints braced"),
      ("G005a", "60 drop-in M8 T-nuts for the sheets", "+?", "decide",
       "a slide-in nut cannot be added once the frame is closed")]
c5 = {(i, 3): {"drop": WARN, "add": OK, "decide": DIM, "revise": DIM}.get(r[3], INK)
      for i, r in enumerate(t5)}

fig = plt.figure(figsize=(13.4, 11.0), facecolor="#FBFCFA")
fig.suptitle("Herb Tower  ·  bracket and fastener schedule  ·  Rev 5",
             fontsize=15, fontweight="bold", color=INK, x=.045, ha="left", y=.988)
fig.text(.045, .972,
         "27 horizontal members, 54 end joints. The 30 brackets already delivered cover 30 of them; the other 24 hold on the end tap and the M8 alone.\n"
         "Nothing mounts on a top face, so no bracket touches a tray, a pan, or the slot a sheet fastener needs. Closest approach anywhere: 16 mm.",
         fontsize=8.4, color=LINE, va="top", linespacing=1.6)

S = Sheet(fig)
S.table("1   bracket by joint",
        ["joint type", "bracket", "#qty", "mounts on", "#reach mm", "where"],
        [.00, .135, .345, .375, .715, .745], t1,
        "Every gusset hangs under its rail. Level 0 sits on the floor, so its eight perimeter joints have nothing below them to bolt to. They do not\n"
        "need a bracket: the base pan, 1397 x 457 of 1.6 mm sheet with a 25 mm upstand on every edge and sixteen bolts, is the diaphragm that braces them.",
        colours=c1)

S.table("2   what the two brackets are",
        ["bracket", "brand", "ASIN", "#off", "#price", "geometry, mm", "in the box"],
        [.00, .175, .235, .335, .405, .435, .735], t2,
        "Both are 40 series, slot 8. The gusset's holes sit 20 mm from the inside corner, which is exactly the slot centreline of both profiles, so it\n"
        "needs no drilling anywhere. The hidden connector shows nothing outside the profile and projects nothing past its face.")

S.table("3   fastener schedule, regenerated",
        ["item", "#qty", "owned or to buy", "note"],
        [.00, .265, .295, .445], t3,
        "64 slots but 60 fasteners: over the 40 mm lap the UP piece lies on top of the DOWN piece and one bolt pierces both into a single T-nut, four\n"
        "times. The UP piece is then propped 1.6 mm proud, so each of its other seven fasteners takes an M8 flat washer, DIN 125, as the shim.",
        colours=c3)

S.table("4   tightest bracket-to-fastener clearances",
        ["piece", "lands on", "#slot x, y", "#bracket reach mm", "#clearance mm"],
        [.00, .135, .345, .545, .70], t4,
        "Measured from the near edge of the 18 mm slot to the end of the bracket's reach along the same channel. The two 16 mm cases are the lap\n"
        "bolt on a tier mid rail, which is only 123 mm long and carries a gusset at each end. The T-nut bodies themselves clear by 22.6 mm.",
        colours=c4)

S.table("5   what this changes in the BOM",
        ["line", "item", "#USD", "action", "note"],
        [.00, .07, .55, .60, .70], t5,
        "The open question is the T-nut. 80/20's own 40 series nut, part 40-1984, is 15.88 mm across the T, which is 0.625 in; the 40 EU slot-8 nuts in\n"
        "the PETOX box are 16 mm nominal, and several 80/20 owners report they will not enter the channel. That decides the frame, not just the nut.",
        colours=c5)

fig.text(.955, .012, "Rev 5  ·  2026-10-10", fontsize=7.5, color=LINE, ha="right")
fig.savefig("bracket_tables_rev5.png", dpi=150, facecolor="#FBFCFA")
print("ok", len(J), "joints")
