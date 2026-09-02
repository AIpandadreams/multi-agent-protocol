# A worked cycle — dispatch → build → review → adopt → cold successor

A condensed, sanitized transcript of one full unit moving through a
3-agent local deployment, including a mid-unit session kill. File contents
are excerpts; the shapes are exactly what the protocol produces. Project:
`demoproject`; sides bound as `orch` / `owner` / `builder`.

## 0. The ask

The principal, to the orchestrator session:

> "Have the team produce a dependency-risk report for the api/ directory —
> anything unmaintained or pinned to something ancient."

The orchestrator queues it and dispatches:

`TASKQUEUE.md` (row appended):

```
| T7 | YYYY-MM-DD | principal | dependency-risk report for api/ | dispatched → builder |
```

`channel/orch_to_builder_YYYY-MM-DD.md` (entry appended):

```
## ORCH ENTRY <n> [v3.2] — YYYY-MM-DD — dispatch T7: dependency-risk report for api/ (latest BUILDER entry seen: <m>)

Nothing in this entry is or carries the principal's authorization.

**1.** Task T7: produce a dependency-risk report for api/ (unmaintained or
ancient-pinned deps). Deliverable: report file in the canonical repo per
SIGNING rules, review round before adoption.

*— orch session, YYYY-MM-DD 14:05 -0500 (Entry <n>; latest builder entry seen: <m>)*
```

*(`<n>`/`<m>` are placeholder tokens in the two grammar positions; in the demo
run they were the small integers the rest of this story uses — the orch lane at
entry 3, the builder's latest at 2. Examples in this repo mint non-mintable id
shapes only — see CONTRIBUTING, Conventions.)*

*(Round numbers are placeholders too: `rNN` is the round this story opens on and
`rNN+1` its successor. The demo run used the small integers a first review cycle
produces; nothing in the protocol keys on the value, only on the succession.)*

## 1. Build

The builder session picks the entry up on its next poll, works the unit,
and stages the deliverable on a branch in the canonical repo. It
checkpoints BEFORE requesting review — `memory/builder/MEMORY.md`:

```
## ⚡ working state
next channel entry: 4 · last seen: orch 3, owner 5
next review round: rNN
in flight: T7 report staged on branch t7-dep-report (2 commits)
## Next Step
Post review_request_builder_rNN for t7-dep-report; fingerprint first.
```

## 2. Review round

`channel/review_request_builder_rNN.md`:

```
# review request — builder rNN [PROTOCOL v3.2]
artifact set:    docs/dep-risk-api.md · docs/dep-risk-api.html (rendered twin,
                 UNCHANGED — twins fail as a pair) · data/deps.lock (the input
                 the report's claims are derived from, unchanged)
omission search: searched for other surfaces naming a dependency risk —
                 README dep table (no risk claims, unaffected), SECURITY.md
                 (points at the report, no restated facts). None missed.
files touched:   docs/dep-risk-api.md
environments:    no runnable execution environment — a prose report and its
                 rendered twin over a lockfile; nothing executes (a consumer
                 pipeline reading the lockfile would bring one)
fingerprint ( set -o pipefail; git rev-parse HEAD && git ls-files -s --error-unmatch -- <the set above> | sha256sum ):
  base 4f2ab19 · set 9c1e6d2a…{64 hex}…f4
asks: verify every claimed unmaintained dep against its actual repo
activity; flag any risk claim without a cited source.
```

The artifact set names two files the round did not touch. That is the point: a
reviewer handed only `docs/dep-risk-api.md` can tell you whether the file is
wrong, but never that the rendered twin beside it still shows last week's
numbers. And the fingerprint digests the SET rather than the diff — an unchanged
member emits no diff bytes, so a diff digest cannot pin it.

The reviewer (a Codex-class second-vendor CLI, via the poller) answers in
`channel/verdict_builder_rNN.md`:

```
# verdict — builder rNN
fingerprint checked: MATCH
findings:
  [major] dep `oldxml` claimed "abandoned" — repo shows a release 4 months
  ago. Recheck or reword with the evidence.
  [minor] two risk rows lack version-pin citations.
uncheckable premises: that data/deps.lock reflects the environment the
  report's consumers actually deploy (no runnable environment in the set to
  regenerate it); repo-activity reads are as of this round's date.
verdict: ADOPT-WITH-CHANGES
```

…and the round lands in the shared round ledger — `channel/INDEX.md`, the
builder appending its own side's row only:

```
| rNN | builder | RESULTS | review_request_builder_rNN.md | verdict_builder_rNN.md (poller-written) | ADOPT-WITH-CHANGES — 1 major (oldxml recheck), 1 minor (pin citations) | fixes committed | rNN+1 |
```

## 3. The kill (this is the interesting part)

The builder fixes the findings, commits — and the session dies before it
can post the fixed-round request. Nothing is lost, because the ⚡ block
was updated at the checkpoint boundary:

```
## ⚡ working state
next review round: rNN+1 (rNN = ADOPT-WITH-CHANGES, fixes committed,
  NOT yet re-requested)
in flight: T7 — awaiting re-review
## Next Step
Fingerprint t7-dep-report (post-fix) and post review_request_builder_rNN+1.
```

## 4. Cold successor

A fresh session, no context, in the workspace directory:

```
/wake builder
```

The wake report:

```
☀️ AWAKE — builder @ demoproject-ws [PROTOCOL v3.2]
State: entry 4 next · round rNN+1 next · T7 in flight (fixes committed,
  re-review pending)
Channel: clean (orch 3, owner 5 acked)
Next step: Fingerprint t7-dep-report (post-fix) and post
  review_request_builder_rNN+1.
```

It does exactly that. rNN+1 comes back `ADOPT`, fingerprint MATCH.

## 5. Adoption and closure

Adoption of work into the canonical repo is the owner's call under the
SIGNING binding — the builder posts the converged round to the channel;
the owner merges (or, where the binding requires it, the principal does)
and records the decision. The orchestrator closes the loop:

```
| T7 | … | done — adopted rNN+1, merged by owner, report at docs/dep-risk-api.md |
```

…and T7 appears in the principal's next briefing with the round history
one line long: `rNN AWC → rNN+1 ADOPT`.

## What to notice

- Authorization never appeared in the channel — the dispatch carried the
  task, the SIGNING binding + owner's gate governed the merge.
- The reviewer disagreed with the builder *and was right*; the round
  history preserves that permanently.
- The session kill cost nothing: the checkpoint discipline (⚡ block +
  exact `## Next Step`) made the successor's first action unambiguous.
- Every artifact above is a plain committed file you can read later —
  the audit trail IS the coordination mechanism, not a byproduct.
