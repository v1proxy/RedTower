"""Shared test rig: the core services plus simulated ESPHome nodes, all on the in-memory bus."""
import atexit
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SCRATCH = tempfile.mkdtemp(prefix="gh-tests-")                 # every rig's data folder lives here
atexit.register(shutil.rmtree, SCRATCH, ignore_errors=True)
os.environ["GH_CONFIG_DIR"] = str(ROOT / "config")         # robot.yaml for the gantry

from gh import topics as T                      # noqa: E402
from gh.bus import MemoryBus                    # noqa: E402
from gh.core.safety import Governor             # noqa: E402
from gh.core.store import Store                 # noqa: E402
from gh.core.supervisor import Supervisor       # noqa: E402
from gh.manifest import load_dir                # noqa: E402
from gh.runtime import NullRuntime              # noqa: E402

LIMITS = yaml.safe_load((ROOT / "config" / "limits.yaml").read_text())
PROFILES = yaml.safe_load((ROOT / "config" / "profiles.yaml").read_text())


class Clock:
    def __init__(self, t=1_800_000_000.0): self.t = t      # fixed start so tests do not depend on today
    def __call__(self): return self.t
    def add(self, s): self.t += s


class SimNodes:
    """Publishes what Home Assistant's mqtt_statestream would publish for healthy nodes."""

    def __init__(self, bus, fahrenheit=False):
        self.bus, self.f = bus, fahrenheit

    def set(self, domain, obj, state, unit=None):
        base = f"{T.HA_STATE}/{domain}/greenhouse_{obj}"
        if unit:
            self.bus.publish(f"{base}/unit_of_measurement", json.dumps(unit), retain=True)
        self.bus.publish(f"{base}/state", str(state), retain=True)

    def healthy(self, vpd=1.0, moisture=55, temp_c=24.0):
        for node in ("tier_a", "tier_b", "tier_c", "utility"):
            self.set("binary_sensor", f"{node}_status", "on")
        for key in ("doors", "safety_circuit_tripped", "leak_detected", "leak_lockout", "reservoir_low_float",
                    "watering_active"):
            self.set("binary_sensor", f"utility_{key}", "off")
        self.set("sensor", "utility_reservoir_level", 80, "%")
        self.set("sensor", "utility_cabinet_power", 203, "W")
        for t in "abc":
            temp = temp_c * 1.8 + 32 if self.f else temp_c
            self.set("sensor", f"tier_{t}_air_temperature", round(temp, 2), "°F" if self.f else "°C")
            self.set("sensor", f"tier_{t}_air_humidity", 60, "%")
            self.set("sensor", f"tier_{t}_vpd", vpd, "kPa")
            self.set("sensor", f"tier_{t}_leaf_vpd", vpd - 0.1, "kPa")
            self.set("sensor", f"tier_{t}_leaf_to_air_delta", -1.2, "°C")
            self.set("sensor", f"tier_{t}_median_moisture", moisture, "%")
        self.set("sensor", "tier_c_co2", 610, "ppm")


class Rig:
    def __init__(self, authority="auto", installed=None):
        self.clock, self.bus, self.rt = Clock(), MemoryBus(), NullRuntime()
        self.ms = load_dir(ROOT / "modules")
        for m in self.ms.values():
            m.installed = True
        self.tmp = tempfile.mkdtemp(dir=SCRATCH)
        os.environ["GH_DATA_DIR"] = self.tmp
        self.sup = Supervisor(self.bus, self.ms, self.rt, Path(self.tmp) / "s.json", authority, self.clock)
        self.gov = Governor(self.bus, self.ms, LIMITS, self.clock)
        self.store = Store(self.bus, ":memory:", PROFILES, self.clock)
        self.sup.start(); self.gov.start(); self.store.start()
        self.nodes = SimNodes(self.bus)
        self.mods = {}
        self.mirror = True                  # Home Assistant keeps resyncing, as it would in real life
        self.beat_all()

    def add(self, cls, name):
        mod = cls(self.bus, self.ms[name], self.clock)
        mod.start()
        self.mods[name] = mod
        return mod

    def beat_all(self, skip=()):
        for name, m in self.ms.items():
            if name not in skip and name not in getattr(self, "mods", {}):
                self.bus.publish(T.health(name), {"alive": True, "state": "stub" if m.stub else "running"})

    def run(self, seconds, step=60):
        """Advance time, ticking every module."""
        for _ in range(int(seconds // step)):
            self.clock.add(step)
            if self.mirror:
                self.bus.publish(f"{T.HA_STATE}/heartbeat", "1")
            for mod in self.mods.values():
                mod.tick()
            self.gov.tick()
            self.beat_all()

    def state(self, name):
        return self.bus.get(T.status(name))["state"]

    def driven(self, actuator):
        return [json.loads(p) for t, p in self.bus.sent if t == T.actuator_set(actuator)]

    def verdicts(self, source=None):
        out = [json.loads(p) for t, p in self.bus.sent if t.startswith(f"{T.ROOT}/safety/verdict/")]
        return [v for v in out if source is None or v["source"] == source]

    def plant(self, pos, kind="basil"):
        self.bus.publish(T.STORE_CMD_UI, {"op": "replace_plant", "position": pos, "type": kind})
