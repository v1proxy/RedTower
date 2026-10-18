"""First frame from the overview camera, with the pot regions drawn on it (commissioning).
Stop gh-widecam first: only one program may hold the camera.

  python tools_widecam_check.py [device] [output folder]     device defaults to 0 (/dev/video0)

Writes widecam_frame.jpg and widecam_regions.jpg. Adjust config/widecam.yaml until every box
holds one pot and its plant, with the lights at their day setting.
"""
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gh.mods.widecam import V4l2, load_rois, measure     # noqa: E402

device = sys.argv[1] if len(sys.argv) > 1 else 0
device = int(device) if str(device).isdigit() else device
out = Path(sys.argv[2] if len(sys.argv) > 2 else ".")
out.mkdir(parents=True, exist_ok=True)
frame = V4l2(device, 1920, 1080).grab()
print("frame", frame.shape[1], "x", frame.shape[0])
cv2.imwrite(str(out / "widecam_frame.jpg"), frame)
for pos, (x, y, w, h) in load_rois(Path(__file__).resolve().parent / "config" / "widecam.yaml")["regions"].items():
    m = measure(frame, (x, y, w, h))
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
    cv2.putText(frame, pos, (x + 4, y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    print(f"{pos}: canopy {m['canopy_fraction']:.3f}")
cv2.imwrite(str(out / "widecam_regions.jpg"), frame)
print("wrote", out / "widecam_frame.jpg", "and", out / "widecam_regions.jpg")
