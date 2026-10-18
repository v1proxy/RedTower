from pathlib import Path

from gh.mods.envagent import EnvAgent
from gh.module import run

if __name__ == "__main__":
    run(EnvAgent, Path(__file__).with_name("manifest.yaml"))
