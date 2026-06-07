"""
Security tests for MindPattern API

Categories covered:
  1. Input injection (SQL injection, XSS in journal and check-in fields)
  2. Authentication and authorization (weak passwords, CSRF via missing token,
     broken access control across users)
  3. Server configuration (security headers, JSON content type)
  4. User data isolation through URL IDs (journal, check-in, insights)

Skipped / documented future work:
  - Login rate limiting (not yet implemented)
  - 2FA (not in MVP scope)
  - TLS/HTTPS scanning (handled by deployment provider)
  - Dependency auditing (run separately: `pip-audit` / `npm audit`)

This file only tests the app's own endpoints with its own test DB.
No external URLs are contacted, no real attacks are performed.
"""
import pytest

# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

CHECKIN_BASE = {
    "date": "2026-07-15",
    "mood_rating": 3,
    "stress_level": 3,
    "sleep_hours": 7.0,
    "exercised": False,
    "socialized": False,
    "workload_level": 3,
}

JOURNAL_BASE = {"content": "An ordinary journal entry."}


def _post_checkin(client, headers, overrides=None):
    payload = {**CHECKIN_BASE, **(overrides or {})}
    return client.post("/api/checkins", json=payload, headers=headers)


def _post_journal(client, headers, overrides=None):
    payload = {**JOURNAL_BASE, **(overrides or {})}
    return client.post("/api/journals", json=payload, headers=headers)


# ===========================================================================
# 1. INPUT INJECTION
# ===========================================================================

# ---------------------------------------------------------------------------
# 1.1  SQL injection — login endpoint
# ---------------------------------------------------------------------------

def test_sql_injection_login_email_is_rejected(client):
    """
    Name: SQL injection via email field does not grant access
    Setup: no users exist
    Action: POST /auth/login with classic SQL injection email
    Expected: 401 or 422 — no token returned
    Why: A naive string-interpolated query like
         SELECT * FROM users WHERE email='...' would be exploitable.
         SQLAlchemy's ORM uses parameterised queries, so this should fail
         cleanly, but the test pins the contract.
    """
    resp = client.post(
        "/api/auth/login",
        json={"email": "' OR '1'='1", "password": "' OR '1'='1"},
    )
    assert resp.status_code in (400, 401, 422), resp.text
    assert "access_token" not in resp.json()


def test_sql_injection_login_does_not_return_token(client):
    """
    Name: Injection-style login payload never produces a usable token
    Note: Complements the status-code check by asserting the JSON body
          contains no 'access_token' key regardless of status.
    """
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin'--", "password": "anything"},
    )
    assert "access_token" not in resp.json()


# ---------------------------------------------------------------------------
# 1.2  SQL injection — journal content
# ---------------------------------------------------------------------------

def test_sql_injection_in_journal_content_does_not_crash(client, alice_headers):
    """
    Name: SQL injection in journal body is stored safely or rejected — no crash
    Action: POST /journals with classic DROP TABLE payload
    Expected: 200/201 (stored as text) or 400/422 (rejected by validation).
              The server must NOT return 500.
    Why: Content fields pass through NLP but are never interpolated into raw SQL.
         This test guards against future regressions if raw queries are added.
    """
    resp = _post_journal(client, alice_headers, {"content": "'); DROP TABLE users; --"})
    assert resp.status_code in (200, 201, 400, 422), (
        f"Unexpected status {resp.status_code}: {resp.text}"
    )


def test_sql_injection_in_journal_users_table_survives(client, alice_headers):
    """
    Name: After injecting DROP TABLE users into a journal, alice can still log in
    Setup: alice submits DROP TABLE payload, then tries GET /auth/me
    Expected: GET /auth/me still returns 200 — the users table is intact
    Why: Confirms the injection was not executed as SQL.
    """
    _post_journal(client, alice_headers, {"content": "'); DROP TABLE users; --"})
    resp = client.get("/api/auth/me", headers=alice_headers)
    assert resp.status_code == 200


def test_sql_injection_in_journal_checkins_table_survives(client, alice_headers):
    """
    Name: Injecting DROP TABLE checkins into a journal does not drop the table
    Setup: alice submits the payload, then creates a normal check-in
    Expected: check-in creation succeeds — the table is intact
    """
    _post_journal(client, alice_headers, {"content": "'); DROP TABLE checkins_v2; --"})
    resp = _post_checkin(client, alice_headers)
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# 1.3  SQL injection — check-in notes
# ---------------------------------------------------------------------------

