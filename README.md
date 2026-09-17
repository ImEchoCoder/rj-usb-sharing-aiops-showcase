# RJ USB Sharing — AI-powered AIOps (Engineering Showcase)

A sanitized engineering showcase of the **AIOps / observability layer** behind a
commercial SaaS product (**RJ USB Sharing** — secure USB/IP device sharing for
phone-flashing repair services).

> **Important.** This repository is intentionally **sanitized demo material**, not
> the production source. The production codebase is private and proprietary; it is not
> published — it contains the business logic of a revenue-generating SaaS, its
> licenses, credentials, and server infrastructure details.
>
> Nothing in this repo contains live credentials, private keys, bot tokens, server
> addresses, or customer data.

---

## What this showcases

An **agentic incident-response system** ("AIOps brain") that watches a production
stack, reasons over **real live evidence**, and proposes fixes — but **never executes
anything without a human approving it**. Built around a 6-step loop:

```
Observe ─► Retrieve ─► Reason ─► Approve ─► Act ─► Learn
   │           │          │          │         │        │
   │           │          │      human-in-     │   postmortem feeds
   │           │          │      the-loop      │   the RAG memory
   ▼           ▼          ▼          ▼         ▼        ▼
Loki/Prom    Qdrant RAG  LLM JSON    Telegram    SSH     KB learns
health snap  grounding   diagnosis   approval   bridge   the fix
```

### The stack (all lightweight, fits a 1 GB VM)

| Layer | Technology | Purpose |
|---|---|---|
| Logs | Loki (LogQL) | Centrally shipped journald logs, `unit` labels |
| Metrics | Prometheus + Pushgateway | Relay/service metrics, 30 s cadence |
| Dashboards | Grafana | Auto-provisioned datasources + overview panel |
| Vector store | Qdrant | RAG memory: KB docs + learned incidents |
| Agent | FastAPI (`/diagnose`, `/alerts`, `/incident`, `/runbooks`) | Context gathering + diagnosis + lifecycle |
| LLM | OpenRouter (primary) → Gemini (fallback) | `json_mode` diagnostics, embeddings, chat |
| ChatOps | Telegram bot DMs | Operator-facing commands + push alerting |
| Bridge | Restricted SSH (forced-command, allowlist) | Read-only auto-run; mutations always ask |

---

## The AIOps contract

1. **Proactive:** on every health snapshot, if something degrades the bot **pushes a DM** —
   nobody has to ask.
2. **Grounded:** diagnoses are built from **live evidence** (LogQL queries, Prometheus
   instant queries, RAG-retrieved runbooks) with citations — not LLM guesses.
3. **Safe by design:** reads are automatic; **any state-changing action requires an
   explicit human `/approve`** in the DM, with a per-request token and TTL.
4. **Self-learning:** every incident is correlated under one ID, gets a human-reviewed
   postmortem, and the confirmed fix is stored back into the RAG memory so the next
   diagnosis recalls it.
5. **Honest limits:** the LLM is advisory and gated; the real kill-switch is the
   approval flow and the allowlisted-command SSH bridge, never the model.

## Repository layout

```
├── README.md
├── docs/
│   ├── aiops-overview.md        # Observe → … → Learn, roles, timers, tiers
│   ├── rag-architecture.md      # Qdrant + embeddings + authority + poison defense
│   ├── incident-lifecycle.md    # correlation, postmortem, runbook learning
│   └── security-model.md        # approval gate, SSH bridge, secrets, audit
├── examples/
│   ├── sample-incident.json       # a real-shaped incident, sanitized
│   ├── sample-rag-query.py        # retrieval + evidence-ranking pattern (runnable)
│   ├── sample-agent-workflow.py   # read-only vs mutating decision loop (runnable)
│   ├── sample-prometheus-alert.yml
│   └── sample-loki-loki.yaml
└── tests/example-tests/           # example test discipline (runnable with pytest)
```

The large architecture PNGs in the author's private repo are **not** copied here;
ASCII diagrams in the docs are the portable equivalent.

## Running the examples

```bash
# Retrieval pattern (pure Python, no network — embeddings are mocked in)
python examples/sample-rag-query.py --question "relay metrics went stale"

# Agent decision-loop pattern (prints a transcript)
python examples/sample-agent-workflow.py --issue "usbip-relay inactive"

python -m pytest tests/example-tests/ -q
```

## Production experience (what a recruiter should read)

- Ran a **real multi-VM stack** (this layer + the USB/IP relay + web backend) in production.
- Root-caused a real incident: an **ingest-side degradation in the log store**
  starved the telemetry push, caused the relay metric to go stale, and tripped a
  false alert — diagnosed from Prometheus timestamps, the log store's own logs,
  and reference data.
- Hardened the stack afterwards: decoupled the metric push from the log-shipping loop,
  tightened Loki limits for a 1 GB box, and fixed an incident-correlation-ID lifecycle bug.
- Continual guardrails: approval-gated remediation ran in controlled fire-tests
  (graceful stop/start of a production service with **zero user-facing impact**).

## Security notice

See [`docs/security-model.md`](docs/security-model.md). The examples here are
illustrative patterns; the production implementation differs and is private.

## License

Examples and docs in this repo are published under the MIT License (see
[`LICENSE`](LICENSE)). The **RJ USB Sharing product itself is proprietary** and not
published.