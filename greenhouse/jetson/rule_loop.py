#!/usr/bin/env python3
"""The cheap watcher that sits under the gardener.

claude_gardener.py used to run every 30 minutes because nothing else was looking. That
made the model the thing standing between a plant and a problem, and it cost about $765
a year to have it re-read a mostly unchanged greenhouse 48 times a day.

This process reads the same sensors every 5 minutes for nothing. It decides only one
question: is any number outside a hard band? If yes it writes an escalation line and the
gardener wakes within 30 seconds. If no it is silent. The gardener then runs hourly, and
out of turn whenever this fires, which is the same responsiveness for a fifth of the calls.

It deliberately actuates nothing. Three layers, each with one job:
  ESPHome node firmware   hard interlocks, refuses regardless of what anyone asks
  rule_loop.py (this)     watches, escalates, never acts
  claude_gardener.py      decides and acts, inside LIMITS

Adding a fourth actor here would mean two things could water the same zone, so it does not.

pip install requests
"""
import json
import time
from datetime import datetime
from pathlib import Path

import requests

CFG = json.loads(Path("/opt/greenhouse/gardener.json").read_text())
HA = CFG["ha"]["url"].rstrip("/")
HEAD = {"Authorization": f"Bearer {CFG['ha']['token']}", "Content-Type": "application/json"}
ESCALATIONS = Path(CFG.get("escalations", "/opt/greenhouse/escalations.jsonl"))
PERIOD = CFG.get("rule_loop", {}).get("period_minutes", 5) * 60
TIERS = ["a", "b", "c"]

# Hard bands. Wider than the bands in the gardener's system prompt on purpose: this is
# "something is wrong", not "something could be better". Tuning belongs to the model.
BANDS = CFG.get("rule_loop", {}).get("bands", {
    "air_temp_c": [15.0, 33.0],
    "humidity_pct": [30.0, 90.0],
    "vpd_kpa": [0.4, 2.0],
    "median_soil_pct": [25.0, 75.0],
    "leaf_air_delta_c": [-10.0, 2.5],
})
CO2_FLOOR = 350.0
RESERVOIR_FLOOR_PCT = 15.0

# Once a reading is out of band it stays out for a while, and re-escalating every 5
# minutes would wake the gardener constantly and cost more than the old 30 minute loop.
# One escalation per key per hour.
QUIET_S = CFG.get("rule_loop", {}).get("requiet_minutes", 60) * 60
_last = {}


def ha_state(entity, cast=float, default=None):
    try:
        r = requests.get(f"{HA}/api/states/{entity}", headers=HEAD, timeout=10)
        if not r.ok:
            return default
        s = r.json()
    except requests.RequestException:
        return default
    if s["state"] in ("unknown", "unavailable", ""):
        return default
    try:
        return cast(s["state"])
    except (TypeError, ValueError):
        return s["state"]


def escalate(key, text, severity="soon"):
    now = time.time()
    if now - _last.get(key, 0) < QUIET_S:
        return False
    _last[key] = now
    with ESCALATIONS.open("a") as f:
        f.write(json.dumps({
            "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
            "key": key, "severity": severity, "what": text}) + "\n")
    print(f"[{datetime.now():%H:%M}] escalate {key}: {text}")
    return True


def check_tier(t):
    p = f"sensor.greenhouse_tier_{t}_"
    readings = {
        "air_temp_c": ha_state(p + "air_temperature"),
        "humidity_pct": ha_state(p + "air_humidity"),
        "vpd_kpa": ha_state(p + "vpd"),
        "median_soil_pct": ha_state(p + "median_moisture"),
        "leaf_air_delta_c": ha_state(p + "leaf_to_air_delta"),
    }
    for name, value in readings.items():
        if value is None:
            escalate(f"{t}.{name}.stale", f"tier {t} {name} is unavailable", "soon")
            continue
        lo, hi = BANDS[name]
        if value < lo or value > hi:
            escalate(f"{t}.{name}",
                     f"tier {t} {name} is {value:g}, outside {lo:g} to {hi:g}",
                     "now" if name in ("air_temp_c", "median_soil_pct") else "soon")
    driest = ha_state(p + "driest_plant_moisture")
    median = readings["median_soil_pct"]
    if driest is not None and median is not None and median - driest > 20:
        # The gardener's own rules call this a blocked emitter rather than a dry tier,
        # so it is worth getting in front of it rather than waiting for the hour.
        escalate(f"{t}.emitter",
                 f"tier {t} driest pot {driest:g}% vs median {median:g}%, "
                 f"looks like one emitter not the tier", "soon")


def check_cabinet():
    co2 = ha_state("sensor.greenhouse_tier_c_co2")
    if co2 is not None and co2 < CO2_FLOOR:
        escalate("co2", f"CO2 is {co2:g} ppm, below {CO2_FLOOR:g}", "soon")
    res = ha_state("sensor.greenhouse_utility_reservoir_level")
    if res is not None and res < RESERVOIR_FLOOR_PCT:
        escalate("reservoir", f"reservoir at {res:g}%, below {RESERVOIR_FLOOR_PCT:g}%", "now")
    if ha_state("binary_sensor.greenhouse_utility_leak_detected", str, "off") == "on":
        escalate("leak", "leak detector is latched", "now")
    if ha_state("binary_sensor.greenhouse_utility_doors", str, "off") == "on":
        escalate("doors", "a door has been open at a scheduled check", "soon")


def main():
    ESCALATIONS.touch(exist_ok=True)
    print(f"rule loop up, every {PERIOD // 60} min, quiet period {QUIET_S // 60} min")
    while True:
        started = time.time()
        try:
            for t in TIERS:
                check_tier(t)
            check_cabinet()
        except Exception as exc:                    # never let one bad read kill the watcher
            print("rule loop error:", exc)
        time.sleep(max(30, PERIOD - (time.time() - started)))


if __name__ == "__main__":
    main()
