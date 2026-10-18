"""Overview camera (driver): the fixed wide-angle camera in the top back-left corner that sees
all three tiers. At the configured times (11:00 and 19:00, lights on) it takes one frame, cuts
each pot out by its region in config/widecam.yaml and measures it: how much of the region is
canopy, how green it is, how much is yellowing, and a 0-100 stress score that also weighs a
canopy that shrinks between morning and evening (wilting) and a week without growth.

There is no depth here. Canopy is a fraction of the pot's own region: comparable day to day for
the same pot, not between pots. The arm camera does the measuring in millimetres.
Backend "v4l2" reads the USB camera through OpenCV; "sim" draws the cabinet."""
import json
import os
import time
from pathlib import Path

import cv2
import numpy as np
import yaml

from .. import topics as T
from ..bus import loads
from ..module import Module

DAY = 86400
YELLOW_FULL = 0.25       # this much of the canopy yellow counts as fully discoloured
WILT_LOSS = 0.15         # canopy down this much from morning to evening: wilting
STALL_GAIN = 0.05        # less growth than this over a week: stalled
KEEP_DAYS = 14


def load_rois(path=None):
    path = Path(path or Path(os.environ.get("GH_CONFIG_DIR", "/app/config")) / "widecam.yaml")
    return yaml.safe_load(path.read_text())


