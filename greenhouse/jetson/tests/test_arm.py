"""The myCobot backend of the arm driver against a simulated arm with pymycobot's interface."""
import copy
import unittest
from unittest import mock

from rig import Rig, T
from gh.mods import arm as A
from gh.mods.mycobot import SimCobot

STATE = f"{T.ROOT}/arm/state"
SPEC = A.load_spec()
STOW, LOOK = SPEC["poses"]["stow"], SPEC["poses"]["look"]


class FaultyCobot(SimCobot):
    """SimCobot plus the ways a real arm on a network goes wrong."""

    def __init__(self, clock, start=STOW):
        super().__init__(clock, move_s=3.0, start=start)
        self.sent, self.dropped, self.garbage, self.stuck, self.short = [], False, False, False, False

    def _net(self):
        if self.dropped:
            raise ConnectionResetError("connection reset by peer")

    def send_angles(self, angles, speed):
        self._net()
        self.sent.append((list(angles), speed))
        if self.short:                                       # collision detection: stops halfway
            self.angles = [a / 2 for a in angles]
            return
        super().send_angles(angles, speed)
        if self.stuck:
            self.until = float("inf")

    def get_angles(self):
        self._net()
        return -1 if self.garbage else super().get_angles()

    def is_moving(self):
        self._net()
        return super().is_moving()


class Bench(unittest.TestCase):
    def rig(self, taught=True, start=STOW):
        r = Rig()
        spec = copy.deepcopy(SPEC)
        spec["taught"] = taught
        self.cobots = [FaultyCobot(r.clock, start)]
        for target, kw in ((A, dict(load_spec=lambda: spec)),
                           (A.mycobot, dict(connect=lambda host, port: self._next()))):
            patch = mock.patch.multiple(target, **kw)
            patch.start()
            self.addCleanup(patch.stop)
        r.ms["arm"].config["backend"] = "mycobot"
        self.cobot = self.cobots[0]
        self.arm = r.add(A.Arm, "arm")
        r.bus.publish(f"{T.ROOT}/gantry/state", {"at": "A01", "busy": False}, retain=True)
        self.r = r
        return r

    def _next(self):
        if not self.cobots:
            raise ConnectionRefusedError("no server on 192.168.10.25:9000")
        return self.cobots.pop(0)

    def cmd(self, action, position="A01", rid="a"):
        self.r.bus.publish(T.actuator_set("arm"), {"id": rid, "action": action, "position": position})

    def run_s(self, seconds, step=0.5):
        for _ in range(int(round(seconds / step))):
            self.r.clock.add(step)
            self.arm.tick()

    def state(self):
        return self.r.bus.get(STATE)

    def stowed(self):
        return self.r.bus.retained[T.interlock("arm_stowed")]


class TestMyCobot(Bench):
    def test_untaught_poses_never_move_the_arm(self):
        self.rig(taught=False)
        self.assertEqual(self.arm.state, "fault")
        self.assertIn("not taught", self.arm.detail)
        for action in ("park", "capture"):
            self.cmd(action)
        self.assertEqual(self.cobot.sent, [])
        self.assertEqual(self.state()["error"], "refused: arm.yaml poses are not taught")

    def test_capture_goes_to_look_then_asks_the_camera(self):
        r = self.rig()
        self.assertEqual((self.state()["pose"], self.stowed()), ("parked", "OK"))
        self.cmd("capture")
        self.assertEqual(self.cobot.sent[-1], (LOOK, SPEC["speed"]))
        self.assertEqual((self.state()["pose"], self.stowed()), ("moving", "OPEN"))
        self.run_s(4)
        self.assertEqual(self.state()["pose"], "at_plant")
        self.assertIn((T.cmd("d405"), '{"op": "capture", "position": "A01", "id": "a"}'), r.bus.sent)
        self.cmd("park", rid="p")
        self.run_s(4)
        self.assertEqual((self.state()["pose"], self.stowed()), ("parked", "OK"))

    def test_an_arm_that_starts_out_of_the_lane_blocks_the_gantry(self):
        self.rig(start=LOOK)
        self.assertEqual((self.state()["pose"], self.stowed()), ("at_plant", "OPEN"))
        self.cmd("park")
        self.run_s(4)
        self.assertEqual(self.stowed(), "OK")

    def test_servos_off_is_not_parked(self):
        self.rig()
        self.cobot.powered = False
        self.run_s(3)
        self.assertEqual((self.state()["pose"], self.stowed()), ("unknown", "OPEN"))

    def test_connection_lost_then_back(self):
        self.rig()
        self.cobot.dropped = True
        self.run_s(1)
        self.assertEqual((self.state()["pose"], self.stowed(), self.arm.state), ("unknown", "OPEN", "fault"))
        self.cmd("park")
        self.assertEqual(self.state()["error"], "refused: arm not connected")
        self.run_s(11)                                       # first retry: server not up yet
        self.assertEqual(self.arm.state, "fault")
        self.cobots.append(FaultyCobot(self.r.clock))
        self.run_s(11)
        self.assertEqual((self.state()["pose"], self.stowed(), self.arm.state), ("parked", "OK", "running"))

    def test_garbage_joint_reads(self):
        self.rig()
        self.cobot.garbage = True
        self.run_s(0.5)
        self.assertEqual(self.arm.state, "running")         # one bad read is tolerated
        self.run_s(1.5)
        self.assertIn("no joint angles", self.arm.detail)
        self.assertEqual(self.stowed(), "OPEN")

    def test_stopped_short_and_timed_out(self):
        self.rig()
        self.cobot.short = True
        self.cmd("capture")
        self.run_s(3)
        self.assertIn("stopped short", self.state()["error"])
        self.assertEqual(self.stowed(), "OPEN")
        self.cobot.short, self.cobot.stuck = False, True
        self.cmd("park", rid="p")
        self.run_s(35)
        self.assertIn("park timed out", self.state()["error"])

    def test_approach_and_cut_wait_for_the_real_sequence(self):
        self.rig()
        for action in ("approach", "cut"):
            self.cmd(action)
            self.assertEqual(self.state()["error"], f"refused: {action} is not built for the real arm yet")
        self.assertEqual(self.cobot.sent, [])

    def test_refuses_to_leave_the_lane_away_from_the_plant(self):
        self.rig()
        self.cmd("capture", position="B03")
        self.assertIn("not at B03", self.state()["error"])
        self.r.bus.publish(f"{T.ROOT}/gantry/state", {"at": "moving", "busy": True}, retain=True)
        self.cmd("capture")
        self.assertEqual(self.state()["error"], "refused: gantry is moving")
        self.assertEqual(self.cobot.sent, [])


if __name__ == "__main__":
    unittest.main()
