# Example tests

`example-tests/` holds a **clean-room** illustration of the dedup state machine
(pattern only — no production code) to demonstrate the test discipline used in
the private repo:

- state-machine transitions asserted explicitly (open / silent / remind / update / recover);
- a fault after a recover **must** get a fresh correlation id;
- reads and mutations are exercised by pure functions, no network.

Run:

```bash
python -m pytest tests/example-tests/ -q
```