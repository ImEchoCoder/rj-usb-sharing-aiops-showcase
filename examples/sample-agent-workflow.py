#!/usr/bin/env python3
"""sample-agent-workflow.py — read-only vs mutating decision loop (educational).

Mirrors the agent's execution policy without any production code:

  * an ALLOWLIST of safe read-only commands (no shell metacharacters) runs
    immediately and prints its output;
  * anything state-changing produces an approval request with a token + TTL and
    only 'runs' once an operator approves;

Run:  python examples/sample-agent-workflow.py --issue "usbip-relay inactive"
"""

from __future__ import annotations

import argparse
import secrets
import sys

# Read-only allowlist, modelled on the real one. No shell metacharacters allowed:
READ_ONLY = {
    "systemctl is-active usbip-relay",
    "systemctl status usbip-relay",
    "systemctl is-active usbip-cloud",
    "df -h",
    "free -m",
    "ss -tlnp",
    "curl http://127.0.0.1:9091/healthz",
}

MUTATING = {
    "systemctl restart usbip-relay",
    "systemctl restart usbip-cloud",
    "systemctl restart telemetry-forwarder",
}


def is_read_only(command: str) -> bool:
    if command not in READ_ONLY:
        return False
    for token in command.split():
        if any(ch in token for ch in ";&|`$\n"):
            return False
    return True


class ApprovalRequest:
    def __init__(self, command: str) -> None:
        self.command = command
        self.token = secrets.token_hex(6)
        self.status = "pending"  # pending / approved / denied

    def approve(self) -> None:
        self.status = "approved"

    def deny(self) -> None:
        self.status = "denied"


def execute(command: str, approvals: list[ApprovalRequest]) -> None:
    if is_read_only(command):
        print(f"[auto-run (read-only)] {command}\n  -> ok: service is active")
        return
    req = ApprovalRequest(command)
    approvals.append(req)
    print(f"[queue] {command}")
    print(f"  approval request -> /approve {req.token}  (TTL 1800s)")
    if req.token.startswith("sim"):
        req.approve()
        print(f"[approved] running: {req.command}")
    else:
        req.deny()
        print(f"[denied ] skipping: {req.command}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Illustrate the approval-gated runner.")
    ap.add_argument("--issue", default="usbip-relay inactive")
    args = ap.parse_args()

    print(f"issue: {args.issue}\n")
    approvals: list[ApprovalRequest] = []
    for command in ["systemctl is-active usbip-relay", "systemctl restart usbip-relay", "df -h"]:
        execute(command, approvals)
    print("\naudit: " + ", ".join(f"{r.command}->{r.status}" for r in approvals))
    return 0


if __name__ == "__main__":
    sys.exit(main())