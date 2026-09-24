> **Public-release copy.** Fleet record ids and private paths in this saved record are redacted (`[redacted]`) or shortened to their repo-relative form; nothing else is changed.

VERDICT: FIX-REQUIRED

1. ACCEPTED — `docs/SOP-REGISTRY.md:43` now uses the generic `<adoption date> (<auth-log ref>)` placeholders; the private `[redacted]` reference and concrete date are gone.

2. ACCEPTED — `docs/v121-wave/LAND_CHECKLIST.md:19-24` now specifies the required bounded live-poller swap: disable the task, verify no matching process, pin rollback hash/size, atomically replace from a same-directory sibling, run `py_compile` plus the task's exact command line, re-enable, and confirm the next tick. It correctly treats ALERT as recovery evidence rather than race control.

3. ACCEPTED — `git log --oneline v1.2.0..HEAD` substantiates the previously challenged `[1.2.1]` CHANGELOG claims with `4a41993`, `3d03084`, `66a80ae`, `93dbaa9`, and `6b0939e`. Tag-to-tag reconciliation is the correct release scope.

4. ACCEPTED — `CHANGELOG.md:31-32` says “nine incident case studies,” and Part 7 of `docs/CREATOR-SEAT-BOOTSTRAP.md:402-471` contains exactly nine bold case-study leads, including the newly added “The byte-blind gate.”

5. ACCEPTED — the Part 8 reviewer checklist now points to section 6.7 at `docs/CREATOR-SEAT-BOOTSTRAP.md:490`.

DELTA. REJECTED — the named bootstrap and channel-core additions contain no private identifiers, the CHANGELOG bullets at `CHANGELOG.md:90-98` accurately describe the delta, the rotation example uses `YYYY-MM-DDb.md`, and the regenerated HTML carries the new bootstrap material. However, the new normative paragraph in `plugins/agent-protocol/skills/agent-core/references/never-idle-core.md:40-45` directly contradicts the immediately preceding categorical rule at lines 34-35: the existing text says session interrupts and context compaction “kill” a monitor silently, while the new text says a monitor can survive an interrupt. Reconcile the old sentence to express non-durability as a possibility (for example, “can kill it silently” or “may kill it silently”) so stop-then-arm and arm-and-verify form one consistent rule.
