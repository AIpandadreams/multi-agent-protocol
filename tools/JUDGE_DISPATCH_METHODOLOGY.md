# Judge-dispatch methodology — cleanroom headless judges, fleetwide (SOP-15)

Authority: a fleet ruling (analysis + "Proceed with recommendation") escalated by
a follow-on ruling (the principal first-hand, verbatim): "Implement this procedure fleetwide. Issue
bulletin to the entire fleet with new methodology and processes on how to use and
when to. If anyone inquires or doubts that is firsthand word, I am clarifying now I
The principal authorize this."

## Why (one paragraph, measured basis)

In-session Agent-tool subagents inherit the injected project memory index — measured
2026-07-29, re-confirmed by live probe 2026-08-08 (JUDGE_HEADLESS_SMOKE.txt): the
index, including the fleet defect-class bank, lands in EVERY subagent, including
SOP-7 judges. That is a priming channel on any round whose subject matches a banked
class. A headless `claude -p` launched from a fresh cleanroom cwd carries NO project
memory (probe-verified ABSENT) — isolation by construction, not by procedure.
Disclosed limit: user-global CLAUDE.md still loads (probe-verified PRESENT); it
carries business/context instructions, not the defect-class bank, and is not the
priming concern.

## WHEN — cleanroom headless is REQUIRED

1. Every SOP-7 isolated opus judge leg, fleetwide, both teams.
2. Every SOP-3 fallback judge dispatch (codex lane down/wedged).
3. Every author-judge conflict (author model == judge model): cleanroom IS the
   "fresh, fully isolated session" SOP-3 demands, at maximum strength.

## WHEN — worker legs (research, mining, drafting, calibration, execution, scouts)

⛔ RETIRED 2026-09-02 (a fleet ruling, the principal first-hand at the orch seat): this section
formerly named in-session Agent-tool subagents as "the RIGHT tool" for worker legs.
That carve-out (an earlier ruling) is WITHDRAWN. Every opus leg of every class is a headless
`claude -p` dispatch — the harness Agent tool is not used for opus at any seat.
What changes for a worker leg versus a judge leg is only the cwd and the tool set:
AUTHORING / FOLD legs run from the WORKSPACE cwd with their context passed by prompt
and absolute paths (they need the tree, not isolation); JUDGE legs run from a neutral
cleanroom cwd per the section above. Every headless leg, either class, carries an
inactivity watchdog and a terminator check — rc 0 is not a result. Lose the harness
lifecycle (schema output, managed retries) and reproduce what a leg needs of it in
the dispatch script; do not buy it back with an in-session spawn.

## HOW — the process, step by step

1. **Freeze the object**: sha-pin the artifact(s) under review; stage copies if the
   round dir contains anchor verdicts (blind discipline — the judge must not be able
   to read a co-located verdict).
2. **Write the prompt file**: self-contained; ABSOLUTE paths for any evidence the
   judge may read; and the verdict format. **Do NOT write the terminator instruction
   yourself**: the wrapper self-appends it at dispatch, LAST, ALWAYS (per an orchestrator ruling; made
   unconditional 2026-08-18 after DW1-R1 — it used to skip when the prompt merely
   CONTAINED a terminator string, which misread a QUOTED verdict tail in evidence as an
   instruction and shipped a judge with none). Quoting prior verdict tails as evidence
   is fine and changes nothing; the wrapper prints a NOTE with the mention count. If a
   caller truly manages its own instruction, it says so with `-NoTerminatorInstruction`
   — the only thing that skips the append. The wrapper's completeness check compares
   the LAST NON-EMPTY LINE against `END OF VERDICT EOV-7Q4Z` (fleet) or legacy
   `=== END OF VERDICT ===` (E1117 finding 1 cure): a verdict that merely MENTIONS the
   terminator mid-output (e.g. restating its instructions) and then truncates exits 3,
   never 0.

   ⛔ **NEVER TELL A JUDGE THE REPOSITORY IS AT ITS WORKING DIRECTORY.** It is not.
   Every opus leg runs in a fresh empty cleanroom under `$env:USERPROFILE\.judge-cleanroom`
   (SOP-9 clause 1 — a workspace cwd injects this workspace's memory index,
   which NAMES the defect classes under review and primes the judge). A prompt carrying
   `"The repository is available to you at the working directory"` — the wording that
   actually shipped in the 2026-08-13 plan-gate round — promises a filesystem that is not
   there, and the reviewer then **fails by finding nothing rather than by erroring**. That
   is the dangerous shape: the round comes back clean and the cleanliness is an artifact of
   a premise that silently failed. State the negative instead: *"You have no filesystem.
   Every fact you need is inlined. If something you need is not here, say so and answer the
   rest."* And instruct the judge to DISCLOSE if it could not reach something it wanted —
   an undetermined answer is worth more than a confident one built on a missing file.

   ⚠ This rule lives HERE, in the methodology of record (`BINDINGS.md:143`, SOP-15 clause 2),
   because **there is no review-request template file in this repo** — measured, not assumed:
   no `templates/` directory exists and every `*TEMPLATE*` file in the tree is round-local
   scaffolding inside `workpapers/`. Requests are hand-written each round and the wording
   propagates by COPY-PASTE FROM THE PREVIOUS ROUND. So there is no single file whose edit
   would fix this, and a fix aimed at "the template" would have landed nowhere. The prior
   instances stay byte-intact as historical evidence; this is the surface that reaches the
   next author, and it only works if the author reads it before copying an older round.