def measure(frame, roi):
    """One pot: canopy fraction of its region, greenness, yellow fraction."""
    x, y, w, h = roi
    crop = frame[y:y + h, x:x + w]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    green = (hue >= 35) & (hue <= 90) & (sat > 60) & (val > 40)          # same bands as perception
    yellow = (hue >= 20) & (hue < 35) & (sat > 90) & (val > 110)
    plant = cv2.morphologyEx((green | yellow).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    n = int(plant.sum())
    return {"canopy_fraction": round(n / float(w * h), 4),
            "greenness": round(float((green & plant).sum()) / n, 3) if n else None,
            "yellow_fraction": round(float((yellow & plant).sum()) / n, 3) if n else None}


def stress(m, morning=None, week_ago=None):
    """0-100. Discolouration counts most, then wilting since this morning, then a stalled week.
    Starting weights, to be tuned on the real plants."""
    if not m["canopy_fraction"]:
        return 0, []
    flags, score = [], 60 * min(1.0, (m["yellow_fraction"] or 0) / YELLOW_FULL)
    if (m["yellow_fraction"] or 0) >= YELLOW_FULL / 2:
        flags.append("yellowing")
    if morning and m["canopy_fraction"] < morning * (1 - WILT_LOSS):
        score += 25
        flags.append("wilting since the morning")
    if week_ago and m["canopy_fraction"] <= week_ago * (1 + STALL_GAIN):
        score += 15
        flags.append("no growth in a week")
    return int(round(min(100.0, score))), flags


def draw_cabinet(rois, plants, size=(1920, 1080), seed=0):
    """A synthetic overview frame: a pot in each region, a plant of the given size (0 to 1) where
    one grows, yellowed if asked."""
    rng = np.random.default_rng(seed)
    frame = np.full((size[1], size[0], 3), (30, 32, 35), np.uint8)
    for pos, (x, y, w, h) in rois.items():
        cv2.rectangle(frame, (x + w // 4, y + h - h // 4), (x + 3 * w // 4, y + h - 4), (50, 65, 85), -1)
        p = plants.get(pos)
        if not p or p.get("size", 0) <= 0:
            continue
        cx, cy, r = x + w // 2, y + h // 2, max(3, int(min(w, h) * 0.45 * p["size"]))
        for _ in range(6):
            dx, dy = (int(v) for v in rng.integers(-r // 3 - 1, r // 3 + 1, 2))
            cv2.ellipse(frame, (cx + dx, cy + dy), (r // 2 + 2, r // 3 + 2), int(rng.integers(0, 180)), 0, 360,
                        (45, int(150 + rng.integers(0, 40)), 55), -1)
        if p.get("yellow"):
            cv2.ellipse(frame, (cx, cy), (r // 2, r // 3), 30, 0, 360, (40, 200, 210), -1)
    return frame


class V4l2:
    def __init__(self, device, width, height):
        self.cap = cv2.VideoCapture(device)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if not self.cap.isOpened():
            raise OSError(f"cannot open camera {device}")

    def grab(self):
        for _ in range(5):                                  # let exposure settle
            self.cap.read()
        ok, frame = self.cap.read()
        if not ok:
            raise OSError("the camera returned no frame")
        return frame


class Widecam(Module):
    def setup(self):
        self.rois = {k: tuple(v) for k, v in load_rois()["regions"].items()}
        self.plants, self.done, self.pending = {}, set(), []
        self.history_path = self.data_dir / "widecam_history.json"
        self.history = loads(self.history_path.read_text(), {}) if self.history_path.exists() else {}
        self.bus.subscribe(f"{T.ROOT}/plant/+", lambda t, p: self.plants.__setitem__(t.split("/")[-1], loads(p, {})))
        self.cam = None
        try:
            if self.config["backend"] == "v4l2":
                self.cam = V4l2(self.config["device"], self.config["width"], self.config["height"])
                self.report("running", f"camera {self.config['device']}")
            else:
                self.report("stub", "simulated overview camera")
        except Exception as exc:
            self.report("fault", f"camera not available: {exc}")

    def on_cmd(self, data):
        if data.get("op") == "capture":
            self.pending.append("manual")

    def loop(self):
        lt = time.localtime(self.clock())
        stamp = f"{lt.tm_year}-{lt.tm_yday}-{lt.tm_hour:02d}:{lt.tm_min:02d}"
        for at in self.config["times"]:
            hh, mm = (int(v) for v in at.split(":"))
            key = f"{lt.tm_year}-{lt.tm_yday}-{at}"
            if (lt.tm_hour, lt.tm_min) >= (hh, mm) and lt.tm_hour == hh and key not in self.done:
                self.done.add(key)
                self.pending.append("am" if hh < 15 else "pm")
        while self.pending:
            self.capture(self.pending.pop(0), stamp)

    def grab(self):
        if self.cam is not None:
            return self.cam.grab()
        if self.config["backend"] != "sim":
            raise OSError("camera not available")
        now, plants = self.clock(), {}
        for pos, p in self.plants.items():
            if p.get("type_confirmed") and p.get("status") != "dead":
                days = (now - (p.get("planted") or now)) / DAY
                plants[pos] = {"size": min(0.9, 0.35 + 0.03 * days), "yellow": p.get("status") == "attention"}
        return draw_cabinet(self.rois, plants, (self.config["width"], self.config["height"]), seed=int(now) % 1000)

    def capture(self, slot, stamp):
        try:
            frame = self.grab()
        except Exception as exc:
            return self.report("fault", f"capture failed: {exc}")
        now, annotated = self.clock(), frame.copy()
        for pos, roi in self.rois.items():
            m = measure(frame, roi)
            hist = self.history.setdefault(pos, [])
            today = time.localtime(now).tm_yday
            morning = next((c for ts, c, s in reversed(hist) if s == "am" and time.localtime(ts).tm_yday == today), None)
            week = [c for ts, c, s in hist if 6.5 * DAY <= now - ts <= 7.5 * DAY]
            score, flags = stress(m, morning if slot == "pm" else None, week[0] if week else None)
            if slot in ("am", "pm"):
                hist.append([now, m["canopy_fraction"], slot])
            self.history[pos] = [h for h in hist if now - h[0] <= KEEP_DAYS * DAY]
            plant = self.plants.get(pos, {})
            body = dict(m, position=pos, stress=score, flags=flags, ts=now, slot=slot,
                        plant=plant.get("common") if plant.get("type_confirmed") else None)
            self.bus.publish(T.vision(pos), body, retain=True)
            x, y, w, h = roi
            colour = (60, 60, 230) if score >= 50 else (80, 200, 80) if m["canopy_fraction"] else (120, 120, 120)
            cv2.rectangle(annotated, (x, y), (x + w, y + h), colour, 2)
            cv2.putText(annotated, f"{pos} {score}", (x + 4, y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, colour, 2)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.write_text(json.dumps(self.history))
        small = cv2.resize(annotated, (960, int(960 * annotated.shape[0] / annotated.shape[1])))
        ok, jpg = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok:
            self.bus.publish(T.photo("overview"), jpg.tobytes(), retain=True)
        self.report(self.state if self.state != "fault" else ("stub" if self.cam is None else "running"),
                    f"last overview {stamp} ({slot})")
