"""Plant tender. After each daily capture it looks at one plant with the measurements and the
annotated photo, and reports the growth stage, a status and at most one suggested action.

It picks a labelled candidate (C1, C2, ...), never a coordinate. A cut is only ever proposed,
as a tend task the governor holds for the owner's approval in every mode. Once approved, motion
goes back to the plant, captures it again and finds the same candidate before anything cuts."""
import json

from .. import topics as T
from ..bus import loads
from ..module import Module
from .llm import reply_topic  # noqa: F401

OUTPUT = f"{T.ROOT}/tender/output"
TOOL = {
    "name": "assess",
    "description": "Report the assessment of this one plant.",
    "input_schema": {"type": "object", "required": ["stage_index", "status", "note", "action", "confidence"], "properties": {
        "stage_index": {"type": "integer", "description": "Index into the milestone list, starting at 0."},
        "status": {"type": "string", "enum": ["ok", "attention", "ready"],
                   "description": "ready = ready to pick. attention = the owner should look, including if it looks dead."},
        "note": {"type": "string", "description": "One or two plain sentences for the owner."},
        "action": {"type": "string", "enum": ["none", "pinch", "remove_leaf", "harvest"]},
        "candidate": {"type": "string", "description": "Label of the candidate to act on, such as C3. Required unless action is none."},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1}}},
}
SYSTEM = """You assess one plant in an indoor greenhouse from one annotated photo and depth measurements.
The plant type was entered by the owner and is certain. Do not second-guess it; if the photo clearly shows a \
different plant, set status to attention and say so.
Choose the growth stage from the given milestone list only. Suggest an action only when clearly useful, and only \
on a candidate label that is drawn on the photo. If unsure, choose action none. You never give coordinates."""


class Tender(Module):
    def setup(self):
        self.plants, self.queue, self.waiting = {}, [], None
        self.bus.subscribe(f"{T.ROOT}/plant/+", lambda t, p: self.plants.__setitem__(t.split("/")[-1], loads(p, {})))
        self.bus.subscribe(f"{T.ROOT}/observation/+", self._on_obs)
        self.bus.subscribe(f"{T.ROOT}/llm/reply/+", self._on_reply)
        self.seen = {}

    def _on_obs(self, topic, payload):
        obs = loads(payload, {})
        pos = obs.get("position")
        if pos and self.seen.get(pos) != obs.get("ts"):          # retained observations arrive again on restart
            self.seen[pos] = obs.get("ts")
            self.queue.append(obs)

    def loop(self):
        now = self.clock()
        if self.waiting and now > self.waiting[2]:
            obs = self.waiting[1]
            self.waiting = None
            self._log(obs["position"], "skipped", "the language model did not answer in time")
        while not self.waiting and self.queue:
            obs = self.queue.pop(0)
            plant = self.plants.get(obs["position"], {})
            if not plant.get("type_confirmed") or plant.get("status") == "dead":
                self._log(obs["position"], "skipped", "no confirmed living plant at this position")
                continue
            if not obs.get("candidates") and "no plant found" in obs.get("quality", []):
                self._mark(obs["position"], "attention")
                self._log(obs["position"], "attention", "the camera found no plant here")
                continue
            job = f"tender-{obs['position']}-{int(now)}"
            facts = {"position": obs["position"], "plant_type": plant.get("common"), "scientific_name": plant.get("scientific"),
                     "milestones": plant.get("milestones"), "current_stage_index": plant.get("stage"),
                     "measurements": {k: obs.get(k) for k in ("height_mm", "width_mm", "canopy_area_cm2", "greenness", "yellow_fraction")},
                     "candidates": [{"label": c["label"], "kind": c["kind"]} for c in obs["candidates"]],
                     "image_quality_notes": obs.get("quality", [])}
            self.waiting = (job, obs, now + self.config["reply_timeout_s"])
            self.bus.publish(T.cmd("llm"), {"id": job, "system": SYSTEM, "tool": TOOL, "images": [obs["annotated"]],
                                            "user": json.dumps(facts, indent=1)})

    def _on_reply(self, topic, payload):
        reply = loads(payload, {})
        if not self.waiting or reply.get("id") != self.waiting[0]:
            return
        obs, self.waiting = self.waiting[1], None
        pos = obs["position"]
        if not reply.get("ok"):
            return self._log(pos, "skipped", f"language model unavailable: {reply.get('error')}")
        a = reply["tool_input"]
        plant = self.plants.get(pos, {})
        stage = a.get("stage_index")
        if isinstance(stage, int) and not isinstance(stage, bool) and 0 <= stage < len(plant.get("milestones", [])):
            self.bus.publish(T.cmd("store"), {"op": "set_stage", "position": pos, "stage": stage, "source": self.name})
        else:
            stage = plant.get("stage", 0)
        status = a.get("status") if a.get("status") in ("ok", "attention", "ready") else "attention"
        note = str(a.get("note") or "")[:300]
        action, label = a.get("action", "none"), a.get("candidate")
        conf = a.get("confidence") if isinstance(a.get("confidence"), (int, float)) else 0.0
        if action in ("pinch", "remove_leaf", "harvest"):
            labels = {c["label"] for c in obs["candidates"]}
            if label not in labels:
                status, note = "attention", f"{note} (suggested {action} on {label!r}, which is not a drawn candidate: not proposed)"
            elif conf < self.config["min_confidence"]:
                note = f"{note} (suggested {action} on {label} at confidence {conf:.2f}: below the threshold, not proposed)"
            elif stage == 0:
                note = f"{note} (suggested {action} on {label}: refused, the plant is still a seedling)"
            else:
                c = next(c for c in obs["candidates"] if c["label"] == label)
                self.request("robot", "tend", f"{action} {label}", pos, why=f"{action} at {label}: {note}"[:300],
                             target={"action": action, "label": label, "kind": c["kind"], "xyz_mm": c["xyz_mm"]})
                status = "attention"
        self._mark(pos, status)
        self._log(pos, status, note, stage=stage, confidence=conf, action=action, candidate=label)
        self.cycle_done(f"{pos}: {status}")

    def _mark(self, pos, status):
        self.bus.publish(T.cmd("store"), {"op": "mark", "position": pos, "status": status, "source": self.name})

    def _log(self, pos, result, note, **extra):
        body = dict(position=pos, result=result, note=note, ts=self.clock(), **extra)
        self.bus.publish(OUTPUT, body, retain=True)
        self.bus.publish(T.log("tender"), body)
