"""Climate (service). Deterministic, no AI. The ESPHome nodes already run the photoperiod and
the exhaust thermostat on their own, so the plants are safe without this module. What this
adds is steering toward a VPD target, and pushing photoperiod and light settings to the nodes."""
from .. import topics as T
from ..bus import loads
from ..module import Module
from ..sensors import TIERS, Sensors

EVAL_S = 60
STARTUP_GRACE_S = 60     # retained readings take a moment to arrive after a restart
VERDICT_WAIT_S = 30      # a request with no verdict by then was lost (governor restarting)


class Climate(Module):
    def setup(self):
        self.s = Sensors(self.bus)
        self.started = self.clock()
        self.last_eval = self.last_humidify = 0.0
        self.exhaust_boost = False
        self.applied = {}
        self.inflight = {}           # request id -> (undo, sent at): undone if denied or lost
        self.bus.subscribe(T.actuator_set("climate_setpoint"), self._on_setpoint)
        self.bus.subscribe(f"{T.ROOT}/safety/verdict/+", self._on_verdict)

    def _on_setpoint(self, topic, payload):
        data = loads(payload, {})
        if data.get("action") == "vpd_target" and isinstance(data.get("value"), (int, float)):
            self.config["vpd_target"] = float(data["value"])
            self.save_config()

    def _ask(self, actuator, action, value, undo):
        """Request a setting. If the governor denies it, or the request is lost, undo() makes the
        next evaluation ask again instead of believing the setting was applied."""
        self.n = getattr(self, "n", 0) + 1
        rid = f"climate-{actuator}-{action}-{int(self.clock())}-{self.n}"
        self.inflight[rid] = (undo, self.clock())          # registered first: the verdict can arrive at once
        self.request(actuator, action, value, req_id=rid)

    def _on_verdict(self, topic, payload):
        v = loads(payload, {})
        entry = self.inflight.pop(v.get("id"), None)
        if entry and v.get("result") != "approved":
            entry[0]()

    def loop(self):
        now = self.clock()
        if now - self.last_eval < EVAL_S:
            return
        self.last_eval = now
        for rid, (undo, sent) in list(self.inflight.items()):
            if now - sent > VERDICT_WAIT_S:
                del self.inflight[rid]
                undo()
        self._push_light_settings()
        vpd = self.s.tier_mean("vpd")
        if vpd is None:
            self.last_eval = now - EVAL_S + 5                # look again in 5 s, not in a minute
            if now - self.started < STARTUP_GRACE_S:
                return self.report("running", "waiting for the first VPD reading")
            return self.report("fault", "no VPD reading from any tier")
        target, band = self.config["vpd_target"], self.config["vpd_band"]
        detail = f"VPD {vpd:.2f} kPa, target {target:.2f}"
        if vpd > target + band:                                   # air too dry
            if now - self.last_humidify >= self.config["humidify_gap_min"] * 60:
                self.last_humidify = now
                self.request("humidifier", "on", self.config["humidify_minutes"])
                detail += ", humidifying"
            self._boost(False)
        elif vpd < target - band:                                 # air too humid
            self._boost(True)
            detail += ", extra ventilation"
        else:
            self._boost(False)
        self.report("running", detail)

    def _boost(self, on):
        if on != self.exhaust_boost:
            self.exhaust_boost = on
            duty = self.config["exhaust_boost_duty"] if on else self.config["exhaust_base_duty"]
            self._ask("exhaust", "min_duty", duty, undo=lambda: setattr(self, "exhaust_boost", not on))

    def _push_light_settings(self):
        for tier in TIERS:
            for action, key in (("photoperiod", "photoperiod_hours"), ("intensity", "light_intensity")):
                want = self.config[key]
                if self.applied.get((tier, action)) != want:
                    self.applied[(tier, action)] = want
                    self._ask(f"light_{tier}", action, want,
                              undo=lambda k=(tier, action), w=want: self.applied.get(k) == w and self.applied.pop(k))

    def on_config(self):
        self.last_eval = 0.0
