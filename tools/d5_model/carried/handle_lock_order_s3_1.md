- ⚠ **New, smaller residual (R9′):** mandatory locking means *we* can block *peers*. A held
  lock makes a seat's hand-append fail with `PermissionError` — correct, but it must be
  **short**, and it must never be held across a network call, a subprocess, or a git
  operation. ⛔ **The lock-scope sentence that stood here through v8 — *"The lock scope is
  gate → write → read-back and nothing else"* — is STRUCK at its site (v8-round O4,
  [[amend-at-the-claim-site]]): it contradicted §12/§6.2, which run the §1 gate clauses,
  §2.2 predicates, §2.4 consumer agreement and the §4.1d scan BEFORE the lock ("the
  prechecks stay where they are … lock-free by design"), and read literally it licensed
  holding the lock across §2.4's registered-consumer invocations — subprocesses under
  timeouts, including shell-grammar consumers — which is the "never held across a
  subprocess" violation this same bullet forbids, capable of wedging the fleet's channel
  for the length of a 28-call-site census. The same un-struck-superseded-clause class v6
  struck at §2, recommitted here.** The lock scope OF RECORD, restated as the order
  §12/§6.2 actually pin: **lock scope = §4.1e binding re-verify → emission
  recompute/compare → journal `INTENT` write → single `fh.write` → read-back → release**
  — plus §7.1b step 1's whole-lane snapshot read, which is an in-memory read and no more.
  A write path that can wedge the fleet's own channel is worse than the problem it solves.
