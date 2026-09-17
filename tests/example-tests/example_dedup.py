# example/example_dedup.py — tiny pure dedup state machine.

"""Clean-room illustration of the alert dedup state machine used in the agent.

Transitions:
  healthy  --fault-->  open (alert once, set notified_at)
  open     --same-->   silent-within-cooldown, else remind
  open     --new key--> update
  any      --clear-->  recover (clears incident_id)

This is a pattern re-implemented for the showcase, not production code.
"""

from __future__ import annotations

import itertools
import uuid

IDS = itertools.count(0)
COOLDOWN_S = 600


def fresh_id() -> str:
    # simulated correlation id (12 chars in the real system)
    return uuid.uuid4().hex[:12]


def decide(issues: list[str], state: dict, now: float) -> tuple[list[str], dict]:
    was = set(state.get("active_keys", []))
    keys = set(issues)
    actions: list[str] = []

    if not keys:
        actions = ["recover"] if was else []
        next_state = {
            "active_keys": [],
            "notified_at": 0.0,
            "last_update_at": now,
            "incident_id": None,
        }
        return actions, next_state

    fresh = keys - was
    opened = not was or bool(fresh)
    within_cooldown = state.get("notified_at") and (now - state["notified_at"]) < COOLDOWN_S

    if fresh:
        actions.append("open" if not was else "update")
        notified_at = now
    elif within_cooldown:
        actions.append("silent")
        notified_at = state.get("notified_at", 0.0)
    else:
        actions.append("remind")
        notified_at = now

    next_state = {
        "active_keys": sorted(keys),
        "notified_at": notified_at,
        "last_update_at": now,
        "incident_id": state.get("incident_id") or fresh_id(),
    }
    return actions, next_state