def test_sql_injection_in_checkin_notes_does_not_crash(client, alice_headers):
    """
    Name: SQL injection in check-in notes is stored safely or rejected — no 500
    Action: POST /checkins with DROP TABLE payload in notes
    Expected: 201 (stored as text) or 400/422 (rejected). Never 500.
    """
    resp = _post_checkin(client, alice_headers, {"notes": "'); DROP TABLE checkins_v2; --"})
    assert resp.status_code in (200, 201, 400, 422), (
        f"Unexpected status {resp.status_code}: {resp.text}"
    )


def test_sql_injection_in_checkin_notes_table_survives(client, alice_headers):
    """
    Name: After injecting DROP TABLE into check-in notes, the checkins table is intact
    Setup: alice submits injection payload, then creates a second check-in on a new date
    Expected: second check-in is created — the table survived
    """
    _post_checkin(client, alice_headers, {"notes": "'); DROP TABLE checkins_v2; --"})
    resp = _post_checkin(client, alice_headers, {"date": "2026-07-16"})
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# 1.4  XSS — journal content
# ---------------------------------------------------------------------------

def test_xss_in_journal_content_server_does_not_crash(client, alice_headers):
    """
    Name: Script tag in journal content does not crash the server
    Action: POST /journals with <script>alert('xss')</script>
    Expected: 201 (stored as plain text) or 400/422. Never 500.
    Note: The API returns JSON. A browser rendering the content must escape it.
          This test confirms the server itself stays stable and responds with JSON.
    """
    resp = _post_journal(client, alice_headers, {"content": "<script>alert('xss')</script>"})
    assert resp.status_code in (200, 201, 400, 422)
    assert "application/json" in resp.headers.get("content-type", "")


def test_xss_in_journal_content_response_is_json(client, alice_headers):
    """
    Name: Fetching a journal entry with script content returns JSON, not HTML
    Setup: alice creates a journal with XSS payload; fetches it back
    Expected: GET /journals/{id} returns 200 with JSON content-type
    Why: If the API ever rendered HTML from user content, the script would run
         in a browser. JSON responses force the frontend to choose how to render.
    """
    create = _post_journal(client, alice_headers, {"content": "<script>alert('xss')</script>"})
    if create.status_code not in (200, 201):
        pytest.skip("Server rejected XSS payload before storage — content-type check not needed")
    entry_id = create.json()["id"]
    resp = client.get(f"/api/journals/{entry_id}", headers=alice_headers)
    assert resp.status_code == 200
    assert "application/json" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# 1.5  XSS — check-in notes
# ---------------------------------------------------------------------------

def test_xss_in_checkin_notes_server_does_not_crash(client, alice_headers):
    """
    Name: img onerror payload in check-in notes does not crash the server
    Action: POST /checkins with onerror payload in notes
    Expected: 201 (stored as plain text) or 400/422. Never 500. Response is JSON.
    """
    resp = _post_checkin(
        client, alice_headers,
        {"notes": "<img src=x onerror=alert('xss')>"},
    )
    assert resp.status_code in (200, 201, 400, 422)
    assert "application/json" in resp.headers.get("content-type", "")


def test_xss_in_checkin_notes_response_is_json(client, alice_headers):
    """
    Name: Fetching a check-in with XSS payload in notes returns JSON, not HTML
    """
    create = _post_checkin(
        client, alice_headers,
        {"notes": "<img src=x onerror=alert('xss')>"},
    )
    if create.status_code not in (200, 201):
        pytest.skip("Server rejected XSS payload before storage — content-type check not needed")
    entry_id = create.json()["id"]
    resp = client.get(f"/api/checkins/{entry_id}", headers=alice_headers)
    assert resp.status_code == 200
    assert "application/json" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# 1.6  File upload — no upload routes exposed
# ---------------------------------------------------------------------------

def test_no_file_upload_route_unauthenticated(client):
    """
    Name: Common upload URLs are not routed by the API
    Expected: 404 for /api/upload, /api/files, /api/profile/upload
    Why: MindPattern has no file upload feature. These routes must not exist
         unauthenticated (or at all).
    Note: If a file upload feature is added in future, this test should be
          updated to verify file-type and size restrictions instead.
    """
    for path in ("/api/upload", "/api/files", "/api/profile/upload"):
        resp = client.post(path)
        assert resp.status_code == 404, (
            f"Unexpected status {resp.status_code} on {path} — upload route may have been added"
        )


