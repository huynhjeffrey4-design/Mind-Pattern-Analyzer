"""
Tests: NLP analysis (sentiment scoring + keyword extraction + crisis detection)

This is the analysis layer that runs automatically on every journal entry.
Although the implementation is rule-based rather than a language model, it
is the component responsible for surfacing insights from user text — and
therefore the one most in need of precise, category-driven tests.

All tests in this file are pure unit tests (no HTTP, no DB) because the
functions are deterministic and side-effect-free.

Categories covered:
  - Happy path
  - Bad input / edge cases
  - AI safety wording (crisis detection correctness)
"""
import pytest
from app.services.nlp import analyze_text, compute_sentiment, extract_keywords
from app.services.safety import detect_safety_keywords, SAFETY_RESOURCE_MESSAGE


# ---------------------------------------------------------------------------
# Happy path — sentiment scoring
# ---------------------------------------------------------------------------

def test_positive_sentiment_for_unambiguously_happy_text():
    """
    Name: Clearly positive text scores as positive
    Setup: sentence containing multiple words from the POSITIVE_WORDS set
    Action: compute_sentiment(text)
    Expected: label == "positive", score > 0
    Why: Positive sentiment is the primary signal used in mood trend charts.
         If it's mislabelled, happy days appear flat or negative in the UI.
    """
    score, label = compute_sentiment("I feel happy wonderful joy grateful amazing today.")
    assert label == "positive"
    assert score > 0


def test_negative_sentiment_for_unambiguously_distressing_text():
    """
    Name: Clearly negative text scores as negative
    Setup: sentence containing multiple words from the NEGATIVE_WORDS set
    Action: compute_sentiment(text)
    Expected: label == "negative", score < 0
    Why: Negative trend detection requires accurate negative labelling.
         A false positive here would hide worsening patterns from the user.
    """
    score, label = compute_sentiment("I am sad exhausted anxious overwhelmed lonely frustrated.")
    assert label == "negative"
    assert score < 0


def test_neutral_sentiment_for_text_with_no_emotion_words():
    """
    Name: Factual text with no emotion vocabulary scores neutral
    Setup: sentence about logistics with no pos/neg words
    Action: compute_sentiment(text)
    Expected: label == "neutral", score == 0.0
    Why: The scorer must not hallucinate sentiment. Returning positive or
         negative for neutral text would corrupt the trend chart baseline.
    """
    score, label = compute_sentiment("The meeting starts at 3pm. We will review the budget.")
    assert label == "neutral"
    assert score == 0.0


def test_balanced_text_scores_near_neutral():
    """
    Name: Text with equal positive and negative words lands at neutral
    Setup: one positive word ("happy") and one negative word ("sad")
    Action: compute_sentiment(text)
    Expected: label == "neutral" (score == 0.0 exactly: (1-1)/2 = 0)
    Why: Mixed emotional entries are common; forcing them into positive or
         negative would add false signal to trend analysis.
    """
    score, label = compute_sentiment("I feel happy but also sad today.")
    assert label == "neutral"
    assert score == 0.0


# ---------------------------------------------------------------------------
# Happy path — keyword extraction
# ---------------------------------------------------------------------------

def test_keyword_extraction_finds_stress_topic():
    """
    Name: "stressed" text yields a stress-related keyword
    Setup: sentence mentioning being stressed
    Action: extract_keywords(text)
    Expected: at least one of {"stress", "stressed"} in result
    Why: Keywords from journals are the raw material for the "Recurring
         Themes" insight. Missing them means the insight never fires.
    """
    keywords = extract_keywords("I was stressed all day because of the deadline.")
    stress_related = {"stress", "stressed"}
    assert stress_related & set(keywords), f"Expected a stress keyword, got: {keywords}"


def test_keyword_extraction_finds_sleep_topic():
    """
    Name: Sleep mention yields a sleep-related keyword
    Setup: sentence about insomnia/poor sleep
    Action: extract_keywords(text)
    Expected: at least one of {"sleep", "insomnia"} in result
    Why: Sleep patterns are a key correlate; failing to tag sleep entries
         means the sleep→mood insight never gets journal context.
    """
    keywords = extract_keywords("I barely slept last night — insomnia again.")
    sleep_related = {"sleep", "insomnia", "sleeping"}
    assert sleep_related & set(keywords), f"Expected a sleep keyword, got: {keywords}"


def test_keyword_extraction_returns_empty_for_unrelated_text():
    """
    Name: Technical jargon outside the keyword vocabulary yields nothing
    Setup: sentence about software deployment
    Action: extract_keywords(text)
    Expected: empty list
    Why: Returning false-positive keywords for unrelated text would pollute
         the "Recurring Themes" insight with meaningless topics.
    """
    keywords = extract_keywords("The Kubernetes pod crashed during the rollout.")
    assert keywords == []


