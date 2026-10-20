#!/usr/bin/env python3
"""Maag daily running cost: electricity + Claude tokens.

Electricity comes from the Rev E BOM Power sheet, with two corrections (see NOTE).
Token counts are built from the real prompts in jetson/claude_gardener.py and
jetson/plant_tender.py, by constructing a representative payload and measuring it.
"""
import json
from datetime import datetime

# ------------------------------------------------------------------ tariff
# Houston, CenterPoint. The greenhouse is a marginal load on an existing bill, so
# the fixed $4.90/month customer charge does not apply to it; only the per-kWh parts do.
ENERGY_C_KWH = 9.15      # market average, chooseenergy, Oct 2026
TDU_C_KWH = 6.40         # CenterPoint residential delivery, effective 2026-09-01
RATE = (ENERGY_C_KWH + TDU_C_KWH) / 100.0        # $/kWh marginal

DRV_EFF = 0.92           # Mean Well HLG driver
PSU_EFF = 0.88           # LRS-350-24
PSU_IDLE_W = 3.0         # no-load draw of the 24 V brick, 24 h/day

# ------------------------------------------------------------------ loads
# (name, rail, steady_W, peak_W, hours_per_day)
# NOTE: the Rev E sheet computes Wh as steady_W * hours. For the RealSense and the
# humidifier the steady column is 0 because they are off most of the time, so the
# sheet scores them as zero energy. Here an intermittent load uses its peak while on.
LOADS = [
    ("Grow lights Tier A",        "AC",  65 / DRV_EFF, 65 / DRV_EFF, 16),
    ("Grow lights Tier B",        "AC",  40 / DRV_EFF, 40 / DRV_EFF, 16),
    ("Grow lights Tier C",        "AC",  40 / DRV_EFF, 40 / DRV_EFF, 16),
    ("Fans, 5 x Noctua",          "12V",  6.0,  11.0, 24),
    ("ESP32 nodes + sensors",     "PoE",  8.0,  10.0, 24),
    ("PoE switch TL-SG108PE",     "AC",   6.0,   9.0, 24),
    ("Jetson Orin Nano Super",    "AC",  12.0,  25.0, 24),
    ("Overview camera",           "USB",  1.5,   2.0, 24),
    ("RealSense D405",            "USB",  0.0,   1.6, 1),
    ("Humidifier",                "AC",   0.0,  24.0, 0.5),
    ("Pump + one valve",          "24V", 46.0,  46.0, 0.17),
    ("Gantry X + Z",              "24V", 28.0,  55.0, 1),
    ("Z brake",                   "24V",  4.5,   4.5, 1),
    ("myCobot 280 Pi idle",       "12V",  5.0,   5.0, 23),
    ("myCobot 280 Pi moving",     "12V", 15.0,  60.0, 1),
]


def electricity():
    rows, wh_dc_rails, wh_total = [], 0.0, 0.0
    for name, rail, steady, peak, hours in LOADS:
        w = steady if steady > 0 else peak           # the correction
        wh = w * hours
        rows.append((name, rail, w, hours, wh))
        wh_total += wh
        if rail in ("12V", "24V"):
            wh_dc_rails += wh
    conv_loss = wh_dc_rails * (1 / PSU_EFF - 1)
    idle = PSU_IDLE_W * 24
    kwh = (wh_total + conv_loss + idle) / 1000.0
    return rows, wh_total, conv_loss, idle, kwh


# ------------------------------------------------------------------ tokens
# Sonnet 5, the model in gardener.example.json
PRICE = {"in": 2.00, "out": 10.00, "cache_read": 0.20, "cache_write_1h": 4.00}
CHARS_PER_TOKEN = 3.6            # dense JSON and schema text


def tok(chars):
    return chars / CHARS_PER_TOKEN


