# RAG Architecture

The vector memory makes the LLM critique **grounded**: it can answer "what went
wrong **here** and what fixed it last time" instead of producing generic advice.

## Storage (Qdrant)

Two collections are never mixed:

- **KB** — curated operational documents & runbooks (how the stack is deployed,
  known failure patterns, remediation steps).
- **LEARNED** — incidents recorded by the system itself: each *confirmed* incident
  is embedded and upserted as a vector, tagged with authority `LEARNED`.

Both are tiny (a 1 GB VM — no heavy corpora), so retrieval is fast and cheap.

## Embeddings

- Provider-agnostic: **OpenRouter** upstream first (`text-embedding-3-small`),
  native Gemini fallback.
- On startup and on ingest, documents are chunked, embedded, and upserted with
  metadata (`source`, `authority`, `ts`, headers).

## Retrieval

`retrieve(query, k)`:

1. Embed the question.
2. Cosine-search the collections.
3. Return the top-K hits with a `score`.

## Authority & ranking

Evidence has an explicit hierarchy and the model is *told* about it:

```
LIVE    (fresh operational evidence — highest)   — but "trust but verify"
 KB     (curated runbook knowledge)
LEARNED (past incidents — reference only)
```

A low-authority or low-score hit is excluded or de-prioritized; the system prompt
labels each block so the model can weigh it honestly.

## Poison / contradiction defense

- Learned incidents must never out-rank live evidence.
- A deterministic **contradiction check** flags a `LEARNED` claim that conflicts
  with current `LIVE` evidence (e.g. "relay is on `X`" while Live now says `Y`) —
  the contradiction is surfaced as a warning in the evidence block and to the model.
- Retrieval never **executes** anything: outputs are advisory.

## Confidence

Each answer carries:

- `confidence` — the model's free-text verdict.
- `confidence_score` — validated/clamped to `[0,1]`.
- per-field `field_confidence{...}`.
- `evidence: ranked + poison_flags` so the operator can inspect exactly what the
  answer was based on.

## Golden eval (no LLM needed)

An invariant evaluator runs over a golden regression set and gates on a
`MIN_PASS_RATE`:

- schema keys present; severity/confidence in the valid enums;
- `confidence_score` ∈ [0,1];
- authority ordering respected;
- poison examples must be flagged.

Because it needs no API key, it runs in CI and on every deploy.

## Example

See [`examples/sample-rag-query.py`](../examples/sample-rag-query.py) for a
self-contained, runnable version of the retrieve → rank → return pattern.