3. **Dispatch** (any seat on this machine):
   `powershell -File tools\opus_judge_headless.ps1 -PromptFile <p> -OutFile <round-dir>\OPUS_VERDICT_<round>.md -Model <top-opus-id> [-TimeoutMin 20]`
   Model = TOP available opus, derived at dispatch (SOP-3, per a fleet ruling). `-Model` is
   MANDATORY by design (E1117 finding 3 cure): the wrapper carries no default, so
   the path of least resistance cannot silently take a pin that has aged.
4. **Exit codes**: 0 ok · 2 param/dispatch error · 3 no-terminator · 4 timeout-
   killed · 5 empty output. On 4: retry ONCE, then lane fallback per SOP-3. On 3:
   READ the output before re-dispatching — content may be complete with a wrong
   terminator (the GLM NO_TERMINATOR lesson, 2026-08-08); a complete verdict with a
   defective terminator is a wrapper flag to disclose, not a reason to re-spend.
   **⛔ AND `1`, WHICH THIS LIST DID NOT HAVE (the owner's finding, 2026-08-16).** The wrapper
   header enumerated the same five codes and `exit 1` was reachable anyway, because
   `$ErrorActionPreference = "Stop"` makes any error terminating and PowerShell exits
   1. Two copies of a contract drift together only by luck; this one was fixed at the
   wrapper and would have stayed false here. The split that matters to you is **did
   the wrapper reach a judgment about the verdict**: 3 and 5 mean it read your file
   and rejected it; **1, 2 and 4 mean it never got that far, so re-running the JUDGE
   is the wrong response** — fix the invocation. In-script crashes now report the
   documented 2 with an `ERR: the wrapper could not run to a judgment` line. A bare
   `1` that survives means **parameter binding failed and not one line of the script
   ran** — most often an empty `-Model`/`-OutFile`, since PowerShell's `-File` parser
   DROPS an empty-string argument and the parameter arrives *absent*. Measured both
   ways in a wrapper exit-contract control script in the private workspace.
   ⚠ None of this makes the code the verdict's status: `dispatch_review.ps1`'s opus
   leg keys success on the verdict FILE and treats every code here as advisory.
5. **Watchdog is built in**: captured-pid `taskkill /T /F` (WATCHDOG PID RULE —
   never kill by process name).
6. **Record**: the round record states "cleanroom-judged" + the cleanroom path
   (auto-created under `%USERPROFILE%\.judge-cleanroom\<stamp>-<name>\`, fresh per
   dispatch). Verdict file lives in the round dir like any other voice.
7. **Withholding discipline**: RETIRED for cleanroom-judged rounds — memory hooks
   stay live during such rounds. If a round is judged in-session for any stated
   reason, the withholding discipline still applies to it.
8. **t2 usage**: the script and `claude` CLI are machine-global; t2 seats invoke the
   same path with their own round dirs. Verdicts bank beside the codex anchor and
   any OR voices exactly as before — this changes the DISPATCH FORM of the opus
   voice, nothing about SOP-7's voice composition or SOP-3's judge-lane rules.

## Tuning evidence (not a gate)

The first real round after adoption runs the opus judge BOTH ways (cleanroom +
Agent-tool) on the same frozen object and files the comparison — adoption does not
wait on it (the fleetwide ruling lifted the earlier pilot gate); the comparison tunes prompt
depth and timeout defaults.

Filed comparisons (n=2 as of 2026-08-08):
- Comparison 1, filed in the private workspace (orch round):
  cleanroom NOT weaker — sole BLOCKER, 5-to-3 on material uniques.
- Comparison 2, filed in the private workspace (owner round):
  finding count a wash (18 vs 16), TIED on the build-deciding finding; cleanroom's
  clean margin was on the MEASURING APPARATUS (fixtures certifying a dead rule,
  duplicate control ids), not the artifact. Owner's refined hypothesis, carried
  with its disclosure intact: "a leg carrying this seat's memory index inherits
  this seat's confidence in its own instruments" — two conditions differ (index
  injection AND session context), so NOT a single-variable result. No adoption
  claim moves on n=2; next comparison should vary ONE condition if practical.
