"""Tests for the module contract and the four core services, on the in-memory bus.
Run: python3 -m unittest discover -s tests -v   (from the jetson folder)"""
import atexit
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gh import topics as T                                    # noqa: E402
from gh.bus import MemoryBus, match                           # noqa: E402
from gh.core.bridge import Bridge                             # noqa: E402
from gh.core.safety import Governor                           # noqa: E402
from gh.core.store import Store, positions                    # noqa: E402
from gh.core.supervisor import Supervisor                     # noqa: E402
from gh.manifest import ManifestError, load_dir, parse, validate_set  # noqa: E402
from gh.module import Module                                  # noqa: E402
from gh.runtime import NullRuntime                            # noqa: E402

LIMITS = yaml.safe_load((ROOT / "config" / "limits.yaml").read_text())
SCRATCH = tempfile.mkdtemp(prefix="gh-tests-core-")
atexit.register(shutil.rmtree, SCRATCH, ignore_errors=True)
PROFILES = yaml.safe_load((ROOT / "config" / "profiles.yaml").read_text())


class Clock:
    def __init__(self): self.t = 1_000_000.0
    def __call__(self): return self.t
    def add(self, s): self.t += s


def all_installed():
    """The real manifests, treated as if every module were built."""
    ms = load_dir(ROOT / "modules")
    for m in ms.values():
        m.installed = True
    return ms


class Rig:
    """Supervisor, governor and store on one bus, with every module reporting healthy."""

    def __init__(self, authority="auto"):
        self.clock, self.bus, self.rt = Clock(), MemoryBus(), NullRuntime()
        self.ms = all_installed()
        self.tmp = tempfile.mkdtemp(dir=SCRATCH)
        self.sup = Supervisor(self.bus, self.ms, self.rt, Path(self.tmp) / "s.json", authority, self.clock)
        self.gov = Governor(self.bus, self.ms, LIMITS, self.clock)
        self.store = Store(self.bus, ":memory:", PROFILES, self.clock)
        self.sup.start(); self.gov.start(); self.store.start()
        self.beat_all()
        for lock in ("door", "estop", "water", "arm_stowed", "gantry_still"):
            self.bus.publish(T.interlock(lock), "OK", retain=True)

    def beat_all(self, skip=()):
        for name, m in self.ms.items():
            if name not in skip:
                self.bus.publish(T.health(name), {"alive": True, "state": "stub" if m.stub else "running"})

    def state(self, name):
        return self.bus.get(T.status(name))["state"]

    def ask(self, source, actuator, action, value=None, position=None, rid="r1", ui=False, **extra):
        topic = T.SAFETY_REQUEST_UI if ui else T.SAFETY_REQUEST
        self.bus.publish(topic, dict({"id": rid, "source": source, "actuator": actuator,
                                      "action": action, "value": value, "position": position}, **extra))
        verdicts = [json.loads(p) for t, p in self.bus.sent if t == T.verdict(rid)]
        return verdicts[-1]

    def driven(self, actuator):
        return [json.loads(p) for t, p in self.bus.sent if t == T.actuator_set(actuator)]


class TestBus(unittest.TestCase):
    def test_wildcards(self):
        self.assertTrue(match("greenhouse/+/health", "greenhouse/arm/health"))
        self.assertFalse(match("greenhouse/+/health", "greenhouse/arm/health/x"))
        self.assertTrue(match("greenhouse/log/#", "greenhouse/log/decision"))
        self.assertFalse(match("greenhouse/+/enable", "greenhouse/arm/enable/set"))

    def test_retained_delivered_to_late_subscriber(self):
        bus, got = MemoryBus(), []
        bus.publish("a/b", "1", retain=True)
        bus.subscribe("a/+", lambda t, p: got.append(p))
        self.assertEqual(got, ["1"])


