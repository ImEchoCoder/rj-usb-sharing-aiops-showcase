#!/usr/bin/env python3
"""sample-rag-query.py — the retrieval -> rank -> evidence pattern (educational).

This is a self-contained illustration of the RAG pattern used by the AIOps agent:
embed the question, cosine-search the memory, rank by authority, and expose
contradictions. In the real system the index is Qdrant and embeddings come from an
embeddings API; here the corpus is tiny and in-memory so the demo is deterministic
and runnable with zero dependencies.

Run:  python examples/sample-rag-query.py --question "relay metrics went stale"
"""

from __future__ import annotations

import argparse
import hashlib
import math
import statistics
import sys


AUTHORITY_ORDER = {"live": 3, "kb": 2, "learned": 1}

# Docs are ("title", "body", "authority"). No production data here.
DOCS = [
    (
        "Relay metrics staleness (learned)",
        "If relay_up disappears from Prometheus, first check the shipper "
        "loop and the log-ingestion side, not the relay: recent incidents were "
        "caused by the log-push path blocking the metric upload (the relay itself "
        "kept restarts=0).",
        "learned",
    ),
    (
        "Own runbook: telemetry push",
        "Metrics are scraped every 30s and PUT to the pushgateway. A missing series "
        "older than ~5 minutes means the push stopped. Check the shipper journal for "
        "HTTP 500 / timeout lines before suspecting the monitored service.",
        "kb",
    ),
    (
        "Live probe (latest)",  # contrived, to show authority beats timestamp
        "All procs up, restarts=0, /healthz 200. No active fault on the relay.",
        "live",
    ),
]


def embed(text: str, dim: int = 64) -> list[float]:
    """Deterministic stand-in for a real embedding endpoint."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    values = [b for b in h[:dim // 4]] * (dim // 4)
    values = values[:dim]
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def retrieve(question: str, k: int = 2) -> list[tuple[str, str, str, float]]:
    qv = embed(question)
    ranked = []
    for title, body, authority in DOCS:
        score = cosine(qv, embed(f"{title}. {body}"))
        ranked.append((title, body, authority, score))
    ranked.sort(key=lambda r: (AUTHORITY_ORDER[r[2]], r[3]), reverse=True)
    return ranked[:k]


def find_contradictions(chosen: list[tuple[str, str, str, float]]) -> list[str]:
    learned = [b for _, b, a, _ in chosen if a == "learned"]
    live = [b for _, b, a, _ in chosen if a == "live"]
    flags = []
    for lb in learned:
        for vb in live:
            if "no active fault" in vb and "not the relay" in lb:
                flags.append("LEARNED claim conflicts with LIVE evidence — trust Live.")
    return flags


def main() -> int:
    ap = argparse.ArgumentParser(description="Illustrate the RAG retrieval pattern.")
    ap.add_argument("--question", default="why did the relay metric go stale?")
    args = ap.parse_args()

    chosen = retrieve(args.question)
    flags = find_contradictions(chosen)

    print(f"Q: {args.question}\n")
    for title, body, authority, score in chosen:
        print(f"[{authority.upper():7s} score={score:.3f}] {title}\n  {body}\n")
    for f in flags:
        print(f"!! {f}")
    print("evidence.order:", [a for _, _, a, _ in chosen])

    # The gate the real pipelines enforce.
    if flags:
        print("poison_flags: present — degrade answer with a warning")
    if "live" not in [a for _, _, a, _ in chosen]:
        print("warning: no LIVE evidence in top-k; answer is reference-only")

    print("\nmodel_prompt_block:")
    print(json_blob(chosen, flags))
    return 0


def json_blob(chosen, flags) -> str:
    import json

    return json.dumps(
        {
            "evidence": {
                "ranked": [
                    {"authority": a, "score": round(s, 3), "title": t}
                    for t, _, a, s in chosen
                ],
                "poison_flags": flags,
            }
        },
        indent=2,
    )


if __name__ == "__main__":
    sys.exit(main())