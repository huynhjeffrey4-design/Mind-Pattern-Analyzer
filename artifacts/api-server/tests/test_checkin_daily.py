"""
Tests: Daily check-in once-per-day enforcement, editing, and viewing

Intended behavior under test:
  1. A user can create exactly one check-in per calendar day.
  2. A second POST for the same date returns 409 — no duplicate is created.
  3. The user can edit today's check-in via PATCH /checkins/{id}.
  4. The user can view all their check-ins via GET /checkins.
  5. The user can view one check-in by ID via GET /checkins/{id}.
  6. Users can only view and edit their own check-ins.
  7. All routes require authentication.

Field name reference (actual API names):
  mood_rating      — mood on a 1–5 scale
  stress_level     — stress on a 1–5 scale
  sleep_hours      — hours of sleep (float, 0–24)
  energy_level     — energy on a 1–5 scale
  exercised        — bool
  socialized       — bool
  workload_level   — workload on a 1–5 scale
  notes            — optional free-text
"""
import pytest

TODAY = "2026-07-01"
OTHER_DAY = "2026-06-30"

CHECKIN_A = {
    "date": TODAY,
    "mood_rating": 3,
    "stress_level": 4,
    "sleep_hours": 6.5,
    "energy_level": 2,
    "exercised": False,
    "socialized": True,
    "workload_level": 4,
    "notes": "Initial daily check-in.",
}

CHECKIN_UPDATED = {
    "mood_rating": 5,
    "stress_level": 2,
    "sleep_hours": 8.0,
    "energy_level": 5,
    "exercised": True,
    "socialized": True,
    "workload_level": 2,
    "notes": "Updated check-in for today.",
}


# ---------------------------------------------------------------------------
# 1. Create one check-in
# ---------------------------------------------------------------------------

def test_create_checkin_returns_201(client, alice_headers):
    """
    Name: Creating a check-in returns 201 and the full record
    Setup: authenticated alice, no prior check-in for TODAY
    Action: POST /checkins with complete valid data
    Expected: 201 with id, mood_rating, stress_level, sleep_hours,
              energy_level, exercised, socialized, workload_level,
              notes, created_at all present
    Why: Verifies the basic creation path end-to-end and that every field
         a client depends on is serialised in the response.
    """
    resp = client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    assert resp.status_code == 201
    body = resp.json()

    required = {
        "id", "mood_rating", "stress_level", "sleep_hours",
        "energy_level", "exercised", "socialized", "workload_level",
        "notes", "created_at",
    }
    missing = required - set(body.keys())
    assert not missing, f"Response missing fields: {missing}"

    assert body["mood_rating"] == CHECKIN_A["mood_rating"]
    assert body["stress_level"] == CHECKIN_A["stress_level"]
    assert body["sleep_hours"] == CHECKIN_A["sleep_hours"]
    assert body["exercised"] == CHECKIN_A["exercised"]
    assert body["socialized"] == CHECKIN_A["socialized"]
    assert body["workload_level"] == CHECKIN_A["workload_level"]
    assert body["notes"] == CHECKIN_A["notes"]


# ---------------------------------------------------------------------------
# 2. One check-in per calendar day
# ---------------------------------------------------------------------------

def test_duplicate_checkin_same_day_returns_409(client, alice_headers):
    """
    Name: Second check-in for the same date is rejected with 409
    Setup: alice already has a check-in for TODAY
    Action: POST /checkins with the same date again
    Expected: 409 Conflict
    Why: Without this guard, a user can flood the database with check-ins for
         the same day, producing meaningless trend data and breaking streak
         calculations.
    """
    client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    resp = client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    assert resp.status_code == 409


def test_duplicate_rejected_does_not_create_second_row(client, alice_headers):
    """
    Name: After a rejected duplicate, GET /checkins still returns exactly one
          entry for that date
    Setup: two POST attempts for TODAY
    Action: GET /checkins
    Expected: exactly one entry with date == TODAY in the list
    Why: A bug that saves the record before raising the conflict would pass
         test_duplicate_checkin_same_day_returns_409 but fail this one.
    """
    client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)

    resp = client.get("/api/checkins", headers=alice_headers)
    assert resp.status_code == 200
    today_entries = [c for c in resp.json() if c["date"] == TODAY]
    assert len(today_entries) == 1, (
        f"Expected 1 check-in for {TODAY}, found {len(today_entries)}"
    )


