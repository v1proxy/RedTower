#!/usr/bin/env python3
"""The plant tender: Claude looks at one plant through the D405 and decides what to do.

One plant, one visit. The gantry parks the arm over a pot, the D405 takes an aligned
RGBD capture, plant_perception turns that into millimetres and a handful of labelled
candidate points, and this module asks Claude three things in one call:

    what is this plant, how is it doing, and what should the arm do about it

Claude answers by calling tools. It may only pick an action from a fixed list and may
only aim at a candidate label that perception actually produced, so the worst a bad
answer can do is send the arm to a real leaf for no good reason, never to a coordinate
that does not exist.

Destructive actions (pinching tips, cutting leaves) are proposals by default. They go
to Home Assistant and wait for you. Flip allow_cutting in the config once you trust it.

    pip install anthropic opencv-python numpy paho-mqtt
"""
import base64
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic
import cv2
import numpy as np

CFG = json.loads(Path("/opt/greenhouse/gardener.json").read_text())
TCFG = CFG.get("tender", {})
MODEL = TCFG.get("model", CFG.get("model", "claude-sonnet-5"))
JOURNAL = Path(TCFG.get("journal", "/opt/greenhouse/tender_journal.jsonl"))
RECORDS = Path(TCFG.get("records", "/opt/greenhouse/plant_records.json"))
ALLOW_CUTTING = bool(TCFG.get("allow_cutting", False))
MIN_CUT_CONFIDENCE = float(TCFG.get("min_cut_confidence", 0.7))

ACTIONS = ["none", "closer_look", "pinch_tip", "harvest_leaf", "remove_dead_leaf",
           "water_more", "water_less", "flag_human"]
DESTRUCTIVE = {"pinch_tip", "harvest_leaf", "remove_dead_leaf"}

SYSTEM = """You tend one plant at a time in a 27-plant indoor cabinet: 7 compact peppers on
Tier A, 10 herbs each on Tiers B and C, in soil pots under dimmable LED bars.

You are looking through a RealSense D405 on the arm's flange, about 200 mm above the pot.
The image you receive is annotated: every candidate point the vision system found is circled
and labelled C1, C2 and so on, with its height above the soil in millimetres. Those labels are
the only places the arm can go. Never invent a coordinate or refer to a label that is not drawn.

Work in this order, as three tool calls:
1. identify_plant: say what you think it is from the leaf shape, margin, venation and growth
   habit, and how confident you are. If the record already names a species, you are confirming
   or contradicting it, and contradicting is useful information.
2. assess_health: a 0-100 score and the specific issues you can see. Judge from the image, not
   from the numbers alone: leggy growth, chlorosis between veins, crisped margins, pest damage,
   soil surface too wet or too dry, crowding.
3. choose_action: exactly one action, with a one-line reason a person would find useful.

How to choose:
- Most visits should be "none". A plant that is fine needs nothing.
- pinch_tip on a herb that is getting tall and sparse: taking the top growth point makes it bush
  out. Only on established plants, never on seedlings, and only at a tip candidate.
- harvest_leaf when the plant is big enough that removing one mature leaf costs it nothing, and
  the leaf is one you would actually want in a kitchen. Prefer outer, larger, older leaves.
- remove_dead_leaf for clearly dead or diseased tissue, which is worth taking early because it
  spreads.
- water_more or water_less only when what you see disagrees with the probe: a wilting plant on a
  wet probe usually means root trouble or a broken emitter, which is a flag_human, not more water.
- closer_look when the image is ambiguous and a second capture from nearer would settle it.
- flag_human for anything structural: pests, disease you cannot identify, a pot that has dried
  to shrinkage, a plant outgrowing its tier.

Be specific and brief. "C2, lowest outer leaf, yellow from the margin inward" beats "unhealthy leaf"."""

