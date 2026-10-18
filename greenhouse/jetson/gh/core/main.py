"""Entry point for the four core services: python -m gh.core.main <name>"""
import json
import os
import signal
import sys
import time
from pathlib import Path

import yaml

from .. import __version__, topics as T
from ..bus import MqttBus
from ..manifest import load_dir
from ..module import HEARTBEAT_S, modules_dir


def main(name):
    data = Path(os.environ.get("GH_DATA_DIR", "/data"))
    conf = Path(os.environ.get("GH_CONFIG_DIR", "/app/config"))
    data.mkdir(parents=True, exist_ok=True)
    manifests = load_dir(modules_dir())
    will = json.dumps({"alive": False})
    bus = MqttBus(f"gh-{name}", will_topic=T.health(name), will_payload=will)

    if name == "supervisor":
        from ..runtime import DockerRuntime, NullRuntime
        from .supervisor import Supervisor
        # GH_RUNTIME=none runs without Docker: the supervisor still computes every status but
        # starts and stops nothing. Used for bench runs where each module is a plain process.
        runtime = NullRuntime() if os.environ.get("GH_RUNTIME") == "none" else DockerRuntime()
        svc = Supervisor(bus, manifests, runtime, data / "supervisor.json")
    elif name == "safety":
        from .safety import Governor
        svc = Governor(bus, manifests, yaml.safe_load((conf / "limits.yaml").read_text()))
    elif name == "store":
        from .store import Store
        svc = Store(bus, str(data / "greenhouse.db"), yaml.safe_load((conf / "profiles.yaml").read_text()))
    elif name == "bridge":
        from .bridge import Bridge
        svc = Bridge(bus, manifests)
    else:
        sys.exit(f"unknown core service {name}")

    stop = {"now": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(now=True))
    svc.start()
    print(f"core {name} started with {len(manifests)} modules known", flush=True)
    last = 0.0
    while not stop["now"]:
        now = time.time()
        if now - last >= HEARTBEAT_S:
            last = now
            bus.publish(T.health(name), {"alive": True, "ts": now, "state": "running", "version": __version__})
        if hasattr(svc, "tick"):
            svc.tick()
        time.sleep(1.0)
    bus.publish(T.health(name), will, retain=True)
    time.sleep(0.5)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
