"""Hand-eye calibration of the D405 on the myCobot flange (open item in the design basis).

Stop gh-arm and gh-d405 first: this tool talks to both directly. Doors closed, gantry parked.

1. Capture. Fix a printed chessboard flat in the cabinet so it cannot move. For each pose,
   move the arm by hand or with myStudio so the whole board is in view, then press Enter.
   Take 10 to 15 poses, tilting and rolling the wrist by 40 degrees or more between them:
   poses that mostly slide the camera cannot fix its rotation.

     python tools_handeye_calibrate.py capture calib_out --host 192.168.10.25

2. Solve. Detects the board in every image, solves (Tsai), prints the spread and saves
   handeye.json to the data folder when it is usable.

     python tools_handeye_calibrate.py solve calib_out [--corners 6x4] [--square 10] [--force]

The board: --corners counts INNER corners (a board of 7 by 5 squares has 6 by 4). Measure a
printed square with calipers and pass it with --square; a printer's scaling makes the board's
distances wrong by the same factor. In simulation, 20 mm squares halved the error of 10 mm
ones, and the true error at a leaf 200 mm ahead was up to about twice the reported spread.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gh import handeye as H                                 # noqa: E402


def capture(args):
    from gh.mods.d405 import RealSense
    from gh.mods.mycobot import connect
    out = Path(args.folder)
    out.mkdir(parents=True, exist_ok=True)
    mc, cam = connect(args.host, args.port), RealSense()
    (out / "intr.json").write_text(json.dumps(cam.intr))
    n = len(list(out.glob("pose_*.json")))
    print("Enter: record this pose.  r: release the servos to move by hand.  l: lock them.  q: finish.")
    while True:
        key = input(f"pose {n + 1}> ").strip().lower()
        if key == "q":
            break
        if key == "r":
            mc.release_all_servos()
            continue
        if key == "l":
            mc.power_on()
            continue
        coords = mc.get_coords()
        if not (isinstance(coords, list) and len(coords) == 6):
            print("  the arm returned no coordinates; lock the servos (l) and try again")
            continue
        color = cam.grab()[0]
        found = H.find_board(color, cam.intr, args.corners, args.square)
        n += 1
        cv2.imwrite(str(out / f"pose_{n:02d}.jpg"), color, [cv2.IMWRITE_JPEG_QUALITY, 95])
        (out / f"pose_{n:02d}.json").write_text(json.dumps({"coords": coords}))
        print(f"  saved. board {'found, reprojection %.2f px' % found[1] if found else 'NOT found: move so all of it is in view'}")
    cam.close()


def solve(args):
    folder = Path(args.folder)
    intr = json.loads((folder / "intr.json").read_text())
    coords, boards, used = [], [], []
    for meta in sorted(folder.glob("pose_*.json")):
        found = H.find_board(cv2.imread(str(meta.with_suffix(".jpg"))), intr, args.corners, args.square)
        if found is None:
            print(f"{meta.stem}: no board, skipped")
            continue
        coords.append(json.loads(meta.read_text())["coords"])
        boards.append(found[0])
        used.append(meta.stem)
        print(f"{meta.stem}: board found, reprojection {found[1]:.2f} px")
    if len(coords) < 3:
        sys.exit("fewer than 3 poses with the board: nothing to solve")
    r = H.solve_any(coords, boards)
    ok, text = H.verdict(r)
    print(f"\nEuler order {r['convention']} (the other order spreads {r['other_spread_mm']} mm)")
    print(f"poses {r['poses']}, wrist rotation span {r['rotation_span_deg']} degrees, "
          f"board orientation spread {r['rotation_spread_deg']} degrees")
    for name, d in zip(used, r["per_pose_mm"]):
        print(f"  {name}: {d} mm from the mean")
    print(("PASS  " if ok else "FAIL  ") + text)
    T = r["T_flange_cam"]
    print("camera in the flange frame, mm:", [round(float(v), 1) for v in T[:3, 3]])
    if ok or args.force:
        path = Path(args.out or Path(os.environ.get("GH_DATA_DIR", "/data")) / "handeye.json")
        H.save(r, path)
        print("saved", path)
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("capture", "solve"))
    ap.add_argument("folder")
    ap.add_argument("--host", default="192.168.10.25")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--corners", default="6x4", type=lambda s: tuple(int(v) for v in s.lower().split("x")))
    ap.add_argument("--square", type=float, default=10.0, help="measured square size in mm")
    ap.add_argument("--out", help="where to write handeye.json (default: the data folder)")
    ap.add_argument("--force", action="store_true", help="save even if the spread is not usable")
    args = ap.parse_args()
    capture(args) if args.mode == "capture" else solve(args)


if __name__ == "__main__":
    main()
