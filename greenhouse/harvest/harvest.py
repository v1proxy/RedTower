"""Maag harvest: where cut leaves go. One model for the booklet and the cut files.

Two destinations, the way the Herb Snip sorts every cut:

    dead leaves   down, into the DEAD-LEAF TRAY in the base bay. A bent 5052
                  tray hung by its rims on two guide rails bolted to the base
                  pan with the pan's own bolts; a printed handle stands up off
                  its front wall, with a slot the whole hand goes through.
                  Open the bottom-left door, slide it out.

    harvest       out, through the right panel, into the SIDE FEEDER at tier B:
                  two printed compartments outside the cabinet, leaves and
                  veggies, each with a lift-out tray, under one clear inclined
                  lid on a piano hinge. Built after the side feeders of a bird
                  cage: you collect from outside without opening the doors.

Coordinates are cabinet.py's: x 0..1397 left to right seen from the front,
y 0..559 with y = 0 the FRONT face, z 0..1829, floor at z = -20.

The feeder is parametric: FEEDER = Feeder(side="right", tier="B"). The modular
cabinet puts it on the left with side="left": the model mirrors about the
cabinet's centre plane x = W / 2 and every cut file follows.

    python harvest.py        # every check, as a report
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "gantry"))
sys.path.insert(0, os.path.join(_HERE, "..", "frame"))
sys.path.insert(0, os.path.join(_HERE, "..", "enclosure"))
sys.path.insert(0, os.path.join(_HERE, "..", "booklet"))
sys.path.insert(0, _HERE)

from kit3d import extrude, merge, mv, rot, circle_pts, cylinder, box, revolve   # noqa: E402
import cabinet as C                                                               # noqa: E402
import enclosure as E                                                             # noqa: E402
import hardware as HW                                                             # noqa: E402
import csg                                                                        # noqa: E402

W, D, H, SER = C.W, C.D, C.H, C.SER
LV = C.LEVELS

# ------------------------------------------------------------------ sheet
T = 1.6002                      # 5052 H32 0.063 in, SendCutSend
BD = 2.438                      # their 90 degree bend deduction at 0.063 (sendcutsend/unfold.py)
PAN_TOP = SER + C.T_SHEET       # 41.6: the base pan's DOWN floor, top face
PAN_LIP = SER + C.LIP           # 65.0: its front lip, top edge
BOLT_X = (150.0, 650.0)         # the pan's own bolts the rails reuse (DOWN piece, front and back lines)
BOLT_Y = (C.PF_, C.PB_)         # 20, 539

# ------------------------------------------------------------------ guide rails
# A C-channel opening AWAY from the tray: bottom flange on the pan round the
# pan's bolt, web standing up beside the tray's side wall, top flange out
# again. The tray hangs on the top flanges by its two rims, so its floor rides
# 5 above the pan's front lip and slides straight out over it.
RAIL = dict(web=(170.0, 630.0),          # web faces toward the tray, left and right
            bottom=29.0, top=13.0,       # flange lengths, outside dimension from the web face
            run=118.4,                   # top face of the top flange: the tray's rims ride here
            y0=6.0, y1=550.0,            # rail ends: clear of the pan's lips and their bends
            stop=512.0, tab=138.0,       # back stop: the web stands up to z 138 from y 512
            hole=9.0)                    # round, M8 clearance (the pan's slot is 9 wide too)

# ------------------------------------------------------------------ the tray
TRAY = dict(x0=171.5, x1=628.5,          # outside of the side walls: 1.5 off each web
            y0=32.0, y1=512.0,           # outside of front and back walls; the back on the stops
            z0=70.0, h=50.0,             # floor's underside 5 over the lip; rims' top face at 120
            rim=13.0)                    # rims out from the side walls' outside face
HANDLE = dict(x0=325.0, x1=475.0, z0=74.0, z1=292.0,      # printed, bolted on the front wall
              plate=8.0, slot=(340.0, 460.0, 228.0, 270.0),
              bar=(6.0, 270.0, 292.0), frame_t=18.0,
              bolts=[(350.0, 95.0), (400.0, 95.0), (450.0, 95.0)])
RIM_Z = TRAY["z0"] + TRAY["h"]          # 120.0


def _flip_x(mesh, about):
    V, F = mesh
    V2 = V.copy()
    V2[:, 0] = 2 * about - V2[:, 0]
    return (V2, F[:, ::-1])


def rail_mesh(side):
    """One guide rail, placed. side 'L' or 'R'. Built as the right rail and
    mirrored about the tray's centre line for the left."""
    r = RAIL
    xw = r["web"][1]
    y0, y1, ys = r["y0"], r["y1"], r["stop"]
    holes = [circle_pts(r["hole"] / 2, 32, xw + 20.0, y) for y in BOLT_Y]
    bot = extrude(np.array([(xw, y0), (xw + r["bottom"], y0), (xw + r["bottom"], y1), (xw, y1)]), T,
                  z0=PAN_TOP, holes=holes)
    web_poly = np.array([(y0, PAN_TOP), (y1, PAN_TOP), (y1, r["tab"]), (ys + 1.0, r["tab"]),
                         (ys + 1.0, r["run"]), (y0, r["run"])])
    web = extrude(web_poly, T)                              # in (y, z), thickness along +w
    Vw, Fw = web
    web = (np.c_[xw + Vw[:, 2], Vw[:, 0], Vw[:, 1]], Fw[:, ::-1])
    top = box(r["top"], ys - y0 - 1.0, T, c=(xw, y0, r["run"] - T))
    m = merge(bot, web, top)
    return m if side == "R" else _flip_x(m, (r["web"][0] + r["web"][1]) / 2)


