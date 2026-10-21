"""Gantry (driver). X on the bottom rail, Z on the mast, FluidNC on the Jackpot3 over USB.

Backend "fluidnc" drives the real controller (fluidnc.py). Backend "sim" has the same
interface and only takes time, so everything above it is built and tested before the
hardware exists. Plant and tier coordinates come from config/robot.yaml.

A plant move needs a homing cycle first: after power-up, an alarm or a stop the position is
not trusted. "home" homes if needed, then goes to the park position. "to_bin" and
"to_waste" go to robot.yaml's "bin" and "waste": the folded arm over the harvest drawer, or
over the base pan clear of it, where the Herb Snip lets go of what it holds.

The gantry never travels with the arm out of the lane. It publishes the gantry_still
interlock the arm needs, and refuses to move itself unless the arm reports parked."""
import os
from pathlib import Path

import yaml

from .. import topics as T
from ..bus import loads
from ..module import Module
from .fluidnc import FluidNC, SerialLink

STATE = f"{T.ROOT}/gantry/state"
ARM_STATE = f"{T.ROOT}/arm/state"
RECONNECT_S = 10
SILENT_S = 5             # no status report for this long: the controller is not answering


def load_layout(path=None):
    path = Path(path or Path(os.environ.get("GH_CONFIG_DIR", "/app/config")) / "robot.yaml")
    return yaml.safe_load(path.read_text())


class SimController:
    """Same interface as FluidNC. Moves and homing take travel_s and always succeed."""

    def __init__(self, clock, travel_s, park=(0.0, 0.0)):
        self.clock, self.travel_s, self.park = clock, travel_s, park
        self.state, self.sub, self.mpos, self.homed, self.homing = "Idle", "", None, False, False
        self.alarm = self.error = ""
        self.pending, self.stopping, self.goal, self.until = (), None, None, 0.0

    def home(self):
        self.homing, self.homed, self.alarm, self.error = True, False, "", ""
        self._go(self.park)

    def move_to(self, x, z):
        self.error = ""
        self._go((float(x), float(z)))

    def _go(self, goal):
        self.goal, self.until, self.state = goal, self.clock() + self.travel_s, "Run"

    def stop(self):
        self.goal, self.state, self.homed, self.homing = None, "Idle", False, False

    def poll(self):
        if self.goal is not None and self.clock() >= self.until:
            self.mpos, self.goal, self.state = self.goal, None, "Idle"
            if self.homing:
                self.homing, self.homed = False, True

    def idle_at(self, x, z, tol=0.05):
        return (self.state == "Idle" and self.mpos is not None and
                abs(self.mpos[0] - x) <= tol and abs(self.mpos[1] - z) <= tol)

    def silent_for(self):
        return 0.0

    def close(self): pass


