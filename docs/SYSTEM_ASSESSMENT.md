# System assessment — capabilities, gaps, and what the community release changes

Date: 2026-07-05. Written as the design basis for the community release
(`multi-agent-protocol`, local-only). Internal document; a scrubbed excerpt
ships as the release's `docs/DESIGN.md`.

---

## 1. What is PROVEN (live evidence, not claims)

| capability | evidence |
|---|---|
| Independent-review convergence | 12 Codex review rounds on the protocol itself (SYS series); every blocker fixed same-cycle; two real TOCTOU vulnerabilities in the automerge path found by review rounds 10–11 and fixed before any deployment ran them |
| Cold-successor resume | Synthetic Phase-5 pilot: 6 sessions, sessions killed mid-unit, successors resumed from the ⚡ working-state block + channel alone, zero integrity violations across a 7-commit replay |
| Auth-log lane end-to-end | <private-repo> relay lane in production: GRANT → RELAY-SENT → RECEIVED(+sha) → exactly-one-landed CONSUMED → ACK, validated mechanically by `validate_auth_log.py` + CI |
| Integrity CI | append-only channel/auth-log checks, CHANNEL_STATE monotonicity, secret scan, fail-closed automerge guard — all firing in production on <private-repo> |
| 2-agent config | <private-repo>: 50+ working rounds under the ancestor protocol; owner-as-interface works for a single-project deployment |
| 3-agent config | <private-repo>: orchestrator-only interface live; workers on demand; heartbeat tick hardened through 4 independent review cycles |
| Config composition | The same skills serve both: role skills are thin deltas over agent-core; BINDINGS (not code) select the configuration. An orchestrator can front multiple worker pairs |
| Reviewer independence | Different-vendor reviewer (Codex) with byte-exact fingerprints; fingerprint mismatch = verdict authorizes nothing (caught real staleness twice) |

## 2. Where it is LACKING (honest gaps)

1. **Onboarding curve.** BINDINGS.md has ~10 slots; a newcomer stamping a
   workspace faces `{{FILL}}` walls with a glossary in a reference file.
   Friction observed even in our own pilot (TASKQUEUE example-duties confusion,
   fixed by a header note only).
2. **Session lifecycle UX.** Ending and resuming a role session requires
   knowing the memory discipline by heart or pasting recall lines. There is no
   one-word "checkpoint and let me close" or "reload the owner" action.
   → This is what /sleep and /wake fix.
3. **Review-round latency.** The poller runs on a 5-minute schedule; a round
   trip is minutes even when both sides are idle. Acceptable for protocol
   changes, noticeable for small units.
4. **Reviewer coupling.** The worked reviewer path assumes a local Codex CLI on
   the same machine. The protocol only requires "independent reviewer", but the
   tooling story is single-path today.
5. **PROXY_AUTH weight.** The auth-log lane is the most complex subsystem and
   most deployments (single project, principal talks to the owner directly)
   never need it. It must not sit in the mandatory path of a first install.
6. **Wave-census machinery** (builder read-waves, coverage checker) is
   <private-repo>-specific in flavor; generic but niche.
7. **Windows-first tooling.** Scheduled-task heartbeats, path examples, and the
   poller assume Windows in places; the protocol itself is OS-neutral.

## 3. What the community release SIMPLIFIES (decisions)

- **Local-only.** Cloud transport, automerge, watchdog, routines — all proven
  but platform-coupled and churning; excluded from v1. Roadmap line only.
- **PROXY_AUTH ships OFF.** Documented in ADVANCED.md; the default story is
  first-hand authorization in whichever session the principal talks to.
- **Wave-census → ADVANCED.md appendix.** Not in the quickstart path.
- **/sleep + /wake ship as first-class commands** — the lifecycle UX gap is the
  first thing a new user hits, so the release leads with the fix.
- **Reviewer is pluggable by documentation**: Codex via `reviewer_poller.py` as
  the worked example; any second CLI or a different-model Claude session as
  alternatives; bound per-deployment in BINDINGS.
- **Quickstart is the product.** One command stamps a workspace; the manual's
  §5b flow becomes QUICKSTART.md with every step runnable as written.

## 4. Improvement candidates NOT in scope for v1 (tracked)

- Interactive `new_project.py --wizard` that fills BINDINGS by Q&A.
- Event-driven reviewer bridge (filesystem watcher instead of 5-min poll).
- Cross-platform heartbeat recipes (cron/launchd equivalents of the tick).
- A conformance test-suite ("protocol lint") a deployment can self-run.
