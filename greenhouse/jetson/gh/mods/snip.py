"""The Herb Snip, the cut-and-hold tool on the myCobot 280's flange (greenhouse/snip).

One TowerPro MG90S closes a blade jaw onto an anvil through a four-bar linkage. Silicone foam
pads either side of the blade close a moment before it, so what is cut stays held: the arm
carries it, folded, to the harvest drawer and opens over it. The same jaw picks a pepper by its stem.

The servo's signal is the arm's own end connector, Atom pin G22, as 50 Hz PWM through
pymycobot's set_pwm_output(channel, frequency, duty). The duty is 0 to 256 of the period, so
one step is 78 us of pulse, about 7 degrees of servo travel: enough for open and closed and
nothing finer, which is all the tool needs. A duty of 0 stops the pulses and the servo goes
limp. The servo's power is a 6 V regulator on the 12 V wrist line, and the doors and the
E-stop cut the arm's power, so an open door ends the pulses and the jaw can be pushed open
by hand.

Calibration lives in arm.yaml under "snip". Until it is marked calibrated the real arm never
sends a pulse; tools_snip_check.py finds the two pulses (commissioning, Herb Snip booklet
step 12)."""
import math

FULL = 256                  # set_pwm_output duty full scale
PULSE_US = (500, 2500)      # what any hobby servo accepts; anything outside is a typo


def duty(us, hz):
    """Pulse width in microseconds to set_pwm_output's duty at hz."""
    if not PULSE_US[0] <= us <= PULSE_US[1]:
        raise ValueError(f"pulse {us} us is outside {PULSE_US[0]} to {PULSE_US[1]}")
    return max(1, min(FULL - 1, round(us * hz * FULL / 1e6)))


def pulse_us(d, hz):
    """The pulse a duty step really gives: what the servo sees after rounding."""
    return d * 1e6 / (hz * FULL)


def check_spec(spec):
    """Problems with an arm.yaml snip block, as a list of strings (empty when usable)."""
    bad = []
    for key in ("pin", "hz", "closed_us", "open_us", "settle_s"):
        if not isinstance(spec.get(key), (int, float)) or isinstance(spec.get(key), bool):
            bad.append(f"snip.{key} is missing or not a number")
    if bad:
        return bad
    for key in ("closed_us", "open_us"):
        try:
            duty(spec[key], spec["hz"])
        except ValueError as exc:
            bad.append(f"snip.{key}: {exc}")
    if not bad and duty(spec["closed_us"], spec["hz"]) == duty(spec["open_us"], spec["hz"]):
        bad.append("snip.closed_us and snip.open_us round to the same duty step")
    return bad


class Snip:
    """The jaw, on anything with pymycobot's set_pwm_output. States: limp (no pulses: nothing
    sent yet, or released), opening, open, closing, closed."""

    def __init__(self, mc, spec, clock):
        self.mc, self.spec, self.clock = mc, spec, clock
        self.jaw, self.until = "limp", 0.0

    def _send(self, d):
        self.mc.set_pwm_output(int(self.spec["pin"]), int(self.spec["hz"]), int(d))

    def open(self):
        self._send(duty(self.spec["open_us"], self.spec["hz"]))
        self.jaw, self.until = "opening", self.clock() + float(self.spec["settle_s"])

    def close(self):
        """Close onto the anvil: a cut, then a hold. The servo keeps pushing while it holds."""
        self._send(duty(self.spec["closed_us"], self.spec["hz"]))
        self.jaw, self.until = "closing", self.clock() + float(self.spec["settle_s"])

    def limp(self):
        self._send(0)
        self.jaw, self.until = "limp", 0.0

    def state(self):
        if self.jaw in ("opening", "closing") and self.clock() >= self.until:
            self.jaw = "open" if self.jaw == "opening" else "closed"
        return self.jaw

    def settled(self):
        return self.state() in ("open", "closed", "limp")


# ------------------------------------------------------------------ the camera's look into the jaws
def jaw_roi(intr, view):
    """Pixel box [u0, v0, u1, v1] where the D405 sees the gap between the jaws: from the cut zone
    to the jaw tips along the image's centre column (arm.yaml snip.stem_view, angles from the
    optical axis, from snip_cad.py's placement). "flip" if the tips come out above the centre."""
    t0, t1 = (math.tan(math.radians(a)) for a in view["ang_y"])
    w = math.tan(math.radians(view["half_width_deg"])) * intr["fx"]
    sign = -1.0 if view.get("flip") else 1.0
    vs = sorted(intr["cy"] - sign * t * intr["fy"] for t in (t0, t1))
    return [max(0, int(intr["cx"] - w)), max(0, int(vs[0])), min(intr["width"], int(intr["cx"] + w) + 1),
            min(intr["height"], int(vs[1]) + 1)]


def stem_present(depth_m, empty_m, roi, view):
    """Something between the jaws: pixels in the box that read nearer than with the jaws empty
    (by view["nearer_mm"]), within the D405's honest range, and enough of them. Returns
    (present, pixels)."""
    u0, v0, u1, v1 = roi
    d, e = depth_m[v0:v1, u0:u1], empty_m[v0:v1, u0:u1]
    near, far = view.get("range_mm", (68, 120))
    ok = (d * 1000 > near) & (d * 1000 < far)
    nearer = ok & ((e <= 0) | (d < e - view.get("nearer_mm", 4.0) / 1000))
    n = int(nearer.sum())
    return n >= view.get("min_px", 150), n
