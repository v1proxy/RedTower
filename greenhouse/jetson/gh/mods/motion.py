"""Motion (service). Sequences the gantry and the arm. Every move is a request to the safety
governor, so an open door or the E-stop ends a sequence at once.

Two sequences:
  photo route   visit every living plant, take one depth capture, go home. Daily, or on command.
  tend task     an approved cut. Go to the plant, capture it again, find the approved candidate
                again in the new capture (same kind, within MATCH_MM of where it was), approach,
                cut (the Herb Snip cuts and holds), park holding it, then the gantry takes the
                folded arm to the harvest drawer for a harvest or a pinched tip, or to the waste
                spot for a removed leaf, and the jaw opens there. Then home. If the candidate
                cannot be found again, nothing cuts. The governor only allows the arm's part of
                it with the task's one-time grant.

The arm is parked inside the lane before every gantry move, and a park only counts as done
when the arm reports it. The governor and both drivers enforce the same rule."""
import math
import time

from .. import topics as T
from ..bus import loads
from ..module import Module

BUSY = f"{T.ROOT}/robot/busy"
BIN = f"{T.ROOT}/robot/bin"         # pieces in the harvest drawer since it was last emptied, retained
MATCH_MM = 25            # a leaf that moved further than this between captures is not trusted
STEP_ACTIONS = {"goto": ("gantry", "goto"), "home": ("gantry", "home"), "capture": ("arm", "capture"),
                "park": ("arm", "park"), "approach": ("arm", "approach"), "cut": ("arm", "cut"),
                "to_bin": ("gantry", "to_bin"), "to_waste": ("gantry", "to_waste"), "release": ("arm", "release")}
GRANTED = ("approach", "cut", "release")               # the arm's part of an approved tend task
ARM_DONE = ("approach", "cut", "release")              # finished when the arm says so
STATIONS = {"to_bin": "bin", "to_waste": "waste"}      # gantry steps that end at a named spot
THROWN = ("remove_leaf",)                             # what is cut and thrown away, not kept


def refind(target, candidates):
    """The candidate in a fresh capture that is the one the owner approved: same kind, nearest
    to where it was, and within MATCH_MM. Returns (candidate or None, distance or None)."""
    if not target or not target.get("xyz_mm"):
        return None, None
    same = [c for c in candidates if c.get("kind") == target.get("kind") and c.get("xyz_mm")]
    if not same:
        return None, None
    best = min(same, key=lambda c: math.dist(c["xyz_mm"], target["xyz_mm"]))
    d = math.dist(best["xyz_mm"], target["xyz_mm"])
    return (best if d <= MATCH_MM else None), round(d, 1)


