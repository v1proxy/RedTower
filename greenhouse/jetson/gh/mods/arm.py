"""Arm (driver), myCobot 280 Pi over TCP (mycobot.py). Backend "sim" runs the same code on a
simulated arm. Joint poses come from config/arm.yaml: "stow", folded inside the lane, and
"look", the depth camera in front of the pot. A capture moves to look, then asks the depth
camera for a frame.

The pose the arm reports is read from its joints, never assumed: parked means the joints are
at stow, the servos are powered and nothing is moving. The real arm is not moved until
arm.yaml is marked taught.

The arm publishes the arm_stowed interlock the gantry needs, and refuses to leave the lane
while the gantry is moving or is parked at a different plant from the one asked about."""
import os
from pathlib import Path

import yaml

from .. import topics as T
from ..bus import loads
from ..module import Module
from . import mycobot

STATE = f"{T.ROOT}/arm/state"
GANTRY_STATE = f"{T.ROOT}/gantry/state"
RECONNECT_S = 10
READ_FAILURES = 3          # this many bad joint reads in a row means the link is gone
START_GRACE_S = 1.5        # a servo move may not report "moving" at once
POWER_EVERY = 5            # ticks between servo power checks


def load_spec(path=None):
    path = Path(path or Path(os.environ.get("GH_CONFIG_DIR", "/app/config")) / "arm.yaml")
    return yaml.safe_load(path.read_text())


