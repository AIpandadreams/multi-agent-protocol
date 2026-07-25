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
- No personal data, no real paths from your machine, no secrets. CI catches a few
  generic shapes and nothing more — roughly, a path under the `C:` drive's users
  folder, a `/home/` path, a gmail or yahoo address — because the scrub gate runs
  the example pattern list. A macOS home path, a users folder on any other drive,
  most other mail domains, and anything specific to your organization are all
  invisible to it: your own private list and the review are what catch those
  (below).

## What a green scrub does not prove

The scrub gate has two legs. The pattern list is one, and `release_scrub.py`
takes it as an argument because what counts as private is a property of your
deployment, not of this protocol. `--private-path` is the other: after the
pattern list is loaded, it checks whether a path known to be private — a
directory or a single file — has been dragged into the tree, and if one has,
aborts before the scan reads any release content.

The list CI points at, `examples/scrub_patterns.example.txt`, holds twelve
patterns of two kinds. Eight stand in for organization-specific strings — a
generic personal name, a generic company, a generic repo handle — and match no
real organization's identifiers. The other four are deployment-independent leak
*shapes* that do fire on real content, but narrowly — roughly: a path under the
`C:` drive's users folder; a `/home/` path; a gmail address; a yahoo address.
Against this repo it passes because nothing here matches any of the twelve — not
because anything of yours was checked.

Read those descriptions as approximations. Each is a regex, and prose cannot
pin a regex's edge: a `/home/` path is caught only when the next component
starts with a letter, so one starting with a digit or an underscore is not,
and the two mail patterns have no end anchor, so an address whose domain begins
with a named provider and continues past it is caught, while one where the
provider appears only after a prefix label is not. The list is in the tree at
the path above — open it when the answer matters. Measured, for the cases
likeliest to mislead: a macOS `/Users/` path, a users folder on any drive but
`C:`, and an address containing neither token all pass clean.

(This section cannot quote the list's contents without matching them. Drafting
it tripped the gate twice — once on the stand-in tokens, once on a Windows home
path written out in full — which is why the shapes above are described rather
than spelled. Take that as the control it is: the gate demonstrably fires, so
its greens are not inert.)

Read a green CI scrub as exactly this: `profiles/private` was not in the tree,
and none of the twelve patterns matched the files the tool actually scanned.
Scope is part of that claim: the tool prunes `.git`, `__pycache__`,
`node_modules` and `.claude`, skips files it treats as binary by extension,
silently skips files it cannot read, and excludes the patterns file itself from
the scan — which is why pointing CI at a list living inside the scanned tree
comes back green rather than permanently self-matching red.

That is a real baseline, and it is not a clean bill of health. Before
publishing, run the gate with your own list — kept outside the repo, untracked —
and keep the named-path leg:
`python tools/release_scrub.py <tree> --patterns <your-list> --private-path <a-path-that-must-not-exist>`

This is written down because the failure was measured. A document carrying six
internal authorization ids, internal absolute paths, internal role names and one
person's name eight times returned `release_scrub: clean` at exit 0 under the CI
invocation above, and 5 of its 10 patterns matched when the same bytes were
scanned with a deployment-specific list. Correct invocation, real green, no
assurance about anything the list was never given.

The general form: **a gate's green must name its denominator — in its own
output, where the person reading it is looking.** `release_scrub.py` prints
`release_scrub: clean` and nothing else. The invocation names the root, the
pattern source and the named private paths; the implementation supplies the rest
— the pruned directories, the skipped binaries, the files it could not read, the
patterns file's own exclusion. That the invocation is spelled out in full above
is why the failure being cured here is a reading failure as much as a naming
one, and making the clean line report its pattern count and source is a wanted
change.

## Reporting problems

- Bugs / doc defects: open an issue with the bug template.
- Protocol design discussions: open an issue with the amendment-proposal
  template *before* writing the PR — design consensus first saves everyone
  a re-review.
- Security-sensitive reports: see [SECURITY.md](SECURITY.md) — not the
  public tracker.
