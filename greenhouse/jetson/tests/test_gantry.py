"""The FluidNC gantry backend against an emulated controller on the serial link."""
import unittest
from unittest import mock

from fake_fluidnc import FakeFluidNC
from rig import Rig, T
from gh.mods import gantry as G
from gh.mods.arm import Arm
from gh.mods.d405 import D405
from gh.mods.esphome import EsphomeLink
from gh.mods.motion import BUSY, Motion
from gh.mods.perception import Perception

STATE = f"{T.ROOT}/gantry/state"


class Bench(unittest.TestCase):
    def rig(self, **fake):
        r = Rig()
        self.fake = FakeFluidNC(r.clock, **fake)
        self.links = [self.fake]
        patch = mock.patch.object(G, "SerialLink", side_effect=lambda port, baud: self._link())
        patch.start()
        self.addCleanup(patch.stop)
        r.ms["gantry"].config["backend"] = "fluidnc"
        self.g = r.add(G.Gantry, "gantry")
        r.bus.publish(f"{T.ROOT}/arm/state", {"pose": "parked", "busy": False}, retain=True)
        self.r = r
        return r

    def _link(self):
        if not self.links:
            raise OSError("no such device /dev/ttyUSB0")
        return self.links.pop(0)

    def cmd(self, action, position=None, rid="g"):
        self.r.bus.publish(T.actuator_set("gantry"), {"id": rid, "action": action, "position": position})

    def run_s(self, seconds, step=0.2):
        for _ in range(int(round(seconds / step))):
            self.r.clock.add(step)
            self.g.tick()

    def state(self):
        return self.r.bus.get(STATE)

    def homed(self):
        self.cmd("home")
        self.run_s(8)
        self.assertTrue(self.state()["homed"])


