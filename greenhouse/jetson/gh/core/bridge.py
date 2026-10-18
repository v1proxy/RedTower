"""Home Assistant bridge. Publishes MQTT discovery so every module, the authority
selector, the kill switch, the approval count and all plant positions appear in
Home Assistant on their own. New modules show up with no dashboard editing.

Liveness uses expire_after, which Home Assistant evaluates itself. So an entity goes
unavailable even if the whole Jetson is dead, which is what the agent-down watchdog needs."""
from .. import topics as T
from .store import positions

DEVICE = {"identifiers": ["greenhouse"], "name": "Greenhouse", "manufacturer": "Red Tower",
          "model": "Herb Tower"}
ALIVE_EXPIRE_S = 45


class Bridge:
    def __init__(self, bus, manifests):
        self.bus, self.manifests = bus, manifests

    def start(self):
        self.bus.subscribe(T.HA_STATUS, lambda t, p: p.strip() == "online" and self.announce())
        self.announce()

    def entities(self):
        out = []

        def add(kind, uid, **cfg):
            # The entity id the package and the panel use. Home Assistant 2026 reads default_entity_id
            # and ignores object_id, deriving the id from the names instead; older releases read
            # object_id. Both are sent so every release lands on the same id.
            cfg.update(unique_id=f"greenhouse_{uid}", object_id=f"greenhouse_{uid}",
                       default_entity_id=f"{kind}.greenhouse_{uid}", device=DEVICE)
            out.append((f"homeassistant/{kind}/greenhouse_{uid}/config", cfg))

        add("select", "authority", name="Authority", state_topic=T.AUTHORITY_STATE,
            command_topic=T.AUTHORITY_SET, options=list(T.AUTHORITY), icon="mdi:shield-account")
        add("switch", "kill", name="Agent kill switch", state_topic=T.KILL_STATE,
            command_topic=T.KILL_SET, payload_on="ON", payload_off="OFF", icon="mdi:stop-circle")
        add("sensor", "pending_approvals", name="Pending approvals", state_topic=T.SAFETY_PENDING,
            state_class="measurement", icon="mdi:clipboard-check")
        for name, m in self.manifests.items():
            if not m.always_on:
                add("switch", f"{name}_enabled", name=f"{m.title} enabled", state_topic=T.enable(name),
                    command_topic=T.enable_set(name), payload_on="ON", payload_off="OFF")
            add("sensor", f"{name}_status", name=f"{m.title} status", state_topic=T.status(name),
                value_template="{{ value_json.state }}", json_attributes_topic=T.status(name))
            add("binary_sensor", f"{name}_alive", name=f"{m.title} alive", state_topic=T.health(name),
                value_template="{{ 'ON' if value_json.alive else 'OFF' }}",
                device_class="connectivity", expire_after=ALIVE_EXPIRE_S)
            if m.layer == "agent":
                add("sensor", f"{name}_last_cycle", name=f"{m.title} last cycle", state_topic=T.cycle(name),
                    value_template="{{ value_json.ts | int | timestamp_local }}",
                    json_attributes_topic=T.cycle(name),
                    **({"expire_after": int(m.cycle_minutes * 90)} if m.cycle_minutes else {}))
        for pos in positions():
            p = pos.lower()
            add("sensor", f"plant_{p}", name=f"Plant {pos}",
                state_topic=T.plant(pos), value_template="{{ value_json.status }}",
                json_attributes_topic=T.plant(pos), icon="mdi:sprout")
            add("sensor", f"observation_{p}", name=f"Plant {pos} height", state_topic=T.observation(pos),
                value_template="{{ value_json.height_mm }}", unit_of_measurement="mm",
                json_attributes_topic=T.observation(pos), icon="mdi:ruler")
            add("camera", f"photo_{p}", name=f"Plant {pos} photo", topic=T.photo(pos))
            add("camera", f"annotated_{p}", name=f"Plant {pos} candidates", topic=T.photo(pos) + "/annotated")
            add("camera", f"history_{p}", name=f"Plant {pos} photo history", topic=T.photo(pos) + "/history")
        for pos in positions():
            add("sensor", f"vision_{pos.lower()}", name=f"Plant {pos} stress", state_topic=T.vision(pos),
                value_template="{{ value_json.stress }}", json_attributes_topic=T.vision(pos),
                state_class="measurement", icon="mdi:leaf-maple")
        add("camera", "overview", name="Overview camera", topic=T.photo("overview"))
        add("camera", "live_d405", name="Arm camera live", topic=f"{T.ROOT}/live/d405")
        add("binary_sensor", "robot_busy", name="Robot busy", state_topic=f"{T.ROOT}/robot/busy",
            payload_on="ON", payload_off="OFF", device_class="running")
        add("sensor", "proposals", name="Proposals", state_topic=T.PROPOSALS,
            value_template="{{ value_json | length }}",
            json_attributes_topic=T.PROPOSALS, json_attributes_template="{{ {'items': value_json} | tojson }}")
        add("sensor", "last_decision", name="Last governor decision", state_topic=T.log("decision"),
            value_template="{{ value_json.result }}", json_attributes_topic=T.log("decision"))
        for agent, label in (("envagent", "Environment agent"), ("tender", "Plant tender")):
            add("sensor", f"{agent}_output", name=f"{label} output", state_topic=f"{T.ROOT}/{agent}/output",
                value_template="{{ value_json.ts | int | timestamp_local }}",
                json_attributes_topic=f"{T.ROOT}/{agent}/output")
        return out

    def announce(self):
        for topic, cfg in self.entities():
            self.bus.publish(topic, cfg, retain=True)
