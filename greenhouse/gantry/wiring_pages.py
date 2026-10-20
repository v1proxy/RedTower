"""Gantry wiring pages for the Rev E booklet (schematics, not 3D views).

Sources for terminal names and ratings:
  Omron G9SE datasheet: A1/A2 supply, T11-T12 and T21-T22 the two input
    channels, manual reset = 24 V on T33 with an NO switch from T31 to T32,
    outputs 13-14 and 23-24 (5 A 30 V DC resistive, DC13 1.5 A, fuse <= 8 A),
    X1 a PNP auxiliary output, 100 mA, NOT a safety output.
  Elecrow 4X 2209 (FluidNC): 6 inputs, 2 x 3 A MOSFET outputs, 4 x TMC2209 on
    UART, USB-C. GPIO numbers are deliberately not printed: they come from the
    board's own FluidNC config.
"""
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle

INK = "#15191c"
DIM = "#5b6770"
W24 = "#c2410c"      # +24 V, fused
W24S = "#a16207"     # +24 V after the safety relay
WGND = "#1f2937"     # 0 V
WSIG = "#2563eb"     # signal
WSAFE = "#7c3aed"    # safety loop
MOT = {"A+": "#111111", "A-": "#15803d", "B+": "#dc2626", "B-": "#2563eb"}
_TF = ["IBM Plex Mono"]          # set from the booklet's TITLE_FONT when a page is drawn


def box(ax, x, y, w, h, title, sub="", title_at="top", tx=10):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=6",
                                facecolor="#f5f7f8", edgecolor="#9aa7b0", lw=1.1, zorder=20))
    ty = y + h - 16 if title_at == "top" else y + 44
    ax.text(x + tx, ty, title, fontsize=9.2, fontweight="semibold", family=_TF[0], color=INK, zorder=51)
    if sub:
        ax.text(x + tx, ty - 9, sub, fontsize=7.6, color=DIM, zorder=51, va="top",
                linespacing=1.35)


def term(ax, x, y, name, where="l", fs=7.8):
    """Terminal dot on a box face, label inside the box:
    'l' left face, 'r' right face, 'b' bottom face (label above)."""
    ax.add_patch(Circle((x, y), 3.6, facecolor="white", edgecolor=INK, lw=1.0, zorder=60))
    if name:
        dx, dy, ha, va = {"l": (8, 0, "left", "center"), "r": (-8, 0, "right", "center"),
                          "b": (0, 9, "center", "bottom"), "t": (0, -9, "center", "top")}[where]
        ax.text(x + dx, y + dy, name, fontsize=fs, color=INK, ha=ha, va=va, zorder=61)
    return (x, y)


def wire(ax, pts, color, lw=1.7):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=lw, zorder=40, solid_capstyle="round",
            solid_joinstyle="round")


def dot(ax, p, color):
    ax.add_patch(Circle(p, 3.0, facecolor=color, edgecolor="none", zorder=45))


def lab(ax, x, y, s, color, ha="left", va="bottom", fs=7.4):
    ax.text(x, y, s, fontsize=fs, color=color, ha=ha, va=va, zorder=62, linespacing=1.3,
            bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.92))


def off_page(ax, x, y, color):
    ax.annotate("", xy=(x + 10, y), xytext=(x - 4, y),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.4, mutation_scale=11),
                zorder=46)


def nc_contact(ax, x0, x1, y, color=INK):
    """Normally closed: the blade rests against the far contact's hook."""
    for x in (x0, x1):
        ax.add_patch(Circle((x, y), 2.6, color=color, zorder=58))
    ax.plot([x0, x1 + 3], [y, y - 6], color=color, lw=1.5, zorder=58)
    ax.plot([x1, x1], [y, y - 9], color=color, lw=1.2, zorder=58)


def no_contact(ax, x0, x1, y, color=INK):
    for x in (x0, x1):
        ax.add_patch(Circle((x, y), 2.6, color=color, zorder=58))
    ax.plot([x0, x1 - 2], [y, y + 11], color=color, lw=1.5, zorder=58)


def notes(ax, y, rows, x1=190):
    for a, b in rows:
        ax.text(60, y, a, fontsize=8.3, fontweight="semibold", family=_TF[0], color=INK, va="top")
        ax.text(x1, y, b, fontsize=8.1, color=DIM, va="top", linespacing=1.35)
        y -= 24 + 16 * b.count("\n")


