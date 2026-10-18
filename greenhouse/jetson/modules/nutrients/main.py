"""Nutrients module, stub. It runs, answers the module contract and shows up in the
interface, but has no dosing hardware behind it. Replace loop() when the pumps and the
EC and pH probes exist. The governor's dosing limit is zero until then."""
from pathlib import Path

from gh.module import Module, run


class Nutrients(Module):
    def setup(self):
        self.report("stub", "no dosing hardware installed")

    def on_cmd(self, data):
        self.report("stub", f"ignored command {data.get('op')!r}: no hardware")


if __name__ == "__main__":
    run(Nutrients, Path(__file__).with_name("manifest.yaml"))
