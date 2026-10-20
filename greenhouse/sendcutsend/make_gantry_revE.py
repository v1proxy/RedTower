#!/usr/bin/env python3
"""SendCutSend cut files for the gantry, Rev E.

  arm_plate_revB.dxf       6061-T6 0.250 in, 1 off. Cut, tap, countersink.
  rail_bracket_top.dxf     5052-H32 0.125 in, 2 off. Cut and one 90 deg bend.
  rail_bracket_bottom.dxf  5052-H32 0.125 in, 2 off. Cut and one 90 deg bend.

Hole sizes are SendCutSend's own drawing sizes, not nominal:
  tapped M3 x 0.5  -> draw 2.60   tapped M4 x 0.7 -> draw 3.41
  countersunk M5 90 deg -> draw the 5.00 minor hole only (they cut 10.0 x 2.44 deep)
  plain M5 clearance -> 5.50

The bracket files carry the cut outline and holes only, as SendCutSend asks.
The bend line position is printed below for entering in their app, and drawn in
rail_bracket_*_bends.dxf for reference (never upload that one).

Geometry source: greenhouse/gantry/parts.py (arm_plate, rail_bracket_flat),
the same functions the assembly booklet draws.
"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "gantry"))
import parts as P

# DXF writer, the same as make_dxf.py's (that module writes the tray files on import)
class Dxf:
    def __init__(self):
        self.e = []

    def line(self, p, q, dashed=False):
        self.e.append(("LINE", p, q, dashed))

    def arc(self, c, r, a0, a1):
        self.e.append(("ARC", c, r, a0, a1))

    def circle(self, c, r):
        self.e.append(("CIRCLE", c, r))

    def dumps(self):
        o = ["0", "SECTION", "2", "HEADER",
             "9", "$INSUNITS", "70", "4",
             "9", "$MEASUREMENT", "70", "1",
             "0", "ENDSEC",
             "0", "SECTION", "2", "TABLES",
             "0", "TABLE", "2", "LTYPE", "70", "2",
             "0", "LTYPE", "2", "CONTINUOUS", "70", "0", "3", "Solid line",
             "72", "65", "73", "0", "40", "0.0",
             "0", "LTYPE", "2", "DASHED", "70", "0", "3", "Dashed",
             "72", "65", "73", "2", "40", "9.0", "49", "6.0", "49", "-3.0",
             "0", "ENDTAB",
             "0", "TABLE", "2", "LAYER", "70", "1",
             "0", "LAYER", "2", "0", "70", "0", "62", "7", "6", "CONTINUOUS",
             "0", "ENDTAB", "0", "ENDSEC",
             "0", "SECTION", "2", "ENTITIES"]
        for ent in self.e:
            if ent[0] == "LINE":
                _, p, q, dashed = ent
                o += ["0", "LINE", "8", "0", "6", "DASHED" if dashed else "CONTINUOUS",
                      "10", f"{p[0]:.4f}", "20", f"{p[1]:.4f}", "30", "0.0",
                      "11", f"{q[0]:.4f}", "21", f"{q[1]:.4f}", "31", "0.0"]
            elif ent[0] == "ARC":
                _, c, r, a0, a1 = ent
                o += ["0", "ARC", "8", "0", "6", "CONTINUOUS",
                      "10", f"{c[0]:.4f}", "20", f"{c[1]:.4f}", "30", "0.0",
                      "40", f"{r:.4f}", "50", f"{a0:.4f}", "51", f"{a1:.4f}"]
            else:
                _, c, r = ent
                o += ["0", "CIRCLE", "8", "0", "6", "CONTINUOUS",
                      "10", f"{c[0]:.4f}", "20", f"{c[1]:.4f}", "30", "0.0",
                      "40", f"{r:.4f}"]
        o += ["0", "ENDSEC", "0", "EOF"]
        return "\n".join(o) + "\n"


TAP_M3, TAP_M4, CSK_M5, CLR_M5 = 2.60, 3.41, 5.00, 5.50


def rrect(d, w, h, r, cx=0.0, cy=0.0):
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    d.line((x0 + r, y0), (x1 - r, y0)); d.arc((x1 - r, y0 + r), r, 270, 360)
    d.line((x1, y0 + r), (x1, y1 - r)); d.arc((x1 - r, y1 - r), r, 0, 90)
    d.line((x1 - r, y1), (x0 + r, y1)); d.arc((x0 + r, y1 - r), r, 90, 180)
    d.line((x0, y1 - r), (x0, y0 + r)); d.arc((x0 + r, y0 + r), r, 180, 270)


def arm_plate():
    d = Dxf()
    rrect(d, 160.0, 160.0, 12.0)
    d.circle((0, 0), 11.0)                                   # cable pass, 22
    for x, y in P.ARM_GBASE_HOLES:
        d.circle((x, y), TAP_M3 / 2)                         # G base, tap M3
    for x, y in P.ARM_BASE_HOLES:
        d.circle((x, y), TAP_M4 / 2)                         # bare arm, tap M4
    for x, y in P.ARM_PLATE_CSK:
        d.circle((x, y), CSK_M5 / 2)                         # to the XL plate, csk M5
    return d


def bracket(kind):
    L, holes, bend_y, BA = P.rail_bracket_flat(kind)
    W = P.RB_W
    d = Dxf()
    d.line((0, 0), (W, 0)); d.line((W, 0), (W, L)); d.line((W, L), (0, L)); d.line((0, L), (0, 0))
    for x, y, dia in holes:
        d.circle((x, y), CLR_M5 / 2)
    ref = Dxf()
    for e in d.e:
        ref.e.append(e)
    ref.line((0, bend_y), (W, bend_y), dashed=True)
    return d, ref, L, bend_y, holes


if __name__ == "__main__":
    out = []
    open(os.path.join(HERE, "arm_plate_revB.dxf"), "w").write(arm_plate().dumps())
    out.append("arm_plate_revB.dxf      160 x 160, 6061-T6 0.250: tap M3 x4 (2.60 drawn), tap M4 x4 (3.41), "
               "countersink M5 90 deg x4 on the ARM side (5.00 drawn)")
    for kind in ("top", "bottom"):
        d, ref, L, by, holes = bracket(kind)
        open(os.path.join(HERE, f"rail_bracket_{kind}.dxf"), "w").write(d.dumps())
        open(os.path.join(HERE, f"rail_bracket_{kind}_bends.dxf"), "w").write(ref.dumps())
        La, Lb = P.RB_KIND[kind][:2]
        out.append(f"rail_bracket_{kind}.dxf  flat {P.RB_W:.1f} x {L:.2f}, 5052-H32 0.125, one 90 deg bend at "
                   f"{by:.2f} from the leg-A end, legs {La:.0f} x {Lb:.0f} outside, inside radius = t")
    print("\n".join(out))