def test_different_dates_both_accepted(client, alice_headers):
    """
    Name: Check-ins on different calendar dates are both accepted
    Setup: one check-in for TODAY, one for OTHER_DAY
    Action: POST both, then GET /checkins
    Expected: both appear in the list (no false positive de-duplication)
    Why: The uniqueness constraint is (user_id, date); same user, different
         date must succeed.
    """
    client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    client.post(
        "/api/checkins",
        json={**CHECKIN_A, "date": OTHER_DAY},
        headers=alice_headers,
    )

    resp = client.get("/api/checkins", headers=alice_headers)
    dates = [c["date"] for c in resp.json()]
    assert TODAY in dates
    assert OTHER_DAY in dates


# ---------------------------------------------------------------------------
# 3. Edit today's check-in
# ---------------------------------------------------------------------------

def test_patch_checkin_returns_200_with_updated_values(client, alice_headers):
    """
    Name: PATCH /checkins/{id} returns 200 with updated field values
    Setup: alice creates a check-in, then patches it
    Action: PATCH /checkins/{id} with new mood_rating, stress_level, notes
    Expected: 200 and the response body reflects the new values
    Why: The update path is the primary way users correct a check-in they
         submitted with wrong values. A wrong status or stale values in the
         response breaks the UI optimistic update.
    """
    create = client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    entry_id = create.json()["id"]

    resp = client.patch(
        f"/api/checkins/{entry_id}",
        json=CHECKIN_UPDATED,
        headers=alice_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mood_rating"] == CHECKIN_UPDATED["mood_rating"]
    assert body["stress_level"] == CHECKIN_UPDATED["stress_level"]
    assert body["sleep_hours"] == CHECKIN_UPDATED["sleep_hours"]
    assert body["energy_level"] == CHECKIN_UPDATED["energy_level"]
    assert body["exercised"] == CHECKIN_UPDATED["exercised"]
    assert body["notes"] == CHECKIN_UPDATED["notes"]


def test_patch_persists_to_database(client, alice_headers):
    """
    Name: Updated values survive a subsequent GET by ID
    Setup: alice creates then patches a check-in
    Action: GET /checkins/{id} after the PATCH
    Expected: persisted values match what was patched, not the original
    Why: If the repository commits the update but refreshes a stale in-memory
         object, the PATCH response looks correct but a fresh fetch reveals the
         old data — this test catches that.
    """
    create = client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    entry_id = create.json()["id"]

    client.patch(
        f"/api/checkins/{entry_id}", json=CHECKIN_UPDATED, headers=alice_headers
    )

    resp = client.get(f"/api/checkins/{entry_id}", headers=alice_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["mood_rating"] == CHECKIN_UPDATED["mood_rating"]
    assert body["stress_level"] == CHECKIN_UPDATED["stress_level"]
    assert body["notes"] == CHECKIN_UPDATED["notes"]


def test_patch_partial_update_leaves_other_fields_unchanged(client, alice_headers):
    """
    Name: PATCH with a subset of fields only changes those fields
    Setup: alice creates a check-in with all fields set
    Action: PATCH with only mood_rating changed
    Expected: mood_rating is updated; all other fields retain original values
    Why: PATCH semantics require partial updates. If every unspecified field
         is reset to None or a default, the user loses data silently.
    """
    create = client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    entry_id = create.json()["id"]

    client.patch(
        f"/api/checkins/{entry_id}",
        json={"mood_rating": 1},
        headers=alice_headers,
    )

    resp = client.get(f"/api/checkins/{entry_id}", headers=alice_headers)
    body = resp.json()
    assert body["mood_rating"] == 1
    assert body["stress_level"] == CHECKIN_A["stress_level"], "stress_level should be unchanged"
    assert body["sleep_hours"] == CHECKIN_A["sleep_hours"], "sleep_hours should be unchanged"
    assert body["notes"] == CHECKIN_A["notes"], "notes should be unchanged"


def test_patch_nonexistent_checkin_returns_404(client, alice_headers):
    """
    Name: PATCH on a non-existent ID returns 404
    Setup: alice has no check-in with id 99999
    Action: PATCH /checkins/99999
    Expected: 404
    Why: 500 on a missing record is an unhandled exception; 404 is the
         correct semantic and avoids leaking server internals.
    """
    resp = client.patch(
        "/api/checkins/99999", json={"mood_rating": 5}, headers=alice_headers
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. View all check-ins
# ---------------------------------------------------------------------------

def test_list_returns_all_own_checkins(client, alice_headers):
    """
    Name: GET /checkins returns all check-ins belonging to the authenticated user
    Setup: alice creates check-ins on two different dates
    Action: GET /checkins
    Expected: 200, list, both entries present
    Why: Verifies the basic read path and that the list is not capped at 1.
    """
    client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    client.post(
        "/api/checkins",
        json={**CHECKIN_A, "date": OTHER_DAY},
        headers=alice_headers,
    )

    resp = client.get("/api/checkins", headers=alice_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    dates = [c["date"] for c in resp.json()]
    assert TODAY in dates
    assert OTHER_DAY in dates


def test_list_response_includes_required_fields(client, alice_headers):
    """
    Name: Each item in GET /checkins includes all fields the frontend needs
    Setup: alice creates one check-in
    Action: GET /checkins
    Expected: first item has id, mood_rating, stress_level, sleep_hours,
              energy_level, exercised, socialized, workload_level,
              notes, created_at
    Why: If a field is missing from the list serialiser (different from the
         single-item serialiser), the frontend silently gets undefined and
         renders blank UI sections.
    """
    client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)

    resp = client.get("/api/checkins", headers=alice_headers)
    assert resp.status_code == 200
    item = resp.json()[0]
    required = {
        "id", "mood_rating", "stress_level", "sleep_hours",
        "energy_level", "exercised", "socialized", "workload_level",
        "notes", "created_at",
    }
    missing = required - set(item.keys())
    assert not missing, f"List item missing fields: {missing}"


def test_list_is_empty_for_new_user(client, alice_headers):
    """
    Name: Fresh user receives an empty list, not 404 or null
    Setup: alice has no check-ins
    Action: GET /checkins
    Expected: 200 with []
    Why: Returning 404 on an empty list is a common bug that breaks the
         frontend empty-state render.
    """
    resp = client.get("/api/checkins", headers=alice_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_ordered_newest_first(client, alice_headers):
    """
    Name: Entries are returned newest-first
    Setup: two check-ins on different dates (OTHER_DAY before TODAY)
    Action: GET /checkins
    Expected: first item is the most recent date
    Why: The frontend renders the list top-to-bottom; wrong ordering forces
         users to scroll to find their latest entry.
    """
    client.post(
        "/api/checkins",
        json={**CHECKIN_A, "date": OTHER_DAY},
        headers=alice_headers,
    )
    client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)

    resp = client.get("/api/checkins", headers=alice_headers)
    dates = [c["date"] for c in resp.json()]
    assert dates[0] == TODAY, f"Expected {TODAY} first, got {dates[0]}"


# ---------------------------------------------------------------------------
# 5. View one check-in by ID
# ---------------------------------------------------------------------------

def test_get_by_id_returns_correct_entry(client, alice_headers):
    """
    Name: GET /checkins/{id} returns the specific check-in
    Setup: alice creates a check-in
    Action: GET /checkins/{id} using the id from the create response
    Expected: 200 with matching id and field values
    Why: If the repository query omits the user_id filter for single-item
         fetches, any ID would return any user's record.
    """
    create = client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    entry_id = create.json()["id"]

    resp = client.get(f"/api/checkins/{entry_id}", headers=alice_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == entry_id
    assert body["mood_rating"] == CHECKIN_A["mood_rating"]
    assert body["sleep_hours"] == CHECKIN_A["sleep_hours"]


def test_get_nonexistent_id_returns_404(client, alice_headers):
    """
    Name: GET /checkins/99999 returns 404, not 500
    Setup: alice has no check-in with id 99999
    Action: GET /checkins/99999
    Expected: 404
    Why: Unhandled SQLAlchemy None raises an AttributeError and produces a
         500 if the route doesn't guard against a missing record.
    """
    resp = client.get("/api/checkins/99999", headers=alice_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 6. User isolation — viewing
# ---------------------------------------------------------------------------

def test_user_cannot_view_other_users_checkin(client, alice_headers, bob, bob_headers):
    """
    Name: Bob cannot read Alice's check-in by ID
    Setup: alice creates a check-in; bob knows the id
    Action: GET /checkins/{alice_id} with Bob's token
    Expected: 404 (query is user-scoped, so the row is simply not found)
    Why: Health data must be strictly isolated. 404 rather than 403 is
         privacy-preserving: it doesn't confirm the record exists.
    """
    create = client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    entry_id = create.json()["id"]

    resp = client.get(f"/api/checkins/{entry_id}", headers=bob_headers)
    assert resp.status_code == 404


def test_list_excludes_other_users_checkins(client, alice_headers, bob, bob_headers):
    """
    Name: Bob's check-in list never contains Alice's entries
    Setup: alice and bob each create one check-in (same date, different users)
    Action: GET /checkins with Bob's token
    Expected: list contains only Bob's entry
    Why: A missing WHERE user_id = ? on the list query would leak every
         user's data to every other user.
    """
    client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    client.post(
        "/api/checkins",
        json={**CHECKIN_A, "date": OTHER_DAY},   # different date so Bob's create doesn't 409
        headers=bob_headers,
    )

    resp = client.get("/api/checkins", headers=bob_headers)
    assert resp.status_code == 200
    for entry in resp.json():
        assert entry["date"] != TODAY, (
            "Bob's list contains Alice's entry — user_id filter is missing"
        )


# ---------------------------------------------------------------------------
# 7. User isolation — editing
# ---------------------------------------------------------------------------

def test_user_cannot_patch_other_users_checkin(client, alice_headers, bob, bob_headers):
    """
    Name: Bob cannot update Alice's check-in
    Setup: alice creates a check-in
    Action: PATCH /checkins/{alice_id} with Bob's token
    Expected: 404 (user-scoped query makes the record invisible to Bob)
    Why: Without this guard, any authenticated user could overwrite another
         user's mood data — a severe integrity and privacy violation.
    """
    create = client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    entry_id = create.json()["id"]

    resp = client.patch(
        f"/api/checkins/{entry_id}",
        json={"mood_rating": 1},
        headers=bob_headers,
    )
    assert resp.status_code == 404


def test_failed_cross_user_patch_leaves_original_unchanged(
    client, alice_headers, bob, bob_headers
):
    """
    Name: After Bob's rejected PATCH, Alice's values are unchanged
    Setup: alice creates a check-in; bob attempts to overwrite mood to 1
    Action: fetch Alice's check-in with Alice's token after Bob's attempt
    Expected: mood_rating still equals the original value
    Why: Confirms that the 404 response genuinely blocked the write and
         wasn't just a response error masking a committed update.
    """
    create = client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    entry_id = create.json()["id"]
    original_mood = CHECKIN_A["mood_rating"]

    client.patch(
        f"/api/checkins/{entry_id}",
        json={"mood_rating": 1},
        headers=bob_headers,
    )

    resp = client.get(f"/api/checkins/{entry_id}", headers=alice_headers)
    assert resp.status_code == 200
    assert resp.json()["mood_rating"] == original_mood, (
        "Alice's mood_rating was changed by Bob's request"
    )


# ---------------------------------------------------------------------------
# 8. Unauthenticated access
# ---------------------------------------------------------------------------

def test_list_requires_auth(client):
    """GET /checkins without a token → 401"""
    assert client.get("/api/checkins").status_code == 401


def test_create_requires_auth(client):
    """POST /checkins without a token → 401"""
    assert client.post("/api/checkins", json=CHECKIN_A).status_code == 401


def test_patch_requires_auth(client, alice, alice_headers):
    """PATCH /checkins/{id} without a token → 401"""
    create = client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    entry_id = create.json()["id"]
    assert client.patch(f"/api/checkins/{entry_id}", json={"mood_rating": 5}).status_code == 401


def test_get_by_id_requires_auth(client, alice, alice_headers):
    """GET /checkins/{id} without a token → 401"""
    create = client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    entry_id = create.json()["id"]
    assert client.get(f"/api/checkins/{entry_id}").status_code == 401


# ---------------------------------------------------------------------------
# GET /checkins/today — timezone-safe date lookup
# ---------------------------------------------------------------------------

def test_today_endpoint_returns_checkin_for_supplied_date(client, alice_headers):
    """
    Name: GET /checkins/today?date=YYYY-MM-DD finds the check-in for that date
    Setup: alice creates a check-in for TODAY
    Action: GET /checkins/today?date=TODAY
    Expected: 200 with the correct entry
    Why: The /today endpoint accepts the client's local date to avoid timezone
         mismatches between the browser (local TZ) and the server (UTC). This
         test verifies the query uses the supplied date, not the server clock.
    """
    create = client.post("/api/checkins", json=CHECKIN_A, headers=alice_headers)
    entry_id = create.json()["id"]

    resp = client.get(f"/api/checkins/today?date={TODAY}", headers=alice_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == entry_id


def test_today_endpoint_returns_404_when_no_checkin_for_date(client, alice_headers):
    """
    Name: GET /checkins/today?date=X returns 404 when no entry exists for that date
    Setup: alice has no check-in for TODAY
    Action: GET /checkins/today?date=TODAY
    Expected: 404
    Why: Clients use 404 to decide whether to show the "create" or "edit" form.
         A wrong status would lock users into the wrong mode.
    """
    resp = client.get(f"/api/checkins/today?date={TODAY}", headers=alice_headers)
    assert resp.status_code == 404


def test_today_endpoint_requires_auth(client):
    """GET /checkins/today without a token → 401"""
    assert client.get(f"/api/checkins/today?date={TODAY}").status_code == 401
