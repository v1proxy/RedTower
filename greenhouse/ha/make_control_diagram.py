"""The control system diagram for docs/interface/: one path to every actuator.

Drawn in the Maag house style from what the code does: who may ask (gh/core/safety.py and
the module manifests), what the governor checks and in which order (Governor.check), where an
approved command goes (the actuator bridge in ha/packages/greenhouse_jetson.yaml, the gantry
and arm drivers) and what runs around that path (supervisor, bridge, mirror, watchdog).

    python greenhouse/ha/make_control_diagram.py [--fonts DIR]

Writes control-system.svg and, with playwright installed, control-system.png. --fonts (or
$MAAG_FONTS) is a folder with IBMPlexMono-{Regular,Medium,SemiBold}.woff and
Inter-{Regular,Medium,SemiBold}.woff, the files the Maag design system carries; without it the
PNG uses this machine's fonts.
"""
import argparse
import os
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "docs" / "interface"
VERSION = (ROOT / "VERSION").read_text().strip()

# Maag tokens (design system, Paper theme)
INK, DIM, FRAME, RULE, EDGE = "#15191c", "#5b6770", "#dfe5e9", "#c3ccd2", "#9aa7b0"
PANEL, CHIP, OK, WARN, SIGNAL, SAFETY = "#f5f7f8", "#eef2f5", "#15803d", "#b91c1c", "#2563eb", "#7c3aed"
MONO = "'IBM Plex Mono', ui-monospace, Menlo, monospace"
SANS = "Inter, system-ui, 'Segoe UI', sans-serif"
W, H = 1600, 930

out = []


def text(x, y, s, size=13.6, fill=INK, family=SANS, weight=400, anchor="start"):
    out.append(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
               f'fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')


def rect(x, y, w, h, fill=PANEL, stroke=EDGE, sw=1.5, r=6, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" '
               f'stroke-width="{sw}"{d}/>')


STYLE = {  # line style -> size, colour, family, weight
    "body": (13.6, INK, SANS, 400), "dim": (13.6, DIM, SANS, 400), "code": (12.4, SIGNAL, MONO, 400),
    "safe": (13.6, SAFETY, SANS, 500), "ok": (14.5, OK, MONO, 600), "warn": (14.5, WARN, MONO, 600),
    "word": (14.5, INK, MONO, 600),
}


def box(x, y, w, h, title, lines, sub=None, fill=PANEL, stroke=EDGE, title_col=INK):
    rect(x, y, w, h, fill, stroke)
    text(x + 14, y + 26, title, 14.5, title_col, MONO, 600)
    yy = y + 26
    if sub:
        yy += 20
        text(x + 14, yy, sub, 12.2, DIM)
    yy += 10
    for style, s in lines:
        size, col, fam, wt = STYLE[style]
        yy += 21 if style not in ("ok", "warn", "word") else 24
        text(x + 14, yy, s, size, col, fam, wt)


def arrow(x1, y1, x2, y2, col=INK, sw=2.0, dash=None, head=True):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    m = f' marker-end="url(#h{col[1:]})"' if head else ""
    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{sw}"{d}{m}/>')


