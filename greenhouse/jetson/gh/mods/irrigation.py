"""Irrigation (service). Deterministic, no AI. Waters a tier when its median soil moisture is
below the threshold, at most once an hour per tier, only in the daytime window, never while
the robot is moving. Every run goes through the safety governor. The utility node keeps its
own leak lockout and pump watchdog whatever this module does."""
import time

from .. import topics as T
from ..module import Module
from ..sensors import TIERS, Sensors

EVAL_S = 900
STARTUP_GRACE_S = 60     # retained readings take a moment to arrive after a restart


class Irrigation(Module):
    def setup(self):
        self.s = Sensors(self.bus)
        self.started = self.clock()
        self.last_eval = 0.0
        self.last_run = {t: 0.0 for t in TIERS}
        self.robot_busy = False
        self.bus.subscribe(f"{T.ROOT}/robot/busy", lambda t, p: setattr(self, "robot_busy", p.strip().upper() == "ON"))

    def hour(self):
        return time.localtime(self.clock()).tm_hour

    def loop(self):
        now = self.clock()
        if now - self.last_eval < EVAL_S:
            return
        self.last_eval = now
        if self.robot_busy:
            return self.report("running", "waiting: robot is moving")
        if not self.config["start_hour"] <= self.hour() < self.config["end_hour"]:
            return self.report("running", "outside the watering window")
        notes = []
        for tier in TIERS:
            moisture = self.s.num(f"tier_{tier}_median_moisture")
            if moisture is None:
                notes.append(f"{tier.upper()} no reading")
                continue
            if moisture < self.config[f"threshold_{tier}"] and now - self.last_run[tier] >= self.config["min_gap_s"]:
                self.last_run[tier] = now
                self.request(f"water_{tier}", "run", self.config[f"run_{tier}_s"],
                             req_id=f"irrigation-{tier}-{int(now)}")
                notes.append(f"{tier.upper()} watering at {moisture:.0f}%")
            else:
                notes.append(f"{tier.upper()} {moisture:.0f}%")
        missing = sum("no reading" in n for n in notes)
        if missing == len(TIERS):
            self.last_eval = now - EVAL_S + 5                # look again in 5 s, not in 15 minutes
            if now - self.started < STARTUP_GRACE_S:
                return self.report("running", "waiting for the first moisture readings")
        self.report("fault" if missing == len(TIERS) else "running", ", ".join(notes))

    def on_config(self):
        self.last_eval = 0.0          # a new threshold or window applies now, not in 15 minutes
