#!/usr/bin/env python3
"""First-run check for the RealSense D405.

Answers the questions that matter before you trust it on the arm:
  does the host see it, on USB 3 or USB 2, what firmware, which streams exist,
  is the depth actually valid at working distance, and what is the real frame rate.

It saves a colour frame and a colourised depth frame so you can look at them.

    pip install pyrealsense2 opencv-python numpy
    python d405_check.py
"""
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pyrealsense2 as rs

OUT = Path(__file__).with_name("d405_check_output")
W, H, FPS = 848, 480, 30


def banner(t):
    print("\n" + t + "\n" + "-" * len(t))


def main():
    OUT.mkdir(exist_ok=True)

    banner("Devices")
    ctx = rs.context()
    devices = list(ctx.query_devices())
    if not devices:
        print("No RealSense device found.")
        print("Check: USB-C cable seated at both ends, and that the port is USB 3 (blue, or marked SS).")
        return 1

    dev = devices[0]
    info = rs.camera_info
    for label, key in [("Name", info.name), ("Serial", info.serial_number),
                       ("Firmware", info.firmware_version),
                       ("Recommended firmware", info.recommended_firmware_version),
                       ("USB type", info.usb_type_descriptor),
                       ("Product line", info.product_line)]:
        try:
            print(f"{label:22}: {dev.get_info(key)}")
        except RuntimeError:
            pass

    usb = dev.get_info(info.usb_type_descriptor)
    if usb.startswith("2"):
        print("\nWARNING: the camera negotiated USB 2. Depth at 848x480x30 will not run.")
        print("Move it to a USB 3 port and use a USB 3 cable, not a charge-only one.")

    try:
        fw, rec = dev.get_info(info.firmware_version), dev.get_info(info.recommended_firmware_version)
        if fw != rec:
            print(f"\nNOTE: firmware {fw} differs from the recommended {rec}.")
            print("Update it in the RealSense Viewer before calibrating anything.")
    except RuntimeError:
        pass

    banner("Stream profiles offered")
    for sensor in dev.query_sensors():
        name = sensor.get_info(info.name)
        seen = set()
        for p in sensor.get_stream_profiles():
            v = p.as_video_stream_profile()
            if not v:
                continue
            key = (p.stream_name(), v.width(), v.height(), p.format(), p.fps())
            if key in seen:
                continue
            seen.add(key)
        sizes = sorted({(k[1], k[2]) for k in seen}, reverse=True)[:4]
        streams = sorted({k[0] for k in seen})
        print(f"{name:22}: {', '.join(streams)}  sizes {sizes}")

    banner(f"Streaming {W}x{H} @ {FPS} for 5 s")
    pipe = rs.pipeline()
    cfg = rs.config()
    cfg.enable_stream(rs.stream.depth, W, H, rs.format.z16, FPS)
    cfg.enable_stream(rs.stream.color, W, H, rs.format.bgr8, FPS)
    try:
        profile = pipe.start(cfg)
    except RuntimeError as exc:
        print(f"Could not start that configuration: {exc}")
        print("Try 640x480 or drop to 15 fps, and re-check the USB type above.")
        return 1

    scale = profile.get_device().first_depth_sensor().get_depth_scale()
    align = rs.align(rs.stream.color)
    frames_seen, t0 = 0, time.time()
    depth_img = color_img = None

    while time.time() - t0 < 5:
        frames = align.process(pipe.wait_for_frames())
        d, c = frames.get_depth_frame(), frames.get_color_frame()
        if not d or not c:
            continue
        frames_seen += 1
        depth_img = np.asanyarray(d.get_data())
        color_img = np.asanyarray(c.get_data())

    pipe.stop()
    elapsed = time.time() - t0
    print(f"Frames: {frames_seen} in {elapsed:.1f} s  ->  {frames_seen / elapsed:.1f} fps")

    banner("Depth sanity")
    centre = depth_img[H // 2 - 40:H // 2 + 40, W // 2 - 40:W // 2 + 40].astype(float) * scale
    valid = centre[(centre > 0.05) & (centre < 1.0)]
    if valid.size == 0:
        print("No valid depth in the centre patch.")
        print("The D405 sees from about 70 mm; closer than that returns nothing. Back off to 150-300 mm.")
    else:
        print(f"Valid pixels in centre patch : {100 * valid.size / centre.size:.0f} %")
        print(f"Distance (median)            : {np.median(valid) * 1000:.0f} mm")
        print(f"Spread (5th to 95th pct)     : {np.percentile(valid, 5) * 1000:.0f}"
              f" to {np.percentile(valid, 95) * 1000:.0f} mm")
        if np.median(valid) < 0.07:
            print("Closer than the minimum range: move back, this is the usual cause of a failed grasp.")

    cv2.imwrite(str(OUT / "color.png"), color_img)
    colourised = cv2.applyColorMap(
        cv2.convertScaleAbs(depth_img, alpha=0.08), cv2.COLORMAP_TURBO)
    cv2.imwrite(str(OUT / "depth.png"), colourised)
    print(f"\nWrote {OUT / 'color.png'} and {OUT / 'depth.png'}")
    print("Hold a leaf about 200 mm away and run again: the leaf should read as a clean blob,")
    print("not speckle. Speckle at that range usually means too little light or a smeared lens.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
