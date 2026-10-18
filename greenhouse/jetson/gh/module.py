"""Base class every module is built on. It implements the module's side of the
contract: heartbeat on health, live config, commands, and a clean stop when disabled."""
import json
import os
import signal
import time
from pathlib import Path

import yaml

from . import topics as T
from .bus import MqttBus, loads
from .manifest import parse

HEARTBEAT_S = 10


class Module:
    def __init__(self, bus, manifest, clock=time.time):
        self.bus, self.manifest, self.clock = bus, manifest, clock
        self.name = manifest.name
        self.data_dir = Path(os.environ.get("GH_DATA_DIR", "/data"))
        self.config = dict(manifest.config)
        self.config.update(self._saved_config())
        self.enabled = True
        self.state, self.detail = ("stub" if manifest.stub else "running"), ""
        self._last_beat = 0.0
        self._seq = 0

    # ---- lifecycle
    def start(self):
        self.bus.subscribe(T.enable(self.name), self._on_enable)
        self.bus.subscribe(T.config_set(self.name), self._on_config)
        self.bus.subscribe(T.cmd(self.name), self._on_cmd)
        self.bus.publish(T.config(self.name), self.config, retain=True)
        self.setup()
        self.beat()

    def tick(self):
        if self.clock() - self._last_beat >= HEARTBEAT_S:
            self.beat()
        if self.enabled:
            self.loop()

    def beat(self):
        self._last_beat = self.clock()
        self.bus.publish(T.health(self.name), {
            "alive": True, "ts": self._last_beat, "state": self.state,
            "detail": self.detail, "version": self.manifest.version})

    def report(self, state, detail=""):
        """state is running, stub or fault. The supervisor turns it into the shown status."""
        self.state, self.detail = state, detail
        self.beat()

    def cycle_done(self, summary=""):
        """Agents call this after each completed cycle. Home Assistant's watchdog reads it."""
        self.bus.publish(T.cycle(self.name), {"ts": self.clock(), "summary": summary}, retain=True)

    def request(self, actuator, action, value=None, position=None, req_id=None, why="", **extra):
        """Ask the safety governor to drive an actuator. Modules never drive one directly.
        extra: "task" (the approved task an arm action belongs to) and "target" (what a tend
        task acts on) travel with the request to the actuator."""
        self._seq += 1
        req_id = req_id or f"{self.name}-{int(self.clock())}-{self._seq}"
        self.bus.publish(T.SAFETY_REQUEST, dict({"id": req_id, "source": self.name, "actuator": actuator,
                                                 "action": action, "value": value, "position": position,
                                                 "why": why}, **extra))
        return req_id

    # ---- contract handlers
    def _on_enable(self, topic, payload):
        self.enabled = payload.strip().upper() != "OFF"

    def _on_config(self, topic, payload):
        new = loads(payload)
        if not isinstance(new, dict):
            return
        unknown = set(new) - set(self.manifest.config)
        if unknown:
            self.report(self.state, f"ignored unknown config keys {sorted(unknown)}")
            new = {k: v for k, v in new.items() if k in self.manifest.config}
        self.config.update(new)
        self.save_config()
        self.on_config()

    # ---- config that survives a restart
    def _config_path(self):
        return self.data_dir / "config" / f"{self.name}.json"

    def _saved_config(self):
        """Changes made at run time, kept in the data folder. Keys the manifest no longer has are dropped."""
        try:
            saved = loads(self._config_path().read_text(), {})
        except OSError:
            return {}
        return {k: v for k, v in saved.items() if k in self.manifest.config} if isinstance(saved, dict) else {}

    def save_config(self):
        self.bus.publish(T.config(self.name), self.config, retain=True)
        changed = {k: v for k, v in self.config.items() if self.manifest.config.get(k) != v}
        try:
            path = self._config_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(changed, indent=1))
        except OSError as exc:
            self.detail = f"config not saved: {exc}"

    def _on_cmd(self, topic, payload):
        data = loads(payload)
        if isinstance(data, dict) and self.enabled:
            self.on_cmd(data)

    # ---- for subclasses
    def setup(self): pass
    def loop(self): pass
    def on_config(self): pass
    def on_cmd(self, data): pass


def run(module_cls, manifest_path, tick_s=1.0):
    """Container entry point."""
    manifest = parse(yaml.safe_load(Path(manifest_path).read_text()), str(manifest_path))
    will = json.dumps({"alive": False})
    bus = MqttBus(f"gh-{manifest.name}", will_topic=T.health(manifest.name), will_payload=will)
    mod = module_cls(bus, manifest)
    stop = {"now": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(now=True))
    mod.start()
    print(f"{manifest.name} {manifest.version} started", flush=True)
    while not stop["now"]:
        mod.tick()
        time.sleep(tick_s)
    bus.publish(T.health(manifest.name), will, retain=True)
    time.sleep(0.5)


def modules_dir():
    return os.environ.get("GH_MODULES_DIR", "/app/modules")