def tray_mesh():
    t = TRAY
    x0, x1, y0, y1, z0 = t["x0"], t["x1"], t["y0"], t["y1"], t["z0"]
    z1 = z0 + t["h"]
    floor = box(x1 - x0, y1 - y0, T, c=(x0, y0, z0))
    holes = [circle_pts(2.75, 24, x, z) for x, z in HANDLE["bolts"]]
    fw = extrude(np.array([(x0, z0), (x1, z0), (x1, z1 - T), (x0, z1 - T)]), T, holes=holes)
    V, F = fw
    front = (np.c_[V[:, 0], y0 + V[:, 2], V[:, 1]], F[:, ::-1])
    back = box(x1 - x0, T, t["h"] - T, c=(x0, y1 - T, z0))
    left = box(T, y1 - y0, t["h"] - T, c=(x0, y0, z0))
    right = box(T, y1 - y0, t["h"] - T, c=(x1 - T, y0, z0))
    rl = box(t["rim"], y1 - y0 - 4.0, T, c=(x0 - t["rim"], y0 + 2.0, z1 - T))
    rr = box(t["rim"], y1 - y0 - 4.0, T, c=(x1, y0 + 2.0, z1 - T))
    return merge(floor, front, back, left, right, rl, rr)


def handle_solid():
    """The printed handle, as a manifold solid in cabinet coordinates. Its back
    face (y = TRAY y0) bears on the tray's front wall."""
    h = HANDLE
    yb = TRAY["y0"]                       # back face, on the wall
    yp = yb - h["plate"]                  # front face of the plate
    ybar = h["bar"][0]
    sx0, sx1, sz0, sz1 = h["slot"]
    outline = csg.rrect(h["x0"], h["z0"], h["x1"], h["z1"], 16.0, 48)
    plate = csg.prism(outline, "y", yp, yb)
    fr = csg.prism(csg.rrect(h["x0"], sz0 - 12.0, h["x1"], h["z1"], 16.0, 48), "y", yb - h["frame_t"], yb)
    bar = csg.rbox(h["x0"] - 1, ybar, h["bar"][1] - 2.0, h["x1"] + 1, yb, h["z1"], 9.0, axis="x")
    clip_ = csg.prism(outline, "y", ybar - 1, yb + 1)
    body = csg.union(plate, fr, bar ^ clip_)
    slot = csg.prism(csg.rrect(sx0, sz0, sx1, sz1, (sz1 - sz0) / 2 - 0.5, 48), "y", ybar - 5, yb + 5)
    body = body - slot
    for x, z in h["bolts"]:
        body = body - csg.cyl(2.75, h["plate"] + 2, "y", c=(x, yp - 1, z))
        body = body - csg.hexprism(8.2, 5.5, "y", c=(x, yp - 0.01, z))
    return body


