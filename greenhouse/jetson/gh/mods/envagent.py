"""Environment agent, modelled on the Sol biodome loop: wake every 30 minutes, read the
sensors, decide, act. It has no direct control. Every action is a request to the safety
governor, which bounds it, and in "proposes" mode holds it for the user's approval."""
import json
import time

from .. import topics as T
from ..bus import loads
from ..module import Module
from ..sensors import TIERS, Sensors
from .llm import reply_topic

OUTPUT = f"{T.ROOT}/envagent/output"
TIER = {"type": "string", "enum": ["a", "b", "c"]}
TOOL = {
    "name": "decide",
    "description": "Report your assessment of the greenhouse and the actions to take this cycle.",
    "input_schema": {"type": "object", "required": ["assessment", "actions", "note"], "properties": {
        "assessment": {"type": "string", "description": "Two or three plain sentences for the owner."},
        "note": {"type": "string", "description": "One line to remember for the next cycles. May be empty."},
        "actions": {"type": "array", "maxItems": 4, "items": {"type": "object", "required": ["type", "why"], "properties": {
            "type": {"type": "string", "enum": ["set_vpd_target", "water", "set_light_intensity", "set_photoperiod",
                                                "set_circulation", "set_exhaust_setpoint", "humidify"]},
            "tier": TIER, "value": {"type": "number"}, "why": {"type": "string"}}}}}},
}
SYSTEM = """You tend an indoor herb and pepper greenhouse: three tiers (A: compact peppers, B and C: herbs) in soil \
pots with drip irrigation, LED grow lights, circulation and exhaust fans and a humidifier. You wake every 30 minutes.
Deterministic controllers already hold the photoperiod, an exhaust thermostat, VPD steering and moisture-based \
watering. Your job is to notice what they miss and adjust setpoints. Prefer no action when readings are in range.
Units: temperature in degrees C, VPD in kPa, moisture and humidity in percent. A missing reading is "null": never \
guess it, and say so. Every action is checked against hard limits and may need the owner's approval.
Action values: set_vpd_target kPa 0.6-1.5; water seconds 5-180 with tier; set_light_intensity percent 10-100 with \
tier; set_photoperiod hours 8-18 with tier; set_circulation percent 20-100 with tier; set_exhaust_setpoint degrees C \
20-30; humidify minutes 1-15."""
ACTIONS = {"set_vpd_target": ("climate_setpoint", "vpd_target", False), "water": ("water_{t}", "run", True),
           "set_light_intensity": ("light_{t}", "intensity", True), "set_photoperiod": ("light_{t}", "photoperiod", True),
           "set_circulation": ("circ_{t}", "duty", True), "set_exhaust_setpoint": ("exhaust", "setpoint", False),
           "humidify": ("humidifier", "on", False)}


class EnvAgent(Module):
    def setup(self):
        self.s = Sensors(self.bus)
        self.last_cycle, self.waiting, self.open, self.last_output = 0.0, None, {}, None
        self.notes_path = self.data_dir / "envagent_notes.json"
        self.notes = loads(self.notes_path.read_text(), []) if self.notes_path.exists() else []
        self.bus.subscribe(f"{T.ROOT}/llm/reply/+", self._on_reply)
        self.bus.subscribe(f"{T.ROOT}/safety/verdict/+", self._on_verdict)

    def snapshot(self):
        tiers = {t.upper(): {k: self.s.num(f"tier_{t}_{k}") for k in
                             ("air_temperature", "air_humidity", "vpd", "leaf_vpd", "leaf_to_air_delta", "median_moisture")}
                 for t in TIERS}
        return {"local_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(self.clock())), "tiers": tiers,
                "co2_ppm": self.s.num("tier_c_co2"), "reservoir_percent": self.s.num("utility_reservoir_level"),
                "cabinet_power_w": self.s.num("utility_cabinet_power"), "notes_from_earlier_cycles": self.notes[-8:]}

    def loop(self):
        now = self.clock()
        if self.waiting and now > self.waiting[1]:
            self.waiting = None
            self._finish("The language model did not answer in time.", [], failed=True)
        if not self.waiting and now - self.last_cycle >= self.config["cycle_minutes"] * 60:
            self.last_cycle = now
            job = f"envagent-{int(now)}"
            self.waiting = (job, now + self.config["reply_timeout_s"])
            self.bus.publish(T.cmd("llm"), {"id": job, "system": SYSTEM, "tool": TOOL,
                                            "user": "Current state:\n" + json.dumps(self.snapshot(), indent=1)})

    def _on_reply(self, topic, payload):
        reply = loads(payload, {})
        if not self.waiting or reply.get("id") != self.waiting[0]:
            return
        self.waiting = None
        self.open = {}
        if not reply.get("ok"):
            return self._finish(f"Language model unavailable: {reply.get('error')}", [], failed=True)
        decision = reply["tool_input"]
        results = []
        for act in (decision.get("actions") or [])[:4]:
            results.append(self._act(act if isinstance(act, dict) else {}))
        note = str(decision.get("note") or "").strip()
        if note:
            self.notes = (self.notes + [f"{time.strftime('%m-%d %H:%M', time.localtime(self.clock()))} {note[:200]}"])[-20:]
            self.notes_path.parent.mkdir(parents=True, exist_ok=True)
            self.notes_path.write_text(json.dumps(self.notes))
        self._finish(str(decision.get("assessment") or "").strip(), results)

    def _act(self, act):
        spec = ACTIONS.get(act.get("type"))
        if not spec:
            return {"type": act.get("type"), "result": "ignored", "reason": "unknown action"}
        actuator, action, needs_tier = spec
        if needs_tier and act.get("tier") not in TIERS:
            return {"type": act["type"], "result": "ignored", "reason": "tier missing"}
        self.n = getattr(self, "n", 0) + 1
        rid = f"envagent-{int(self.clock())}-{self.n}"
        entry = {"type": act["type"], "tier": act.get("tier"), "value": act.get("value"),
                 "result": "sent", "reason": ""}
        self.open[rid] = entry                      # registered first: the verdict can arrive at once
        self.request(actuator.format(t=act.get("tier")), action, act.get("value"), req_id=rid,
                     why=str(act.get("why", ""))[:300])
        return entry

    def _on_verdict(self, topic, payload):
        v = loads(payload, {})
        entry = self.open.get(v.get("id"))
        if entry is not None:
            entry.update(result=v.get("result"), reason=v.get("reason", ""))
            if self.last_output and entry in self.last_output["actions"]:
                self.bus.publish(OUTPUT, self.last_output, retain=True)
            if v.get("result") != "proposed":
                self.open.pop(v.get("id"), None)

    def _finish(self, text, results, failed=False):
        self.last_output = {"ts": self.clock(), "text": text, "actions": results, "failed": failed}
        self.bus.publish(OUTPUT, self.last_output, retain=True)
        if failed:
            return self.report("fault", text)           # no cycle_done: the watchdog will notice
        self.cycle_done(text[:200])
        self.report("running", f"last cycle: {len(results)} actions")