class TestManifest(unittest.TestCase):
    def test_real_manifests_load_in_dependency_order(self):
        ms = load_dir(ROOT / "modules")
        order = validate_set(ms)
        self.assertEqual(len(ms), 17)
        self.assertLess(order.index("esphome"), order.index("climate"))
        self.assertLess(order.index("climate"), order.index("envagent"))

    def test_rejects_bad_manifests(self):
        base = {"name": "x1", "title": "X", "layer": "service"}
        with self.assertRaises(ManifestError): parse(dict(base, layer="wrong"))
        with self.assertRaises(ManifestError): parse(dict(base, name="Bad Name"))
        with self.assertRaises(ManifestError): parse(dict(base, surprise=1))
        with self.assertRaises(ManifestError): parse({"name": "x1", "layer": "core"})
        with self.assertRaises(ManifestError):
            validate_set({"x1": parse(dict(base, depends=["ghost"]))})

    def test_rejects_cycle(self):
        a = parse({"name": "aa", "title": "A", "layer": "service", "depends": ["bb"]})
        b = parse({"name": "bb", "title": "B", "layer": "service", "depends": ["aa"]})
        with self.assertRaises(ManifestError): validate_set({"aa": a, "bb": b})

    def test_core_may_not_depend_on_a_module(self):
        c = parse({"name": "cc", "title": "C", "layer": "core", "depends": ["dd"]})
        d = parse({"name": "dd", "title": "D", "layer": "driver"})
        with self.assertRaises(ManifestError): validate_set({"cc": c, "dd": d})


class TestModuleContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["GH_DATA_DIR"] = self.tmp.name
        self.bus, self.clock = MemoryBus(), Clock()
        self.m = parse({"name": "demo", "title": "Demo", "layer": "service", "config": {"gain": 1}})
        self.mod = Module(self.bus, self.m, self.clock)
        self.mod.start()

    def test_heartbeat_and_config(self):
        self.assertTrue(json.loads(self.bus.sent[-1][1])["alive"])
        self.bus.publish(T.config_set("demo"), {"gain": 3, "nope": 9})
        self.assertEqual(self.bus.get(T.config("demo")), {"gain": 3})
        before = len(self.bus.sent)
        self.clock.add(11); self.mod.tick()
        self.assertGreater(len(self.bus.sent), before)

    def test_config_survives_a_restart(self):
        self.bus.publish(T.config_set("demo"), {"gain": 3})
        again = Module(self.bus, self.m, self.clock)
        self.assertEqual(again.config, {"gain": 3})
        newer = parse({"name": "demo", "title": "Demo", "layer": "service", "config": {"rate": 2}})
        self.assertEqual(Module(self.bus, newer, self.clock).config, {"rate": 2})   # dropped key is ignored

    def test_disabled_module_ignores_commands(self):
        seen = []
        self.mod.on_cmd = seen.append
        self.bus.publish(T.enable("demo"), "OFF", retain=True)
        self.bus.publish(T.cmd("demo"), {"op": "go"})
        self.assertEqual(seen, [])
        self.bus.publish(T.enable("demo"), "ON", retain=True)
        self.bus.publish(T.cmd("demo"), {"op": "go"})
        self.assertEqual(seen, [{"op": "go"}])


