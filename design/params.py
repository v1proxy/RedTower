"""Herb Tower design parameters.

One Envelope describes the space somebody has. Everything else in the repo is
derived from it by solve.py, so there is exactly one place to change a number.

The ranges here are not taste. Each bound comes from a physical limit that is
named in the comment next to it, and solve.py explains any value it rejects.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal

DESIGN_VERSION = open(__file__.rsplit("/", 2)[0] + "/VERSION").read().strip() \
    if __import__("os").path.exists(__file__.rsplit("/", 2)[0] + "/VERSION") else "0.0.0"

# --------------------------------------------------------------------- limits
W_MIN, W_MAX = 600.0, 3000.0        # closet bay to a full room wall
D_MIN, D_MAX = 300.0, 760.0         # a tray shallower than 300 will not hold a 4.5 in pot
H_MIN, H_MAX = 900.0, 2600.0        # a bench-top unit up to something you still reach the top of

# 4040 T-slot carrying a loaded tray: beyond this span the shelf sags enough to
# pond water in the tray, so solve.py inserts an intermediate upright.
SPAN_MAX_4040 = 1500.0
SPAN_MAX_2040 = 900.0

# ADS1115 answers on four addresses only: 0x48, 0x49, 0x4A, 0x4B.
ADC_CH = 4
ADC_MAX_PER_BUS = 4
PROBES_MAX_PER_TIER = ADC_CH * ADC_MAX_PER_BUS      # 16

# The arm's own geometry, from the Elephant Robotics URDF.
ARM_REACH = 280.0          # published working radius
ARM_BASE_DIA = 160.0       # measured across the base of the mesh
ARM_STOWED_H = 437.0       # measured, folded
ARM_PLATE_T = 6.35         # G071, 0.250 in
GANTRY_CARRIAGE_D = 70.0   # XLarge C-Beam carriage + wheels, back of plate to rail face
CORRIDOR_MIN = 230.0       # carriage + plate + arm base + working clearance

MODULES = ("gantry", "arm", "climate")


@dataclass
class Envelope:
    """The space available, plus what the builder wants in it."""

    name: str = "custom"

    # --- the space -------------------------------------------------------
    width: float = 1397.0            # outside width of the frame, mm
    depth: float = 457.0             # outside depth, mm
    height: float = 1829.0           # outside height, mm

    # --- growing ---------------------------------------------------------
    tiers: int = 3                   # growing levels (not counting the base bay)
    pot_size: Literal["4.5in", "1gal", "2gal"] = "4.5in"
    bottom_tier_pot: str | None = None   # a bigger pot on tier A, e.g. "1gal"
    tall_bottom_tier: bool = True    # give tier A the extra headroom for peppers
    plant_height: float = 190.0      # canopy target above the pot rim on a normal tier, mm
    bottom_tier_bonus: float = 250.0 # extra headroom for tier A when tall_bottom_tier

    # --- modules ---------------------------------------------------------
    modules: tuple[str, ...] = ("gantry", "arm", "climate")

    # --- build choices ---------------------------------------------------
    series: Literal[20, 40] = 40     # T-slot series
    base_bay: float = 304.8          # height of the services bay under tier A, mm
    top_plenum: float = 40.0         # gap above the top tier's light, mm
    tray_lip: float = 25.0           # tray upstand, mm
    ppfd_target: float = 300.0       # umol/m2/s at canopy, drives LED wattage
    photoperiod_h: int = 16

    notes: str = ""

    # ------------------------------------------------------------------ util
    def has(self, module: str) -> bool:
        return module in self.modules

    def to_dict(self) -> dict:
        d = asdict(self)
        d["modules"] = list(self.modules)
        return d


POT = {
    #            across mm, height mm, litres. Pitch is computed: pots are spread
    #            across the clear span, so the gap falls out of how many fit.
    "4.5in": dict(size=114.3, height=127.0, litres=1.2,
                  part="HC Companies Square Black Form Pot, 4.5 in deep"),
    "1gal":  dict(size=134.6, height=175.0, litres=3.8,
                  part="Gro Pro Premium Nursery Pot, 1 gallon"),
    "2gal":  dict(size=221.0, height=218.0, litres=7.6,
                  part="Gro Pro Premium Nursery Pot, 2 gallon"),
}

POT_GAP = 12.0        # minimum air gap between pot walls, mm
POT_EDGE = 6.0        # minimum gap from the tray upstand to the first pot, mm


class DesignError(ValueError):
    """Raised when an envelope cannot be built. The message says why."""


PRESETS: dict[str, Envelope] = {
    "xs": Envelope(
        name="xs",
        width=600.0, depth=360.0, height=1100.0,
        tiers=2, pot_size="4.5in", tall_bottom_tier=False,
        plant_height=200.0,
        modules=(),                      # no rail, no arm, no climate block
        series=20, base_bay=180.0,
        notes="Closet bay or a wide bookshelf. Hand-tended: sensing, light and "
              "drip only. Two tiers of herbs, one node plus the utility node.",
    ),
    "s": Envelope(
        name="s",
        width=900.0, depth=400.0, height=1500.0,
        tiers=3, pot_size="4.5in", tall_bottom_tier=False,
        plant_height=200.0,
        modules=("climate",),
        series=20, base_bay=240.0,
        notes="A wardrobe or an alcove. Still hand-tended, but with the exhaust "
              "and CO2 block so it can run with the doors shut.",
    ),
    "m": Envelope(
        name="m",
        width=1397.0, depth=457.0, height=1829.0,
        tiers=3, pot_size="4.5in", tall_bottom_tier=True,
        plant_height=190.0, bottom_tier_bonus=250.0, bottom_tier_pot="1gal",
        modules=("gantry", "arm", "climate"),
        series=40, base_bay=304.8,
        notes="The Red Tower reference build. 27 plants, robot-tended. Every "
              "drawing and every BOM revision in this repo is this size.",
    ),
    "l": Envelope(
        name="l",
        width=2100.0, depth=560.0, height=2200.0,
        tiers=4, pot_size="1gal", tall_bottom_tier=True,
        plant_height=190.0, bottom_tier_bonus=200.0,
        modules=("gantry", "arm", "climate"),
        series=40, base_bay=330.0,
        notes="A garage or utility-room wall. Wide enough to need an "
              "intermediate upright, which the solver adds for you.",
    ),
    "xl": Envelope(
        name="xl",
        width=3000.0, depth=610.0, height=2400.0,
        tiers=5, pot_size="4.5in", tall_bottom_tier=True,
        plant_height=190.0, bottom_tier_bonus=200.0,
        modules=("gantry", "arm", "climate"),
        series=40, base_bay=350.0,
        notes="Full room wall. At this width one arm cannot reach everything "
              "from one gantry position, so the solver reports the dwell "
              "positions the motion planner has to visit.",
    ),
}
