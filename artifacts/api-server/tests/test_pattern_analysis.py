"""
Tests: Running pattern analysis
POST /api/insights/generate
GET  /api/insights

Categories covered:
  - Happy path
  - Bad input
  - Edge cases
  - Privacy/security
  - AI safety wording (factual descriptions, no alarmist language)
"""
import pytest
from tests.conftest import seed_checkins


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_generates_sleep_mood_insight_when_correlated(client, db_session, alice, alice_headers):
    """
    Name: Sleep-mood correlation detected from check-in data
    Setup: 6 check-ins alternating high/low sleep paired with high/low mood
           (strong positive correlation)
    Action: POST /insights/generate
    Expected: at least one insight with insight_type == "sleep_mood"
    Why: The sleep→mood insight is the primary pattern MindPattern promises
         to detect. If the Pearson logic is broken or the threshold is wrong,
         users see nothing useful.
    """
    seed_checkins(db_session, alice.id, [
        {"mood_rating": 5, "stress_level": 2, "sleep_hours": 9.0},
        {"mood_rating": 2, "stress_level": 4, "sleep_hours": 4.0},
        {"mood_rating": 5, "stress_level": 2, "sleep_hours": 8.5},
        {"mood_rating": 2, "stress_level": 4, "sleep_hours": 3.5},
        {"mood_rating": 4, "stress_level": 3, "sleep_hours": 8.0},
        {"mood_rating": 1, "stress_level": 5, "sleep_hours": 3.0},
    ])

    resp = client.post("/api/insights/generate", headers=alice_headers)
    assert resp.status_code == 200
    types = [i["insight_type"] for i in resp.json()["insights"]]
    assert "sleep_mood" in types


def test_generates_exercise_mood_insight_when_correlated(
    client, db_session, alice, alice_headers
):
    """
    Name: Exercise-mood correlation detected from check-in data
    Setup: 6 check-ins — exercise days show consistently higher mood
    Action: POST /insights/generate
    Expected: at least one insight with insight_type == "exercise_mood"
    Why: Exercise is a key lifestyle lever; users should be told when their
         data shows a clear exercise-mood link so they can act on it.
    """
    seed_checkins(db_session, alice.id, [
        {"mood_rating": 5, "stress_level": 2, "sleep_hours": 7, "exercised": True},
        {"mood_rating": 5, "stress_level": 2, "sleep_hours": 7, "exercised": True},
        {"mood_rating": 5, "stress_level": 2, "sleep_hours": 7, "exercised": True},
        {"mood_rating": 2, "stress_level": 4, "sleep_hours": 7, "exercised": False},
        {"mood_rating": 2, "stress_level": 4, "sleep_hours": 7, "exercised": False},
        {"mood_rating": 2, "stress_level": 4, "sleep_hours": 7, "exercised": False},
    ])

    resp = client.post("/api/insights/generate", headers=alice_headers)
    assert resp.status_code == 200
    types = [i["insight_type"] for i in resp.json()["insights"]]
    assert "exercise_mood" in types


