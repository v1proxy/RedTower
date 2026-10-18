"""Message bus. MqttBus talks to Mosquitto on the Home Assistant Yellow.
MemoryBus is the same interface in memory, used by the tests."""
import json
import os
from collections import deque


def match(pattern: str, topic: str) -> bool:
    """MQTT wildcard match: + is one level, # is the rest."""
    p, t = pattern.split("/"), topic.split("/")
    for i, part in enumerate(p):
        if part == "#":
            return True
        if i >= len(t) or (part != "+" and part != t[i]):
            return False
    return len(p) == len(t)


def loads(payload, default=None):
    try:
        return json.loads(payload)
    except (TypeError, ValueError):
        return default


class MemoryBus:
    def __init__(self):
        self.retained = {}
        self.subs = []
        self.sent = []
        self._queue = deque()
        self._draining = False

    def subscribe(self, pattern, callback):
        self.subs.append((pattern, callback))
        for topic, payload in list(self.retained.items()):
            if match(pattern, topic):
                callback(topic, payload)

    def publish(self, topic, payload, retain=False):
        if not isinstance(payload, (str, bytes)):
            payload = json.dumps(payload)
        if retain:
            if payload == "":
                self.retained.pop(topic, None)
            else:
                self.retained[topic] = payload
        self.sent.append((topic, payload))
        self._queue.append((topic, payload))
        if self._draining:
            return
        self._draining = True
        try:
            while self._queue:
                t, p = self._queue.popleft()
                for pattern, cb in list(self.subs):
                    if match(pattern, t):
                        cb(t, p)
        finally:
            self._draining = False

    def get(self, topic, default=None):
        return loads(self.retained.get(topic), self.retained.get(topic, default))


class MqttBus:
    """Thin wrapper over paho-mqtt. Connection settings come from the environment
    so no credentials live in the code or the image."""

    def __init__(self, client_id, will_topic=None, will_payload=None):
        import paho.mqtt.client as mqtt

        self._subs = []
        self._c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        user = os.environ.get("GH_MQTT_USER")
        if user:
            self._c.username_pw_set(user, os.environ.get("GH_MQTT_PASSWORD"))
        if will_topic:
            self._c.will_set(will_topic, will_payload, qos=1, retain=True)
        self._c.on_connect = self._on_connect
        self._c.on_message = self._on_message
        self._c.reconnect_delay_set(1, 30)
        self._c.connect_async(os.environ.get("GH_MQTT_HOST", "192.168.10.10"),
                              int(os.environ.get("GH_MQTT_PORT", "1883")), keepalive=30)
        self._c.loop_start()

    def _on_connect(self, client, userdata, flags, reason, properties=None):
        for pattern, _ in self._subs:
            client.subscribe(pattern, qos=1)

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
        except UnicodeDecodeError:
            return                          # binary topics (camera frames) are not for handlers
        for pattern, cb in list(self._subs):
            if match(pattern, msg.topic):
                try:
                    cb(msg.topic, payload)
                except Exception as exc:  # one bad handler must not kill the loop
                    print(f"handler error on {msg.topic}: {exc!r}", flush=True)

    def subscribe(self, pattern, callback):
        self._subs.append((pattern, callback))
        self._c.subscribe(pattern, qos=1)

    def publish(self, topic, payload, retain=False):
        if not isinstance(payload, (str, bytes)):
            payload = json.dumps(payload)
        self._c.publish(topic, payload, qos=1, retain=retain)
