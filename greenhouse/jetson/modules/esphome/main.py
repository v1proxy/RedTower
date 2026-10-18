from pathlib import Path

from gh.mods.esphome import EsphomeLink
from gh.module import run

if __name__ == "__main__":
    run(EsphomeLink, Path(__file__).with_name("manifest.yaml"))
