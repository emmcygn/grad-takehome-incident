import pytest
from datetime import datetime, timezone  # Added timezone to fix namespace issue
from render_schedule import render_schedule, parse_timestamp, get_base_user

# Sample schedule for tests
SAMPLE_SCHEDULE = {
    "users": ["alice", "bob", "charlie"],
    "handover_start_at": "2025-11-07T17:00:00Z",
    "handover_interval_days": 7
}

def test_parse_timestamp():
    ts = "2025-11-07T17:00:00Z"
    dt = parse_timestamp(ts)
    assert dt == datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)

def test_get_base_user():
    time = parse_timestamp("2025-11-07T17:00:00Z")
    assert get_base_user(SAMPLE_SCHEDULE, time) == "alice"

    time = parse_timestamp("2025-11-14T17:00:00Z")
    assert get_base_user(SAMPLE_SCHEDULE, time) == "bob"

    time = parse_timestamp("2025-11-21T17:00:00Z")
    assert get_base_user(SAMPLE_SCHEDULE, time) == "charlie"

    # Before start (projects backwards)
    time = parse_timestamp("2025-10-31T17:00:00Z")  # 7 days before
    assert get_base_user(SAMPLE_SCHEDULE, time) == "charlie"

def test_basic_rotation():
    from_time = parse_timestamp("2025-11-07T17:00:00Z")
    until_time = parse_timestamp("2025-11-28T17:00:00Z")
    overrides = []
    entries = render_schedule(SAMPLE_SCHEDULE, overrides, from_time, until_time)
    assert len(entries) == 3
    assert entries[0] == {"user": "alice", "start_at": "2025-11-07T17:00:00Z", "end_at": "2025-11-14T17:00:00Z"}
    assert entries[1] == {"user": "bob", "start_at": "2025-11-14T17:00:00Z", "end_at": "2025-11-21T17:00:00Z"}
    assert entries[2] == {"user": "charlie", "start_at": "2025-11-21T17:00:00Z", "end_at": "2025-11-28T17:00:00Z"}

def test_simple_override():
    from_time = parse_timestamp("2025-11-07T17:00:00Z")
    until_time = parse_timestamp("2025-11-21T17:00:00Z")
    overrides = [
        {"user": "charlie", "start_at": "2025-11-10T17:00:00Z", "end_at": "2025-11-10T22:00:00Z"}
    ]
    entries = render_schedule(SAMPLE_SCHEDULE, overrides, from_time, until_time)
    assert len(entries) == 4
    assert entries[0] == {"user": "alice", "start_at": "2025-11-07T17:00:00Z", "end_at": "2025-11-10T17:00:00Z"}
    assert entries[1] == {"user": "charlie", "start_at": "2025-11-10T17:00:00Z", "end_at": "2025-11-10T22:00:00Z"}
    assert entries[2] == {"user": "alice", "start_at": "2025-11-10T22:00:00Z", "end_at": "2025-11-14T17:00:00Z"}
    assert entries[3] == {"user": "bob", "start_at": "2025-11-14T17:00:00Z", "end_at": "2025-11-21T17:00:00Z"}

def test_overlapping_overrides():
    from_time = parse_timestamp("2025-11-07T17:00:00Z")
    until_time = parse_timestamp("2025-11-14T17:00:00Z")
    overrides = [
        {"user": "bob", "start_at": "2025-11-10T12:00:00Z", "end_at": "2025-11-12T12:00:00Z"},
        {"user": "charlie", "start_at": "2025-11-11T00:00:00Z", "end_at": "2025-11-11T23:59:00Z"}  # Nested inside bob
    ]
    entries = render_schedule(SAMPLE_SCHEDULE, overrides, from_time, until_time)
    assert len(entries) == 5
    assert entries[0]["user"] == "alice"  # Before first override
    assert entries[1]["user"] == "bob"    # Bob starts
    assert entries[2]["user"] == "charlie"  # Charlie nested
    assert entries[3]["user"] == "bob"    # Back to bob
    assert entries[4]["user"] == "alice"  # Back to alice until handover

