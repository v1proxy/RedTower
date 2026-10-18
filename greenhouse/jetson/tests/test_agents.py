"""Motion, depth camera, perception, LLM gateway, environment agent and plant tender,
all in simulation with a scripted stand-in for the language model."""
import json
import time
import unittest

from rig import Rig, T
from gh.mods.arm import Arm
from gh.mods.climate import Climate
from gh.mods.d405 import D405
from gh.mods.envagent import OUTPUT as ENV_OUT, EnvAgent
from gh.mods.esphome import EsphomeLink
from gh.mods.gantry import Gantry
from gh.mods.llm import LlmGateway
from gh.mods.motion import BUSY, Motion
from gh.mods.perception import Perception, analyse
from gh.mods.simscene import make_scene
from gh.mods.tender import OUTPUT as TENDER_OUT, Tender


def tool_reply(payload, tokens=900):
    return {"content": [{"type": "tool_use", "name": "x", "input": payload}],
            "usage": {"input_tokens": tokens, "output_tokens": 100}}


class Robot(unittest.TestCase):
    def rig(self, authority="auto", plants=("A01", "B03")):
        r = Rig(authority)
        r.add(EsphomeLink, "esphome")
        r.nodes.healthy()
        for p in plants:
            r.plant(p)
        r.ms["d405"].config["backend"] = "sim"
        for cls, name in ((Gantry, "gantry"), (Arm, "arm"), (D405, "d405"), (Perception, "perception"), (Motion, "motion")):
            r.add(cls, name)
        self.llm = r.add(LlmGateway, "llm")
        self.llm.api_key = "test-key"
        self.bodies = []
        return r

    def script(self, *replies):
        replies = list(replies)

        def transport(body, key):
            self.bodies.append(body)
            item = replies.pop(0) if len(replies) > 1 else replies[0]
            if isinstance(item, Exception):
                raise item
            return item
        self.llm.transport = transport


