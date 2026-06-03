from typing import List, Optional, Tuple

KEYWORDS = [
    "stress", "stressed", "stressful",
    "sleep", "sleeping", "insomnia",
    "school", "class", "homework", "exam",
    "work", "job", "boss", "deadline",
    "exercise", "gym", "workout", "run", "running",
    "family", "parent", "parents", "mom", "dad", "sibling",
    "friends", "friend", "social",
    "anxiety", "anxious", "panic", "worried", "worry",
    "sad", "sadness", "depressed", "down",
    "happy", "happiness", "joy", "great", "wonderful",
    "tired", "exhausted", "fatigue", "drained",
]

POSITIVE_WORDS = {
    "happy", "happiness", "joy", "joyful", "great", "wonderful", "good",
    "amazing", "fantastic", "excellent", "positive", "energized", "excited",
    "grateful", "thankful", "blessed", "motivated", "inspired", "calm",
    "peaceful", "content", "satisfied", "refreshed", "optimistic", "hopeful",
    "better", "improved", "productive", "accomplished", "proud", "loved",
}

NEGATIVE_WORDS = {
    "sad", "sadness", "depressed", "depression", "unhappy", "miserable",
    "terrible", "awful", "horrible", "bad", "worse", "worst", "negative",
    "anxious", "anxiety", "panic", "stressed", "stress", "stressful",
    "tired", "exhausted", "drained", "overwhelmed", "hopeless", "lonely",
    "angry", "frustrated", "upset", "disappointed", "worried", "scared",
    "fearful", "nervous", "irritated", "annoyed", "bored", "empty",
}


def extract_keywords(text: str) -> List[str]:
    text_lower = text.lower()
    words = set(text_lower.replace(",", " ").replace(".", " ").replace("!", " ").split())
    found = []
    seen_roots = set()
    for kw in KEYWORDS:
        root = kw.rstrip("edingsly")[:5]
        if root not in seen_roots:
            for word in words:
                if word.startswith(root) or word == kw:
                    found.append(kw.split()[0])
                    seen_roots.add(root)
                    break
    return list(dict.fromkeys(found))


def compute_sentiment(text: str) -> Tuple[float, str]:
    words = set(text.lower().split())
    positive_count = len(words & POSITIVE_WORDS)
    negative_count = len(words & NEGATIVE_WORDS)
    total = positive_count + negative_count
    if total == 0:
        return 0.0, "neutral"
    score = (positive_count - negative_count) / total
    if score > 0.2:
        label = "positive"
    elif score < -0.2:
        label = "negative"
    else:
        label = "neutral"
    return round(score, 3), label


def analyze_text(content: str) -> dict:
    keywords = extract_keywords(content)
    sentiment_score, sentiment_label = compute_sentiment(content)
    return {
        "keywords": keywords,
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
    }