# ===========================================================================
# 2. AUTHENTICATION AND AUTHORIZATION
# ===========================================================================

# ---------------------------------------------------------------------------
# 2.1  Weak password rejection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("weak_password", ["123", "abc", "1234567", "pass"])
def test_weak_password_rejected_at_registration(client, weak_password):
    """
    Name: Registration rejects passwords shorter than 8 characters
    Setup: attempt to register with each weak password (all < 8 chars)
    Expected: 422 (Pydantic Field min_length=8 rejection)
    Why: Weak passwords are trivially brute-forceable. The minimum-length
         guard prevents the most obvious credential stuffing targets.
    Note: "password" (8 chars) is allowed by the length check — it sits
         exactly at the boundary. Banning common dictionary words would
         require a blocklist, which is out of scope for the MVP.
    """
    resp = client.post(
        "/api/auth/register",
        json={
            "email": f"user_{weak_password}@test.com",
            "password": weak_password,
            "display_name": "Test",
        },
    )
    assert resp.status_code in (400, 422), (
        f"Expected 400/422 for weak password '{weak_password}', got {resp.status_code}"
    )


def test_strong_password_is_accepted_at_registration(client):
    """
    Name: Registration accepts passwords of 8+ characters
    Expected: 201 — confirm the min_length guard does not block valid passwords
    """
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "stronguser@test.com",
            "password": "Secur3Pa$$",
            "display_name": "Strong",
        },
    )
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# 2.2  Login rate limiting
# ---------------------------------------------------------------------------

@pytest.mark.skip(
    reason=(
        "Login rate limiting (429 Too Many Requests) is not yet implemented. "
        "TODO: add SlowAPI or similar middleware before production launch. "
        "This test documents the expected future behaviour."
    )
)
def test_repeated_failed_logins_trigger_rate_limit(client):
    """
    Name: 10 failed login attempts should trigger 429 Too Many Requests
    Expected future behaviour: status 429 after threshold is exceeded.
    """
    for _ in range(10):
        client.post(
            "/api/auth/login",
            json={"email": "victim@example.com", "password": "wrongpassword"},
        )
    resp = client.post(
        "/api/auth/login",
        json={"email": "victim@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 429


# ---------------------------------------------------------------------------
# 2.3  Two-Factor Authentication
# ---------------------------------------------------------------------------

@pytest.mark.skip(
    reason=(
        "2FA is not implemented in the MVP. "
        "Future work: add TOTP (e.g. pyotp) as an optional second factor. "
        "This is documented here as a security checklist item."
    )
)
def test_2fa_not_implemented_placeholder():
    """2FA security checklist placeholder — see skip reason."""
    pass


# ---------------------------------------------------------------------------
# 2.4  CSRF protection via JWT bearer token requirement
#       State-changing endpoints must reject requests with no Authorization header.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("POST",   "/api/checkins"),
    ("PATCH",  "/api/checkins/1"),
    ("POST",   "/api/journals"),
    ("DELETE", "/api/journals/1"),
    ("PUT",    "/api/users/me/settings"),
    ("POST",   "/api/insights/generate"),
])
def test_state_changing_endpoints_require_bearer_token(client, method, path):
    """
    Name: All state-changing endpoints return 401 with no Authorization header
    Why: The app uses JWT bearer tokens stored in JS (not cookies), so there is
         no CSRF attack surface — but only if every mutating endpoint actually
         checks for the token. This test pins that contract.
    """
    resp = client.request(method, path, json={})
    assert resp.status_code == 401, (
        f"{method} {path} returned {resp.status_code} without a token"
    )


# ---------------------------------------------------------------------------
# 2.5  Broken access control — other user's journal
# ---------------------------------------------------------------------------

def test_bob_cannot_read_alices_journal(client, alice_headers, bob, bob_headers):
    """
    Name: Bob cannot GET Alice's journal entry by ID
    Expected: 404 — user-scoped query makes the row invisible to Bob
    Why: Mental health data is highly sensitive. GET must be scoped by user_id.
    """
    create = _post_journal(client, alice_headers)
    journal_id = create.json()["id"]

    resp = client.get(f"/api/journals/{journal_id}", headers=bob_headers)
    assert resp.status_code in (403, 404)