class TestFluidNC(Bench):
    def test_connects_and_needs_homing_before_a_plant_move(self):
        self.rig()
        self.run_s(1)
        self.assertEqual(self.fake.lines[0], "$I")
        self.assertEqual(self.state()["controller"], "Alarm")      # FluidNC locks until homed
        self.cmd("goto", "A01")
        self.assertEqual(self.state()["error"], "refused: not homed: send home first")
        self.assertNotIn("G53", " ".join(self.fake.lines))
        self.homed()
        self.assertEqual(self.fake.lines[-1], "$H")
        self.assertEqual((self.state()["at"], self.g.state), ("home", "running"))

    def test_goto_a_plant_in_machine_coordinates(self):
        self.rig()
        self.homed()
        self.cmd("goto", "B05")
        self.assertEqual(self.fake.lines[-1], "G53 G1 X534.000 Z820.000 F3000")
        self.run_s(1)
        s = self.state()
        self.assertTrue(s["busy"])
        self.assertEqual(self.r.bus.retained[T.interlock("gantry_still")], "OPEN")
        self.run_s(20)
        s = self.state()
        self.assertEqual((s["at"], s["busy"], s["x_mm"], s["z_mm"]), ("B05", False, 534, 820))
        self.assertEqual(self.r.bus.retained[T.interlock("gantry_still")], "OK")

    def test_home_when_homed_goes_to_park_without_rehoming(self):
        self.rig()
        self.homed()
        self.cmd("goto", "A07")
        self.run_s(30)
        n = self.fake.lines.count("$H")
        self.cmd("home")
        self.run_s(30)
        self.assertEqual(self.fake.lines.count("$H"), n)
        self.assertEqual(self.fake.lines[-1], "G53 G1 X0.000 Z0.000 F3000")
        self.assertEqual(self.state()["at"], "home")

    def test_refuses_targets_outside_the_travel(self):
        self.rig()
        self.homed()
        self.g.layout["plants"]["C10"] = 1500
        self.cmd("goto", "C10")
        self.assertIn("outside the travel", self.state()["error"])
        self.cmd("goto", "D01")
        self.assertIn("no coordinates for D01", self.state()["error"])

    def test_stop_holds_first_and_resets_only_once_stopped(self):
        self.rig()
        self.homed()
        self.cmd("goto", "C10")
        self.run_s(2)
        mark = len(self.fake.written)
        self.cmd("stop")
        self.assertIn(b"!", self.fake.written[mark:])
        self.assertNotIn(b"\x18", self.fake.written[mark:])        # still decelerating
        self.assertEqual(self.r.bus.retained[T.interlock("gantry_still")], "OPEN")
        self.run_s(1)
        self.assertIn(b"\x18", self.fake.written[mark:])
        self.assertNotIn("alarm", self.g.detail)                    # no alarm 3: position was not lost
        s = self.state()
        self.assertEqual((s["at"], s["homed"], s["busy"]), ("unknown", False, False))
        self.assertEqual(self.r.bus.retained[T.interlock("gantry_still")], "OK")
        self.cmd("goto", "A01")
        self.assertIn("not homed", self.state()["error"])

    def test_hard_limit_alarm_mid_move(self):
        self.rig()
        self.homed()
        self.cmd("goto", "C10")
        self.run_s(2)
        self.fake.hard_limit()
        self.run_s(1)
        s = self.state()
        self.assertEqual((s["at"], s["homed"]), ("unknown", False))
        self.assertIn("hard limit", s["error"])
        self.assertEqual(self.g.state, "fault")
        self.homed()                                                # homing clears it
        self.assertEqual(self.g.state, "running")

    def test_failed_homing(self):
        self.rig()
        self.fake.fail_homing = True
        self.cmd("home")
        self.run_s(8)
        s = self.state()
        self.assertFalse(s["homed"])
        self.assertIn("homing switch not found", s["error"])

    def test_controller_restart_mid_move(self):
        self.rig()
        self.homed()
        self.cmd("goto", "C10")
        self.run_s(2)
        self.fake.move, self.fake.state = None, "Alarm"
        self.fake.out += b"\r\nGrbl 3.7 [FluidNC v3.7.8 (noradio) '$' for help]\r\n"
        self.run_s(1)
        s = self.state()
        self.assertEqual((s["at"], s["homed"]), ("unknown", False))
        self.assertIn("lost its position", s["error"])

    def test_line_error_fails_the_move(self):
        self.rig()
        self.homed()
        self.fake.state = "Alarm"                                   # locked: the move line is refused
        self.cmd("goto", "A02")
        self.run_s(1)
        self.assertIn("error:9", self.state()["error"])
        self.assertEqual(self.state()["at"], "unknown")

    def test_unplugged_then_plugged_back(self):
        self.rig()
        self.homed()
        self.fake.plugged = False
        self.run_s(1)
        self.assertEqual(self.g.state, "fault")
        self.assertEqual(self.state()["controller"], "disconnected")
        self.cmd("goto", "A01")
        self.assertIn("not connected", self.state()["error"])
        self.run_s(12)                                              # retry finds no device
        self.assertEqual(self.g.state, "fault")
        self.links.append(FakeFluidNC(self.r.clock))
        self.run_s(11)
        self.assertEqual(self.g.state, "running")
        self.assertFalse(self.state()["homed"])                     # a new connection is never trusted

    def test_silent_controller_is_dropped(self):
        self.rig()
        self.fake.mute = True
        self.run_s(6)
        self.assertIn("has not answered", self.g.detail)

    def test_arm_out_is_refused_before_anything_is_sent(self):
        self.rig()
        self.r.bus.publish(f"{T.ROOT}/arm/state", {"pose": "at_plant", "busy": False}, retain=True)
        self.cmd("home")
        self.assertEqual(self.state()["error"], "refused: arm is not stowed")
        self.assertNotIn("$H", self.fake.lines)


class TestRouteOnFluidNC(Bench):
    def test_photo_route_on_the_emulated_controller(self):
        r = self.rig()
        r.add(EsphomeLink, "esphome")
        r.nodes.healthy()
        for p in ("A01", "C10"):
            r.plant(p)
        r.ms["d405"].config["backend"] = "sim"
        for cls, name in ((Arm, "arm"), (D405, "d405"), (Perception, "perception"), (Motion, "motion")):
            r.add(cls, name)
        r.bus.publish(T.cmd("motion"), {"op": "capture_route"})
        for _ in range(900):
            r.clock.add(0.2)
            for mod in r.mods.values():
                mod.tick()
            r.gov.tick()
            r.beat_all()
            if r.bus.retained[BUSY] == "OFF":
                break
        self.assertEqual(r.bus.retained[BUSY], "OFF", r.mods["motion"].detail)
        moves = [l for l in self.fake.lines if l.startswith(("G53", "$H"))]
        self.assertEqual(moves, ["$H", "G53 G1 X36.000 Z260.000 F3000", "G53 G1 X1194.000 Z1180.000 F3000",
                                 "G53 G1 X0.000 Z0.000 F3000"])
        for pos in ("A01", "C10"):
            self.assertTrue(r.bus.get(T.observation(pos))["candidates"])


if __name__ == "__main__":
    unittest.main()
