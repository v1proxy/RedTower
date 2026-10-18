#!/usr/bin/env python3
"""Separate the camera's real frame rate from Python processing cost.

Streams depth + colour at 848x480x30 for 5 s without any processing and reads the
frame metadata (actual fps, exposure). Then times rs.align on the same frames.
"""
import time

import pyrealsense2 as rs

W, H, FPS = 848, 480, 30
pipe = rs.pipeline()
cfg = rs.config()
cfg.enable_stream(rs.stream.depth, W, H, rs.format.z16, FPS)
cfg.enable_stream(rs.stream.color, W, H, rs.format.bgr8, FPS)
pipe.start(cfg)
for _ in range(15):          # let auto-exposure settle
    pipe.wait_for_frames()

md = rs.frame_metadata_value
n, t0, exp, afps = 0, time.time(), [], []
while time.time() - t0 < 5:
    fs = pipe.wait_for_frames()
    n += 1
    d = fs.get_depth_frame()
    for key, out in ((md.actual_exposure, exp), (md.actual_fps, afps)):
        if d.supports_frame_metadata(key):
            out.append(d.get_frame_metadata(key))
el = time.time() - t0
print(f"raw pipeline      : {n / el:.1f} fps")
if afps:
    print(f"camera reports    : {sum(afps) / len(afps) / (1000 if max(afps) > 1000 else 1):.1f} fps (metadata)")
if exp:
    print(f"depth exposure    : {sum(exp) / len(exp) / 1000:.1f} ms average (33 ms is the ceiling at 30 fps)")

align = rs.align(rs.stream.color)
n, t0 = 0, time.time()
while time.time() - t0 < 5:
    align.process(pipe.wait_for_frames())
    n += 1
el = time.time() - t0
print(f"with rs.align     : {n / el:.1f} fps")
pipe.stop()