class TestSupervisor(unittest.TestCase):
    def test_first_power_up(self):
        r = Rig()
        self.assertEqual(r.state("climate"), "running")
        self.assertEqual(r.state("nutrients"), "disabled")
        self.assertEqual(r.state("envagent"), "paused")       # authority is auto
        self.assertFalse(r.rt.running["envagent"])
        self.assertTrue(r.rt.running["climate"])

    def test_disabling_a_driver_degrades_dependents_down_the_chain(self):
        r = Rig("proposes")
        self.assertEqual(r.state("tender"), "running")
        r.bus.publish(T.enable_set("d405"), "OFF")
        self.assertEqual(r.state("d405"), "disabled")
        self.assertEqual(r.state("perception"), "degraded")
        self.assertEqual(r.state("tender"), "degraded")
        self.assertEqual(r.state("climate"), "running")
        self.assertFalse(r.rt.running["d405"])
        r.bus.publish(T.enable_set("d405"), "ON")
        self.assertEqual(r.state("tender"), "running")

    def test_core_cannot_be_disabled(self):
        r = Rig()
        r.bus.publish(T.enable_set("safety"), "OFF")
        self.assertEqual(r.state("safety"), "running")
        self.assertTrue(r.rt.running["safety"])
        self.assertEqual(r.bus.retained[T.enable("safety")], "ON")

    def test_authority_off_stops_everything_above_core(self):
        r = Rig("proposes")
        r.bus.publish(T.AUTHORITY_SET, "off")
        self.assertEqual(r.state("climate"), "stopped")
        self.assertEqual(r.state("arm"), "stopped")
        self.assertEqual(r.state("store"), "running")
        self.assertFalse(r.rt.running["climate"])

    def test_kill_switch_halts_agents_only(self):
        r = Rig("autonomous")
        r.bus.publish(T.KILL_SET, "ON")
        for agent in ("envagent", "tender", "llm"):
            self.assertEqual(r.state(agent), "halted")
            self.assertFalse(r.rt.running[agent])
        self.assertEqual(r.state("irrigation"), "running")

    def test_silent_module_goes_offline(self):
        r = Rig()
        r.clock.add(31)
        r.beat_all(skip=("esphome",))
        r.sup.tick()
        self.assertEqual(r.state("esphome"), "offline")
        self.assertEqual(r.state("climate"), "degraded")

    def test_last_will_marks_offline(self):
        r = Rig()
        r.bus.publish(T.health("esphome"), {"alive": False}, retain=True)
        self.assertEqual(r.state("esphome"), "offline")

    def test_state_survives_restart(self):
        r = Rig()
        r.bus.publish(T.enable_set("widecam"), "OFF")
        r.bus.publish(T.AUTHORITY_SET, "manual")
        again = Supervisor(MemoryBus(), r.ms, NullRuntime(), r.sup.path, "auto", r.clock)
        self.assertFalse(again.enabled["widecam"])
        self.assertEqual(again.authority, "manual")

    def test_uninstalled_module_reports_missing(self):
        bus = MemoryBus()
        ms = load_dir(ROOT / "modules")
        ms["nutrients"].installed = False                       # declared, code not built
        ms["nutrients"].default_enabled = True
        with tempfile.TemporaryDirectory() as d:
            rt = NullRuntime()
            Supervisor(bus, ms, rt, Path(d) / "s.json").start()
        self.assertEqual(bus.get(T.status("nutrients"))["state"], "missing")
        self.assertFalse(rt.running["nutrients"])


