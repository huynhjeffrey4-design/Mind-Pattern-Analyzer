"""
Tests: Protecting user privacy

Covers authentication enforcement and cross-user data isolation across
all major endpoints.

Categories covered:
  - Privacy/security (primary)
  - Bad input (malformed / missing tokens)
"""
from datetime import timedelta
from app.core.security import create_access_token
from tests.conftest import seed_checkins


# ---------------------------------------------------------------------------
# Authentication enforcement
# ---------------------------------------------------------------------------

def test_journals_list_requires_auth(client):
    """
    Name: GET /journals without a token returns 401
    Setup: no Authorization header
    Action: GET /journals
    Expected: 401
    Why: Catch-all auth test for the most common read path.
    """
    assert client.get("/api/journals").status_code == 401


def test_journals_post_requires_auth(client):
    """
    Name: POST /journals without a token returns 401
    Setup: no Authorization header
    Action: POST /journals with valid body
    Expected: 401
    Why: An unauthenticated write could create orphaned or attacker-owned
         rows if the user_id lookup is skipped.
    """
    resp = client.post("/api/journals", json={"content": "Unauthenticated."})
    assert resp.status_code == 401


def test_insights_generate_requires_auth(client):
    """
    Name: POST /insights/generate without a token returns 401
    Setup: no Authorization header
    Action: POST /insights/generate
    Expected: 401
    Why: Insights are computed from private check-in data; the route must
         not run without knowing who is asking.
    """
    assert client.post("/api/insights/generate").status_code == 401


def test_checkins_list_requires_auth(client):
    """
    Name: GET /checkins without a token returns 401
    Setup: no Authorization header
    Action: GET /checkins
    Expected: 401
    Why: Check-ins contain sensitive daily health data; the read endpoint
         must enforce auth.
    """
    assert client.get("/api/checkins").status_code == 401


def test_dashboard_summary_requires_auth(client):
    """
    Name: GET /dashboard/summary without a token returns 401
    Setup: no Authorization header
    Action: GET /dashboard/summary
    Expected: 401
    Why: The dashboard aggregates all of a user's health data — it is a
         high-value target for unauthenticated access.
    """
    assert client.get("/api/dashboard/summary").status_code == 401


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------

def test_malformed_token_is_rejected(client):
    """
    Name: A garbled Bearer token returns 401
    Setup: random string in the Authorization header
    Action: GET /journals
    Expected: 401
    Why: The server must not crash (500) or succeed (200) on a token it
         cannot decode; it must reject it cleanly.
    """
    headers = {"Authorization": "Bearer this-is-not-a-valid-jwt"}
    assert client.get("/api/journals", headers=headers).status_code == 401


def test_expired_token_is_rejected(client, alice):
    """
    Name: An expired JWT is rejected
    Setup: generate a token that expired 1 hour ago
    Action: GET /journals with the expired token
    Expected: 401
    Why: Tokens have expiry for a reason — accepting expired tokens
         would allow indefinite access from a stolen token.
    """
    expired_token = create_access_token(
        {"sub": str(alice.id)}, expires_delta=timedelta(hours=-1)
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    assert client.get("/api/journals", headers=headers).status_code == 401


# ---------------------------------------------------------------------------
# Cross-user data isolation
# ---------------------------------------------------------------------------

def test_user_cannot_read_other_users_journal_by_id(
    client, alice, alice_headers, bob_headers
):
    """
    Name: Bob cannot read Alice's journal entry by its ID
    Setup: alice creates an entry; bob uses the same ID
    Action: GET /journals/{alice_entry_id} with bob's token
    Expected: 404
    Why: Journal entries are the most sensitive data in the app. A missing
         user_id filter on the single-record GET would expose every entry
         to any authenticated user.
    """
    create = client.post(
        "/api/journals",
        json={"content": "Alice's private thoughts."},
        headers=alice_headers,
    )
    entry_id = create.json()["id"]

    assert client.get(f"/api/journals/{entry_id}", headers=bob_headers).status_code == 404


def test_journal_list_excludes_other_users_entries(
    client, alice_headers, bob_headers
):
    """
    Name: Alice's entries are absent from Bob's journal list
    Setup: both alice and bob create one entry each
    Action: GET /journals with bob's token
    Expected: bob's list contains only his own entry
    Why: A missing WHERE user_id = ? on the list query would leak all users'
         entries to every authenticated user — a systemic breach, not just
         a single-record issue.
    """
    client.post(
        "/api/journals", json={"content": "Alice's entry."}, headers=alice_headers
    )
    client.post(
        "/api/journals", json={"content": "Bob's entry."}, headers=bob_headers
    )

    entries = client.get("/api/journals", headers=bob_headers).json()
    contents = [e["content"] for e in entries]
    assert "Alice's entry." not in contents
    assert "Bob's entry." in contents


def test_insights_use_only_the_requesting_users_checkins(
    client, db_session, alice, alice_headers, bob, bob_headers
):
    """
    Name: Bob's insight generation is unaffected by Alice's check-in history
    Setup: alice has 6 strong-pattern check-ins; bob has none
    Action: POST /insights/generate with bob's token
    Expected: bob sees "insufficient_data", not alice's patterns
    Why: If the insight service queries ALL check-ins instead of filtering
         by user_id, bob would receive insights derived from alice's private
         health data — a serious privacy violation.
    """
    seed_checkins(db_session, alice.id, [
        {"mood_rating": 5, "stress_level": 1, "sleep_hours": 9},
        {"mood_rating": 1, "stress_level": 5, "sleep_hours": 3},
        {"mood_rating": 5, "stress_level": 1, "sleep_hours": 9},
        {"mood_rating": 1, "stress_level": 5, "sleep_hours": 3},
        {"mood_rating": 5, "stress_level": 1, "sleep_hours": 9},
        {"mood_rating": 1, "stress_level": 5, "sleep_hours": 3},
    ])

    resp = client.post("/api/insights/generate", headers=bob_headers)
    assert resp.status_code == 200
    types = [i["insight_type"] for i in resp.json()["insights"]]
    assert "insufficient_data" in types
    assert "sleep_mood" not in types


def test_checkins_list_excludes_other_users_checkins(
    client, db_session, alice, alice_headers, bob, bob_headers
):
    """
    Name: Alice's check-ins are absent from Bob's check-in list
    Setup: alice has a check-in; bob has none
    Action: GET /checkins with bob's token
    Expected: empty list for bob
    Why: Check-ins record daily physiological and psychological data.
         Leaking them across users would expose sensitive daily health logs.
    """
    seed_checkins(db_session, alice.id, [
        {"mood_rating": 4, "stress_level": 3, "sleep_hours": 7}
    ])

    resp = client.get("/api/checkins", headers=bob_headers)
    assert resp.status_code == 200
    assert resp.json() == []
