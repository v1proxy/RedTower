"""Check the broker access list (Gate B). Run it after installing mosquitto-acl.sample.
Reads GH_MQTT_HOST, GH_CORE_USER/PASSWORD and GH_MODULE_USER/PASSWORD from the environment
or from .env.

The safety design rests on two claims that only the broker can make true:
  a module cannot drive an actuator, approve a proposal, or act as the user;
  the core services can.
This sends one probe per topic and watches, as gh_core, which probes come through.

Every probe uses a name or a payload that no live service acts on (unknown module "aclcheck",
unknown proposal id, an operation the store rejects). The two probes that would change state
if the access list were missing are sent in the safe direction: kill switch ON, authority off.
If either one comes through, set them back in Home Assistant.

  python tools_acl_check.py
"""
import json
import os
import sys
import time
import uuid
from pathlib import Path

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
env = here / ".env"
if env.exists():
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from gh.bus import MqttBus                                   # noqa: E402

# Topics a module must never write. Each needs the access list.
MODULE_DENIED = {
    "greenhouse/actuator/aclcheck/set": "drive an actuator around the governor",
    "greenhouse/safety/request/ui": "send a request as the user",
    "greenhouse/store/cmd/ui": "set a plant type as the user",
    "greenhouse/proposal/aclcheck/decision": "approve its own proposal",
    "greenhouse/authority": "raise the governor's authority",
    "greenhouse/authority/set": "change the authority",
    "greenhouse/kill": "clear the kill switch at the governor",
    "greenhouse/kill/set": "clear the kill switch",
    "greenhouse/aclcheck/enable": "change another module's enable state",
    "greenhouse/aclcheck/enable/set": "enable another module",
    "greenhouse/aclcheck/config/set": "reconfigure another module",
    "greenhouse/aclcheck/cmd": "command another module",
    "greenhouse/ha/binary_sensor/greenhouse_aclcheck/state": "fake the Home Assistant mirror the interlocks come from",
    "homeassistant/aclcheck": "write Home Assistant discovery",
}
# Topics modules publish in normal operation. A deny here breaks a module.
MODULE_ALLOWED = [
    "greenhouse/aclcheck/health", "greenhouse/aclcheck/config", "greenhouse/aclcheck/cycle",
    "greenhouse/aclcheck/output", "greenhouse/sensor/aclcheck", "greenhouse/interlock/aclcheck",
    "greenhouse/photo/aclcheck", "greenhouse/live/aclcheck", "greenhouse/observation/aclcheck",
    "greenhouse/vision/aclcheck",
    "greenhouse/arm/aclcheck", "greenhouse/llm/aclcheck", "greenhouse/d405/cmd",
    "greenhouse/esphome/refresh", "greenhouse/safety/request", "greenhouse/store/cmd",
    "greenhouse/log/aclcheck",
]
# Topics the core must be able to write.
CORE_ALLOWED = ["greenhouse/actuator/aclcheck/set", "greenhouse/aclcheck/enable", "greenhouse/proposal/aclcheck",
                "homeassistant/aclcheck"]
SAFE_PAYLOAD = {"greenhouse/kill": "ON", "greenhouse/kill/set": "ON", "greenhouse/authority": "off",
                "greenhouse/authority/set": "aclcheck", "greenhouse/aclcheck/enable": "OFF",
                "greenhouse/aclcheck/enable/set": "OFF"}


def connect(user_key, password_key, name):
    os.environ["GH_MQTT_USER"] = os.environ.get(user_key, "")
    os.environ["GH_MQTT_PASSWORD"] = os.environ.get(password_key, "")
    bus = MqttBus(f"gh-aclcheck-{name}")
    end = time.time() + 5
    while time.time() < end and not bus._c.is_connected():
        time.sleep(0.1)
    return bus


def payload(topic, token):
    if topic in SAFE_PAYLOAD:
        return SAFE_PAYLOAD[topic]
    # Shaped so the governor and the store reject it if it ever reaches them.
    return json.dumps({"id": f"aclcheck-{token}", "source": "aclcheck", "op": "aclcheck",
                       "actuator": "aclcheck", "action": "aclcheck", "token": token})


def probe(sender, observer_seen, topics, token):
    sent = {}
    for topic in topics:
        body = payload(topic, token)
        sent[topic] = body
        sender.publish(topic, body)
    time.sleep(2.0)
    return {t: any(st == t and sp == body for st, sp in observer_seen) for t, body in sent.items()}


def main():
    seen, results = [], []
    core = connect("GH_CORE_USER", "GH_CORE_PASSWORD", "core")
    module = connect("GH_MODULE_USER", "GH_MODULE_PASSWORD", "module")
    for who, bus in (("gh_core", core), ("gh_module", module)):
        ok = bus._c.is_connected()
        results.append(ok)
        print(("PASS  " if ok else "FAIL  ") + f"{who} connects")
    if not all(results):
        sys.exit("cannot test the access list without both users")
    core.subscribe("greenhouse/#", lambda t, p: seen.append((t, p)))
    core.subscribe("homeassistant/#", lambda t, p: seen.append((t, p)))
    time.sleep(1.0)
    token = uuid.uuid4().hex[:8]

    print("\nA module must not be able to:")
    for topic, came in probe(module, seen, MODULE_DENIED, token).items():
        results.append(not came)
        print(("PASS  " if not came else "FAIL  ") + f"{MODULE_DENIED[topic]}  ({topic})")
    print("\nModules still need to write:")
    for topic, came in probe(module, seen, MODULE_ALLOWED, token).items():
        results.append(came)
        print(("PASS  " if came else "FAIL  ") + topic)
    print("\nThe core must be able to write:")
    for topic, came in probe(core, seen, CORE_ALLOWED, token).items():
        results.append(came)
        print(("PASS  " if came else "FAIL  ") + topic)

    print("\nKnown gap, by design for now: any module may write greenhouse/interlock/# and greenhouse/sensor/#,")
    print("because the ESPHome link derives them. A faulty module could report a door as closed. The door")
    print("reeds and the E-stop still cut gantry and arm power through the safety relay.")
    print("\n%d of %d checks passed" % (sum(results), len(results)))
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