class Motion(Module):
    def setup(self):
        self.plants, self.gantry, self.arm, self.queue = {}, {}, {}, []
        self.step = None                    # (kind, position, request id, deadline)
        self.last_route_day = None
        self.tasks, self.task, self.obs, self.captured, self.label_now = [], None, {}, {}, None
        self.bus.subscribe(f"{T.ROOT}/plant/+", lambda t, p: self.plants.__setitem__(t.split("/")[-1], loads(p, {})))
        self.bus.subscribe(f"{T.ROOT}/gantry/state", self._on_gantry)
        self.bus.subscribe(f"{T.ROOT}/arm/state", self._on_arm)
        self.bus.subscribe(f"{T.ROOT}/arm/done", self._on_arm_done)
        self.bus.subscribe(f"{T.ROOT}/capture/+", self._on_capture)
        self.bus.subscribe(f"{T.ROOT}/observation/+", self._on_observation)
        self.bus.subscribe(f"{T.ROOT}/safety/verdict/+", self._on_verdict)
        self.bus.subscribe(T.actuator_set("robot"), self._on_robot)
        self.bin_items, self.keep = None, False                 # until our own retained count comes back
        self.bus.subscribe(BIN, self._on_bin)
        self._busy(False)

    def _busy(self, on):
        self.busy = on
        self.bus.publish(BUSY, "ON" if on else "OFF", retain=True)

    def living(self):
        return sorted(p for p, d in self.plants.items() if d.get("type_confirmed") and d.get("status") != "dead")

    def idle(self):
        return not self.step and not self.queue

    def _first(self):
        return [("park", None)] + ([] if self.gantry.get("homed") else [("home", None)])   # no trusted position yet

    # ---- commands
    def _on_bin(self, topic, payload):
        if self.bin_items is None:
            n = loads(payload, 0)
            self.bin_items = n if isinstance(n, int) and not isinstance(n, bool) else 0

    def _bin(self, n):
        self.bin_items = n
        self.bus.publish(BIN, n, retain=True)

    def on_cmd(self, data):
        op = data.get("op")
        if op == "stop":
            return self._abort("stopped by command")
        if op == "bin_emptied":
            return self._bin(0)
        if not self.idle():
            return self.report("running", "busy, command ignored")
        if op == "capture_route":
            self.start_route(self.living())
        elif op == "visit" and data.get("position") in self.living():
            self.start_route([data["position"]])
        elif op == "home":
            self.queue = [("park", None), ("home", None)]
            self._busy(True)

    def _on_robot(self, topic, payload):
        """An approved tend task from the governor. It waits if a sequence is running."""
        cmd = loads(payload, {})
        if self.enabled and isinstance(cmd, dict) and cmd.get("action") == "tend" and cmd.get("position"):
            self.tasks.append(cmd)

    def start_route(self, positions):
        if not positions:
            return self.report("running", "no living plants to visit")
        self.queue = (self._first() + [s for p in positions for s in (("goto", p), ("capture", p), ("park", None))]
                      + [("home", None)])
        self._busy(True)
        self.report("running", f"photo route: {len(positions)} plants")

    def start_tend(self, task):
        pos = task["position"]
        self.task, self.label_now = task, None
        keep = ((task.get("target") or {}).get("action") not in THROWN)
        self.keep = keep
        if keep and (self.bin_items or 0) >= self.config["bin_capacity"]:
            self._journal("stopped", f"the harvest drawer holds {self.bin_items} pieces: empty it, then press "
                                     "Harvest drawer emptied")
            return self.report("running", "harvest drawer full")
        after = [("to_bin", None) if keep else ("to_waste", None), ("release", pos)]
        self.queue = self._first() + [("goto", pos), ("capture", pos), ("find", pos), ("approach", pos),
                                      ("cut", pos), ("park", None)] + after + [("home", None)]
        self._busy(True)
        self.report("running", f"tend task at {pos}: {task.get('value')}")

    # ---- sequencing
    def loop(self):
        now = self.clock()
        lt = time.localtime(now)
        if self.idle() and self.tasks:
            self.start_tend(self.tasks.pop(0))
        elif (self.idle() and lt.tm_hour == self.config["capture_hour"] and self.last_route_day != lt.tm_yday):
            self.last_route_day = lt.tm_yday
            self.start_route(self.living())
        if self.step:
            kind, pos, rid, deadline = self.step
            done = ((kind == "goto" and self.gantry.get("at") == pos and not self.gantry.get("busy")) or
                    (kind in STATIONS and self.gantry.get("at") == STATIONS[kind] and not self.gantry.get("busy")) or
                    (kind == "home" and self.gantry.get("at") == "home" and not self.gantry.get("busy")) or
                    (kind == "park" and self.arm.get("pose") == "parked" and not self.arm.get("busy")))
            if kind == "find":
                obs = self.obs.get(pos)
                if obs and obs.get("ts") == self.captured.get(pos):          # the observation of this capture
                    c, d = refind((self.task or {}).get("target"), obs.get("candidates", []))
                    if c is None:
                        then = ((self.task or {}).get("target") or {}).get("label")
                        return self._abort(f"{then} not found again in the new capture"
                                           + (f" (nearest {d} mm away)" if d is not None else "") + ": nothing cut")
                    self.label_now, done = c["label"], True
            if done:
                self.step = None
            elif now > deadline:
                return self._abort(f"timed out on {kind} {pos or ''}".strip())
        if not self.step and self.queue:
            kind, pos = self.queue.pop(0)
            self.n = getattr(self, "n", 0) + 1
            rid = f"motion-{int(now)}-{self.n}"
            self.step = (kind, pos, rid, now + self.config["step_timeout_s"])   # set first: the verdict can arrive at once
            if kind in STEP_ACTIONS:
                actuator, action = STEP_ACTIONS[kind]
                extra = {}
                if kind in GRANTED:
                    extra = {"task": self.task["id"]}
                why = f"tend task {self.task['id']}" if self.task else "photo route"
                self.request(actuator, action, self.label_now if kind in ("approach", "cut") else None, pos,
                             req_id=rid, why=why, **extra)
        elif self.idle() and self.busy:
            if self.task:
                self._journal("done", f"cut {self.label_now} (approved as {self.task['target'].get('label')})")
            self._busy(False)
            self.report("running", "idle")

    def _journal(self, result, note):
        t, self.task = self.task, None
        self.bus.publish(T.log("tend"), {"task": t["id"], "position": t.get("position"), "value": t.get("value"),
                                         "result": result, "note": note, "ts": self.clock()})

    def _on_gantry(self, topic, payload):
        self.gantry = loads(payload, {}) or {}
        self._driver_refused(self.gantry, ("goto", "home") + tuple(STATIONS))

    def _on_arm(self, topic, payload):
        self.arm = loads(payload, {}) or {}
        self._driver_refused(self.arm, ("capture",) + ARM_DONE)

    def _driver_refused(self, state, kinds):
        if self.step and self.step[0] in kinds and state.get("error") and state.get("id") == self.step[2]:
            self._abort(f"{self.step[0]} refused by the driver: {state['error']}")

    def _on_arm_done(self, topic, payload):
        done = loads(payload, {}) or {}
        if self.step and self.step[0] in ARM_DONE and done.get("id") == self.step[2]:
            if self.step[0] == "release" and getattr(self, "keep", False) and self.gantry.get("at") == "bin":
                self._bin((self.bin_items or 0) + 1)
            self.step = None

    def _on_capture(self, topic, payload):
        pos = topic.split("/")[-1]
        self.captured[pos] = (loads(payload, {}) or {}).get("ts")
        if self.step and self.step[0] == "capture" and pos == self.step[1]:
            self.step = None

    def _on_observation(self, topic, payload):
        obs = loads(payload, {}) or {}
        if obs.get("position"):
            self.obs[obs["position"]] = obs

    def _on_verdict(self, topic, payload):
        v = loads(payload, {})
        if self.step and v.get("id") == self.step[2] and v.get("result") != "approved":
            self._abort(f"{self.step[0]} refused: {v.get('reason')}")

    def _abort(self, why):
        was_active = bool(self.step or self.queue)
        self.step, self.queue = None, []
        if was_active:
            self.request("gantry", "stop", why=why)
            self.request("arm", "park", why=why)
        if self.task:
            self._journal("stopped", why)
        self._busy(False)
        self.report("running", f"route ended: {why}")
