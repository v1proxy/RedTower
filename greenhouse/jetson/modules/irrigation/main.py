from pathlib import Path

from gh.mods.irrigation import Irrigation
from gh.module import run

if __name__ == "__main__":
    run(Irrigation, Path(__file__).with_name("manifest.yaml"))
