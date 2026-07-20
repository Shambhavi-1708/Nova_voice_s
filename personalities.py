"""
personalities.py

Single source of truth for NovaVoice's AI Personality System.

Each personality defines:
- the behavior instructions layered on top of the assistant's core system
  prompt (calendar + Spotify capabilities stay identical across all of them)
- the voice trigger phrases that switch to it when heard in the user's speech
- the short confirmation line the assistant speaks back once switched

The Flask backend serves this list to the frontend via GET /api/personalities
so nothing is hardcoded or duplicated inside index.html.
"""

from typing import TypedDict


class Personality(TypedDict):
    key: str            # stable identifier used everywhere (URLs, storage, matching)
    display_name: str   # shown in the UI dropdown
    prompt: str          # behavior instructions prepended to the session's system prompt
    confirmation: str    # line the assistant should speak once this mode is activated
    triggers: list[str]  # lowercase phrases that switch to this personality when spoken


PERSONALITIES: dict[str, Personality] = {
    "friendly": {
        "key": "friendly",
        "display_name": "Friendly Assistant",
        "prompt": (
            "Personality: Friendly Assistant. Be warm and conversational, like a helpful "
            "friend. Use simple, everyday language. You can occasionally sound playful or "
            "enthusiastic, but don't overdo it. Keep things upbeat and approachable."
        ),
        "confirmation": "Friendly mode activated! I'm here to help, just ask away.",
        "triggers": [
            "switch to friendly mode",
            "switch to friendly",
            "use friendly mode",
            "be friendly",
            "friendly mode",
        ],
    },
    "professional": {
        "key": "professional",
        "display_name": "Professional Assistant",
        "prompt": (
            "Personality: Professional Assistant. Be formal, concise, and business-like. "
            "Avoid unnecessary humor or filler words. Get straight to the point while "
            "remaining polite and precise."
        ),
        "confirmation": "Professional mode activated. How may I assist you?",
        "triggers": [
            "switch to professional mode",
            "switch to professional",
            "use professional mode",
            "be professional",
            "professional mode",
        ],
    },
    "teacher": {
        "key": "teacher",
        "display_name": "Teacher",
        "prompt": (
            "Personality: Teacher. Explain concepts step by step. Use concrete examples and "
            "analogies. After explaining a step, briefly check whether the user understands "
            "before moving on. Encourage learning and reasoning rather than just handing "
            "over direct answers."
        ),
        "confirmation": "Teacher mode activated. I'll explain everything step by step.",
        "triggers": [
            "switch to teacher mode",
            "switch to teacher",
            "use teacher mode",
            "be a teacher",
            "teacher mode",
        ],
    },
    "coding_mentor": {
        "key": "coding_mentor",
        "display_name": "Coding Mentor",
        "prompt": (
            "Personality: Coding Mentor. Help debug code and explain WHY errors happen, not "
            "just how to fix them. Encourage best practices. Avoid simply handing over a "
            "finished solution without explanation — guide the user toward understanding it "
            "themselves."
        ),
        "confirmation": "Coding mentor mode activated. Let's dig into the code together.",
        "triggers": [
            "switch to coding mentor",
            "switch to coding mentor mode",
            "use coding mentor mode",
            "be a coding mentor",
            "coding mentor mode",
        ],
    },
}

DEFAULT_PERSONALITY = "friendly"


def get_personality(key: str) -> Personality:
    """Returns the personality for a given key, falling back to the default if unknown."""
    return PERSONALITIES.get(key, PERSONALITIES[DEFAULT_PERSONALITY])


def list_personalities() -> list[Personality]:
    """Returns all personalities as an ordered list, for consistent UI rendering."""
    order = ["friendly", "professional", "teacher", "coding_mentor"]
    return [PERSONALITIES[k] for k in order]
