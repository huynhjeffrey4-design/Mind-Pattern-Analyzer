from typing import List, Tuple

SAFETY_KEYWORDS = [
    "suicide", "suicidal", "kill myself", "end my life", "want to die",
    "self-harm", "self harm", "cutting", "hurt myself", "not worth living",
    "no reason to live", "better off dead", "overdose",
]


def detect_safety_keywords(text: str) -> Tuple[bool, List[str]]:
    text_lower = text.lower()
    matched = [kw for kw in SAFETY_KEYWORDS if kw in text_lower]
    return len(matched) > 0, matched


SAFETY_RESOURCE_MESSAGE = (
    "If you're going through a difficult time, please reach out for support. "
    "You can contact the 988 Suicide & Crisis Lifeline by calling or texting 988, "
    "or visit the Crisis Text Line by texting HOME to 741741."
)
