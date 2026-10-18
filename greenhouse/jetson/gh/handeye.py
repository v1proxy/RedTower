"""Hand-eye calibration: the fixed transform from the arm's flange to the D405.

A chessboard sits still in the cabinet and the arm looks at it from 10 to 15 poses. At each
pose the arm reports its flange pose in its base frame and the image gives the board pose in
the camera frame. Tsai's method finds the flange-to-camera transform that makes the two
agree. Because the board never moved, its position in the base frame has to come out the
same at every pose: the worst pose's distance from the mean is the quality number.

Everything is in millimetres. Transforms are 4x4 matrices, T_a_b maps b coordinates into a.
"""
import json
import math
import time

import cv2
import numpy as np

CONVENTIONS = ("xyz", "zyx")       # the arm's Euler order is checked, not assumed: see solve_any
GOOD_MM, USABLE_MM = 3.0, 8.0
MIN_ROTATION_DEG = 30.0            # less rotation than this between poses cannot pin the rotation down
MIN_POSES = 8


def _rx(a): c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def _ry(a): c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def _rz(a): c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def euler_to_R(rx, ry, rz, order="xyz"):
    """Degrees. "xyz": rotate about fixed x, then y, then z (roll, pitch, yaw): Rz Ry Rx.
    "zyx": the reverse: Rx Ry Rz."""
    a, b, c = (math.radians(v) for v in (rx, ry, rz))
    return _rz(c) @ _ry(b) @ _rx(a) if order == "xyz" else _rx(a) @ _ry(b) @ _rz(c)


def R_to_euler(R, order="xyz"):
    if order == "xyz":
        rx, ry, rz = math.atan2(R[2, 1], R[2, 2]), math.asin(-R[2, 0]), math.atan2(R[1, 0], R[0, 0])
    else:
        rx, ry, rz = math.atan2(-R[1, 2], R[2, 2]), math.asin(R[0, 2]), math.atan2(-R[0, 1], R[0, 0])
    return [math.degrees(v) for v in (rx, ry, rz)]


def transform(R, t):
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = R, np.ravel(t)
    return T


def flange_pose(coords, order="xyz"):
    """The arm's get_coords() [x, y, z, rx, ry, rz] (mm, degrees) as T_base_flange."""
    x, y, z, rx, ry, rz = (float(v) for v in coords)
    return transform(euler_to_R(rx, ry, rz, order), [x, y, z])


def board_points(corners=(6, 4), square_mm=10.0):
    cols, rows = corners
    return np.array([[i * square_mm, j * square_mm, 0.0] for j in range(rows) for i in range(cols)], np.float32)


def normalise(found, corners):
    """One board frame in every view. OpenCV may number the corners from any end of the grid,
    and a board whose two corner counts have the same parity looks the same turned 180 degrees.
    Mirrored orderings are undone (the printed board is always seen from the front), then the
    first corner is taken as the one nearer the image's top left. Keep the camera's roll within
    about 70 degrees of the board's edges while calibrating."""
    cols, rows = corners
    g = found.reshape(rows, cols, 2)
    xd, yd = g[0, -1] - g[0, 0], g[-1, 0] - g[0, 0]
    if xd[0] * yd[1] - xd[1] * yd[0] < 0:
        g = g[:, ::-1]
    if g[0, 0].sum() > g[-1, -1].sum():
        g = g[::-1, ::-1]
    return np.ascontiguousarray(g.reshape(-1, 1, 2))


def find_board(image, intr, corners=(6, 4), square_mm=10.0):
    """T_cam_board and the RMS reprojection error in pixels, or None if no board is seen."""
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ok, found = cv2.findChessboardCorners(gray, corners, cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE)
    if not ok:
        return None
    found = cv2.cornerSubPix(gray, found, (5, 5), (-1, -1),
                             (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.01))
    found = normalise(found, corners)
    K = np.array([[intr["fx"], 0, intr["cx"]], [0, intr["fy"], intr["cy"]], [0, 0, 1]], np.float64)
    obj = board_points(corners, square_mm)
    ok, rvec, tvec = cv2.solvePnP(obj, found, K, None, flags=cv2.SOLVEPNP_IPPE)
    if not ok:
        return None
    proj, _ = cv2.projectPoints(obj, rvec, tvec, K, None)
    rms = float(np.sqrt(np.mean(np.sum((proj - found) ** 2, axis=2))))
    return transform(cv2.Rodrigues(rvec)[0], tvec), rms


def rotation_span(flanges):
    """The largest rotation between any two flange poses, in degrees."""
    best = 0.0
    for i, a in enumerate(flanges):
        for b in flanges[i + 1:]:
            R = a[:3, :3].T @ b[:3, :3]
            best = max(best, math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2)))))
    return best