def gardener_snapshot_chars(n_plants=27, journal_entries=40):
    plant = {"id": "a01", "label": "A01", "tier": "a",
             "species": "Capsicum annuum (compact)", "stage": "seedling",
             "planted": "2026-10-01"}
    vision = {"canopy_area": 1842.5, "greenness": 0.71, "yellowing": 0.04, "stress": 0.12}
    tier = {"air_temp_c": 24.1, "rh_pct": 61.0, "vpd_kpa": 1.18, "leaf_delta_c": -1.4,
            "soil_moisture_pct": 38.0, "light_on_hour": 6, "photoperiod_h": 16,
            "intensity_pct": 85, "circulation_pct": 40, "par_umol": 310}
    entry = {"ts": "2026-10-13T14:30:00-05:00", "tool": "water_zone",
             "args": {"tier": "b", "seconds": 45,
                      "reason": "soil moisture on Tier B fell to 31 percent"},
             "result": "ok, watered tier b for 45 s"}
    state = {
        "now": "2026-10-13T20:30-05:00",
        "tiers": {t: tier for t in ("a", "b", "c")},
        "co2_ppm": 640,
        "exhaust_setpoints": {"temp_setpoint_c": 25.0, "rh_limit_pct": 70,
                              "exhaust_min_pct": 20},
        "water": {"reservoir_pct": 72, "reservoir_litres": 14.4, "water_temp_c": 21.8,
                  "delivered_today_ml": 1860, "leak": "off", "lockout": "off"},
        "doors_open": "off", "robot_busy": "off", "power_w": 148.2,
        "plants": [dict(plant, id=f"p{i:02d}") for i in range(n_plants)],
        "vision": {f"p{i:02d}": vision for i in range(n_plants)},
        "recent_actions": [entry for _ in range(journal_entries)],
    }
    return len(json.dumps(state, indent=1))


SYS_GARDENER_CHARS = 1678        # measured from claude_gardener.py
TOOLS_GARDENER_CHARS = 3400      # 8 tools, as JSON schema on the wire
SYS_TENDER_CHARS = 2244
TOOLS_TENDER_CHARS = 1900
IMAGE_TOKENS = 848 * 480 / 750   # D405 capture, (w*h)/750


def gardener_day(cycles=48, rounds=2.2, out_tokens=320):
    base_in = tok(SYS_GARDENER_CHARS + TOOLS_GARDENER_CHARS
                  + gardener_snapshot_chars() + 120)
    # each extra tool round resends the transcript plus the new tool result
    in_tokens = base_in * rounds
    return dict(cycles=cycles,
                in_tok=in_tokens * cycles,
                out_tok=out_tokens * rounds * cycles,
                base_in=base_in)


def tender_day(plants=27, rounds=2.5, out_tokens=260):
    brief_chars = 900
    base_in = tok(SYS_TENDER_CHARS + TOOLS_TENDER_CHARS + brief_chars) + IMAGE_TOKENS
    return dict(runs=plants,
                in_tok=base_in * rounds * plants,
                out_tok=out_tokens * rounds * plants,
                base_in=base_in)


def cost(in_tok, out_tok, cached_frac=0.0):
    cached = in_tok * cached_frac
    fresh = in_tok - cached
    return (fresh * PRICE["in"] + cached * PRICE["cache_read"]
            + out_tok * PRICE["out"]) / 1e6


# ------------------------------------------------------- scenario D, as shipped
# Measured against the real prompt after the 2026-10-13 change: hourly cadence, the
# static head (system + roster + tool schemas) on a 1 h cache breakpoint, 6 h of
# digested journal, Haiku 5.5 on the loop and Sonnet 5.5 on the per-plant vision pass.
D_STATIC_TOK = 2021          # cached prefix, byte-identical every call
D_DYN_TOK = 1328             # fresh payload per call
D_CYCLES = 24 + 3            # hourly, plus ~3 early wake-ups from rule_loop.py
HAIKU55 = {"in": 0.10, "out": 0.50, "cache_read": 0.01, "cache_write_1h": 0.20}
SONNET55 = {"in": 2.00, "out": 10.00, "cache_read": 0.10, "cache_write_1h": 4.00}


