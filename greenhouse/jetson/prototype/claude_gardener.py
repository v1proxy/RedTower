#!/usr/bin/env python3
"""Claude tends Maag.

Once an hour this wakes up, gathers the same variable set the Sol biodome steers on
(air temperature, humidity, VPD, leaf-to-air delta, soil moisture, CO2, plus our vision
metrics and reservoir state), asks Claude what to do, and executes whatever it asks for
through a small set of bounded tools. Between those hours rule_loop.py watches the same
sensors every 5 minutes for free and wakes this process early if something leaves its band.

What Claude may change: photoperiod and light intensity per tier, watering runs, the
climate setpoints, circulation duty, the humidifier, and robot tasks. Nothing else.

What Claude can never do: touch the safety chain, exceed the bounds in LIMITS below,
water a locked-out zone, or move the arm while a door is open. Those live in the ESPHome
node firmware and the robot supervisor, which refuse regardless of what is asked.

Kill switch: input_boolean.gh_claude_autonomy in Home Assistant. Off means this process
still thinks and journals, but executes nothing.

Cost shape (see greenhouse/opex_model.py). Three things keep the bill down:
  1. The static head, system prompt + tool schemas + the plant roster, is one cached
     prefix with a 1 hour TTL. It is byte-identical every cycle, so after the first
     call of each hour it bills at the cache read rate instead of the input rate.
  2. The journal sent back is 6 hours and 12 entries, digested, not 24 hours of raw rows.
     The full history stays on disk; only the recent part needs to be in the prompt.
  3. The routine loop runs on Haiku. The per-plant vision pass in plant_tender.py keeps
     Sonnet, because judging a leaf from a photo is the part that needs the better model.

pip install anthropic requests paho-mqtt
"""
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import anthropic
import paho.mqtt.client as mqtt
import requests

CFG = json.loads(Path("/opt/greenhouse/gardener.json").read_text())
HA = CFG["ha"]["url"].rstrip("/")
HEAD = {"Authorization": f"Bearer {CFG['ha']['token']}", "Content-Type": "application/json"}
JOURNAL = Path(CFG.get("journal", "/opt/greenhouse/journal.jsonl"))
ESCALATIONS = Path(CFG.get("escalations", "/opt/greenhouse/escalations.jsonl"))
MODEL = CFG.get("model", "claude-haiku-5-5")
JOURNAL_HOURS = CFG.get("journal_hours", 6)
JOURNAL_LIMIT = CFG.get("journal_limit", 12)
TIERS = ["a", "b", "c"]
ZONE = {"a": 1, "b": 2, "c": 3}

# Hard bounds. Claude's requests are clamped to these, and anything outside is refused
# and reported back to it, so a bad number becomes a conversation rather than a flood.
LIMITS = {
    "on_hour": (0, 23),
    "photoperiod_h": (10, 18),
    "intensity_pct": (20, 100),
    "water_seconds": (10, 180),
    "water_runs_per_zone_per_day": 3,
    "temp_setpoint_c": (18.0, 30.0),
    "rh_limit_pct": (55, 85),
    "exhaust_min_pct": (15, 60),
    "circulation_pct": (0, 100),
    "humidifier_minutes": (1, 30),
}


# ---------------------------------------------------------------- Home Assistant

def ha_get(entity):
    r = requests.get(f"{HA}/api/states/{entity}", headers=HEAD, timeout=10)
    return r.json() if r.ok else None


def ha_state(entity, cast=float, default=None):
    s = ha_get(entity)
    if not s or s["state"] in ("unknown", "unavailable", ""):
        return default
    try:
        return cast(s["state"])
    except (TypeError, ValueError):
        return s["state"]


def ha_call(domain, service, data):
    r = requests.post(f"{HA}/api/services/{domain}/{service}", headers=HEAD, json=data, timeout=30)
    return r.ok, (r.text[:200] if not r.ok else "ok")


def autonomy_on():
    return ha_state("input_boolean.gh_claude_autonomy", str, "off") == "on"


# ---------------------------------------------------------------- snapshot

