# Reviewer convergence loop — builder side [PROTOCOL v2.8]

> **Tier: every-session.** The REVIEWER ARCHITECTURE and VERDICT CONTRACT live
> in ONE place: `../../agent-core/references/review-core.md` — read it before
> your first round of a session. This file adds the builder's round mechanics,
> round types, and honesty disciplines. The multi-round convergence cycle —
> four seats, round budget, adjudicating reviewer disagreement, anti-anchoring
> — lives in `../../agent-core/references/review-convergence.md`. Conflicts with
> review-core are bugs to report, and review-core wins.

Every builder job passes through the independent reviewer (REVIEWER binding —
e.g. Codex driven through a background relay agent). The loop matters because
it is the only adversarial check on work the owner will consume as input:
treat it as a peer gate, not a rubber stamp — its catches have included
factual confabulations, definitional errors in baselines, control designs
that couldn't fail, and stale wording contradicting adopted decisions.

## Round mechanics (builder side)

1. **Write the request file** in the shared inbox:
   `review_request_<SIDE>_r<NN>.md` (your side's series, per review-core). The
   request states: round type, crossed-round state (latest counterpart entries
   seen, latest ledger row), the **artifact set** under review (paths — the
   artifact set, NOT merely the files you touched: name co-maintained twins even
   when unchanged, and record your omission search — *what should have changed
   and didn't?*; then list the touched subset separately), the artifact's
   **execution environments** (which this round actually executes, which stay
   UNEXECUTED with the residual risk named — review-convergence's
   environment-coverage rule; "none — prose only" is a valid enumeration), an
   execution summary, any mandated disclosures, and **numbered questions** the
   reviewer must answer with explicit per-question verdicts.
2. **Launch the relay** as a background subagent so you keep working during
   review latency. The relay prompt names: the request file to read first,
   every file to read, what to verify independently (arithmetic, claims vs
   artifacts, discipline checks), the standing constraints (read-only; changes
   LISTED; the relay itself adds no editorial severity of its own and never
   renames the owner-owned vocabulary — reviewer-emitted severity tags pass
   through verbatim), and review-core's verdict output contract including the
   write-fallback chain.
3. **Adopt the verdict:** apply every required change (in-place for pre-freeze
   drafts; by dated amendment for anything already frozen/reviewed), then
   record the round in the ledger (your side's rows). Verdict transcriptions are
   shared files — the file-hygiene baseline (UTF-8 without BOM, byte-gated) is in
   `../../agent-core/references/channel-core.md`; repair mojibake before the file
   is cited anywhere (ops-gotchas).
4. **Blockers** ⇒ the next round is a fix-confirmation round scoped to the
   blockers, not a results round.

## Round types

- **FREEZE** — reviews a spec before any execution. Nothing the spec governs
  may run until the reviewer clears execution. Freeze rounds routinely add
  controls (that is their job); adopt them rather than defending the draft.
- **RESULTS** — adjudicates an executed job's record against its frozen spec.
  Mandated disclosures (your own errors, adjudication layers you added,
  convention deviations) are listed IN the request — hiding one voids the
  round's value.
- **FIX-CONFIRMATION** — narrow round verifying that named blockers were
  fixed. Keep it scoped; don't smuggle new material in.

## Disciplines that keep the loop honest

- **One round in flight at a time on your lane.** Use latency for the next
  job's drafting, memory checkpoints, and channel intake — never for starting
  an execution that isn't cleared.
- **Crossed-round catches:** the reviewer may observe counterpart-channel
  movement you haven't seen. Treat that as a feature; reconcile before acting.
- **Independent verification requests:** always ask the reviewer to re-derive
  key arithmetic and claims from the artifacts, not from your summary. Its job
  is to catch you.
- **Your errors are round material.** Self-caught defects get disclosed at the
  next round with the dated amendment; reviewer-caught defects get fixed,
  recorded, and credited — the honest record is the product.
