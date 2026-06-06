"""
Tests: Insight generation when sufficient check-in data exists

The existing test_pattern_analysis.py uses minimal 6-row fixtures to verify
that the Pearson math fires. These tests use realistic 30–60 row datasets to
verify the full pipeline — seeding, correlation detection, persistence, and
response shape — at a volume closer to real-world use.

Features tested:
  - All three correlation types (sleep→mood, exercise→mood, workload→stress)
  - Journal keyword recurrence insight
  - Repeated generate calls (idempotency / no duplicates)
  - Generated count accuracy
  - Response structure completeness

Categories covered:
  - Happy path (primary)
  - Edge cases
  - Privacy/security
"""
import pytest
from tests.conftest import seed_checkins
from app.models.journal import JournalEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_correlated(db, user_id, n=30):
    """
    Seed n check-ins with three explicit correlations:
      - sleep > 7.5h  →  mood 4-5
      - sleep < 5.5h  →  mood 1-2      (sleep→mood r > 0.20)
      - workload 4-5  →  stress 4-5
      - workload 1-2  →  stress 1-2    (workload→stress r > 0.25)
      - exercised     →  mood +1       (exercise diff > 0.30)
    """
    rows = []
    for i in range(n):
        well_rested = (i % 2 == 0)
        sleep = 8.5 if well_rested else 4.5
        base_mood = 4 if well_rested else 2
        high_workload = (i % 3 == 0)
        workload = 5 if high_workload else 2
        base_stress = 5 if high_workload else 2
        exercised = (i % 4 == 0)
        mood = min(5, base_mood + (1 if exercised else 0))
        rows.append({
            "date": f"2026-{str(3 + i // 30).zfill(2)}-{str((i % 28) + 1).zfill(2)}",
            "mood_rating": mood,
            "stress_level": base_stress,
            "sleep_hours": sleep,
            "exercised": exercised,
            "workload_level": workload,
        })
    return seed_checkins(db, user_id, rows)


