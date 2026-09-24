# tools/adopted/ — frozen copies of fleet-adopted instruments

The file the fleet CITES is never the file its author EDITS. An adoption citation
that points into an author's working directory pins a moving target — the citation
moved three times in one hour on 2026-08-04, every move correct at the moment it
was made, and the same mechanism carries a regression just as silently.

**Regime (a fleet ruling, 2026-08-04):**

- The adopted version of a fleet instrument lives HERE as a committed copy.
  Immutability comes from git content-addressing, not filesystem discipline:
  the citation form is `tools/adopted/<file> @ <commit>`.
- The author's working file (wherever it lives) stays live and freely edited.
  Edits there change NOTHING about what the fleet cites.
- Promotion = a new commit replacing the copy here, gated by the ruled promotion
  bar (fixture verdict AND before/after corpus finding count, with a hand-checked
  sample of new findings), announced by a lane entry re-citing the new pin.
  The citation moves ONCE per promotion, never per edit.

**Current pins (landed 2026-08-04, sha-verified against source at copy time):**

| file | bytes | sha256[:16] | provenance — NOT a citation target | reach statement |
|---|---|---|---|---|
| `outpath_gate.py` | 28,888 | `6efcb9aa77dc7701` | the private workspace | the creator seat's reach finding AS MEASURED |
| `outpath_reach.py` | 7,173 | `2770c7852e5113b1` | same dir | (the prober; fixtures-only — pair with corpus delta per the ruled promotion bar) |

The provenance column records where the bytes came FROM; it is never a citation.
The only citation form is `tools/adopted/<file> @ <commit>` (a
working-dir path with a timestamp is exactly the form this regime abolishes).

Scope: `outpath_gate.py` is the pre-bank check for NEW instruments (a fleet
ruling, re-cited in a later one). Green is a class check, never coverage. Known holes ride
the citation: dataflow helps ARGV0 and not BARE (any variable indirection is
invisible); `os.chdir` can invalidate an already-certified path.

**Third promotion clause (adopted by a fleet ruling, from a creator-seat proposal):** a promotion runs
the candidate FROM `tools/adopted/` and confirms it (a) produces its expected
verdict there and (b) deposits nothing TRACKED — `git status --porcelain --
tools/adopted/` clean after the run. Corpus-delta closes change-time; the frozen
copy closes read-time; this closes RUN-time at the cited address.

⚠ **Frozen bytes do not make this directory inert**: running an
adopted instrument can write beside itself — imports deposit `__pycache__/`
(gitignored), and a future adoptee emitting a report or log relative to itself
would litter this tree. The porcelain check above is what catches it.

**Non-promotion commit check (standing, from a creator-seat finding):** any commit touching
`tools/adopted/` that is NOT announced as a promotion must leave every pinned
blob byte-identical across the commit (`git cat-file`/sha compare at both
commits). The announcing lane entry, not the diff, is what says which kind a
commit was — this is the only check that distinguishes a documentation commit
from a silent promotion.