def handle_mesh():
    return csg.to_mesh(handle_solid())


# ------------------------------------------------------------------ fasteners
def rail_bolts(side, explode=0.0):
    """The pan's two bolts at this rail, now M8 x 16 through the rail's bottom
    flange, the pan and its washer (the UP piece's stack: 4.8)."""
    x = BOLT_X[0] if side == "L" else BOLT_X[1]
    out = []
    for y in BOLT_Y:
        top = PAN_TOP + T
        out.append(("bolt", mv(C.button_head(8, 16.0), x, y, top + 1.6 + explode)))
        out.append(("washer", mv(C.washer8(), x, y, top + explode * 0.6)))
    return out


def handle_bolts(explode=0.0):
    """Three M5 x 10 button heads from inside the tray, through the front wall
    and the handle into M5 nylocs sunk in hex pockets on the handle's face."""
    out = []
    yi = TRAY["y0"] + T                   # inside face of the front wall: the heads bear here
    yn = TRAY["y0"] - HANDLE["plate"] + 5.5   # pocket floor: the nyloc's bearing face
    for x, z in HANDLE["bolts"]:
        out.append(("bolt", mv(rot(HW.button_head(5, 10.0), rx=-math.pi / 2), x, yi + explode, z)))
        out.append(("nyloc", mv(rot(HW.nyloc(5), rx=math.pi / 2), x, yn - explode * 0.6, z)))
    return out


# ================================================================== the feeder
# Local frame (w, u, v): w out of the frame's outer face (w = 0 there; the
# panel's outer face is at w = E.OUT), u along the face (= cabinet y), v up (= z).
# side="right": x = W + w. side="left": x = -w (the modular cabinet's mirror).
REED = E.REED                                    # Honeywell 7939WG-WH, the doors' switch
LID_T = 4.5                                      # SendCutSend polycarbonate 0.177 in, clear: the doors' sheet
HINGE_LEN = 12.0 * 25.4                          # one McMaster 1658A15, as on the doors
TIER_Z = {"A": LV[1], "B": LV[2], "C": LV[3]}
OPEN_R = 25.0                                    # opening corners: a 30 bridge to print over
WELL = dict(hole=10.0, flange_d=14.0, flange_t=1.2, body_d=9.5, body_l=11.0)   # M4 rubber well nut, 1 to 4 grip


