"""Screenshots of the Greenhouse panel for docs/interface/, from the real card in demo mode.

Runs the card exactly as Home Assistant loads it (a JavaScript module, config {demo: true})
in headless Chromium at the four target sizes, then the close-ups the guide uses.

    pip install playwright pillow && python -m playwright install chromium
    python greenhouse/ha/make_shots.py [--fonts DIR]

The card asks for IBM Plex Sans and IBM Plex Mono and falls back to the system font. Give
--fonts a folder holding IBMPlexSans-{Regular,Italic,Medium,SemiBold}.woff2 and
IBMPlexMono-{Regular,Medium}.woff2 (IBM's own release, packages/plex-*/fonts/complete/woff2)
to render it as a device with Plex installed sees it; without it the shots use this
machine's system font. Nothing is fetched from the network.
"""
import argparse
import os
import re
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CARD = HERE / "www" / "greenhouse" / "greenhouse-panel.js"
OUT = ROOT / "docs" / "interface"

FACES = {  # file -> (family, weight, style)
    "IBMPlexSans-Regular.woff2": ("IBM Plex Sans", 400, "normal"),
    "IBMPlexSans-Italic.woff2": ("IBM Plex Sans", 400, "italic"),
    "IBMPlexSans-Medium.woff2": ("IBM Plex Sans", 500, "normal"),
    "IBMPlexSans-SemiBold.woff2": ("IBM Plex Sans", 600, "normal"),
    "IBMPlexMono-Regular.woff2": ("IBM Plex Mono", 400, "normal"),
    "IBMPlexMono-Medium.woff2": ("IBM Plex Mono", 500, "normal"),
}
SIZES = [  # name, CSS width, device pixel ratio: the four sizes of the interface baseline
    ("desktop-1320", 1320, 1, "Desktop, 1320"),
    ("tablet-1280", 1280, 1, "10 in tablet, 1280 landscape"),
    ("tablet-600", 600, 2, "7 in tablet, 600 portrait"),
    ("mobile-390", 390, 2, "Phone, 390"),
]


def page_html(fonts):
    faces = "".join(
        f"@font-face{{font-family:'{fam}';font-style:{st};font-weight:{w};src:url(http://maag.test/f/{n}) format('woff2')}}"
        for n, (fam, w, st) in FACES.items() if fonts and (fonts / n).exists())
    # Faces go on the document: Chromium ignores @font-face inside a shadow root.
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{faces}
html,body{{margin:0;background:#14181a}}</style>
<script type="module" src="http://maag.test/card.js"></script></head>
<body><greenhouse-panel id="c"></greenhouse-panel>
<script type="module">
await customElements.whenDefined('greenhouse-panel');
document.getElementById('c').setConfig({{demo: true}});
await Promise.all(["400 16px 'IBM Plex Sans'", "600 16px 'IBM Plex Sans'", "400 16px 'IBM Plex Mono'",
  "500 16px 'IBM Plex Mono'"].map((f) => document.fonts.load(f)));
document.body.dataset.ready = '1';
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fonts", type=Path, default=os.environ.get("MAAG_PLEX_WOFF2"))
    a = ap.parse_args()
    fonts = Path(a.fonts) if a.fonts else None
    html = page_html(fonts)
    OUT.mkdir(parents=True, exist_ok=True)
    raw = OUT / "_raw"
    raw.mkdir(exist_ok=True)

    def route(r):
        url = r.request.url
        if url.startswith("http://maag.test/f/"):
            return r.fulfill(body=(fonts / url.rsplit("/", 1)[1]).read_bytes(), content_type="font/woff2")
        if url == "http://maag.test/card.js":
            return r.fulfill(body=CARD.read_text(), content_type="text/javascript")
        if url.startswith("http://maag.test/"):
            return r.fulfill(body=html, content_type="text/html")
        return r.abort()            # the card makes no calls of its own; anything else is a fault

    def act(page, a, scope=""):
        page.locator("greenhouse-panel").locator(f'{scope}[data-act="{a}"]').first.click()
        page.wait_for_timeout(250)

    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, w, dpr, _ in SIZES:
            ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=dpr,
                                timezone_id="America/Chicago", locale="en-US")
            page = ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.route("**/*", route)
            page.goto("http://maag.test/")
            page.wait_for_selector("body[data-ready='1']")
            page.wait_for_timeout(400)
            page.screenshot(path=str(raw / f"{name}.png"), full_page=True)
            if name == "desktop-1320":
                card = page.locator("greenhouse-panel")
                page.screenshot(path=str(raw / "hero.png"), clip={"x": 0, "y": 0, "width": w, "height": 860})
                act(page, "power")
                card.locator("section").nth(3).screenshot(path=str(raw / "power.png"))
                act(page, "power")
                act(page, "plant:A04")
                card.locator(".two").screenshot(path=str(raw / "plants-console.png"))
                act(page, "expand")
                page.screenshot(path=str(raw / "plant-overlay.png"))
                act(page, "expand", ".overlay button")
                page.evaluate("window.scrollTo(0, 0)")
                act(page, "kill")
                page.screenshot(path=str(raw / "kill.png"), clip={"x": 0, "y": 0, "width": w, "height": 452})
                act(page, "kill")
                act(page, "auth:off")
                act(page, "water:a")
                card.locator("section").nth(2).screenshot(path=str(raw / "denied.png"))
            if errors:
                raise SystemExit(f"{name}: the card threw {errors[0]}")
            ctx.close()
        b.close()

    # The card's own colours, read from its source, always get an exact palette entry: a status
    # dot is a few pixels and a plain median cut would shift its colour, and colour is meaning.
    own = sorted(set(re.findall(r"#[0-9a-fA-F]{6}\b", CARD.read_text())) | {"#ffffff"})

    def save(src, dst, im=None):
        im = (im or Image.open(src)).convert("RGB")
        base = im.quantize(colors=256 - len(own), method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        pal = base.getpalette()[: 3 * (256 - len(own))]
        for c in own:
            pal += [int(c[i:i + 2], 16) for i in (1, 3, 5)]
        ref = Image.new("P", (1, 1))
        ref.putpalette(pal)
        im.quantize(palette=ref, dither=Image.Dither.NONE).save(dst, optimize=True)

    for n in ("hero", "power", "plants-console", "plant-overlay", "kill", "denied"):
        save(raw / f"{n}.png", OUT / f"panel-{n}.png")
    for name, w, dpr, _ in SIZES:
        save(raw / f"{name}.png", OUT / f"panel-{name}.png")

    # The four sizes side by side, first screen and a half of each, at one scale.
    shots = [Image.open(raw / f"{name}.png").convert("RGB") for name, *_ in SIZES]
    shots = [s.resize((w, round(s.height * w / s.width)), Image.LANCZOS) for s, (_, w, *_) in zip(shots, SIZES)]
    h, gap, pad = 1300, 40, 40
    sheet = Image.new("RGB", (sum(w for _, w, *_ in SIZES) + gap * 3 + pad * 2, h + pad * 2), "#ffffff")
    x = pad
    for s, (_, w, *_) in zip(shots, SIZES):
        sheet.paste(s.crop((0, 0, w, min(h, s.height))), (x, pad))
        x += w + gap
    save(None, OUT / "panel-sizes.png", sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS))

    for f in raw.iterdir():
        f.unlink()
    raw.rmdir()
    for f in sorted(OUT.glob("panel-*.png")):
        im = Image.open(f)
        print(f"{f.relative_to(ROOT)}  {im.width} x {im.height}  {f.stat().st_size // 1024} kB")


if __name__ == "__main__":
    main()
