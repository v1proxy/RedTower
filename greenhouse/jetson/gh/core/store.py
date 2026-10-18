"""State store: the plant registry and the decision log, in SQLite.

The registry is the record of what grows where. The user's entry sets the plant
type; the camera may suggest one but never writes it."""
import json
import sqlite3
import time

from .. import topics as T
from ..bus import loads

LAYOUT = {"A": 7, "B": 10, "C": 10}      # tier A: peppers, tiers B and C: herbs
STATUSES = ("empty", "ok", "attention", "ready", "dead")
GENERIC_MILESTONES = ["Seedling", "Established", "Mature", "Ready"]


def positions():
    return [f"{t}{n:02d}" for t, count in LAYOUT.items() for n in range(1, count + 1)]


class Store:
    def __init__(self, bus, db_path, profiles, clock=time.time):
        self.bus, self.profiles, self.clock = bus, profiles, clock
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.executescript("""
            create table if not exists plants(position text primary key, data text not null);
            create table if not exists log(id integer primary key, ts real, kind text, data text);
        """)
        for pos in positions():
            self.db.execute("insert or ignore into plants values(?, ?)",
                            (pos, json.dumps(self._empty(pos))))
        self.db.commit()

    def _empty(self, pos):
        return {"position": pos, "type": None, "type_confirmed": False, "common": None,
                "scientific": None, "profile": "none", "milestones": [], "stage": 0,
                "status": "empty", "planted": None}

    def start(self):
        self.bus.subscribe(T.cmd("store"), self._on_cmd)
        self.bus.subscribe(T.STORE_CMD_UI, self._on_cmd)
        self.bus.subscribe(f"{T.ROOT}/log/+", self._on_log)
        for pos in positions():
            self._publish(pos)

    def get(self, pos):
        row = self.db.execute("select data from plants where position=?", (pos,)).fetchone()
        return json.loads(row[0]) if row else None

    def _put(self, plant):
        self.db.execute("update plants set data=? where position=?", (json.dumps(plant), plant["position"]))
        self.db.commit()
        self._publish(plant["position"])

    def _publish(self, pos):
        self.bus.publish(T.plant(pos), self.get(pos), retain=True)

    # ---- commands
    def _on_cmd(self, topic, payload):
        data = loads(payload)
        if not isinstance(data, dict):
            return
        # The topic decides whether this is the user. The broker ACL protects it.
        if topic == T.STORE_CMD_UI:
            data["source"] = "ui"
        elif data.get("source") == "ui":
            data["source"] = "module"
        plant = self.get(str(data.get("position")))
        handler = getattr(self, "op_" + str(data.get("op")), None)
        if plant is None or handler is None:
            return self._event("rejected", data, "unknown position or operation")
        problem = handler(plant, data)
        if problem:
            return self._event("rejected", data, problem)
        self._put(plant)
        self._event("applied", data, "")

    def op_replace_plant(self, plant, data):
        """Only the user replaces a plant. Resets growth and loads the care profile."""
        if data.get("source") != "ui":
            return "only the user can set a plant type"
        name = str(data.get("type") or "").strip()
        if not name:
            return "plant type is empty"
        profile = self.profiles.get(name.lower())
        plant.update(self._empty(plant["position"]))
        plant.update({"type": name, "type_confirmed": True, "status": "ok", "planted": self.clock(),
                      "common": profile["common"] if profile else name,
                      "scientific": profile["scientific"] if profile else None,
                      "milestones": profile["milestones"] if profile else GENERIC_MILESTONES,
                      "profile": "ready" if profile else "pending"})

    def op_clear_plant(self, plant, data):
        if data.get("source") != "ui":
            return "only the user can clear a position"
        plant.update(self._empty(plant["position"]))

    def op_set_stage(self, plant, data):
        stage = data.get("stage")
        if not plant["type_confirmed"]:
            return "no confirmed plant at this position"
        if isinstance(stage, bool) or not isinstance(stage, int) or not 0 <= stage < len(plant["milestones"]):
            return "stage is out of range"
        plant["stage"] = stage
        if plant["status"] in ("ok", "ready"):
            plant["status"] = "ready" if stage == len(plant["milestones"]) - 1 else "ok"

    def op_mark(self, plant, data):
        if data.get("status") not in STATUSES or data.get("status") == "empty":
            return "unknown status"
        if not plant["type_confirmed"]:
            return "no confirmed plant at this position"
        plant["status"] = data["status"]

    # ---- log
    def _on_log(self, topic, payload):
        self.db.execute("insert into log(ts, kind, data) values(?,?,?)",
                        (self.clock(), topic.split("/")[-1], payload))
        self.db.commit()

    def _event(self, result, data, reason):
        self.bus.publish(T.log("store"), {"result": result, "reason": reason, "request": data})

    def recent(self, kind, limit=50):
        rows = self.db.execute("select ts, data from log where kind=? order by id desc limit ?", (kind, limit))
        return [(ts, loads(d, d)) for ts, d in rows]
