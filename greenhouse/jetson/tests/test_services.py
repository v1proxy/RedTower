"""ESPHome link, climate and irrigation against simulated nodes."""
import time
import unittest

from rig import Rig, SimNodes, T
from gh.mods.climate import Climate
from gh.mods.esphome import EsphomeLink
from gh.mods.irrigation import Irrigation


def at_hour(rig, hour):
    """Move the rig clock to the next time the local clock shows this hour."""
    lt = time.localtime(rig.clock())
    rig.clock.add(((hour - lt.tm_hour) % 24) * 3600 - lt.tm_min * 60 - lt.tm_sec)


class TestEsphomeLink(unittest.TestCase):
    def test_no_data_means_interlocks_unknown_and_fault(self):
        r = Rig()
        link = r.add(EsphomeLink, "esphome")
        self.assertEqual(link.state, "fault")
        self.assertEqual(r.bus.retained[T.interlock("door")], "UNKNOWN")
        self.assertEqual(r.state("climate"), "degraded")

    def test_healthy_nodes(self):
        r = Rig()
        r.add(EsphomeLink, "esphome")
        r.nodes.healthy()
        for lock in ("door", "estop", "water"):
            self.assertEqual(r.bus.retained[T.interlock(lock)], "OK")
        self.assertEqual(r.bus.get(T.sensor("tier_a_vpd"))["v"], 1.0)
        self.assertEqual(r.state("esphome"), "running")

    def test_fahrenheit_is_converted(self):
        r = Rig()
        r.add(EsphomeLink, "esphome")
        SimNodes(r.bus, fahrenheit=True).healthy(temp_c=25.0)
        v = r.bus.get(T.sensor("tier_b_air_temperature"))
        self.assertAlmostEqual(v["v"], 25.0, places=1)
        self.assertEqual(v["unit"], "°C")

    def test_unit_arriving_after_state_still_converts(self):
        r = Rig()
        r.add(EsphomeLink, "esphome")
        r.bus.publish(f"{T.HA_STATE}/sensor/greenhouse_tier_a_air_temperature/state", "77.0")
        r.bus.publish(f"{T.HA_STATE}/sensor/greenhouse_tier_a_air_temperature/unit_of_measurement", '"°F"')
        self.assertAlmostEqual(r.bus.get(T.sensor("tier_a_air_temperature"))["v"], 25.0, places=1)

    def test_door_leak_and_offline_node(self):
        r = Rig()
        link = r.add(EsphomeLink, "esphome")
        r.nodes.healthy()
        r.nodes.set("binary_sensor", "utility_doors", "on")
        self.assertEqual(r.bus.retained[T.interlock("door")], "OPEN")
        r.nodes.set("binary_sensor", "utility_leak_lockout", "on")
        self.assertEqual(r.bus.retained[T.interlock("water")], "OPEN")
        r.nodes.set("binary_sensor", "utility_safety_circuit_tripped", "unavailable")
        self.assertEqual(r.bus.retained[T.interlock("estop")], "UNKNOWN")
        r.nodes.set("binary_sensor", "tier_b_status", "off")
        self.assertIn("tier_b", link.detail)
        self.assertEqual(r.state("esphome"), "fault")
        self.assertIsNone(r.bus.get(T.sensor("utility_safety_circuit_tripped"))["v"])

    def test_silent_mirror_drops_the_interlocks(self):
        r = Rig()
        link = r.add(EsphomeLink, "esphome")
        r.nodes.healthy()
        self.assertIn(("greenhouse/esphome/refresh", "1"), r.bus.sent)
        r.mirror = False
        r.run(600)
        self.assertEqual(r.bus.retained[T.interlock("door")], "OK")
        r.run(600)
        self.assertEqual(r.bus.retained[T.interlock("door")], "UNKNOWN")
        self.assertIn("silent", link.detail)
        r.bus.publish(f"{T.HA_STATE}/heartbeat", "1")
        r.run(60)
        self.assertEqual(r.bus.retained[T.interlock("door")], "OK")

    def test_ignores_entities_outside_the_greenhouse(self):
        r = Rig()
        r.add(EsphomeLink, "esphome")
        r.bus.publish(f"{T.HA_STATE}/sensor/living_room_temperature/state", "21")
        self.assertFalse([t for t in r.bus.retained if "living_room" in t and "/sensor/" in t and t.startswith("greenhouse/sensor")])


