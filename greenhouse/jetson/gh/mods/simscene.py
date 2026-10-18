"""Synthetic plant scenes for the simulated depth camera and for tests.
Returns a colour image (BGR), a depth image in metres and pinhole intrinsics, laid out the
way the D405 sees a pot from the front at about 25 cm."""
import cv2
import numpy as np

W, H = 640, 480
INTR = {"fx": 430.0, "fy": 430.0, "cx": 320.0, "cy": 240.0, "width": W, "height": H}


def make_scene(seed=0, stage=2, yellow_leaf=False, fruit=False, empty=False):
    rng = np.random.default_rng(seed)
    color = np.full((H, W, 3), (38, 36, 34), np.uint8)
    depth = np.zeros((H, W), np.float32)                      # 0 = no return (far background)

    def blob(center, axes, bgr, z, angle=0):
        mask = np.zeros((H, W), np.uint8)
        cv2.ellipse(mask, center, axes, angle, 0, 360, 255, -1)
        color[mask > 0] = bgr
        depth[mask > 0] = z

    cv2.rectangle(color, (220, 380), (420, 470), (60, 70, 90), -1)        # pot
    depth[380:470, 220:420] = 0.27
    blob((320, 378), (95, 16), (40, 60, 85), 0.27)                         # soil surface
    if empty:
        return color, depth, dict(INTR)
    top = 360 - 50 - stage * 55
    cv2.line(color, (320, 372), (320, top), (40, 120, 50), 6)             # stem
    cv2.line(depth, (320, 372), (320, top), 0.25, 6)
    for i in range(2 + stage * 2):
        y = int(360 - 30 - i * (330 - top) / max(1, 1 + stage * 2))
        side = -1 if i % 2 else 1
        cx = 320 + side * int(45 + rng.integers(0, 25))
        blob((cx, y), (38, 15), (45, int(150 + rng.integers(0, 40)), 55), 0.22 + 0.01 * (i % 3), angle=side * 20)
    blob((320, top - 8), (20, 12), (60, 190, 70), 0.24)                    # growth tip
    if yellow_leaf:
        blob((250, 345), (34, 13), (40, 200, 210), 0.23, angle=-15)
    if fruit:
        blob((360, top + 60), (16, 22), (40, 40, 200), 0.21)
    return color, depth, dict(INTR)
