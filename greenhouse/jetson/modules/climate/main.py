from pathlib import Path

from gh.mods.climate import Climate
from gh.module import run

if __name__ == "__main__":
    run(Climate, Path(__file__).with_name("manifest.yaml"))