class Services(unittest.TestCase):
    def rig(self, **kw):
        r = Rig()
        r.add(EsphomeLink, "esphome")
        r.nodes.healthy(**kw)
        return r


class TestClimate(Services):
    def test_pushes_light_settings_once(self):
        r = self.rig()
        r.add(Climate, "climate")
        r.run(300)
        self.assertEqual([d["value"] for d in r.driven("light_a") if d["action"] == "photoperiod"], [16])
        self.assertEqual(len(r.driven("light_c")), 2)

    def test_in_band_does_nothing(self):
        r = self.rig(vpd=1.1)
        r.add(Climate, "climate")
        r.run(3600)
        self.assertEqual(r.driven("humidifier"), [])
        self.assertEqual(r.driven("exhaust"), [])

    def test_dry_air_humidifies_with_a_gap(self):
        r = self.rig(vpd=1.5)
        r.add(Climate, "climate")
        r.run(3600)
        runs = r.driven("humidifier")
        self.assertEqual(len(runs), 3)                      # 20 minute gap
        self.assertTrue(all(d["value"] == 5 for d in runs))

    def test_governor_caps_humidifier_per_hour(self):
        r = self.rig(vpd=1.5)
        c = r.add(Climate, "climate")
        r.bus.publish(T.config_set("climate"), {"humidify_minutes": 15, "humidify_gap_min": 10})
        r.run(3600)
        self.assertEqual(sum(d["value"] for d in r.driven("humidifier")), 30)
        self.assertTrue(any("hourly" in v["reason"] for v in r.verdicts("climate")))
        self.assertEqual(c.config["humidify_minutes"], 15)

    def test_humid_air_boosts_exhaust_then_restores(self):
        r = self.rig(vpd=0.6)
        r.add(Climate, "climate")
        r.run(300)
        self.assertEqual([d["value"] for d in r.driven("exhaust")], [50])
        r.nodes.healthy(vpd=1.0)
        r.run(300)
        self.assertEqual([d["value"] for d in r.driven("exhaust")], [50, 25])

    def test_no_reading_is_a_fault_and_no_action(self):
        r = Rig()
        r.add(EsphomeLink, "esphome")
        c = r.add(Climate, "climate")
        r.run(300)
        self.assertEqual(c.state, "fault")
        self.assertEqual(r.driven("humidifier"), [])

    def test_agent_setpoint_reaches_climate_only_through_governor(self):
        r = self.rig()
        c = r.add(Climate, "climate")
        r.bus.publish(T.AUTHORITY_SET, "autonomous")
        r.bus.publish(T.SAFETY_REQUEST, {"id": "e1", "source": "envagent", "actuator": "climate_setpoint",
                                         "action": "vpd_target", "value": 1.3})
        self.assertEqual(c.config["vpd_target"], 1.3)
        r.bus.publish(T.SAFETY_REQUEST, {"id": "e2", "source": "envagent", "actuator": "climate_setpoint",
                                         "action": "vpd_target", "value": 3.0})
        self.assertEqual(c.config["vpd_target"], 1.3)

    def test_approved_setpoint_survives_a_restart(self):
        r = self.rig()
        r.add(Climate, "climate")
        r.bus.publish(T.AUTHORITY_SET, "autonomous")
        r.bus.publish(T.SAFETY_REQUEST, {"id": "e1", "source": "envagent", "actuator": "climate_setpoint",
                                         "action": "vpd_target", "value": 1.3})
        again = Climate(r.bus, r.ms["climate"], r.clock)
        self.assertEqual(again.config["vpd_target"], 1.3)

    def test_denied_light_setting_is_asked_again(self):
        r = Rig("manual")                       # the governor refuses services in manual
        r.add(EsphomeLink, "esphome")
        r.nodes.healthy()
        r.add(Climate, "climate")
        r.run(120)
        self.assertEqual(r.driven("light_a"), [])
        r.bus.publish(T.AUTHORITY_SET, "auto")
        r.run(120)
        self.assertEqual([d["value"] for d in r.driven("light_a") if d["action"] == "photoperiod"], [16])

    def test_request_lost_at_cold_start_is_asked_again(self):
        r = self.rig()
        c = r.add(Climate, "climate")
        real = r.bus.publish                    # the governor is not listening yet: requests vanish
        r.bus.publish = lambda t, p, retain=False: None if t == T.SAFETY_REQUEST else real(t, p, retain)
        r.run(60)
        self.assertEqual(r.driven("light_a"), [])
        r.bus.publish = real
        r.run(180)
        self.assertEqual([d["value"] for d in r.driven("light_a") if d["action"] == "photoperiod"], [16])
        self.assertEqual(c.inflight, {})

    def test_no_fault_while_the_first_readings_arrive(self):
        r = Rig()
        r.add(EsphomeLink, "esphome")
        c = r.add(Climate, "climate")
        r.run(30, step=5)
        self.assertEqual(c.state, "running")
        r.nodes.healthy()
        r.run(10, step=5)
        self.assertIn("VPD 1.00", c.detail)


