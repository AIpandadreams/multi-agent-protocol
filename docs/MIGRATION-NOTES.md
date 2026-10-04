# Migration notes — published protocol text

Dated notes for readers of the published commands when a batch changes what a command DOES, not only
what it says. Each note names the canonical lines it ports. Notes are appended as dated sections, never edited.

## 2026-09-20 — `/sleep` routes the head through the renderer; the REARM unit lands (steps 1b / 4b / 5b)

Public `/sleep` now routes every write of the volatile head — the ⚡ working-state block and the
`## Next Step` section — through the renderer, `tools/render_head.py <workspace> <role>` [canonical
`sleep.md` L60–63], and forbids hand-authoring the head: not the ⚡ block, not the `## Next Step`, not a
"small refresh", outside one bootstrap exception [L64–68]. A head that is still hand-authored (no `render_head` footer) migrates once via
`tools/render_head.py --adopt`, which demotes the old head byte-intact under a `####` historical heading
and renders the single new head [L69–73]. State a successor needs goes into the ledger
(`plans/*.plan.yaml` step status / evidence / clocks), then render — never into hand-written head prose
[L73–76]. Hand judgment lives in `## Standing judgment`, which the renderer never generates or modifies
[L77–78]. The same batch lands the three steps that are one mechanism: `/sleep` soft-lands everything
in flight first (step 1b [L22–53]) and writes `memory/<role>/REARM.md` so a restart survives (step 4b
[L182–215]); `/wake` re-arms from that file (step 5b [canonical `wake.md` L144–159]). Three deliberate
differences from the canonical text travel with this port and are recorded in `DECLARED-DELTAS.md`
(rows dated 2026-09-20): the renderer bullet's "step 3" cites a canonical step this file does not
carry, the ported step keeps its canonical number `4b` after the published step 3, and one phrase in
step 4b names a cloud-synced share generically where the canonical text names a vendor.
