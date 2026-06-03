"""
Tests: Viewing journal entries
GET /api/journals
GET /api/journals/{id}

Categories covered:
  - Happy path
  - Bad input
  - Edge cases
  - Privacy/security
"""


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_list_returns_own_entries(client, alice_headers):
    """
    Name: Listed entries belong to the authenticated user
    Setup: alice creates two entries
    Action: GET /journals with alice's token
    Expected: both entries appear in the list
    Why: Verifies the basic read path works end-to-end, not just that the
         route exists.
    """
    client.post("/api/journals", json={"content": "Entry one."}, headers=alice_headers)
    client.post("/api/journals", json={"content": "Entry two."}, headers=alice_headers)

    resp = client.get("/api/journals", headers=alice_headers)
    assert resp.status_code == 200
    contents = [e["content"] for e in resp.json()]
    assert "Entry one." in contents
    assert "Entry two." in contents


def test_list_returns_most_recent_first(client, alice_headers):
    """
    Name: Entries are ordered newest-first
    Setup: alice creates entry A then entry B (B is newer)
    Action: GET /journals
    Expected: first element in response is entry B
    Why: Users expect to see their latest writing at the top; wrong ordering
         forces them to scroll to find recent entries, degrading the UX.
    """
    client.post("/api/journals", json={"content": "Older entry."}, headers=alice_headers)
    client.post("/api/journals", json={"content": "Newer entry."}, headers=alice_headers)

    resp = client.get("/api/journals", headers=alice_headers)
    assert resp.status_code == 200
    entries = resp.json()
    assert entries[0]["content"] == "Newer entry."


def test_get_by_id_returns_correct_entry(client, alice_headers):
    """
    Name: GET /{id} returns the specific entry
    Setup: alice creates an entry
    Action: GET /journals/{id} using the id from the create response
    Expected: response content matches the created entry
    Why: The single-entry view is used on the journal detail page; a wrong
         or empty response would break that screen.
    """
    create = client.post(
        "/api/journals",
        json={"title": "Test", "content": "Specific entry content."},
        headers=alice_headers,
    )
    entry_id = create.json()["id"]

    resp = client.get(f"/api/journals/{entry_id}", headers=alice_headers)
    assert resp.status_code == 200
    assert resp.json()["content"] == "Specific entry content."


def test_response_includes_nlp_fields(client, alice_headers):
    """
    Name: Response body exposes NLP analysis fields
    Setup: authenticated user
    Action: create an entry, then GET it by id
    Expected: response contains sentiment_label, sentiment_score, keywords
    Why: The frontend renders these fields in the entry card; missing fields
         would cause runtime errors or blank UI sections.
    """
    create = client.post(
        "/api/journals",
        json={"content": "I feel happy and grateful today."},
        headers=alice_headers,
    )
    entry_id = create.json()["id"]
    resp = client.get(f"/api/journals/{entry_id}", headers=alice_headers)

    data = resp.json()
    assert "sentiment_label" in data
    assert "sentiment_score" in data
    assert "keywords" in data


# ---------------------------------------------------------------------------
# Bad input
# ---------------------------------------------------------------------------

def test_get_nonexistent_id_returns_404(client, alice_headers):
    """
    Name: Non-existent ID returns 404, not 500
    Setup: empty journal for alice
    Action: GET /journals/99999
    Expected: 404
    Why: Returning 500 on a missing record is an unhandled exception —
         404 is the correct semantic and keeps error handling consistent.
    """
    resp = client.get("/api/journals/99999", headers=alice_headers)
    assert resp.status_code == 404


def test_list_requires_auth(client):
    """
    Name: Listing entries without a token is rejected
    Setup: no Authorization header
    Action: GET /journals
    Expected: 401
    Why: Journal entries are sensitive health data; unauthenticated reads
         must be blocked at the route level.
    """
    resp = client.get("/api/journals")
    assert resp.status_code == 401


def test_get_by_id_requires_auth(client, alice, alice_headers):
    """
    Name: Fetching an entry by ID without a token is rejected
    Setup: alice creates an entry
    Action: GET /journals/{id} with no Authorization header
    Expected: 401
    Why: Same as above — individual entry reads must enforce auth.
    """
    create = client.post(
        "/api/journals", json={"content": "Private."}, headers=alice_headers
    )
    entry_id = create.json()["id"]

    resp = client.get(f"/api/journals/{entry_id}")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_list_is_empty_for_new_user(client, alice_headers):
    """
    Name: Fresh user has an empty journal list
    Setup: alice exists but has never written an entry
    Action: GET /journals
    Expected: 200 with an empty array (not 404, not null)
    Why: 404 on an empty list is a common bug; the frontend must receive []
         to render the empty-state UI rather than crash.
    """
    resp = client.get("/api/journals", headers=alice_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_pagination_limit(client, alice_headers):
    """
    Name: limit query parameter caps the number of results
    Setup: alice creates 5 entries
    Action: GET /journals?limit=2
    Expected: exactly 2 entries returned
    Why: Without working pagination, a user with many entries would receive
         unbounded responses, degrading performance.
    """
    for i in range(5):
        client.post(
            "/api/journals", json={"content": f"Entry {i}"}, headers=alice_headers
        )

    resp = client.get("/api/journals?limit=2", headers=alice_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_pagination_offset(client, alice_headers):
    """
    Name: offset query parameter skips earlier results
    Setup: alice creates 3 entries; the last-created will be first in the list
    Action: GET /journals?limit=1&offset=1
    Expected: the second entry (by recency) is returned, not the first
    Why: Pagination without a working offset forces the client to implement
         client-side pagination, which re-downloads all data.
    """
    for label in ["first", "second", "third"]:
        client.post(
            "/api/journals", json={"content": label}, headers=alice_headers
        )

    full = client.get("/api/journals", headers=alice_headers).json()
    paged = client.get("/api/journals?limit=1&offset=1", headers=alice_headers).json()

    assert len(paged) == 1
    assert paged[0]["id"] == full[1]["id"]


# ---------------------------------------------------------------------------
# Privacy/security
# ---------------------------------------------------------------------------

def test_user_cannot_see_other_users_entry_by_id(client, alice, alice_headers, bob, bob_headers):
    """
    Name: User B cannot read user A's entry by ID
    Setup: alice creates an entry; bob knows the entry's id
    Action: GET /journals/{alice_entry_id} with bob's token
    Expected: 404 (not 403 — the query filters by user_id so the row is
              simply not found)
    Why: Returning 403 leaks the existence of the entry. 404 is both
         correct and privacy-preserving.
    """
    create = client.post(
        "/api/journals", json={"content": "Alice's private thoughts."}, headers=alice_headers
    )
    entry_id = create.json()["id"]

    resp = client.get(f"/api/journals/{entry_id}", headers=bob_headers)
    assert resp.status_code == 404


def test_list_does_not_include_other_users_entries(client, alice_headers, bob_headers):
    """
    Name: Alice's entries never appear in Bob's journal list
    Setup: alice and bob each create one entry
    Action: GET /journals with bob's token
    Expected: response contains only bob's entry
    Why: Cross-user data leakage in a list endpoint is harder to spot than
         a single-record leak — this test catches an absent WHERE clause.
    """
    client.post(
        "/api/journals", json={"content": "Alice's entry."}, headers=alice_headers
    )
    client.post(
        "/api/journals", json={"content": "Bob's entry."}, headers=bob_headers
    )

    resp = client.get("/api/journals", headers=bob_headers)
    assert resp.status_code == 200
    entries = resp.json()
    assert all(e["content"] != "Alice's entry." for e in entries)
    assert any(e["content"] == "Bob's entry." for e in entries)
