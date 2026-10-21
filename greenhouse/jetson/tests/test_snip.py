"""The Herb Snip: pulse arithmetic, the jaw, the arm driver's cut and release on a simulated
myCobot, and where a tend task takes what it cut (the harvest drawer, or the waste spot)."""
import json
import unittest

import numpy as np

from rig import T
from gh.mods import snip as S
from gh.mods.motion import BUSY
import test_agents as TA
from test_arm import Bench, SPEC

SNIP = dict(SPEC["snip"], calibrated=True, closed_us=2400, open_us=700)
STOW = SPEC["poses"]["stow"]
CLOSED, OPEN = S.duty(2400, 50), S.duty(700, 50)


class Clock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t


class Pwm:
    def __init__(self): self.sent = []
    def set_pwm_output(self, channel, frequency, pin_val): self.sent.append((channel, frequency, pin_val))


class TestPulses(unittest.TestCase):
    def test_duty_is_the_pulse_over_the_period_in_256ths(self):
        self.assertEqual(S.duty(1500, 50), 19)                   # 1500 / 20000 * 256 = 19.2
        self.assertEqual(S.duty(2400, 50), 31)
        self.assertAlmostEqual(S.pulse_us(31, 50), 2421.9, places=1)
        self.assertAlmostEqual(S.pulse_us(1, 50), 78.1, places=1)   # the end connector's finest step

    def test_impossible_pulses_and_specs_are_caught(self):
        with self.assertRaises(ValueError):
            S.duty(250, 50)
        self.assertEqual(S.check_spec(SNIP), [])
        self.assertIn("same duty step", S.check_spec(dict(SNIP, open_us=2390))[0])
        self.assertIn("snip.pin", S.check_spec(dict(SNIP, pin=None))[0])
        self.assertIn("outside", S.check_spec(dict(SNIP, open_us=3000))[0])

    def test_jaw_states_follow_the_settle_time(self):
        mc, clock = Pwm(), Clock()
        jaw = S.Snip(mc, SNIP, clock)
        self.assertEqual(jaw.state(), "limp")                    # nothing sent: the servo is limp
        jaw.open()
        self.assertEqual((jaw.state(), mc.sent[-1]), ("opening", (22, 50, OPEN)))
        clock.t += SNIP["settle_s"]
        self.assertEqual(jaw.state(), "open")
        jaw.close()
        clock.t += SNIP["settle_s"]
        self.assertEqual((jaw.state(), mc.sent[-1]), ("closed", (22, 50, CLOSED)))
        jaw.limp()
        self.assertEqual((jaw.state(), mc.sent[-1]), ("limp", (22, 50, 0)))

    def test_the_stem_check_counts_what_is_nearer_than_the_empty_jaws(self):
        intr = {"fx": 640.0, "fy": 640.0, "cx": 640.0, "cy": 360.0, "width": 1280, "height": 720}
        view = SPEC["snip"]["stem_view"]
        u0, v0, u1, v1 = roi = S.jaw_roi(intr, view)
        self.assertTrue(u0 < 640 < u1 and 360 < v0 < v1)          # below the centre, on the centre column
        empty = np.zeros((720, 1280), np.float32)
        empty[v0:v1, u0:u1] = 0.110                                # the far jaw's inside face
        self.assertEqual(S.stem_present(empty, empty, roi, view)[0], False)
        stem = empty.copy()
        stem[v0:v1, 630:650] = 0.080                               # a 20 px wide stem at 80 mm
        present, n = S.stem_present(stem, empty, roi, view)
        self.assertTrue(present)
        self.assertEqual(n, 20 * (v1 - v0))


class TestArmJaw(Bench):
    def rig(self, taught=True, start=STOW, snip=SNIP):
        return super().rig(taught=taught, start=start, snip=snip)

    def test_release_only_from_the_fold(self):
        self.rig(start=SPEC["poses"]["look"])
        self.cmd("release")
        self.assertIn("release is from the stow pose", self.state()["error"])
        self.assertEqual(self.cobot.pwm, [])

    def test_release_opens_at_the_fold_and_closes_again(self):
        self.rig()
        self.cmd("release", rid="r")
        self.run_s(4)
        self.assertEqual(self.cobot.pwm, [(22, 50, OPEN), (22, 50, CLOSED)])
        self.assertEqual(self.cobot.sent, [])                       # no joint moves: only the jaw
        self.assertEqual((self.state()["pose"], self.stowed()), ("parked", "OK"))

    def test_no_pulses_reach_an_unpowered_arm(self):
        self.rig()
        self.cobot.powered = False
        self.cmd("cut")
        self.assertEqual(self.cobot.pwm, [])


class TestWhereTheCutGoes(TA.Robot):
    run_plant = TA.TestTender.run_plant
    tends = TA.TestTender.tends
    BASE = TA.TestTender.BASE

    def approved(self, action):
        r = self.run_plant(dict(self.BASE, action=action, candidate="C1"), authority="autonomous", stage=2)
        prop = self.tends(r)[0]
        r.bus.publish(T.proposal_decision(prop["id"]), "approve")
        r.run(240, step=1)
        return r, prop

    def test_a_pinched_tip_rides_folded_to_the_drawer(self):
        r, prop = self.approved("pinch")
        arm = [d["action"] for d in r.driven("arm")]
        self.assertEqual(arm[arm.index("approach"):], ["approach", "cut", "park", "release"])
        self.assertEqual([d["action"] for d in r.driven("gantry")][-2:], ["to_bin", "home"])
        rel = next(d for d in r.driven("arm") if d["action"] == "release")
        self.assertEqual((rel["task"], rel["position"]), (prop["id"], "A01"))
        self.assertEqual(r.bus.retained[BUSY], "OFF")
        self.assertEqual(r.bus.get(f"{T.ROOT}/arm/state")["pose"], "parked")
        journal = [json.loads(p) for t, p in r.bus.sent if t == T.log("tend")]
        self.assertEqual(journal[-1]["result"], "done")

    def test_the_bin_counts_its_pieces_and_a_full_bin_stops_the_next_harvest(self):
        r, _ = self.approved("pinch")
        self.assertEqual(r.bus.retained[f"{T.ROOT}/robot/bin"], "1")
        r.mods["motion"].bin_items = r.mods["motion"].config["bin_capacity"]
        r.bus.publish(T.SAFETY_REQUEST_UI, {"id": "t9", "actuator": "robot", "action": "tend",
                                             "value": "pinch C1", "position": "A01",
                                             "target": {"action": "pinch", "label": "C1", "kind": "tip",
                                                        "xyz_mm": [0, 0, 300]}})
        r.run(30, step=1)
        journal = [json.loads(p) for t, p in r.bus.sent if t == T.log("tend")]
        self.assertEqual(journal[-1]["result"], "stopped")
        self.assertIn("harvest drawer holds 40", journal[-1]["note"])
        r.bus.publish(T.cmd("motion"), {"op": "bin_emptied"})
        self.assertEqual(r.bus.retained[f"{T.ROOT}/robot/bin"], "0")

    def test_a_removed_leaf_goes_to_the_waste_spot_never_the_drawer(self):
        r, _ = self.approved("remove_leaf")
        self.assertIn("release", [d["action"] for d in r.driven("arm")])
        gantry = [d["action"] for d in r.driven("gantry")]
        self.assertIn("to_waste", gantry)
        self.assertNotIn("to_bin", gantry)
        self.assertNotIn(f"{T.ROOT}/robot/bin", r.bus.retained)            # nothing counted
        self.assertEqual(r.bus.get(f"{T.ROOT}/gantry/state")["at"], "home")


if __name__ == "__main__":
    unittest.main()
