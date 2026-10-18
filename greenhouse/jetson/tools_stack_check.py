"""Run the whole stack against a private Mosquitto broker and check it end to end.

The unit tests run every module on an in-memory bus. This runs them the way the Jetson will:
each core service and module is its own process, with the broker user docker-compose gives it,
talking through a real Mosquitto that enforces mosquitto-acl.sample.

It starts its own broker on a free local port, so it never touches the live greenhouse.
Home Assistant is played by this script: it mirrors healthy ESPHome nodes, records what
reaches greenhouse/actuator/, and sends the interface's commands. Gantry, arm and depth
camera run on their simulated backends. The language model has no key, so the agents are
only checked for starting and pausing.

Needs mosquitto and mosquitto_passwd on the PATH (apt install mosquitto) and the packages in
requirements-test.txt. Takes about two minutes.

  python tools_stack_check.py [--keep]     --keep leaves the logs and data folder in place
  python tools_stack_check.py --docker     the same checks on the containers from docker-compose.yml
                                           (images built first: docker compose build)
"""
import getpass
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from gh import topics as T                                  # noqa: E402
from gh.bus import MqttBus, loads                           # noqa: E402
from gh.core.bridge import Bridge                           # noqa: E402
from gh.manifest import load_dir                            # noqa: E402

CORE = ("supervisor", "safety", "store", "bridge")
MODULES = ("esphome", "climate", "irrigation", "gantry", "arm", "d405", "perception", "motion", "nutrients",
           "llm", "envagent", "tender", "widecam")
USERS = {"gh_core": "core-pw", "gh_module": "module-pw", "homeassistant": "ha-pw"}
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + (f"  ({detail})" if detail and not ok else ""), flush=True)
    return ok


def wait(cond, seconds):
    end = time.time() + seconds
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.2)
    return bool(cond())


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Broker:
    def __init__(self, tmp):
        self.port, self.dir = free_port(), tmp / "broker"
        self.dir.mkdir()
        pw = self.dir / "passwd"
        for i, (user, password) in enumerate(USERS.items()):
            subprocess.run(["mosquitto_passwd", "-b"] + (["-c"] if i == 0 else []) + [str(pw), user, password],
                           check=True, capture_output=True)
        acl = (HERE / "mosquitto-acl.sample").read_text() + "\nuser homeassistant\ntopic readwrite #\n"
        (self.dir / "acl").write_text(acl)
        os.chmod(pw, 0o600); os.chmod(self.dir / "acl", 0o600)
        (self.dir / "mosquitto.conf").write_text(
            f"user {getpass.getuser()}\nlistener {self.port} 127.0.0.1\nallow_anonymous false\n"
            f"password_file {pw}\nacl_file {self.dir / 'acl'}\npersistence false\n")
        self.proc = subprocess.Popen(["mosquitto", "-c", str(self.dir / "mosquitto.conf")],
                                     stdout=open(self.dir / "log", "w"), stderr=subprocess.STDOUT)
        if not wait(self._up, 10):
            sys.exit("broker did not start, see " + str(self.dir / "log"))

    def _up(self):
        try:
            socket.create_connection(("127.0.0.1", self.port), 0.5).close()
            return True
        except OSError:
            return False

    def stop(self):
        self.proc.terminate()
        self.proc.wait(10)


class Stack:
    def __init__(self, tmp, port):
        self.tmp, self.logs, self.procs = tmp, tmp / "logs", {}
        self.logs.mkdir()
        self.env = dict(os.environ, PYTHONPATH=str(HERE), PYTHONUNBUFFERED="1", GH_MQTT_HOST="127.0.0.1",
                        GH_MQTT_PORT=str(port), GH_DATA_DIR=str(tmp / "data"), GH_MODULES_DIR=str(HERE / "modules"),
                        GH_CONFIG_DIR=str(HERE / "config"), GH_RUNTIME="none", GH_ANTHROPIC_API_KEY="")

    def start(self, name):
        user = "gh_core" if name in CORE else "gh_module"
        cmd = ([sys.executable, "-m", "gh.core.main", name] if name in CORE
               else [sys.executable, str(HERE / "modules" / name / "main.py")])
        env = dict(self.env, GH_MQTT_USER=user, GH_MQTT_PASSWORD=USERS[user])
        self.procs[name] = subprocess.Popen(cmd, env=env, cwd=HERE, stdout=open(self.logs / f"{name}.log", "a"),
                                            stderr=subprocess.STDOUT)

    def kill(self, name):
        self.procs[name].send_signal(signal.SIGKILL)       # no goodbye: only the last will tells
        self.procs[name].wait(10)

    def stop(self):
        for p in self.procs.values():
            if p.poll() is None:
                p.terminate()
        for p in self.procs.values():
            try:
                p.wait(15)
            except subprocess.TimeoutExpired:
                p.kill()

    def crashed(self):
        return {n: p.returncode for n, p in self.procs.items() if p.poll() is not None}