def tier_block(t):
    p = f"sensor.greenhouse_tier_{t}_"
    return {
        "air_temp_c": ha_state(p + "air_temperature"),
        "humidity_pct": ha_state(p + "air_humidity"),
        "vpd_kpa": ha_state(p + "vpd"),
        "leaf_vpd_kpa": ha_state(p + "leaf_vpd"),
        "leaf_air_delta_c": ha_state(p + "leaf_to_air_delta"),
        "median_soil_pct": ha_state(p + "median_moisture"),
        "driest_plant_pct": ha_state(p + "driest_plant_moisture"),
        "light_on": ha_state(f"light.greenhouse_tier_{t}_grow_light", str, "unknown"),
        "light_level_raw": ha_state(p + "light_level_clear"),
        "photoperiod_h": ha_state(f"number.greenhouse_tier_{t}_photoperiod"),
        "on_hour": ha_state(f"number.greenhouse_tier_{t}_lights_on_hour"),
        "intensity_pct": ha_state(f"number.greenhouse_tier_{t}_light_intensity"),
        "circulation_pct": ha_state(f"number.greenhouse_tier_{t}_circulation_fan_duty"),
    }


def snapshot():
    vision = {}
    for plant in CFG["plants"]:
        pid = plant["id"]
        vision[pid] = {
            "canopy_area": ha_state(f"sensor.greenhouse_vision_{pid}_canopy_area"),
            "greenness": ha_state(f"sensor.greenhouse_vision_{pid}_greenness"),
            "yellowing": ha_state(f"sensor.greenhouse_vision_{pid}_yellowing"),
            "stress": ha_state(f"sensor.greenhouse_vision_{pid}_stress"),
        }
    return {
        "now": datetime.now().astimezone().isoformat(timespec="minutes"),
        "tiers": {t: tier_block(t) for t in TIERS},
        "co2_ppm": ha_state("sensor.greenhouse_tier_c_co2"),
        "exhaust_setpoints": {
            "temp_setpoint_c": ha_state("number.greenhouse_tier_c_temperature_setpoint"),
            "rh_limit_pct": ha_state("number.greenhouse_tier_c_humidity_limit"),
            "exhaust_min_pct": ha_state("number.greenhouse_tier_c_exhaust_minimum_duty"),
        },
        "water": {
            "reservoir_pct": ha_state("sensor.greenhouse_utility_reservoir_level"),
            "reservoir_litres": ha_state("sensor.greenhouse_utility_reservoir_volume"),
            "water_temp_c": ha_state("sensor.greenhouse_utility_water_temperature"),
            "delivered_today_ml": ha_state("sensor.greenhouse_utility_water_delivered_today"),
            "leak": ha_state("binary_sensor.greenhouse_utility_leak_detected", str, "unknown"),
            "lockout": ha_state("binary_sensor.greenhouse_utility_leak_lockout", str, "unknown"),
        },
        "doors_open": ha_state("binary_sensor.greenhouse_utility_doors", str, "unknown"),
        "robot_busy": ha_state("binary_sensor.greenhouse_robot_busy", str, "unknown"),
        "power_w": ha_state("sensor.greenhouse_utility_cabinet_power"),
        "vision": vision,
        "recent_actions": recent_journal(),
        "escalations": drain_escalations(),
    }


def recent_journal(hours=None, limit=None):
    """The last few hours, digested.

    The old version sent 24 hours of raw rows, 2,400 tokens, every single cycle: the
    largest line item in the whole cabinet, electricity included. Nothing in a 20 hour
    old watering record changes what to do now, and the verbose args and result strings
    were being re-read ~50 times a day each. One compact line per action says as much.
    """
    hours = JOURNAL_HOURS if hours is None else hours
    limit = JOURNAL_LIMIT if limit is None else limit
    if not JOURNAL.exists():
        return []
    cutoff = datetime.now().astimezone() - timedelta(hours=hours)
    out = []
    for line in JOURNAL.read_text().splitlines()[-400:]:
        try:
            row = json.loads(line)
            if datetime.fromisoformat(row["ts"]) < cutoff:
                continue
        except (ValueError, KeyError):
            continue
        out.append(digest(row))
    return out[-limit:]


def digest(row):
    """One action as one short string: 14:30 water_zone b 45s -> ok."""
    args = row.get("args") or {}
    bits = [str(args[k]) for k in ("tier", "task", "target", "urgency") if args.get(k)]
    for k, suffix in (("seconds", "s"), ("minutes", "min"), ("intensity_pct", "%"),
                      ("photoperiod_h", "h"), ("duty_pct", "%")):
        if args.get(k) is not None:
            bits.append(f"{args[k]}{suffix}")
    ok = str(row.get("result", "")).startswith("ok")
    when = str(row.get("ts", ""))[11:16]
    return f"{when} {row.get('tool', '?')} {' '.join(bits)} -> {'ok' if ok else 'FAILED'}".strip()


