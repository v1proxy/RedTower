from pathlib import Path

from gh.mods.d405 import D405
from gh.module import run

if __name__ == "__main__":
    run(D405, Path(__file__).with_name("manifest.yaml"))