class DockerStack:
    """The stack from docker-compose.yml, as containers. A generated override points them at the
    private broker over the host network, binds the data volume to the run folder, and drops the
    USB mapping for the camera, which this machine may not have. The supervisor's real Docker
    runtime starts and stops the module containers, as it will on the Jetson, and Docker's
    restart policy brings back a container that dies."""
    PROJECT = "ghcheck"
    restarts_itself = True

    def __init__(self, tmp, port):
        self.tmp, self.logs = tmp, tmp / "logs"
        self.logs.mkdir()
        (tmp / "data").mkdir()
        names = yaml.safe_load((HERE / "docker-compose.yml").read_text())["services"]
        lines = ["services:"]
        for name in names:
            lines += [f"  {name}:", "    network_mode: host", "    environment:",
                      "      GH_MQTT_HOST: 127.0.0.1", f"      GH_MQTT_PORT: \"{port}\""]
            if name == "d405":
                lines.append("    devices: !reset []")
        lines += ["volumes:", "  gh-data:", "    driver: local", "    driver_opts:",
                  "      type: none", "      o: bind", f"      device: {tmp / 'data'}"]
        (tmp / "override.yml").write_text("\n".join(lines) + "\n")
        (tmp / "env").write_text(f"GH_CORE_USER=gh_core\nGH_CORE_PASSWORD={USERS['gh_core']}\n"
                                 f"GH_MODULE_USER=gh_module\nGH_MODULE_PASSWORD={USERS['gh_module']}\n"
                                 "GH_ANTHROPIC_API_KEY=\n")
        self.compose = ["docker", "compose", "-p", self.PROJECT, "-f", str(HERE / "docker-compose.yml"),
                        "-f", str(tmp / "override.yml"), "--env-file", str(tmp / "env")]
        self.started = False

    def start(self, name):
        if not self.started:                                # one "up" brings every service
            self.started = True
            subprocess.run(self.compose + ["up", "-d", "--no-build"], cwd=HERE, check=True,
                           stdout=open(self.logs / "compose.log", "a"), stderr=subprocess.STDOUT)

    def _inspect(self, name, fmt):
        out = subprocess.run(["docker", "inspect", "-f", fmt, f"gh-{name}"], capture_output=True, text=True)
        return out.stdout.strip()

    def kill(self, name):
        """A crash, not a docker stop or docker kill: those count as stopped by hand, and Docker's
        restart policy then leaves the container down."""
        pid = int(self._inspect(name, "{{.State.Pid}}"))
        try:
            os.kill(pid, signal.SIGKILL)
        except PermissionError:                             # the container runs as root and we do not
            subprocess.run(["sudo", "-n", "kill", "-9", str(pid)], check=True)

    def restarts(self, name):
        return int(self._inspect(name, "{{.RestartCount}}") or 0)

    def stop(self):
        with open(self.logs / "containers.log", "w") as fh:
            subprocess.run(self.compose + ["logs", "--no-color", "--tail", "40"], cwd=HERE, stdout=fh,
                           stderr=subprocess.STDOUT)
        subprocess.run(self.compose + ["down", "-v", "--timeout", "15"], cwd=HERE,
                       stdout=open(self.logs / "compose.log", "a"), stderr=subprocess.STDOUT)

    IDLE = ("nutrients", "llm", "envagent", "tender")       # disabled, or agents at authority auto

    def crashed(self):
        """Restarted, restarting, or not running when it should be. A container the supervisor
        stopped on purpose is not a crash, whatever its exit code."""
        out = {}
        for name in CORE + MODULES:
            state = self._inspect(name, "{{.State.Status}} {{.State.ExitCode}} {{.RestartCount}}").split()
            if (not state or state[0] == "restarting" or state[2] != "0"
                    or (state[0] != "running" and name not in self.IDLE)):
                out[name] = " ".join(state) or "missing"
        return out


