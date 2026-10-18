from pathlib import Path

from gh.mods.arm import Arm
from gh.module import run

if __name__ == "__main__":
    run(Arm, Path(__file__).with_name("manifest.yaml"), tick_s=0.5)
