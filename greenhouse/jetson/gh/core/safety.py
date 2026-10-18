"""Safety governor: the only path to an actuator.

Every module, including the interface, sends a request. The governor checks who is
asking, the authority ceiling, the kill switch, hard limits, interlocks and the plant
record, then either drives the actuator, turns the request into a proposal that waits
for the user's approval, or denies it. When anything is unknown it denies."""
import time

from .. import topics as T
from ..bus import loads

UI = "ui"                     # requests typed by the user in the Home Assistant interface
HOUR = 3600
GRANT_S = 15 * 60             # an approved tend task must reach its cut within this
PASS_THROUGH = ("task", "target")


class Governor:
    def __init__(self, bus, manifests, limits, clock=time.time, proposal_ttl_s=24 * HOUR):
        self.bus, self.manifests, self.limits, self.clock = bus, manifests, limits, clock
        self.ttl = proposal_ttl_s
        self.authority, self.kill = "off", False      # deny everything until told otherwise
        self.enabled, self.interlocks, self.plants = {}, {}, {}
        self.usage = {}                               # (actuator, action) -> [(ts, value)]
        self.proposals = {}
        self.grants = {}                              # approved tend task id -> what it allows

    def start(self):
        self.bus.subscribe(T.AUTHORITY_STATE, lambda t, p: setattr(self, "authority", p.strip().lower()))
        self.bus.subscribe(T.KILL_STATE, lambda t, p: setattr(self, "kill", p.strip().upper() == "ON"))
        self.bus.subscribe(f"{T.ROOT}/+/enable", self._on_enable)
        self.bus.subscribe(f"{T.ROOT}/interlock/+", self._on_interlock)
        self.bus.subscribe(f"{T.ROOT}/plant/+", self._on_plant)
        self.bus.subscribe(T.SAFETY_REQUEST, self._on_request)
        self.bus.subscribe(T.SAFETY_REQUEST_UI, self._on_request)
        self.bus.subscribe(f"{T.ROOT}/proposal/+/decision", self._on_decision)
        self._pending()

    def _on_enable(self, topic, payload):
        self.enabled[topic.split("/")[1]] = payload.strip().upper() == "ON"

    def _on_interlock(self, topic, payload):
        self.interlocks[topic.split("/")[-1]] = payload.strip().upper()

    def _on_plant(self, topic, payload):
        self.plants[topic.split("/")[-1]] = loads(payload, {}) or {}

    # ---- checks
    def check(self, req):
        """Return (verdict, reason). verdict is approved, proposed or denied."""
        for key in ("id", "source", "actuator", "action"):
            if not isinstance(req.get(key), str) or not req[key]:
                return "denied", f"request has no {key}"
        src, act, action = req["source"], req["actuator"], req["action"]
        rule = self.limits.get(act, {}).get(action)
        if rule is None:
            return "denied", f"no limit is defined for {act}.{action}"
        layer = None
        if src != UI:
            m = self.manifests.get(src)
            if m is None:
                return "denied", f"unknown source {src}"
            layer = m.layer
            if not self.enabled.get(src, False):
                return "denied", f"{src} is disabled"
            if act not in m.requests:
                return "denied", f"{src} is not allowed to use {act}"
        safe_off = bool(rule.get("safe_off"))
        if layer == "agent" and self.kill:
            return "denied", "kill switch is on"
        if self.authority == "off" and not safe_off:
            return "denied", "authority is off"
        if self.authority == "manual" and src != UI and not safe_off:
            return "denied", "authority is manual"
        if layer == "agent" and self.authority not in ("proposes", "autonomous"):
            return "denied", "agents are not active at this authority level"
        policy = rule.get("approval", "never")
        proposal = src != UI and (policy == "always" or
                                  (policy == "agent" and layer == "agent" and self.authority != "autonomous"))
        # Interlocks describe this moment. A proposal runs later, if at all, and is checked
        # again in full when it is approved, so they are only checked for what runs now.
        if rule.get("needs_grant") and src != UI:
            bad = self._grant_problem(req, rule["needs_grant"])
            if bad:
                return "denied", bad
            proposal = False                          # the owner approved the task this belongs to
        bad = self._limits(req, rule, interlocks=not proposal)
        if bad:
            return "denied", bad
        if proposal:
            return "proposed", "waiting for approval"
        return "approved", "within limits"

    def _grant_problem(self, req, kind):
        """An arm action that only an approved task may cause: one of each, at that plant, in time."""
        grant = self.grants.get(req.get("task") or "")
        if grant is None or grant["kind"] != kind:
            return f"{req['actuator']}.{req['action']} needs an approved {kind} task"
        if self.clock() > grant["expires"]:
            return f"the approved {kind} task has expired"
        if req.get("position") != grant["position"]:
            return f"the approved {kind} task is for {grant['position']}, not {req.get('position')}"
        if grant["left"].get(req["action"], 0) <= 0:
            return f"{req['action']} was already done for this task"
        return None

    def _limits(self, req, rule, interlocks=True):
        value = req.get("value")
        if "min" in rule or "max" in rule or "max_per_hour" in rule:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return "value must be a number"
            if value < rule.get("min", float("-inf")) or value > rule.get("max", float("inf")):
                return f"value {value} is outside {rule.get('min')} to {rule.get('max')}"
        if "max_per_hour" in rule:
            now = self.clock()
            used = sum(v for ts, v in self.usage.get((req["actuator"], req["action"]), []) if now - ts < HOUR)
            if used + value > rule["max_per_hour"]:
                return f"hourly limit reached ({used} of {rule['max_per_hour']} used)"
        for lock in rule.get("interlocks", []) if interlocks else []:
            if self.interlocks.get(lock) != "OK":
                return f"interlock {lock} is not OK"
        if rule.get("needs_plant"):
            plant = self.plants.get(req.get("position") or "")
            if not plant or not plant.get("type_confirmed"):
                return "no confirmed plant type at this position"
            if plant.get("status") == "dead":
                return "plant at this position is marked dead"
        return None

    # ---- flow
    def _on_request(self, topic, payload):
        req = loads(payload)
        if not isinstance(req, dict):
            return
        # Who is asking is decided by the topic, which the broker ACL protects,
        # never by what the message claims.
        if topic == T.SAFETY_REQUEST_UI:
            req["source"] = UI
        elif req.get("source") == UI:
            return self._verdict(req, "denied", "interface requests must use the interface topic")
        verdict, reason = self.check(req)
        if verdict == "approved":
            self._execute(req)
        elif verdict == "proposed":
            self.proposals[req["id"]] = dict(req, created=self.clock(), reason_given=str(req.get("why", ""))[:300])
            self.bus.publish(T.proposal(req["id"]), self.proposals[req["id"]], retain=True)
            self._pending()
        self._verdict(req, verdict, reason)

    def _on_decision(self, topic, payload):
        pid = topic.split("/")[-2]
        req = self.proposals.pop(pid, None)
        if req is None:
            return
        self.bus.publish(T.proposal(pid), "", retain=True)
        self._pending()
        if payload.strip().lower() != "approve":
            return self._verdict(req, "denied", "rejected by user")
        # Conditions may have changed since the proposal was made. Check again as the user.
        verdict, reason = self.check(dict(req, source=UI))
        if verdict == "approved":
            self._execute(req)
            return self._verdict(req, "approved", "approved by user")
        self._verdict(req, "denied", reason)

    def _execute(self, req):
        value = req.get("value")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            self.usage.setdefault((req["actuator"], req["action"]), []).append((self.clock(), value))
        rule = self.limits.get(req["actuator"], {}).get(req["action"], {})
        if rule.get("grants"):                        # an approved task: allow its arm actions, once each
            self.grants[req["id"]] = {"kind": req["action"], "position": req.get("position"),
                                      "expires": self.clock() + GRANT_S, "left": dict(rule["grants"])}
        grant = self.grants.get(req.get("task") or "")
        if rule.get("needs_grant") and grant:
            grant["left"][req["action"]] -= 1
        body = {"id": req["id"], "action": req["action"], "value": value, "position": req.get("position")}
        body.update({k: req[k] for k in PASS_THROUGH if k in req})
        self.bus.publish(T.actuator_set(req["actuator"]), body)

    def _verdict(self, req, verdict, reason):
        rid = str(req.get("id", "unknown"))
        body = {"id": rid, "result": verdict, "reason": reason, "source": req.get("source"),
                "actuator": req.get("actuator"), "action": req.get("action"),
                "value": req.get("value"), "position": req.get("position"), "ts": self.clock()}
        self.bus.publish(T.verdict(rid), body)
        self.bus.publish(T.log("decision"), body)

    def _pending(self):
        self.bus.publish(T.SAFETY_PENDING, str(len(self.proposals)), retain=True)
        self.bus.publish(T.PROPOSALS, sorted(self.proposals.values(), key=lambda r: r["created"]), retain=True)

    def tick(self):
        now = self.clock()
        for pid in [p for p, r in self.proposals.items() if now - r["created"] > self.ttl]:
            req = self.proposals.pop(pid)
            self.bus.publish(T.proposal(pid), "", retain=True)
            self._verdict(req, "denied", "proposal expired")
        for key in list(self.usage):
            self.usage[key] = [(ts, v) for ts, v in self.usage[key] if now - ts < HOUR]
        self.grants = {k: g for k, g in self.grants.items() if now <= g["expires"]}
        self._pending()