def path(d, col=INK, sw=2.0, dash=None):
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{sw}"{ds} marker-end="url(#h{col[1:]})"/>')


def label(x, y, s, col=DIM, anchor="middle", family=SANS, size=12.2):
    text(x, y, s, size, col, family, 400, anchor)


# ------------------------------------------------------------------ page
rect(18, 18, W - 36, H - 36, "none", FRAME, 1.7, 0)
text(48, 76, "The control system · one path to every actuator", 24.3, INK, MONO, 600)
text(48, 108, "Whoever asks, you or an agent, the safety governor decides. The ESPHome nodes can still refuse on their own.",
     15.3, DIM)

# ------------------------------------------------------------------ who asks
text(48, 158, "Who asks", 11.5, DIM, MONO, 600)
box(48, 170, 300, 132, "You · the panel", [
    ("body", "Manual buttons, jog, Photo now"), ("body", "Approve or reject a proposal"),
    ("code", "greenhouse/safety/request/ui"), ("dim", "Only the interface may write it (ACL)")])
box(48, 318, 300, 112, "Services · Layer 2", [
    ("body", "Climate, irrigation, motion"), ("body", "Run at Auto and above"),
    ("code", "greenhouse/safety/request")])
box(48, 446, 300, 132, "Agents · Layer 3", [
    ("body", "Environment agent, plant tender"), ("body", "Only at Agent proposes or autonomous"),
    ("safe", "Never with the kill switch on"), ("code", "greenhouse/safety/request")])
for y in (236, 374, 512):
    arrow(348, y, 392, y)

# ------------------------------------------------------------------ governor
gx, gy, gw, gh = 396, 170, 452, 408
rect(gx, gy, gw, gh, "#ffffff", INK, 2.2)
text(gx + 16, gy + 28, "Safety governor · Jetson, Layer 0", 15.5, INK, MONO, 600)
text(gx + 16, gy + 50, "The only path to an actuator. Unknown means denied.", 12.6, DIM)
checks = [
    ("Who", "The topic decides. A module must be enabled", "and allowed this actuator in its manifest."),
    ("Kill switch", "On: every agent request is denied.", None),
    ("Authority", "Off: only turning things off. Manual: you,", "and turning off. Agents: proposes and up."),
    ("Limits", "Min, max and per hour, from limits.yaml.", "An action with no limit is always denied."),
    ("Interlocks", "Door, E-stop, water, arm stowed, gantry still.", None),
    ("Plant", "Work at a plant needs a confirmed type,", "and the plant not marked dead."),
    ("Approval", "Per action: never, agent or always.", "A cut always waits for you."),
]
yy = gy + 84
for i, (head, l1, l2) in enumerate(checks, 1):
    col = SAFETY if head in ("Kill switch", "Interlocks") else INK
    out.append(f'<circle cx="{gx + 30}" cy="{yy - 5}" r="12" fill="{INK}"/>')
    text(gx + 30, yy, str(i), 13, "#ffffff", MONO, 700, "middle")
    text(gx + 52, yy, head, 13.6, col, MONO, 600)
    text(gx + 148, yy, l1, 12.8, INK)
    if l2:
        text(gx + 148, yy + 18, l2, 12.8, INK)
    yy += 48 if l2 else 40

# ------------------------------------------------------------------ verdicts
vx, vw = 892, 262
text(vx, 158, "Verdict", 11.5, DIM, MONO, 600)
box(vx, 170, vw, 112, "APPROVED", [
    ("body", "Runs now, published on"), ("code", "greenhouse/actuator/<name>/set"),
    ("dim", "Counted against the hourly limit")], title_col=OK)
box(vx, 300, vw, 150, "PROPOSED", [
    ("body", "Waits in the panel's approval"), ("body", "queue, and as a notification"),
    ("body", "Approve: back through every check"), ("dim", "Reject, or 24 h pass: denied")])
box(vx, 468, vw, 110, "DENIED", [
    ("body", "Nothing moves. Logged with"), ("body", "its reason, and shown in the"), ("body", "panel as Last request")],
    title_col=WARN)
for y in (226, 375, 523):
    arrow(gx + gw, y, vx - 4, y)

# ------------------------------------------------------------------ executors
ex, ew = 1190, 362
text(ex, 158, "Who acts", 11.5, DIM, MONO, 600)
rect(ex, 170, ew, 214, PANEL, EDGE)
text(ex + 14, 196, "Home Assistant · actuator bridge", 14.5, INK, MONO, 600)
text(ex + 14, 220, "Lights, fans, humidifier, watering", 13.6)
text(ex + 14, 241, "Calls the ESPHome action for each command", 13.6, DIM)
rect(ex + 14, 256, ew - 28, 116, "#ffffff", SAFETY, 1.5)
text(ex + 28, 280, "ESPHome node · refuses on its own", 13.6, SAFETY, MONO, 600)
text(ex + 28, 303, "Pump and valves internal: not on the API", 13.2)
text(ex + 28, 324, "No water with a wet tray, the float down,", 13.2)
text(ex + 28, 344, "the leak lockout latched or the E-stop open", 13.2)
text(ex + 28, 364, "Valves normally closed: a dead node waters nothing", 12.4, DIM)
rect(ex, 400, ew, 178, PANEL, EDGE)
text(ex + 14, 426, "Gantry and arm drivers · Layer 1", 14.5, INK, MONO, 600)
text(ex + 14, 450, "FluidNC X and Z, myCobot 280 Pi", 13.6)
text(ex + 14, 474, "The gantry never moves with the arm out;", 13.6, SAFETY)
text(ex + 14, 495, "the arm never moves on a moving carriage", 13.6, SAFETY)
text(ex + 14, 519, "A cut needs an approved tend task: one", 13.6)
text(ex + 14, 540, "approach, one cut, one release, 15 min", 13.6)
text(ex + 14, 564, "Each driver refuses on its own as well", 12.4, DIM)
path(f"M {vx + vw} 214 L 1172 214 L 1172 277 L {ex - 4} 277", OK, 2.2)
path(f"M 1172 277 L 1172 489 L {ex - 4} 489", OK, 2.2)

# ------------------------------------------------------------------ around the path
text(48, 630, "Around the path", 11.5, DIM, MONO, 600)
bw, gap, by, bh = 361, 20, 642, 222
around = [
    ("Supervisor · Layer 0", [
        ("body", "Owns enable, authority and the kill"), ("body", "switch, and keeps them across restarts"),
        ("body", "Starts and stops containers: agents"), ("body", "run only at Agent proposes or"),
        ("body", "autonomous, never with the kill on"), ("dim", "One status per module: running,"),
        ("dim", "stub, degraded, paused, halted,"), ("dim", "disabled, stopped, offline")]),
    ("HA bridge · Layer 0", [
        ("body", "MQTT discovery: about 220 entities"), ("body", "under the device Greenhouse"),
        ("body", "The panel writes these, and the"), ("body", "supervisor obeys them:"),
        ("code", "select.greenhouse_authority"), ("code", "switch.greenhouse_kill"),
        ("code", "switch.greenhouse_<module>_enabled")]),
    ("Mirror and interlocks", [
        ("body", "Home Assistant copies every node"), ("body", "state to MQTT"),
        ("code", "greenhouse/ha/<entity>/state"), ("body", "The ESPHome link turns them into"),
        ("body", "interlocks the governor reads:"), ("safe", "door, estop, water: OK, OPEN or"),
        ("safe", "UNKNOWN. Unknown is not OK")]),
    ("Watchdog · Home Assistant", [
        ("body", "Runs on the Yellow, so it fires"), ("body", "when the Jetson itself is dead"),
        ("body", "Agent down at proposes or up:"), ("body", "notified, hourly, then recovered"),
        ("body", "Irrigation down 10 min: Home"), ("body", "Assistant waters by its own rule"),
        ("dim", "Not when you stopped it yourself")]),
]
for i, (title, lines) in enumerate(around):
    box(48 + i * (bw + gap), by, bw, bh, title, lines)
text(W - 48, H - 30, f"Maag  ·  design {VERSION}", 11.1, DIM, SANS, 400, "end")

markers = "".join(
    f'<marker id="h{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for c in (INK, OK, DIM))
SVG = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
       f'<title>Maag control system: one path to every actuator</title><defs>{markers}</defs>'
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>{"".join(out)}</svg>')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fonts", type=Path, default=os.environ.get("MAAG_FONTS"))
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "control-system.svg").write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + SVG + "\n", encoding="utf-8")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("wrote control-system.svg (pip install playwright for the PNG)")
        return
    fonts = Path(a.fonts) if a.fonts else None
    files = {"IBM Plex Mono": ["IBMPlexMono-Regular", "IBMPlexMono-Medium", "IBMPlexMono-SemiBold"],
             "Inter": ["Inter-Regular", "Inter-Medium", "Inter-SemiBold"]}
    faces = "".join(
        f"@font-face{{font-family:'{fam}';font-weight:{w};src:url(http://maag.test/f/{n}.woff)}}"
        for fam, names in files.items() for n, w in zip(names, (400, 500, 600))
        if fonts and (fonts / f"{n}.woff").exists())
    html = (f"<!doctype html><html><head><meta charset=\"utf-8\"><style>{faces}html,body{{margin:0}}</style></head><body>{SVG}"
            "<script>Promise.all([\"600 16px 'IBM Plex Mono'\",\"400 16px Inter\",\"500 16px Inter\"]"
            ".map(f=>document.fonts.load(f))).then(()=>document.body.dataset.ready='1')</script></body></html>")

    def route(r):
        url = r.request.url
        if url.startswith("http://maag.test/f/"):
            return r.fulfill(body=(fonts / url.rsplit("/", 1)[1]).read_bytes(), content_type="font/woff")
        if url.startswith("http://maag.test/"):
            return r.fulfill(body=html, content_type="text/html; charset=utf-8")
        return r.abort()

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1.25)
        page.route("**/*", route)
        page.goto("http://maag.test/")
        page.wait_for_selector("body[data-ready='1']")
        png = OUT / "control-system.png"
        page.locator("svg").screenshot(path=str(png))
        b.close()
    try:                                  # 256 colours, the house colours kept exact: a third of the size
        from PIL import Image
        im = Image.open(png).convert("RGB")
        own = [INK, DIM, FRAME, RULE, EDGE, PANEL, CHIP, OK, WARN, SIGNAL, SAFETY, "#ffffff"]
        base = im.quantize(colors=256 - len(own), method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        pal = base.getpalette()[: 3 * (256 - len(own))]
        for c in own:
            pal += [int(c[i:i + 2], 16) for i in (1, 3, 5)]
        ref = Image.new("P", (1, 1))
        ref.putpalette(pal)
        im.quantize(palette=ref, dither=Image.Dither.NONE).save(png, optimize=True)
    except ImportError:
        pass
    print("wrote control-system.svg and control-system.png")


if __name__ == "__main__":
    main()