class HomeAssistant:
    """Plays Home Assistant: the statestream mirror of four healthy nodes, the actuator bridge
    (recorded only) and the interface's commands."""

    def __init__(self, port):
        os.environ.update(GH_MQTT_HOST="127.0.0.1", GH_MQTT_PORT=str(port), GH_MQTT_USER="homeassistant",
                          GH_MQTT_PASSWORD=USERS["homeassistant"])
        self.bus = MqttBus("ha-standin")
        if not wait(self.bus._c.is_connected, 5):
            sys.exit("Home Assistant stand-in cannot connect")
        self.retained, self.driven, self.mirror, self.history = {}, [], {}, []
        self.bus.subscribe(f"{T.ROOT}/#", self._on)
        self.bus.subscribe("homeassistant/#", self._on)
        self.bus.subscribe(f"{T.ROOT}/actuator/+/set", lambda t, p: self.driven.append((t.split("/")[2], loads(p, {}))))
        self.bus.subscribe(f"{T.ROOT}/esphome/refresh", lambda t, p: self.resync())

    def _on(self, topic, payload):
        self.retained[topic] = payload
        self.history.append((topic, payload))

    def get(self, topic):
        return loads(self.retained.get(topic), self.retained.get(topic))

    def status(self, name):
        return (self.get(T.status(name)) or {}).get("state")

    def set(self, domain, obj, state, unit=None):
        self.mirror[(domain, obj)] = (str(state), unit)
        self._send(domain, obj)

    def _send(self, domain, obj):
        state, unit = self.mirror[(domain, obj)]
        base = f"{T.HA_STATE}/{domain}/greenhouse_{obj}"
        if unit:
            self.bus.publish(f"{base}/unit_of_measurement", json.dumps(unit), retain=True)
        self.bus.publish(f"{base}/state", state, retain=True)

    def resync(self):
        for domain, obj in list(self.mirror):
            self._send(domain, obj)
        self.bus.publish(f"{T.HA_STATE}/heartbeat", "1")

    def healthy(self):
        for node in ("tier_a", "tier_b", "tier_c", "utility"):
            self.set("binary_sensor", f"{node}_status", "on")
        for key in ("doors", "safety_circuit_tripped", "leak_detected", "leak_lockout", "reservoir_low_float",
                    "watering_active"):
            self.set("binary_sensor", f"utility_{key}", "off")
        self.set("sensor", "utility_reservoir_level", 80, "%")
        self.set("sensor", "utility_cabinet_power", 203, "W")
        for t in "abc":
            self.set("sensor", f"tier_{t}_air_temperature", 24.0, "°C")
            self.set("sensor", f"tier_{t}_air_humidity", 60, "%")
            self.set("sensor", f"tier_{t}_vpd", 1.0, "kPa")
            self.set("sensor", f"tier_{t}_leaf_vpd", 0.9, "kPa")
            self.set("sensor", f"tier_{t}_leaf_to_air_delta", -1.2, "°C")
            self.set("sensor", f"tier_{t}_median_moisture", 55, "%")
        self.set("sensor", "tier_c_co2", 610, "ppm")
        self.bus.publish(f"{T.HA_STATE}/heartbeat", "1")

    def was_driven(self, actuator, action=None, value=None):
        return any(a == actuator and (action is None or d.get("action") == action) and
                   (value is None or d.get("value") == value) for a, d in self.driven)


