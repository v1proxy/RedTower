"""Read access to the normalised sensor values published by the ESPHome link."""
from . import topics as T
from .bus import loads

TIERS = ("a", "b", "c")


class Sensors:
    def __init__(self, bus):
        self.values = {}
        bus.subscribe(f"{T.ROOT}/sensor/+", self._on)

    def _on(self, topic, payload):
        data = loads(payload, {})
        self.values[topic.split("/")[-1]] = data.get("v") if isinstance(data, dict) else None

    def num(self, key):
        v = self.values.get(key)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    def text(self, key):
        v = self.values.get(key)
        return v if isinstance(v, str) else None

    def tier_mean(self, name):
        vals = [self.num(f"tier_{t}_{name}") for t in TIERS]
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None
