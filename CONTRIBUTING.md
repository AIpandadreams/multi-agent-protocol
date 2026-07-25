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

A green scrub in step 2 covers less than it looks like it covers — read
[What a green scrub does not prove](#what-a-green-scrub-does-not-prove) before
you lean on it.

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
- No personal data, no real paths from your machine, no secrets. CI catches only
  the generic shapes — a Windows or Linux home path, a consumer email domain —
  because the scrub gate runs the placeholder pattern list. Anything specific to
  your organization is invisible to it: your own private list and the review are
  what catch those (below).

## What a green scrub does not prove

The scrub gate has two legs. `--private-path` is a fail-fast guard: if a
directory known to be private has been dragged into the tree at all, the scan
aborts before a file is read. The pattern list is the second, and
`release_scrub.py` takes it as an argument because what counts as private is a
property of your deployment, not of this protocol.

The list CI points at, `examples/scrub_patterns.example.txt`, holds twelve
patterns of two kinds. Everything organization-specific in it is a stand-in — a
generic personal name, a generic company, a generic repo handle — and matches
nothing real. Four are deployment-independent leak *shapes* that do fire on real
content: Windows and Linux home-directory paths, consumer email domains. So it
catches the generic accidents and is blind to everything specific to you.
Against this repo it passes because nothing here happens to match the stand-ins,
not because anything of yours was checked.

Read a green CI scrub as exactly this: `profiles/private` was not in the tree,
and none of twelve patterns matched the files the tool actually scanned — of
which only the home-path and email shapes could ever match real content. Scope
counts too: the tool prunes `.git`, `__pycache__`, `node_modules` and `.claude`,
skips files it treats as binary by extension, and silently skips files it cannot
read.

That is a real baseline, and it is not a clean bill of health. Before
publishing, run the gate with your own list — kept outside the repo, untracked —
and keep the named-path leg:
`python tools/release_scrub.py <tree> --patterns <your-list> --private-path <your-private-dir>`

This is written down because the failure was measured. A document carrying six
internal authorization ids, internal absolute paths, internal role names and one
person's name eight times returned `release_scrub: clean` at exit 0 under the CI
invocation above, and 5 of its 10 patterns matched when the same bytes were
scanned with a deployment-specific list. Correct invocation, real green, no
assurance about anything the list was never given.

The general form: **a gate's green must name its denominator — in its own
output, where the person reading it is looking.** `release_scrub.py` prints
`release_scrub: clean` and nothing else; what it compared against lives only in
the invocation, which this file happens to spell out in full above — so the
failure being cured here is a reading failure as much as a naming one. Making
the tool print its pattern count and source file on a clean run is a wanted
change.

(Drafting this section tripped the gate: quoting the example file's stand-in
tokens verbatim made this file match them — RELEASE BLOCKED, 2 hits. Take that
as the control it is. The gate demonstrably fires, so its greens are not inert.)

## Reporting problems

- Bugs / doc defects: open an issue with the bug template.
- Protocol design discussions: open an issue with the amendment-proposal
  template *before* writing the PR — design consensus first saves everyone
  a re-review.
- Security-sensitive reports: see [SECURITY.md](SECURITY.md) — not the
  public tracker.
