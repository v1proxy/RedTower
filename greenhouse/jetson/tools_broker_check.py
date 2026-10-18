"""Check the core against a real MQTT broker (task 4).
Reads GH_MQTT_HOST, GH_CORE_USER and GH_CORE_PASSWORD from the environment or from .env.
Uses the topic prefix "greenhouse/selftest", which no module reads, so nothing touches the
real greenhouse topics. It sits inside greenhouse/# so the broker ACL lets gh_core use it.

  python tools_broker_check.py
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
env = here / ".env"
if env.exists():
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
os.environ["GH_MQTT_USER"] = os.environ.get("GH_CORE_USER", "")
os.environ["GH_MQTT_PASSWORD"] = os.environ.get("GH_CORE_PASSWORD", "")

from gh.bus import MqttBus                                   # noqa: E402

P = "greenhouse/selftest"                                    # isolated from the live topics

results = []


def check(name, ok):
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name, flush=True)


def wait(cond, seconds=5):
    end = time.time() + seconds
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.1)
    return False


got = {}
a = MqttBus("gh-selftest-a")
time.sleep(1.5)
check("connects with the core user", a._c.is_connected())
a.subscribe(f"{P}/#", lambda t, p: got.__setitem__(t, p))
a.publish(f"{P}/plain", {"n": 1})
check("JSON round trip", wait(lambda: json.loads(got.get(f"{P}/plain", "{}")).get("n") == 1))
a.publish(f"{P}/kept", "ON", retain=True)
time.sleep(0.5)
late = {}
b = MqttBus("gh-selftest-b", will_topic=f"{P}/b/health", will_payload=json.dumps({"alive": False}))
time.sleep(1.5)
b.subscribe(f"{P}/kept", lambda t, p: late.__setitem__(t, p))
check("retained message reaches a late subscriber", wait(lambda: late.get(f"{P}/kept") == "ON"))
b.publish(f"{P}/b/health", {"alive": True})
check("heartbeat seen", wait(lambda: f"{P}/b/health" in got and json.loads(got[f"{P}/b/health"])["alive"]))
b._c._sock.close()                                           # kill the connection without a goodbye
check("last will delivered when a module dies", wait(lambda: json.loads(got.get(f"{P}/b/health", "{}")).get("alive") is False, 60))
a.publish(f"{P}/photo", bytes([255, 216, 255, 0, 200]), retain=True)
time.sleep(0.5)
check("binary frame does not break handlers", a._c.is_connected())
for topic in (f"{P}/kept", f"{P}/photo", f"{P}/b/health"):
    a.publish(topic, "", retain=True)                        # clean up retained test topics
time.sleep(0.5)
print("\n%d of %d checks passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