class TestIrrigation(Services):
    def test_waters_dry_tier_once_per_hour_in_window(self):
        r = self.rig(moisture=30)
        at_hour(r, 9)
        r.add(Irrigation, "irrigation")
        r.run(3 * 3600 + 900)
        self.assertEqual([d["value"] for d in r.driven("water_a")], [120, 120, 120, 120])
        self.assertEqual([d["value"] for d in r.driven("water_b")], [60, 60, 60, 60])

    def test_wet_soil_is_left_alone(self):
        r = self.rig(moisture=60)
        at_hour(r, 9)
        r.add(Irrigation, "irrigation")
        r.run(7200)
        self.assertEqual(r.driven("water_a"), [])

    def test_never_at_night(self):
        r = self.rig(moisture=10)
        at_hour(r, 22)
        r.add(Irrigation, "irrigation")
        r.run(3 * 3600)
        self.assertEqual(r.driven("water_a"), [])

    def test_leak_blocks_watering_at_the_governor(self):
        r = self.rig(moisture=10)
        at_hour(r, 9)
        r.nodes.set("binary_sensor", "utility_leak_detected", "on")
        r.add(Irrigation, "irrigation")
        r.run(3600)
        self.assertEqual(r.driven("water_a"), [])
        self.assertTrue(all(v["result"] == "denied" for v in r.verdicts("irrigation")))

    def test_waits_for_the_robot(self):
        r = self.rig(moisture=10)
        at_hour(r, 9)
        r.bus.publish(f"{T.ROOT}/robot/busy", "ON", retain=True)
        r.add(Irrigation, "irrigation")
        r.run(1800)
        self.assertEqual(r.driven("water_a"), [])
        r.bus.publish(f"{T.ROOT}/robot/busy", "OFF", retain=True)
        r.run(900)
        self.assertEqual(len(r.driven("water_a")), 1)

    def test_disabled_module_does_not_water(self):
        r = self.rig(moisture=10)
        at_hour(r, 9)
        r.add(Irrigation, "irrigation")
        r.bus.publish(T.enable_set("irrigation"), "OFF")
        r.run(3600)
        self.assertEqual(r.driven("water_a"), [])

    def test_config_change_applies_at_once(self):
        r = self.rig(moisture=30)
        at_hour(r, 22)
        r.add(Irrigation, "irrigation")
        r.run(60)
        self.assertEqual(r.driven("water_a"), [])
        r.bus.publish(T.config_set("irrigation"), {"end_hour": 24})
        r.run(60)
        self.assertEqual(len(r.driven("water_a")), 1)

    def test_no_fault_while_the_first_readings_arrive(self):
        r = Rig()
        r.add(EsphomeLink, "esphome")
        at_hour(r, 9)
        m = r.add(Irrigation, "irrigation")
        r.run(30, step=5)
        self.assertEqual(m.state, "running")
        r.nodes.healthy(moisture=30)
        r.run(10, step=5)
        self.assertEqual(len(r.driven("water_a")), 1)       # watered within seconds, not 15 minutes

    def test_missing_reading_on_all_tiers_is_a_fault(self):
        r = Rig()
        r.add(EsphomeLink, "esphome")
        at_hour(r, 9)
        m = r.add(Irrigation, "irrigation")
        r.run(900)
        self.assertEqual(m.state, "fault")


if __name__ == "__main__":
    unittest.main()
