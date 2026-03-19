"""
tips_engine.py
Simple threshold-based rules engine that converts raw swing metrics into
human-readable findings (what we observed) and tips (what to try next).
"""

from typing import Dict, List, Tuple


def generate_findings_and_tips(
    metrics: Dict[str, float],
    handedness: str,
) -> Tuple[List[str], List[str]]:
    """Map *metrics* to findings and tips via threshold rules.

    Returns (findings, tips) where tips is capped at 3 items and de-duped.
    """
    findings: List[str] = []
    tips: List[str] = []

    # ------------------------------------------------------------------
    # Rule 1 – Lateral spine tilt at setup (face-on view)
    # ------------------------------------------------------------------
    tilt = metrics.get("spine_tilt_deg_setup")
    if tilt is not None:
        if tilt > 8:
            findings.append(
                f"Noticeable lateral spine tilt ({tilt}°) at setup."
            )
            tips.append(
                "Try to keep your spine more centered at address — "
                "avoid leaning too far toward or away from the target."
            )
        else:
            findings.append(
                f"Lateral spine tilt at setup is about {tilt}°, "
                "which looks fairly neutral."
            )

    # ------------------------------------------------------------------
    # Rule 2 – Visible knee flex at setup (face-on view)
    # ------------------------------------------------------------------
    knee = metrics.get("average_knee_flex_deg_setup")
    if knee is not None:
        if knee > 12:
            findings.append(
                "Knees look noticeably flexed at setup from the face-on "
                "view."
            )
            tips.append(
                "Straighten your knees slightly so your weight stays over "
                "the middle of your feet."
            )

    # ------------------------------------------------------------------
    # Rule 3 – Head sway (backswing)
    # ------------------------------------------------------------------
    sway_back = metrics.get("head_sway_body_units_setup_to_top")
    if sway_back is not None:
        if sway_back > 0.5:
            findings.append(
                "Head sways noticeably away from the target in the "
                "backswing."
            )
            tips.append(
                "Try to keep your head more centered; feel rotation rather "
                "than sliding in the backswing."
            )
        elif sway_back > 0.3:
            findings.append(
                "There is a moderate amount of lateral head movement during "
                "the backswing."
            )

    # ------------------------------------------------------------------
    # Rule 4 – Head sway (downswing → follow-through)
    # ------------------------------------------------------------------
    sway_down = metrics.get("head_sway_body_units_top_to_impact")
    if sway_down is not None:
        if sway_down > 2.0:
            findings.append(
                "Significant head movement toward the target through "
                "the downswing and follow-through."
            )
            tips.append(
                "Focus on keeping your head quieter through the "
                "hitting zone — let the body rotate around a stable center."
            )
        elif sway_down > 1.2:
            findings.append(
                "Moderate head movement toward the target into the "
                "follow-through."
            )

    # ------------------------------------------------------------------
    # Rule 5 – Lateral hip shift (setup → impact)
    # ------------------------------------------------------------------
    hip_shift = metrics.get("hip_shift_toward_target_units")
    if hip_shift is not None:
        abs_shift = abs(hip_shift)
        if abs_shift < 0.08:
            findings.append(
                "Very little lateral hip movement between setup and "
                "impact."
            )
            tips.append(
                "A small lateral bump toward the target before the "
                "downswing can improve sequencing and ball-turf contact."
            )
        elif abs_shift > 0.45:
            findings.append(
                "Notable lateral hip slide between setup and impact."
            )
            tips.append(
                "Try to rotate your hips more and slide them less to "
                "maintain your swing center."
            )
        else:
            findings.append(
                f"Lateral hip movement is moderate ({abs_shift:.2f} "
                "shoulder-widths)."
            )

    # ------------------------------------------------------------------
    # Rule 6 – Stance width
    # ------------------------------------------------------------------
    stance = metrics.get("stance_width_ratio")
    if stance is not None:
        if stance < 0.7:
            findings.append("Your stance looks relatively narrow.")
            tips.append(
                "Try a slightly wider stance for more stability."
            )
        elif stance > 1.2:
            findings.append("Your stance looks quite wide.")
            tips.append(
                "Experiment with bringing your feet a bit closer together."
            )

    # ------------------------------------------------------------------
    # Rule 7 – Shoulder tilt at impact
    # Positive = lead shoulder higher than trail shoulder (good).
    # Tour average: 20-35° of tilt at impact.
    # ------------------------------------------------------------------
    shoulder_tilt = metrics.get("shoulder_tilt_deg_impact")
    if shoulder_tilt is not None:
        if shoulder_tilt < 10:
            findings.append(
                "Shoulders are fairly level at impact — not much tilt."
            )
            tips.append(
                "Feel your lead shoulder staying high through impact; "
                "this helps compress the ball and improve your strike."
            )
        elif shoulder_tilt > 40:
            findings.append(
                "Very steep shoulder tilt at impact."
            )
            tips.append(
                "Try to moderate how much you dip your trail shoulder — "
                "a little less tilt can help with consistency."
            )
        else:
            findings.append(
                "Good shoulder tilt at impact — lead shoulder is "
                "nicely stacked above the trail side."
            )

    # ------------------------------------------------------------------
    # Rule 8 – Posture change (spine angle setup vs impact)
    # Best players maintain their spine angle within 3-5° through impact.
    # ------------------------------------------------------------------
    posture_change = metrics.get("posture_change_deg")
    if posture_change is not None:
        if posture_change > 8:
            findings.append(
                "Noticeable change in posture between setup and impact — "
                "you may be standing up through the ball."
            )
            tips.append(
                "Try to maintain your spine angle through impact. A good "
                "drill: practice half-swings keeping your belt buckle "
                "pointing at the ball."
            )
        elif posture_change <= 5:
            findings.append(
                "Great posture retention — your spine angle stays "
                "consistent from setup to impact."
            )

    # ------------------------------------------------------------------
    # Rule 9 – Shoulder turn (setup vs top of backswing)
    # Tour average: 85-100° of shoulder turn. Below 60° is restricted.
    # ------------------------------------------------------------------
    shoulder_turn = metrics.get("shoulder_turn_deg")
    if shoulder_turn is not None:
        if shoulder_turn < 50:
            findings.append(
                "Limited shoulder turn in the backswing — your upper "
                "body isn't fully coiling."
            )
            tips.append(
                "Focus on turning your back fully toward the target. "
                "Feel your lead shoulder under your chin at the top."
            )
        elif shoulder_turn > 100:
            findings.append(
                "Very large shoulder turn — great rotation if you can "
                "control it."
            )
        else:
            findings.append(
                f"Solid shoulder turn ({shoulder_turn:.0f}°) — good "
                "upper body coil."
            )

    # ------------------------------------------------------------------
    # Deduplicate tips and cap at 3
    # ------------------------------------------------------------------
    seen: set = set()
    unique_tips: List[str] = []
    for tip in tips:
        if tip not in seen:
            seen.add(tip)
            unique_tips.append(tip)
    tips = unique_tips[:3]

    return findings, tips
