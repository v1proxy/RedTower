#!/usr/bin/env python3
"""Close-range depth quality on a real plant, in the arm's working band.

Streams 848x480 @ 30 with depth aligned to colour and keeps the frame with the
most pixels inside the band (default 100-350 mm). Reports:

  coverage  share of the frame with valid depth inside the band
  fill      valid pixels / the object's filled silhouette: how holey the leaf is
  temporal  median per-pixel depth std over 15 consecutive frames: sensor noise,
            independent of the leaf's shape (needs the object still for 0.5 s)
  range     nearest / median / farthest inside the band

Saves the colour frame, a depth map scaled to the band (near = red, far = blue,
no depth = black, out of band = dimmed), a side-by-side composite, and the raw
depth of the best frame (.npy, uint16, 0.1 mm units on the D405).

    python d405_leaf.py [--lo 100] [--hi 350] [--secs 15] [--lead 0]
"""
import argparse
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import pyrealsense2 as rs

OUT = Path(__file__).with_name("d405_check_output")
W, H, FPS, WIN = 848, 480, 30, 15


def colourise(m, lo, hi):
    """Depth in metres -> BGR image scaled to [lo, hi]."""
    valid = m > 0
    norm = np.clip((m - lo) / (hi - lo), 0, 1)
    img = cv2.applyColorMap((255 * (1 - norm)).astype(np.uint8), cv2.COLORMAP_TURBO)
    oob = valid & ((m < lo) | (m > hi))
    img[oob] = (img[oob] * 0.3).astype(np.uint8)
    img[~valid] = 0
    return img


def silhouette(band):
    """Largest in-band blob with its interior holes filled."""
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    closed = cv2.morphologyEx(band.astype(np.uint8), cv2.MORPH_CLOSE, k)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(closed, 8)
    if n < 2:
        return None
    blob = (lab == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    contours, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(blob)
    cv2.drawContours(filled, contours, -1, 1, thickness=-1)
    return filled.astype(bool)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lo", type=float, default=100, help="band near edge, mm")
    ap.add_argument("--hi", type=float, default=350, help="band far edge, mm")
    ap.add_argument("--secs", type=float, default=15)
    ap.add_argument("--lead", type=float, default=0, help="seconds to wait first")
    a = ap.parse_args()
    lo, hi = a.lo / 1000, a.hi / 1000
    OUT.mkdir(exist_ok=True)
    if a.lead:
        print(f"lead-in {a.lead:.0f} s", flush=True)
        time.sleep(a.lead)

    pipe, cfg = rs.pipeline(), rs.config()
    cfg.enable_stream(rs.stream.depth, W, H, rs.format.z16, FPS)
    cfg.enable_stream(rs.stream.color, W, H, rs.format.bgr8, FPS)
    scale = pipe.start(cfg).get_device().first_depth_sensor().get_depth_scale()
    align = rs.align(rs.stream.color)
    for _ in range(15):                      # let auto-exposure settle
        pipe.wait_for_frames()

    buf, best, steady = deque(maxlen=WIN), None, None
    n, t0 = 0, time.time()
    while time.time() - t0 < a.secs:
        fr = align.process(pipe.wait_for_frames())
        d, c = fr.get_depth_frame(), fr.get_color_frame()
        if not d or not c:
            continue
        n += 1
        raw = np.asanyarray(d.get_data()).copy()
        m = raw.astype(np.float32) * scale
        band = (m > lo) & (m < hi)
        buf.append(m)
        if best is None or band.mean() > best["cov"]:
            best = dict(cov=band.mean(), raw=raw, m=m, band=band,
                        color=np.asanyarray(c.get_data()).copy())
        if len(buf) == WIN and n % 5 == 0:
            stack = np.stack(buf)
            held = ((stack > lo) & (stack < hi)).all(axis=0)
            if held.sum() > 500 and (steady is None or held.sum() > steady[0]):
                steady = (int(held.sum()), float(np.median(stack[:, held].std(axis=0))))
    pipe.stop()
    el = time.time() - t0

    print(f"frames    : {n} in {el:.1f} s -> {n / el:.1f} fps")
    print(f"band      : {a.lo:.0f}-{a.hi:.0f} mm")
    if best is None or best["cov"] < 0.002:
        print("nothing inside the band: move the plant so a leaf sits inside it")
        return 1

    m, band = best["m"], best["band"]
    obj = silhouette(band)
    print(f"coverage  : {100 * best['cov']:.0f} % of the frame")
    if obj is not None:
        inside = band & obj
        v = m[inside] * 1000
        print(f"fill      : {100 * inside.sum() / obj.sum():.0f} % of a {obj.sum()} px silhouette"
              " (the rest are holes)")
        print(f"range     : nearest {v.min():.0f}, median {np.median(v):.0f},"
              f" farthest {v.max():.0f} mm")
    if steady:
        print(f"temporal  : {steady[1] * 1000:.2f} mm median per-pixel std over {WIN} frames"
              f" ({steady[0]} px held still)")
    else:
        print("temporal  : not measured (nothing held still in the band for 0.5 s)")

    col = colourise(m, lo, hi)
    comp = np.hstack([best["color"], col])
    cv2.putText(comp, f"red {a.lo:.0f} mm  blue {a.hi:.0f} mm  black no depth",
                (W + 10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(str(OUT / "leaf_color.png"), best["color"])
    cv2.imwrite(str(OUT / "leaf_depth.png"), col)
    cv2.imwrite(str(OUT / "leaf_side_by_side.png"), comp)
    np.save(OUT / "leaf_depth_raw.npy", best["raw"])
    print(f"wrote leaf_*.png and leaf_depth_raw.npy to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
