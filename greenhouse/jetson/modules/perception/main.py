from pathlib import Path

from gh.mods.perception import Perception
from gh.module import run

if __name__ == "__main__":
    run(Perception, Path(__file__).with_name("manifest.yaml"))