def _skew(v):
    return np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])


def _rodrigues_mod(R):
    """Modified Rodrigues vector 2 sin(angle / 2) * axis, as Tsai and Lenz use it."""
    rvec = cv2.Rodrigues(R)[0].ravel()
    angle = np.linalg.norm(rvec)
    return np.zeros(3) if angle < 1e-12 else 2 * math.sin(angle / 2) * rvec / angle


def tsai(flanges, boards):
    """Tsai and Lenz (1989): solve A X = X B for X = T_flange_cam over consecutive pose pairs,
    A the flange motion and B the matching camera motion. Rotation first, then translation, both
    by least squares. Written out here because OpenCV 5's Python build no longer exposes
    calibrateHandEye."""
    rows_r, rhs_r, motions = [], [], []
    for i in range(len(flanges) - 1):
        A = np.linalg.inv(flanges[i + 1]) @ flanges[i]
        B = boards[i + 1] @ np.linalg.inv(boards[i])
        pa, pb = _rodrigues_mod(A[:3, :3]), _rodrigues_mod(B[:3, :3])
        rows_r.append(_skew(pa + pb))
        rhs_r.append(pb - pa)
        motions.append((A, B))
    p = np.linalg.lstsq(np.vstack(rows_r), np.concatenate(rhs_r), rcond=None)[0]
    p = 2 * p / math.sqrt(1 + p @ p)
    R = (1 - (p @ p) / 2) * np.eye(3) + 0.5 * (np.outer(p, p) + math.sqrt(max(0.0, 4 - p @ p)) * _skew(p))
    rows_t = [A[:3, :3] - np.eye(3) for A, _ in motions]
    rhs_t = [R @ B[:3, 3] - A[:3, 3] for A, B in motions]
    t = np.linalg.lstsq(np.vstack(rows_t), np.concatenate(rhs_t), rcond=None)[0]
    return transform(R, t)


def solve(flanges, boards):
    """flanges: T_base_flange per pose. boards: T_cam_board per pose. Returns T_flange_cam and
    where the board landed in the base frame at each pose."""
    X = tsai(flanges, boards)
    in_base = [F @ X @ B for F, B in zip(flanges, boards)]
    origins = np.array([T[:3, 3] for T in in_base])
    dist = np.linalg.norm(origins - origins.mean(axis=0), axis=1)
    U, _, Vt = np.linalg.svd(sum(T[:3, :3] for T in in_base))       # mean board orientation
    mean_R = U @ Vt
    turn = [math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(mean_R.T @ T[:3, :3]) - 1) / 2)))) for T in in_base]
    return {"T_flange_cam": X, "spread_mm": float(dist.max()), "per_pose_mm": [round(float(d), 2) for d in dist],
            "worst_pose": int(dist.argmax()), "rotation_spread_deg": round(max(turn), 2),
            "rotation_span_deg": round(rotation_span(flanges), 1), "poses": len(flanges)}


def solve_any(coords, boards):
    """Solve with each Euler order the arm might use and keep the consistent one. With the
    wrong order the board 'moves' between poses by centimetres, so the spread tells them apart."""
    results = []
    for order in CONVENTIONS:
        r = solve([flange_pose(c, order) for c in coords], boards)
        r["convention"] = order
        results.append(r)
    best = min(results, key=lambda r: r["spread_mm"])
    best["other_spread_mm"] = round(max(r["spread_mm"] for r in results), 1)
    return best


def verdict(result):
    """(usable, one line for the owner)."""
    s, span, n = result["spread_mm"], result["rotation_span_deg"], result["poses"]
    if n < MIN_POSES:
        return False, f"only {n} poses with the board found; take at least {MIN_POSES}"
    if span < MIN_ROTATION_DEG:
        return False, (f"the poses turn the camera by only {span:.0f} degrees; tilt and roll the wrist more, "
                       "mostly-translation poses cannot fix the rotation")
    if s < GOOD_MM:
        return True, f"spread {s:.1f} mm: good"
    if s < USABLE_MM:
        return True, f"spread {s:.1f} mm: usable for leaf work"
    return False, (f"spread {s:.1f} mm, worst at pose {result['worst_pose'] + 1}: the board moved, the square size "
                   "is wrong (measure a printed square with calipers), or that pose's image is poor")


def save(result, path):
    body = {k: v for k, v in result.items() if k != "T_flange_cam"}
    body.update(T_flange_cam=np.round(result["T_flange_cam"], 6).tolist(), ts=time.time())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=1))


def load(path):
    body = json.loads(path.read_text())
    body["T_flange_cam"] = np.array(body["T_flange_cam"])
    return body
