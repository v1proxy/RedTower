#!/usr/bin/env python3
"""Turn one D405 capture of one plant into geometry a tender agent can act on.

The D405 gives colour and depth from the same stereo pair, so a pixel in the colour
image is a pixel in the depth image. That lets us answer in millimetres: how tall is
this plant, how wide is the canopy, where are the growth tips, which leaf is nearest
the camera, and what surface normal would a gripper meet if it approached that leaf.

Nothing here talks to a model. It produces numbers and a set of labelled candidate
points (C1, C2, ...) drawn onto an annotated image. The agent then chooses among the
labels. That split matters: a wrong number here is a bad measurement, while a model
inventing a coordinate would be a blade in the wrong place.

Camera frame convention (RealSense): +x right, +y down, +z forward, metres.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple

import cv2
import numpy as np

NEAR_M, FAR_M = 0.07, 0.45          # the D405's honest working band for this rig
MIN_LEAF_PX = 400                    # a blob this big counts as a leaf when counting leaves
MIN_BLOB_PX = 150                    # a blob this big can still belong to the plant (tips are small)
CLUSTER_MM = 70.0                    # radius around the anchor blob that is still this plant
DEDUP_MM = 15.0                      # candidates closer than this to an existing one are the same spot
TIP_MIN_MM = 12.0                    # a growth tip has to stand this clear of the soil
TIP_SPREAD_MM = 15.0                 # a second tip must be within this of the highest one


@dataclass
class Candidate:
    """One place on the plant the arm could go, with everything needed to go there."""
    label: str                       # C1, C2, ... what the agent refers to
    kind: str                        # tip | leaf | stem
    pixel: Tuple[int, int]
    point_m: Tuple[float, float, float]      # camera frame, metres
    normal: Tuple[float, float, float]       # unit surface normal, camera frame
    area_mm2: float
    height_above_soil_mm: float
    confidence: float                # 0-1, from depth validity and blob compactness


@dataclass
class PlantGeometry:
    plant_id: str
    ok: bool
    reason: str = ""
    soil_distance_mm: float = 0.0
    canopy_width_mm: float = 0.0
    canopy_depth_mm: float = 0.0
    canopy_area_mm2: float = 0.0
    canopy_height_mm: float = 0.0            # how far the canopy rises off the soil plane
    leaf_count: int = 0
    greenness: float = 0.0                   # 0-100, mean excess-green of plant pixels
    yellow_fraction: float = 0.0             # 0-100, discoloured share of plant pixels
    valid_depth_fraction: float = 0.0        # 0-100, sanity check on the capture itself
    centroid_m: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    candidates: List[Candidate] = field(default_factory=list)

    def brief(self) -> dict:
        """Compact dict for the agent prompt: numbers only, no arrays."""
        d = asdict(self)
        d["candidates"] = [
            {"label": c.label, "kind": c.kind,
             "height_above_soil_mm": round(c.height_above_soil_mm, 1),
             "area_mm2": round(c.area_mm2), "confidence": round(c.confidence, 2),
             "distance_mm": round(c.point_m[2] * 1000, 1)}
            for c in self.candidates]
        return d


def _excess_green(bgr: np.ndarray) -> np.ndarray:
    f = bgr.astype(np.float32) / 255.0
    b, g, r = f[..., 0], f[..., 1], f[..., 2]
    s = r + g + b + 1e-6
    return 2 * g / s - r / s - b / s


def _soil_plane(depth_m: np.ndarray) -> float:
    """Rough distance to the soil, before we know which pixels are plant.

    Looking down into a pot, the single most common depth in the frame is the soil surface
    and the tray around it. The modal depth is therefore a better first guess than a
    percentile, which drifts as the canopy grows. Needed before masking because soil brown
    and a dying leaf are nearly the same colour, so colour alone cannot separate them.
    """
    d = depth_m[(depth_m > NEAR_M) & (depth_m < FAR_M)]
    if d.size < 500:
        return FAR_M
    hist, edges = np.histogram(d, bins=np.arange(NEAR_M, FAR_M + 0.005, 0.005))
    far = edges[:-1] >= np.median(d)                 # the soil is never nearer than the median
    if not far.any():
        return float(np.median(d))
    i = int(np.argmax(np.where(far, hist, 0)))
    return float(edges[i] + 0.0025)


def _plant_mask(bgr: np.ndarray, depth_m: np.ndarray, soil_m: float) -> np.ndarray:
    """Plant = green enough, or sick-coloured and standing clear of the soil."""
    exg = _excess_green(bgr)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    green = (exg > 0.04) & (val > 35)
    # Yellowing and browning leaves are still plant: a tender agent must see sick tissue.
    # But potting soil sits in the same hue band, so sick tissue has to also stand above the
    # soil plane. Without that test the whole pot reads as one large diseased leaf.
    above_soil = depth_m < (soil_m - 0.006)
    sick = (hue >= 12) & (hue <= 34) & (sat > 70) & (val > 60) & above_soil
    in_range = (depth_m > NEAR_M) & (depth_m < FAR_M)
    mask = ((green | sick) & in_range).astype(np.uint8)
    k = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    return mask


def _plant_cluster(mask: np.ndarray, depth_m: np.ndarray, fx: float) -> np.ndarray:
    """Keep the blobs belonging to the pot we are parked over, and drop the neighbour's.

    From above, one plant is not one blob: leaves are separated by gaps of visible soil, and
    a growth tip standing above the canopy is usually its own island. So we pick an anchor
    blob (big and near the image centre, which is the pot the gantry stopped at) and keep
    every other blob whose centre falls within CLUSTER_MM of it, converted to pixels at the
    anchor's own depth. Herb pots sit on a 132 mm pitch, so a 70 mm radius takes this plant's
    leaves and usually leaves the neighbour's alone. When canopies genuinely overlap, an
    intruding leaf will be visible in the annotated image, which is the point of annotating it.
    """
    n, labels, stats, cents = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n <= 1:
        return mask
    h, w = mask.shape
    cx, cy = w / 2, h / 2
    blobs = [(stats[i, cv2.CC_STAT_AREA] - 8 * np.hypot(cents[i][0] - cx, cents[i][1] - cy), i)
             for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= MIN_BLOB_PX]
    if not blobs:
        return mask
    anchor = max(blobs)[1]                                # big and central wins
    az = depth_m[labels == anchor]
    az = float(np.median(az[(az > NEAR_M) & (az < FAR_M)])) if np.any(
        (az > NEAR_M) & (az < FAR_M)) else FAR_M
    r_px = (CLUSTER_MM / 1000.0) * fx / max(az, 1e-6)
    ax, ay = cents[anchor]
    out = np.zeros_like(mask)
    for _, i in blobs:
        if np.hypot(cents[i][0] - ax, cents[i][1] - ay) <= r_px:
            out[labels == i] = 1
    return out


def _normal_at(depth_m: np.ndarray, u: int, v: int, fx: float, fy: float,
               ppx: float, ppy: float, win: int = 9, tol: float = 0.008):
    """Surface normal from a plane fit over the local 3D points, so the gripper meets a leaf square on.

    Only points within `tol` of the centre pixel's own depth join the fit. That matters at a
    leaf edge: include the surface behind it and the fit tips over toward the step instead of
    following the leaf, which would send the gripper in sideways.

    Returns a unit vector pointing back toward the camera, which is the direction to approach from.
    """
    h, w = depth_m.shape
    z0 = float(depth_m[v, u])
    if not (NEAR_M < z0 < FAR_M):
        return (0.0, 0.0, -1.0)
    u0, u1 = max(0, u - win), min(w, u + win + 1)
    v0, v1 = max(0, v - win), min(h, v + win + 1)
    patch = depth_m[v0:v1, u0:u1]
    vs, us = np.nonzero((np.abs(patch - z0) < tol) & (patch > NEAR_M) & (patch < FAR_M))
    if us.size < 12:
        return (0.0, 0.0, -1.0)
    zs = patch[vs, us].astype(np.float64)
    X = ((us + u0) - ppx) * zs / fx
    Y = ((vs + v0) - ppy) * zs / fy
    P = np.stack([X, Y, zs], axis=1)
    P -= P.mean(axis=0)
    _, _, Vt = np.linalg.svd(P, full_matrices=False)
    n = Vt[-1]                                            # least-variance direction = plane normal
    if n[2] > 0:
        n = -n                                            # camera looks along +z, so approach is -z
    n /= np.linalg.norm(n) + 1e-9
    return tuple(float(x) for x in n)


def analyse(plant_id: str, bgr: np.ndarray, depth_m: np.ndarray,
            intrinsics, max_candidates: int = 6) -> PlantGeometry:
    """Full per-plant analysis from one aligned RGBD capture.

    `intrinsics` needs .fx .fy .ppx .ppy, which is what rs.video_stream_profile gives.
    `depth_m` is the aligned depth image in metres, same shape as bgr.
    """
    g = PlantGeometry(plant_id=plant_id, ok=False)
    in_range = (depth_m > NEAR_M) & (depth_m < FAR_M)
    g.valid_depth_fraction = round(100.0 * in_range.mean(), 1)
    if in_range.mean() < 0.02:
        g.reason = ("almost no depth in the working band: the arm is probably too far from the pot, "
                    "or closer than the 70 mm minimum")
        return g

    soil_guess = _soil_plane(depth_m)
    mask = _plant_cluster(_plant_mask(bgr, depth_m, soil_guess), depth_m, intrinsics.fx)
    if mask.sum() < MIN_LEAF_PX:
        g.reason = "no plant-coloured region found in range: empty pot, or the pose missed the plant"
        return g

    plant = mask.astype(bool)
    fx, fy = intrinsics.fx, intrinsics.fy
    ppx, ppy = intrinsics.ppx, intrinsics.ppy

    # Soil plane, refined: the in-range pixels that are not plant sit on soil and pot rim.
    soil_pixels = depth_m[in_range & ~plant]
    soil = float(np.median(soil_pixels)) if soil_pixels.size > 200 else soil_guess
    g.soil_distance_mm = round(soil * 1000, 1)

    pd = depth_m[plant]
    pd = pd[(pd > NEAR_M) & (pd < FAR_M)]
    if pd.size < 50:
        g.reason = "plant region has no usable depth"
        return g

    # Metric size: each pixel covers (z/fx)*(z/fy) m2, so area is depth-weighted, not a pixel count.
    ys, xs = np.nonzero(plant)
    zs = depth_m[ys, xs]
    ok = (zs > NEAR_M) & (zs < FAR_M)
    ys, xs, zs = ys[ok], xs[ok], zs[ok]
    X = (xs - ppx) * zs / fx
    Y = (ys - ppy) * zs / fy
    g.canopy_width_mm = round(float(X.max() - X.min()) * 1000, 1)
    g.canopy_depth_mm = round(float(Y.max() - Y.min()) * 1000, 1)
    g.canopy_area_mm2 = round(float(np.sum((zs / fx) * (zs / fy))) * 1e6, 1)
    g.canopy_height_mm = round(max(0.0, (soil - float(np.percentile(zs, 2)))) * 1000, 1)
    g.centroid_m = (round(float(X.mean()), 4), round(float(Y.mean()), 4), round(float(zs.mean()), 4))

    exg = _excess_green(bgr)
    g.greenness = round(float(np.clip(exg[plant].mean() * 250, 0, 100)), 1)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    yellowish = ((hsv[..., 0] >= 12) & (hsv[..., 0] <= 34) & (hsv[..., 1] > 70))
    g.yellow_fraction = round(100.0 * float(yellowish[plant].mean()), 1)

    # Leaves: erode to split touching blades, then count what survives.
    eroded = cv2.erode(mask, np.ones((7, 7), np.uint8), iterations=1)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(eroded, connectivity=8)
    leaves = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= MIN_LEAF_PX]
    g.leaf_count = len(leaves)

    cands: List[Candidate] = []

    def add(kind, u, v, area_px, conf):
        z = float(depth_m[v, u])
        if not (NEAR_M < z < FAR_M):
            return
        pt = ((u - ppx) * z / fx, (v - ppy) * z / fy, z)
        # A growth tip is also the centroid of its own small blob, so it would otherwise be
        # offered twice, once as a tip and once as a leaf. The agent must not be able to
        # "harvest a leaf" that is really the growth point.
        for c in cands:
            if np.linalg.norm(np.subtract(c.point_m, pt)) * 1000 < DEDUP_MM:
                return
        area_mm2 = area_px * (z / fx) * (z / fy) * 1e6
        cands.append(Candidate(label=f"C{len(cands) + 1}", kind=kind, pixel=(int(u), int(v)),
                               point_m=tuple(round(p, 4) for p in pt),
                               normal=_normal_at(depth_m, u, v, fx, fy, ppx, ppy),
                               area_mm2=round(area_mm2, 1),
                               height_above_soil_mm=round(max(0.0, (soil - z)) * 1000, 1),
                               confidence=round(float(conf), 2)))

    # Growth tips: plant pixels closest to the camera, which looking down means highest.
    # A tip has to stand clear of the soil and be a near-match for the highest point found,
    # otherwise an ordinary mid-canopy leaf gets labelled a growth tip and offered for pinching.
    z_plant = np.where(plant, depth_m, np.inf)
    top_mm = None
    for _ in range(2):
        v, u = np.unravel_index(np.argmin(z_plant), z_plant.shape)
        z = float(z_plant[v, u])
        if not np.isfinite(z):
            break
        h_mm = (soil - z) * 1000
        if h_mm < TIP_MIN_MM or (top_mm is not None and h_mm < top_mm - TIP_SPREAD_MM):
            break
        blob = np.zeros_like(mask)
        cv2.circle(blob, (int(u), int(v)), 25, 1, -1)
        add("tip", int(u), int(v), int((blob & mask).sum()), 0.9)
        top_mm = h_mm if top_mm is None else top_mm
        cv2.circle(z_plant, (int(u), int(v)), 40, np.inf, -1)   # suppress, find the next tip

    # Leaf centres, biggest first: these are the grasp or cut targets.
    for i in sorted(leaves, key=lambda i: -stats[i, cv2.CC_STAT_AREA])[:max_candidates - len(cands)]:
        u, v = int(cents[i][0]), int(cents[i][1])
        if not plant[min(v, plant.shape[0] - 1), min(u, plant.shape[1] - 1)]:
            continue
        compact = stats[i, cv2.CC_STAT_AREA] / max(1, stats[i, cv2.CC_STAT_WIDTH] * stats[i, cv2.CC_STAT_HEIGHT])
        add("leaf", u, v, stats[i, cv2.CC_STAT_AREA], 0.5 + 0.5 * compact)

    g.candidates = cands[:max_candidates]
    g.ok = len(g.candidates) > 0
    if not g.ok:
        g.reason = "found a plant but no candidate point had valid depth"
    return g


def annotate(bgr: np.ndarray, geo: PlantGeometry) -> np.ndarray:
    """Draw the candidates so the agent can refer to them by label."""
    img = bgr.copy()
    for c in geo.candidates:
        u, v = c.pixel
        colour = (0, 220, 255) if c.kind == "tip" else (80, 255, 80)
        cv2.circle(img, (u, v), 14, colour, 2)
        cv2.line(img, (u - 20, v), (u - 6, v), colour, 2)
        text = f"{c.label} {c.kind} {c.height_above_soil_mm:.0f}mm"
        # Outline first: a label has to stay readable over a bright leaf as well as dark soil,
        # because the agent reads these labels out of the image and cannot ask what one said.
        cv2.putText(img, text, (u + 18, v + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, text, (u + 18, v + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    colour, 1, cv2.LINE_AA)
    header = (f"{geo.plant_id}  canopy {geo.canopy_width_mm:.0f}x{geo.canopy_depth_mm:.0f} mm  "
              f"h {geo.canopy_height_mm:.0f} mm  leaves {geo.leaf_count}  yellow {geo.yellow_fraction:.0f}%")
    cv2.rectangle(img, (0, 0), (img.shape[1], 26), (20, 20, 20), -1)
    cv2.putText(img, header, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def from_realsense(plant_id: str, color_bgr: np.ndarray, depth_frame, max_candidates: int = 6):
    """Convenience wrapper for a live rs depth frame (already aligned to colour)."""
    intr = depth_frame.profile.as_video_stream_profile().intrinsics
    scale = 0.001 if depth_frame.get_units() == 0 else depth_frame.get_units()
    depth_m = np.asanyarray(depth_frame.get_data()).astype(np.float32) * scale
    geo = analyse(plant_id, color_bgr, depth_m, intr, max_candidates)
    return geo, annotate(color_bgr, geo)
