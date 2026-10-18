from pathlib import Path

from gh.mods.tender import Tender
from gh.module import run

if __name__ == "__main__":
    run(Tender, Path(__file__).with_name("manifest.yaml"))