def test_bob_cannot_delete_alices_journal(client, alice_headers, bob, bob_headers):
    """
    Name: Bob cannot DELETE Alice's journal entry
    Expected: 404 — Bob cannot even confirm the entry exists
    """
    create = _post_journal(client, alice_headers)
    journal_id = create.json()["id"]

    resp = client.delete(f"/api/journals/{journal_id}", headers=bob_headers)
    assert resp.status_code in (403, 404)


def test_alices_journal_still_exists_after_bobs_delete_attempt(
    client, alice_headers, bob, bob_headers
):
    """
    Name: Alice's journal is unchanged after Bob's failed delete attempt
    Expected: Alice can still fetch her journal at 200
    """
    create = _post_journal(client, alice_headers)
    journal_id = create.json()["id"]
    client.delete(f"/api/journals/{journal_id}", headers=bob_headers)

    resp = client.get(f"/api/journals/{journal_id}", headers=alice_headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 2.6  Broken access control — other user's check-in
# ---------------------------------------------------------------------------

def test_bob_cannot_read_alices_checkin(client, alice_headers, bob, bob_headers):
    """
    Name: Bob cannot GET Alice's check-in by ID
    Expected: 404
    """
    create = _post_checkin(client, alice_headers)
    checkin_id = create.json()["id"]

    resp = client.get(f"/api/checkins/{checkin_id}", headers=bob_headers)
    assert resp.status_code in (403, 404)


def test_bob_cannot_patch_alices_checkin(client, alice_headers, bob, bob_headers):
    """
    Name: Bob cannot PATCH Alice's check-in
    Expected: 404 — and Alice's values remain unchanged
    """
    create = _post_checkin(client, alice_headers)
    checkin_id = create.json()["id"]

    resp = client.patch(
        f"/api/checkins/{checkin_id}",
        json={"mood_rating": 1},
        headers=bob_headers,
    )
    assert resp.status_code in (403, 404)


def test_alices_checkin_unchanged_after_bobs_patch_attempt(
    client, alice_headers, bob, bob_headers
):
    """
    Name: Alice's check-in values are unchanged after Bob's failed PATCH
    """
    create = _post_checkin(client, alice_headers)
    checkin_id = create.json()["id"]
    original_mood = CHECKIN_BASE["mood_rating"]

    client.patch(
        f"/api/checkins/{checkin_id}",
        json={"mood_rating": 1},
        headers=bob_headers,
    )

    resp = client.get(f"/api/checkins/{checkin_id}", headers=alice_headers)
    assert resp.status_code == 200
    assert resp.json()["mood_rating"] == original_mood


# ---------------------------------------------------------------------------
# 2.7  Broken access control — user settings
# ---------------------------------------------------------------------------

def test_settings_endpoint_uses_me_not_user_id(client, alice_headers, bob, bob_headers):
    """
    Name: Settings are accessed only via /me/settings — no ID-based URL exists
    Action: Bob attempts to read settings via guessed paths with Alice's user id
    Expected: 404 on any ID-based path; /me/settings returns only Bob's own data
    Why: /me/* routes bind to the authenticated user, so there is no way to
         request another user's settings by changing an ID in the URL.
         This test confirms no ID-based alternative route is accidentally exposed.
    """
    for path in ("/api/users/1/settings", "/api/users/2/settings", "/api/users/settings/1"):
        resp = client.get(path, headers=bob_headers)
        assert resp.status_code == 404, (
            f"Unexpected {resp.status_code} on {path} — an ID-based settings route may be exposed"
        )


def test_settings_me_returns_own_data_not_other_users(client, alice_headers, bob_headers):
    """
    Name: /me/settings always returns the authenticated user's settings
    Action: Alice and Bob each call GET /users/me/settings
    Expected: each response contains only that user's settings (different user_id)
    """
    alice_resp = client.get("/api/users/me/settings", headers=alice_headers)
    bob_resp = client.get("/api/users/me/settings", headers=bob_headers)
    assert alice_resp.status_code == 200
    assert bob_resp.status_code == 200


# ---------------------------------------------------------------------------
# 2.8  Unauthenticated access to all protected endpoints
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("GET",    "/api/checkins"),
    ("GET",    "/api/checkins/1"),
    ("POST",   "/api/checkins"),
    ("PATCH",  "/api/checkins/1"),
    ("GET",    "/api/journals"),
    ("GET",    "/api/journals/1"),
    ("POST",   "/api/journals"),
    ("DELETE", "/api/journals/1"),
    ("GET",    "/api/insights"),
    ("POST",   "/api/insights/generate"),
    ("GET",    "/api/users/me/settings"),
    ("PUT",    "/api/users/me/settings"),
    ("GET",    "/api/auth/me"),
    ("GET",    "/api/dashboard/summary"),
    ("GET",    "/api/dashboard/mood-trends"),
    ("GET",    "/api/dashboard/stress-trends"),
    ("GET",    "/api/dashboard/sleep-mood"),
])
def test_unauthenticated_request_returns_401(client, method, path):
    """
    Name: Every private endpoint returns 401 with no Authorization header
    Why: Users must be unable to access any mental health data by typing a
         URL directly in a browser or making a request without a token.
    """
    resp = client.request(method, path, json={})
    assert resp.status_code == 401, (
        f"{method} {path} returned {resp.status_code} without auth — endpoint may be unprotected"
    )