def journal(**row):
    row["ts"] = datetime.now().astimezone().isoformat(timespec="seconds")
    with JOURNAL.open("a") as f:
        f.write(json.dumps(row) + "\n")


# ---------------------------------------------------------------- tools

TOOLS = [
    {"name": "set_light", "description": "Set the photoperiod window and intensity for one tier.",
     "input_schema": {"type": "object", "properties": {
         "tier": {"type": "string", "enum": TIERS},
         "on_hour": {"type": "integer"}, "photoperiod_h": {"type": "integer"},
         "intensity_pct": {"type": "integer"},
         "reason": {"type": "string"}},
         "required": ["tier", "reason"]}},
    {"name": "water_zone", "description": "Run one tier's drip zone for a number of seconds.",
     "input_schema": {"type": "object", "properties": {
         "tier": {"type": "string", "enum": TIERS},
         "seconds": {"type": "integer"}, "reason": {"type": "string"}},
         "required": ["tier", "seconds", "reason"]}},
    {"name": "set_climate", "description": "Set the exhaust thermostat setpoints (Tier C node governs the cabinet).",
     "input_schema": {"type": "object", "properties": {
         "temp_setpoint_c": {"type": "number"}, "rh_limit_pct": {"type": "integer"},
         "exhaust_min_pct": {"type": "integer"}, "reason": {"type": "string"}},
         "required": ["reason"]}},
    {"name": "set_circulation", "description": "Set one tier's circulation fan duty.",
     "input_schema": {"type": "object", "properties": {
         "tier": {"type": "string", "enum": TIERS},
         "duty_pct": {"type": "integer"}, "reason": {"type": "string"}},
         "required": ["tier", "duty_pct", "reason"]}},
    {"name": "run_humidifier", "description": "Run the humidifier for a few minutes to bring VPD down.",
     "input_schema": {"type": "object", "properties": {
         "minutes": {"type": "integer"}, "reason": {"type": "string"}},
         "required": ["minutes", "reason"]}},
    {"name": "robot_task", "description": "Queue a robot task: inspect a tier, or prune/harvest one plant.",
     "input_schema": {"type": "object", "properties": {
         "task": {"type": "string", "enum": ["inspect", "prune", "harvest", "home"]},
         "target": {"type": "string"}, "reason": {"type": "string"}},
         "required": ["task", "reason"]}},
    {"name": "note", "description": "Write an observation or a plan to the journal without changing anything.",
     "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    {"name": "ask_human", "description": "Flag something a person must handle: refill, disease, hardware fault.",
     "input_schema": {"type": "object", "properties": {
         "urgency": {"type": "string", "enum": ["fyi", "soon", "now"]},
         "text": {"type": "string"}}, "required": ["urgency", "text"]}},
]

SYSTEM = """You tend a 27-plant indoor greenhouse: 7 compact peppers on Tier A, 10 herbs on Tier B,
10 herbs on Tier C, all in soil pots under dimmable LED bars with per-pot capacitive moisture probes,
per-tier air and canopy sensors, CO2 at the top, and a robot arm on a gantry.

You run once an hour, and out of turn whenever the local rule loop escalates something. A
cheap rule loop checks the same sensors every 5 minutes between your runs, so you are not the
thing standing between a plant and a problem: if something had crossed a hard band you would
have been woken already. Most runs should therefore change nothing: say so with a short note
and stop. Act when a number is outside the band for that crop and growth stage, and prefer the
smallest correction that will work.

If "escalations" is non-empty, those are what the rule loop saw since your last run. Deal with
them first and say what you did about each.

Bands worth holding, unless the plants tell you otherwise:
- Herbs: VPD 0.8-1.2 kPa, soil median 40-60 %, DLI about 17 mol/m2/day (16 h at the set intensity).
- Peppers: VPD 0.8-1.4 kPa, soil median 35-55 %, DLI about 29 mol/m2/day, more light while fruiting.
- Leaf-to-air delta above +1.5 C for an hour means the canopy is closing stomata: check water first.
- CO2 below about 450 ppm with lights on means the exhaust is running harder than it needs to.

Watering rules you must respect: the median probe drives the decision, never a single dry outlier.
A dry outlier plus a normal median means a blocked emitter, which is an ask_human, not more water.
Never water a tier twice within an hour, and never when the reservoir is under 15 % or a leak is latched.

Robot tasks: inspect is cheap, use it when vision flags a plant or you want a closer look before
deciding. Harvest and prune are physical and irreversible, so explain the reason and prefer asking
first when the plant is young or the call is marginal.

Every tool call needs a one-line reason written for the owner, not for you. Be concise and specific:
"Tier B median 34 %, below the 40 % floor, 60 s" beats "watering because dry"."""


