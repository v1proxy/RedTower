"""Supervisor: owns which modules are enabled, the authority ceiling and the kill
switch, starts and stops containers, and publishes the one status per module that
the interface shows."""
import json
import time
from pathlib import Path

from .. import topics as T
from ..bus import loads
from ..manifest import validate_set

STALE_S = 30          # no heartbeat for this long means the module is offline
AGENT_MODES = ("proposes", "autonomous")
UP = ("running", "stub")       # a simulated driver still counts as present for its dependents


class Supervisor:
    def __init__(self, bus, manifests, runtime, state_path, default_authority="auto", clock=time.time):
        self.bus, self.manifests, self.runtime, self.clock = bus, manifests, runtime, clock
        self.order = validate_set(manifests)
        self.path = Path(state_path)
        saved = loads(self.path.read_text(), {}) if self.path.exists() else {}
        self.enabled = {n: m.default_enabled for n, m in manifests.items()}
        self.enabled.update({k: v for k, v in saved.get("enabled", {}).items() if k in manifests})
        self.authority = saved.get("authority", default_authority)
        self.kill = bool(saved.get("kill", False))
        self.health = {}
        self.published = {}

    # ---- wiring
    def start(self):
        self.bus.subscribe(f"{T.ROOT}/+/enable/set", self._on_enable_set)
        self.bus.subscribe(f"{T.ROOT}/+/health", self._on_health)
        self.bus.subscribe(T.AUTHORITY_SET, self._on_authority)
        self.bus.subscribe(T.KILL_SET, self._on_kill)
        self.refresh(force=True)

    def _on_enable_set(self, topic, payload):
        name = topic.split("/")[1]
        m = self.manifests.get(name)
        if not m or m.always_on:
            return                      # core modules cannot be switched off
        self.enabled[name] = payload.strip().upper() == "ON"
        self.refresh()

    def _on_health(self, topic, payload):
        name = topic.split("/")[1]
        data = loads(payload, {})
        if name in self.manifests and isinstance(data, dict):
            data["seen"] = self.clock()
            self.health[name] = data
            self.refresh()

    def _on_authority(self, topic, payload):
        value = payload.strip().lower()
        if value in T.AUTHORITY:
            self.authority = value
            self.refresh()

    def _on_kill(self, topic, payload):
        self.kill = payload.strip().upper() == "ON"
        self.refresh()

    # ---- logic
    def wanted(self, name):
        """Should this module's container be running right now?"""
        m = self.manifests[name]
        if m.always_on:
            return True
        if not m.installed or not self.enabled[name] or self.authority == "off":
            return False
        if m.layer == "agent" and (self.kill or self.authority not in AGENT_MODES):
            return False
        return True

    def mode(self, name):
        m = self.manifests[name]
        if m.layer in ("core", "driver"):
            return ""
        if self.authority in ("off", "manual"):
            return self.authority if m.layer == "service" or self.authority == "off" else "paused"
        if m.layer == "service":
            return "auto"
        return self.authority if self.authority in AGENT_MODES else "paused"

    def compute(self):
        now, out = self.clock(), {}
        for name in self.order:
            m = self.manifests[name]
            h = self.health.get(name)
            alive = bool(h and h.get("alive") and now - h.get("seen", 0) <= STALE_S)
            detail = (h or {}).get("detail", "")
            if not m.installed:
                state = "missing"
            elif m.always_on:
                state = "running" if alive else "offline"
            elif self.authority == "off":
                state = "stopped"
            elif not self.enabled[name]:
                state = "disabled"
            elif m.layer == "agent" and self.kill:
                state = "halted"
            elif m.layer == "agent" and self.authority not in AGENT_MODES:
                state = "paused"
            elif any(out[d]["state"] not in UP for d in m.depends):
                state = "degraded"
                detail = "waiting on " + ", ".join(d for d in m.depends if out[d]["state"] not in UP)
            elif not alive:
                state = "offline"
            elif h.get("state") == "fault":
                state = "fault"
            elif h.get("state") == "stub" or (m.stub and h.get("state") != "running"):
                state = "stub"                  # the module knows its backend; the manifest is the default
            else:
                state = "running"
            out[name] = {"state": state, "mode": self.mode(name), "detail": detail,
                         "version": m.version, "layer": m.layer, "title": m.title}
        return out

    def refresh(self, force=False):
        self._pub(T.AUTHORITY_STATE, self.authority, force)
        self._pub(T.KILL_STATE, "ON" if self.kill else "OFF", force)
        for name, status in self.compute().items():
            self.runtime.want(name, self.wanted(name))
            self._pub(T.enable(name), "ON" if self.enabled[name] else "OFF", force)
            self._pub(T.status(name), json.dumps(status, sort_keys=True), force)
        self._save()

    def tick(self):
        self.refresh()

    def _pub(self, topic, payload, force):
        if force or self.published.get(topic) != payload:
            self.published[topic] = payload
            self.bus.publish(topic, payload, retain=True)

    def _save(self):
        data = json.dumps({"enabled": self.enabled, "authority": self.authority, "kill": self.kill})
        if not self.path.exists() or self.path.read_text() != data:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(data)
