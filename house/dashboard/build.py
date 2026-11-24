"""Builds the dashboard's one resource file from its two parts.

    python build.py           writes www/redtower-ui/redtower-ui.js
    python build.py --check   exits 1 if www/redtower-ui/redtower-ui.js is not what the sources build

Part A (src/redtower-ui.js): the look, the house in lines (custom:rt-house-card) and the helpers the
button-card templates call. Part B (src/rt-cards.js): the other cards. Home Assistant loads the result as
one JavaScript module, /local/redtower-ui/redtower-ui.js?v=<version>.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = [os.path.join(HERE, "src", "redtower-ui.js"), os.path.join(HERE, "src", "rt-cards.js")]
OUT = os.path.join(HERE, "www", "redtower-ui", "redtower-ui.js")


def build():
    return "".join(open(p, encoding="utf-8", newline="").read() for p in PARTS)


def main():
    text = build()
    version = re.search(r'const VERSION = "([^"]+)"', text).group(1)
    if "--check" in sys.argv:
        current = open(OUT, encoding="utf-8", newline="").read() if os.path.exists(OUT) else ""
        if current != text:
            print(f"{OUT} is out of date: run python build.py")
            sys.exit(1)
        print(f"redtower-ui.js {version} matches its sources")
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"{OUT}: redtower-ui.js {version}, {len(text)} characters")


if __name__ == "__main__":
    main()
