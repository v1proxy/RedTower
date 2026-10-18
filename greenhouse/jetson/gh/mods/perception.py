"""Perception (service). Turns one depth capture of one plant into numbers and into a set of
labelled candidate points (C1, C2, ...) drawn on an annotated image.

Nothing here talks to a model. The plant tender later chooses among the labels; it never
invents a coordinate. Camera frame: +x right, +y down, +z forward.

Measured against the camera frame, so "height" is the plant's vertical extent as seen from
the front. It is a consistent growth measure, not a tape-measure height from the soil."""
import json
from pathlib import Path

import cv2
import numpy as np

from .. import topics as T
from ..bus import loads
from ..module import Module

NEAR_M, FAR_M = 0.07, 0.45          # the D405's working band on this rig
MIN_BLOB_PX = 300                   # at 640 px wide; smaller blobs are noise
MERGE_MM = 18                       # candidates closer than this are one candidate
MAX_CANDIDATES = 8


def analyse(color, depth, intr):
    """Pure function: images in, observation dict and annotated image out."""
    h, w = depth.shape
    scale = 640.0 / w                                                   # analyse at a fixed width
    if scale != 1.0:
        color = cv2.resize(color, (640, int(round(h * scale))), interpolation=cv2.INTER_AREA)
        depth = cv2.resize(depth, (640, int(round(h * scale))), interpolation=cv2.INTER_NEAREST)
    fx, fy, cx, cy = (intr[k] * scale for k in ("fx", "fy", "cx", "cy"))
    valid = (depth > NEAR_M) & (depth < FAR_M)
    hsv = cv2.cvtColor(color, cv2.COLOR_BGR2HSV)
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    green = (hue >= 35) & (hue <= 90) & (sat > 60) & (val > 40) & valid
    yellow = (hue >= 20) & (hue < 35) & (sat > 90) & (val > 110) & valid   # soil is duller and darker
    plant = cv2.morphologyEx((green | yellow).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, labels, stats, cents = cv2.connectedComponentsWithStats(plant, 8)
    keep = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= MIN_BLOB_PX]
    mask = np.isin(labels, keep)
    obs = {"valid_depth_fraction": round(float(valid.mean()), 3), "plant_pixels": int(mask.sum()),
           "height_mm": None, "width_mm": None, "canopy_area_cm2": None, "greenness": None,
           "yellow_fraction": None, "nearest_mm": None, "candidates": [], "quality": []}
    annotated = color.copy()
    if obs["valid_depth_fraction"] < 0.02:
        obs["quality"].append("no usable depth: plant out of the 7 to 45 cm band, or lens blocked")
    if not keep:
        obs["quality"].append("no plant found")
        return obs, annotated

    vs, us = np.nonzero(mask)
    z = depth[vs, us]
    x_mm, y_mm = (us - cx) * z / fx * 1000, (vs - cy) * z / fy * 1000
    lo, hi = np.percentile(y_mm, [2, 98])
    obs["height_mm"] = round(float(hi - lo), 1)
    lo, hi = np.percentile(x_mm, [2, 98])
    obs["width_mm"] = round(float(hi - lo), 1)
    obs["canopy_area_cm2"] = round(float((z * z / (fx * fy)).sum() * 1e4), 1)
    obs["nearest_mm"] = round(float(np.percentile(z, 2) * 1000), 1)
    g = float((green & mask).sum())
    obs["yellow_fraction"] = round(float((yellow & mask).sum()) / max(1.0, float(mask.sum())), 3)
    obs["greenness"] = round(g / max(1.0, float(mask.sum())), 3)

    def point(u, v, kind):
        zz = float(depth[int(v), int(u)])
        if not NEAR_M < zz < FAR_M:
            return None
        return {"kind": kind, "px": [int(u / scale), int(v / scale)],
                "xyz_mm": [round(float((u - cx) * zz / fx * 1000), 1), round(float((v - cy) * zz / fy * 1000), 1),
                           round(zz * 1000, 1)],
                "_uv": (int(u), int(v))}

    found = []
    top = int(np.argmin(vs))                                           # highest plant pixel = growth tip
    found.append(point(us[top], min(vs[top] + 4, depth.shape[0] - 1), "tip"))
    yn, ylabels, ystats, ycents = cv2.connectedComponentsWithStats((yellow & mask).astype(np.uint8), 8)
    for i in range(1, yn):                                             # yellowing leaves come first
        if ystats[i, cv2.CC_STAT_AREA] >= MIN_BLOB_PX // 2:
            ys, xs = np.nonzero(ylabels == i)
            j = int(np.argmin((xs - ycents[i][0]) ** 2 + (ys - ycents[i][1]) ** 2))
            found.append(point(xs[j], ys[j], "yellow_leaf"))
    for i in sorted(keep, key=lambda i: -stats[i, cv2.CC_STAT_AREA]):
        cu, cv_ = cents[i]
        ys, xs = np.nonzero(labels == i)
        j = int(np.argmin((xs - cu) ** 2 + (ys - cv_) ** 2))           # centroid snapped onto the blob
        kind = "yellow_leaf" if yellow[ys[j], xs[j]] else "leaf"
        found.append(point(xs[j], ys[j], kind))
        k = int(np.argmin(ys))
        found.append(point(xs[k], min(ys[k] + 4, depth.shape[0] - 1), "tip"))
    out = []
    for c in filter(None, found):
        if all(np.linalg.norm(np.subtract(c["xyz_mm"], o["xyz_mm"])) > MERGE_MM for o in out):
            out.append(c)
    for n_, c in enumerate(out[:MAX_CANDIDATES], 1):
        c["label"] = f"C{n_}"
        u, v = c.pop("_uv")
        cv2.circle(annotated, (u, v), 9, (255, 255, 255), 2)
        cv2.putText(annotated, c["label"], (u + 11, v + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 4)
        cv2.putText(annotated, c["label"], (u + 11, v + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    obs["candidates"] = out[:MAX_CANDIDATES]
    return obs, annotated


class Perception(Module):
    def setup(self):
        self.pending = []
        self.bus.subscribe(f"{T.ROOT}/capture/+", lambda t, p: self.pending.append(loads(p, {})))

    def loop(self):
        while self.pending:
            self.process(self.pending.pop(0))

    def process(self, cap):
        pos = cap.get("position")
        try:
            color = cv2.imread(cap["color"])
            depth = np.load(cap["depth"]).astype(np.float32) / 10000.0
            intr = json.loads(Path(cap["intr"]).read_text())
            if color is None:
                raise ValueError("colour image unreadable")
            obs, annotated = analyse(color, depth, intr)
        except Exception as exc:
            return self.report("fault", f"{pos}: {exc}")
        path = cap["color"].replace("_color.jpg", "_annotated.jpg")
        cv2.imwrite(path, annotated)
        obs.update(position=pos, ts=cap.get("ts"), annotated=path, simulated=bool(cap.get("simulated")))
        self.bus.publish(T.observation(pos), obs, retain=True)
        ok, jpg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok:
            self.bus.publish(T.photo(pos) + "/annotated", jpg.tobytes(), retain=True)
        self.report("running", f"{pos}: {len(obs['candidates'])} candidates" + ("; " + "; ".join(obs["quality"]) if obs["quality"] else ""))
