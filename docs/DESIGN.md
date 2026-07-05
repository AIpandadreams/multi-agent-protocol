# Design notes — what's proven, what's simplified, what's next

This release is a distillation, not a prototype. This page records what
the released subset is distilled *from*, so you can judge which guarantees
are evidence-backed and which are engineering judgment.

## Provenance

The protocol began as the organically-developed working agreement of a
two-agent pair (owner + builder) collaborating on a long-running
production project, written down by the agents themselves. That draft then
went through an independent cross-vendor review loop — every protocol file
adversarially reviewed by a different vendor's model, every blocking
finding fixed and re-reviewed — across **twelve review rounds** before and
during live deployment. The orchestrator role and the auth-log lane were
added in that reviewed lineage, not bolted on.

## Evidence behind the core claims

| claim | how it was tested |
|---|---|
| a cold successor resumes from the ⚡ block + channel alone | pilot: sessions killed mid-unit across a full multi-session cycle (dispatch → build → review → adopt), successors resumed with zero integrity violations; the workspace's commit history replayed clean |
| the review gate catches real defects | review rounds found, among others, two time-of-check/time-of-use vulnerabilities in trust-control tooling — before that tooling ever ran unattended |
| the auth-log lane resists double-spends | the exactly-one-landed-CONSUMED rule is validated mechanically, globally across logs, in CI; race behavior (push contention on the reservation) is part of the design, not an accident |
| channel discipline survives long collaborations | the 2-agent configuration ran 50+ working rounds on production work under the ancestor protocol |
| append-only + monotonic-state CI catches tampering | CI checks fire on every push of every workspace; the checks fail closed (an unenumerable diff is a failure, not a pass) |

## What this release deliberately simplifies

- **PROXY_AUTH ships off.** It is the most complex subsystem and most
  deployments never need it — first-hand approval in whichever session
  asks is simpler and equally safe. The lane is fully included and
  documented for when the relay round-trip becomes a real cost.
- **Local transport only.** The upstream system also runs a cloud
  transport: scheduled cold-successor wakes over git, workers publishing
  state via branch → PR → integrity-gated automerge (with base-sha trust
  evaluation, protected-path guards, and head-pinned merges — the two
  TOCTOU findings above are from hardening exactly that path). It is
  excluded here because it depends on a hosting platform surface that is
  still moving; releasing a recipe that stops matching the platform would
  be worse than a roadmap line.
- **Wave census is an appendix.** Powerful for large evidence jobs,
  irrelevant to a first deployment.
- **One worked reviewer path.** The protocol only requires "independent
  reviewer"; the tooling ships the Codex bridge because it's the path with
  the most miles on it.

## Known gaps (v1)

Honest list — these are real, and PRs are welcome (see
[CONTRIBUTING](../CONTRIBUTING.md)):

1. **BINDINGS onboarding.** ~10 slots with a glossary is a wall for
   newcomers. Softened by `new_project.py --wizard` (interactive slot
   fill); a guided glossary in-wizard could go further.
2. **Review latency.** The poller defaults to a 5-min poll loop; its
   `--watch` mode (a stdlib directory-signature watcher) closes local
   latency to a couple of seconds. A true OS-level filesystem watcher
   (inotify/ReadDirectoryChangesW) remains a possible refinement.
3. **Reviewer coupling.** The worked path assumes a local Codex CLI on the
   same machine.
4. **Windows-first tooling edges.** The protocol is OS-neutral; some
   heartbeat recipes and ops-gotchas examples carry a Windows accent.
5. **Conformance depth.** `tools/conformance_check.py` self-verifies a
   workspace's structure, bindings, PROXY_AUTH guard, and auth-log chain;
   deeper semantic checks (e.g. TASKQUEUE/DUTIES agreement) could still grow.

## Design stances (won't change)

- The principal's irreversible gates are not bindable away — no
  configuration exists in which an agent, on its own say-so, does any of the
  first-hand-only super-classes: outward-facing/publish actions, email SEND,
  new-money/new-recipient financial actions, destructive operations on another
  party's artifacts, canonical-repo merges, or changes to PROXY_AUTH / gates /
  embargoes / the protocol.
- The reviewer is a party, not a feature flag.
- Coordination state is append-only. Convenience never justifies editing
  history.
- Bindings over examples: the protocol will keep refusing to hardcode
  anyone's paths, cadences, or models — including ours.
