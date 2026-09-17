# Security Model

The security posture of the AIOps layer is: **the LLM is advisory, the approval
gate is the authority, the SSH bridge is the perimeter, secrets never touch the
repo.**

## 1. Approval-gated mutation

- **Reads are automatic.** An allowlist of safe commands (with no shell
  metacharacters that could smuggle a second command) runs immediately and returns
  output.
- **Mutations are queued.** An operator must reply `/approve <token>` in the DM;
  every request carries a per-request token and a TTL, and the exact command + target
  is shown before a decision. `/deny` cancels with an audit line.
- Executions are **documented** in an append-only audit log (who/what/when +
  result), and any auto-heal failure records a `ROLLBACK` marker.

## 2. Restricted SSH bridge

- The bridge VM's SSH does **not** allow arbitrary shells: the authorized key is a
  **forced-command** entry (`restrict`) that can only invoke an allowlisted runner.
- The runner is a minimal gatekeeper: it validates each requested command against
  an explicit allowlist before executing (`systemctl is-active/status`,
  loopback `/healthz`, … restarts) and writes its own audit trail.
- The observability agent never holds the *production* admin key; it holds only the
  restricted ops key, and even that cannot open an interactive session.

## 3. Ownership boundaries

- Telemetry collection is **push-only** (the product VM pushes logs/metrics to the
  observability VM; no inbound ports are opened on the product box).
- The agent runs in a container with read-only mounts for the KB and the ops key.
- Production deployment config (`systemd`, nginx, env layout) is not published.

## 4. Secrets handling

- No `.env`, tokens, or keys are committed. Secrets arrive via sealed env at
  deploy time; gitignoring `.env` is enforced.
- Syntax is: **the repo documents *which* secrets exist and how they're injected,
  never their values.**

## 5. The model's role

- Output is always **advisory JSON** with evidence citations; it can never execute
  anything by itself.
- `json_mode`, enum validation, and `confidence_score` clamping keep the machine
  verdict well-formed; the human is the decider.
- A failing or hallucinating model degrades to "no diagnosis", never to "run the
  command".

## 6. Honest limits

No system using an offline-interpreted client can be hardened to "uncrackable";
the acknowledged single points of failure are the SSH keys and the human-account
credentials on the servers — which is why they are the focus of rotation,
hardening (key-only logins, no root login, rate-limited jails), and the break-glass
key plan.

## Published here vs. private

This showcase publishes the **patterns**. The exact allowlist, the runner
implementation, the warning/deny heuristics, and the production topology remain
private. This repo contains **no hostnames, addresses, ports, service names,
keys, or credentials** — references to VMs/servers/bridges are conceptual, not
identifiable.