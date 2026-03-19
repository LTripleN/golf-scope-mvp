"""
pose_metrics.py
MediaPipe Pose detection and 2D swing-metric computation.

Uses the mediapipe.tasks.vision.PoseLandmarker API (v0.10.x+).

All spatial metrics are normalised by *body_scale* (shoulder width in pixels)
so the numbers are independent of how far the golfer stands from the camera.
"""

import math
import os
from typing import Dict, List, Optional, Tuple

import cv2
import mediapipe as mp

# ---------------------------------------------------------------------------
# MediaPipe Task-based API references
# ---------------------------------------------------------------------------
_vision = mp.tasks.vision
_PoseLandmark = _vision.PoseLandmark
_PoseLandmarker = _vision.PoseLandmarker
_PoseLandmarkerOptions = _vision.PoseLandmarkerOptions
_BaseOptions = mp.tasks.BaseOptions

# Model path – lives next to this file; also works when deployed to Render.
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "pose_landmarker_full.task")

# Landmark indices we care about (same int values as the enum)
_LANDMARKS_OF_INTEREST = {
    "nose": _PoseLandmark.NOSE,
    "left_shoulder": _PoseLandmark.LEFT_SHOULDER,
    "right_shoulder": _PoseLandmark.RIGHT_SHOULDER,
    "left_hip": _PoseLandmark.LEFT_HIP,
    "right_hip": _PoseLandmark.RIGHT_HIP,
    "left_knee": _PoseLandmark.LEFT_KNEE,
    "right_knee": _PoseLandmark.RIGHT_KNEE,
    "left_ankle": _PoseLandmark.LEFT_ANKLE,
    "right_ankle": _PoseLandmark.RIGHT_ANKLE,
    "left_wrist": _PoseLandmark.LEFT_WRIST,
    "right_wrist": _PoseLandmark.RIGHT_WRIST,
}


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------
def _load_image_bgr(path: str, target_width: int = 640):
    """Read *path* with OpenCV and resize to *target_width* keeping aspect ratio."""
    img = cv2.imread(path)
    if img is None:
        raise RuntimeError(f"OpenCV could not read image at {path}")
    h, w = img.shape[:2]
    if w != target_width:
        scale = target_width / w
        new_h = int(h * scale)
        img = cv2.resize(img, (target_width, new_h), interpolation=cv2.INTER_AREA)
    return img


# ---------------------------------------------------------------------------
# MediaPipe helper
# ---------------------------------------------------------------------------
def _run_mediapipe_pose(image_bgr) -> Optional[List]:
    """Run PoseLandmarker on a BGR image."""
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

    options = _PoseLandmarkerOptions(
        base_options=_BaseOptions(model_asset_path=_MODEL_PATH),
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
    )
    with _PoseLandmarker.create_from_options(options) as landmarker:
        result = landmarker.detect(mp_image)

    if not result.pose_landmarks or len(result.pose_landmarks) == 0:
        return None
    return result.pose_landmarks[0]


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def _get_point(
    landmarks: List, index: int, width: int, height: int
) -> Tuple[float, float]:
    """Convert normalised MediaPipe landmark to pixel (x, y)."""
    lm = landmarks[index]
    return lm.x * width, lm.y * height


def _distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def _angle(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
) -> float:
    """Angle in degrees at vertex *b*."""
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.hypot(*ba)
    mag_bc = math.hypot(*bc)
    if mag_ba == 0 or mag_bc == 0:
        return 0.0
    cos_val = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_val))


def _angle_from_vertical(
    base: Tuple[float, float], tip: Tuple[float, float]
) -> float:
    """Angle in degrees between the vector base→tip and vertical (0, -1)."""
    dx = tip[0] - base[0]
    dy = tip[1] - base[1]
    dot = -dy
    mag = math.hypot(dx, dy)
    if mag == 0:
        return 0.0
    cos_val = max(-1.0, min(1.0, dot / mag))
    return math.degrees(math.acos(cos_val))


def _midpoint(p1: Tuple[float, float], p2: Tuple[float, float]) -> Tuple[float, float]:
    return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)


# ---------------------------------------------------------------------------
# Per-frame landmark extraction
# ---------------------------------------------------------------------------

def _extract_landmarks(image_bgr) -> Optional[Dict[str, Tuple[float, float]]]:
    """Run pose on *image_bgr* and return a dict of named pixel points, or None."""
    landmarks_list = _run_mediapipe_pose(image_bgr)
    if landmarks_list is None:
        return None

    h, w = image_bgr.shape[:2]
    points: Dict[str, Tuple[float, float]] = {}
    for name, idx in _LANDMARKS_OF_INTEREST.items():
        points[name] = _get_point(landmarks_list, idx, w, h)
    return points