class TestGovernor(unittest.TestCase):
    def test_service_within_limits_drives_actuator(self):
        r = Rig()
        self.assertEqual(r.ask("irrigation", "water_a", "run", 20)["result"], "approved")
        self.assertEqual(r.driven("water_a")[-1]["value"], 20)

    def test_range_and_hourly_cap(self):
        r = Rig()
        self.assertEqual(r.ask("irrigation", "water_a", "run", 181)["result"], "denied")
        for i in range(3):
            self.assertEqual(r.ask("irrigation", "water_a", "run", 60, rid=f"a{i}")["result"], "approved")
        self.assertEqual(r.ask("irrigation", "water_b", "run", 60, rid="b0")["result"], "approved")
        v = r.ask("irrigation", "water_a", "run", 5, rid="a4")
        self.assertEqual(v["result"], "denied")
        self.assertIn("hourly", v["reason"])
        r.clock.add(3601)
        self.assertEqual(r.ask("irrigation", "water_a", "run", 30, rid="a5")["result"], "approved")
        self.assertEqual(len(r.driven("water_a")), 4)
        self.assertEqual(len(r.driven("water_b")), 1)

    def test_value_must_be_a_number(self):
        r = Rig()
        for bad in (None, "20", True):
            self.assertEqual(r.ask("irrigation", "water_a", "run", bad)["result"], "denied")

    def test_module_may_only_use_its_own_actuators(self):
        r = Rig()
        self.assertEqual(r.ask("climate", "water_a", "run", 5)["result"], "denied")
        self.assertEqual(r.ask("ghost", "water_a", "run", 5)["result"], "denied")
        self.assertEqual(r.ask("irrigation", "laser", "fire", 1)["result"], "denied")

    def test_disabled_module_is_denied(self):
        r = Rig()
        r.bus.publish(T.enable_set("irrigation"), "OFF")
        self.assertEqual(r.ask("irrigation", "water_a", "run", 5)["result"], "denied")

    def test_a_module_cannot_pose_as_the_interface(self):
        r = Rig("manual")
        self.assertEqual(r.ask("ui", "water_a", "run", 5)["result"], "denied")
        self.assertEqual(r.ask("anything", "water_a", "run", 5, rid="u1", ui=True)["result"], "approved")

    def test_manual_blocks_services_but_allows_off(self):
        r = Rig("manual")
        self.assertEqual(r.ask("irrigation", "water_a", "run", 5)["result"], "denied")
        self.assertEqual(r.ask("irrigation", "water", "stop")["result"], "approved")

    def test_off_denies_even_the_interface_except_safe_off(self):
        r = Rig("off")
        r.bus.publish(T.enable(  "irrigation"), "ON", retain=True)
        self.assertEqual(r.ask("x", "water_a", "run", 5, ui=True)["result"], "denied")
        self.assertEqual(r.ask("x", "water", "stop", rid="r2", ui=True)["result"], "approved")

    def test_agent_proposal_then_approval(self):
        r = Rig("proposes")
        v = r.ask("envagent", "water_a", "run", 20)
        self.assertEqual(v["result"], "proposed")
        self.assertEqual(r.driven("water_a"), [])
        self.assertEqual(r.bus.retained[T.SAFETY_PENDING], "1")
        r.bus.publish(T.proposal_decision("r1"), "approve")
        self.assertEqual(r.driven("water_a")[-1]["value"], 20)
        self.assertEqual(r.bus.retained[T.SAFETY_PENDING], "0")
        self.assertNotIn(T.proposal("r1"), r.bus.retained)

    def test_rejected_and_expired_proposals_never_run(self):
        r = Rig("proposes")
        r.ask("envagent", "water_a", "run", 20)
        r.bus.publish(T.proposal_decision("r1"), "reject")
        r.ask("envagent", "water_a", "run", 20, rid="r2")
        r.clock.add(25 * 3600); r.gov.tick()
        r.bus.publish(T.proposal_decision("r2"), "approve")
        self.assertEqual(r.driven("water_a"), [])

    def test_approval_is_rechecked_against_current_conditions(self):
        r = Rig("proposes")
        r.bus.publish(T.STORE_CMD_UI, {"op": "replace_plant", "position": "A01", "type": "basil"})
        self.assertEqual(r.ask("tender", "robot", "tend", "pinch C1", "A01")["result"], "proposed")
        r.bus.publish(T.interlock("door"), "OPEN", retain=True)
        r.bus.publish(T.proposal_decision("r1"), "approve")
        self.assertEqual(r.driven("robot"), [])

    def test_autonomous_runs_agent_requests_but_cutting_still_needs_approval(self):
        r = Rig("autonomous")
        r.bus.publish(T.STORE_CMD_UI, {"op": "replace_plant", "position": "A01", "type": "basil"})
        self.assertEqual(r.ask("envagent", "water_a", "run", 20)["result"], "approved")
        self.assertEqual(r.ask("tender", "robot", "tend", "pinch C1", "A01", rid="c1")["result"], "proposed")
        self.assertEqual(r.driven("robot"), [])
        self.assertIn("not allowed to use arm", r.ask("tender", "arm", "cut", "C1", "A01", rid="c2")["reason"])

    def test_arm_actions_need_a_live_grant_from_an_approved_tend_task(self):
        r = Rig("auto")
        for pos in ("A01", "B03"):
            r.bus.publish(T.STORE_CMD_UI, {"op": "replace_plant", "position": pos, "type": "basil"})
        self.assertIn("needs an approved tend task", r.ask("motion", "arm", "cut", "C1", "A01", rid="x")["reason"])
        self.assertEqual(r.ask("ui", "robot", "tend", "pinch C1", "A01", rid="t1", ui=True)["result"], "approved")
        self.assertEqual(r.driven("robot")[-1]["position"], "A01")
        self.assertEqual(r.ask("motion", "arm", "approach", "C2", "A01", rid="a1", task="t1")["result"], "approved")
        self.assertIn("already done", r.ask("motion", "arm", "approach", "C2", "A01", rid="a2", task="t1")["reason"])
        self.assertIn("is for A01", r.ask("motion", "arm", "cut", "C2", "B03", rid="k0", task="t1")["reason"])
        self.assertEqual(r.ask("motion", "arm", "cut", "C2", "A01", rid="k1", task="t1")["result"], "approved")
        self.assertEqual(r.driven("arm")[-1]["task"], "t1")                 # the task travels to the arm
        self.assertIn("already done", r.ask("motion", "arm", "cut", "C2", "A01", rid="k2", task="t1")["reason"])
        r.ask("ui", "robot", "tend", "pinch C1", "A01", rid="t2", ui=True)
        r.clock.add(16 * 60)
        self.assertEqual(r.ask("motion", "arm", "cut", "C1", "A01", rid="k3", task="t2")["result"], "denied")
        r.gov.tick()
        self.assertNotIn("t2", r.gov.grants)

    def test_kill_switch_denies_agents(self):
        r = Rig("autonomous")
        r.bus.publish(T.KILL_SET, "ON")
        v = r.ask("envagent", "water_a", "run", 20)
        self.assertEqual((v["result"], v["reason"]), ("denied", "kill switch is on"))
        self.assertEqual(r.ask("irrigation", "water_a", "run", 20, rid="s1")["result"], "approved")

    def test_agents_denied_when_authority_is_auto(self):
        r = Rig("auto")
        self.assertEqual(r.ask("envagent", "water_a", "run", 20)["result"], "denied")

    def test_interlocks_fail_safe(self):
        r = Rig()
        r.bus.publish(T.interlock("door"), "OPEN", retain=True)
        self.assertEqual(r.ask("motion", "gantry", "home")["result"], "denied")
        fresh = Rig()
        fresh.gov.interlocks.clear()                           # never heard from the interlock
        self.assertEqual(fresh.ask("motion", "gantry", "home")["result"], "denied")
        self.assertEqual(fresh.ask("motion", "gantry", "stop", rid="s")["result"], "approved")

    def test_gantry_needs_the_arm_stowed_and_the_arm_a_still_gantry(self):
        r = Rig()
        r.bus.publish(T.interlock("arm_stowed"), "OPEN", retain=True)
        self.assertIn("arm_stowed", r.ask("motion", "gantry", "home")["reason"])
        self.assertEqual(r.ask("motion", "gantry", "stop", rid="s")["result"], "approved")
        r.bus.publish(T.STORE_CMD_UI, {"op": "replace_plant", "position": "A01", "type": "basil"})
        r.bus.publish(T.interlock("gantry_still"), "OPEN", retain=True)
        self.assertIn("gantry_still", r.ask("motion", "arm", "capture", None, "A01", rid="c")["reason"])
        self.assertEqual(r.ask("motion", "arm", "park", rid="p")["result"], "approved")

    def test_proposals_wait_for_interlocks_until_they_are_approved(self):
        r = Rig("proposes")
        r.bus.publish(T.interlock("water"), "OPEN", retain=True)
        self.assertEqual(r.ask("envagent", "water_a", "run", 20)["result"], "proposed")
        self.assertEqual(r.ask("irrigation", "water_a", "run", 20, rid="s1")["result"], "denied")   # runs now
        r.bus.publish(T.proposal_decision("r1"), "approve")
        self.assertEqual(r.driven("water_a"), [])                  # still open when approved: denied
        r.bus.publish(T.interlock("water"), "OK", retain=True)
        r.ask("envagent", "water_a", "run", 20, rid="r2")
        r.bus.publish(T.proposal_decision("r2"), "approve")
        self.assertEqual(r.driven("water_a")[-1]["value"], 20)

    def test_arm_needs_a_confirmed_living_plant(self):
        r = Rig()
        self.assertEqual(r.ask("motion", "arm", "capture", None, "A01")["result"], "denied")
        r.bus.publish(T.STORE_CMD_UI, {"op": "replace_plant", "position": "A01", "type": "basil"})
        self.assertEqual(r.ask("motion", "arm", "capture", None, "A01", rid="b")["result"], "approved")
        r.bus.publish(T.cmd("store"), {"op": "mark", "position": "A01", "status": "dead"})
        self.assertEqual(r.ask("motion", "arm", "capture", None, "A01", rid="c")["result"], "denied")

    def test_governor_denies_before_it_hears_the_authority(self):
        bus = MemoryBus()
        gov = Governor(bus, all_installed(), LIMITS, Clock())
        gov.start()
        bus.publish(T.enable("irrigation"), "ON", retain=True)
        bus.publish(T.SAFETY_REQUEST, {"id": "z", "source": "irrigation", "actuator": "water_a",
                                       "action": "run", "value": 5})
        self.assertFalse([1 for t, _ in bus.sent if t == T.actuator_set("water_a")])

    def test_nutrient_stub_can_never_dose(self):
        r = Rig()
        r.bus.publish(T.enable_set("nutrients"), "ON")
        self.assertEqual(r.ask("nutrients", "dosing", "dose", 1)["result"], "denied")

    def test_every_verdict_is_logged(self):
        r = Rig()
        r.ask("irrigation", "water_a", "run", 20)
        r.ask("irrigation", "water_a", "run", 999, rid="r2")
        self.assertEqual([d["result"] for _, d in r.store.recent("decision")], ["denied", "approved"])


