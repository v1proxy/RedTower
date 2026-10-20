"""Check the Home Assistant side against a real Home Assistant (step 15).

Runs the Home Assistant Docker image with the greenhouse package, a private Mosquitto with the
access list, and the stack as processes. Home Assistant's REST API stands in for the ESPHome
nodes: their entities are set as states, which is what the package's mirror automation reacts
to. Nothing here touches the live greenhouse.

Checks: the configuration is valid; MQTT discovery creates every entity the package and the
panel use; the mirror automation feeds the stack until the interlocks read OK; an approved
watering reaches the actuator bridge, which picks the right ESPHome action; the package logs
no errors; and the panel renders on the real entities in headless Chromium.

Needs docker, mosquitto, and for the panel: pip install playwright websocket-client
  python tools_ha_check.py [--keep] [--image homeassistant/home-assistant:stable]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
HA_DIR = HERE.parent / "ha"
sys.path.insert(0, str(HERE))

from gh import topics as T                                              # noqa: E402
from gh.bus import MqttBus, loads                                       # noqa: E402
from gh.core.bridge import Bridge                                       # noqa: E402
from gh.core.store import positions                                     # noqa: E402
from gh.manifest import load_dir                                        # noqa: E402
from tools_stack_check import (CORE, MODULES, USERS, Broker, Stack, check, free_port,  # noqa: E402
                               results, wait)

IMAGE = sys.argv[sys.argv.index("--image") + 1] if "--image" in sys.argv else "homeassistant/home-assistant:stable"
CONTAINER = "ghcheck-ha"
NODE = re.compile(r"\.greenhouse_(tier|utility)_")                      # entities the ESPHome nodes provide
ENTITY = re.compile(r"\b(sensor|binary_sensor|switch|select|camera|number|light|fan|input_boolean|button)"
                    r"\.greenhouse_[a-z0-9_]+\b")


class HomeAssistant:
    def __init__(self, tmp, broker_port):
        self.port, self.cfg = free_port(), tmp / "ha"
        (self.cfg / "packages").mkdir(parents=True)
        shutil.copy(HA_DIR / "packages" / "greenhouse_jetson.yaml", self.cfg / "packages")
        shutil.copytree(HA_DIR / "www", self.cfg / "www")
        (self.cfg / "configuration.yaml").write_text(
            "default_config:\nhomeassistant:\n  packages: !include_dir_named packages\n"
            f"  time_zone: America/Chicago\nhttp:\n  server_port: {self.port}\n")
        self.url, self.token, self.broker_port = f"http://127.0.0.1:{self.port}", None, broker_port

    def check_config(self):
        out = subprocess.run(["docker", "run", "--rm", "-v", f"{self.cfg}:/config", IMAGE, "python", "-m",
                              "homeassistant", "--script", "check_config", "-c", "/config"],
                             capture_output=True, text=True, timeout=300)
        bad = [l for l in out.stdout.splitlines() if "Failed config" in l or "Invalid config" in l]
        return out.returncode == 0 and not bad, "\n".join(bad) or out.stdout[-400:]

    def start(self):
        subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)
        subprocess.run(["docker", "run", "-d", "--name", CONTAINER, "--network", "host", "-e", "TZ=America/Chicago",
                        "-v", f"{self.cfg}:/config", IMAGE], check=True, capture_output=True)
        return wait(lambda: self._get("/api/onboarding", auth=False) is not None, 180)

    def stop(self):
        subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)

    def logs(self):
        return subprocess.run(["docker", "logs", CONTAINER], capture_output=True, text=True).stderr

    # ---- HTTP
    def _req(self, method, path, body=None, auth=True, form=False):
        data, headers = None, {}
        if body is not None:
            data = (urllib.parse.urlencode(body) if form else json.dumps(body)).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(self.url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                text = resp.read().decode()
                return json.loads(text) if text else {}
        except (OSError, ValueError):
            return None

    def _get(self, path, auth=True):
        return self._req("GET", path, auth=auth)

    def onboard(self):
        client = self.url + "/"
        user = self._req("POST", "/api/onboarding/users", {"client_id": client, "name": "Bench", "username": "bench",
                                                            "password": "bench-pw-1234", "language": "en"}, auth=False)
        tok = self._req("POST", "/auth/token", {"grant_type": "authorization_code", "code": user["auth_code"],
                                                 "client_id": client}, auth=False, form=True)
        self.token, self.tokens = tok["access_token"], tok
        for step, body in (("core_config", {}), ("analytics", {}),
                           ("integration", {"client_id": client, "redirect_uri": client})):
            self._req("POST", f"/api/onboarding/{step}", body)
        return bool(self.token)

    def add_mqtt(self):
        flow = self._req("POST", "/api/config/config_entries/flow", {"handler": "mqtt", "show_advanced_options": True})
        for _ in range(4):                                  # the broker form, possibly behind a menu
            if not flow or flow.get("type") == "create_entry":
                break
            if flow.get("type") == "menu":
                flow = self._req("POST", f"/api/config/config_entries/flow/{flow['flow_id']}", {"next_step_id": "broker"})
                continue
            answer = defaults(flow.get("data_schema", []))
            answer.update(broker="127.0.0.1", port=self.broker_port, username="homeassistant",
                          password=USERS["homeassistant"])
            flow = self._req("POST", f"/api/config/config_entries/flow/{flow['flow_id']}", answer)
        return bool(flow and flow.get("type") == "create_entry"), str(flow)[:300]

    def states(self):
        return {s["entity_id"]: s for s in (self._get("/api/states") or [])}

    def set_state(self, entity, state, unit=None):
        self._req("POST", f"/api/states/{entity}",
                  {"state": str(state), "attributes": {"unit_of_measurement": unit} if unit else {}})

    def ws(self, messages):
        """Send websocket commands in order and return their results."""
        import websocket
        conn = websocket.create_connection(self.url.replace("http", "ws") + "/api/websocket", timeout=15)
        conn.recv()
        conn.send(json.dumps({"type": "auth", "access_token": self.token}))
        conn.recv()
        out = []
        for i, msg in enumerate(messages, 1):
            conn.send(json.dumps(dict(msg, id=i)))
            while True:
                reply = json.loads(conn.recv())
                if reply.get("id") == i and reply.get("type") == "result":
                    out.append(reply)
                    break
        conn.close()
        return out


def defaults(schema):
    """A config-flow form filled with its own defaults, so new fields in a later release still
    get a value. Required booleans without one are off; required choices take the first option."""
    out = {}
    for field in schema:
        if field.get("type") == "expandable":
            out[field["name"]] = defaults(field.get("schema", []))
        elif "default" in field:
            out[field["name"]] = field["default"]
        elif field.get("required"):
            sel = field.get("selector", {})
            if "boolean" in sel:
                out[field["name"]] = False
            elif "select" in sel and sel["select"].get("options"):
                opt = sel["select"]["options"][0]
                out[field["name"]] = opt["value"] if isinstance(opt, dict) else opt
    return out


def nodes_healthy(ha, moisture=55):
    """The four ESPHome nodes, as the states Home Assistant would hold for them."""
    for node in ("tier_a", "tier_b", "tier_c", "utility"):
        ha.set_state(f"binary_sensor.greenhouse_{node}_status", "on")
    for key in ("doors", "safety_circuit_tripped", "leak_detected", "leak_lockout", "reservoir_low_float",
                "watering_active"):
        ha.set_state(f"binary_sensor.greenhouse_utility_{key}", "off")
    ha.set_state("sensor.greenhouse_utility_reservoir_level", 80, "%")
    ha.set_state("sensor.greenhouse_utility_cabinet_power", 203, "W")
    for t in "abc":
        for key, value, unit in (("air_temperature", 24.0, "°C"), ("air_humidity", 60, "%"), ("vpd", 1.0, "kPa"),
                                 ("leaf_vpd", 0.9, "kPa"), ("leaf_to_air_delta", -1.2, "°C"),
                                 ("median_moisture", moisture, "%")):
            ha.set_state(f"sensor.greenhouse_tier_{t}_{key}", value, unit)
    ha.set_state("sensor.greenhouse_tier_c_co2", 610, "ppm")


def referenced():
    """Entity ids the package and the panel use, with their templates expanded."""
    package = (HA_DIR / "packages" / "greenhouse_jetson.yaml").read_text()
    panel = (HA_DIR / "www" / "greenhouse" / "greenhouse-panel.js").read_text()
    ids = {m.group(0) for m in ENTITY.finditer(package + panel) if not m.group(0).endswith("_")}
    ms = load_dir(HERE / "modules")
    ids |= {f"sensor.greenhouse_{n}_status" for n in ms} | {f"binary_sensor.greenhouse_{n}_alive" for n in ms}
    ids |= {f"switch.greenhouse_{n}_enabled" for n, m in ms.items() if not m.always_on}
    ids |= {f"sensor.greenhouse_{a}_last_cycle" for a in ("envagent", "tender", "llm")}
    for p in positions():
        p = p.lower()
        ids |= {f"sensor.greenhouse_plant_{p}", f"sensor.greenhouse_observation_{p}", f"camera.greenhouse_photo_{p}",
                f"camera.greenhouse_annotated_{p}", f"camera.greenhouse_history_{p}"}
    return ids


def panel_renders(ha, tmp):
    """Put the card on a dashboard and open it in headless Chromium with the bench user's token."""
    from playwright.sync_api import sync_playwright
    view = yaml.safe_load((HA_DIR / "dashboard_view.yaml").read_text())[0]
    view["cards"][0].pop("demo", None)                                      # real entities, not simulated data
    res = ha.ws([{"type": "lovelace/resources/create", "res_type": "module", "url": "/local/greenhouse/greenhouse-panel.js"},
                 {"type": "lovelace/dashboards/create", "url_path": "gh-check", "title": "Greenhouse check", "mode": "storage"},
                 {"type": "lovelace/config/save", "url_path": "gh-check", "config": {"views": [view]}}])
    if not all(r.get("success") for r in res):
        return False, f"dashboard setup failed: {res}"
    errors, chrome = [], next(iter(sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))), None)
    tokens = dict(ha.tokens, hassUrl=ha.url, clientId=ha.url + "/", expires=int(time.time() * 1000) + 1800 * 1000)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=str(chrome) if chrome else None)
        context = browser.new_context(viewport={"width": 1400, "height": 1000})
        # In place before any page script runs, so the frontend never redirects to its login form.
        context.add_init_script(f"localStorage.setItem('hassTokens', {json.dumps(json.dumps(tokens))});")
        page = context.new_page()
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(ha.url + "/gh-check/greenhouse")
        # The card re-renders on every state update; wait until it shows the stack as it is.
        found = page.wait_for_function("""() => {
            const find = (root) => { if (!root) return null;
              for (const el of root.querySelectorAll('*')) {
                if (el.tagName.toLowerCase() === 'greenhouse-panel') return el;
                const f = find(el.shadowRoot); if (f) return f; }
              return null; };
            const card = find(document);
            if (!card || !card.shadowRoot) return null;
            const text = [...card.shadowRoot.childNodes].filter(n => n.nodeName !== 'STYLE')
                .map(n => n.textContent).join(' ');
            return text.includes('Running') && !text.includes('not answering') ? text : null;
        }""", timeout=30000)
        text = found.json_value()
        page.screenshot(path=str(tmp / "panel.png"), full_page=True)
        browser.close()
    own = [e for e in errors if "greenhouse" in e.lower() or "panel" in e.lower()]
    shown = all(w in text for w in ("Maag", "Climate", "Safety governor", "Stub", "Paused", "Disabled"))
    return not own and shown, {"errors": own, "text": text}


