"""Turn an Envelope into a complete, checked design.

Nothing here is a lookup table. Every number is computed from the envelope and
the physical constants in params.py, and anything that cannot be satisfied is
either a hard DesignError (the build is impossible as asked) or a warning (it
will work, but the builder should know).

    from design.params import PRESETS
    from design.solve import solve
    d = solve(PRESETS["m"])
    print(d.report())
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from params import (Envelope, DesignError, POT, POT_GAP, POT_EDGE, MODULES,
                    W_MIN, W_MAX, D_MIN, D_MAX, H_MIN, H_MAX,
                    SPAN_MAX_2040, SPAN_MAX_4040,
                    ADC_CH, ADC_MAX_PER_BUS, PROBES_MAX_PER_TIER,
                    ARM_REACH, ARM_BASE_DIA, ARM_STOWED_H, ARM_PLATE_T,
                    GANTRY_CARRIAGE_D, CORRIDOR_MIN)

# Stack above a pot rim that is not plant: LED bar, its mount, and the gap that
# keeps the canopy out of the diodes.
LIGHT_STACK = 70.0
SHELF_T = 1.6                 # tray floor sheet, mm
EDGE_MARGIN = 12.0            # tray edge to the first pot, mm
EMITTER_ML_MIN = 31.5         # 0.5 GPH pressure-compensating emitter
DAILY_FRACTION = 0.12         # of pot volume per day, design figure
RESERVOIR_DAYS = 6.0
LED_EFFICACY = 2.7            # umol/J for an LM301H-class bar, conservative
BAR_W_PER_M = 62.5            # a 560 mm / 35 W class bar, used to count bars


@dataclass
class Tier:
    index: int
    label: str                # A, B, C ...
    z: float                  # shelf top surface, mm from the floor
    pitch: float              # to the next shelf (or to the plenum)
    headroom: float           # usable height above the shelf
    pots: int
    pot_pitch: float
    probes: int
    adcs: int
    led_watts: float
    led_bars: int
    emitters: int
    zone_ml_min: float


@dataclass
class Design:
    env: Envelope
    version: str

    # frame
    bays: int
    interior_uprights: int
    clear_span: float
    usable_width: float
    extrusion_total_m: float

    # depth split
    corridor: float
    tray_depth: float
    tray_width: float

    # tiers
    tiers: list[Tier]
    levels: list[float]

    # arm
    arm_j1_y: float | None
    arm_reach_front: float | None
    pot_row_front: float | None
    arm_reach_margin: float | None
    lateral_half_reach: float | None
    rail_travel: float | None

    # systems
    nodes: int
    poe_ports: int
    switch: str
    total_pots: int
    total_probes: int
    daily_water_l: float
    reservoir_l: float
    connected_load_w: float

    warnings: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ view
    def report(self) -> str:
        e = self.env
        L = []
        a = L.append
        a(f"Herb Tower  ·  design {self.version}  ·  preset \"{e.name}\"")
        a("=" * 72)
        a(f"Envelope        {e.width:.0f} W x {e.depth:.0f} D x {e.height:.0f} H mm"
          f"   ·  {e.series}{e.series} T-slot")
        a(f"Modules         {', '.join(e.modules) if e.modules else 'none (core only)'}")
        a("")
        a(f"Frame           {self.bays} bay(s), {self.interior_uprights} interior upright(s), "
          f"clear span {self.clear_span:.0f} mm")
        a(f"                {self.extrusion_total_m:.1f} m of extrusion")
        a(f"Depth split     tray {self.tray_depth:.0f} mm"
          + (f"  +  gantry corridor {self.corridor:.0f} mm" if e.has('gantry') else "  (no corridor, no gantry)"))
        a(f"Tray            {self.tray_width:.0f} x {self.tray_depth:.0f} mm, {e.tray_lip:.0f} mm lip")
        a("")
        a(f"{'tier':<6}{'shelf z':>9}{'pitch':>8}{'headroom':>10}{'pots':>6}"
          f"{'probes':>8}{'ADCs':>6}{'LED W':>8}{'bars':>6}{'mL/min':>9}")
        for t in self.tiers:
            a(f"{t.label:<6}{t.z:>9.0f}{t.pitch:>8.0f}{t.headroom:>10.0f}{t.pots:>6}"
              f"{t.probes:>8}{t.adcs:>6}{t.led_watts:>8.0f}{t.led_bars:>6}{t.zone_ml_min:>9.0f}")
        a("")
        bp = f", tier A in {e.bottom_tier_pot}" if e.bottom_tier_pot else ""
        a(f"Plants          {self.total_pots} pots, {e.pot_size}{bp}")
        a(f"Water           {self.daily_water_l:.1f} L/day design draw, "
          f"reservoir {self.reservoir_l:.0f} L for {RESERVOIR_DAYS:.0f} days")
        a(f"Electrical      {self.connected_load_w:.0f} W connected")
        a(f"Network         {self.nodes} nodes, {self.poe_ports} PoE ports needed -> {self.switch}")
        if self.env.has("arm"):
            a("")
            a(f"Arm             J1 at y={self.arm_j1_y:.0f} mm from the front face")
            a(f"                reaches forward to y={self.arm_reach_front:.0f} mm; "
              f"pot row starts at y={self.pot_row_front:.0f} mm")
            a(f"                margin {self.arm_reach_margin:+.0f} mm, "
              f"lateral half-reach {self.lateral_half_reach:.0f} mm")
            a(f"                rail travel needed {self.rail_travel:.0f} mm")
        if self.warnings:
            a("")
            a("WARNINGS")
            for w in self.warnings:
                a(f"  ! {w}")
        return "\n".join(L)


# ---------------------------------------------------------------------- solve
def solve(env: Envelope, version: str = "0.0.0") -> Design:
    warn: list[str] = []
    _check_envelope(env)

    ser = float(env.series) * 10.0            # 20 -> 200? no: series 20 = 20 mm
    ser = 20.0 if env.series == 20 else 40.0

    # --- frame: how many bays before the shelf sags -----------------------
    span_max = SPAN_MAX_2040 if env.series == 20 else SPAN_MAX_4040
    inner = env.width - 2 * ser
    bays = max(1, math.ceil(inner / span_max))
    interior = bays - 1
    clear_span = (env.width - ser * (bays + 1)) / bays
    if clear_span <= 0:
        raise DesignError(
            f"{env.width:.0f} mm is too narrow for {bays + 1} uprights of "
            f"{ser:.0f} mm. Use a wider envelope or the 20-series.")
    usable_width = env.width - 2 * ser
    if interior:
        warn.append(
            f"{env.width:.0f} mm exceeds the {span_max:.0f} mm span a "
            f"{env.series}{env.series} shelf carries without ponding, so the design "
            f"adds {interior} interior upright(s). Pots cannot sit in the "
            f"{ser:.0f} mm those occupy.")
        usable_width -= interior * ser

    # --- depth: corridor first, tray gets the rest ------------------------
    if env.has("gantry"):
        corridor = max(CORRIDOR_MIN,
                       GANTRY_CARRIAGE_D + ARM_PLATE_T + ARM_BASE_DIA + 18.0)
        tray_depth = env.depth - corridor
        if tray_depth < 150.0:
            raise DesignError(
                f"A gantry needs a {corridor:.0f} mm corridor, which leaves only "
                f"{tray_depth:.0f} mm of tray in a {env.depth:.0f} mm cabinet. "
                f"Either go at least {corridor + 150:.0f} mm deep or drop the "
                f"'gantry' module.")
    else:
        corridor = 0.0
        tray_depth = env.depth - 30.0

    pot = POT[env.pot_size]
    if tray_depth < pot["size"] + 2 * EDGE_MARGIN:
        raise DesignError(
            f"A {env.pot_size} pot is {pot['size']:.0f} mm square and the tray is "
            f"only {tray_depth:.0f} mm deep. Go deeper, use a smaller pot, or drop "
            f"the gantry to reclaim its corridor.")

    # --- vertical: can every tier hold a plant? ---------------------------
    min_pitch = pot["height"] + env.plant_height + LIGHT_STACK
    avail = env.height - env.base_bay - env.top_plenum
    if avail < env.tiers * min_pitch:
        short = env.tiers * min_pitch - avail
        raise DesignError(
            f"{env.tiers} tiers need {env.tiers * min_pitch:.0f} mm of stack "
            f"({min_pitch:.0f} mm each for a {pot['height']:.0f} mm pot, "
            f"{env.plant_height:.0f} mm of plant and {LIGHT_STACK:.0f} mm of light), "
            f"but only {avail:.0f} mm is left after the {env.base_bay:.0f} mm base "
            f"bay. Short by {short:.0f} mm: lose a tier, lower the canopy target, "
            f"or go {short:.0f} mm taller.")

    pitches = _distribute(avail, env.tiers, min_pitch,
                          env.bottom_tier_bonus if env.tall_bottom_tier else 0.0)

    # --- the grid ---------------------------------------------------------
    # Pots are spread across the clear span, so the count comes first and the
    # pitch falls out of it. n pots need n walls plus (n-1) gaps plus two edges.
    def grid(p):
        n = max(0, int((clear_span - 2 * POT_EDGE + POT_GAP) // (p["size"] + POT_GAP)))
        if n == 0:
            raise DesignError(
                f"No {p['size']:.0f} mm pot fits in a {clear_span:.0f} mm clear span.")
        pitch = ((clear_span - 2 * POT_EDGE - p["size"]) / (n - 1)
                 if n > 1 else clear_span)
        return n * bays, pitch

    pots_per_tier, pot_pitch = grid(pot)
    bottom_pot = POT[env.bottom_tier_pot] if env.bottom_tier_pot else pot
    bottom_pots, bottom_pitch = grid(bottom_pot)
    if pots_per_tier == 0:
        raise DesignError(
            f"No {env.pot_size} pot fits in a {clear_span:.0f} mm clear span.")

    tiers: list[Tier] = []
    levels = [0.0, env.base_bay]
    z = env.base_bay
    tier_area = (usable_width / 1000.0) * (tray_depth / 1000.0)   # m2
    led_w = env.ppfd_target * tier_area / LED_EFFICACY
    bars = max(1, math.ceil(led_w / (BAR_W_PER_M * usable_width / 1000.0 / 1.0)
                            if usable_width else 1))
    bars = max(1, round(led_w / 35.0))        # 35 W class bars

    for i in range(env.tiers):
        is_bottom = (i == 0 and env.bottom_tier_pot is not None)
        n_pots = bottom_pots if is_bottom else pots_per_tier
        p_pitch = bottom_pitch if is_bottom else pot_pitch
        adcs = math.ceil(n_pots / ADC_CH)
        if n_pots > PROBES_MAX_PER_TIER:
            warn.append(
                f"Tier {chr(65 + i)} has {n_pots} pots but one node can only "
                f"read {PROBES_MAX_PER_TIER} probes ({ADC_MAX_PER_BUS} ADS1115 on "
                f"four addresses). Split the tier across two nodes, or accept "
                f"zone-level moisture for the surplus pots.")
            adcs = ADC_MAX_PER_BUS
        tiers.append(Tier(
            index=i, label=chr(65 + i), z=z, pitch=pitches[i],
            headroom=pitches[i] - LIGHT_STACK,
            pots=n_pots, pot_pitch=p_pitch,
            probes=min(n_pots, PROBES_MAX_PER_TIER), adcs=adcs,
            led_watts=led_w, led_bars=bars,
            emitters=n_pots,
            zone_ml_min=n_pots * EMITTER_ML_MIN))
        z += pitches[i]
        levels.append(z)

    # --- arm geometry ------------------------------------------------------
    j1 = reach_front = row_front = margin = half = travel = None
    if env.has("arm"):
        if not env.has("gantry"):
            raise DesignError(
                "The 'arm' module needs the 'gantry' module: the arm has a "
                f"{ARM_REACH:.0f} mm reach and has to be carried to each plant.")
        j1 = tray_depth + GANTRY_CARRIAGE_D + ARM_PLATE_T + ARM_BASE_DIA / 2
        reach_front = j1 - ARM_REACH
        # pots are pushed to the BACK of the tray, nearest the arm
        row_front = tray_depth - pot["size"] - POT_EDGE
        margin = row_front - reach_front
        if margin < 0:
            warn.append(
                f"The arm cannot reach the front of the pot row: J1 sits "
                f"{j1:.0f} mm back, its {ARM_REACH:.0f} mm reach stops at "
                f"y={reach_front:.0f} mm, and the pots start at y={row_front:.0f} mm. "
                f"Short by {-margin:.0f} mm. Push the pots further back, go "
                f"shallower, or accept that the arm works the back of each pot only.")
        dy = j1 - (tray_depth - pot["size"] / 2 - POT_EDGE)
        half = math.sqrt(max(0.0, ARM_REACH ** 2 - dy ** 2))
        travel = max(0.0, usable_width - 2 * half)
        for t in tiers:
            if t.headroom < ARM_STOWED_H:
                warn.append(
                    f"Tier {t.label} has {t.headroom:.0f} mm of headroom and the arm "
                    f"is {ARM_STOWED_H:.0f} mm tall stowed, so it has to travel "
                    f"folded and unfold only once the mast has it at the tier.")
                break

    # --- systems -----------------------------------------------------------
    total_pots = sum(t.pots for t in tiers)
    total_probes = sum(t.probes for t in tiers)
    nodes = env.tiers + 1
    poe = nodes
    switch = _switch_for(poe, env)
    if poe > 4:
        warn.append(
            f"{poe} PoE ports are needed ({env.tiers} tier nodes + utility) and the "
            f"TL-SG108PE has four. The design specifies {switch} instead.")

    daily_l = sum(t.pots * (bottom_pot if t.index == 0 and env.bottom_tier_pot
                                    else pot)["litres"] for t in tiers) * DAILY_FRACTION
    reservoir = max(10.0, math.ceil(daily_l * RESERVOIR_DAYS))

    load = sum(t.led_watts for t in tiers)
    load += 15.0 * env.tiers                       # fans and sensing per tier
    if env.has("climate"):
        load += 60.0                               # humidifier duty average
    if env.has("arm"):
        load += 120.0                              # arm + Jetson
    if env.has("gantry"):
        load += 60.0                               # steppers

    extrusion = _extrusion_metres(env, bays, interior, levels)

    return Design(
        env=env, version=version,
        bays=bays, interior_uprights=interior, clear_span=clear_span,
        usable_width=usable_width, extrusion_total_m=extrusion,
        corridor=corridor, tray_depth=tray_depth, tray_width=clear_span,
        tiers=tiers, levels=levels,
        arm_j1_y=j1, arm_reach_front=reach_front, pot_row_front=row_front,
        arm_reach_margin=margin, lateral_half_reach=half, rail_travel=travel,
        nodes=nodes, poe_ports=poe, switch=switch,
        total_pots=total_pots, total_probes=total_probes,
        daily_water_l=daily_l, reservoir_l=reservoir, connected_load_w=load,
        warnings=warn)


# ------------------------------------------------------------------- helpers
def _check_envelope(e: Envelope) -> None:
    for val, lo, hi, nm in ((e.width, W_MIN, W_MAX, "width"),
                            (e.depth, D_MIN, D_MAX, "depth"),
                            (e.height, H_MIN, H_MAX, "height")):
        if not (lo <= val <= hi):
            raise DesignError(
                f"{nm} {val:.0f} mm is outside the supported range "
                f"{lo:.0f} to {hi:.0f} mm.")
    if e.tiers < 1:
        raise DesignError("A design needs at least one tier.")
    if e.pot_size not in POT:
        raise DesignError(f"Unknown pot size {e.pot_size!r}.")
    for m in e.modules:
        if m not in MODULES:
            raise DesignError(f"Unknown module {m!r}. Known: {', '.join(MODULES)}.")


def _distribute(avail: float, n: int, floor_: float, bonus: float) -> list[float]:
    """Every tier clears `floor_`; tier A takes `bonus` first, the rest splits even.

    The bonus is what makes a 1 gal pepper on the bottom shelf possible while the
    herbs above it sit on tighter pitches. It is capped at the surplus actually
    available, so asking for a bonus you cannot afford quietly gets you a level
    stack rather than a design error.
    """
    base = [floor_] * n
    surplus = avail - floor_ * n
    if n == 1:
        return [avail]
    take = min(bonus, surplus)
    base[0] += take
    rest = (surplus - take) / n
    for i in range(n):
        base[i] += rest
    return base


def _switch_for(poe: int, env: Envelope) -> str:
    if poe <= 4:
        return "TP-Link TL-SG108PE (4 PoE of 8 ports)"
    if poe <= 8:
        return "TP-Link TL-SG1016PE (8 PoE of 16 ports)"
    return "TP-Link TL-SG1218MP (16 PoE) or a second switch"


def _extrusion_metres(e: Envelope, bays: int, interior: int,
                      levels: list[float]) -> float:
    uprights = (2 + interior) * 2                      # front and back
    m = uprights * e.height
    m += len(levels) * 2 * e.width                     # front and back rails
    m += len(levels) * (2 + interior) * e.depth        # side and interior rails
    return m / 1000.0


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from params import PRESETS
    v = "0.0.0"
    vf = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERSION")
    if os.path.exists(vf):
        v = open(vf).read().strip()
    which = sys.argv[1:] or list(PRESETS)
    for name in which:
        try:
            print(solve(PRESETS[name], v).report())
        except DesignError as ex:
            print(f"preset {name}: REJECTED\n  {ex}")
        print("\n")
