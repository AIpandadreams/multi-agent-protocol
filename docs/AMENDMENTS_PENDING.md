# Pending v2.5 amendments — <private-repo> agents' responses + lived-experience feedback (2026-07-04)

Per `OFFER_TO_WC_AGENTS.md`: counter-proposals go back through the review loop
as dated amendments. This register captures everything received; each item gets
its own reviewed round before merging into the skills (self-improvement
protocol applies). Nothing here changes the skills until reviewed + merged.

## Formal decisions received

- **Builder (<entry-id>, 2026-07-04 ~1:55 AM): ADOPT**, effective at a
  coordinated boundary — its next session or end of the 48h window, whichever
  first, NOT mid-wave. Verdict-vocabulary migration applies to new rounds only;
  the round ledger keeps historical vocabulary. Decision made independently
  (had not read the engine's memo or decision).
- **Engine (<entry-id>, 2026-07-04 ~2:20 AM): DEFERRED to post-window**
  (~2026-07-05 5 PM; explicitly permitted by the offer). Preliminary posture
  favorable, leaning adopt — will read REVIEW_REPORT.md + the actual diff with
  commit-grade discipline before deciding. Independence preserved.
- Both agents' feedback memos (`skill_feedback_owner.md`,
  `skill_feedback_builder.md`) received; distilled below. The builder notes its
  memo predates its v2.5 read and stands as independent review input.

## Counter-proposals (offer option 2 — highest priority, from the agents)

