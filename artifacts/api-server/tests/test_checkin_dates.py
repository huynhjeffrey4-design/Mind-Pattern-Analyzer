"""
Tests: Date correctness through the full check-in and dashboard pipeline

Problem: JavaScript's `new Date("2026-06-06")` parses date-only strings as
UTC midnight. Users not in UTC see the wrong calendar day on chart labels.

These tests verify the backend side of the contract:
  - The date stored in the DB is exactly the date the client sent.
  - The trend APIs (`/dashboard/mood-trends`, `/dashboard/stress-trends`)
    return that exact date string unchanged.
  - The sleep-mood API returns the correct date.
  - Dates are always YYYY-MM-DD strings, never datetime objects.
  - Check-ins on consecutive dates produce correctly-ordered trend points.

The frontend fix (parseISO instead of new Date) is covered separately by
the e2e suite; these tests guard the backend contract that the frontend
relies on.
"""

DATE_A = "2026-05-30"
DATE_B = "2026-05-31"
DATE_C = "2026-06-01"


def _create(client, headers, date, mood=3, stress=4, sleep=7.0):
    return client.post(
        "/api/checkins",
        json={
            "date": date,
            "mood_rating": mood,
            "stress_level": stress,
            "sleep_hours": sleep,
            "exercised": False,
            "socialized": False,
        },
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Stored date matches submitted date
# ---------------------------------------------------------------------------

def test_stored_date_matches_submitted_date(client, alice_headers):
    """
    Name: Date stored in the DB is exactly what the client sent
    Setup: alice submits a check-in with date DATE_A
    Action: POST /checkins; GET /checkins/{id}
    Expected: date field on the returned record equals DATE_A exactly
    Why: If the server re-formats the date through a datetime object in the
         local or UTC timezone, the stored string can shift by one day for
         clients near midnight.
    """
    resp = _create(client, alice_headers, DATE_A)
    assert resp.status_code == 201
    entry_id = resp.json()["id"]

    fetched = client.get(f"/api/checkins/{entry_id}", headers=alice_headers)
    assert fetched.status_code == 200
    assert fetched.json()["date"] == DATE_A, (
        f"Expected stored date '{DATE_A}', got '{fetched.json()['date']}'"
    )


def test_date_field_is_yyyy_mm_dd_string(client, alice_headers):
    """
    Name: Date field in the API response is a plain YYYY-MM-DD string
    Setup: alice submits a check-in with date DATE_A
    Action: GET /checkins/{id}
    Expected: date is a str matching YYYY-MM-DD, not a datetime or epoch int
    Why: If the serialiser returns a full ISO-8601 datetime with a 'Z' suffix
         (e.g. '2026-05-30T00:00:00Z'), JavaScript's `new Date(v)` would
         interpret it differently from a date-only string, causing the same
         off-by-one display bug the fix targets.
    """
    resp = _create(client, alice_headers, DATE_A)
    entry_id = resp.json()["id"]
    body = client.get(f"/api/checkins/{entry_id}", headers=alice_headers).json()

    date_val = body["date"]
    import re
    assert isinstance(date_val, str), f"Expected str, got {type(date_val)}"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_val), (
        f"Date is not YYYY-MM-DD: '{date_val}'"
    )


def test_list_date_fields_are_all_yyyy_mm_dd(client, alice_headers):
    """
    Name: Every date in GET /checkins uses YYYY-MM-DD format
    Setup: alice creates three check-ins on different dates
    Action: GET /checkins
    Expected: every item's date is a YYYY-MM-DD string
    Why: The list response goes through a different serialiser code path than
         the single-item response. A missing model_config or wrong field type
         could produce datetime strings only on the list endpoint.
    """
    import re
    for d in [DATE_A, DATE_B, DATE_C]:
        _create(client, alice_headers, d)

    items = client.get("/api/checkins", headers=alice_headers).json()
    assert len(items) == 3
    for item in items:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", item["date"]), (
            f"List item date is not YYYY-MM-DD: '{item['date']}'"
        )


# ---------------------------------------------------------------------------
# Mood trend dates
# ---------------------------------------------------------------------------

