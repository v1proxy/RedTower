"""Arm (driver), myCobot 280 Pi over TCP (mycobot.py), with the Herb Snip on its flange
(snip.py). Backend "sim" runs the same code on a simulated arm. Joint poses come from
config/arm.yaml: "stow", the transit fold inside the lane, and "look", the depth camera in
front of the pot. A capture moves to look, then asks the depth camera for a frame.

Actions, each a list of steps run in order (a joint move, a jaw move, a pause):
  park      to stow. The jaw keeps what it holds: the fold clears the tray line either way.
  capture   to look, then a depth frame.
  approach  jaw open, then the reach (simulated only: the real reach is not built yet).
  cut       jaw closed: the blade cuts and the pads hold. It stays closed through the park.
  release   parked only: jaw open, a pause, jaw closed. Motion takes the gantry first to the
            harvest drawer (robot.yaml "bin") or to the waste spot ("waste"): the arm itself
            never leaves the lane with what it cut.

The pose the arm reports is read from its joints, never assumed: parked means the joints are
at stow, the servos are powered and nothing is moving. The real arm is not moved until
arm.yaml is marked taught, and the jaw gets no pulse until its snip block is calibrated.

The arm publishes the arm_stowed interlock the gantry needs, and refuses to leave the lane
while the gantry is moving or is parked somewhere other than where the action belongs."""
import os
from pathlib import Path

import yaml

from .. import topics as T
from ..bus import loads
from ..module import Module
from . import mycobot
from . import snip as S