def main():
    for tool in ("docker", "mosquitto", "mosquitto_passwd"):
        if not shutil.which(tool):
            sys.exit(f"{tool} is not on the PATH")
    tmp = Path(tempfile.mkdtemp(prefix="gh-ha-"))
    broker = Broker(tmp)
    stack = Stack(tmp, broker.port)
    ha = HomeAssistant(tmp, broker.port)
    try:
        print("Configuration")
        ok, why = ha.check_config()
        check("Home Assistant accepts the configuration with the package", ok, why)
        check("Home Assistant starts", ha.start())
        check("onboarding through the API", ha.onboard())
        ok, why = ha.add_mqtt()
        check("MQTT integration connects to the broker as the homeassistant user", ok, why)

        print("\nStack and discovery")
        nodes_healthy(ha)
        for name in CORE + MODULES:
            stack.start(name)
        os.environ.update(GH_MQTT_HOST="127.0.0.1", GH_MQTT_PORT=str(broker.port), GH_MQTT_USER="gh_core",
                          GH_MQTT_PASSWORD=USERS["gh_core"])
        core = MqttBus("ghcheck-observer")
        seen = {}
        core.subscribe(f"{T.ROOT}/#", lambda t, p: seen.__setitem__(t, p))
        wanted = {cfg["default_entity_id"] for _, cfg in Bridge(None, load_dir(HERE / "modules")).entities()}
        wait(lambda: wanted <= set(ha.states()), 90)
        have = set(ha.states())
        check("every entity the stack announces exists under its intended id", wanted <= have,
              f"{len(wanted - have)} missing, e.g. {sorted(wanted - have)[:6]}; similar ids present: "
              f"{sorted(e for e in have if 'greenhouse' in e and e not in wanted and not NODE.search(e))[:6]}")
        refs = referenced()
        missing = sorted(e for e in refs - have if not NODE.search(e))
        check("every entity the package and the panel use exists", not missing, f"{len(missing)} missing: {missing[:10]}")

        print("\nMirror and interlocks")
        core.publish(f"{T.ROOT}/esphome/refresh", "1")
        check("the mirror automation feeds the stack until the interlocks read OK",
              wait(lambda: all(seen.get(T.interlock(k)) == "OK" for k in ("door", "estop", "water")), 60),
              str({k: seen.get(T.interlock(k)) for k in ("door", "estop", "water")}))
        check("node readings arrive at the stack in SI units",
              wait(lambda: (loads(seen.get(T.sensor("tier_b_vpd")), {}) or {}).get("v") == 1.0, 30))

        print("\nActuator bridge")
        ha.set_state("sensor.greenhouse_tier_b_median_moisture", 20, "%")
        core.publish(T.config_set("irrigation"), {"start_hour": 0, "end_hour": 24})
        found = {}

        def watering_traced():
            runs = ha.ws([{"type": "trace/list", "domain": "automation", "item_id": "gh_actuator_bridge"}])[0]
            for run in runs.get("result") or []:                    # light settings run through it too
                trace = ha.ws([{"type": "trace/get", "domain": "automation", "item_id": "gh_actuator_bridge",
                                "run_id": run["run_id"]}])[0].get("result", {})
                for steps in (trace.get("trace") or {}).values():   # what ran, not the automation's text
                    for step in steps:
                        params = (step.get("result") or {}).get("params") or {}
                        if params.get("service") == "greenhouse_utility_water_zone":
                            found.update(params, topic=trace.get("trigger", ""))
                            return True
            return False
        ok = wait(watering_traced, 60)
        data = found.get("service_data", {})
        check("an approved watering calls esphome.greenhouse_utility_water_zone with zone 2 for 60 s",
              ok and found.get("domain") == "esphome" and str(data.get("zone")) == "2" and str(data.get("seconds")) == "60"
              and "water_b" in found.get("topic", ""), str(found)[:400])

        print("\nPanel")
        try:
            ok, info = panel_renders(ha, tmp)
            check("the panel shows every module's real status, without errors", ok, str(info)[:500])
            if isinstance(info, dict):
                print("      panel text starts:", " ".join(info["text"].split())[:160])
        except ImportError:
            print("SKIP  the panel (pip install playwright websocket-client)")
        except Exception as exc:                                # timed out waiting for the real statuses
            check("the panel shows every module's real status, without errors", False, str(exc).splitlines()[0])

        print("\nLog")
        errors = [l for l in ha.logs().splitlines() if " ERROR " in l and ("greenhouse" in l.lower() or "template" in l.lower())
                  and "esphome.greenhouse_utility_water_zone" not in l and "Action esphome." not in l]
        check("the package logs no errors (the missing ESPHome actions aside)", not errors, "\n".join(errors[:5]))
    finally:
        (tmp / "ha.log").write_text(ha.logs())
        stack.stop()
        ha.stop()
        broker.stop()
    print("\n%d of %d checks passed" % (sum(results), len(results)))
    if "--keep" in sys.argv or not all(results):
        print("logs, screenshot and data kept in", tmp)
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
