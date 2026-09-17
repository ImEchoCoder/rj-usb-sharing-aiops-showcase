# Incident Lifecycle

One fault is one thread: **a single correlation ID** ties together its open,
updates, reminders, and recovery — in the alert DMs, the JSONL event history, and
the postmortem.

## Timeline

```
t0  health snapshot ............ ALL GREEN (idle, nothing recorded)
t1  snapshot ................... FAILING:
                                  actions = [open]
                                  incident_id = 12-char correlation id
                                  DM = "ALERT: <key> — <live LLM diagnosis>"
t2  snapshot, new issue key .... actions = [update]   DM = "UPDATE: <new key>"
t3..+ snapshot, same keys ...... within cooldown → silent
                                  after ALERT_REMINDER_S → "REMINDER"
t4  snapshot ................... HEALTHY:
                                  actions = [recover]
                                  DM = "RECOVERED: <key>"
                                  postmortem written with the SAME incident_id
```

### Key rules

- **Open/update/recover events only enter history when the state actually
  transitions**; healthy-idle is not recorded.
- The recover event is tagged with the **resolved** incident's ID; the persisted
  state then **clears `incident_id`** so the next fault gets a fresh one.
- A diagnosis is attached to ALERT / UPDATE / REMINDER transitions, never to
  RECOVER (recovery text is factual). If the LLM call fails, the alert still goes
  out — a broken model must not suppress an incident.
- `ALERT_COOLDOWN_S` suppresses re-DM for the *same* active set; a *new* fault key
  still alerts immediately.
- State is persisted (JSON) so a container restart doesn't re-alert the same thing.

## Events (JSONL history)

Every transition appends one line:

```jsonc
{
  "ts": 1789395970.126,
  "issues": [{"key": "obs/relay-metrics-stale", "severity": "critical", "detail": "no relay metrics pushed (forwarder/pushgateway down?)"}],
  "worst": "critical",
  "actions": ["open"],
  "incident_id": "107fcc994d84"
}
```

See [`examples/sample-incident.json`](../examples/sample-incident.json) for a full
sanitized incident (open → update → recover) as the system reports it.

## Postmortem + learning

On recovery:

1. Pair the last **open** event in the *past* (never a future one) with the
   current recover.
2. Write a short postmortem (`summary`, `cause`, `resolution`, `duration`,
   `incident_id`).
3. Optionally **record the confirmed fix** into the vector memory
   (`authority: LEARNED`) so the next diagnosis recalls it.
4. Repeated human approvals of the same fix drive a **runbook trust bump** — the
   path to tier-1 self-heal.

## Example incident (real shape, sanitized)

The repo ships [`examples/sample-incident.json`](../examples/sample-incident.json):
an `obs/relay-metrics-stale` event that looks exactly like the production
occurrence — including that the *apparent* cause ("forwarder/pushgateway down") was
**not** the real cause (it was a Loki ingest-side degradation starving the
telemetry push). That is the kind of grounded distinction the evidence pipeline is
built to make.