class Arm(Module):
    def setup(self):
        self.spec = load_spec()
        self.job, self.pose, self.angles, self.moving, self.powered = None, "unknown", None, False, False
        self.mc, self.lock, self.last, self.gantry, self.error, self.req = None, None, None, {}, "", None
        self.retry_at, self.failures, self.ticks = 0.0, 0, 0
        self.bus.subscribe(GANTRY_STATE, lambda t, p: setattr(self, "gantry", loads(p, {}) or {}))
        self.bus.subscribe(T.actuator_set("arm"), self._on_set)
        self._connect()
        self.refresh()

    # ---- connection
    def _connect(self):
        backend = self.config["backend"]
        try:
            if backend == "sim":
                self.mc = mycobot.SimCobot(self.clock, self.config["sim_move_s"], self.spec["poses"]["stow"])
                self.report("stub", "simulated arm, no hardware")
            elif backend == "mycobot":
                self.mc = mycobot.connect(self.config["host"], self.config["port"])
                if not self.mc.is_power_on():
                    self.mc.power_on()
                if self.spec.get("taught"):
                    self.report("running", f"myCobot at {self.config['host']}")
                else:
                    self.report("fault", "arm.yaml poses are not taught: the arm will not move")
            else:
                self.report("fault", f"unknown backend {backend!r}")
            self.ticks = 0                                  # check servo power on the first read
        except Exception as exc:                            # Pi booting, wrong address, no server
            self._lost(f"arm not reachable: {exc}")

    def _lost(self, why):
        self.mc, self.job, self.angles, self.moving = None, None, None, False
        self.retry_at = self.clock() + RECONNECT_S
        self.report("fault", why)

    # ---- reading the arm
    def refresh(self):
        if self.mc is not None:
            try:
                angles = self.mc.get_angles()
                self.moving = self.mc.is_moving() == 1
                if self.ticks % POWER_EVERY == 0:
                    self.powered = self.mc.is_power_on() == 1
            except Exception as exc:                        # socket timeout, connection reset
                self._lost(f"arm connection lost: {exc}")
                angles = None
            if self.mc is not None:
                if mycobot.valid_angles(angles):
                    self.angles, self.failures = [float(a) for a in angles], 0
                else:
                    self.failures += 1
                    if self.failures >= READ_FAILURES:
                        self._lost(f"arm returns no joint angles ({angles!r})")
        self.pose = self.derive_pose()
        self._pub()

    def near(self, name):
        tol = self.spec["tolerance_deg"]
        return self.angles is not None and all(abs(a - b) <= tol for a, b in zip(self.angles, self.spec["poses"][name]))

    def derive_pose(self):
        if self.mc is None or self.angles is None:
            return "unknown"
        if self.job is not None or self.moving:
            return "moving"
        if self.near("stow") and self.powered:
            return "parked"
        if self.near("look"):
            return "at_plant"
        return "unknown"

    def _pub(self):
        lock = "OK" if self.pose == "parked" else "OPEN"
        if lock != self.lock:                                   # interlock first, so it is in place
            self.lock = lock                                    # before anyone sees the new state
            self.bus.publish(T.interlock("arm_stowed"), lock, retain=True)
        body = {"pose": self.pose, "busy": self.job is not None, "id": self.req, "error": self.error,
                "angles": None if self.angles is None else [round(a) for a in self.angles]}
        if body != self.last:
            self.last = body
            self.bus.publish(STATE, body, retain=True)

    # ---- commands from the governor
    def _on_set(self, topic, payload):
        cmd = loads(payload, {})
        if not self.enabled or not isinstance(cmd, dict) or cmd.get("action") not in ("park", "capture", "approach", "cut"):
            return
        action, now = cmd["action"], self.clock()
        self.req, self.error = cmd.get("id"), ""
        problem = self.refusal(cmd)
        if problem:
            self.error = f"refused: {problem}"
            self.report(self.state, self.error)
            return self.refresh()
        if self.job is not None:
            self.mc.stop()
        if action in ("park", "capture"):
            goal = "stow" if action == "park" else "look"
            self.mc.send_angles(self.spec["poses"][goal], self.spec["speed"])
            self.job = dict(cmd, goal=goal, sent=now, deadline=now + self.config["move_timeout_s"])
        else:                                                   # sim only: approach and cut take time
            self.job = dict(cmd, goal=None, sent=now, deadline=now + self.config["sim_move_s"])
        self.refresh()

    def refusal(self, cmd):
        action = cmd.get("action")
        if self.mc is None:
            return "arm not connected"
        if self.config["backend"] != "sim" and not self.spec.get("taught"):
            return "arm.yaml poses are not taught"
        if action == "park":
            return ""
        if action in ("approach", "cut") and self.config["backend"] != "sim":
            return f"{action} is not built for the real arm yet"
        if self.gantry.get("busy"):
            return "gantry is moving"
        if self.gantry.get("at") != cmd.get("position"):
            return f"gantry is at {self.gantry.get('at')}, not at {cmd.get('position')}"
        return ""

    # ---- every tick
    def loop(self):
        self.ticks += 1
        if self.mc is None:
            if self.config["backend"] != "sim" and self.clock() >= self.retry_at:
                self._connect()
            return self.refresh()
        self.refresh()
        job, now = self.job, self.clock()
        if job is None or self.mc is None:
            return
        if job["goal"] is None:
            if now >= job["deadline"]:
                self._done(job)
        elif not self.moving and self.near(job["goal"]):
            self._done(job)
        elif now > job["deadline"]:
            self._fail(f"{job['action']} timed out")
        elif not self.moving and now - job["sent"] > START_GRACE_S:
            self._fail(f"{job['action']} stopped short of the {job['goal']} pose")

    def _done(self, job):
        self.job = None
        if job["action"] == "capture":
            self.bus.publish(T.cmd("d405"), {"op": "capture", "position": job.get("position"), "id": job.get("id")})
        if job["action"] != "park":
            self.bus.publish(f"{T.ROOT}/arm/done", {"id": job.get("id"), "action": job["action"],
                                                   "position": job.get("position"), "value": job.get("value"),
                                                   "simulated": self.config["backend"] == "sim"})
        if self.state == "fault":
            self.report("stub" if self.config["backend"] == "sim" else "running", "")
        self.refresh()

    def _fail(self, why):
        try:
            self.mc.stop()
        except Exception:
            pass
        self.job, self.error = None, why
        self.report("fault", why)
        self.refresh()