class Feeder:
    """Two printed compartments side by side on the outside of a side panel,
    one tray in each, one clear lid over both on a piano hinge."""

    MOD_W = HINGE_LEN / 2          # 152.4: two modules make the hinge's 12 in
    DEPTH = 170.0                  # back plate's back face to the outer wall's outer face
    WALL, FLOOR, BACK = 3.0, 3.0, 4.0
    HEIGHT = 250.0                 # the printer's 256 less 6
    LID_ANGLE = 30.0               # below horizontal, falling away from the panel
    OVERHANG = 15.0                # the lid past the outer wall: the finger lip
    SCREW_DZ = 13.2                # floor's underside below the rail's slot line
    NAMES = ("leaves", "veggies")

    def __init__(self, side="right", tier="B", u0=178.0, openings=((245.0, 325.0), (336.0, 416.0)),
                 open_v=(1015.0 - 985.2, 1175.0 - 985.2)):
        self.side, self.tier = side, tier
        self.face = side
        self.rail_v = TIER_Z[tier] + SER / 2                 # the tier's side-rail slot line, 985.2 at B
        self.vf = self.rail_v - self.SCREW_DZ                # module floor's underside, 972.0
        self.vt = self.vf + self.HEIGHT                      # back plate's top, 1222.0
        self.u0 = u0
        self.wb = E.OUT                                      # back plate's back face: on the panel
        self.mods = [(u0, u0 + self.MOD_W), (u0 + self.MOD_W, u0 + 2 * self.MOD_W)]
        self.openings = [(a, b, self.rail_v + open_v[0], self.rail_v + open_v[1]) for a, b in openings]
        th = math.radians(self.LID_ANGLE)
        self.d = np.array([math.cos(th), -math.sin(th)])      # down the lid, in (w, v)
        self.n = np.array([math.sin(th), math.cos(th)])       # the lid's upward normal
        self.pin = np.array([self.wb + self.BACK + E.KNUCKLE_R, self.vt])

    # ---- the lid line
    def lid_under(self, w):
        """v of the lid's underside at w: the line the side walls' top edges follow."""
        p0 = self.pin - (E.KNUCKLE_R + LID_T) * self.n
        s = (w - p0[0]) / self.d[0]
        return p0[1] + s * self.d[1]

    def lid_top(self, w):
        p0 = self.pin - E.KNUCKLE_R * self.n
        s = (w - p0[0]) / self.d[0]
        return p0[1] + s * self.d[1]

    @property
    def w_out(self):
        return self.wb + self.DEPTH                          # outer wall's outer face

    # ---- placement
    def to_world(self, mesh):
        V, F = mesh
        w, u, v = V[:, 0], V[:, 1], V[:, 2]
        if self.side == "right":
            return (np.c_[W + w, u, v], F)
        return (np.c_[-w, u, v], F[:, ::-1])

    def solid_to_world(self, s):
        if self.side == "right":
            return s.translate([W, 0, 0])
        return s.mirror([1, 0, 0])

    # ---- the printed module
    def module_solid(self, k):
        """Module k (0 front, 1 back) as a manifold solid in (w, u, v)."""
        a, b = self.mods[k]
        wb, wo = self.wb, self.w_out
        vf, vt = self.vf, self.vt
        t, fl, bk = self.WALL, self.FLOOR, self.BACK
        # side profile in (w, v): back plate up to vt, the lid line, the outer wall down
        wo_top = self.lid_under(wo)
        prof = [(wb, vf), (wo, vf), (wo, wo_top), (wb + bk, self.lid_under(wb + bk)), (wb + bk, vt), (wb, vt)]
        outer = csg.prism(prof, "y", a, b)
        # hollow: everything inside the walls, up through the lid line
        inner_prof = [(wb + bk, vf + fl), (wo - t, vf + fl), (wo - t, vt + 50), (wb + bk, vt + 50)]
        inner = csg.prism(inner_prof, "y", a + t, b - t)
        body = outer - inner
        # the arm's opening through the back plate
        for oa, ob, ov0, ov1 in self.openings:
            if a < (oa + ob) / 2 < b:
                body = body - csg.prism(csg.rrect(oa, ov0, ob, ov1, OPEN_R, 48), "x", wb - 1, wb + bk + 1)
        # screw holes: two M5 on the rail line, two M4 over the opening
        for u in self.screw_u(k):
            body = body - csg.cyl(2.9, bk + 2, "x", c=(wb - 1, u, self.rail_v))
        for u in self.top_u(k):
            body = body - csg.cyl(2.3, bk + 2, "x", c=(wb - 1, u, self.v_top_bolt))
            # counterbore on the back face for the well nut's flange
            body = body - csg.cyl(WELL["flange_d"] / 2 + 0.4, WELL["flange_t"] + 1.0, "x",
                                  c=(wb - 1.0, u, self.v_top_bolt))
        if k == 1:
            body = body - csg.cyl(4.0, bk + 2, "x", c=(wb - 1, self.wire_hole[0], self.wire_hole[1]))
        return body

    def screw_u(self, k):
        a, b = self.mods[k]
        return [a + 30.0, b - 32.4]

    def top_u(self, k):
        a, b = self.mods[k]
        return [a + 22.0, b - 22.0]

    @property
    def v_top_bolt(self):
        return self.vt - 30.0

    @property
    def wire_hole(self):
        """(u, v) of the reed switch's wire, through module 1's back plate and the panel."""
        return (self.mods[1][1] - 12.0, self.vt - 70.0)

    # ---- trays
    TRAY_GAP = 2.0
    TRAY_WALL = 2.4
    TRAY_H = 66.0

    def tray_box(self, k):
        a, b = self.mods[k]
        u0, u1 = a + self.WALL + self.TRAY_GAP, b - self.WALL - self.TRAY_GAP
        w0 = self.wb + self.BACK + 9.0                       # clear of the M5 heads on the back plate
        w1 = self.w_out - self.WALL - 27.0                   # a finger's width in front of it
        v0 = self.vf + self.FLOOR
        return w0, w1, u0, u1, v0, v0 + self.TRAY_H

    def tray_solid(self, k):
        w0, w1, u0, u1, v0, v1 = self.tray_box(k)
        t = self.TRAY_WALL
        outer = csg.rbox(w0, u0, v0, w1, u1, v1, 8.0, axis="z")
        inner = csg.rbox(w0 + t, u0 + t, v0 + 2.0, w1 - t, u1 - t, v1 + 5, 6.0, axis="z")
        body = outer - inner
        # a thumb notch in the outer wall's rim, to lift it by
        um = (u0 + u1) / 2
        body = body - csg.cyl(17.0, 12.0, "x", c=(w1 - 6.0, um, v1))
        return body

    # ---- lid, hinge, switch
    def lid_mesh(self):
        p0 = self.pin - (E.KNUCKLE_R + LID_T) * self.n + 4.0 * self.d
        s_end = (self.w_out + self.OVERHANG - p0[0]) / self.d[0]
        a, b = self.mods[0][0], self.mods[1][1]
        c0 = p0
        c1 = p0 + s_end * self.d
        quad = np.array([c0, c1, c1 + LID_T * self.n, c0 + LID_T * self.n])
        m = extrude(quad, b - a)                               # (w, v) profile, along +u
        V, F = m
        return (np.c_[V[:, 0], a + V[:, 2], V[:, 1]], F[:, ::-1])

    def lid_flat(self):
        """The lid as cut: (length down the slope, width)."""
        p0 = self.pin - (E.KNUCKLE_R + LID_T) * self.n + 4.0 * self.d
        s_end = (self.w_out + self.OVERHANG - p0[0]) / self.d[0]
        return s_end, self.mods[1][1] - self.mods[0][0]

    def hinge_mesh(self, open_deg=0.0):
        """Fixed leaf on the back plate's outer face, knuckle, lid leaf on the lid's top face."""
        a, b = self.mods[0][0], self.mods[1][1]
        L = b - a
        lw, lt, r = E.LEAF_W - E.KNUCKLE_R, E.LEAF_T, E.KNUCKLE_R
        fixed = box(lt, L, lw, c=(self.wb + self.BACK, a, self.pin[1] - r - lw))
        kn = cylinder(r, L, n=20)
        kn = (np.c_[kn[0][:, 0] + self.pin[0], kn[0][:, 2] + a, kn[0][:, 1] + self.pin[1]], kn[1])
        q0 = self.pin + r * self.d - r * self.n
        quad = np.array([q0, q0 + lw * self.d, q0 + lw * self.d + lt * self.n, q0 + lt * self.n])
        lm = extrude(quad, L)
        lid_leaf = (np.c_[lm[0][:, 0], a + lm[0][:, 2], lm[0][:, 1]], lm[1][:, ::-1])
        if open_deg:
            lid_leaf = self.swing(lid_leaf, open_deg)
        return merge(fixed, kn), lid_leaf

    def lid_rest_deg(self):
        """How far the lid opens before its far edge, top face, leans on the panel."""
        L, _ = self.lid_flat()
        s_end = L + 4.0
        for k in range(0, 1800):
            a = math.radians(k / 10.0)
            th = math.radians(-self.LID_ANGLE) + a
            d = np.array([math.cos(th), math.sin(th)])
            n = np.array([-math.sin(th), math.cos(th)])
            far = self.pin - E.KNUCKLE_R * n + s_end * d
            if far[0] <= self.wb + 1e-6:
                return k / 10.0
        return 180.0

    def swing(self, mesh, deg):
        """Turn a lid-side mesh about the hinge pin, opening upward by deg."""
        V, F = mesh
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        p = self.pin
        dw, dv = V[:, 0] - p[0], V[:, 2] - p[1]
        # opening turns the lid toward the panel: counter-clockwise seen with w right, v up
        w2 = p[0] + c * dw - s * dv
        v2 = p[1] + s * dw + c * dv
        return (np.c_[w2, V[:, 1], v2], F)

    def reed_switch(self):
        """Switch on the inner face of module 1's back side wall, under the lid;
        its magnet on the lid's underside above it. Returns (switch, magnet) in (w, u, v)."""
        sw, mg = REED["sw"], REED["mag"]
        u_wall = self.mods[1][1] - self.WALL
        wc = self.w_out - 50.0
        # the switch's top face 15 under the lid, both inclined with it
        top = self.lid_under(wc) - 15.0
        swm = box(sw[0], sw[2], sw[1], c=(wc - sw[0] / 2, u_wall - sw[2], top - sw[1]))
        mgm = box(mg[0], mg[1], mg[2], c=(wc - mg[0] / 2, u_wall - mg[1] - 1.0, self.lid_under(wc) - mg[2]))
        return swm, mgm

    def magnet_place(self):
        """Where the lid's magnet goes, measured on the lid as cut: (down the lid
        from its hinge edge, in from its back end), to the magnet's centre."""
        sw, mg = self.reed_switch()
        c = mg[0].mean(0)
        p0 = self.pin - (E.KNUCKLE_R + LID_T) * self.n + 4.0 * self.d
        along = float((c[0] - p0[0]) / self.d[0])
        return round(along, 0), round(float(self.mods[1][1] - c[1]), 0)

    # ---- fasteners
    def screws(self):
        """[(kind, (w, u, v), M, L)]: M5 x 20 on the rail line into the rail's
        T-nuts; over the openings, where no frame is behind the panel, M4 x 20
        into rubber well nuts set in the panel from outside: nothing to reach
        inside the cabinet for."""
        out = []
        for k in (0, 1):
            for u in self.screw_u(k):
                out.append(("m5", (self.wb + self.BACK, u, self.rail_v), 5, 20.0))
            for u in self.top_u(k):
                out.append(("m4", (self.wb + self.BACK, u, self.v_top_bolt), 4, 20.0))
        return out

    def screw_stacks(self):
        """What each screw clamps and how far it reaches past it."""
        m5 = self.BACK + E.T_PANEL + E.TAPE + E.WASH["t"]
        m4 = self.BACK
        return {"M5 x 20, rail": dict(stack=round(m5, 3), reach=round(20.0 - m5, 2),
                                      past_lips=round(20.0 - m5 - C.SLOT_LIP, 2),
                                      spare=round(C.SLOT_DEPTH - (20.0 - m5), 2)),
                "M4 x 20, well nut": dict(stack=round(m4, 2), past_plate=round(20.0 - m4, 2),
                                          nut_reach=round(WELL["flange_t"] + WELL["body_l"], 2))}

    def panel_holes(self):
        """[(u, v, dia, what)] the feeder adds to its side panel (face coordinates)."""
        out = []
        for kind, (w, u, v), M, L in self.screws():
            out.append((u, v, E.HOLE if M == 5 else WELL["hole"], "feeder M5" if M == 5 else "feeder well nut"))
        out.append((self.wire_hole[0], self.wire_hole[1], 8.0, "reed wire"))
        return out

    def panel_cutouts(self):
        """[(u0, v0, u1, v1, r, what)] rectangular cut-outs for the arm."""
        return [(a, v0, b, v1, OPEN_R, "feeder opening") for a, b, v0, v1 in self.openings]