def test_mood_trends_returns_submitted_dates(client, alice_headers):
    """
    Name: /dashboard/mood-trends echoes back the exact submitted dates
    Setup: alice creates check-ins for DATE_A, DATE_B, DATE_C
    Action: GET /dashboard/mood-trends
    Expected: trend array contains all three dates as YYYY-MM-DD strings
    Why: If the service layer converts dates through Python's datetime, the
         UTC-vs-local ambiguity can shift them; this test pins the contract
         that the stored date string passes through unchanged.
    """
    for d in [DATE_A, DATE_B, DATE_C]:
        _create(client, alice_headers, d)

    resp = client.get("/api/dashboard/mood-trends", headers=alice_headers)
    assert resp.status_code == 200
    trend_dates = [pt["date"] for pt in resp.json()["trends"]]
    assert DATE_A in trend_dates, f"{DATE_A} missing from mood trends: {trend_dates}"
    assert DATE_B in trend_dates, f"{DATE_B} missing from mood trends: {trend_dates}"
    assert DATE_C in trend_dates, f"{DATE_C} missing from mood trends: {trend_dates}"


def test_mood_trends_dates_are_yyyy_mm_dd_strings(client, alice_headers):
    """
    Name: Mood trend date fields are plain YYYY-MM-DD strings
    Setup: alice creates one check-in
    Action: GET /dashboard/mood-trends
    Expected: every point's date matches YYYY-MM-DD
    Why: The frontend formatter `format(parseISO(v), ...)` requires a
         date-only string; a full ISO datetime would be parsed differently
         and could still produce the off-by-one bug even with the fix applied.
    """
    import re
    _create(client, alice_headers, DATE_A)

    resp = client.get("/api/dashboard/mood-trends", headers=alice_headers)
    for pt in resp.json()["trends"]:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", pt["date"]), (
            f"Mood trend date is not YYYY-MM-DD: '{pt['date']}'"
        )


def test_mood_trends_chronological_order(client, alice_headers):
    """
    Name: Mood trend points are in chronological (oldest-first) order
    Setup: alice creates check-ins for DATE_A then DATE_C then DATE_B
    Action: GET /dashboard/mood-trends
    Expected: dates appear in ascending order: DATE_A, DATE_B, DATE_C
    Why: The Recharts LineChart connects points left-to-right. If the API
         returns them newest-first, the line would zigzag backwards in time.
    """
    for d in [DATE_A, DATE_C, DATE_B]:   # intentionally unordered
        _create(client, alice_headers, d)

    resp = client.get("/api/dashboard/mood-trends", headers=alice_headers)
    dates = [pt["date"] for pt in resp.json()["trends"]]
    assert dates == sorted(dates), (
        f"Mood trends are not in chronological order: {dates}"
    )


def test_mood_trend_value_matches_submitted_mood_rating(client, alice_headers):
    """
    Name: Mood trend value equals the mood_rating submitted
    Setup: alice creates a check-in on DATE_A with mood_rating=5
    Action: GET /dashboard/mood-trends
    Expected: the trend point for DATE_A has value=5.0
    Why: If the service reads the wrong column or applies a transformation,
         the chart plots the wrong number — this pins the value passthrough.
    """
    _create(client, alice_headers, DATE_A, mood=5)

    resp = client.get("/api/dashboard/mood-trends", headers=alice_headers)
    point = next(pt for pt in resp.json()["trends"] if pt["date"] == DATE_A)
    assert point["value"] == 5.0, f"Expected 5.0, got {point['value']}"


# ---------------------------------------------------------------------------
# Stress trend dates
# ---------------------------------------------------------------------------

def test_stress_trends_returns_submitted_dates(client, alice_headers):
    """
    Name: /dashboard/stress-trends echoes back the exact submitted dates
    Setup: alice creates check-ins for DATE_A, DATE_B, DATE_C
    Action: GET /dashboard/stress-trends
    Expected: trend array contains all three dates as YYYY-MM-DD strings
    """
    for d in [DATE_A, DATE_B, DATE_C]:
        _create(client, alice_headers, d)

    resp = client.get("/api/dashboard/stress-trends", headers=alice_headers)
    assert resp.status_code == 200
    trend_dates = [pt["date"] for pt in resp.json()["trends"]]
    assert DATE_A in trend_dates
    assert DATE_B in trend_dates
    assert DATE_C in trend_dates


