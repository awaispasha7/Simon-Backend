"""
Coach Tools API: endpoints for content strategist/scriptwriter workflows
MVP: No DB required. Optionally calls n8n webhook if configured.
"""

from fastapi import APIRouter, Body
from typing import Dict, List, Optional
import os
import aiohttp

router = APIRouter(prefix="/coach")


def _default_hooks(topic: str) -> List[str]:
    return [
        f"If you're struggling with {topic}, listen to this.",
        f"No one's telling you this about {topic}…",
        f"The real reason you can't stay consistent with {topic}.",
    ]


def _default_ctas() -> List[str]:
    return [
        "Follow for daily mindset shifts.",
        "Comment 'READY' and I’ll send you the framework.",
        "Save this for when motivation dips.",
    ]


def _hashtags(topic: str) -> List[str]:
    base = ["#mindset", "#selfgrowth", "#consistency", "#healing", "#selftrust"]
    topic_tag = f"#{topic.replace(' ', '')[:20].lower()}" if topic else "#coaching"
    return base + [topic_tag]


@router.post("/scriptwriter")
async def scriptwriter(
    topic: str = Body("consistency", embed=True),
    audience: Optional[str] = Body(None, embed=True),
    brand_voice: Optional[str] = Body(None, embed=True),
):
    hook_options = _default_hooks(topic)
    cta_options = _default_ctas()
    hook = hook_options[0]

    script = {
        "hook": hook,
        "story": (
            f"I used to think {topic} was about motivation. It wasn't. It was about identity."
            " The moment I stopped waiting to 'feel ready' and started acting like the person"
            " I said I wanted to be, everything shifted."
        ),
        "lesson": (
            "Don't chase intensity; build minimum commitments you never break."
            " Keep them so small you can't fail. That's how self-trust is rebuilt."
        ),
        "cta": cta_options[0],
        "cta_options": cta_options,
        "hook_options": hook_options,
        "caption": (
            f"{audience or 'For those who feel stuck'}: You don't need more motivation."
            f" You need tiny promises you keep. This is how {topic} becomes automatic."
        ),
        "hashtags": _hashtags(topic),
        "thumbnail_text": [
            "Self-Trust First",
            "Stop Waiting. Start.",
            "Tiny. Daily. Done.",
        ],
        "broll": [
            "Close-up: hands setting phone timer",
            "POV: lacing shoes, morning light",
            "Writing a single sentence in a notebook",
        ],
        "music": ["Emotional ambient", "Warm piano", "Hopeful lo-fi"],
    }
    return {"success": True, "script": script}


@router.post("/competitorrewrite")
async def competitor_rewrite(
    transcript: str = Body(..., embed=True),
    brand_voice: Optional[str] = Body(None, embed=True),
):
    rewritten = (
        "Let's make this real. "
        + transcript.strip()[:500]
        + " — but grounded, human, and specific."
    )
    return {"success": True, "rewritten": rewritten}


@router.post("/avatar_refine")
async def avatar_refine(
    current_avatar: Optional[str] = Body(None, embed=True),
):
    refined = {
        "identity": "High-achieving, self-aware, quietly overwhelmed",
        "core_desires": ["consistency", "self-trust", "emotional clarity"],
        "core_fears": ["falling off again", "being average", "wasting time"],
        "language": ["I start and stop", "I know what to do but don't do it"],
        "moments": ["late-night scrolling", "Sunday reset", "post-failure spiral"],
    }
    return {"success": True, "avatar": refined}


@router.post("/northstar_editor")
async def northstar_editor(
    doc: str = Body(..., embed=True),
):
    improved = (
        "North Star (clear + emotional):\n"
        "I create content that helps people rebuild self-trust through tiny, repeatable wins,"
        " told through honest, relatable stories that make them feel seen."
    )
    return {"success": True, "northstar": improved}


@router.post("/contentplanner")
async def contentplanner(
    pillars: Optional[List[str]] = Body(None, embed=True),
    topic: Optional[str] = Body(None, embed=True),
):
    ideas = [
        {
            "angle": "emotional story",
            "format": "talking_head_punchcut",
            "hook": _default_hooks(topic or "consistency")[1],
            "message": "Tiny promises rebuild identity; intensity breaks it.",
            "cta": _default_ctas()[2],
        },
        {
            "angle": "myth-busting",
            "format": "caption_overlay",
            "hook": "Motivation isn't your problem. Identity is.",
            "message": "Design 2-minute reps. Track streaks, not results.",
            "cta": _default_ctas()[0],
        },
        {
            "angle": "educational",
            "format": "list + voiceover",
            "hook": "3 rules for never falling off again",
            "message": "Pre-decide time, minimum, recovery plan.",
            "cta": _default_ctas()[1],
        },
        {
            "angle": "motivational",
            "format": "broll + narration",
            "hook": "You don't need to be ready. You need to begin.",
            "message": "Self-respect grows when action precedes feeling.",
            "cta": _default_ctas()[0],
        },
        {
            "angle": "emotional story",
            "format": "first-person confession",
            "hook": "I kept quitting because I chased perfect days.",
            "message": "Imperfect daily beats perfect rarely.",
            "cta": _default_ctas()[2],
        },
    ]

    # Optional: forward to n8n for structuring/enrichment if configured
    n8n_url = os.getenv("N8N_CONTENT_PLANNER_WEBHOOK")
    if n8n_url:
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(n8n_url, json={"ideas": ideas, "pillars": pillars, "topic": topic})
        except Exception:
            pass

    return {"success": True, "ideas": ideas}