class TestStore(unittest.TestCase):
    def setUp(self):
        self.bus, self.clock = MemoryBus(), Clock()
        self.store = Store(self.bus, ":memory:", PROFILES, self.clock)
        self.store.start()

    def test_starts_with_27_empty_positions(self):
        self.assertEqual(len(positions()), 27)
        p = self.bus.get(T.plant("C10"))
        self.assertEqual((p["status"], p["type_confirmed"]), ("empty", False))

    def test_only_the_user_sets_a_plant_type(self):
        self.bus.publish(T.cmd("store"), {"op": "replace_plant", "position": "A01", "type": "basil", "source": "ui"})
        self.assertFalse(self.bus.get(T.plant("A01"))["type_confirmed"])
        self.bus.publish(T.STORE_CMD_UI, {"op": "replace_plant", "position": "A01", "type": "Basil"})
        p = self.bus.get(T.plant("A01"))
        self.assertEqual((p["scientific"], p["profile"], p["stage"]), ("Ocimum basilicum", "ready", 0))

    def test_unknown_type_is_accepted_with_profile_pending(self):
        self.bus.publish(T.STORE_CMD_UI, {"op": "replace_plant", "position": "A02", "type": "shiso"})
        p = self.bus.get(T.plant("A02"))
        self.assertEqual((p["type_confirmed"], p["profile"], p["common"]), (True, "pending", "shiso"))

    def test_growth_stage_and_ready_to_pick(self):
        self.bus.publish(T.STORE_CMD_UI, {"op": "replace_plant", "position": "A01", "type": "pepper"})
        self.bus.publish(T.cmd("store"), {"op": "set_stage", "position": "A01", "stage": 4})
        self.assertEqual(self.bus.get(T.plant("A01"))["status"], "ready")
        self.bus.publish(T.cmd("store"), {"op": "set_stage", "position": "A01", "stage": 9})
        self.assertEqual(self.bus.get(T.plant("A01"))["stage"], 4)

    def test_replacing_resets_growth_and_clears_dead(self):
        self.bus.publish(T.STORE_CMD_UI, {"op": "replace_plant", "position": "A01", "type": "pepper"})
        self.bus.publish(T.cmd("store"), {"op": "set_stage", "position": "A01", "stage": 3})
        self.bus.publish(T.cmd("store"), {"op": "mark", "position": "A01", "status": "dead"})
        self.bus.publish(T.cmd("store"), {"op": "set_stage", "position": "A01", "stage": 4})
        self.assertEqual(self.bus.get(T.plant("A01"))["status"], "dead")
        self.bus.publish(T.STORE_CMD_UI, {"op": "replace_plant", "position": "A01", "type": "thyme"})
        p = self.bus.get(T.plant("A01"))
        self.assertEqual((p["status"], p["stage"], p["common"]), ("ok", 0, "Thyme"))

    def test_cannot_stage_an_empty_position(self):
        self.bus.publish(T.cmd("store"), {"op": "set_stage", "position": "B02", "stage": 1})
        self.bus.publish(T.cmd("store"), {"op": "mark", "position": "B02", "status": "ready"})
        self.assertEqual(self.bus.get(T.plant("B02"))["status"], "empty")