def run_checks(ha, stack, tmp):
    expect = {"supervisor": "running", "safety": "running", "store": "running", "bridge": "running",
              "esphome": "running", "climate": "running", "irrigation": "running", "gantry": "stub", "arm": "stub",
              "perception": "running", "motion": "running", "nutrients": "disabled", "llm": "paused",
              "envagent": "paused", "tender": "paused", "widecam": "stub"}
    print("\nStart-up")
    if wait(lambda: (ha.get(T.health("d405")) or {}).get("alive"), 20):
        ha.bus.publish(T.config_set("d405"), {"backend": "sim"})    # no RealSense here: switch at run time
    expect["d405"] = "stub"
    ok = wait(lambda: all(ha.status(n) == s for n, s in expect.items()), 45)
    wrong = {n: ha.status(n) for n, s in expect.items() if ha.status(n) != s}
    check("every service shows its expected status", ok, f"unexpected: {wrong}")
    check("no process crashed", not stack.crashed(), str(stack.crashed()))
    if getattr(stack, "restarts_itself", False):
        idle = stack.IDLE
        stopped = lambda: all(stack._inspect(n, "{{.State.Status}}") == "exited" for n in idle)   # noqa: E731
        check("the supervisor stopped the containers it does not want", wait(stopped, 30),
              str({n: stack._inspect(n, "{{.State.Status}}") for n in idle}))
    disc = {t for t in ha.retained if t.startswith("homeassistant/") and t.endswith("/config")}
    want = {t for t, _ in Bridge(None, load_dir(HERE / "modules")).entities()}
    check("every Home Assistant discovery entity published", want <= disc, f"{len(want - disc)} missing")
    check("door, E-stop and water interlocks are OK",
          all(ha.retained.get(T.interlock(k)) == "OK" for k in ("door", "estop", "water")),
          str({k: ha.retained.get(T.interlock(k)) for k in ("door", "estop", "water")}))

    print("\nPlant registry")
    for pos, kind in (("A01", "pepper"), ("B03", "basil")):
        ha.bus.publish(T.STORE_CMD_UI, {"op": "replace_plant", "position": pos, "type": kind})
    check("the user sets plant types", wait(lambda: all((ha.get(T.plant(p)) or {}).get("type_confirmed")
                                                        for p in ("A01", "B03")), 10))
    mod = module_bus(stack)
    mod.publish(T.cmd("store"), {"op": "replace_plant", "position": "C05", "type": "mint", "source": "ui"})
    mod.publish(T.STORE_CMD_UI, {"op": "replace_plant", "position": "C06", "type": "mint"})
    rejected = lambda: any(t == T.log("store") for t in ha.retained) and \
        "only the user" in str(ha.get(T.log("store")))                                     # noqa: E731
    check("a module claiming to be the user is refused by the store", wait(rejected, 10))
    time.sleep(1.0)
    check("a module cannot reach the user's store topic",
          not (ha.get(T.plant("C06")) or {}).get("type_confirmed"))

    print("\nServices drive actuators only through the governor")
    check("climate pushes the photoperiod to all three tiers",
          wait(lambda: all(ha.was_driven(f"light_{t}", "photoperiod", 16) for t in "abc"), 75))
    ha.set("sensor", "tier_b_median_moisture", 20, "%")
    ha.bus.publish(T.config_set("irrigation"), {"start_hour": 0, "end_hour": 24})
    check("irrigation waters the dry tier B for 60 s", wait(lambda: ha.was_driven("water_b", "run", 60), 15))
    check("and leaves the wet tiers alone", not ha.was_driven("water_a") and not ha.was_driven("water_c"))
    mod.publish(T.actuator_set("water_c"), {"id": "bypass", "action": "run", "value": 180})
    time.sleep(1.5)
    check("a module publishing to an actuator directly is dropped by the broker", not ha.was_driven("water_c"))

    print("\nRobot")
    ha.bus.publish(T.cmd("motion"), {"op": "capture_route"})
    went = wait(lambda: ha.retained.get(f"{T.ROOT}/robot/busy") == "ON", 10)
    done = went and wait(lambda: ha.retained.get(f"{T.ROOT}/robot/busy") == "OFF", 90)
    check("photo route runs and finishes", done, (ha.get(T.status("motion")) or {}).get("detail", ""))
    for pos in ("A01", "B03"):
        obs = ha.get(T.observation(pos)) or {}
        check(f"{pos} captured and measured", len(obs.get("candidates", [])) > 0 and obs.get("height_mm"),
              str({k: obs.get(k) for k in ("height_mm", "quality")}))
    check("capture files on disk", len(list((tmp / "data" / "captures").glob("*/*_color.jpg"))) >= 2)
    check("gantry finished at home", (ha.get(f"{T.ROOT}/gantry/state") or {}).get("at") == "home")

    n_before = len(ha.driven)
    ha.bus.publish(T.cmd("motion"), {"op": "capture_route"})
    wait(lambda: any(a == "arm" and d.get("action") == "capture" for a, d in ha.driven[n_before:]), 30)
    ha.set("binary_sensor", "utility_doors", "on")
    stopped = wait(lambda: ha.retained.get(f"{T.ROOT}/robot/busy") == "OFF", 30)
    check("opening the door ends the route", stopped and ha.was_driven("gantry", "stop"),
          (ha.get(T.status("motion")) or {}).get("detail", ""))
    check("door interlock reads OPEN", ha.retained.get(T.interlock("door")) == "OPEN")
    ha.set("binary_sensor", "utility_doors", "off")

    print("\nApproved cut")
    wait(lambda: ha.retained.get(T.interlock("door")) == "OK", 20)          # the door closed above
    c = ((ha.get(T.observation("A01")) or {}).get("candidates") or [{}])[0]
    ha.bus.publish(T.SAFETY_REQUEST_UI, {"id": "ui-tend-1", "source": "ui", "actuator": "robot", "action": "tend",
                                         "value": f"pinch {c.get('label')}", "position": "A01",
                                         "target": {"action": "pinch", "label": c.get("label"), "kind": c.get("kind"),
                                                    "xyz_mm": c.get("xyz_mm")}})
    tended = lambda: [loads(p, {}) for t, p in ha.history if t == T.log("tend")]                     # noqa: E731
    wait(lambda: tended(), 150)
    cuts = [d for a, d in ha.driven if a == "arm" and d.get("action") == "cut"]
    check("an approved cut goes back, finds the leaf again and cuts once",
          tended() and tended()[-1].get("result") == "done" and len(cuts) == 1 and cuts[0].get("task") == "ui-tend-1",
          str(tended()[-1:] or (ha.get(T.status("motion")) or {}).get("detail")))

    print("\nFailure")
    mark = len(ha.history)
    will = lambda: any(t == T.health("climate") and loads(p, {}).get("alive") is False      # noqa: E731
                       for t, p in ha.history[mark:])
    stack.kill("climate")
    if getattr(stack, "restarts_itself", False):
        check("a module that dies is restarted by Docker", wait(lambda: stack.restarts("climate") >= 1, 30))
    else:
        check("a module that dies is shown offline", wait(lambda: ha.status("climate") == "offline", 60),
              ha.status("climate"))
        stack.start("climate")
    check("its last will reaches the broker", wait(will, 60))
    check("and it comes back", wait(lambda: ha.status("climate") == "running", 45), ha.status("climate"))


def module_bus(stack):
    """A rogue client holding the module credentials."""
    os.environ.update(GH_MQTT_USER="gh_module", GH_MQTT_PASSWORD=USERS["gh_module"])
    bus = MqttBus("gh-rogue")
    wait(bus._c.is_connected, 5)
    return bus


def main():
    for tool in ("mosquitto", "mosquitto_passwd") + (("docker",) if "--docker" in sys.argv else ()):
        if not shutil.which(tool):
            sys.exit(f"{tool} is not on the PATH")
    tmp = Path(tempfile.mkdtemp(prefix="gh-stack-"))
    broker = Broker(tmp)
    stack = (DockerStack if "--docker" in sys.argv else Stack)(tmp, broker.port)
    try:
        ha = HomeAssistant(broker.port)
        ha.healthy()
        for name in CORE + MODULES:
            stack.start(name)
        run_checks(ha, stack, tmp)
    finally:
        stack.stop()
        broker.stop()
    print("\n%d of %d checks passed" % (sum(results), len(results)))
    if "--keep" in sys.argv or not all(results):
        print("logs and data kept in", tmp)
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