class TestMotionAndPerception(Robot):
    def test_photo_route_visits_every_living_plant_and_goes_home(self):
        r = self.rig()
        r.bus.publish(T.cmd("store"), {"op": "mark", "position": "B03", "status": "dead"})
        r.plant("C10")
        r.bus.publish(T.cmd("motion"), {"op": "capture_route"})
        self.assertEqual(r.bus.retained[BUSY], "ON")
        r.run(120, step=1)
        self.assertEqual(r.bus.retained[BUSY], "OFF")
        self.assertEqual([d["position"] for d in r.driven("gantry") if d["action"] == "goto"], ["A01", "C10"])
        self.assertEqual(r.bus.get(f"{T.ROOT}/gantry/state")["at"], "home")
        for pos in ("A01", "C10"):
            obs = r.bus.get(T.observation(pos))
            self.assertGreater(len(obs["candidates"]), 0)
            self.assertIsInstance(r.bus.retained[T.photo(pos)], bytes)
            self.assertIsInstance(r.bus.retained[T.photo(pos) + "/history"], bytes)
        self.assertIsInstance(r.bus.retained[f"{T.ROOT}/live/d405"], bytes)
        self.assertNotIn(T.observation("B03"), r.bus.retained)

    def test_arm_is_parked_at_every_gantry_move(self):
        r = self.rig(plants=("A01", "B03", "C10"))
        r.bus.publish(T.cmd("motion"), {"op": "capture_route"})
        r.run(120, step=1)
        self.assertEqual(r.bus.retained[BUSY], "OFF")
        arm, moves = "parked", 0
        for topic, payload in r.bus.sent:
            if topic == f"{T.ROOT}/arm/state":
                arm = json.loads(payload)["pose"]
            elif topic == T.actuator_set("gantry") and json.loads(payload)["action"] in ("goto", "home"):
                moves += 1
                self.assertEqual(arm, "parked")
        self.assertEqual(moves, 5)                          # homing, three plants, home
        self.assertEqual(r.bus.get(f"{T.ROOT}/arm/state")["pose"], "parked")

    def test_drivers_refuse_on_their_own(self):
        r = self.rig()
        r.bus.publish(T.actuator_set("arm"), {"id": "a1", "action": "capture", "position": "A01"})
        self.assertIn("not at A01", r.bus.get(f"{T.ROOT}/arm/state")["error"])     # gantry never went there
        r.bus.publish(f"{T.ROOT}/arm/state", {"pose": "at_plant", "busy": False}, retain=True)
        r.bus.publish(T.actuator_set("gantry"), {"id": "g1", "action": "goto", "position": "A01"})
        g = r.bus.get(f"{T.ROOT}/gantry/state")
        self.assertEqual((g["busy"], g["error"]), (False, "refused: arm is not stowed"))
        r.bus.publish(f"{T.ROOT}/arm/state", {"pose": "parked", "busy": False}, retain=True)
        r.bus.publish(T.actuator_set("gantry"), {"id": "g2", "action": "goto", "position": "A01"})
        self.assertEqual(r.bus.get(f"{T.ROOT}/gantry/state")["error"], "refused: not homed: send home first")
        r.bus.publish(T.actuator_set("gantry"), {"id": "g3", "action": "home"})
        r.run(4, step=1)
        self.assertTrue(r.bus.get(f"{T.ROOT}/gantry/state")["homed"])
        r.bus.publish(T.actuator_set("gantry"), {"id": "g4", "action": "goto", "position": "A01"})
        self.assertTrue(r.bus.get(f"{T.ROOT}/gantry/state")["busy"])
        r.bus.publish(T.actuator_set("arm"), {"id": "a2", "action": "capture", "position": "A01"})
        self.assertEqual(r.bus.get(f"{T.ROOT}/arm/state")["error"], "refused: gantry is moving")

    def test_route_waits_for_a_real_park(self):
        r = self.rig()
        arm = r.mods["arm"]
        arm.mc.angles = list(arm.spec["poses"]["look"])     # the arm is out
        arm.refresh()
        arm.enabled = False                                 # and will not answer the park
        r.bus.publish(T.cmd("motion"), {"op": "capture_route"})
        r.run(30, step=1)
        self.assertEqual([d for d in r.driven("gantry") if d["action"] == "goto"], [])
        r.run(120, step=1)
        self.assertEqual(r.bus.retained[BUSY], "OFF")
        self.assertIn("timed out on park", r.mods["motion"].detail)

    def test_route_ends_when_a_driver_refuses(self):
        r = self.rig()
        r.bus.publish(T.cmd("motion"), {"op": "capture_route"})
        for _ in range(20):                                 # park, home, then on its way to A01
            r.run(1, step=1)
            if r.mods["motion"].step and r.mods["motion"].step[0] == "goto":
                break
        step = r.mods["motion"].step
        self.assertEqual(step[0], "goto")
        r.bus.publish(f"{T.ROOT}/gantry/state", {"at": "unknown", "busy": False, "id": step[2],
                                                "error": "refused: arm is not stowed"}, retain=True)
        self.assertEqual(r.bus.retained[BUSY], "OFF")
        self.assertIn("refused by the driver", r.mods["motion"].detail)

    def test_camera_backend_switches_without_a_restart(self):
        r = Rig()
        r.ms["d405"].config["backend"] = "realsense"
        cam = r.add(D405, "d405")
        self.assertEqual(cam.state, "fault")            # no RealSense SDK on the test machine
        r.bus.publish(T.config_set("d405"), {"backend": "sim"})
        self.assertEqual(cam.state, "stub")
        self.assertEqual(r.state("d405"), "stub")       # shown as simulated, though the manifest is not a stub
        cam.on_cmd({"op": "capture", "position": "A01"})
        cam.tick()
        self.assertIn(f"{T.ROOT}/capture/A01", [t for t, _ in r.bus.sent])

    def test_open_door_ends_the_route(self):
        r = self.rig()
        r.bus.publish(T.cmd("motion"), {"op": "capture_route"})
        r.run(4, step=1)
        r.nodes.set("binary_sensor", "utility_doors", "on")
        r.run(60, step=1)
        self.assertEqual(r.bus.retained[BUSY], "OFF")
        self.assertIn("refused", r.mods["motion"].detail)
        self.assertEqual(r.driven("gantry")[-1]["action"], "stop")
        self.assertNotIn(T.observation("B03"), r.bus.retained)

    def test_daily_route_starts_once_at_the_capture_hour(self):
        r = self.rig()
        lt = time.localtime(r.clock())
        r.clock.add(((9 - lt.tm_hour) % 24) * 3600 - lt.tm_min * 60 - lt.tm_sec - 30)
        r.run(3600, step=1)
        self.assertEqual(len([d for d in r.driven("arm") if d["action"] == "capture"]), 2)

    def test_irrigation_sees_robot_busy(self):
        r = self.rig()
        r.bus.publish(T.cmd("motion"), {"op": "visit", "position": "A01"})
        self.assertEqual(r.bus.retained[BUSY], "ON")

    def test_perception_numbers_grow_with_the_plant(self):
        small, _ = analyse(*make_scene(seed=3, stage=0))
        big, _ = analyse(*make_scene(seed=3, stage=3))
        self.assertGreater(big["height_mm"], small["height_mm"] * 2)
        self.assertGreater(big["canopy_area_cm2"], small["canopy_area_cm2"])
        json.dumps(big)                                             # must be plain JSON

    def test_perception_flags_yellow_leaf_and_empty_pot(self):
        obs, _ = analyse(*make_scene(seed=1, stage=3, yellow_leaf=True))
        self.assertIn("yellow_leaf", [c["kind"] for c in obs["candidates"]])
        self.assertGreater(obs["yellow_fraction"], 0.03)
        empty, _ = analyse(*make_scene(empty=True))
        self.assertEqual((empty["candidates"], empty["quality"]), ([], ["no plant found"]))

    def test_soil_is_not_counted_as_plant(self):
        obs, _ = analyse(*make_scene(empty=True))
        self.assertEqual(obs["plant_pixels"], 0)

    def test_candidates_carry_real_depth(self):
        obs, _ = analyse(*make_scene(seed=2, stage=2))
        for c in obs["candidates"]:
            self.assertTrue(200 <= c["xyz_mm"][2] <= 280, c)
        labels = [c["label"] for c in obs["candidates"]]
        self.assertEqual(labels, [f"C{i}" for i in range(1, len(labels) + 1)])

    def test_resolution_does_not_change_the_measurement(self):
        import cv2
        color, depth, intr = make_scene(seed=4, stage=2)
        a, _ = analyse(color, depth, intr)
        big = {k: v * 2 for k, v in intr.items()}
        b, _ = analyse(cv2.resize(color, (1280, 960)), cv2.resize(depth, (1280, 960), interpolation=cv2.INTER_NEAREST), big)
        self.assertAlmostEqual(a["height_mm"], b["height_mm"], delta=4)


