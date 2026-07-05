# Contributing

Thanks for wanting to improve the protocol. This repo eats its own
dogfood: **changes to protocol files go through the same review discipline
the protocol prescribes.**

## The short version

1. Fork, branch, make your change.
2. `python tools/mirror_check.py` must be green (CI enforces it).
3. Open a PR. For **protocol-file changes** (anything under
   `plugins/agent-protocol/`), include a filled amendment header (below).
4. Protocol changes get an independent review round before merge; docs and
   tooling changes get a normal review.

## What kind of change is it?

| change | path | bar |
|---|---|---|
| docs, examples, typos | `docs/`, `README`, `examples/` | normal PR review |
| tooling | `tools/` | normal review + the tool's own test/demo run in the PR description |
| **protocol** | `plugins/agent-protocol/**` | amendment header + independent review round + version-stamp discipline |
| authorization/gate rules, hard-rails sections | — | **not accepted from agents in any deployment, and PRs here get extra scrutiny**: these lines are the security boundary. Expect a slow, careful review |

## Amendment header (protocol PRs)

Paste at the top of the PR description:

```
AMENDMENT
problem:        <the defect or gap, ideally with a reproduced example>
files touched:  <list>
principal-locked paths touched: <none | list + justification>
version impact: <none | bump to vX.Y because …>
fingerprint:    <output of: git diff main...HEAD | sha256sum>
```

The fingerprint pins what was reviewed — if you push more commits after a
review, the review is void and re-runs on the new bytes. (Yes, this is the
protocol's own review-round rule applied to its own repo.)

## Conventions

- Keep the mirror invariants: role skills are thin deltas over
  `agent-core`; don't duplicate core rule blocks into role files
  (`mirror_check.py` will fail you).
- Every protocol file carries a `[PROTOCOL vX.Y]` stamp; new files too.
- Write like the docs write: complete sentences, evidence over adjectives,
  and when a rule exists because something broke, say what broke.
- No personal data, no real paths from your machine, no secrets — CI
  secret-scans, and reviews look for the rest.

## Reporting problems

- Bugs / doc defects: open an issue with the bug template.
- Protocol design discussions: open an issue with the amendment-proposal
  template *before* writing the PR — design consensus first saves everyone
  a re-review.
- Security-sensitive reports: see [SECURITY.md](SECURITY.md) — not the
  public tracker.