def _seed_journals(db, user_id, keyword_content_pairs):
    """Directly insert JournalEntry rows with pre-set keywords."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    for content, keywords in keyword_content_pairs:
        entry = JournalEntry(
            user_id=user_id,
            content=content,
            keywords=keywords,
            sentiment_score=0.0,
            sentiment_label="neutral",
            safety_flagged=False,
            created_at=now,
            updated_at=now,
        )
        db.add(entry)
    db.commit()


# ---------------------------------------------------------------------------
# Happy path — all three correlation types
# ---------------------------------------------------------------------------

def test_workload_stress_insight_detected(client, db_session, alice, alice_headers):
    """
    Name: Workload→stress correlation surfaces as an insight
    Setup: 30 check-ins where high workload (4-5) always pairs with high
           stress (4-5) and low workload (1-2) pairs with low stress (1-2)
    Action: POST /insights/generate
    Expected: at least one insight with insight_type == "workload_stress"
    Why: workload→stress is the third correlation the service detects but it
         was missing from previous tests. If the filter (workload_level IS NOT
         NULL) or the r threshold logic is broken, this is the only test that
         catches it.
    """
    _seed_correlated(db_session, alice.id, n=30)

    resp = client.post("/api/insights/generate", headers=alice_headers)
    assert resp.status_code == 200
    types = [i["insight_type"] for i in resp.json()["insights"]]
    assert "workload_stress" in types, f"Expected workload_stress, got: {types}"


def test_all_three_correlation_insights_appear_together(
    client, db_session, alice, alice_headers
):
    """
    Name: All three correlations surface simultaneously from a single dataset
    Setup: 60 check-ins with explicit sleep→mood, exercise→mood, and
           workload→stress correlations
    Action: POST /insights/generate
    Expected: response contains sleep_mood, exercise_mood, and workload_stress
    Why: Using only 6-row minimal fixtures in isolation can mask interactions
         between the three detectors. This test validates that none of them
         suppress the others when all three patterns are present in the data.
    """
    _seed_correlated(db_session, alice.id, n=60)

    resp = client.post("/api/insights/generate", headers=alice_headers)
    assert resp.status_code == 200
    types = [i["insight_type"] for i in resp.json()["insights"]]

    assert "sleep_mood" in types,     f"Missing sleep_mood — got: {types}"
    assert "exercise_mood" in types,  f"Missing exercise_mood — got: {types}"
    assert "workload_stress" in types, f"Missing workload_stress — got: {types}"


def test_journal_keywords_insight_generated_when_recurring_themes_exist(
    client, db_session, alice, alice_headers
):
    """
    Name: Recurring journal themes surface as a journal_keywords insight
    Setup: 3 check-ins (minimum) + 5 journal entries all tagged with "stress"
    Action: POST /insights/generate
    Expected: at least one insight with insight_type == "journal_keywords"
    Why: The journal_keywords insight is driven by a separate counter on
         journal entries, not check-in correlations. It was untested before
         and its presence here verifies the two data sources (checkins +
         journals) are combined correctly in the insight pipeline.
    """
    seed_checkins(db_session, alice.id, [
        {"mood_rating": 3, "stress_level": 3, "sleep_hours": 7},
        {"mood_rating": 3, "stress_level": 3, "sleep_hours": 7},
        {"mood_rating": 3, "stress_level": 3, "sleep_hours": 7},
    ])
    _seed_journals(db_session, alice.id, [
        ("Work was overwhelming again", "stress, work"),
        ("Can't shake the stress from deadlines", "stress, work"),
        ("Another stressful meeting", "stress"),
        ("Feeling the pressure build up", "stress, anxiety"),
        ("So much stress about the project", "stress, work"),
    ])

    resp = client.post("/api/insights/generate", headers=alice_headers)
    assert resp.status_code == 200
    types = [i["insight_type"] for i in resp.json()["insights"]]
    assert "journal_keywords" in types, f"Expected journal_keywords, got: {types}"


def test_journal_keywords_insight_lists_top_recurring_word(
    client, db_session, alice, alice_headers
):
    """
    Name: The journal keywords insight description names the most frequent theme
    Setup: 3 check-ins + 5 journal entries all containing the keyword "stress"
    Action: POST /insights/generate
    Expected: the journal_keywords insight description contains "stress"
    Why: Surfacing generic insight text without the actual word is not useful.
         The description must name the theme so users can recognise what the
         pattern refers to.
    """
    seed_checkins(db_session, alice.id, [
        {"mood_rating": 3, "stress_level": 3, "sleep_hours": 7},
        {"mood_rating": 3, "stress_level": 3, "sleep_hours": 7},
        {"mood_rating": 3, "stress_level": 3, "sleep_hours": 7},
    ])
    _seed_journals(db_session, alice.id, [
        ("Rough day", "stress"),
        ("Busy week", "stress"),
        ("Too much on my plate", "stress"),
        ("Exhausted by everything", "stress"),
        ("Just stressed again", "stress"),
    ])

    resp = client.post("/api/insights/generate", headers=alice_headers)
    kw_insight = next(
        (i for i in resp.json()["insights"] if i["insight_type"] == "journal_keywords"),
        None,
    )
    assert kw_insight is not None
    assert "stress" in kw_insight["description"].lower()


# ---------------------------------------------------------------------------
# Happy path — response structure
# ---------------------------------------------------------------------------

def test_generate_response_includes_generated_count(
    client, db_session, alice, alice_headers
):
    """
    Name: generate response body includes an accurate generated_count
    Setup: 30 check-ins with three detectable correlations
    Action: POST /insights/generate
    Expected: generated_count > 0 and matches the number of insights returned
    Why: The frontend uses generated_count to show a "X new insights found"
         banner. A mismatched count (e.g. always 0) would make every run look
         like it produced nothing.
    """
    _seed_correlated(db_session, alice.id, n=30)

    resp = client.post("/api/insights/generate", headers=alice_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["generated_count"] > 0
    assert body["generated_count"] == len(body["insights"])


def test_each_insight_has_required_fields(client, db_session, alice, alice_headers):
    """
    Name: Every insight in the response carries all required fields
    Setup: 30 check-ins with detectable correlations
    Action: POST /insights/generate
    Expected: each insight object has id, insight_type, title, description,
              suggestion, created_at fields; confidence is present (may be null)
    Why: Missing fields cause frontend runtime errors. Spot-checking a single
         field misses fields that are None-coalesced silently.
    """
    _seed_correlated(db_session, alice.id, n=30)

    resp = client.post("/api/insights/generate", headers=alice_headers)
    required = {"id", "insight_type", "title", "description", "suggestion", "created_at"}
    for insight in resp.json()["insights"]:
        missing = required - set(insight.keys())
        assert not missing, f"Insight missing fields: {missing} — full insight: {insight}"
        assert insight["title"], "title must not be empty"
        assert insight["description"], "description must not be empty"
        assert insight["suggestion"], "suggestion must not be empty"


# ---------------------------------------------------------------------------
# Edge cases — repeated calls
# ---------------------------------------------------------------------------

def test_second_generate_call_does_not_duplicate_insight_types(
    client, db_session, alice, alice_headers
):
    """
    Name: Calling generate twice does not accumulate duplicate insight rows
    Setup: 30 check-ins with detectable correlations
    Action: POST /insights/generate twice; GET /insights
    Expected: the GET response does not contain two entries with the same
              insight_type from the same run
    Why: Without a clear-and-replace strategy, each generate call would append
         more rows, so after ten runs the user would see ten sleep_mood cards.
         This test catches that accumulation bug.
    """
    _seed_correlated(db_session, alice.id, n=30)

    client.post("/api/insights/generate", headers=alice_headers)
    client.post("/api/insights/generate", headers=alice_headers)

    resp = client.get("/api/insights", headers=alice_headers)
    assert resp.status_code == 200
    types = [i["insight_type"] for i in resp.json()]
    # Each type should appear at most once — no duplicates from double-generate
    from collections import Counter
    for t, count in Counter(types).items():
        assert count == 1, f"insight_type '{t}' appears {count} times — duplicate rows created"


def test_insights_reflect_updated_data_on_second_generate(
    client, db_session, alice, alice_headers
):
    """
    Name: A second generate call with more data can surface additional insights
    Setup: first generate with 2 check-ins (insufficient); then add 30 more
           correlated check-ins and generate again
    Action: POST /insights/generate twice
    Expected: second call returns specific correlation insights, not just
              "insufficient_data"
    Why: Users start with few check-ins and add more over time. The generate
         endpoint must re-analyse the latest data each time, not cache the
         first result forever.
    """
    # First call — not enough data
    seed_checkins(db_session, alice.id, [
        {"mood_rating": 3, "stress_level": 3, "sleep_hours": 7},
        {"mood_rating": 4, "stress_level": 2, "sleep_hours": 8},
    ])
    first = client.post("/api/insights/generate", headers=alice_headers)
    first_types = [i["insight_type"] for i in first.json()["insights"]]
    assert "insufficient_data" in first_types

    # Add strongly correlated data
    _seed_correlated(db_session, alice.id, n=30)

    # Second call — should now surface real patterns
    second = client.post("/api/insights/generate", headers=alice_headers)
    second_types = [i["insight_type"] for i in second.json()["insights"]]
    assert "insufficient_data" not in second_types, (
        "After adding 30 correlated check-ins, insights should not still say "
        "'insufficient_data'"
    )
    real_types = {"sleep_mood", "exercise_mood", "workload_stress", "journal_keywords"}
    assert real_types & set(second_types), (
        f"Expected at least one correlation insight, got: {second_types}"
    )


# ---------------------------------------------------------------------------
# Privacy/security
# ---------------------------------------------------------------------------

def test_insights_list_only_returns_own_insights(
    client, db_session, alice, alice_headers, bob, bob_headers
):
    """
    Name: GET /insights returns only the authenticated user's insights
    Setup: alice generates insights from 30 correlated check-ins; bob has none
    Action: GET /insights with bob's token
    Expected: bob's list is empty
    Why: Insights are derived from private health data. If the list query
         misses the user_id filter, every user sees everyone else's patterns.
    """
    _seed_correlated(db_session, alice.id, n=30)
    client.post("/api/insights/generate", headers=alice_headers)

    bob_insights = client.get("/api/insights", headers=bob_headers)
    assert bob_insights.status_code == 200
    assert bob_insights.json() == [], (
        f"Bob should see no insights, got: {bob_insights.json()}"
    )
