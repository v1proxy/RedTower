"""Take one real capture with the D405 and run perception on it (task 8).
  python tools_d405_check.py [output folder]
Writes d405_color.jpg, d405_annotated.jpg and d405_observation.json."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gh.mods.d405 import RealSense                       # noqa: E402
from gh.mods.perception import FAR_M, NEAR_M, analyse    # noqa: E402

out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
out.mkdir(parents=True, exist_ok=True)
cam = RealSense()
print("camera serial", cam.serial, "intrinsics", {k: round(v, 1) for k, v in cam.intr.items()})
color, depth, intr = cam.grab()
cam.close()
valid = (depth > NEAR_M) & (depth < FAR_M)
print("frame", color.shape, "depth range m", round(float(depth[depth > 0].min()), 3) if (depth > 0).any() else None,
      round(float(depth.max()), 3), "pixels in working band", round(float(valid.mean()), 3))
obs, annotated = analyse(color, depth, intr)
cv2.imwrite(str(out / "d405_color.jpg"), color)
cv2.imwrite(str(out / "d405_annotated.jpg"), annotated)
vis = cv2.applyColorMap(np.clip(depth / FAR_M * 255, 0, 255).astype(np.uint8), cv2.COLORMAP_TURBO)
vis[depth == 0] = 0
cv2.imwrite(str(out / "d405_depth.jpg"), vis)
(out / "d405_observation.json").write_text(json.dumps(obs, indent=1))
print(json.dumps({k: v for k, v in obs.items() if k != "candidates"}))
print("candidates", [(c["label"], c["kind"], c["xyz_mm"]) for c in obs["candidates"]])