class Gantry(Module):
    def setup(self):
        self.layout = load_layout()
        self.at, self.target, self.req, self.error = "unknown", None, None, ""
        self.deadline, self.retry_at, self.last = 0.0, 0.0, None
        self.arm, self.lock, self.ctl = {}, None, None
        self.bus.subscribe(ARM_STATE, lambda t, p: setattr(self, "arm", loads(p, {}) or {}))
        self.bus.subscribe(T.actuator_set("gantry"), self._on_set)
        self._connect()
        self._pub()

    # ---- controller
    def _connect(self):
        backend = self.config["backend"]
        try:
            if backend == "sim":
                park = self.layout["park"]
                self.ctl = SimController(self.clock, self.config["sim_travel_s"], (park["x"], park["z"]))
                self.report("stub", "simulated motion, no hardware")
            elif backend == "fluidnc":
                link = SerialLink(self.config["port"], self.config["baud"])
                self.ctl = FluidNC(link, self.clock, self.layout["feed_mm_min"])
                self.report("running", f"FluidNC on {self.config['port']}, not homed")
            else:
                self.report("fault", f"unknown backend {backend!r}")
        except Exception as exc:                          # unplugged, wrong port, no permission
            self.ctl = None
            self.retry_at = self.clock() + RECONNECT_S
            self.report("fault", f"controller not available: {exc}")

    def _lost(self, why):
        if self.ctl:
            try:
                self.ctl.close()
            except Exception:
                pass
        self.ctl, self.target, self.at = None, None, "unknown"
        self.retry_at = self.clock() + RECONNECT_S
        self.report("fault", why)
        self._pub()

    def moving(self):
        c = self.ctl
        return self.target is not None or bool(c and (c.state in ("Run", "Jog", "Home") or c.stopping is not None
                                                     or (c.state, c.sub) == ("Hold", "1")))

    def arm_stowed(self):
        return self.arm.get("pose") == "parked" and not self.arm.get("busy")

    def _pub(self):
        lock = "OPEN" if self.moving() else "OK"
        if lock != self.lock:                                   # interlock first, so it is in place
            self.lock = lock                                    # before anyone sees the new state
            self.bus.publish(T.interlock("gantry_still"), lock, retain=True)
        c = self.ctl
        pos = c.mpos if c and c.mpos else (None, None)
        body = {"at": self.at, "busy": self.moving(), "id": self.req, "error": self.error,
                "homed": bool(c and c.homed), "controller": c.state if c else "disconnected",
                "x_mm": None if pos[0] is None else round(pos[0]), "z_mm": None if pos[1] is None else round(pos[1])}
        if body != self.last:
            self.last = body
            self.bus.publish(STATE, body, retain=True)

    # ---- commands from the governor
    def _on_set(self, topic, payload):
        cmd = loads(payload, {})
        if not self.enabled or not isinstance(cmd, dict):
            return
        action = cmd.get("action")
        if action == "stop":
            if self.ctl:
                self.ctl.stop()
            self.target, self.at, self.error = None, "unknown", ""      # stopped mid-travel: position not trusted
            return self._pub()
        if action not in ("home", "goto", "to_bin", "to_waste"):
            return
        self.req, self.error = cmd.get("id"), ""
        problem = self.refusal(action, cmd.get("position"))
        if problem:
            self.error = f"refused: {problem}"
            self.report(self.state, self.error)
            return self._pub()
        if action == "home" and not self.ctl.homed:
            self.ctl.home()
            self.target = ("home", None, None)
        else:
            where = {"goto": cmd.get("position"), "to_bin": "bin", "to_waste": "waste"}.get(action)
            x, z = self.coords(where)
            self.ctl.move_to(x, z)
            self.target = ("home" if action == "home" else where, x, z)
        self.at, self.deadline = "moving", self.clock() + self.config["move_timeout_s"]
        self._pub()

    def coords(self, position):
        if position is None:
            return float(self.layout["park"]["x"]), float(self.layout["park"]["z"])
        if position in ("bin", "waste"):
            return float(self.layout[position]["x"]), float(self.layout[position]["z"])
        return float(self.layout["plants"][position]), float(self.layout["tiers"][position[0]])

    def refusal(self, action, position):
        if self.ctl is None:
            return "controller not connected"
        if not self.arm_stowed():
            return "arm is not stowed"
        if self.moving():
            return "already moving"
        if action in ("goto", "to_bin", "to_waste"):
            if action != "goto":
                position = "bin" if action == "to_bin" else "waste"
                if not isinstance(self.layout.get(position), dict):
                    return f"robot.yaml has no {position} position"
            elif position not in self.layout["plants"] or str(position)[:1] not in self.layout["tiers"]:
                return f"no coordinates for {position}"
            if not self.ctl.homed:
                return "not homed: send home first"
            x, z = self.coords(position)
            t = self.layout["travel"]
            if not (t["x_min"] <= x <= t["x_max"] and t["z_min"] <= z <= t["z_max"]):
                return f"{position} at X {x:.0f} Z {z:.0f} is outside the travel in robot.yaml"
        return ""

    # ---- every tick
    def loop(self):
        if self.ctl is None:
            if self.config["backend"] != "sim" and self.clock() >= self.retry_at:
                self._connect()
            return
        try:
            self.ctl.poll()
        except OSError as exc:                                  # USB unplugged mid-run
            return self._lost(f"controller connection lost: {exc}")
        c, now = self.ctl, self.clock()
        if self.target is not None:
            name, x, z = self.target
            if c.alarm or c.error:
                self._fail(c.alarm or c.error)
            elif x is not None and not c.homed:
                self._fail("controller lost its position (restart or reset)")
            elif name == "home" and x is None:
                if c.homed and not c.homing and c.state == "Idle":         # homing cycle done: go to park
                    px, pz = self.coords(None)
                    if not c.idle_at(px, pz):
                        c.move_to(px, pz)
                    self.target = ("home", px, pz)
            elif c.idle_at(x, z):
                self.at, self.target = name, None
                if self.state == "fault":
                    self.report("running" if self.config["backend"] != "sim" else "stub", "")
            if self.target is not None and now > self.deadline:
                c.stop()
                self._fail(f"move to {name} timed out")
        silent = c.silent_for()
        if silent is not None and silent > SILENT_S:
            return self._lost(f"controller has not answered for {silent:.0f} s")
        if c.alarm and self.state != "fault":
            self.report("fault", f"controller {c.alarm}: send home to clear")
        self._pub()

    def _fail(self, why):
        self.target, self.at, self.error = None, "unknown", why
        self.report("fault", why)