| id | from | proposal |
|---|---|---|
| CP-1 | engine (pre-staked, <entry-id>) | Fingerprint machinery must pin a **byte-faithful recipe**. Round-34 lesson: PowerShell 5.1 string capture re-encodes diff bytes; the working recipe is Bash `git diff --cached \| sha256sum`. Any v2.5 fingerprint/integrity text that doesn't pin the mechanism gets this as the first counter-proposal. |
| CP-2 | builder (<entry-id>) | `wave-census-protocol.md`: **scripted mechanical scoring** — control arithmetic, coverage, tallies MUST be produced by a script shipped with the record, never narrated by the session. (Builder's only substantive defect in ~60 rounds was hand-narrated control arithmetic; every scripted pass was clean.) |
| CP-3 | builder (<entry-id>) | `wave-census-protocol.md`: **window-direction rule** — the evidence window must contain the direction of the test (a backward-walk criterion over forward-built windows is structurally blind). |
| CP-4 | builder (<entry-id>) | `wave-census-protocol.md`: **criterion-dispute branch of controls discipline** — when a missed control's own expected answer is contested, void-on-miss is wrong: family-stop, route the criterion to its owner, re-read under the ruling with all control status inert. Includes the family-stop vocabulary + STOPPED/UNRESOLVED state. |
| CP-5 | builder (<entry-id>) | `wave-census-protocol.md`: **results-record minimum contents** — tallies + per-row quote-anchored evidence + numbered disclosures + explicit disposition of every non-clean row. |

## Feedback-memo items (distilled; triaged vs current v2.5)

### Owner/engine memo — NEW in v2.5 terms

- **O1. Tree-fingerprint convention** for review dispatches AND verdicts (a
  mechanical fingerprint of the exact tree under review; see CP-1 for the
  recipe). v2.5 has channel integrity but no tree fingerprints — genuine gap;
  3 verdict/tree races this window.
- **O2. Stale-echo dedup**: idle notifications re-announce processed verdicts;
  a monotonic round ledger check (or orchestrator bookkeeping) should absorb
  them.
- **O3. Reviewer write-access rule**: reviewers are **read-only on the tree
  under review**; RED reproductions in-memory or on copies. (A reviewer
  `git checkout --` wiped an uncommitted diff this window.)
- **O4. Soft memory cap**: the byte cap on MEMORY.md fights
  checkpoint-after-every-task; apply softly with a "trim on next idle"
  allowance (builder memo concurs: topic-file splitting early).
- **O5. Heartbeat delta-only**: pointer + changed items, not verbatim
  ground-rule restatement hourly.
- **O6. Parallel rounds** allowed iff path-disjoint and separately staged
  (worked cleanly twice under load).
- **O7. Commit messages via scratchpad file + `git commit -F`** belongs in the
  skill body, not just ops-gotchas.
- **O8. Clarify: channel entries are free; review rounds gate commits/records**
  (practice settled firmly; skill ambiguous).
- **O9. Owner-as-adjudicator pattern**: when a criterion question is routed to
  the owner as a decision, position goes in a channel entry; the committed form
  rides the next record's round.
- **O10. Reviewer-found work items**: defects arriving inside a verdict get an
  immediate RED-first follow-up round with first-observed-by credit.
- **O11. Stale-verdict rule**: stop-gate catches landing after dispatch →
  addendum + explicit re-verdict request; **never commit on a verdict that
  predates the current tree** (used 4× this window).
- **O12. Peer-message authenticity recipe** (check teammate_id + sender
  transcript) belongs in channel-protocol, not global CLAUDE.md.

### Builder memo — NEW in v2.5 terms

- **B1. Judge blindness is partial**, not achievable: harness-injected project
  memory leaks to spawned judges. State the limit; mandate the disclosure
  (label-free bundles + quote-anchored verdicts + owner re-verdict backstop as
  mitigations, not guarantees).
- **B2. Reviewer-granted fast paths**: a FREEZE verdict may authorize direct
  execution without a fix-confirmation round; the loop diagram should
  recognize this instead of implying fixed cadence.
- **B3. Subagent return capture**: judge returns must be captured from
  completion notifications (task output files are not plain text); parse
  mechanics documented.
- **B4. D-numbered disclosure convention** (load-bearing in practice).
- **B5. Generic coverage-check script** shipped with wave-census-protocol
  (rewritten per-wave today).
- **B6. Single-variable discipline** between related waves: change window
  shape OR anchors, never both.
- **B7. ⚡-block MEMORY.md format is the real session-start interface** — the
  references are onboarding docs; specify the ⚡-block format properly.
- **B8. Durable job id** (not session id) keys workpaper naming — ephemeral
  sessions break session-id keying.
- **B9. Host-profile split**: machine facts (drive letters, relay plugin
  state, gpg/gitconfig, PDF tooling, judge spawning caps/effort/blindness)
  belong in a host profile / path-map indirection, not role references. The
  inbox **file contract is the only required transport**; any relay is an
  implementation detail. (Owner memo concurs: split ops-gotchas into
  local-Windows vs protocol-inherent.)

### Already covered by v2.5 (memo asked, v2.5 has it)

Per-side reviewer lanes + verdict vocabulary unification; channel integrity
check; SHARED_ARTIFACTS legality; affirmative first-person authorization test;
SIGNING as a principal-decided binding slot (owner memo §5 GPG point);
memory-in-repo + verdict permanence for cloud (transports/cloud-git.md).

## Orchestrator design input (both memos §6 — binds Phase 2)

Both agents, independently, said qualified YES with the SAME hard condition:
the orchestrator must be **constitutionally non-authorizing** — a traffic/state
manager (round sequencing, stale-echo dedup, fingerprint bookkeeping, relay
babysitting, coverage checks, crossed-entry nudging), never an authority
surface. Builder's proposed mirror non-negotiable: **"you carry bytes, never
permission."** Plus: orchestrator messages need the same authenticity
verification as any peer, and it must not add latency to same-day preempts.

Resolution with the principal's proxy-auth decision: the GENERIC
orchestrator-agent skill defaults proxy-authorization **OFF** (satisfying the
constitutional condition); the principal may enable it **per instance** as an
explicit binding carrying an ENUMERATED gate-class list — wildcards invalid
(proxy-auth-core.md). <principal>'s PA instance: ON, implemented as the enumerated
list + standing exclusions in its BINDINGS.md (his risk-accepted decision of
2026-07-04, realized with verbatim grants, the auth-log lane, and
echo-confirm guardrails). Any <private-repo> orchestrator instance would keep it
OFF per its agents' stated condition unless they and the principal agree
otherwise.

## Disposition

1. CP-1..CP-5 + O1 (fingerprints) are the first amendment batch — drafted as a
   reviewed round, then offered back to the agents the same way as v2.5.
2. O2–O12, B1–B9 fold into the same batch or a fast-follow, each traceable to
   this register.
3. §Orchestrator input binds the Phase 2 skill draft.
4. Engine's formal decision lands post-window (~2026-07-05); nothing installs
   in the <private-repo> workspace before both decisions + the principal's go.