# The plant roster never changes between cycles, so it does not belong in the snapshot:
# it belongs in the cached prefix with the system prompt and the tool schemas. Those three
# together are ~2,500 tokens that are byte-identical every call.
ROSTER = "The pots, fixed for this planting:\n" + "\n".join(
    f"{p['label']} tier {p['tier']} {p['species']} stage {p['stage']} planted {p['planted']}"
    for p in CFG["plants"])

# cache_control goes on the LAST block of the prefix, and the prefix is tools -> system ->
# messages, so this one breakpoint caches the tool schemas and both system blocks. 1h TTL
# because the loop is hourly; a 5 minute TTL would expire before every single call and we
# would pay the write premium every time for nothing.
SYSTEM_BLOCKS = [
    {"type": "text", "text": SYSTEM},
    {"type": "text", "text": ROSTER,
     "cache_control": {"type": "ephemeral", "ttl": "1h"}},
]


def drain_escalations():
    """Whatever rule_loop.py flagged since the last cycle. Read once, then cleared."""
    if not ESCALATIONS.exists():
        return []
    rows = []
    for line in ESCALATIONS.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    ESCALATIONS.write_text("")
    return rows[-20:]


def clamp(name, value, default=None):
    lo, hi = LIMITS[name]
    if value is None:
        return default
    return max(lo, min(hi, value))


def waters_today(tier):
    """Counted off the raw journal on disk, never off the digest sent to the model."""
    if not JOURNAL.exists():
        return 0
    cutoff = datetime.now().astimezone() - timedelta(hours=24)
    n = 0
    for line in JOURNAL.read_text().splitlines()[-400:]:
        try:
            row = json.loads(line)
            if (datetime.fromisoformat(row["ts"]) >= cutoff
                    and row.get("tool") == "water_zone"
                    and (row.get("args") or {}).get("tier") == tier
                    and str(row.get("result", "")).startswith("ok")):
                n += 1
        except (ValueError, KeyError):
            continue
    return n


