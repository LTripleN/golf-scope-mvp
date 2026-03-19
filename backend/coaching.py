"""
coaching.py
Generate a personalized AI coaching summary using Claude.

Falls back to a simple rule-based summary if the LLM call fails.
"""

import os
import json
from typing import Dict, List

# Try Anthropic SDK — available when server started with llm-api credentials
try:
    from anthropic import Anthropic
    _client = Anthropic()
    _HAS_ANTHROPIC = True
except Exception:
    _client = None
    _HAS_ANTHROPIC = False


SYSTEM_PROMPT = """You are SwingAI Coach — a concise, friendly golf instructor.
You're reviewing face-on swing video analysis data.

Write exactly 2-3 SHORT sentences:
1. One positive observation (lead with encouragement)
2. The single most impactful thing to work on
3. One specific drill or feel to try

Rules:
- Maximum 50 words total. Be punchy and direct.
- Use everyday language — zero jargon.
- No metric numbers. Describe qualitatively.
- No bullet points, no markdown, no headers. Plain text only.
- Write like a text from a supportive coach, not an essay."""


def generate_coaching_summary(
    metrics: Dict[str, float],
    findings: List[str],
    tips: List[str],
    handedness: str,
) -> str:
    """Generate a personalized coaching paragraph from analysis data.

    Uses Claude if available, otherwise falls back to a simple template.
    """
    if _HAS_ANTHROPIC and _client is not None:
        try:
            return _call_llm(metrics, findings, tips, handedness)
        except Exception as e:
            print(f"LLM coaching call failed: {e}")
            return _fallback_summary(findings, tips)
    else:
        return _fallback_summary(findings, tips)


def _call_llm(
    metrics: Dict[str, float],
    findings: List[str],
    tips: List[str],
    handedness: str,
) -> str:
    """Call Claude to generate the coaching summary."""
    user_msg = f"""Swing data for a {handedness}-handed golfer (face-on):

Metrics: {json.dumps(metrics)}

Findings:
{chr(10).join(f"- {f}" for f in findings) if findings else "- No issues flagged."}

Tips:
{chr(10).join(f"- {t}" for t in tips) if tips else "- None triggered."}

Write your coaching summary (max 50 words, 2-3 sentences)."""

    message = _client.messages.create(
        model="claude_haiku_4_5",
        max_tokens=150,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return message.content[0].text.strip()


def _fallback_summary(findings: List[str], tips: List[str]) -> str:
    """Simple template-based fallback when LLM is unavailable."""
    if not findings and not tips:
        return (
            "Your setup looks solid from this angle. Keep filming yourself "
            "regularly to track progress."
        )

    parts = []
    positive = [f for f in findings if "neutral" in f.lower() or "good" in f.lower() or "solid" in f.lower() or "great" in f.lower()]
    issues = [f for f in findings if f not in positive]

    if positive:
        parts.append("Some good things in your swing.")

    if issues:
        parts.append(f"Focus area: {issues[0].lower()}")

    if tips:
        parts.append(tips[0])

    return " ".join(parts)