def scenario_d(rounds=2.2, out_tokens=320):
    writes = D_CYCLES * D_STATIC_TOK                     # 1 h TTL, one write per run
    reads = D_CYCLES * (rounds - 1) * D_STATIC_TOK       # the extra tool rounds hit it
    fresh = D_CYCLES * rounds * D_DYN_TOK
    out = D_CYCLES * rounds * out_tokens
    g = (fresh * HAIKU55["in"] + reads * HAIKU55["cache_read"]
         + writes * HAIKU55["cache_write_1h"] + out * HAIKU55["out"]) / 1e6
    t_in, t_out = 1944 * 2.5 * 27, 260 * 2.5 * 27
    t = (t_in * SONNET55["in"] + t_out * SONNET55["out"]) / 1e6
    return g, t, fresh + reads + writes + out + t_in + t_out


if __name__ == "__main__":
    rows, wh, loss, idle, kwh = electricity()
    print(f"ELECTRICITY   marginal rate {RATE*100:.2f} c/kWh "
          f"({ENERGY_C_KWH} energy + {TDU_C_KWH} CenterPoint delivery)\n")
    print(f"{'load':26} {'rail':5} {'W':>7} {'h/day':>6} {'Wh/day':>9}")
    print("-" * 58)
    for name, rail, w, h, e in rows:
        print(f"{name:26} {rail:5} {w:7.1f} {h:6.2f} {e:9.1f}")
    print("-" * 58)
    print(f"{'load subtotal':26} {'':5} {'':7} {'':6} {wh:9.1f}")
    print(f"{'PSU conversion loss':26} {'':5} {'':7} {'':6} {loss:9.1f}")
    print(f"{'24 V brick no-load':26} {'':5} {'':7} {'':6} {idle:9.1f}")
    print(f"\n  {kwh:.3f} kWh/day   ${kwh*RATE:.3f}/day   "
          f"${kwh*RATE*30.44:.2f}/month   ${kwh*RATE*365:.2f}/year")
    lights = sum(e for n, _, _, _, e in rows if n.startswith("Grow lights"))
    print(f"  lighting is {lights/ (wh+loss+idle) * 100:.0f}% of it\n")

    g = gardener_day()
    t = tender_day()
    print("CLAUDE TOKENS   model claude-sonnet-5, "
          f"${PRICE['in']}/M in, ${PRICE['out']}/M out, ${PRICE['cache_read']}/M cache read\n")
    print(f"  gardener  {g['cycles']} cycles/day, {g['base_in']:,.0f} input tokens per call")
    print(f"            {g['in_tok']:,.0f} in + {g['out_tok']:,.0f} out per day")
    print(f"  tender    {t['runs']} plants/day, {t['base_in']:,.0f} input tokens per call "
          f"(incl. {IMAGE_TOKENS:.0f} image)")
    print(f"            {t['in_tok']:,.0f} in + {t['out_tok']:,.0f} out per day")
    tot_in, tot_out = g["in_tok"] + t["in_tok"], g["out_tok"] + t["out_tok"]
    print(f"\n  total {tot_in + tot_out:,.0f} tokens/day "
          f"({tot_in:,.0f} in, {tot_out:,.0f} out)")
    c0 = cost(tot_in, tot_out, 0.0)
    print(f"  ${c0:.3f}/day   ${c0*30.44:.2f}/month   ${c0*365:.2f}/year")
    print(f"\n  electricity + agents: ${kwh*RATE + c0:.2f}/day, "
          f"${(kwh*RATE + c0)*30.44:.2f}/month")

    gd, td, dtok = scenario_d()
    d = gd + td
    print(f"\nSCENARIO D, as shipped 2026-10-13\n")
    print(f"  gardener  {D_CYCLES} runs/day on Haiku 5.5, cached head  ${gd:.3f}/day")
    print(f"  tender    27 plants/day on Sonnet 5.5                   ${td:.3f}/day")
    print(f"  agents    {dtok:,.0f} tokens/day                        ${d:.3f}/day")
    print(f"  total with electricity: ${d + kwh*RATE:.2f}/day, "
          f"${(d + kwh*RATE)*30.44:.2f}/month, ${(d + kwh*RATE)*365:.0f}/year")
    print(f"  down {100*(1 - (d + kwh*RATE)/(c0 + kwh*RATE)):.0f}% from as-designed")