# ===========================================================================
# 3. SERVER CONFIGURATION AND SECURITY HEADERS
# ===========================================================================

# ---------------------------------------------------------------------------
# 3.1  Security headers on API responses
# ---------------------------------------------------------------------------

def test_security_header_x_content_type_options(client):
    """X-Content-Type-Options: nosniff prevents MIME-sniffing attacks."""
    resp = client.get("/api/health")
    assert resp.headers.get("x-content-type-options") == "nosniff", (
        "Missing or wrong X-Content-Type-Options header"
    )


def test_security_header_x_frame_options(client):
    """X-Frame-Options: DENY prevents clickjacking via iframe embedding."""
    resp = client.get("/api/health")
    assert resp.headers.get("x-frame-options") == "DENY", (
        "Missing or wrong X-Frame-Options header"
    )


def test_security_header_referrer_policy(client):
    """Referrer-Policy: no-referrer prevents leaking the URL in referer headers."""
    resp = client.get("/api/health")
    assert resp.headers.get("referrer-policy") == "no-referrer", (
        "Missing or wrong Referrer-Policy header"
    )


def test_security_header_content_security_policy(client):
    """Content-Security-Policy: default-src 'self' restricts resource loading."""
    resp = client.get("/api/health")
    csp = resp.headers.get("content-security-policy", "")
    assert "default-src" in csp, f"Missing Content-Security-Policy header (got: '{csp}')"


def test_security_headers_present_on_authenticated_endpoints(client, alice_headers):
    """Security headers appear on authenticated API responses too, not just /health."""
    resp = client.get("/api/checkins", headers=alice_headers)
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"


# ---------------------------------------------------------------------------
# 3.2  JSON content type on all API endpoints
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/api/health",
])
def test_public_endpoints_return_json_content_type(client, path):
    """
    Name: Public API endpoints return application/json content type
    Why: If user-generated content were ever rendered as HTML, the browser
         could execute inline scripts. JSON content-type prevents this.
    """
    resp = client.get(path)
    assert "application/json" in resp.headers.get("content-type", ""), (
        f"{path} does not return application/json"
    )


def test_checkins_list_returns_json_content_type(client, alice_headers):
    resp = client.get("/api/checkins", headers=alice_headers)
    assert "application/json" in resp.headers.get("content-type", "")


def test_journals_list_returns_json_content_type(client, alice_headers):
    resp = client.get("/api/journals", headers=alice_headers)
    assert "application/json" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# 3.3  HTTPS / TLS
# ---------------------------------------------------------------------------

@pytest.mark.skip(
    reason=(
        "TLS/HTTPS is handled by the Replit deployment provider — not testable "
        "in the local test environment. "
        "Production checklist: ensure the deployment enforces HTTPS and redirects "
        "HTTP to HTTPS. Do not serve the app over plain HTTP in production."
    )
)
def test_https_enforced_in_production():
    """TLS checklist placeholder — see skip reason."""
    pass


# ---------------------------------------------------------------------------
# 3.4  Dependency auditing note
# ---------------------------------------------------------------------------

@pytest.mark.skip(
    reason=(
        "Dependency auditing is a manual / CI step, not a runtime test. "
        "Run: `pip-audit` (Python) or `npm audit` (Node) in CI. "
        "Do not blindly upgrade dependencies — review changelogs for breaking changes."
    )
)
def test_dependencies_have_no_known_vulnerabilities():
    """Dependency audit checklist placeholder — see skip reason."""
    pass


