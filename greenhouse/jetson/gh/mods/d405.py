"""Depth camera (driver), Intel RealSense D405 on the arm flange.

One capture = one colour frame and one depth frame aligned to it, saved under the data
folder, announced on greenhouse/capture/<position>, and published as the plant's latest
photo. Backend "realsense" uses the real camera; "sim" generates a synthetic plant."""
import json
import time

import cv2
import numpy as np

from .. import topics as T
from ..module import Module
from .simscene import make_scene


def history_strip(folder, days=7, thumb=(160, 120)):
    """One JPEG with the latest capture of each of the last days, newest first."""
    latest = {}
    for path in sorted(folder.glob("*_color.jpg")):
        latest[path.name[:8]] = path                                  # one per calendar day
    tiles = []
    for day in sorted(latest, reverse=True)[:days]:
        img = cv2.imread(str(latest[day]))
        if img is None:
            continue
        tile = cv2.resize(img, thumb, interpolation=cv2.INTER_AREA)
        label = f"{day[4:6]}/{day[6:8]}"
        cv2.putText(tile, label, (6, thumb[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
        cv2.putText(tile, label, (6, thumb[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        tiles.append(tile)
    if not tiles:
        return None
    ok, jpg = cv2.imencode(".jpg", np.hstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 80])
    return jpg.tobytes() if ok else None


class RealSense:
    def __init__(self, width=1280, height=720, warmup=15):
        import pyrealsense2 as rs
        self.rs, self.warmup = rs, warmup
        self.pipe, cfg = rs.pipeline(), rs.config()
        cfg.enable_stream(rs.stream.depth, width, height, rs.format.z16, 30)
        cfg.enable_stream(rs.stream.color, width, height, rs.format.bgr8, 30)
        profile = self.pipe.start(cfg)
        self.scale = profile.get_device().first_depth_sensor().get_depth_scale()
        self.align = rs.align(rs.stream.color)
        i = profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()
        self.intr = {"fx": i.fx, "fy": i.fy, "cx": i.ppx, "cy": i.ppy, "width": i.width, "height": i.height}
        self.serial = profile.get_device().get_info(rs.camera_info.serial_number)

    def grab(self):
        for _ in range(self.warmup):                      # let auto-exposure settle
            self.pipe.wait_for_frames(5000)
        self.warmup = 3
        frames = self.align.process(self.pipe.wait_for_frames(5000))
        color = np.asanyarray(frames.get_color_frame().get_data()).copy()
        depth = np.asanyarray(frames.get_depth_frame().get_data()).astype(np.float32) * self.scale
        return color, depth, dict(self.intr)

    def close(self):
        self.pipe.stop()


class Sim:
    serial = "simulated"

    def __init__(self):
        self.n = 0

    def grab(self, position=""):
        self.n += 1
        return make_scene(seed=sum(map(ord, position)) + self.n, stage=(sum(map(ord, position)) % 4))

    def close(self): pass


class D405(Module):
    def setup(self):
        self.cam, self.pending = None, []
        self._open()

    def _open(self):
        if self.cam:
            self.cam.close()
        self.cam, self.backend = None, self.config["backend"]
        try:
            self.cam = RealSense() if self.backend == "realsense" else Sim()
            self.report("running" if self.backend == "realsense" else "stub", f"camera {self.cam.serial}")
        except Exception as exc:                          # camera unplugged, driver missing
            self.report("fault", f"camera not available: {exc}")

    def on_config(self):
        if hasattr(self, "backend") and self.config["backend"] != self.backend:
            self._open()              # switch backend without a restart, e.g. to sim while unplugged

    def on_cmd(self, data):
        if data.get("op") == "capture" and isinstance(data.get("position"), str):
            self.pending.append(data)

    def loop(self):
        while self.pending and self.cam:
            self.capture(self.pending.pop(0))
        period = self.config["live_period_s"]
        if self.cam and period > 0 and self.clock() - getattr(self, "last_live", 0) >= period:
            self.last_live = self.clock()
            try:
                color = (self.cam.grab("live") if isinstance(self.cam, Sim) else self.cam.grab())[0]
                ok, jpg = cv2.imencode(".jpg", cv2.resize(color, (640, int(640 * color.shape[0] / color.shape[1]))),
                                       [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ok:
                    self.bus.publish(f"{T.ROOT}/live/d405", jpg.tobytes(), retain=True)
            except Exception as exc:
                self.report("fault", f"live view failed: {exc}")

    def capture(self, cmd):
        pos = cmd["position"]
        try:
            color, depth, intr = self.cam.grab(pos) if isinstance(self.cam, Sim) else self.cam.grab()
        except Exception as exc:
            return self.report("fault", f"capture failed: {exc}")
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(self.clock()))
        folder = self.data_dir / "captures" / pos
        folder.mkdir(parents=True, exist_ok=True)
        base = folder / stamp
        cv2.imwrite(f"{base}_color.jpg", color, [cv2.IMWRITE_JPEG_QUALITY, 90])
        np.save(f"{base}_depth.npy", (depth * 10000).astype(np.uint16))          # 0.1 mm units
        (folder / f"{stamp}_intr.json").write_text(json.dumps(intr))
        ok, jpg = cv2.imencode(".jpg", cv2.resize(color, (640, int(640 * color.shape[0] / color.shape[1]))),
                               [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok:
            self.bus.publish(T.photo(pos), jpg.tobytes(), retain=True)
        strip = history_strip(folder)
        if strip is not None:
            self.bus.publish(T.photo(pos) + "/history", strip, retain=True)
        self.bus.publish(f"{T.ROOT}/capture/{pos}", {"position": pos, "ts": self.clock(), "id": cmd.get("id"),
                                                   "color": f"{base}_color.jpg", "depth": f"{base}_depth.npy",
                                                   "intr": str(folder / f"{stamp}_intr.json"),
                                                   "simulated": isinstance(self.cam, Sim)})
        self.report(self.state if self.state != "fault" else "running", f"last capture {pos} {stamp}")
