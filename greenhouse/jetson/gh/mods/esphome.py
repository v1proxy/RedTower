"""ESPHome link (driver). The four ESPHome nodes talk to Home Assistant, and Home Assistant
mirrors their states to MQTT (mqtt_statestream). This module turns that mirror into clean
sensor topics in SI units, derives the safety interlocks, and watches that the nodes are up.

Commands go the other way without passing through here: the governor publishes
greenhouse/actuator/<x>/set and a Home Assistant automation calls the ESPHome action."""
from .. import topics as T
from ..bus import loads
from ..module import Module

NODES = ("tier_a", "tier_b", "tier_c", "utility")
OFFLINE = (None, "unavailable", "unknown", "")
STALE_S = 900        # Home Assistant resyncs every 5 minutes; three missed means the mirror is dead


class EsphomeLink(Module):
    def setup(self):
        self.raw, self.units, self.locks = {}, {}, {}
        self.last_seen = None
        self.bus.subscribe(f"{T.HA_STATE}/heartbeat", lambda t, p: setattr(self, "last_seen", self.clock()))
        self.bus.publish(f"{T.ROOT}/esphome/refresh", "1")           # ask Home Assistant for a full copy
        self.bus.subscribe(f"{T.HA_STATE}/+/+/state", self._on_state)
        self.bus.subscribe(f"{T.HA_STATE}/+/+/unit_of_measurement", self._on_unit)
        self._evaluate()

    @staticmethod
    def _key(topic):
        obj = topic.split("/")[3]
        return obj[len("greenhouse_"):] if obj.startswith("greenhouse_") else None

    def _on_unit(self, topic, payload):
        key = self._key(topic)
        if key:
            self.units[key] = loads(payload, payload)
            if key in self.raw:
                self._publish(key)

    def _on_state(self, topic, payload):
        key = self._key(topic)
        if key:
            self.last_seen = self.clock()
            self.raw[key] = payload.strip()
            self._publish(key)
            self._evaluate()

    def _publish(self, key):
        raw, unit = self.raw[key], self.units.get(key)
        value = None
        if raw not in OFFLINE:
            try:
                value = float(raw)
                if unit in ("°F", "°F"):                 # Home Assistant shows imperial here
                    value, unit = round((value - 32) / 1.8, 2), "°C"
            except ValueError:
                value = raw
        self.bus.publish(T.sensor(key), {"v": value, "unit": unit, "ts": self.clock()}, retain=True)

    def loop(self):
        self._evaluate()

    def _is(self, key, state):
        return self.raw.get(key) == state

    def _evaluate(self):
        def lock(name, ok, known):
            value = "UNKNOWN" if not known else ("OK" if ok else "OPEN")
            if self.locks.get(name) != value:
                self.locks[name] = value
                self.bus.publish(T.interlock(name), value, retain=True)

        r = self.raw
        fresh = self.last_seen is None or self.clock() - self.last_seen <= STALE_S
        known = lambda *keys: fresh and all(r.get(k) not in OFFLINE for k in keys)      # noqa: E731
        lock("door", self._is("utility_doors", "off"), known("utility_doors"))
        lock("estop", self._is("utility_safety_circuit_tripped", "off"), known("utility_safety_circuit_tripped"))
        water = ("utility_leak_detected", "utility_leak_lockout", "utility_reservoir_low_float",
                 "utility_safety_circuit_tripped")
        lock("water", all(self._is(k, "off") for k in water), known(*water))

        down = [n for n in NODES if not self._is(f"{n}_status", "on")]
        if not self.raw:
            state, detail = "fault", "no data from Home Assistant yet"
        elif not fresh:
            state, detail = "fault", "Home Assistant mirror has gone silent"
        elif down:
            state, detail = "fault", "nodes offline: " + ", ".join(down)
        else:
            state, detail = "running", ""
        if (state, detail) != (self.state, self.detail):
            self.report(state, detail)