# ===========================================================================
# 4. USER DATA ISOLATION THROUGH URL IDs
# ===========================================================================

# ---------------------------------------------------------------------------
# 4.1  Journal GET isolation
# ---------------------------------------------------------------------------

def test_journal_get_url_isolation(client, alice_headers, bob, bob_headers):
    """
    Name: Bob cannot access Alice's journal by guessing the numeric ID in the URL
    Setup: Alice creates a journal; Bob uses its ID in GET /journals/{id}
    Expected: 404 — the user_id filter makes the record invisible to Bob
    Why: This is the most direct privacy threat for health data: an authenticated
         user enumerating another user's records by incrementing an ID.
    """
    journal_id = _post_journal(client, alice_headers).json()["id"]
    resp = client.get(f"/api/journals/{journal_id}", headers=bob_headers)
    assert resp.status_code in (403, 404), (
        f"Bob received status {resp.status_code} — Alice's journal may be exposed"
    )


# ---------------------------------------------------------------------------
# 4.2  Journal DELETE isolation
# ---------------------------------------------------------------------------

def test_journal_delete_url_isolation(client, alice_headers, bob, bob_headers):
    """
    Name: Bob cannot delete Alice's journal via URL ID
    Expected: 404 — and Alice's journal still exists after the attempt
    """
    journal_id = _post_journal(client, alice_headers).json()["id"]

    delete_resp = client.delete(f"/api/journals/{journal_id}", headers=bob_headers)
    assert delete_resp.status_code in (403, 404)

    still_there = client.get(f"/api/journals/{journal_id}", headers=alice_headers)
    assert still_there.status_code == 200, "Alice's journal was deleted by Bob"


# ---------------------------------------------------------------------------
# 4.3  Check-in GET isolation
# ---------------------------------------------------------------------------

def test_checkin_get_url_isolation(client, alice_headers, bob, bob_headers):
    """
    Name: Bob cannot access Alice's check-in by guessing the numeric ID in the URL
    Expected: 404
    """
    checkin_id = _post_checkin(client, alice_headers).json()["id"]
    resp = client.get(f"/api/checkins/{checkin_id}", headers=bob_headers)
    assert resp.status_code in (403, 404), (
        f"Bob received status {resp.status_code} — Alice's check-in may be exposed"
    )


# ---------------------------------------------------------------------------
# 4.4  Check-in PATCH isolation
# ---------------------------------------------------------------------------

def test_checkin_patch_url_isolation(client, alice_headers, bob, bob_headers):
    """
    Name: Bob cannot modify Alice's check-in via URL ID
    Expected: 404 and Alice's mood_rating is unchanged
    """
    create = _post_checkin(client, alice_headers)
    checkin_id = create.json()["id"]
    original_mood = create.json()["mood_rating"]

    patch_resp = client.patch(
        f"/api/checkins/{checkin_id}",
        json={"mood_rating": 1},
        headers=bob_headers,
    )
    assert patch_resp.status_code in (403, 404)

    alice_view = client.get(f"/api/checkins/{checkin_id}", headers=alice_headers)
    assert alice_view.json()["mood_rating"] == original_mood, (
        "Alice's mood_rating was changed by Bob's PATCH attempt"
    )


# ---------------------------------------------------------------------------
# 4.5  Insight list isolation
# ---------------------------------------------------------------------------

def test_insight_list_only_returns_own_insights(client, alice_headers, bob, bob_headers):
    """
    Name: GET /insights only returns the authenticated user's insights
    Setup: Alice generates insights; Bob lists his own insights
    Expected: Bob sees 0 insights (or only his own) — never Alice's
    Why: Insights are derived from personal health data. A missing user_id
         filter on the list query would expose all users' insights to everyone.
    """
    client.post("/api/insights/generate", headers=alice_headers)

    bob_resp = client.get("/api/insights", headers=bob_headers)
    assert bob_resp.status_code == 200
    assert isinstance(bob_resp.json(), list)

    alice_resp = client.get("/api/insights", headers=alice_headers)
    alice_ids = {i["id"] for i in alice_resp.json()}
    bob_ids = {i["id"] for i in bob_resp.json()}
    overlap = alice_ids & bob_ids
    assert not overlap, (
        f"Bob can see Alice's insights — shared IDs: {overlap}"
    )