TOOLS = [
    {"name": "identify_plant",
     "description": "What this plant appears to be, from what you can see.",
     "input_schema": {"type": "object", "properties": {
         "species_guess": {"type": "string"},
         "common_name": {"type": "string"},
         "growth_stage": {"type": "string", "enum": ["seedling", "juvenile", "established", "flowering", "fruiting", "spent"]},
         "confidence": {"type": "number"},
         "matches_record": {"type": "boolean"},
         "notes": {"type": "string"}},
         "required": ["species_guess", "growth_stage", "confidence"]}},
    {"name": "assess_health",
     "description": "Visible condition of the plant.",
     "input_schema": {"type": "object", "properties": {
         "score": {"type": "integer", "description": "0 dying, 100 thriving"},
         "issues": {"type": "array", "items": {"type": "string"}},
         "reasoning": {"type": "string"}},
         "required": ["score", "reasoning"]}},
    {"name": "choose_action",
     "description": "One action for the arm or the watering system, aimed at a candidate label.",
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ACTIONS},
         "candidate": {"type": "string", "description": "C1, C2, ... required for arm actions"},
         "reason": {"type": "string"},
         "urgency": {"type": "string", "enum": ["now", "this_week", "whenever"]}},
         "required": ["action", "reason"]}},
]


def _b64_png(img: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("could not encode the annotated image")
    return base64.standard_b64encode(buf.tobytes()).decode()


def load_records() -> dict:
    return json.loads(RECORDS.read_text()) if RECORDS.exists() else {}


def save_record(pid: str, patch: dict):
    recs = load_records()
    rec = recs.get(pid, {})
    rec.update(patch)
    rec["updated"] = datetime.now().astimezone().isoformat(timespec="minutes")
    recs[pid] = rec
    RECORDS.write_text(json.dumps(recs, indent=1))


def history(pid: str, limit: int = 6) -> list:
    if not JOURNAL.exists():
        return []
    out = []
    for line in JOURNAL.read_text().splitlines()[-500:]:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("plant_id") == pid:
            out.append({k: row.get(k) for k in ("ts", "action", "reason", "executed", "health")})
    return out[-limit:]


def journal(**row):
    row["ts"] = datetime.now().astimezone().isoformat(timespec="seconds")
    with JOURNAL.open("a") as f:
        f.write(json.dumps(row) + "\n")


def consider(geo, annotated_bgr: np.ndarray, soil_moisture_pct: Optional[float] = None,
             llm: Optional[anthropic.Anthropic] = None) -> dict:
    """Ask Claude about one plant. Returns a decision dict; performs no motion."""
    llm = llm or anthropic.Anthropic(api_key=CFG["anthropic_api_key"])
    recs = load_records()
    rec = recs.get(geo.plant_id, {})

    brief = {
        "plant_id": geo.plant_id,
        "record": {k: rec.get(k) for k in ("species", "common_name", "stage", "planted", "last_harvest")},
        "soil_moisture_pct": soil_moisture_pct,
        "measurements": geo.brief(),
        "recent_visits": history(geo.plant_id),
    }

    messages = [{"role": "user", "content": [
        {"type": "text", "text": "Here is the annotated close-up and the measured geometry.\n\n"
                                 + json.dumps(brief, indent=1, default=str)},
        {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                     "data": _b64_png(annotated_bgr)}},
    ]}]

    decision = {"plant_id": geo.plant_id, "identify": None, "health": None, "action": None}
    for _ in range(3):
        reply = llm.messages.create(model=MODEL, max_tokens=1200, system=SYSTEM,
                                    tools=TOOLS, messages=messages)
        calls = [b for b in reply.content if b.type == "tool_use"]
        if not calls:
            break
        messages.append({"role": "assistant", "content": reply.content})
        results = []
        for c in calls:
            if c.name == "identify_plant":
                decision["identify"] = c.input
            elif c.name == "assess_health":
                decision["health"] = c.input
            elif c.name == "choose_action":
                decision["action"] = c.input
            results.append({"type": "tool_result", "tool_use_id": c.id, "content": "recorded"})
        messages.append({"role": "user", "content": results})
        if decision["action"]:
            break

    return _validate(decision, geo)


