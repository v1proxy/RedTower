from pathlib import Path

from gh.mods.motion import Motion
from gh.module import run

if __name__ == "__main__":
    run(Motion, Path(__file__).with_name("manifest.yaml"))
