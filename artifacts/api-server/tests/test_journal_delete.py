"""
Tests: Deleting a journal entry
DELETE /api/journals/{id}

Categories covered:
  - Happy path
  - Bad input
  - Edge cases
  - Privacy/security
  - AI safety wording (audit trail preservation)
"""
from app.models.safety_event import SafetyEvent


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_delete_own_entry_returns_204(client, alice_headers):
    """
    Name: Deleting your own entry returns 204 No Content
    Setup: alice creates an entry
    Action: DELETE /journals/{id}
    Expected: 204
    Why: 204 is the correct HTTP status for a successful delete with no
         response body; returning 200 with a body or 200 with null would be
         non-standard.
    """
    create = client.post(
        "/api/journals", json={"content": "I will delete this."}, headers=alice_headers
    )
    entry_id = create.json()["id"]

    resp = client.delete(f"/api/journals/{entry_id}", headers=alice_headers)
    assert resp.status_code == 204


def test_deleted_entry_is_no_longer_retrievable(client, alice_headers):
    """
    Name: Entry is gone after deletion
    Setup: alice creates and then deletes an entry
    Action: GET /journals/{id} after the DELETE
    Expected: 404
    Why: A soft-delete bug or missing commit could leave the record visible;
         this test catches that.
    """
    create = client.post(
        "/api/journals", json={"content": "Goodbye."}, headers=alice_headers
    )
    entry_id = create.json()["id"]

    client.delete(f"/api/journals/{entry_id}", headers=alice_headers)

    resp = client.get(f"/api/journals/{entry_id}", headers=alice_headers)
    assert resp.status_code == 404


def test_deleted_entry_removed_from_list(client, alice_headers):
    """
    Name: Deleted entry no longer appears in the journal list
    Setup: alice creates two entries then deletes one
    Action: GET /journals after the DELETE
    Expected: list contains only the surviving entry
    Why: Without checking the list, a DELETE that works on single GET but
         not on the list query (different filter path) would go undetected.
    """
    client.post("/api/journals", json={"content": "Keep this."}, headers=alice_headers)
    to_delete = client.post(
        "/api/journals", json={"content": "Delete this."}, headers=alice_headers
    )
    entry_id = to_delete.json()["id"]

    client.delete(f"/api/journals/{entry_id}", headers=alice_headers)

    resp = client.get("/api/journals", headers=alice_headers)
    contents = [e["content"] for e in resp.json()]
    assert "Delete this." not in contents
    assert "Keep this." in contents


# ---------------------------------------------------------------------------
# Bad input
# ---------------------------------------------------------------------------

def test_delete_nonexistent_entry_returns_404(client, alice_headers):
    """
    Name: Deleting a non-existent ID returns 404
    Setup: alice has no entries
    Action: DELETE /journals/99999
    Expected: 404
    Why: Returning 204 for a non-existent record falsely signals success
         and can mask logic errors in the client.
    """
    resp = client.delete("/api/journals/99999", headers=alice_headers)
    assert resp.status_code == 404


def test_delete_requires_auth(client, alice, alice_headers):
    """
    Name: Unauthenticated delete is rejected
    Setup: alice creates an entry; no token is sent
    Action: DELETE /journals/{id} without Authorization header
    Expected: 401
    Why: A missing auth check on delete is a dangerous vulnerability —
         any visitor could wipe another user's journal.
    """
    create = client.post(
        "/api/journals", json={"content": "Should not be deletable."}, headers=alice_headers
    )
    entry_id = create.json()["id"]

    resp = client.delete(f"/api/journals/{entry_id}")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_double_delete_returns_404(client, alice_headers):
    """
    Name: Second DELETE on the same entry returns 404
    Setup: alice creates and deletes an entry
    Action: DELETE the same ID again
    Expected: 404 (idempotent-safe: no 500)
    Why: Clients with retry logic will re-send requests; a 500 on the second
         delete would look like a server crash rather than a normal not-found.
    """
    create = client.post(
        "/api/journals", json={"content": "Once only."}, headers=alice_headers
    )
    entry_id = create.json()["id"]

    client.delete(f"/api/journals/{entry_id}", headers=alice_headers)
    resp = client.delete(f"/api/journals/{entry_id}", headers=alice_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Privacy/security
# ---------------------------------------------------------------------------

def test_user_cannot_delete_other_users_entry(client, alice_headers, bob_headers):
    """
    Name: Bob cannot delete Alice's entry
    Setup: alice creates an entry
    Action: DELETE /journals/{alice_entry_id} with bob's token
    Expected: 404 (not 403 — the query is user-scoped, so the row is
              invisible to bob)
    Why: 403 would acknowledge the entry exists; 404 is privacy-preserving.
         This test ensures the delete filter includes user_id.
    """
    create = client.post(
        "/api/journals",
        json={"content": "Alice's private entry."},
        headers=alice_headers,
    )
    entry_id = create.json()["id"]

    resp = client.delete(f"/api/journals/{entry_id}", headers=bob_headers)
    assert resp.status_code == 404

    # alice's entry must still exist
    still_there = client.get(f"/api/journals/{entry_id}", headers=alice_headers)
    assert still_there.status_code == 200


# ---------------------------------------------------------------------------
# AI safety wording — audit trail preservation
# ---------------------------------------------------------------------------

def test_safety_event_persists_after_journal_deletion(
    client, db_session, alice, alice_headers
):
    """
    Name: Deleting a crisis-flagged entry does NOT delete the safety audit record
    Setup: alice writes an entry that triggers the crisis flag; entry is deleted
    Action: query SafetyEvent table after the delete
    Expected: SafetyEvent row still exists for alice referencing the deleted entry
    Why: Safety events are an audit trail, not a cache of the entry. If they
         were deleted along with the entry, there would be no record that a
         crisis signal was ever received — undermining any future clinical
         review or safeguarding process.
    """
    create = client.post(
        "/api/journals",
        json={"content": "I've been thinking about suicide."},
        headers=alice_headers,
    )
    entry_id = create.json()["id"]
    assert create.json()["safety_flagged"] is True

    client.delete(f"/api/journals/{entry_id}", headers=alice_headers)

    # The journal entry is gone...
    assert client.get(f"/api/journals/{entry_id}", headers=alice_headers).status_code == 404

    # ...but the safety event must still be there.
    event = (
        db_session.query(SafetyEvent)
        .filter(SafetyEvent.user_id == alice.id, SafetyEvent.source_id == entry_id)
        .first()
    )
    assert event is not None, "SafetyEvent must not be deleted with the journal entry"