class TestGateway(Robot):
    def ask(self, r, job_id="j1", **kw):
        r.bus.publish(T.cmd("llm"), dict(id=job_id, user="hello", **kw))
        r.run(1, step=1)
        return [json.loads(p) for t, p in r.bus.sent if t == f"{T.ROOT}/llm/reply/{job_id}"][-1]

    def test_gateway_needs_agent_authority(self):
        r = self.rig("auto")
        self.assertEqual(r.state("llm"), "paused")

    def test_structured_answer_and_request_shape(self):
        r = self.rig("proposes")
        self.script(tool_reply({"a": 1}))
        out = self.ask(r, tool={"name": "x", "description": "d", "input_schema": {"type": "object"}})
        self.assertEqual((out["ok"], out["tool_input"]), (True, {"a": 1}))
        body = self.bodies[0]
        self.assertEqual(body["tool_choice"], {"type": "tool", "name": "x"})
        self.assertEqual(body["model"], "claude-sonnet-5-5")

    def test_missing_structured_answer_is_an_error(self):
        r = self.rig("proposes")
        self.script({"content": [{"type": "text", "text": "sorry"}], "usage": {}})
        self.assertFalse(self.ask(r, tool={"name": "x", "description": "d", "input_schema": {}})["ok"])

    def test_no_key_network_failure_and_budget(self):
        r = self.rig("proposes")
        self.script(OSError("network unreachable"))
        self.assertIn("API call failed", self.ask(r)["error"])
        self.assertEqual(self.llm.state, "fault")
        self.script(tool_reply({}, tokens=399_950))
        self.assertTrue(self.ask(r, "j2")["ok"])
        self.assertIn("budget", self.ask(r, "j3")["error"])
        self.assertEqual(len(self.bodies), 2)                       # the third call never left
        r.clock.add(86400)
        self.assertTrue(self.ask(r, "j4")["ok"])                     # new day, budget reset
        self.llm.api_key = ""
        self.assertIn("no API key", self.ask(r, "j5")["error"])

    def test_hourly_call_limit(self):
        r = self.rig("proposes")
        self.script(tool_reply({}, tokens=1))
        self.llm.config["calls_per_hour"] = 2
        self.assertTrue(self.ask(r, "a")["ok"]); self.assertTrue(self.ask(r, "b")["ok"])
        self.assertIn("hourly", self.ask(r, "c")["error"])