def test_stress_trend_value_matches_submitted_stress_level(client, alice_headers):
    """
    Name: Stress trend value equals the stress_level submitted
    Setup: alice creates a check-in on DATE_A with stress_level=2
    Action: GET /dashboard/stress-trends
    Expected: the trend point for DATE_A has value=2.0
    """
    _create(client, alice_headers, DATE_A, stress=2)

    resp = client.get("/api/dashboard/stress-trends", headers=alice_headers)
    point = next(pt for pt in resp.json()["trends"] if pt["date"] == DATE_A)
    assert point["value"] == 2.0, f"Expected 2.0, got {point['value']}"


def test_stress_trends_chronological_order(client, alice_headers):
    """
    Name: Stress trend points are in chronological (oldest-first) order
    Setup: three check-ins in unordered date order
    Action: GET /dashboard/stress-trends
    Expected: dates appear in ascending order
    """
    for d in [DATE_C, DATE_A, DATE_B]:
        _create(client, alice_headers, d)

    resp = client.get("/api/dashboard/stress-trends", headers=alice_headers)
    dates = [pt["date"] for pt in resp.json()["trends"]]
    assert dates == sorted(dates), f"Stress trends not in chronological order: {dates}"


# ---------------------------------------------------------------------------
# Sleep-mood data dates
# ---------------------------------------------------------------------------

def test_sleep_mood_returns_submitted_dates(client, alice_headers):
    """
    Name: /dashboard/sleep-mood returns the correct date for each point
    Setup: alice creates one check-in on DATE_A with sleep_hours=8.5
    Action: GET /dashboard/sleep-mood
    Expected: the scatter point has date == DATE_A and sleep_hours == 8.5
    Why: The sleep-mood chart tooltip shows the date of each point; a wrong
         date would make it impossible for users to relate a scatter dot to a
         specific day.
    """
    _create(client, alice_headers, DATE_A, sleep=8.5)

    resp = client.get("/api/dashboard/sleep-mood", headers=alice_headers)
    assert resp.status_code == 200
    points = resp.json()["data"]
    match = next((p for p in points if p["date"] == DATE_A), None)
    assert match is not None, f"{DATE_A} not found in sleep-mood data: {points}"
    assert match["sleep_hours"] == 8.5


# ---------------------------------------------------------------------------
# User isolation on dashboard
# ---------------------------------------------------------------------------

def test_mood_trends_only_returns_own_data(client, alice_headers, bob, bob_headers):
    """
    Name: Mood trends for Bob never include Alice's check-ins
    Setup: alice creates a check-in on DATE_A; bob creates one on DATE_B
    Action: GET /dashboard/mood-trends with Bob's token
    Expected: DATE_A is not in Bob's trend dates; DATE_B is
    Why: Dashboard queries must be scoped by user_id. A missing filter would
         mix all users' data into a single trend line.
    """
    _create(client, alice_headers, DATE_A)
    _create(client, bob_headers, DATE_B)

    resp = client.get("/api/dashboard/mood-trends", headers=bob_headers)
    dates = [pt["date"] for pt in resp.json()["trends"]]
    assert DATE_B in dates
    assert DATE_A not in dates, "Alice's date appeared in Bob's mood trends"


def test_stress_trends_only_returns_own_data(client, alice_headers, bob, bob_headers):
    """
    Name: Stress trends for Bob never include Alice's check-ins
    """
    _create(client, alice_headers, DATE_A)
    _create(client, bob_headers, DATE_B)

    resp = client.get("/api/dashboard/stress-trends", headers=bob_headers)
    dates = [pt["date"] for pt in resp.json()["trends"]]
    assert DATE_B in dates
    assert DATE_A not in dates, "Alice's date appeared in Bob's stress trends"