def test_truncation():
    from_time = parse_timestamp("2025-11-10T12:00:00Z")
    until_time = parse_timestamp("2025-11-11T12:00:00Z")
    overrides = []
    entries = render_schedule(SAMPLE_SCHEDULE, overrides, from_time, until_time)
    assert len(entries) == 1
    assert entries[0] == {"user": "alice", "start_at": "2025-11-10T12:00:00Z", "end_at": "2025-11-11T12:00:00Z"}

def test_query_before_start():
    from_time = parse_timestamp("2025-10-31T17:00:00Z")  # Before handover_start
    until_time = parse_timestamp("2025-11-07T17:00:00Z")
    overrides = []
    entries = render_schedule(SAMPLE_SCHEDULE, overrides, from_time, until_time)
    assert len(entries) == 1
    assert entries[0]["user"] == "charlie"  # Projected backward

def test_empty_overrides():
    from_time = parse_timestamp("2025-11-07T17:00:00Z")
    until_time = parse_timestamp("2025-11-14T17:00:00Z")
    overrides = []
    entries = render_schedule(SAMPLE_SCHEDULE, overrides, from_time, until_time)
    assert len(entries) == 1
    assert entries[0]["user"] == "alice"

def test_override_covering_entire_range():
    from_time = parse_timestamp("2025-11-07T17:00:00Z")
    until_time = parse_timestamp("2025-11-14T17:00:00Z")
    overrides = [{"user": "dave", "start_at": "2025-11-07T17:00:00Z", "end_at": "2025-11-14T17:00:00Z"}]
    entries = render_schedule(SAMPLE_SCHEDULE, overrides, from_time, until_time)
    assert len(entries) == 1
    assert entries[0]["user"] == "dave"

def test_override_before_from():
    from_time = parse_timestamp("2025-11-10T17:00:00Z")
    until_time = parse_timestamp("2025-11-14T17:00:00Z")
    overrides = [{"user": "charlie", "start_at": "2025-11-07T17:00:00Z", "end_at": "2025-11-12T17:00:00Z"}]
    entries = render_schedule(SAMPLE_SCHEDULE, overrides, from_time, until_time)
    assert len(entries) == 2
    assert entries[0] == {"user": "charlie", "start_at": "2025-11-10T17:00:00Z", "end_at": "2025-11-12T17:00:00Z"}
    assert entries[1] == {"user": "alice", "start_at": "2025-11-12T17:00:00Z", "end_at": "2025-11-14T17:00:00Z"}

def test_override_after_until():
    from_time = parse_timestamp("2025-11-07T17:00:00Z")
    until_time = parse_timestamp("2025-11-10T17:00:00Z")
    overrides = [{"user": "charlie", "start_at": "2025-11-09T17:00:00Z", "end_at": "2025-11-12T17:00:00Z"}]
    entries = render_schedule(SAMPLE_SCHEDULE, overrides, from_time, until_time)
    assert len(entries) == 2
    assert entries[0]["user"] == "alice"
    assert entries[1]["user"] == "charlie"

def test_same_start_end():
    from_time = parse_timestamp("2025-11-07T17:00:00Z")
    until_time = parse_timestamp("2025-11-07T17:00:00Z")
    overrides = []
    entries = render_schedule(SAMPLE_SCHEDULE, overrides, from_time, until_time)
    assert entries == []  # No duration

def test_no_users():
    schedule = {"users": [], "handover_start_at": "2025-11-07T17:00:00Z", "handover_interval_days": 7}
    from_time = parse_timestamp("2025-11-07T17:00:00Z")
    until_time = parse_timestamp("2025-11-14T17:00:00Z")
    with pytest.raises(ValueError):
        render_schedule(schedule, [], from_time, until_time)

def test_merge_consecutive():
    from_time = parse_timestamp("2025-11-07T17:00:00Z")
    until_time = parse_timestamp("2025-11-14T17:00:00Z")
    overrides = [
        {"user": "alice", "start_at": "2025-11-10T17:00:00Z", "end_at": "2025-11-12T17:00:00Z"}  # Same as base user
    ]
    entries = render_schedule(SAMPLE_SCHEDULE, overrides, from_time, until_time)
    assert len(entries) == 1  # Merged into one alice entry
    assert entries[0]["user"] == "alice"