# ===================================================================== power
def page_power(MS, pdf):
    _TF[0] = MS.TITLE_FONT
    fig, ax = MS.new_page(None, "Wiring  ·  power and the safety relay",
                          "Gantry circuits only. Mains, the GFCI and the fused inlet are on sheet E-01.")
    box(ax, 50, 560, 160, 160, "Supply", "Mean Well LRS-350-24\n24 V DC, 14.6 A\n\nAC in: sheet E-01")
    vp = term(ax, 210, 690, "V+", "r"); vn = term(ax, 210, 600, "V−", "r")

    box(ax, 290, 520, 180, 200, "Fuse block")
    ax.text(460, 532, "Blue Sea 5025, ATO", fontsize=7.4, color=DIM, ha="right", zorder=51)
    fin = term(ax, 290, 690, "+ in", "l")
    fneg = term(ax, 290, 545, "− bus", "l")
    fo = {}
    for y, amp, what in ((680, "1 A", "Z brake"), (640, "5 A", "motion"), (600, "1 A", "relay")):
        ax.add_patch(Rectangle((430, y - 6), 20, 12, facecolor="#fde68a", edgecolor=INK,
                               lw=0.8, zorder=55))
        ax.text(424, y, f"{amp}  {what}", fontsize=7.6, ha="right", va="center", color=INK, zorder=56)
        ax.plot([450, 470], [y, y], color=W24, lw=1.4, zorder=45)
        fo[what] = term(ax, 470, y, "", "r")
    ax.text(450, 566, "the other 3: sheet E-01", fontsize=7.0, ha="right", va="center", color=DIM, zorder=56)

    wire(ax, [vp, fin], W24)
    lab(ax, 250, 696, "1.5 mm²", W24, ha="center")
    wire(ax, [vn, (250, 600), (250, 545), fneg], WGND)
    lab(ax, 256, 566, "1.5 mm²", WGND)

    box(ax, 560, 400, 340, 320, "Safety relay  ·  Omron G9SE-201",
        "24 V DC, two input channels, manual reset")
    a1 = term(ax, 560, 650, "A1", "l")
    bt = {}
    for nm, x in (("T33", 580), ("A2", 615), ("T31", 655), ("T32", 695),
                  ("T11", 750), ("T12", 790), ("T21", 835), ("T22", 875)):
        bt[nm] = term(ax, x, 400, nm, "b", fs=7.4)
    rt = {}
    for nm, y in (("13", 700), ("23", 660), ("14", 600), ("24", 560), ("X1", 480)):
        rt[nm] = term(ax, 900, y, nm, "r")
    ax.text(864, 632, "13-14 and 23-24 are\nthe two safety contacts", fontsize=7.0, color=DIM,
            ha="right", va="top", zorder=61)

    wire(ax, [fo["relay"], (530, 600), (530, 650), a1], W24)
    wire(ax, [(530, 600), (530, 370), (580, 370), bt["T33"]], W24)
    dot(ax, (530, 600), W24)
    wire(ax, [fo["motion"], (500, 640), (500, 745), (920, 745), (920, 700), rt["13"]], W24)
    wire(ax, [fo["Z brake"], (490, 680), (490, 755), (930, 755), (930, 660), rt["23"]], W24)
    wire(ax, [(250, 545), (250, 340), (615, 340), bt["A2"]], WGND)
    dot(ax, (250, 545), WGND)

    # reset button: T31 -> NO -> T32
    box(ax, 625, 170, 100, 150, "Reset", "M22-D-B button\nM22-K10, NO", title_at="bottom")
    wire(ax, [bt["T31"], (655, 262)], WSAFE); wire(ax, [bt["T32"], (695, 262)], WSAFE)
    no_contact(ax, 655, 695, 262)
    ax.plot([675, 675], [270, 292], color=INK, lw=1.0, ls=(0, (2, 2)), zorder=58)
    ax.plot([664, 686], [292, 292], color=INK, lw=1.6, zorder=58)

    # E-stop: one NC block per channel, one head
    box(ax, 732, 170, 170, 150, "E-stop", "M22-PV head\n2 × M22-K01, NC", title_at="bottom")
    for a, b in (("T11", "T12"), ("T21", "T22")):
        xa, xb = bt[a][0], bt[b][0]
        wire(ax, [bt[a], (xa, 262)], WSAFE); wire(ax, [bt[b], (xb, 262)], WSAFE)
        nc_contact(ax, xa, xb, 262)
    ax.plot([770, 855], [258, 258], color=INK, lw=1.0, ls=(0, (2, 2)), zorder=57)
    ax.plot([812, 812], [258, 296], color=INK, lw=1.0, ls=(0, (2, 2)), zorder=57)
    ax.add_patch(FancyBboxPatch((796, 296), 32, 10, boxstyle="round,pad=0,rounding_size=5",
                                facecolor="#dc2626", edgecolor=INK, lw=0.8, zorder=58))
    ax.text(770, 240, "ch 1", fontsize=6.9, color=DIM, ha="center", zorder=58)
    ax.text(855, 240, "ch 2", fontsize=6.9, color=DIM, ha="center", zorder=58)

    for nm, txt in (("14", "to the controller VM+   (next page)"),
                    ("24", "to the Z brake +   (next page)")):
        y = rt[nm][1]
        wire(ax, [rt[nm], (1100, y)], W24S); off_page(ax, 1100, y, W24S)
        lab(ax, 1098, y + 5, txt, W24S, ha="right")
    wire(ax, [rt["X1"], (1100, 480)], WSIG); off_page(ax, 1100, 480, WSIG)
    lab(ax, 1098, 485, "X1 to utility node pin A6", WSIG, ha="right")
    ax.text(1098, 470, "PNP, 100 mA max, through an opto input.\nA status signal, never a safety output.",
            fontsize=7.0, color=DIM, ha="right", va="top", zorder=61)

    ax.text(60, 316, "Colours", fontsize=8.4, fontweight="semibold", family=_TF[0], color=INK)
    for i, (t, c) in enumerate((("+24 V, fused", W24), ("+24 V after the safety relay", W24S),
                                ("0 V", WGND), ("signal", WSIG), ("safety loop", WSAFE))):
        y = 294 - i * 18
        ax.plot([60, 86], [y, y], color=c, lw=2.2)
        ax.text(94, y, t, fontsize=7.8, color=INK, va="center")

    notes(ax, 146, [
        ("How it resets", "24 V on T33, the NO button from T31 to T32. After an E-stop the outputs stay off until "
                          "the head is pulled up\nand the button is pressed and released."),
        ("Contact ratings", "5 A at 30 V DC resistive, 1.5 A inductive. Omron limits the fuse ahead of each contact "
                            "to 8 A: these are 5 A and 1 A."),
        ("Why two contacts", "13-14 cuts the controller, so the motors go limp; 23-24 cuts the brake coil, so the "
                             "mast locks.")])
    ax._body_y = 60.0
    MS.save(fig, ax, pdf, "w1_power")