# ---------------------------------------------------------------------------
# Auto-detect handedness
# ---------------------------------------------------------------------------

def detect_handedness(frame_paths: Dict[str, str]) -> str:
    """Detect whether the golfer is right-handed or left-handed.

    In a face-on view, the golfer faces the camera. For a right-handed golfer,
    the lead (left) foot is to the CAMERA's RIGHT (higher x in image coords)
    relative to the trail (right) foot — because the image is mirrored.

    We look at the setup AND top frames:
    - In setup: which ankle is further from centre tells us the stance bias
    - In top: the wrists move toward the trail side, confirming direction

    Returns "right" or "left".
    """
    # Try setup frame first
    setup_path = frame_paths.get("setup")
    top_path = frame_paths.get("top")

    setup_pts = None
    top_pts = None

    if setup_path:
        img = _load_image_bgr(setup_path)
        setup_pts = _extract_landmarks(img)

    if top_path:
        img = _load_image_bgr(top_path)
        top_pts = _extract_landmarks(img)

    votes = []

    # Method 1: At setup, the golfer's hips are usually slightly offset
    # toward the target. The lead hip is slightly closer to target side.
    # More reliable: the lead wrist is generally slightly closer to
    # the target side at address.
    if setup_pts and top_pts:
        # Method 2 (most reliable): Wrist movement direction during backswing.
        # Right-hander: wrists move to camera-left (lower x) during backswing.
        # Left-hander: wrists move to camera-right (higher x) during backswing.
        avg_wrist_setup_x = (
            setup_pts["left_wrist"][0] + setup_pts["right_wrist"][0]
        ) / 2.0
        avg_wrist_top_x = (
            top_pts["left_wrist"][0] + top_pts["right_wrist"][0]
        ) / 2.0
        wrist_dx = avg_wrist_top_x - avg_wrist_setup_x

        # If wrists moved to camera-left (negative dx), it's a right-hander
        if abs(wrist_dx) > 5:  # minimum threshold in pixels
            votes.append("right" if wrist_dx < 0 else "left")

    if setup_pts:
        # Method 3: Shoulder line tilt at setup.
        # Right-handers typically have right shoulder slightly lower (trail side).
        # In face-on mirrored view, MediaPipe "left_shoulder" is actually the
        # golfer's right shoulder. If left_shoulder.y > right_shoulder.y,
        # the golfer's right shoulder is lower → right-handed.
        y_diff = setup_pts["left_shoulder"][1] - setup_pts["right_shoulder"][1]
        if abs(y_diff) > 3:
            votes.append("right" if y_diff > 0 else "left")

    if not votes:
        return "right"  # default fallback

    # Majority vote
    right_votes = sum(1 for v in votes if v == "right")
    return "right" if right_votes >= len(votes) / 2 else "left"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_metrics_for_frames(
    frame_paths: Dict[str, str],
    handedness: str,
) -> Dict[str, float]:
    """Compute normalised swing metrics across setup / top / impact frames."""
    phase_points: Dict[str, Optional[Dict[str, Tuple[float, float]]]] = {}

    for phase in ("setup", "top", "impact"):
        path = frame_paths.get(phase)
        if path is None:
            phase_points[phase] = None
            continue
        img = _load_image_bgr(path)
        phase_points[phase] = _extract_landmarks(img)

    metrics: Dict[str, float] = {}

    # ---- Setup-frame metrics ------------------------------------------------
    sp = phase_points.get("setup")
    if sp is not None:
        shoulder_center = _midpoint(sp["left_shoulder"], sp["right_shoulder"])
        hip_center = _midpoint(sp["left_hip"], sp["right_hip"])
        body_scale = _distance(sp["left_shoulder"], sp["right_shoulder"])

        if body_scale > 0:
            # Spine tilt at setup (angle from vertical)
            spine_tilt = _angle_from_vertical(hip_center, shoulder_center)
            metrics["spine_tilt_deg_setup"] = round(spine_tilt, 1)

            # Average knee flex
            left_knee_angle = _angle(sp["left_hip"], sp["left_knee"], sp["left_ankle"])
            right_knee_angle = _angle(sp["right_hip"], sp["right_knee"], sp["right_ankle"])
            avg_knee_flex = (180.0 - left_knee_angle + 180.0 - right_knee_angle) / 2.0
            metrics["average_knee_flex_deg_setup"] = round(avg_knee_flex, 1)

            # Stance width ratio
            stance_width = _distance(sp["left_ankle"], sp["right_ankle"])
            metrics["stance_width_ratio"] = round(stance_width / body_scale, 2)

    # ---- Head sway (setup → top) -------------------------------------------
    sp_setup = phase_points.get("setup")
    sp_top = phase_points.get("top")
    if sp_setup is not None and sp_top is not None:
        body_scale_setup = _distance(
            sp_setup["left_shoulder"], sp_setup["right_shoulder"]
        )
        if body_scale_setup > 0:
            head_dx = abs(sp_top["nose"][0] - sp_setup["nose"][0])
            metrics["head_sway_body_units_setup_to_top"] = round(
                head_dx / body_scale_setup, 2
            )

    # ---- Head sway (top → impact) ------------------------------------------
    sp_impact = phase_points.get("impact")
    if sp_top is not None and sp_impact is not None:
        body_scale_top = _distance(
            sp_top["left_shoulder"], sp_top["right_shoulder"]
        )
        if body_scale_top > 0:
            head_dx = abs(sp_impact["nose"][0] - sp_top["nose"][0])
            metrics["head_sway_body_units_top_to_impact"] = round(
                head_dx / body_scale_top, 2
            )

    # ---- Hip shift toward target (setup → impact) --------------------------
    if sp_setup is not None and sp_impact is not None:
        body_scale_setup = _distance(
            sp_setup["left_shoulder"], sp_setup["right_shoulder"]
        )
        if body_scale_setup > 0:
            hip_center_setup = _midpoint(
                sp_setup["left_hip"], sp_setup["right_hip"]
            )
            hip_center_impact = _midpoint(
                sp_impact["left_hip"], sp_impact["right_hip"]
            )

            if handedness == "right":
                lead_ankle_x = sp_setup["left_ankle"][0]
            else:
                lead_ankle_x = sp_setup["right_ankle"][0]

            target_dir = lead_ankle_x - hip_center_setup[0]
            raw_shift = hip_center_impact[0] - hip_center_setup[0]

            if target_dir != 0:
                shift = raw_shift * (target_dir / abs(target_dir))
            else:
                shift = abs(raw_shift)

            metrics["hip_shift_toward_target_units"] = round(
                shift / body_scale_setup, 2
            )

    # ---- NEW: Shoulder tilt at impact (lead shoulder height) ---------------
    if sp_impact is not None:
        # At impact, the lead shoulder should be higher than the trail shoulder.
        # This creates the "stacked" position for compression.
        if handedness == "right":
            lead_shoulder = sp_impact["right_shoulder"]  # golfer's left = MP right (mirrored)
            trail_shoulder = sp_impact["left_shoulder"]
        else:
            lead_shoulder = sp_impact["left_shoulder"]
            trail_shoulder = sp_impact["right_shoulder"]

        # Positive = lead shoulder higher (lower y in image coords = higher)
        shoulder_y_diff = trail_shoulder[1] - lead_shoulder[1]
        body_scale_impact = _distance(
            sp_impact["left_shoulder"], sp_impact["right_shoulder"]
        )
        if body_scale_impact > 0:
            # Convert to angle: atan2 of y-diff over x-distance
            shoulder_dx = abs(trail_shoulder[0] - lead_shoulder[0])
            if shoulder_dx > 0:
                tilt_angle = math.degrees(math.atan2(shoulder_y_diff, shoulder_dx))
                metrics["shoulder_tilt_deg_impact"] = round(tilt_angle, 1)

    # ---- NEW: Posture change (spine angle setup vs impact) -----------------
    if sp_setup is not None and sp_impact is not None:
        sc_setup = _midpoint(sp_setup["left_shoulder"], sp_setup["right_shoulder"])
        hc_setup = _midpoint(sp_setup["left_hip"], sp_setup["right_hip"])
        sc_impact = _midpoint(sp_impact["left_shoulder"], sp_impact["right_shoulder"])
        hc_impact = _midpoint(sp_impact["left_hip"], sp_impact["right_hip"])

        tilt_setup = _angle_from_vertical(hc_setup, sc_setup)
        tilt_impact = _angle_from_vertical(hc_impact, sc_impact)

        metrics["posture_change_deg"] = round(abs(tilt_impact - tilt_setup), 1)

    # ---- NEW: Shoulder turn proxy (setup vs top) ---------------------------
    # In face-on view, when shoulders rotate, their projected width shrinks.
    # The ratio of shoulder width at top vs setup estimates rotation.
    if sp_setup is not None and sp_top is not None:
        sw_setup = _distance(sp_setup["left_shoulder"], sp_setup["right_shoulder"])
        sw_top = _distance(sp_top["left_shoulder"], sp_top["right_shoulder"])
        if sw_setup > 0:
            turn_ratio = sw_top / sw_setup
            # Convert to approximate rotation angle:
            # projected_width = actual_width * cos(angle)
            # So angle ≈ acos(ratio)
            clamped = max(-1.0, min(1.0, turn_ratio))
            turn_deg = math.degrees(math.acos(clamped))
            metrics["shoulder_turn_deg"] = round(turn_deg, 0)

    return metrics