def execute(name, args, dry_run):
    """Apply one tool call. Returns a short result string that goes back to Claude."""
    if dry_run:
        return "not executed: autonomy switch is off"
    try:
        if name == "note":
            return "ok, noted"

        if name == "ask_human":
            ok, msg = ha_call("notify", CFG["ha"].get("notify", "notify"),
                              {"title": f"Greenhouse ({args['urgency']})", "message": args["text"]})
            return "ok, owner notified" if ok else f"notify failed: {msg}"

        if name == "set_light":
            t = args["tier"]
            for key, entity in (("on_hour", "lights_on_hour"), ("photoperiod_h", "photoperiod"),
                                ("intensity_pct", "light_intensity")):
                if args.get(key) is None:
                    continue
                val = clamp(key, args[key])
                ok, msg = ha_call("number", "set_value",
                                  {"entity_id": f"number.greenhouse_tier_{t}_{entity}", "value": val})
                if not ok:
                    return f"failed on {key}: {msg}"
            return "ok, light settings applied"

        if name == "water_zone":
            t = args["tier"]
            if waters_today(t) >= LIMITS["water_runs_per_zone_per_day"]:
                return f"refused: tier {t} already watered {LIMITS['water_runs_per_zone_per_day']} times today"
            res = ha_state("sensor.greenhouse_utility_reservoir_level", float, 0) or 0
            if res < 15:
                return f"refused: reservoir at {res:.0f} %"
            if ha_state("binary_sensor.greenhouse_utility_leak_lockout", str, "off") == "on":
                return "refused: leak lockout is latched"
            secs = clamp("water_seconds", args["seconds"], 60)
            ok, msg = ha_call("esphome", "greenhouse_utility_water_zone",
                              {"zone": ZONE[t], "seconds": int(secs)})
            return f"ok, zone {t} watered {int(secs)} s" if ok else f"failed: {msg}"

        if name == "set_climate":
            pairs = (("temp_setpoint_c", "temperature_setpoint"), ("rh_limit_pct", "humidity_limit"),
                     ("exhaust_min_pct", "exhaust_minimum_duty"))
            for key, entity in pairs:
                if args.get(key) is None:
                    continue
                ok, msg = ha_call("number", "set_value",
                                  {"entity_id": f"number.greenhouse_tier_c_{entity}",
                                   "value": clamp(key, args[key])})
                if not ok:
                    return f"failed on {key}: {msg}"
            return "ok, climate setpoints applied"

        if name == "set_circulation":
            ok, msg = ha_call("number", "set_value",
                              {"entity_id": f"number.greenhouse_tier_{args['tier']}_circulation_fan_duty",
                               "value": clamp("circulation_pct", args["duty_pct"], 40)})
            return "ok, fan duty applied" if ok else f"failed: {msg}"

        if name == "run_humidifier":
            mins = clamp("humidifier_minutes", args["minutes"], 10)
            ok, msg = ha_call("switch", "turn_on", {"entity_id": "switch.greenhouse_utility_humidifier"})
            if not ok:
                return f"failed: {msg}"
            ha_call("script", "turn_on", {"entity_id": "script.gh_humidifier_off_after",
                                          "variables": {"minutes": int(mins)}})
            return f"ok, humidifier on for {int(mins)} min"

        if name == "robot_task":
            if ha_state("binary_sensor.greenhouse_robot_clear_to_run", str, "off") != "on":
                return "refused: robot interlocks not clear (door open, watering, or leak)"
            ok, msg = ha_call("script", "gh_robot_task",
                              {"task": args["task"], "target": args.get("target", "")})
            return f"ok, {args['task']} queued" if ok else f"failed: {msg}"

        return f"unknown tool {name}"
    except Exception as exc:                       # never let one bad call kill the loop
        return f"error: {exc}"


# ---------------------------------------------------------------- the loop

USAGE = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}


def meter(usage):
    """Running token tally, so the cost model can be checked against reality.

    If cache_read stays 0 after the first call of an hour, the prefix is not being hit:
    something upstream of the breakpoint is changing between calls. That is the single
    thing worth watching after this change.
    """
    USAGE["in"] += usage.input_tokens
    USAGE["out"] += usage.output_tokens
    USAGE["cache_read"] += getattr(usage, "cache_read_input_tokens", 0) or 0
    USAGE["cache_write"] += getattr(usage, "cache_creation_input_tokens", 0) or 0


def usage_cost():
    """USD so far this process, at the Oct 2026 Haiku 5.5 rates."""
    r = CFG.get("rates", {"in": 0.10, "out": 0.50, "cache_read": 0.01, "cache_write": 0.20})
    return (USAGE["in"] * r["in"] + USAGE["out"] * r["out"]
            + USAGE["cache_read"] * r["cache_read"]
            + USAGE["cache_write"] * r["cache_write"]) / 1e6


def publish_status(client, text, actions):
    client.publish("greenhouse/claude/last", json.dumps(
        {"summary": text[:250], "actions": actions,
         "tokens": USAGE["in"] + USAGE["out"] + USAGE["cache_read"],
         "cost_usd": round(usage_cost(), 4),
         "cache_hit_pct": round(100 * USAGE["cache_read"]
                                / max(1, USAGE["cache_read"] + USAGE["in"]), 1),
         "ts": datetime.now().astimezone().isoformat(timespec="minutes")}), retain=True)