class TestEnvAgent(Robot):
    def start(self, authority, decision):
        r = self.rig(authority)
        r.add(Climate, "climate")
        self.script(tool_reply(decision) if isinstance(decision, dict) else decision)
        self.agent = r.add(EnvAgent, "envagent")
        r.run(5, step=1)
        return r

    def test_proposes_mode_queues_actions_for_approval(self):
        r = self.start("proposes", {"assessment": "Tier A is dry.", "note": "A dries fastest",
                                    "actions": [{"type": "water", "tier": "a", "value": 60, "why": "median 28%"}]})
        self.assertEqual(r.driven("water_a"), [])
        out = r.bus.get(ENV_OUT)
        self.assertEqual((out["text"], out["actions"][0]["result"]), ("Tier A is dry.", "proposed"))
        prop = r.bus.get(T.PROPOSALS)[0]
        self.assertEqual((prop["actuator"], prop["value"], prop["reason_given"]), ("water_a", 60, "median 28%"))
        r.bus.publish(T.proposal_decision(prop["id"]), "approve")
        self.assertEqual(r.driven("water_a")[0]["value"], 60)
        self.assertIn(T.cycle("envagent"), r.bus.retained)

    def test_autonomous_mode_acts_within_limits_only(self):
        r = self.start("autonomous", {"assessment": "ok", "note": "", "actions": [
            {"type": "set_vpd_target", "value": 1.2, "why": "flowering"},
            {"type": "water", "tier": "b", "value": 900, "why": "too much"},
            {"type": "open_roof", "value": 1, "why": "invented"},
            {"type": "water", "value": 30, "why": "no tier"}]})
        self.assertEqual(r.mods["climate"].config["vpd_target"], 1.2)
        self.assertEqual(r.driven("water_b"), [])
        results = [a["result"] for a in r.bus.get(ENV_OUT)["actions"]]
        self.assertEqual(results, ["approved", "denied", "ignored", "ignored"])

    def test_prompt_carries_readings_and_notes_persist(self):
        r = self.start("autonomous", {"assessment": "ok", "note": "remember this", "actions": []})
        sent = self.bodies[0]["messages"][0]["content"][-1]["text"]
        self.assertIn('"vpd": 1.0', sent)
        r.run(1920, step=60)
        self.assertIn("remember this", self.bodies[1]["messages"][0]["content"][-1]["text"])
        self.assertEqual(len(self.bodies), 2)                       # one call per 30 minutes

    def test_llm_failure_reports_fault_and_no_cycle(self):
        r = self.start("autonomous", OSError("down"))
        self.assertEqual(self.agent.state, "fault")
        self.assertTrue(r.bus.get(ENV_OUT)["failed"])
        self.assertNotIn(T.cycle("envagent"), r.bus.retained)

    def test_kill_switch_blocks_an_agent_that_is_still_running(self):
        r = self.start("autonomous", {"assessment": "x", "note": "", "actions": []})
        r.bus.publish(T.KILL_SET, "ON")
        self.agent.request("water_a", "run", 30)
        self.assertEqual(r.driven("water_a"), [])
        self.assertEqual(r.verdicts("envagent")[-1]["reason"], "kill switch is on")
        self.assertFalse(r.rt.running["envagent"])


