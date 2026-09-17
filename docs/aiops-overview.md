# AIOps Overview

The agentic layer runs as a small FastAPI service (`agent`) on a dedicated
observability VM, watching a production stack that lives on a separate VM. It
implements a six-step autonomous loop with a hard human gate in the middle.

## The 6-step loop

### 1. Observe

Every `ALERT_INTERVAL_S` (default 300 s) the agent takes a **read-only health
snapshot** of the whole stack:

- **Logs** — Loki `/ready`, plus LogQL summary queries over recent JSONL.
- **Metrics** — Prometheus `/ready`, plus instant queries (`relay_up`,
  etc.). A **missing metric = the shipper is dead**, even if every container is up.
- **Vector store** — is Qdrant reachable? (`/collections`)
- **Containers** — `docker ps` state on the observability host.
- **Production** — over the restricted SSH bridge, only allowlisted read-only
  commands (`systemctl is-active …`, loopback `/healthz`).
- **Public** — HTTPS health of the public site.

Severities: `healthy | info | warning | critical`. Classification is based on
**command stdout, not the shell exit code** — an SSH bridge propagates the remote
command's status, so a stopped service and a dead SSH channel must be told apart.

### 2. Retrieve

For anything beyond a trivial status, the agent pulls **grounding evidence**:

- Recent matching log lines for each affected unit (last N minutes).
- A compact metrics summary (instant values + deltas).
- **RAG**: top-K relevant documents from the vector memory
  (`LIVE` operational docs, `KB` runbooks, `LEARNED` past incidents), and the
  detection of any contradiction between them.

### 3. Reason

The evidence + retrieved docs are handed to the LLM (OpenRouter primary, Gemini
fallback) with **JSON mode**:

```jsonc
{
  "severity": "warning",          // healthy | info | warning | critical
  "summary": "…",
  "likely_cause": "…",
  "proposed_fix": "…",
  "commands": ["systemctl restart …"],   // allowlisted-safe only
  "confidence": "high"            // + numeric confidence_score in [0,1]
}
```

The model is told it is **advisory**: its job is to produce a hypothesis and
commands *for review*. A failing LLM call must never suppress an alert.

### 4. Approve

- **Read-only operations** (an allowlist of safe commands with no shell
  metacharacters) run **automatically** and return immediately.
- **State-changing operations** are **queued**: the operator gets an approval
  request (token, description, exact command, target host) in Telegram and must
  reply `/approve <token>` (alternatively `/deny`). Requests expire (TTL) and every
  decision is appended to an audit log.

### 5. Act

An **approved** command runs over the SSH bridge with a forced-command wrapper
(the remote side can only run the allowlisted runner — no interactive shell). After
a fix, a post-fix health re-check runs and the result is reported in the DM.

### 6. Learn

- Every transition (open / update / remind / recover) is recorded to a JSONL event
  history under one **incident correlation ID**.
- On recovery, the agent pairs the last open with the recover, writes a short
  postmortem, and offers the confirmed fix.
- After **N** human approvals of the same kind, the fix becomes a **trusted
  runbook**. A trusted + critical + high-confidence + allowlist-safe runbook can be
  applied *automatically* (tier-1 self-heal), with an audit line and a `ROLLBACK`
  marker on failure.

## Operator-facing commands (Telegram DM)

| Command | Role | Behavior |
|---|---|---|
| `/read` | Reader | Questions over the KB / RAG memory |
| `/diagnose` | Analyst | Live evidence → JSON diagnosis |
| `/execute` | Executor | Command runner (read → auto, mutate → approve) |
| `/code <req>` | Executor | Help the coding agent with approvals |
| `/approve` / `/deny` | Operator | Decide on a pending action |
| `/recents` | any | Recent incidents/history |

## Alerting timers & dedup

- `ALERT_INTERVAL_S` — health snapshot cadence.
- `ALERT_REMINDER_S` — re-DM after a long silence on the same open incident.
- `ALERT_COOLDOWN_S` — suppress re-DM of unchanged active keys within the window;
  **new** fault keys still alert, long outages still remind.
- State machine persists to a JSON file so restarts don't spam duplicates.