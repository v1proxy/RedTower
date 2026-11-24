# The pictures for RedSec's alarm notification: the house in lines, zoomed on where the alarm went off.
# One per contact sensor (its room as a translucent red box, its window or door in solid red) and one per room
# (for alarms that only know their room), plus one for an alarm with no known place (the whole house outlined red).
#   python redsec_pics.py DRAWINGS OUT FONTS
#   DRAWINGS  the folder drawings_plain.py wrote (axo-layout.json and axo-plain-v0..7.svg)
#   OUT       where the PNGs go (they go to Home Assistant's My media, root)
#   FONTS     a folder with IBMPlexMono-Regular.woff2 and IBMPlexMono-Medium.woff2
# Needs Playwright with Chromium (pip install playwright; playwright install chromium).
import json, os, sys, base64
from playwright.sync_api import sync_playwright
if len(sys.argv) < 4:
    sys.exit("usage: python redsec_pics.py DRAWINGS OUT FONTS")
DRAW, OUT, FONTS = sys.argv[1], sys.argv[2], sys.argv[3]
LAY = json.load(open(os.path.join(DRAW, "axo-layout.json")))
CX0, CY0, CW, CH = LAY["crop"]
FROM = ["south-east", "south", "south-west", "west", "north-west", "north", "north-east", "east"]
W, H, DPR = 1200, 600, 1.5
RED, MUTED, INK = "#ED1C24", "#8E9096", "#F3F1EC"
FONT = os.path.join(FONTS, "IBMPlexMono-Regular.woff2")
FONT_M = os.path.join(FONTS, "IBMPlexMono-Medium.woff2")
FLOOR = {1: "Ground floor", 2: "Second floor", 3: "Third floor"}

# what each picture shows: file, room box, opening, view, the words on it
PICS = [
    dict(file="redsec_backyard_window.png", room="guest_room", opening="window_guest_room", view=2, title="Backyard window", where="Guest room · ground floor"),
    dict(file="redsec_balcony_window.png", room="kitchen", opening="door_balcony", view=2, title="Balcony window", where="Kitchen · second floor"),
    dict(file="redsec_room_bedroom.png", room="bedroom", view=2, title="Bedroom", where="Third floor"),
    dict(file="redsec_room_kitchen.png", room="kitchen", view=4, title="Kitchen", where="Second floor"),
    dict(file="redsec_room_living_room.png", room="living_room", view=0, title="Living room", where="Second floor"),
    dict(file="redsec_room_guest_room.png", room="guest_room", view=2, title="Guest room", where="Ground floor"),
    dict(file="redsec_room_studio.png", room="studio", view=4, title="Studio", where="Ground floor"),
    dict(file="redsec_room_garage.png", room="garage", view=0, title="Garage", where="Ground floor"),
    dict(file="redsec_house.png", view=0, title="Red Tower", where="Where: not known"),
]


def loops_d(loops, s, ox, oy):
    return "".join("M" + "L".join(f"{x * s + ox:.1f} {y * s + oy:.1f}" for x, y in pts) + "Z" for pts in loops)


def segs_d(segs, s, ox, oy):
    return "".join(f"M{a * s + ox:.1f} {b * s + oy:.1f}L{c * s + ox:.1f} {e * s + oy:.1f}" for a, b, c, e in segs)


def page(p):
    v = LAY["views"][p["view"]]
    svg_file = os.path.join(DRAW, f"axo-plain-v{p['view']}.svg")
    if p.get("room"):
        b = v["boxes"][p["room"]]
        xs = [x for lp in b["fill"] for x, y in lp]; ys = [y for lp in b["fill"] for x, y in lp]
        bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
        s = min(0.62 * H / (by1 - by0), 0.42 * W / (bx1 - bx0), 1.25)
        s = max(s, 0.42)
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
        if p.get("opening"):
            ax, ay = v["openings"][p["opening"]]["anchor"]
            cx, cy = (cx + ax) / 2, (cy + ay) / 2
        ox, oy = W * 0.56 - cx * s, H * 0.56 - cy * s
        g = (f'<path d="{loops_d(b["fill"], s, ox, oy)}" fill="{RED}" fill-opacity="0.22"/>'
             f'<path d="{segs_d(b["edges"], s, ox, oy)}" fill="none" stroke="{RED}" stroke-opacity="0.65" stroke-width="1.5"/>')
        if p.get("opening"):
            o = v["openings"][p["opening"]]
            g += (f'<path d="{segs_d(o["hidden"], s, ox, oy)}" fill="none" stroke="{RED}" stroke-width="2.4" stroke-dasharray="6 5"/>'
                  f'<path d="{segs_d(o["seen"], s, ox, oy)}" fill="none" stroke="{RED}" stroke-width="4" stroke-linecap="square"/>')
    else:
        bx0, by0, bx1, by1 = v["bbox"]
        s = min(0.84 * H / (by1 - by0), 0.84 * W / (bx1 - bx0))
        ox, oy = W * 0.56 - (bx0 + bx1) / 2 * s, H * 0.5 - (by0 + by1) / 2 * s
        g = f'<path d="{loops_d(v["floors"]["all"], s, ox, oy)}" fill="none" stroke="{RED}" stroke-width="3" stroke-linejoin="round"/>'
    src = "data:image/svg+xml;base64," + base64.b64encode(open(svg_file, "rb").read()).decode()
    b64 = lambda f: base64.b64encode(open(f, "rb").read()).decode()
    fonts = (f"@font-face{{font-family:Mono;font-weight:400;src:url(data:font/woff2;base64,{b64(FONT)}) format('woff2')}}"
             f"@font-face{{font-family:Mono;font-weight:500;src:url(data:font/woff2;base64,{b64(FONT_M)}) format('woff2')}}"
             ".l{position:absolute;left:30px;padding:3px 6px;background:#000;letter-spacing:.08em;text-transform:uppercase}")
    lab = (f'<div class="l" style="top:26px;font:500 22px/1.25 Mono;color:{RED}">{p["title"]}</div>'
           f'<div class="l" style="top:60px;font:400 18px/1.25 Mono;color:{MUTED}">{p["where"]}</div>'
           f'<div class="l" style="bottom:24px;font:400 15px/1.25 Mono;color:{MUTED}">Red Tower · from the {FROM[p["view"]]}</div>')
    return (f'<html><head><style>{fonts}html,body{{margin:0;background:#000;width:{W}px;height:{H}px;overflow:hidden}}</style></head><body>'
            f'<div style="position:relative;width:{W}px;height:{H}px;overflow:hidden">'
            f'<img src="{src}" style="position:absolute;left:{ox:.1f}px;top:{oy:.1f}px;width:{CW * s:.1f}px;height:{CH * s:.1f}px">'
            f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="position:absolute;left:0;top:0">{g}</svg>{lab}</div></body></html>')


os.makedirs(OUT, exist_ok=True)
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=DPR)
    for p in PICS:
        pg.set_content(page(p))
        pg.wait_for_timeout(300)
        pg.evaluate("document.fonts.ready")
        pg.screenshot(path=os.path.join(OUT, p["file"]))
        print(p["file"], os.path.getsize(os.path.join(OUT, p["file"])))
    br.close()
