"""
main.py
FastAPI application for golf swing analysis.

Run locally:
    uvicorn main:app --reload
"""

import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from video_processing import extract_swing_key_frames
from pose_metrics import compute_metrics_for_frames, detect_handedness
from tips_engine import generate_findings_and_tips
from coaching import generate_coaching_summary

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Golf Swing Analyzer",
    version="2.0.0",
    description="Upload a face-on golf swing video and receive pose-based feedback.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Insight builder — structured insight cards for the frontend
# ---------------------------------------------------------------------------

def _build_insights(metrics: Dict[str, float], handedness: str) -> List[Dict[str, Any]]:
    """Build structured insight objects from metrics.

    Each insight has: key, label, value, unit, status (good/watch/fix),
    description, and category.
    """
    insights: List[Dict[str, Any]] = []

    # --- Setup metrics ---
    tilt = metrics.get("spine_tilt_deg_setup")
    if tilt is not None:
        if tilt <= 6:
            status, desc = "good", "Nice and centered"
        elif tilt <= 8:
            status, desc = "watch", "Slightly tilted"
        else:
            status, desc = "fix", "Leaning too much"
        insights.append({
            "key": "spine_tilt_deg_setup",
            "label": "Spine Tilt",
            "value": round(tilt, 1),
            "unit": "°",
            "status": status,
            "description": desc,
            "category": "setup",
        })

    knee = metrics.get("average_knee_flex_deg_setup")
    if knee is not None:
        if knee <= 8:
            status, desc = "good", "Athletic and balanced"
        elif knee <= 12:
            status, desc = "watch", "A bit more flex than usual"
        else:
            status, desc = "fix", "Too much knee bend"
        insights.append({
            "key": "average_knee_flex_deg_setup",
            "label": "Knee Flex",
            "value": round(knee, 1),
            "unit": "°",
            "status": status,
            "description": desc,
            "category": "setup",
        })

    stance = metrics.get("stance_width_ratio")
    if stance is not None:
        if stance < 0.7:
            status, desc = "watch", "Quite narrow"
        elif stance > 1.2:
            status, desc = "watch", "Quite wide"
        else:
            status, desc = "good", "Good width"
        insights.append({
            "key": "stance_width_ratio",
            "label": "Stance Width",
            "value": round(stance, 2),
            "unit": "x",
            "status": status,
            "description": desc,
            "category": "setup",
        })

    # --- Backswing metrics ---
    sway_back = metrics.get("head_sway_body_units_setup_to_top")
    if sway_back is not None:
        if sway_back <= 0.3:
            status, desc = "good", "Steady head"
        elif sway_back <= 0.5:
            status, desc = "watch", "Some lateral movement"
        else:
            status, desc = "fix", "Noticeable sway"
        insights.append({
            "key": "head_sway_body_units_setup_to_top",
            "label": "Backswing Sway",
            "value": round(sway_back, 2),
            "unit": "",
            "status": status,
            "description": desc,
            "category": "backswing",
        })

    shoulder_turn = metrics.get("shoulder_turn_deg")
    if shoulder_turn is not None:
        if shoulder_turn < 50:
            status, desc = "fix", "Limited rotation"
        elif shoulder_turn > 100:
            status, desc = "watch", "Very large turn"
        else:
            status, desc = "good", "Solid upper body coil"
        insights.append({
            "key": "shoulder_turn_deg",
            "label": "Shoulder Turn",
            "value": round(shoulder_turn, 0),
            "unit": "°",
            "status": status,
            "description": desc,
            "category": "backswing",
        })

    # --- Impact metrics ---
    sway_down = metrics.get("head_sway_body_units_top_to_impact")
    if sway_down is not None:
        if sway_down <= 1.2:
            status, desc = "good", "Controlled movement"
        elif sway_down <= 2.0:
            status, desc = "watch", "Moderate movement"
        else:
            status, desc = "fix", "Head moving a lot"
        insights.append({
            "key": "head_sway_body_units_top_to_impact",
            "label": "Downswing Sway",
            "value": round(sway_down, 2),
            "unit": "",
            "status": status,
            "description": desc,
            "category": "impact",
        })

    hip_shift = metrics.get("hip_shift_toward_target_units")
    if hip_shift is not None:
        abs_v = abs(hip_shift)
        if abs_v < 0.08:
            status, desc = "watch", "Very little shift"
        elif abs_v > 0.45:
            status, desc = "fix", "Too much slide"
        else:
            status, desc = "good", "Good weight transfer"
        insights.append({
            "key": "hip_shift_toward_target_units",
            "label": "Hip Shift",
            "value": round(abs_v, 2),
            "unit": "",
            "status": status,
            "description": desc,
            "category": "impact",
        })

    shoulder_tilt = metrics.get("shoulder_tilt_deg_impact")
    if shoulder_tilt is not None:
        abs_tilt = abs(shoulder_tilt)
        if abs_tilt < 10:
            status, desc = "watch", "Shoulders too level"
        elif abs_tilt > 40:
            status, desc = "watch", "Very steep tilt"
        else:
            status, desc = "good", "Nicely stacked"
        insights.append({
            "key": "shoulder_tilt_deg_impact",
            "label": "Shoulder Tilt",
            "value": round(abs_tilt, 1),
            "unit": "°",
            "status": status,
            "description": desc,
            "category": "impact",
        })

    posture_change = metrics.get("posture_change_deg")
    if posture_change is not None:
        if posture_change <= 5:
            status, desc = "good", "Great posture retention"
        elif posture_change <= 8:
            status, desc = "watch", "Some posture loss"
        else:
            status, desc = "fix", "Standing up through impact"
        insights.append({
            "key": "posture_change_deg",
            "label": "Posture Change",
            "value": round(posture_change, 1),
            "unit": "°",
            "status": status,
            "description": desc,
            "category": "impact",
        })

    return insights


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"status": "ok", "service": "golf-swing-analyzer", "version": "2.0.0"}