def test_analyze_text_combines_sentiment_and_keywords():
    """
    Name: analyze_text returns a complete NLP result dict
    Setup: emotionally rich sentence mentioning anxiety
    Action: analyze_text(text)
    Expected: result has keywords, sentiment_score, sentiment_label keys
              with non-None values
    Why: The route calls analyze_text, not the sub-functions directly.
         If the combined wrapper misses a field, the DB insert will fail.
    """
    result = analyze_text("I feel anxious about tomorrow's exam.")
    assert "keywords" in result
    assert "sentiment_score" in result
    assert "sentiment_label" in result
    assert result["sentiment_label"] in {"positive", "negative", "neutral"}


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_string_is_handled_without_error():
    """
    Name: Empty content does not raise an exception
    Setup: empty string
    Action: analyze_text("")
    Expected: returns neutral result (no KeyError, no ZeroDivisionError)
    Why: The Pydantic schema allows an empty string for content (no min_length
         validator). The NLP functions must be defensive against this.
    """
    result = analyze_text("")
    assert result["sentiment_label"] == "neutral"
    assert result["sentiment_score"] == 0.0
    assert result["keywords"] == []


def test_single_positive_word():
    """
    Name: A one-word positive entry scores positive
    Setup: single word "happy"
    Action: compute_sentiment("happy")
    Expected: label == "positive"
    Why: Edge case — a very short entry still deserves accurate scoring.
    """
    score, label = compute_sentiment("happy")
    assert label == "positive"


# ---------------------------------------------------------------------------
# AI safety wording — crisis keyword detection
# ---------------------------------------------------------------------------

def test_crisis_detection_flags_suicide_keyword():
    """
    Name: The word "suicide" triggers the safety flag
    Setup: sentence containing "suicide"
    Action: detect_safety_keywords(text)
    Expected: flagged == True, matched list non-empty
    Why: "suicide" is the most explicit crisis signal. Missing it is a
         direct patient-safety failure.
    """
    flagged, matched = detect_safety_keywords("I have been thinking about suicide.")
    assert flagged is True
    assert len(matched) > 0


def test_crisis_detection_flags_multi_word_phrase():
    """
    Name: Multi-word crisis phrase "want to die" is detected
    Setup: sentence containing "want to die"
    Action: detect_safety_keywords(text)
    Expected: flagged == True
    Why: Crisis phrases are often multi-word; single-word matching would miss
         the most common expressions of suicidal ideation.
    """
    flagged, matched = detect_safety_keywords("Sometimes I just want to die.")
    assert flagged is True


def test_crisis_detection_flags_self_harm_phrase():
    """
    Name: Self-harm language is detected
    Setup: sentence containing the exact phrase "hurt myself"
    Action: detect_safety_keywords(text)
    Expected: flagged == True
    Why: Self-harm content is a second axis of crisis risk. The detector
         uses substring matching, so the exact phrase "hurt myself" must be
         present in the text to trigger.
    """
    flagged, matched = detect_safety_keywords("I want to hurt myself tonight.")
    assert flagged is True


def test_crisis_detection_safe_on_ordinary_distress():
    """
    Name: Ordinary negative language does not trigger the safety flag
    Setup: a distressed but non-crisis sentence
    Action: detect_safety_keywords(text)
    Expected: flagged == False
    Why: Over-flagging safe content erodes user trust, causes alert fatigue,
         and may discourage people from writing honestly about difficult days.
    """
    flagged, _ = detect_safety_keywords(
        "I'm really down today. Work was awful and I'm exhausted."
    )
    assert flagged is False


def test_safety_resource_message_includes_988_hotline():
    """
    Name: The crisis resource message references the 988 Suicide & Crisis Lifeline
    Setup: import SAFETY_RESOURCE_MESSAGE constant
    Action: check message content
    Expected: string contains "988"
    Why: 988 is the correct US crisis lifeline number as of 2022. An outdated
         or missing number in the safety message could prevent someone from
         getting help.
    """
    assert "988" in SAFETY_RESOURCE_MESSAGE


def test_safety_resource_message_includes_crisis_text_line():
    """
    Name: The crisis resource message references the Crisis Text Line
    Setup: import SAFETY_RESOURCE_MESSAGE constant
    Action: check message content
    Expected: string contains "741741" (Crisis Text Line short code)
    Why: Not every person in crisis can make a phone call; the text option
         must be present for accessibility.
    """
    assert "741741" in SAFETY_RESOURCE_MESSAGE
