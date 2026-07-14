# Contributing

Thanks for wanting to improve the protocol. This repo eats its own
dogfood: **changes to protocol files go through the same review discipline
the protocol prescribes.**

## The short version

1. Fork, branch, make your change.
2. All three gates must be green — CI runs exactly these:
   `python tools/mirror_check.py` ·
   `python tools/release_scrub.py . --patterns examples/scrub_patterns.example.txt --private-path profiles/private` ·
   `python -m unittest discover -s tests`
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
artifact set:   <every file this amendment governs, INCLUDING co-maintained
                 counterparts you did not need to change — a doc and its rendered
                 twin, a schema and its generated types, a value that must agree
                 across two manifests. Twins fail as a pair.>
omission search: <what should have changed under this amendment and did not?
                 "none — searched X, Y, Z" is valid; silence is not>
files touched:  <list — the subset of the artifact set you actually edited>
principal-locked paths touched: <none | list + justification>
version impact: <none | bump to vX.Y because …>
fingerprint:    <base + set digest (--error-unmatch errors on an untracked member;
                 the pipefail guard makes that failure propagate — sha256sum alone
                 masks it as exit 0):
                 ( set -o pipefail; git rev-parse HEAD && git ls-files -s --error-unmatch -- <artifact set> | sha256sum )>
```

`artifact set` and `files touched` are deliberately two fields. A review scoped
to what you touched is structurally incapable of reporting what you FORGOT to
touch — and an omission ships as silently as a bad edit. (This header itself
once asked only for `files touched`, and a release nearly shipped a doc whose
co-maintained HTML twin still showed the old content.)

The fingerprint pins what was reviewed — if you push more commits after a
review, the review is void and re-runs on the new bytes. (Yes, this is the
protocol's own review-round rule applied to its own repo.) It digests the SET,
not the diff: an unchanged twin contributes no diff bytes, so a `git diff` digest
is identical whether or not the twin is in the bundle — it cannot pin the members
the `artifact set` field exists to add.

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