class TestTender(Robot):
    def run_plant(self, answer, authority="proposes", stage=None, scene=None):
        r = self.rig(authority, plants=("A01",))
        if stage is not None:
            r.bus.publish(T.cmd("store"), {"op": "set_stage", "position": "A01", "stage": stage})
        self.script(tool_reply(answer) if isinstance(answer, dict) else answer)
        r.add(Tender, "tender")
        r.bus.publish(T.cmd("motion"), {"op": "capture_route"})
        r.run(60, step=1)
        return r

    BASE = {"stage_index": 2, "status": "ok", "note": "Healthy.", "action": "none", "confidence": 0.9}

    def test_stage_and_status_are_written(self):
        r = self.run_plant(dict(self.BASE, stage_index=3, status="ready"))
        p = r.bus.get(T.plant("A01"))
        self.assertEqual((p["stage"], p["status"]), (3, "ready"))
        body = self.bodies[0]
        self.assertEqual(body["messages"][0]["content"][0]["type"], "image")
        self.assertIn("Ocimum basilicum", body["messages"][0]["content"][1]["text"])

    def tends(self, r):
        return [p for p in r.bus.get(T.PROPOSALS) if (p["actuator"], p["action"]) == ("robot", "tend")]

    def test_cut_is_only_ever_a_proposal_even_in_autonomous(self):
        r = self.run_plant(dict(self.BASE, action="pinch", candidate="C1"), authority="autonomous", stage=2)
        self.assertEqual([d for d in r.driven("arm") if d["action"] == "cut"], [])
        prop = self.tends(r)[0]
        self.assertEqual((prop["value"], prop["position"], prop["target"]["label"]), ("pinch C1", "A01", "C1"))
        self.assertEqual(len(prop["target"]["xyz_mm"]), 3)
        self.assertEqual(r.bus.get(T.plant("A01"))["status"], "attention")

    def test_approved_cut_goes_back_finds_the_leaf_again_and_cuts_once(self):
        r = self.run_plant(dict(self.BASE, action="pinch", candidate="C1"), authority="autonomous", stage=2)
        prop = self.tends(r)[0]
        captures = len([t for t, _ in r.bus.sent if t == f"{T.ROOT}/capture/A01"])
        r.bus.publish(T.proposal_decision(prop["id"]), "approve")
        r.run(120, step=1)
        cuts = [d for d in r.driven("arm") if d["action"] == "cut"]
        self.assertEqual(len(cuts), 1)
        self.assertEqual((cuts[0]["task"], cuts[0]["position"]), (prop["id"], "A01"))
        self.assertTrue(cuts[0]["value"].startswith("C"))                # the label in the new capture
        self.assertEqual(len([t for t, _ in r.bus.sent if t == f"{T.ROOT}/capture/A01"]), captures + 1)
        self.assertEqual(r.bus.retained[BUSY], "OFF")
        self.assertEqual(r.bus.get(f"{T.ROOT}/gantry/state")["at"], "home")
        self.assertEqual(r.bus.get(f"{T.ROOT}/arm/state")["pose"], "parked")
        journal = [json.loads(p) for t, p in r.bus.sent if t == T.log("tend")]
        self.assertEqual(journal[-1]["result"], "done")
        r.bus.publish(T.SAFETY_REQUEST, {"id": "again", "source": "motion", "actuator": "arm", "action": "cut",
                                         "value": "C1", "position": "A01", "task": prop["id"]})
        self.assertIn("already done", r.verdicts("motion")[-1]["reason"])   # one approval, one cut

    def test_a_leaf_that_is_gone_is_not_cut(self):
        r = self.run_plant(dict(self.BASE, action="pinch", candidate="C1"), authority="autonomous", stage=2)
        prop = self.tends(r)[0]
        r.gov.proposals[prop["id"]]["target"]["xyz_mm"] = [300.0, 300.0, 300.0]   # nothing there now
        r.bus.publish(T.proposal_decision(prop["id"]), "approve")
        r.run(120, step=1)
        self.assertEqual([d for d in r.driven("arm") if d["action"] in ("approach", "cut")], [])
        journal = [json.loads(p) for t, p in r.bus.sent if t == T.log("tend")]
        self.assertEqual(journal[-1]["result"], "stopped")
        self.assertIn("not found again", journal[-1]["note"])
        self.assertEqual(r.bus.retained[BUSY], "OFF")

    def test_invented_label_is_not_proposed_and_reaches_the_owner(self):
        r = self.run_plant(dict(self.BASE, action="remove_leaf", candidate="C99"), stage=2)
        self.assertFalse(self.tends(r))
        self.assertEqual(r.bus.get(T.plant("A01"))["status"], "attention")
        self.assertIn("not a drawn candidate", r.bus.get(TENDER_OUT)["note"])

    def test_low_confidence_and_seedlings_are_not_cut(self):
        r = self.run_plant(dict(self.BASE, action="pinch", candidate="C1", confidence=0.5), stage=2)
        self.assertFalse(self.tends(r))
        r = self.run_plant(dict(self.BASE, stage_index=0, action="pinch", candidate="C1"))
        self.assertFalse(self.tends(r))
        self.assertIn("seedling", r.bus.get(TENDER_OUT)["note"])

    def test_out_of_range_stage_is_ignored(self):
        r = self.run_plant(dict(self.BASE, stage_index=42), stage=1)
        self.assertEqual(r.bus.get(T.plant("A01"))["stage"], 1)

    def test_tender_never_changes_the_plant_type_or_marks_dead(self):
        r = self.run_plant(dict(self.BASE, status="dead", note="looks dead"))
        p = r.bus.get(T.plant("A01"))
        self.assertEqual((p["type"], p["status"]), ("basil", "attention"))

    def test_llm_down_skips_without_touching_the_plant(self):
        r = self.run_plant(OSError("down"), stage=1)
        self.assertEqual(r.bus.get(T.plant("A01"))["stage"], 1)
        self.assertEqual(r.bus.get(TENDER_OUT)["result"], "skipped")


if __name__ == "__main__":
    unittest.main()