FEEDER = Feeder()


# ================================================================== placed, for drawing
def tray_meshes(out=0.0, handle=True, bolts=True):
    """{name: mesh} for the tray slid out toward the front by `out`."""
    sh = lambda m: mv(m, 0, -out, 0)                         # noqa: E731
    d = {"tray": sh(tray_mesh())}
    if handle:
        d["handle"] = sh(handle_mesh())
    if bolts:
        for k, (kind, m) in enumerate(handle_bolts()):
            d[f"handle_{kind}_{k}"] = sh(m)
    return d


def rail_meshes(bolts=True, explode=0.0):
    d = {"rail_L": rail_mesh("L"), "rail_R": rail_mesh("R")}
    if bolts:
        for side in "LR":
            for k, (kind, m) in enumerate(rail_bolts(side, explode)):
                d[f"rail_{kind}_{side}{k}"] = m
    return d


def well_nut_mesh():
    """Rubber well nut, in its own frame: flange on z = 0 (on the panel's outer
    face), the body down to -body_l with its brass nut at the far end."""
    w = WELL
    fl = cylinder(w["flange_d"] / 2, w["flange_t"], n=32)
    bd = cylinder(w["body_d"] / 2, w["body_l"], n=32, c=(0, 0, -w["body_l"]))
    return merge(fl, bd)


