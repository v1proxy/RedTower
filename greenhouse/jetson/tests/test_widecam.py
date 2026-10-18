"""The overview camera: per-pot measurements on synthetic cabinet frames, the twice-daily
schedule, and the stress score's wilting and stalled-growth rules."""
import time
import unittest

from rig import Rig, T
from gh.mods import widecam as W

ROIS = {k: tuple(v) for k, v in W.load_rois()["regions"].items()}
DAY = 86400


def at(rig, hour, minute=0):
    """Move the rig clock to the next time the local clock shows hour:minute."""
    lt = time.localtime(rig.clock())
    rig.clock.add(((hour - lt.tm_hour) % 24) * 3600 + (minute - lt.tm_min) * 60 - lt.tm_sec)


class TestMeasure(unittest.TestCase):
    def test_canopy_grows_with_the_plant_and_an_empty_pot_is_empty(self):
        frame = W.draw_cabinet(ROIS, {"A01": {"size": 0.3}, "A02": {"size": 0.8}}, seed=1)
        small, big, empty = (W.measure(frame, ROIS[p]) for p in ("A01", "A02", "A03"))
        self.assertGreater(big["canopy_fraction"], small["canopy_fraction"] * 2)
        self.assertGreater(small["greenness"], 0.95)
        self.assertEqual(empty["canopy_fraction"], 0.0)                 # the pot itself is not plant
        self.assertEqual(W.stress(empty), (0, []))

    def test_yellowing_raises_stress(self):
        frame = W.draw_cabinet(ROIS, {"B01": {"size": 0.7}, "B02": {"size": 0.7, "yellow": True}}, seed=2)
        healthy, sick = W.measure(frame, ROIS["B01"]), W.measure(frame, ROIS["B02"])
        self.assertGreater(sick["yellow_fraction"], 0.1)
        self.assertLess(W.stress(healthy)[0], 10)
        score, flags = W.stress(sick)
        self.assertGreater(score, 30)
        self.assertIn("yellowing", flags)

    def test_wilting_and_a_stalled_week(self):
        m = {"canopy_fraction": 0.20, "greenness": 1.0, "yellow_fraction": 0.0}
        self.assertEqual(W.stress(m, morning=0.30), (25, ["wilting since the morning"]))
        self.assertEqual(W.stress(m, morning=0.21), (0, []))           # small dips are normal
        self.assertEqual(W.stress(m, week_ago=0.20), (15, ["no growth in a week"]))
        self.assertEqual(W.stress(m, week_ago=0.15), (0, []))


class TestModule(unittest.TestCase):
    def rig(self):
        r = Rig()
        for pos, kind in (("A01", "pepper"), ("B05", "basil")):
            r.plant(pos, kind)
        self.cam = r.add(W.Widecam, "widecam")
        return r

    def overviews(self, r):
        return [t for t, _ in r.bus.sent if t == T.photo("overview")]

    def test_captures_at_11_and_19_once_each(self):
        r = self.rig()
        at(r, 10, 50)
        r.run(3 * 3600, step=60)                                        # through 11:00
        self.assertEqual(len(self.overviews(r)), 1)
        at(r, 18, 50)
        r.run(2 * 3600, step=60)                                        # through 19:00
        self.assertEqual(len(self.overviews(r)), 2)
        v = r.bus.get(T.vision("A01"))
        self.assertEqual((v["slot"], v["plant"]), ("pm", "Compact pepper"))
        self.assertGreater(v["canopy_fraction"], 0)
        self.assertEqual(r.bus.get(T.vision("C10"))["canopy_fraction"], 0.0)
        self.assertEqual(len([t for t in r.bus.retained if t.startswith(f"{T.ROOT}/vision/")]), 27)
        self.assertIsInstance(r.bus.retained[T.photo("overview")], bytes)
        self.assertEqual(r.state("widecam"), "stub")

    def test_on_demand_capture_and_history_survives_a_restart(self):
        r = self.rig()
        at(r, 11, 0)
        r.run(60, step=60)
        r.bus.publish(T.cmd("widecam"), {"op": "capture"})
        r.run(60, step=60)
        self.assertEqual(len(self.overviews(r)), 2)
        again = W.Widecam(r.bus, r.ms["widecam"], r.clock)
        again.start()
        self.assertEqual(len(again.history["A01"]), 1)                  # the manual one is not history

    def test_unavailable_camera_is_a_fault(self):
        r = Rig()
        r.ms["widecam"].config["backend"] = "v4l2"
        r.ms["widecam"].config["device"] = "/dev/does-not-exist"
        cam = r.add(W.Widecam, "widecam")
        self.assertEqual(cam.state, "fault")
        cam.on_cmd({"op": "capture"})
        cam.tick()
        self.assertIn("capture failed", cam.detail)


if __name__ == "__main__":
    unittest.main()
