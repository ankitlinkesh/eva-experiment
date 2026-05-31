from __future__ import annotations

import re

from .persona import USER_NAME


def _normalize(message: str) -> str:
    text = message.strip().lower()
    text = re.sub(r"[^\w\s']", " ", text)
    return " ".join(text.split())


def maybe_handle_fast_response(message: str) -> tuple[str, str] | None:
    text = _normalize(message)
    if not text:
        return None

    greeting_words = {"hi", "hii", "hiii", "hey", "heyy", "hello", "yo", "howdy", "wassup", "sup"}
    thanks = {"thanks", "thank you", "ty", "appreciate it"}
    acknowledgements = {"okay", "ok", "alr", "alright", "nice", "cool", "lol", "lmao"}

    if text in {"eva", "yo eva", "hey eva", "hi eva", "hello eva"}:
        return f"Yeah {USER_NAME}?", "fast-casual"

    if text in {"lmao im joking", "lmao i'm joking", "lol im joking", "lol i'm joking", "im joking", "i'm joking", "just kidding"}:
        return f"Got it. Joke context cleared; I’m keeping your name as {USER_NAME}.", "fast-casual"

    if text in {"hi eva epdi iruka", "eva epdi iruka", "epdi iruka eva", "hey eva epdi iruka"}:
        return f"Nalla iruken, {USER_NAME}. Nee epdi iruka?", "fast-casual"

    if text == "respond in tamil love":
        return "Seri, Tamil-la respond panren. “Love” ah address-a eduthukkaren.", "fast-casual"

    if text in {"how are you", "how you doing", "how are u", "you good", "u good"}:
        return "Running smooth. What are we working on?", "fast-casual"

    if text in {"you there", "are you there", "still there"}:
        return "Yeah, I'm here. What's the move?", "fast-casual"

    if text in thanks:
        return "Got you.", "fast-casual"

    if text in acknowledgements:
        return "Say less.", "fast-casual"

    words = set(text.split())
    if text in {"hey there", "hello there"}:
        return f"Yo {USER_NAME}, I'm here. What's the move?", "fast-casual"

    if words and words.issubset(greeting_words | {"eva"}):
        return f"Yo {USER_NAME}, I'm here. What's the move?", "fast-casual"

    if text in {"what's up", "whats up", "what up", "what's good", "whats good"}:
        return "I'm here. What are we building?", "fast-casual"

    return None
