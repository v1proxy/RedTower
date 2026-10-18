from pathlib import Path

from gh.mods.gantry import Gantry
from gh.module import run

if __name__ == "__main__":
    run(Gantry, Path(__file__).with_name("manifest.yaml"), tick_s=0.2)     # status polled 5 times a second