STATE = f"{T.ROOT}/arm/state"
GANTRY_STATE = f"{T.ROOT}/gantry/state"
ACTIONS = ("park", "capture", "approach", "cut", "release")
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
        self.retry_at, self.failures, self.ticks, self.snip = 0.0, 0, 0, None
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
                if not self.spec.get("taught"):
                    self.report("fault", "arm.yaml poses are not taught: the arm will not move")
                elif self.snip_problem():
                    self.report("running", f"myCobot at {self.config['host']}; Herb Snip: {self.snip_problem()}")
                else:
                    self.report("running", f"myCobot at {self.config['host']}")
            else:
                self.report("fault", f"unknown backend {backend!r}")
            self.snip = S.Snip(self.mc, self.spec.get("snip") or {}, self.clock) if self.mc else None
            self.ticks = 0                                  # check servo power on the first read
        except Exception as exc:                            # Pi booting, wrong address, no server
            self._lost(f"arm not reachable: {exc}")

    def snip_problem(self):
        spec = self.spec.get("snip") or {}
        bad = S.check_spec(spec)
        if bad:
            return bad[0]
        if self.config["backend"] != "sim" and not spec.get("calibrated"):
            return "arm.yaml snip block is not calibrated (tools_snip_check.py)"
        return ""

    def _lost(self, why):
        self.mc, self.job, self.angles, self.moving, self.snip = None, None, None, False, None
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

    def near(self, name_or_angles):
        tol = self.spec["tolerance_deg"]
        goal = self.spec["poses"][name_or_angles] if isinstance(name_or_angles, str) else name_or_angles
        return self.angles is not None and all(abs(a - b) <= tol for a, b in zip(self.angles, goal))

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

    def jaw(self):
        if self.snip is None:
            return "unknown"
        if not self.powered and self.config["backend"] != "sim":
            return "limp"                                       # no arm power, no pulses
        return self.snip.state()

    def _pub(self):
        lock = "OK" if self.pose == "parked" else "OPEN"
        if lock != self.lock:                                   # interlock first, so it is in place
            self.lock = lock                                    # before anyone sees the new state
            self.bus.publish(T.interlock("arm_stowed"), lock, retain=True)
        body = {"pose": self.pose, "busy": self.job is not None, "id": self.req, "error": self.error,
                "jaw": self.jaw(), "angles": None if self.angles is None else [round(a) for a in self.angles]}
        if body != self.last:
            self.last = body
            self.bus.publish(STATE, body, retain=True)

    # ---- commands from the governor
    def _on_set(self, topic, payload):
        cmd = loads(payload, {})
        if not self.enabled or not isinstance(cmd, dict) or cmd.get("action") not in ACTIONS:
            return
        action, now = cmd["action"], self.clock()
        self.req, self.error = cmd.get("id"), ""
        problem = self.refusal(cmd)
        if problem:
            self.error = f"refused: {problem}"
            self.report(self.state, self.error)
            return self.refresh()
        steps = self.steps(action)
        if self.job is not None:
            self.mc.stop()
        self.job = dict(cmd, steps=steps, i=-1, deadline=now + self._budget(action, steps))
        self._next_step()
        self.refresh()

    def steps(self, action):
        P = self.spec["poses"]
        if action == "park":
            return [("move", P["stow"])]
        if action == "capture":
            return [("move", P["look"])]
        if action == "approach":                                # sim only, see refusal()
            return [("jaw", "open"), ("sim", self.config["sim_move_s"])]
        if action == "cut":
            return [("jaw", "close")]
        return [("jaw", "open"), ("wait", self.spec["snip"].get("release_s", 1.0)), ("jaw", "close")]   # release

    def _budget(self, action, steps):
        moves = sum(1 for s in steps if s[0] == "move")
        return self.config["move_timeout_s"] * max(1, moves)

    def refusal(self, cmd):
        action = cmd.get("action")
        if self.mc is None:
            return "arm not connected"
        real = self.config["backend"] != "sim"
        if real and not self.spec.get("taught"):
            return "arm.yaml poses are not taught"
        if action == "park":
            return ""
        if action == "approach" and real:
            return "approach is not built for the real arm yet"
        if action in ("approach", "cut", "release") and self.snip_problem():
            return f"Herb Snip: {self.snip_problem()}"
        if action == "release" and self.pose != "parked":
            return f"release is from the stow pose, the arm is {self.pose}"
        if self.gantry.get("busy"):
            return "gantry is moving"
        if action == "release":
            return ""
        if self.gantry.get("at") != cmd.get("position"):
            return f"gantry is at {self.gantry.get('at')}, not at {cmd.get('position')}"
        return ""

    # ---- steps
    def _next_step(self):
        job = self.job
        job["i"] += 1
        if job["i"] >= len(job["steps"]):
            return self._done(job)
        kind, arg = job["steps"][job["i"]]
        now = self.clock()
        job["sent"] = now
        if kind == "move":
            self.mc.send_angles(arg, self.spec["speed"])
        elif kind == "jaw":
            (self.snip.open if arg == "open" else self.snip.close)()
        else:                                                   # wait, sim
            job["until"] = now + float(arg)

    def _step_state(self):
        """'done', 'running' or a failure message for the current step."""
        job, now = self.job, self.clock()
        kind, arg = job["steps"][job["i"]]
        if kind == "move":
            if not self.moving and self.near(arg):
                return "done"
            if not self.moving and now - job["sent"] > START_GRACE_S:
                return f"{job['action']} stopped short of {self._name(arg)}"
            return "running"
        if kind == "jaw":
            return "done" if self.snip.settled() else "running"
        return "done" if now >= job["until"] else "running"

    def _name(self, angles):
        for name, pose in self.spec["poses"].items():
            if list(pose) == list(angles):
                return f"the {name} pose"
        return f"waypoint {[round(a) for a in angles]}"

    # ---- every tick
    def loop(self):
        self.ticks += 1
        if self.mc is None:
            if self.config["backend"] != "sim" and self.clock() >= self.retry_at:
                self._connect()
            return self.refresh()
        self.refresh()
        if self.job is None or self.mc is None:
            return
        for _ in range(len(self.job["steps"])):                 # a settled jaw lets the next step start now
            st = self._step_state()
            if st == "running":
                if self.clock() > self.job["deadline"]:
                    return self._fail(f"{self.job['action']} timed out")
                return
            if st != "done":
                return self._fail(st)
            self._next_step()
            if self.job is None:
                return

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
