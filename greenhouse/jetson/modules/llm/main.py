from pathlib import Path

from gh.mods.llm import LlmGateway
from gh.module import run

if __name__ == "__main__":
    run(LlmGateway, Path(__file__).with_name("manifest.yaml"))
