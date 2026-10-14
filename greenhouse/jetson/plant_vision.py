#!/usr/bin/env python3
"""Daily per-plant vision metrics -> Home Assistant via MQTT discovery.

Runs on the compute node (Jetson). One fixed 160 degree camera in the top back-left corner
frames all three tiers, so each pot keeps a fixed region of interest (ROI) in plants.json.
Close-ups come from the RealSense D405 on the arm, written by robot_supervisor during
inspect runs; if a close-up newer than the overview frame exists, its metrics win, because
a wrist view at 200 mm beats a corner view at 1.5 m. For every plant it publishes:
  canopy_area   % of the ROI covered by plant pixels
  greenness     mean excess-green index of plant pixels (0-100)
  yellowing     % of plant pixels in the yellow/brown hue band
  stress        0-100 score combining yellowing, droop and growth stall
and one summary sensor "Vision flagged plants".

Schedule with cron at a time the lights are at a fixed level, e.g.
  0 11 * * *  /usr/bin/python3 /opt/greenhouse/plant_vision.py
Run it twice (11:00 and 19:00) to get droop (afternoon canopy loss).

pip install opencv-python numpy paho-mqtt
"""
import json
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import paho.mqtt.client as mqtt

CFG = json.loads(Path(__file__).with_name("plants.json").read_text())
STATE = Path(__file__).with_name("vision_history.json")
PREFIX = "homeassistant"
DEVICE = {"identifiers": ["greenhouse_vision"], "name": "Greenhouse Vision",
          "manufacturer": "RedTower", "model": "Jetson plant vision"}


def grab(device: str, warmup: int = 10):
    cap = cv2.VideoCapture(device)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv2.CAP_PROP_AUTO_WB, 0)          # fixed white balance so days are comparable
    frame = None
    for _ in range(warmup):                   # let exposure settle
        ok, frame = cap.read()
    cap.release()
    if frame is None:
        raise RuntimeError(f"camera {device} returned no frame")
    return frame


def metrics(roi: np.ndarray) -> dict:
    img = roi.astype(np.float32) / 255.0
    b, g, r = img[..., 0], img[..., 1], img[..., 2]
    s = r + g + b + 1e-6
    exg = 2 * g / s - r / s - b / s                        # excess green on chromaticity
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    green = (exg > 0.05) & (val > 40)
    yellow = (hue >= 15) & (hue <= 32) & (sat > 70) & (val > 60)   # OpenCV hue 0-180
    brown = (hue < 15) & (sat > 60) & (val > 30) & (val < 150)
    plant = green | yellow | brown
    plant = cv2.morphologyEx(plant.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)) > 0
    n = int(plant.sum())
    area = 100.0 * n / plant.size
    if n == 0:
        return {"canopy_area": 0.0, "greenness": 0.0, "yellowing": 0.0}
    return {
        "canopy_area": round(area, 1),
        "greenness": round(float(np.clip(exg[plant].mean() * 250, 0, 100)), 1),
        "yellowing": round(100.0 * float((yellow | brown)[plant].mean()), 1),
    }


def stress_score(pid: str, m: dict, hist: dict) -> float:
    h = hist.get(pid, [])
    score = min(60.0, m["yellowing"] * 2)                  # discoloration
    today = [x for x in h if x["date"] == datetime.now().date().isoformat()]
    if today and m["canopy_area"] < 0.85 * today[0]["canopy_area"]:
        score += 25                                        # >15 % droop since this morning
    week = [x for x in h if x["date"] != datetime.now().date().isoformat()][-7:]
    if len(week) >= 5 and m["canopy_area"] <= min(x["canopy_area"] for x in week):
        score += 15                                        # growth stalled for a week
    return round(min(100.0, score), 0)


def discover(client, pid: str, label: str):
    for key, unit, icon in [("canopy_area", "%", "mdi:leaf"), ("greenness", None, "mdi:palette"),
                            ("yellowing", "%", "mdi:leaf-off"), ("stress", None, "mdi:alert-decagram")]:
        cfg = {"name": f"{label} {key.replace('_', ' ')}", "unique_id": f"gh_vision_{pid}_{key}",
               "object_id": f"greenhouse_vision_{pid}_{key}",
               "state_topic": f"greenhouse/vision/{pid}", "value_template": f"{{{{ value_json.{key} }}}}",
               "state_class": "measurement", "icon": icon, "device": DEVICE}
        if unit:
            cfg["unit_of_measurement"] = unit
        client.publish(f"{PREFIX}/sensor/gh_vision_{pid}/{key}/config", json.dumps(cfg), retain=True)


def main():
    hist = json.loads(STATE.read_text()) if STATE.exists() else {}
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="greenhouse-vision")
    client.username_pw_set(CFG["mqtt"]["user"], CFG["mqtt"]["password"])
    client.connect(CFG["mqtt"]["host"], 1883)
    client.loop_start()

    client.publish(f"{PREFIX}/sensor/gh_vision/flagged/config", json.dumps({
        "name": "Vision flagged plants", "unique_id": "gh_vision_flagged",
        "object_id": "greenhouse_vision_flagged_plants", "state_topic": "greenhouse/vision/summary",
        "value_template": "{{ value_json.flagged | join(', ') if value_json.flagged else 'none' }}",
        "icon": "mdi:sprout", "device": DEVICE}), retain=True)

    flagged, snaps = [], Path(CFG.get("snapshot_dir", "/opt/greenhouse/snapshots"))
    snaps.mkdir(parents=True, exist_ok=True)
    frame = grab(CFG["overview"]["camera"])
    cv2.imwrite(str(snaps / f"{datetime.now():%Y%m%d_%H%M}_overview.jpg"), frame)
    closeups = Path(CFG.get("closeups", {}).get("dir", "/opt/greenhouse/closeups"))
    for p in CFG["plants"]:
        x, y, w, h = p["roi"]
        crop = frame[y:y + h, x:x + w]
        shot = closeups / f"{p['id']}_rgb.png"     # D405 colour frame from the last inspect run
        if shot.exists() and time.time() - shot.stat().st_mtime < 6 * 3600:
            near = cv2.imread(str(shot))
            if near is not None:
                crop = near
        m = metrics(crop)
        m["stress"] = stress_score(p["id"], m, hist)
        discover(client, p["id"], p["label"])
        client.publish(f"greenhouse/vision/{p['id']}", json.dumps(m), retain=True)
        hist.setdefault(p["id"], []).append({"date": datetime.now().date().isoformat(), **m})
        hist[p["id"]] = hist[p["id"]][-30:]
        if m["stress"] >= CFG.get("flag_threshold", 40):
            flagged.append(p["label"])

    client.publish("greenhouse/vision/summary", json.dumps({"flagged": flagged}), retain=True)
    STATE.write_text(json.dumps(hist))
    time.sleep(1)
    client.loop_stop()


if __name__ == "__main__":
    main()
