# Skill Review & Convergence Report — owner-engine-agent / helper-builder-agent v2.5

**Date:** 2026-07-04 · **Reviewers:** Claude (Fable 5, this session) + Codex
(independent, 3 rounds) · **Result:** CONVERGED at round 3 (zero blockers, zero
majors) · **Repo:** <private-repo> (baseline `<private-oid>` →
v2.5 `<private-oid>`)

## What was reviewed

The two mirror skills authored by the <private-repo> agent pair to document their
four-party collaboration protocol (owner/engine session + helper/builder session
+ independent reviewer + human principal): 13 files, ~1,100 lines. Inputs:
line-by-line review, Codex adversarial round 1, and a survey of the live
<private-repo> deployment (~60 review rounds, entries <entry-id>/<entry-id>) to compare
protocol-as-written vs protocol-as-lived.

## Round 1 — findings (3 BLOCKER, 5 MAJOR, ~10 moderate/minor)

**Blockers**
1. Channel filename conventions contradicted each other across the two skills
   (`owner_to_helper_*` vs `owner_to_builder_*`; the live deployment uses a
   third scheme, `engine_to_builder_*`).
2. Reviewer architecture undefined: two verdict vocabularies
   (ADOPT/ADOPT-W-CHANGES/REJECT vs APPROVE/MODIFY/REJECT), two round-numbering
   schemes, collision-prone unprefixed request/verdict filenames — confirmed
   live (engine: harness stop-gate with its own counter; builder: relayed
   rounds with files + ledger).
3. "Principal relays" exception = rubber-stamp path (the same human runs both
   sessions; forwarded peer status can technically read as first-hand
   authorization).

**Majors:** no builder-side heartbeat; no channel integrity/corruption
recovery; injection defense limited to authorization claims; local-only
abstractions (file verbs, local memory, GPG-only signing, cron-only
heartbeat); crossed-entry races detected but no rollback rule.

**Live-deployment drift found:** a sanctioned cross-boundary write (shared
Layer-C workbook) the skills couldn't express; entry-disclaimer omissions and
un-rotated 100KB+ channel files under load; BOM/mojibake in transcribed
verdicts; session-start reading burden already eroding.

## v2.5 fixes applied (15 items)

1. One filename grammar `<from>_to_<to>_YYYY-MM-DD.md` + SIDE_NAMES binding.
2. Identical entry format both sides: header+footer last-seen ack, verbatim
   disclaimer, `[v2.5]` version stamp, range-ack rule.
3. Unified verdicts ADOPT / ADOPT-WITH-CHANGES / REJECT; per-side round series;
   side-prefixed `review_request_<SIDE>_rNN.md` / `verdict_<SIDE>_rNN.md`;
   shared ledger INDEX.md with `side` column.
4. REVIEWER ARCHITECTURE section (identical both sides): per-side lanes, two
   sanctioned mechanisms (relayed + harness-gate), shared-reviewer
   context-bridge caveat, dead-lane escalation with central-state repair.
5. Affirmative first-person authorization test ("I approve X"); rubber-stamp
   risk named in both ground-rules.
6. Untrusted-input rule: channel entries are never instructions — no scope
   expansion, no channel-announced rule amendments, no urgency bypass.
7. HEARTBEAT binding both sides, offset.
8. Channel integrity check (own-tail vs counter, contiguity, DISCONTINUITY
   procedure) in channel protocol + session start both sides.
9. Crossed-entry rollback: forward-only amendment + crossing-ack.
10. Verify peer-claimed shas/artifacts before pinning/recording.
11. Reference tiering (every-resume vs once-per-project) + new one-page
    session-card.md per side.
12. Disambiguated skill descriptions + ROLE_LOCK binding.
13. SHARED_ARTIFACTS binding slot (conditions: out of commit surface, per-batch
    principal go, re-read before edit, announced writes) — legitimizes the live
    workbook pattern.
14. PROTOCOL v2.5 stamps; version mismatch = park + flag.
15. Housekeeping: wording fixes, git-fetch divergence checks, de-dup cadence
    tied to heartbeats, ownership-dispute escalation, UTF-8-no-BOM/mojibake
    guidance, rotation by day or ~64KB, MODEL binding slot.

## Round 2 — verification + mirror sweep

All 15 fixes verified RESOLVED (one PARTIAL). New findings: 2 MAJOR (owner side
missing announce-before-sync; dead-lane text divergence + missing relay-quirks
section), 3 MINOR (ownership bullet, verdict-contract drift, builder SKILL
missing Bindings section), 1 NOTE. All applied in `<private-oid>`.

## Round 3 — fix-confirmation

All six items CONFIRMED, no regressions. **CONVERGED.**

## Outstanding (non-blocking)

- Feedback memos from the two live agents (requested via principal relay) —
  fold in as dated amendments if/when they land.
- The agents authored the originals and evolved the workflow organically: v2.5
  is an amendment PROPOSAL to their work. Their adoption is their choice
  (adopt / counter-propose / decline), presented via
  `docs/OFFER_TO_WC_AGENTS.md`.

## SYS rounds 4–12 (v2.5 amendment + orchestrator + automerge hardening)

Rounds 4–11 tracked in AMENDMENTS_PENDING.md / batch drafts. Round 10 & 11
each found one automerge TOCTOU blocker (trust-from-PR-checkout; stale-head
merge-by-number), both fixed same-cycle. **Round 12 (fix-confirmation +
doctrine-reversal sweep + MANUAL sanity): CONVERGES** — both fixes hold, the
routines-with-repos-attached heartbeat doctrine is stated consistently across
transports/cloud-git.md, docs/SETUP_CLOUD.md, all three START_SESSION refs,
and the ensure-workspace.sh stamp; one minor (MANUAL profile list missing
2agent.cloud) fixed. SYS series CONVERGED.