def _along_w(mesh, f, w, u, v, head_out=True):
    """A fastener built along +z (head up) laid along the feeder's w axis, head
    toward +w (outward), then placed."""
    m = rot(mesh, ry=math.pi / 2)            # +z -> +x
    return f.to_world(mv(m, w, u, v))


def feeder_meshes(f=None, open_deg=0.0, trays=True, lid=True, fasteners=True, explode=0.0):
    """{name: mesh} for the feeder on its panel, world coordinates."""
    f = f or FEEDER
    d = {}
    for k, nm in enumerate(f.NAMES):
        d[f"module_{nm}"] = f.to_world(csg.to_mesh(f.module_solid(k)))
        if trays:
            d[f"tray_{nm}"] = f.to_world(csg.to_mesh(f.tray_solid(k)))
    if lid:
        lm = f.lid_mesh()
        fixed, leaf = f.hinge_mesh()
        sw, mg = f.reed_switch()
        if open_deg:
            lm, leaf, mg = f.swing(lm, open_deg), f.swing(leaf, open_deg), f.swing(mg, open_deg)
        d["lid"] = f.to_world(lm)
        d["hinge_fixed"] = f.to_world(fixed)
        d["hinge_lid"] = f.to_world(leaf)
        d["reed_switch"] = f.to_world(sw)
        d["reed_magnet"] = f.to_world(mg)
    if fasteners:
        for i, (kind, (w, u, v), M, L) in enumerate(f.screws()):
            if kind == "m5":
                d[f"m5_{i}"] = _along_w(HW.button_head(5, L), f, w + E.WASH["t"] + explode, u, v)
                d[f"washer_{i}"] = _along_w(E.washer9021(), f, w + explode * 0.6, u, v)
            else:
                d[f"m4_{i}"] = _along_w(HW.button_head(4, L), f, w + explode, u, v)
                d[f"wellnut_{i}"] = _along_w(well_nut_mesh(), f, E.OUT, u, v)
    return d


