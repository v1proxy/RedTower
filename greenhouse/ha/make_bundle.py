"""Package the Home Assistant side of Maag for download: the release zip and the HACS file.

    python greenhouse/ha/make_bundle.py            # build both
    python greenhouse/ha/make_bundle.py --check    # only check they agree with the sources (CI)

Writes
  dist/greenhouse-panel.js                          the card, where HACS looks for it (tracked)
  greenhouse/ha/build/maag-homeassistant-<v>.zip    the release asset (not tracked)

The zip mirrors Home Assistant's own config folder, so its config/ folder copies straight
over yours. docs/07-home-assistant.md is the guide; the zip's README is the short version.
"""
import argparse
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GH = HERE.parent
ROOT = GH.parent
VERSION = (ROOT / "VERSION").read_text().strip()
CARD = HERE / "www" / "greenhouse" / "greenhouse-panel.js"
DIST = ROOT / "dist" / "greenhouse-panel.js"
BUILD = HERE / "build"
NAME = f"maag-homeassistant-{VERSION}"

FILES = [  # (source, path inside the zip)
    (CARD, "config/www/greenhouse/greenhouse-panel.js"),
    (GH / "homeassistant" / "packages" / "greenhouse.yaml", "config/packages/greenhouse.yaml"),
    (HERE / "packages" / "greenhouse_jetson.yaml", "config/packages/greenhouse_jetson.yaml"),
    (HERE / "dashboard_view.yaml", "dashboard/greenhouse-view.yaml"),
    (HERE / "mosquitto-setup.md", "broker/mosquitto-setup.md"),
    (GH / "jetson" / "mosquitto-acl.sample", "broker/mosquitto-acl.sample"),
    (ROOT / "LICENSE", "LICENSE"),
]

README = f"""# Maag for Home Assistant, design {VERSION}

The Greenhouse view and the Home Assistant side of Maag, the Modular Agentic Autonomous
Greenhouse. The full guide, with the control system and every part of the interface:
https://github.com/v1proxy/RedTower/blob/v{VERSION}/docs/07-home-assistant.md

## Try it first, with simulated data

1. Copy `config/www/greenhouse/` into your Home Assistant `config/www/`.
2. Settings, Dashboards, three dots, Resources, Add resource:
   `/local/greenhouse/greenhouse-panel.js?v={VERSION}`, JavaScript module.
3. Open a dashboard, Edit, three dots, Raw configuration editor, and paste
   `dashboard/greenhouse-view.yaml` under `views:`. It runs with `demo: true`: nothing
   is sent anywhere, every button works on simulated data.

## Then for real

You need the Jetson stack running (greenhouse/jetson in the repository), the MQTT
integration on a Mosquitto broker (`broker/`), and the ESPHome nodes.

1. `configuration.yaml`:

       homeassistant:
         packages: !include_dir_named packages

2. Copy `config/packages/` into your config folder. Both files are needed:
   `greenhouse.yaml` (thresholds, run times, fallback watering, node alerts) and
   `greenhouse_jetson.yaml` (mirror, actuator bridge, watchdog, energy, alerts).
3. In both, replace `notify.notify` with your phone's service, for example
   `notify.mobile_app_<phone>`.
4. Restart Home Assistant, then remove `demo: true` from the view.
5. Energy dashboard: add `sensor.greenhouse_utility_cabinet_energy` as an individual
   device named Greenhouse.

When updating, copy the new files and change `?v=` on the resource so browsers reload it.

MIT licensed. Questions: contact@vittorionetti.com
"""


def card_version():
    m = re.search(r"const CARD_VERSION = '([^']+)'", CARD.read_text())
    return m.group(1) if m else None


def check():
    problems = []
    if card_version() != VERSION:
        problems.append(f"CARD_VERSION in the card is {card_version()}, VERSION is {VERSION}")
    if not DIST.exists() or DIST.read_bytes() != CARD.read_bytes():
        problems.append("dist/greenhouse-panel.js differs from the card: run make_bundle.py")
    for src, _ in FILES:
        if not src.exists():
            problems.append(f"missing {src.relative_to(ROOT)}")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        problems = check()
        for p in problems:
            print("FAIL ", p)
        print("ok" if not problems else f"{len(problems)} problem(s)")
        sys.exit(1 if problems else 0)
    if card_version() != VERSION:
        sys.exit(f"set CARD_VERSION in {CARD.relative_to(ROOT)} to {VERSION} first")
    DIST.parent.mkdir(exist_ok=True)
    DIST.write_bytes(CARD.read_bytes())
    BUILD.mkdir(exist_ok=True)
    zpath = BUILD / f"{NAME}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{NAME}/README.md", README)
        z.writestr(f"{NAME}/VERSION", VERSION + "\n")
        for src, dst in FILES:
            z.write(src, f"{NAME}/{dst}")
    print(f"wrote {DIST.relative_to(ROOT)}")
    print(f"wrote {zpath.relative_to(ROOT)}  {zpath.stat().st_size // 1024} kB")
    for n in zipfile.ZipFile(zpath).namelist():
        print("   ", n)


if __name__ == "__main__":
    main()