class TestBridge(unittest.TestCase):
    def test_discovery(self):
        bus, ms = MemoryBus(), load_dir(ROOT / "modules")
        Bridge(bus, ms).start()
        cfg = {t: json.loads(p) for t, p in bus.retained.items() if t.startswith("homeassistant/")}
        ids = [c["unique_id"] for c in cfg.values()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn("homeassistant/switch/greenhouse_safety_enabled/config", cfg)
        self.assertIn("homeassistant/switch/greenhouse_nutrients_enabled/config", cfg)
        self.assertEqual(cfg["homeassistant/binary_sensor/greenhouse_envagent_alive/config"]["expire_after"], 45)
        self.assertEqual(cfg["homeassistant/sensor/greenhouse_envagent_last_cycle/config"]["expire_after"], 2700)
        self.assertEqual(len([t for t in cfg if "/greenhouse_plant_" in t]), 27)
        self.assertEqual(len([t for t in cfg if t.startswith("homeassistant/camera/")]), 83)
        self.assertEqual(len([t for t in cfg if "/greenhouse_vision_" in t]), 27)
        self.assertEqual(cfg["homeassistant/select/greenhouse_authority/config"]["options"],
                         ["off", "manual", "auto", "proposes", "autonomous"])
        before = len(bus.sent)
        bus.publish(T.HA_STATUS, "online")
        self.assertGreater(len(bus.sent), before + 50)

    def test_every_entity_names_its_own_id(self):
        """Home Assistant 2026 ignores object_id and would derive "switch.greenhouse_agent_kill_switch"
        from the name; default_entity_id keeps the id the package and the panel use."""
        bus = MemoryBus()
        Bridge(bus, load_dir(ROOT / "modules")).start()
        for topic, payload in bus.retained.items():
            if topic.startswith("homeassistant/"):
                c, kind = json.loads(payload), topic.split("/")[1]
                self.assertEqual(c["default_entity_id"], f"{kind}.{c['object_id']}")
        kill = json.loads(bus.retained["homeassistant/switch/greenhouse_kill/config"])
        self.assertEqual(kill["default_entity_id"], "switch.greenhouse_kill")


if __name__ == "__main__":
    unittest.main()
