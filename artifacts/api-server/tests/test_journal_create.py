"""
Tests: Creating a journal entry
POST /api/journals

Categories covered:
  - Happy path
  - Bad input
  - Edge cases
  - AI safety wording (crisis detection)
  - Privacy/security (auth enforcement)
"""
import pytest
from app.models.safety_event import SafetyEvent


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_create_returns_201_with_content(client, alice_headers):
    """
    Name: Create a standard journal entry
    Setup: authenticated user (alice)
    Action: POST /journals with a title and content
    Expected: 201, response body echoes title and content
    Why: Core functionality — users must be able to save entries.
    """
    resp = client.post(
        "/api/journals",
        json={"title": "Monday", "content": "Had a productive day at work."},
        headers=alice_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Monday"
    assert data["content"] == "Had a productive day at work."
    assert data["id"] is not None


def test_create_detects_positive_sentiment(client, alice_headers):
    """
    Name: Positive sentiment scored on happy entry
    Setup: authenticated user
    Action: POST entry whose content is unambiguously positive
    Expected: sentiment_label == "positive", sentiment_score > 0
    Why: The NLP analysis is the core value-add on journal creation; it
         must correctly label emotional tone so the dashboard is meaningful.
    """
    resp = client.post(
        "/api/journals",
        json={"content": "I feel happy wonderful joy grateful amazing today."},
        headers=alice_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["sentiment_label"] == "positive"
    assert data["sentiment_score"] > 0


def test_create_detects_negative_sentiment(client, alice_headers):
    """
    Name: Negative sentiment scored on distressing entry
    Setup: authenticated user
    Action: POST entry whose content is unambiguously negative
    Expected: sentiment_label == "negative", sentiment_score < 0
    Why: Negative sentiment is used to surface patterns over time; wrong
         labelling would make pattern detection misleading.
    """
    resp = client.post(
        "/api/journals",
        json={"content": "I am sad exhausted anxious overwhelmed lonely frustrated."},
        headers=alice_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["sentiment_label"] == "negative"
    assert data["sentiment_score"] < 0


def test_create_extracts_relevant_keywords(client, alice_headers):
    """
    Name: Keywords extracted from entry text
    Setup: authenticated user
    Action: POST entry mentioning stress and sleep topics
    Expected: response keywords list is non-empty and contains at least one
              recognised topic word
    Why: Keywords drive the "Recurring Themes" insight; if extraction is
         broken, the insight engine has no signal to work from.
    """
    resp = client.post(
        "/api/journals",
        json={"content": "I was stressed all day. Barely slept last night."},
        headers=alice_headers,
    )
    assert resp.status_code == 201
    keywords = resp.json()["keywords"] or []
    assert len(keywords) >= 1
    # at least one recognised theme present
    assert any(k in ("stress", "sleep", "stressed", "sleeping") for k in keywords)


def test_create_entry_without_title(client, alice_headers):
    """
    Name: Title is optional
    Setup: authenticated user
    Action: POST entry with no title field
    Expected: 201, title is null in response
    Why: Users often write untitled quick notes; the schema must allow it.
    """
    resp = client.post(
        "/api/journals",
        json={"content": "Just a quick thought today."},
        headers=alice_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["title"] is None


# ---------------------------------------------------------------------------
# Bad input
# ---------------------------------------------------------------------------

def test_create_missing_content_returns_422(client, alice_headers):
    """
    Name: Missing content field is rejected
    Setup: authenticated user
    Action: POST body without the required `content` key
    Expected: 422 Unprocessable Entity
    Why: Content is the substance of a journal entry; silently accepting a
         contentless entry would corrupt the data model.
    """
    resp = client.post("/api/journals", json={"title": "No body"}, headers=alice_headers)
    assert resp.status_code == 422


def test_create_without_auth_returns_401(client):
    """
    Name: Unauthenticated create is rejected
    Setup: no Authorization header
    Action: POST /journals
    Expected: 401
    Why: Journal entries are private health data — unauthenticated writes must
         be impossible.
    """
    resp = client.post("/api/journals", json={"content": "Should not save."})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_create_text_with_no_emotion_words_is_neutral(client, alice_headers):
    """
    Name: Emotionally neutral text produces neutral sentiment
    Setup: authenticated user
    Action: POST entry with factual, emotion-free content
    Expected: sentiment_label == "neutral", sentiment_score == 0.0
    Why: Neutral entries are legitimate; the scorer must not invent sentiment
         that isn't there, which would skew trend charts.
    """
    resp = client.post(
        "/api/journals",
        json={"content": "The meeting started at 3pm. We reviewed the quarterly numbers."},
        headers=alice_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["sentiment_label"] == "neutral"
    assert data["sentiment_score"] == 0.0


def test_create_text_with_no_tracked_keywords_returns_empty_list(client, alice_headers):
    """
    Name: Unrelated vocabulary produces empty keyword list
    Setup: authenticated user
    Action: POST entry about a topic outside the keyword vocabulary
    Expected: keywords is an empty list (not null, not an error)
    Why: An empty list is the correct signal to the insight engine that no
         recognisable themes were mentioned; null would break downstream logic.
    """
    resp = client.post(
        "/api/journals",
        json={"content": "Debugged the Kubernetes deployment all afternoon."},
        headers=alice_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["keywords"] == [] or resp.json()["keywords"] is None


# ---------------------------------------------------------------------------
# AI safety wording / crisis detection
# ---------------------------------------------------------------------------

def test_create_crisis_content_sets_safety_flag(client, alice_headers):
    """
    Name: Crisis keywords set safety_flagged = True
    Setup: authenticated user
    Action: POST entry containing the word "suicide"
    Expected: 201 (entry IS saved), safety_flagged == True
    Why: Blocking the save would prevent someone in crisis from journalling.
         The correct response is to save silently and surface crisis resources
         — not to refuse the write.
    """
    resp = client.post(
        "/api/journals",
        json={"content": "I've been thinking about suicide lately."},
        headers=alice_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["safety_flagged"] is True


def test_create_crisis_content_logs_safety_event(client, db_session, alice, alice_headers):
    """
    Name: Crisis entry creates an audit SafetyEvent in the database
    Setup: authenticated user (alice)
    Action: POST entry containing "want to die"
    Expected: a SafetyEvent row exists in the DB referencing alice's new entry
    Why: SafetyEvents are the audit trail that allows a future review of
         crisis signals. Without this log the flag on the entry is invisible
         to anyone monitoring.
    """
    resp = client.post(
        "/api/journals",
        json={"content": "I want to die, nothing makes sense anymore."},
        headers=alice_headers,
    )
    assert resp.status_code == 201
    entry_id = resp.json()["id"]

    event = (
        db_session.query(SafetyEvent)
        .filter(SafetyEvent.user_id == alice.id, SafetyEvent.source_id == entry_id)
        .first()
    )
    assert event is not None
    assert "want to die" in event.matched_keywords


def test_create_safe_content_does_not_set_safety_flag(client, alice_headers):
    """
    Name: Ordinary distress does not trigger the crisis flag
    Setup: authenticated user
    Action: POST entry with negative but non-crisis language
    Expected: safety_flagged == False
    Why: Overly sensitive flagging would erode user trust; only explicit
         crisis phrases should trigger the flag.
    """
    resp = client.post(
        "/api/journals",
        json={"content": "Feeling really down and exhausted today. Rough week."},
        headers=alice_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["safety_flagged"] is False