def discovery(client):
    dev = {"identifiers": ["greenhouse_claude"], "name": "Greenhouse Gardener",
           "manufacturer": "RedTower", "model": "Claude tending loop"}
    client.publish("homeassistant/sensor/gh_claude/summary/config", json.dumps({
        "name": "Claude last decision", "unique_id": "gh_claude_summary",
        "object_id": "greenhouse_claude_last_decision", "state_topic": "greenhouse/claude/last",
        "value_template": "{{ value_json.summary }}", "icon": "mdi:sprout-outline", "device": dev}), retain=True)
    client.publish("homeassistant/sensor/gh_claude/actions/config", json.dumps({
        "name": "Claude actions this cycle", "unique_id": "gh_claude_actions",
        "object_id": "greenhouse_claude_actions", "state_topic": "greenhouse/claude/last",
        "value_template": "{{ value_json.actions | length }}", "icon": "mdi:robot-happy",
        "state_class": "measurement", "device": dev}), retain=True)
    client.publish("homeassistant/sensor/gh_claude/cost/config", json.dumps({
        "name": "Claude cost since restart", "unique_id": "gh_claude_cost",
        "object_id": "greenhouse_claude_cost", "state_topic": "greenhouse/claude/last",
        "value_template": "{{ value_json.cost_usd }}", "unit_of_measurement": "USD",
        "icon": "mdi:cash", "state_class": "total_increasing", "device": dev}), retain=True)
    client.publish("homeassistant/sensor/gh_claude/cache/config", json.dumps({
        "name": "Claude cache hit rate", "unique_id": "gh_claude_cache",
        "object_id": "greenhouse_claude_cache_hit", "state_topic": "greenhouse/claude/last",
        "value_template": "{{ value_json.cache_hit_pct }}", "unit_of_measurement": "%",
        "icon": "mdi:database-check", "state_class": "measurement", "device": dev}), retain=True)


def cycle(client, llm):
    dry_run = not autonomy_on()
    state = snapshot()
    messages = [{"role": "user", "content":
                 "Here is the current state of the greenhouse. Decide what, if anything, to do.\n\n"
                 + json.dumps(state, indent=1, default=str)}]
    actions, summary = [], ""

    for _ in range(4):                              # a few tool rounds, then wrap up
        reply = llm.messages.create(model=MODEL, max_tokens=1500, system=SYSTEM_BLOCKS,
                                    tools=TOOLS, messages=messages)
        meter(reply.usage)
        text = "".join(b.text for b in reply.content if b.type == "text").strip()
        if text:
            summary = text
        calls = [b for b in reply.content if b.type == "tool_use"]
        if not calls:
            break
        messages.append({"role": "assistant", "content": reply.content})
        results = []
        for call in calls:
            result = execute(call.name, call.input, dry_run)
            journal(tool=call.name, args=call.input, result=result, dry_run=dry_run,
                    reason=call.input.get("reason") or call.input.get("text", ""))
            actions.append({"tool": call.name, "args": call.input, "result": result})
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": result})
        messages.append({"role": "user", "content": results})

    journal(tool="_summary", args={}, result=summary[:500], dry_run=dry_run)
    publish_status(client, summary or "no change", actions)
    return summary, actions


def preflight(llm):
    """Check the model id at boot. A typo here is otherwise a 3 a.m. failure."""
    try:
        llm.models.retrieve(MODEL)
        print(f"model {MODEL} ok")
    except Exception as exc:
        raise SystemExit(f"model {MODEL!r} was rejected: {exc}\n"
                         f"Check the id against the models list and fix gardener.json.")


def main():
    llm = anthropic.Anthropic(api_key=CFG["anthropic_api_key"])
    preflight(llm)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="greenhouse-gardener")
    client.username_pw_set(CFG["mqtt"]["user"], CFG["mqtt"]["password"])
    client.connect(CFG["mqtt"]["host"], 1883)
    client.loop_start()
    discovery(client)
    period = CFG.get("period_minutes", 60) * 60
    while True:
        started = time.time()
        try:
            summary, actions = cycle(client, llm)
            print(f"[{datetime.now():%H:%M}] {len(actions)} action(s), "
                  f"${usage_cost():.4f} so far: {summary[:100]}")
        except Exception as exc:
            journal(tool="_error", args={}, result=str(exc))
            print("cycle failed:", exc)
        # Sleep in short naps so an escalation from rule_loop.py is picked up within
        # 30 s instead of waiting out the rest of the hour.
        deadline = started + period
        while time.time() < deadline:
            time.sleep(min(30, max(1, deadline - time.time())))
            if ESCALATIONS.exists() and ESCALATIONS.stat().st_size > 0:
                print(f"[{datetime.now():%H:%M}] escalation, waking early")
                break


if __name__ == "__main__":
    main()
