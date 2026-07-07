# Review protocol — owner side [PROTOCOL v2.6]

> **Tier: every-session.** The REVIEWER ARCHITECTURE and VERDICT CONTRACT live
> in ONE place: `../../agent-core/references/review-core.md` — read it before
> your first round of a session. This file adds the owner's setup, dispatch
> craft, and the defect classes rounds catch. The multi-round convergence cycle
> — four seats, round budget, adjudicating reviewer disagreement, anti-anchoring
> — lives in `../../agent-core/references/review-convergence.md`. Conflicts with
> review-core are bugs to report, and review-core wins.

Every commit is preceded by a review round from an independent reviewer
(REVIEWER binding — e.g. a Codex-class reviewer). The round is adversarial
verification of YOU — your own decisions are the highest-risk content in any
artifact.

## Setup (owner side)

- One long-lived reviewer lane per session; re-establish fresh each session
  rather than reusing a stale one.
- Instruct both delivery paths every round: verdict file (or ledger row for a
  harness-gate reviewer) AND a relayed summary. If the reviewer goes idle
  without relaying, message it to relay (known quirk: agents finish and idle
  silently) — then apply review-core's dead-lane escalation if still silent.
- The reviewer is READ-ONLY. If its sandbox denies even that, verdicts arrive
  as transcriptions — accept them, banner the transcription in the record.

## Dispatching a round

A dispatch contains:

1. **Exact file path(s) + version** under review, and what else is staged
   (ideally "sole working-tree change").
2. **One paragraph of frame** — what the artifact is, its parent doc, claims.
3. **Your own decisions/changes, listed explicitly**, with the ask to verify
   each against primary evidence.
4. **A numbered review-focus list**: parent-frame conformance; spot-check N
   citations against real sources; soundness of the core mechanism; discipline
   checks (propose-never-decide honored); data hygiene.
5. **The verdict ask** per review-core's contract.

Rounds may QUEUE: send round N+1 marked "queued behind round N". Keep the
pipeline full — draft the next artifact while a round runs.

## Defect classes rounds actually catch (pre-check these before dispatch)

1. **Back-propagation drift** — a later resolution contradicting the earlier
   table/summary it resolves. The most frequently caught class. After
   resolving anything, search the doc for every occurrence.
2. **Drafter false claims** — subagents assert verifiable things that are
   wrong. Flag every number-bearing agent claim for verification.
3. **Path-coverage misses** — a guard added to one code path, not its sibling.
4. **Stale-hedge language** — hedging surviving after the question was
   resolved elsewhere in the doc set.
5. **Citation imprecision** — cited locations that are comments/prose asserted
   as working code; block-vs-line drift; off-by-one pointers.
6. **Silent scope narrowing** — a "full" sweep that quietly bounded itself.
   State your frames explicitly so the reviewer can attack them.
7. **Ownership ambiguity** — two sections describing the same boundary with
   different owners; future implementers fork on it.
8. **Sibling-occurrence drift on reconciliation** — a correction applied only
   to the flagged line while the same fact, phrased the old way, survives
   elsewhere. Not done until a full-file search for the OLD phrasing returns
   only intentionally-kept hits, each with a keep-rationale. Ask the reviewer
   to run the same grep independently.
9. **Provenance/HEAD overclaim** — claiming all reads happened at one commit
   when drafting spanned a HEAD move; describe commit ranges by what `git log
   A..B` shows, never by what they "should" contain.

## After the verdict

- Probe SIGNING readiness (ops-gotchas pattern) → signed commit → push
  immediately (signing warmth is often time-boxed) → post the sha to the
  channel the same cycle (the peer verifies it exists before pinning).
- Commit message: conventional prefix, what shipped, round + verdict, any
  principal flag riding the commit.