def _validate(decision: dict, geo) -> dict:
    """Clamp the decision to what the hardware and the rules allow."""
    act = decision.get("action") or {"action": "none", "reason": "no action proposed"}
    name = act.get("action", "none")
    label = act.get("candidate")
    cand = next((c for c in geo.candidates if c.label == label), None)

    verdict = {"execute": False, "propose": False, "blocked": None}

    if name not in ACTIONS:
        verdict["blocked"] = f"unknown action {name}"
        name = "none"
    elif name in DESTRUCTIVE or name == "closer_look":
        if cand is None:
            # A label that perception never produced means the model and the image disagree.
            # That is worth a person's eyes, so it has to actually reach one rather than
            # quietly becoming a no-op.
            verdict["blocked"] = f"action {name} named candidate {label!r}, which perception did not produce"
            name = "flag_human"
            verdict["execute"] = True
        elif name in DESTRUCTIVE and cand.confidence < MIN_CUT_CONFIDENCE:
            verdict["blocked"] = (f"candidate {label} confidence {cand.confidence:.2f} is below the "
                                  f"{MIN_CUT_CONFIDENCE} needed to cut")
            verdict["propose"] = True
        elif name in DESTRUCTIVE and not ALLOW_CUTTING:
            verdict["blocked"] = "cutting is disabled in the config; sending this as a proposal"
            verdict["propose"] = True
        else:
            verdict["execute"] = True
    elif name in ("water_more", "water_less", "flag_human", "none"):
        verdict["execute"] = name != "none"

    stage = (decision.get("identify") or {}).get("growth_stage")
    if name in DESTRUCTIVE and stage == "seedling":
        verdict.update({"execute": False, "propose": True,
                        "blocked": "the plant reads as a seedling, so nothing gets cut"})

    decision["action"] = {**act, "action": name}
    decision["verdict"] = verdict
    decision["target"] = None if cand is None else {
        "label": cand.label, "kind": cand.kind, "point_m": cand.point_m,
        "normal": cand.normal, "approach_mm": TCFG.get("approach_mm", 40)}
    return decision


def camera_to_arm(point_m, normal, T_flange_cam: np.ndarray, T_base_flange: np.ndarray):
    """Camera-frame point and normal to base-frame pose for the arm.

    T_flange_cam comes from hand-eye calibration (handeye_calibrate.py).
    T_base_flange is the arm's current forward kinematics, from its own controller.
    Returns (position_mm, approach_unit_vector) in the arm's base frame.
    """
    p_cam = np.array([point_m[0], point_m[1], point_m[2], 1.0])
    p_base = T_base_flange @ T_flange_cam @ p_cam
    n_cam = np.array([normal[0], normal[1], normal[2], 0.0])
    n_base = (T_base_flange @ T_flange_cam @ n_cam)[:3]
    n_base /= np.linalg.norm(n_base) + 1e-9
    return p_base[:3] * 1000.0, n_base


def publish(client, decision: dict):
    """Send the decision to Home Assistant: a sensor line, and a proposal if one is waiting."""
    pid = decision["plant_id"]
    act = decision["action"]
    client.publish(f"greenhouse/tender/{pid}", json.dumps({
        "species": (decision.get("identify") or {}).get("common_name"),
        "stage": (decision.get("identify") or {}).get("growth_stage"),
        "health": (decision.get("health") or {}).get("score"),
        "action": act.get("action"), "reason": act.get("reason"),
        "ts": datetime.now().astimezone().isoformat(timespec="minutes")}), retain=True)
    if decision["verdict"]["propose"]:
        client.publish("greenhouse/tender/proposal", json.dumps({
            "plant_id": pid, "action": act.get("action"), "candidate": act.get("candidate"),
            "reason": act.get("reason"), "blocked": decision["verdict"]["blocked"],
            "expires": time.time() + 86400}), retain=False)
    if act.get("action") == "flag_human":
        client.publish("greenhouse/tender/attention", json.dumps({
            "plant_id": pid, "reason": act.get("reason"),
            "blocked": decision["verdict"]["blocked"],
            "issues": (decision.get("health") or {}).get("issues"),
            "image": f"{pid}_annotated.png"}), retain=False)


def record_visit(decision: dict):
    ident = decision.get("identify") or {}
    health = decision.get("health") or {}
    act = decision.get("action") or {}
    journal(plant_id=decision["plant_id"], action=act.get("action"), reason=act.get("reason"),
            candidate=act.get("candidate"), executed=decision["verdict"]["execute"],
            blocked=decision["verdict"]["blocked"], health=health.get("score"),
            issues=health.get("issues"), species=ident.get("species_guess"),
            stage=ident.get("growth_stage"), confidence=ident.get("confidence"))
    patch = {"last_seen": datetime.now().astimezone().isoformat(timespec="minutes"),
             "health": health.get("score")}
    if ident.get("confidence", 0) >= 0.6:
        patch.update({"species": ident.get("species_guess"),
                      "common_name": ident.get("common_name"),
                      "stage": ident.get("growth_stage")})
    save_record(decision["plant_id"], patch)
