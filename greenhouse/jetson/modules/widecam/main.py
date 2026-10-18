from pathlib import Path

from gh.mods.widecam import Widecam
from gh.module import run

if __name__ == "__main__":
    run(Widecam, Path(__file__).with_name("manifest.yaml"), tick_s=5.0)
