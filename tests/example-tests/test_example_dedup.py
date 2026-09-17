"""Tests for the example dedup state machine."""

from example_dedup import decide


def test_open_recovers_with_fresh_id_each_fault():
    state = {"active_keys": [], "notified_at": 0.0, "last_update_at": 0.0, "incident_id": None}
    actions, state = decide(["relay/stale"], state, now=1.0)
    assert actions == ["open"]
    rid = state["incident_id"]
    assert rid

    actions, state = decide([], state, now=5.0)
    assert actions == ["recover"]
    assert state["incident_id"] is None

    actions, state = decide(["relay/stale"], state, now=7.0)
    assert actions == ["open"]
    assert state["incident_id"] != rid


def test_same_key_silent_within_cooldown_then_remind():
    state = {"active_keys": [], "notified_at": 0.0, "last_update_at": 0.0, "incident_id": None}
    _, state = decide(["relay/stale"], state, now=1.0)

    actions, state = decide(["relay/stale"], state, now=2.0)
    assert actions == ["silent"]

    actions, _ = decide(["relay/stale"], state, now=9999.0)
    assert actions == ["remind"]


def test_new_key_updates_without_losing_incident_id():
    state = {"active_keys": [], "notified_at": 0.0, "last_update_at": 0.0, "incident_id": None}
    _, state = decide(["relay/stale"], state, now=1.0)
    rid = state["incident_id"]

    actions, state = decide(["relay/stale", "loki/deadlines"], state, now=3.0)
    assert actions == ["update"]
    assert state["incident_id"] == rid