def test_saved_insights_retrievable_via_get(client, db_session, alice, alice_headers):
    """
    Name: Generated insights are persisted and retrievable via GET
    Setup: 3 check-ins (minimum to trigger analysis)
    Action: POST /insights/generate then GET /insights
    Expected: GET returns a non-empty list
    Why: Insights are saved to the DB so users can revisit them without
         re-running the analysis. A missing save means the history tab is
         always empty.
    """
    seed_checkins(db_session, alice.id, [
        {"mood_rating": 4, "stress_level": 3, "sleep_hours": 7},
        {"mood_rating": 3, "stress_level": 3, "sleep_hours": 6},
        {"mood_rating": 5, "stress_level": 2, "sleep_hours": 8},
    ])

    client.post("/api/insights/generate", headers=alice_headers)

    resp = client.get("/api/insights", headers=alice_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ---------------------------------------------------------------------------
# Bad input
# ---------------------------------------------------------------------------

def test_generate_requires_auth(client):
    """
    Name: Unauthenticated insight generation is rejected
    Setup: no Authorization header
    Action: POST /insights/generate
    Expected: 401
    Why: Insights summarise private health data; this route must enforce auth.
    """
    resp = client.post("/api/insights/generate")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_fewer_than_3_checkins_returns_insufficient_data_message(
    client, db_session, alice, alice_headers
):
    """
    Name: <3 check-ins yields a "More Check-Ins Needed" message
    Setup: alice has only 2 check-ins
    Action: POST /insights/generate
    Expected: 200, one insight with insight_type == "insufficient_data"
    Why: Pearson correlation is meaningless with <3 points. Returning a
         misleading pattern would erode trust; the placeholder message sets
         correct expectations.
    """
    seed_checkins(db_session, alice.id, [
        {"mood_rating": 4, "stress_level": 3, "sleep_hours": 7},
        {"mood_rating": 3, "stress_level": 4, "sleep_hours": 6},
    ])

    resp = client.post("/api/insights/generate", headers=alice_headers)
    assert resp.status_code == 200
    types = [i["insight_type"] for i in resp.json()["insights"]]
    assert "insufficient_data" in types


def test_uniform_sleep_values_produce_no_sleep_mood_insight(
    client, db_session, alice, alice_headers
):
    """
    Name: Identical sleep values produce no sleep→mood correlation
    Setup: 6 check-ins all with exactly 7 hours sleep (zero variance)
    Action: POST /insights/generate
    Expected: response does NOT contain a sleep_mood insight
    Why: Pearson correlation is undefined (den_x == 0) when all x values are
         identical. The code returns 0.0, which is below the 0.2 threshold —
         so no insight should be surfaced. Showing one would be fabricating a
         pattern from flat data.
    """
    seed_checkins(db_session, alice.id, [
        {"mood_rating": r, "stress_level": 3, "sleep_hours": 7.0}
        for r in [2, 4, 3, 5, 1, 4]
    ])

    resp = client.post("/api/insights/generate", headers=alice_headers)
    assert resp.status_code == 200
    types = [i["insight_type"] for i in resp.json()["insights"]]
    assert "sleep_mood" not in types


# ---------------------------------------------------------------------------
# Privacy/security
# ---------------------------------------------------------------------------

def test_insights_are_scoped_to_the_requesting_user(
    client, db_session, alice, alice_headers, bob, bob_headers
):
    """
    Name: Bob's insight generation uses only Bob's check-ins
    Setup: alice has 6 check-ins; bob has 0
    Action: POST /insights/generate with bob's token
    Expected: bob receives "insufficient_data" (his own 0 check-ins), not
              alice's patterns
    Why: Cross-user data in insights is a serious privacy violation —
         bob would see behavioural patterns derived from alice's health data.
    """
    seed_checkins(db_session, alice.id, [
        {"mood_rating": 5, "stress_level": 2, "sleep_hours": 9},
        {"mood_rating": 2, "stress_level": 5, "sleep_hours": 4},
        {"mood_rating": 5, "stress_level": 2, "sleep_hours": 9},
        {"mood_rating": 2, "stress_level": 5, "sleep_hours": 4},
        {"mood_rating": 5, "stress_level": 2, "sleep_hours": 9},
        {"mood_rating": 2, "stress_level": 5, "sleep_hours": 4},
    ])

    resp = client.post("/api/insights/generate", headers=bob_headers)
    assert resp.status_code == 200
    types = [i["insight_type"] for i in resp.json()["insights"]]
    assert "insufficient_data" in types
    assert "sleep_mood" not in types


# ---------------------------------------------------------------------------
# AI safety wording — factual, non-clinical language
# ---------------------------------------------------------------------------

def test_insight_descriptions_do_not_contain_diagnostic_language(
    client, db_session, alice, alice_headers
):
    """
    Name: Generated insight text avoids clinical diagnosis language
    Setup: 6 check-ins that produce a sleep_mood insight
    Action: POST /insights/generate
    Expected: no insight description contains the words "diagnosis",
              "disorder", "depressed", or "clinically"
    Why: MindPattern is a self-reflection tool, not a medical device. Using
         diagnostic language could cause harm or create legal liability. The
         descriptions must stay observational ("tends to be lower") rather
         than clinical.
    """
    seed_checkins(db_session, alice.id, [
        {"mood_rating": 5, "stress_level": 2, "sleep_hours": 9},
        {"mood_rating": 1, "stress_level": 5, "sleep_hours": 3},
        {"mood_rating": 5, "stress_level": 2, "sleep_hours": 9},
        {"mood_rating": 1, "stress_level": 5, "sleep_hours": 3},
        {"mood_rating": 5, "stress_level": 2, "sleep_hours": 9},
        {"mood_rating": 1, "stress_level": 5, "sleep_hours": 3},
    ])

    resp = client.post("/api/insights/generate", headers=alice_headers)
    assert resp.status_code == 200

    forbidden = {"diagnosis", "disorder", "depressed", "clinically", "you have"}
    for insight in resp.json()["insights"]:
        description = insight.get("description", "").lower()
        for word in forbidden:
            assert word not in description, (
                f"Insight description contains forbidden clinical term '{word}': {description}"
            )


def test_insufficient_data_insight_includes_a_suggestion(
    client, db_session, alice, alice_headers
):
    """
    Name: The "not enough data" message gives actionable guidance
    Setup: alice has 2 check-ins
    Action: POST /insights/generate
    Expected: the insufficient_data insight has a non-empty `suggestion` field
    Why: A bare "not enough data" message is a dead end. Including a
         suggestion ("try logging each evening") turns a frustrating wall
         into a concrete next step.
    """
    seed_checkins(db_session, alice.id, [
        {"mood_rating": 3, "stress_level": 3, "sleep_hours": 7},
        {"mood_rating": 4, "stress_level": 2, "sleep_hours": 8},
    ])

    resp = client.post("/api/insights/generate", headers=alice_headers)
    insights = resp.json()["insights"]
    placeholder = next(i for i in insights if i["insight_type"] == "insufficient_data")
    assert placeholder["suggestion"] and len(placeholder["suggestion"]) > 10