# ==================================================================== motion
def page_motion(MS, pdf):
    _TF[0] = MS.TITLE_FONT
    fig, ax = MS.new_page(None, "Wiring  ·  controller, motors, brake, limits",
                          "Elecrow 4X 2209 running FluidNC. Terminal names follow the board; GPIO numbers come from its config.")
    box(ax, 420, 300, 280, 420, "Controller", "Elecrow 4X 2209, FluidNC\n4 × TMC2209 on UART, 2 spare")
    L = {}
    for key, nm, y in (("vm", "VM +", 640), ("g0", "GND", 612), ("xl", "X limit input", 540),
                       ("gx", "GND", 515), ("zl", "Z limit input", 460), ("gz", "GND", 435),
                       ("usb", "USB-C", 350)):
        L[key] = term(ax, 420, y, nm, "l")
    R = {}
    for blk, y0 in (("X", 690), ("Z", 560)):
        ax.text(690, y0 + 18, f"motor {blk}", fontsize=8.0, ha="right", color=INK,
                fontweight="bold", zorder=61)
        for i, c in enumerate(("A+", "A-", "B+", "B-")):
            R[(blk, c)] = term(ax, 700, y0 - i * 22, c.replace("-", "−"), "r")
    mos = term(ax, 700, 400, "MOSFET 1  −", "r")
    ax.text(690, 386, "3 A, switches to 0 V", fontsize=6.9, color=DIM, ha="right", va="top", zorder=61)

    wire(ax, [(70, 640), L["vm"]], W24S)
    lab(ax, 80, 646, "from the safety relay, 14  (power page)", W24S)
    wire(ax, [(70, 612), L["g0"]], WGND)
    lab(ax, 80, 618, "0 V, fuse block − bus", WGND)

    box(ax, 800, 600, 310, 120, "X motor", "NEMA 23, 2.8 A\nat the rail's left end", tx=62)
    box(ax, 800, 380, 310, 200, "Z motor", "23HS22-4004D-B280, at the mast foot\n"
                                           "brake 24 V 4.5 W, two wires,\neither way round", tx=62)
    for blk in ("X", "Z"):
        for c in ("A+", "A-", "B+", "B-"):
            p = R[(blk, c)]
            wire(ax, [p, (800, p[1])], MOT[c], lw=1.6)
            term(ax, 800, p[1], c.replace("-", "−"), "l", fs=7.0)
    ax.text(862, 640, "four wires, two coils", fontsize=7.0, color=DIM, va="center", zorder=61)
    ax.text(862, 476, "StepperOnline colours: A+ black, A− green,\nB+ red, B− blue. Prove the pairs with a\n"
                      "meter: a few ohms across a coil, open between.", fontsize=7.0, color=DIM, va="top",
            zorder=61)
    bp = term(ax, 960, 380, "brake +", "b", fs=7.2)
    bn = term(ax, 850, 380, "brake −", "b", fs=7.2)
    wire(ax, [bn, (850, 360), (740, 360), (740, 400), mos], WGND)
    wire(ax, [bp, (960, 340), (1100, 340)], W24S); off_page(ax, 1100, 340, W24S)
    lab(ax, 1098, 324, "from the safety relay, 24  (power page)", W24S, ha="right", va="top")

    box(ax, 50, 395, 300, 200, "Limit switches", "Xtension kit microswitches, NC contacts")
    for inp, gnd, a, b in (("xl", "gx", "X max", "X min"), ("zl", "gz", "Z max", "Z min")):
        yi, yg = L[inp][1], L[gnd][1]
        wire(ax, [L[inp], (300, yi)], WSIG)
        nc_contact(ax, 260, 300, yi)
        ax.text(280, yi + 8, a, fontsize=7.2, ha="center", color=INK, zorder=61)
        wire(ax, [(260, yi), (160, yi)], WSIG)
        nc_contact(ax, 120, 160, yi)
        ax.text(140, yi + 8, b, fontsize=7.2, ha="center", color=INK, zorder=61)
        wire(ax, [(120, yi), (90, yi), (90, yg), L[gnd]], WGND)
    ax.text(62, 402, "Min and max in series on one input (limit_all_pin).\nA cut wire reads as a tripped limit, never a silent one.", va="bottom",
            fontsize=7.0, color=DIM, zorder=61)

    wire(ax, [(70, 350), L["usb"]], WSIG)
    lab(ax, 80, 356, "to the Jetson: G-code over USB serial", WSIG)

    ax.text(60, 268, "Driver settings  (FluidNC config)", fontsize=8.6, fontweight="semibold", family=_TF[0], color=INK)
    tbl = [("", "run A", "hold A", "µsteps", "steps/mm", "drive"),
           ("X", "1.5", "0.75", "16", "80", "GT2 belt, 20 T pulley"),
           ("Z", "1.8", "0.9", "16", "400", "Tr8×8 lead screw")]
    for i, r in enumerate(tbl):
        y = 246 - i * 19
        for j, cval in enumerate(r):
            ax.text(60 + (0, 30, 82, 134, 186, 252)[j], y, cval, fontsize=8.0, color=INK,
                    fontweight="bold" if (i == 0 or j == 0) else "normal")
    ax.text(60, 186, "A TMC2209 is good for about 2 A RMS, so both motors run below rating.\n"
                     "Z lifts about 1.7 kg on an 8 mm lead: under 0.1 N·m.",
            fontsize=7.6, color=DIM, va="top", linespacing=1.4)

    ax.text(560, 268, "What rides where", fontsize=8.6, fontweight="semibold", family=_TF[0], color=INK)
    route = [("Cable", "Path", "Spec"),
             ("X motor, X limits", "along the rail, fixed", "4 × 0.5 mm² shielded; 2 × 0.25"),
             ("Z motor, brake, Z limits", "X chain, then the mast", "chainflex 4 × 0.5 shielded; 2 × 0.5; 2 × 0.25"),
             ("Arm power, Cat6A, D405", "X chain, then Z chain", "arm brick lead; slim Cat6A; high-flex USB-C"),
             ("VM, 0 V", "enclosure only", "1.5 mm², ferrules")]
    for i, r in enumerate(route):
        y = 246 - i * 19
        for j, cval in enumerate(r):
            ax.text(560 + (0, 150, 290)[j], y, cval, fontsize=7.8, color=INK,
                    fontweight="bold" if i == 0 else "normal")

    notes(ax, 128, [
        ("Brake", "24 V releases it. Before a Z move: M62 P0 (MOSFET on), then a 0.1 s dwell; after the move: M63 P0.\n"
                  "An E-stop or a power cut opens 23-24 and the mast locks whatever the software is doing."),
        ("Shields", "Motor cable shields to GND at the controller end only. No mains in any chain.")], x1=150)
    ax._body_y = 50.0
    MS.save(fig, ax, pdf, "w2_motion")