# ================================================================== checks
def _gantry_low(x0, x1, y0, y1):
    """Lowest point of the gantry (no arm) over a floor footprint, over the X travel."""
    import frame as GF
    import arm280 as A
    keep = A.pose
    A.pose = lambda *a, **k: []
    try:
        low = 1e9
        for xc in np.linspace(GF.X_MIN, GF.X_MAX, 7):
            for p in GF.gantry_parts(xc, GF.MAST_Z0 + 80.0):
                V = p.mesh[0]
                m = (V[:, 0] > x0) & (V[:, 0] < x1) & (V[:, 1] > y0) & (V[:, 1] < y1)
                if m.any():
                    low = min(low, float(V[m, 2].min()))
    finally:
        A.pose = keep
    return low


def tray_checks():
    t, r, h = TRAY, RAIL, HANDLE
    out = {}
    out["floor over the pan's front lip"] = round(t["z0"] - PAN_LIP, 2)
    out["rim, rail tops under the gantry"] = round(_gantry_low(t["x0"] - t["rim"], t["x1"] + t["rim"], r["y0"], r["y1"])
                                                   - r["tab"], 1)
    out["handle under rail F1"] = round(LV[1] - h["z1"], 1)
    out["handle grip behind the door"] = round(h["bar"][0] + E.GAP_F, 2)
    ast = W / 2 - E.ASTRAGAL["w"] / 2
    out["tray past the astragal, left door only"] = round(ast - (t["x1"] + t["rim"]), 1)
    out["left rail off the leak sensor (x 125)"] = round(r["web"][0] - r["bottom"] - 125.0, 1)
    out["right rail off the pan's UP piece"] = round(C.MID[0] - (r["web"][1] + r["bottom"]), 1)
    out["side play, each side"] = round(t["x0"] - r["web"][0], 2)
    out["pan's middle bolt heads under the floor"] = round(t["z0"] - (PAN_TOP + 2 * T + HW.BUTTON[8][1]), 1)
    stack = T + C.T_SHEET + 1.6
    out["rail bolt M8 x 16: stack, reach, spare"] = (round(stack, 2), round(16 - stack, 2),
                                                     round(C.SLOT_DEPTH - (16 - stack), 2))
    out["hand slot"] = (h["slot"][1] - h["slot"][0], h["slot"][3] - h["slot"][2])
    vol = (t["x1"] - t["x0"] - 2 * T) * (t["y1"] - t["y0"] - 2 * T) * (t["h"] - T) / 1e6
    out["tray volume, litres"] = round(vol, 1)
    return out