# ---------------------------------------------------------------------------
# POST /analyze
# ---------------------------------------------------------------------------
@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    handedness: Optional[str] = Form(None),
) -> Dict[str, Any]:
    """Analyse a face-on golf swing video and return metrics, findings, tips, and insights.

    Handedness is now optional — if not provided, it will be auto-detected.
    """

    # --- Read upload and enforce size limit ---------------------------------
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File too large ({len(contents) / (1024 * 1024):.1f} MB). "
                f"Maximum allowed size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
            ),
        )

    # --- Determine file extension -------------------------------------------
    original_name = file.filename or "upload.mp4"
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in (".mp4", ".mov"):
        ext = ".mp4"

    # --- Save to temp dir and process ---------------------------------------
    with tempfile.TemporaryDirectory() as tmp_dir:
        video_path = os.path.join(tmp_dir, f"upload{ext}")
        with open(video_path, "wb") as f:
            f.write(contents)

        # 1. Extract key frames
        try:
            frame_paths = extract_swing_key_frames(video_path, tmp_dir)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Video processing failed: {exc}",
            )

        # 2. Auto-detect or validate handedness
        handedness_source = "user"
        if handedness and handedness.strip().lower() in ("right", "left"):
            handedness = handedness.strip().lower()
        else:
            handedness = detect_handedness(frame_paths)
            handedness_source = "auto"

        # 3. Compute pose metrics
        try:
            metrics = compute_metrics_for_frames(frame_paths, handedness)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Pose analysis failed: {exc}",
            )

        if not metrics:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not detect pose from the video; "
                    "please upload a clearer face-on swing."
                ),
            )

        # 4. Generate findings & tips
        findings, tips = generate_findings_and_tips(metrics, handedness)

        # 5. Build structured insights
        insights = _build_insights(metrics, handedness)

        # 6. Generate AI coaching summary
        coaching_summary = generate_coaching_summary(
            metrics, findings, tips, handedness
        )

    return {
        "scope": metrics,
        "findings": findings,
        "tips": tips,
        "coaching_summary": coaching_summary,
        "handedness": handedness,
        "handedness_source": handedness_source,
        "insights": insights,
    }
