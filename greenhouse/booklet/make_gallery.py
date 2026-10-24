"""The assembly booklets as pages you can read on GitHub.

Renders every page of every assembly booklet from its PDF and writes:

  docs/booklets/<slug>/pNN.jpg    each page, 1400 px wide
  docs/booklets/<slug>/tNN.jpg    each page as a thumbnail, 400 px wide
  docs/booklets/<slug>.md         the booklet page by page, with a contents line
  docs/booklets/README.md         every page of every booklet, in build order
  docs/booklets/cover.jpg         the shared cover render, for the README
  docs/booklets/pages.json        each PDF's hash and page titles (a page is only
                                  re-rendered when its PDF changed)

and the generated blocks between markers in README.md (`booklets`) and in each
module's own guide (`booklet`). Page titles and step numbers are read from the
PDF's text, so nothing here is typed by hand except which four pages show as a
booklet's highlights.

Run it after rebuilding any booklet:

    python greenhouse/booklet/make_gallery.py           [--force]

Needs pdftoppm (poppler), Pillow and pdfplumber.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "docs", "booklets")
FULL_W, THUMB_W, COVER_W = 1400, 400, 1600
SHOW_W = 200                       # thumbnail display width on GitHub, px
WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}

# In build order. `highlights` are page numbers (1 is the cover).
BOOKLETS = [
    dict(slug="frame", name="Frame Rev A",
         pdf="greenhouse/frame/Maag_Frame_Assembly_Instructions_RevA.pdf",
         guide="greenhouse/frame/FRAME_ASSEMBLY.md",
         what="The cabinet: 4040 extrusion, the trays, the base pan and the drains.",
         highlights=[5, 14, 24, 25]),
    dict(slug="gantry", name="Gantry Rev E",
         pdf="greenhouse/gantry/Gantry_Assembly_Instructions_RevE.pdf",
         guide="greenhouse/gantry/GANTRY_ASSEMBLY.md",
         what="The X/Z gantry on the bench, its wiring, then into the cabinet with the arm.",
         highlights=[8, 21, 30, 32]),
    dict(slug="enclosure", name="Enclosure Rev A",
         pdf="greenhouse/enclosure/Maag_Enclosure_Assembly_Instructions_RevA.pdf",
         guide="greenhouse/enclosure/ENCLOSURE.md",
         what="Polycarbonate panels, the fans and the four doors, on the finished cabinet.",
         highlights=[2, 8, 16, 24]),
    dict(slug="harvest", name="Harvest Rev B",
         pdf="greenhouse/harvest/Maag_Harvest_Assembly_Instructions_RevB.pdf",
         guide="greenhouse/harvest/HARVEST.md",
         what="Where the cuts go: the dead-leaf tray in the base and the feeder on the right panel.",
         highlights=[2, 3, 11, 15]),
    dict(slug="snip", name="Herb Snip Rev A",
         pdf="greenhouse/snip/Maag_Herb_Snip_Assembly_Instructions_RevA.pdf",
         guide="greenhouse/snip/HERB_SNIP.md",
         what="The arm's printed cut-and-hold tool: print it, build it, put it on the arm.",
         highlights=[2, 3, 10, 16]),
]
COVER_SRC = "greenhouse/gantry/cover/cover.png"


# --------------------------------------------------------------------------- reading the PDFs

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def page_titles(pdf):
    """(title, step) per page: the title is the 17.5 pt header line, the step the 24 pt numeral."""
    import pdfplumber
    out = []
    with pdfplumber.open(pdf) as doc:
        for i, p in enumerate(doc.pages):
            title, step = {}, {}
            for c in p.chars:
                if c["top"] > 90:
                    continue
                if 16.0 <= c["size"] <= 19.0:
                    title.setdefault(round(c["top"]), []).append(c)
                elif 22.0 <= c["size"] <= 26.0 and c["text"].isdigit():
                    step.setdefault(round(c["top"]), []).append(c)
            t = ""
            if title:
                cs = sorted(title[min(title)], key=lambda c: c["x0"])
                t = "".join(c["text"] for c in cs).strip()
            s = None
            if step:
                s = int("".join(c["text"] for c in sorted(step[min(step)], key=lambda c: c["x0"])))
            if not t:
                t = "Cover" if i == 0 else f"Page {i + 1}"
            out.append((re.sub(r"\s+", " ", t), s))
    return out


def render(pdf, folder):
    """Every page at FULL_W wide and as a THUMB_W thumbnail, as progressive JPEGs."""
    os.makedirs(folder, exist_ok=True)
    for f in os.listdir(folder):
        if re.fullmatch(r"[pt]\d\d\.jpg", f):
            os.remove(os.path.join(folder, f))
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-png", "-scale-to-x", str(FULL_W), "-scale-to-y", "-1",
                        pdf, os.path.join(tmp, "p")], check=True)
        pngs = sorted(f for f in os.listdir(tmp) if f.endswith(".png"))
        for k, f in enumerate(pngs, 1):
            im = Image.open(os.path.join(tmp, f)).convert("RGB")
            im.save(os.path.join(folder, f"p{k:02d}.jpg"), "JPEG", quality=82, optimize=True, progressive=True)
            th = im.resize((THUMB_W, round(im.height * THUMB_W / im.width)), Image.LANCZOS)
            th.save(os.path.join(folder, f"t{k:02d}.jpg"), "JPEG", quality=80, optimize=True, progressive=True)
    return len(pngs)


# --------------------------------------------------------------------------- markdown

def slugify(text, seen):
    """GitHub's heading anchor: lower case, drop all but letters, marks, digits, '_', '-' and
    spaces, spaces to hyphens; a repeat gets -1, -2."""
    s = "".join(ch for ch in text.lower()
                if ch in " -_" or unicodedata.category(ch)[0] in "LMN")
    s = s.replace(" ", "-")
    n = seen.get(s, 0)
    seen[s] = n + 1
    return s if n == 0 else f"{s}-{n}"


def heading(k, title, step):
    return f"{k} · Step {step} · {title}" if step else f"{k} · {title}"


def anchors(pages):
    seen = {}
    return [slugify(heading(k, t, s), seen) for k, (t, s) in enumerate(pages, 1)]


def rel(frm_dir, path):
    return os.path.relpath(os.path.join(ROOT, path), os.path.join(ROOT, frm_dir)).replace(os.sep, "/")


def thumb_cell(b, k, title, step, anchor, frm_dir):
    view = rel(frm_dir, f"docs/booklets/{b['slug']}.md") + f"#{anchor}"
    img = rel(frm_dir, f"docs/booklets/{b['slug']}/t{k:02d}.jpg")
    cap = f"{k} · step {step}: {title}" if step else f"{k} · {title}"
    alt = f"{b['name']}, page {k}: {title}".replace('"', "'")
    return (f'<td align="center" valign="top"><a href="{view}"><img src="{img}" width="{SHOW_W}" '
            f'alt="{alt}"></a><br><sub>{cap}</sub></td>')


def thumb_rows(b, info, ks, frm_dir, per_row=4):
    pages, anc = info["pages"], info["anchors"]
    cells = [thumb_cell(b, k, pages[k - 1][0], pages[k - 1][1], anc[k - 1], frm_dir) for k in ks]
    rows = ["<tr>" + "".join(cells[i:i + per_row]) + "</tr>" for i in range(0, len(cells), per_row)]
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def counts(info):
    steps = sum(1 for _, s in info["pages"] if s)
    return f"{len(info['pages'])} pages, {steps} steps"


def links(b, frm_dir, view_label="Page by page"):
    return (f"[{view_label}]({rel(frm_dir, 'docs/booklets/' + b['slug'] + '.md')}) · "
            f"[PDF]({rel(frm_dir, b['pdf'])}) · [Guide]({rel(frm_dir, b['guide'])})")


def booklet_page(i, b, info):
    d = "docs/booklets"
    prev_b = BOOKLETS[i - 1] if i > 0 else None
    next_b = BOOKLETS[i + 1] if i + 1 < len(BOOKLETS) else None
    nav = [f"[All booklets](README.md)"]
    if prev_b:
        nav.append(f"previous: [{prev_b['name']}]({prev_b['slug']}.md)")
    if next_b:
        nav.append(f"next: [{next_b['name']}]({next_b['slug']}.md)")
    contents = "\n".join(f"- [{heading(k, t, s)}](#{a})"
                          for k, ((t, s), a) in enumerate(zip(info["pages"], info["anchors"]), 1))
    L = [f"# {b['name']}, page by page", "",
         f"<!-- generated by greenhouse/booklet/make_gallery.py from {b['pdf']}: do not edit -->", "",
         f"{b['what']} {counts(info)}. Each page below is the PDF's own page as an image; "
         f"click one for full size.", "",
         f"[PDF]({rel(d, b['pdf'])}) · [Guide]({rel(d, b['guide'])}) · " + " · ".join(nav), "",
         f"<details><summary><b>Contents</b>, {len(info['pages'])} pages</summary>", "", contents, "",
         "</details>", "", "---", ""]
    for k, ((t, s), a) in enumerate(zip(info["pages"], info["anchors"]), 1):
        L += [f"### {heading(k, t, s)}", "",
              f"![{b['name']}, page {k}: {t}]({b['slug']}/p{k:02d}.jpg)", ""]
    L += ["---", "", " · ".join(nav), ""]
    return "\n".join(L)


def gallery(infos):
    d = "docs/booklets"
    total = sum(len(infos[b["slug"]]["pages"]) for b in BOOKLETS)
    L = ["# The assembly booklets", "",
         "<!-- generated by greenhouse/booklet/make_gallery.py: do not edit -->", "",
         f"Every page of the {WORDS.get(len(BOOKLETS), len(BOOKLETS))} assembly booklets, {total} pages "
         "in build order. "
         "Click a page to read it full size in its booklet's page-by-page view; each booklet's "
         "PDF is the one to print.", ""]
    L += ["| | booklet | what it builds | pages |", "|---|---|---|---|"]
    for i, b in enumerate(BOOKLETS, 1):
        L.append(f"| {i} | [{b['name']}](#{slugify(f'{i} · ' + b['name'], {})}) | {b['what']} | "
                 f"{counts(infos[b['slug']])} |")
    L.append("")
    for i, b in enumerate(BOOKLETS, 1):
        info = infos[b["slug"]]
        L += [f"## {i} · {b['name']}", "", f"{b['what']} {counts(info)}.", "", links(b, d), "",
              thumb_rows(b, info, range(1, len(info["pages"]) + 1), d), ""]
    return "\n".join(L)


def readme_block(infos):
    L = ["Each booklet can be paged through here before you print it: "
         "[**every page of every booklet**](docs/booklets/README.md). Click a page below to open "
         "it full size in its booklet.", ""]
    for i, b in enumerate(BOOKLETS, 1):
        info = infos[b["slug"]]
        L += [f"### {i} · {b['name']}", "", f"{b['what']} {counts(info)}.", "",
              thumb_rows(b, info, b["highlights"], "."), "", links(b, "."), ""]
    return "\n".join(L).rstrip() + "\n"


def module_block(b, info):
    d = os.path.dirname(b["guide"])
    return (thumb_rows(b, info, b["highlights"], d) + "\n\n"
            f"**The booklet, page by page:** [all {len(info['pages'])} pages]"
            f"({rel(d, 'docs/booklets/' + b['slug'] + '.md')}) · [PDF]({rel(d, b['pdf'])})\n")


def inject(path, tag, body, after=None):
    """Replace the block between <!-- tag:start --> and <!-- tag:end -->; if there is none, put it
    after the first line matching `after`."""
    start = f"<!-- {tag}:start (generated by greenhouse/booklet/make_gallery.py) -->"
    end = f"<!-- {tag}:end -->"
    text = open(path, encoding="utf-8").read()
    block = f"{start}\n{body.rstrip()}\n{end}"
    m = re.search(rf"<!-- {tag}:start[^>]*-->.*?<!-- {tag}:end -->", text, re.S)
    if m:
        text = text[:m.start()] + block + text[m.end():]
    else:
        lines = text.split("\n")
        at = next(i for i, ln in enumerate(lines) if re.search(after, ln))
        lines[at + 1:at + 1] = ["", block]
        text = "\n".join(lines)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# --------------------------------------------------------------------------- main

def main(force=False):
    os.makedirs(OUT, exist_ok=True)
    man_path = os.path.join(OUT, "pages.json")
    manifest = json.load(open(man_path)) if os.path.exists(man_path) else {}
    infos = {}
    for b in BOOKLETS:
        pdf = os.path.join(ROOT, b["pdf"])
        h = sha(pdf)
        folder = os.path.join(OUT, b["slug"])
        old = manifest.get(b["slug"], {})
        pages = [tuple(p) for p in old.get("pages", [])]
        have = pages and all(os.path.exists(os.path.join(folder, f"{c}{k:02d}.jpg"))
                             for k in range(1, len(pages) + 1) for c in "pt")
        if force or old.get("sha256") != h or not have:
            pages = page_titles(pdf)
            n = render(pdf, folder)
            assert n == len(pages), (b["slug"], n, len(pages))
            print(f"{b['slug']}: rendered {n} pages")
        else:
            print(f"{b['slug']}: unchanged, {len(pages)} pages")
        bad = [k for k in b["highlights"] if not 1 <= k <= len(pages)]
        assert not bad, (b["slug"], bad)
        infos[b["slug"]] = dict(sha256=h, pdf=b["pdf"], pages=[list(p) for p in pages])
        infos[b["slug"]]["anchors"] = anchors(pages)

    cover = os.path.join(OUT, "cover.jpg")
    src = os.path.join(ROOT, COVER_SRC)
    if force or not os.path.exists(cover) or os.path.getmtime(cover) < os.path.getmtime(src):
        im = Image.open(src).convert("RGB")
        im = im.resize((COVER_W, round(im.height * COVER_W / im.width)), Image.LANCZOS)
        im.save(cover, "JPEG", quality=84, optimize=True, progressive=True)

    for i, b in enumerate(BOOKLETS):
        with open(os.path.join(OUT, f"{b['slug']}.md"), "w", encoding="utf-8") as f:
            f.write(booklet_page(i, b, infos[b["slug"]]))
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as f:
        f.write(gallery(infos))
    inject(os.path.join(ROOT, "README.md"), "booklets", readme_block(infos), after=r"^## Assembly booklets")
    for b in BOOKLETS:
        inject(os.path.join(ROOT, b["guide"]), "booklet", module_block(b, infos[b["slug"]]),
               after=r"^\*\*.*Rev [A-Z].*\*\*$")
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump({k: dict(sha256=v["sha256"], pdf=v["pdf"], pages=v["pages"]) for k, v in infos.items()},
                  f, indent=1, ensure_ascii=False)
        f.write("\n")
    total = sum(len(v["pages"]) for v in infos.values())
    print(f"{total} pages in {len(BOOKLETS)} booklets -> {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