def feeder_checks(f=None):
    f = f or FEEDER
    out = {}
    w0, w1, u0, u1, v0, v1 = f.tray_box(0)
    out["module, mm (print bed 256)"] = (round(f.MOD_W, 1), round(f.DEPTH, 1), round(f.HEIGHT, 1))
    out["tray, mm"] = (round(w1 - w0, 1), round(u1 - u0, 1), round(v1 - v0, 1))
    out["opening, u x v"] = [(round(b - a), round(c1 - c0)) for a, b, c0, c1 in f.openings]
    out["opening sill over the rail below"] = round(f.openings[0][2] - (f.rail_v + SER / 2), 1)
    out["tray rim over the sill"] = round(v1 - f.openings[0][2], 1)
    out["lid at the outer wall, at the back plate"] = (round(float(f.lid_under(f.w_out)), 1),
                                                       round(float(f.lid_under(f.wb + f.BACK)), 1))
    sw, mg = f.reed_switch()
    out["reed gap (7939WG works to 32)"] = round(float(mg[0][:, 2].min() - sw[0][:, 2].max()), 1)
    out["screws"] = f.screw_stacks()
    L, Wd = f.lid_flat()
    out["lid, cut"] = (round(float(Wd), 1), round(float(L), 1))
    # the open lid leans on the panel: its top edge against anything on the panel above
    top_edge = f.pin[1] + L
    above = [c for c in E.cutouts(f.face) if c[1] > f.vt and f.mods[0][0] - 20 < c[0] < f.mods[1][1] + 20]
    out["open lid's top edge, below the next thing on the panel"] = round(float(min([c[1] - c[2] / 2 for c in above]
                                                                                 + [1e9]) - top_edge), 1)
    fps = E.footprints(f.face)
    me = [a for k, a in fps if k == "feeder"][0]
    gaps = sorted((round(E._gap(me, a), 1), k) for k, a in fps if k != "feeder")
    out["feeder to the next thing on the panel's outside"] = gaps[0]
    out["openings into the bay, tightest"] = E.cutout_report()[f.face]
    vols = [f.module_solid(k).volume() / 1000 for k in (0, 1)] + [2 * f.tray_solid(0).volume() / 1000]
    out["printed, cm3 solid (modules, trays)"] = [round(v) for v in vols]
    return out


if __name__ == "__main__":
    print("dead-leaf tray")
    for k, v in tray_checks().items():
        print(f"  {k:46s} {v}")
    print("side feeder", FEEDER.side, FEEDER.tier)
    for k, v in feeder_checks().items():
        print(f"  {k:46s} {v}")
