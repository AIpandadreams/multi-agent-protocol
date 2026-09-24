# v1.2.1 land checklist (execute only after P5 fold + P6 final-opinion + the principal's word)

## A. Public (this repository)

1. gpg warm probe (Bash): `echo probe | "/c/Program Files/Git/usr/bin/gpg.exe" --batch --pinentry-mode error --clearsign -o /dev/null`
2. Explicit `git add` of ALL TEN paths (three docs are UNTRACKED — a `commit -a` would ship README/CHANGELOG links to missing files; opus finding 1):
   CHANGELOG.md README.md .claude-plugin/marketplace.json plugins/agent-protocol/.claude-plugin/plugin.json plugins/agent-protocol/skills/agent-core/references/channel-core.md plugins/agent-protocol/skills/agent-core/references/never-idle-core.md tools/reviewer_poller.py docs/CREATOR-SEAT-BOOTSTRAP.md docs/CREATOR-SEAT-BOOTSTRAP.html docs/SOP-REGISTRY.md
   Then VERIFY `git status` shows exactly these ten staged, nothing else, before committing.
3. Commit (unsigned per local override) message:
   "release 1.2.1: live-operation hardening — creator-seat bootstrap + SOP registry docs, channel rotation + tool-verified-timestamp clauses, arm-and-verify wave, reviewer_poller --once failure propagation"
4. `git tag -s v1.2.1 -m "v1.2.1 — live-operation hardening (PROTOCOL v2.6)"`
5. `git push origin main v1.2.1` (disclose branch-protection bypass to the principal in the land report)
6. `gh release create v1.2.1` — notes from CHANGELOG [1.2.1] section
7. Verify CI (mirror-check workflow) green.

## B. Private mirror (the private workspace)

1. Mirror the skill-text edits verbatim to private: `channel-core.md` (two clauses) AND `never-idle-core.md` (stop-then-arm paragraph) — neither file carries de-genericizations; expect byte-identical modulo EOL.
2. Byte-copy public → private tools with a BOUNDED SWAP WINDOW (codex blocker 2 / opus finding 3 — live 5-min schtask executes reviewer_poller.py directly):
   a. `schtasks /Change /TN AgentReviewerPollerPALocal /DISABLE`; verify no python instance running the poller (Win32_Process CommandLine match).
   b. sha256 + byte-size the current private file (rollback pin).
   c. Copy public file to a temp sibling in the SAME directory, then atomic `Move-Item -Force` over the target (same-volume rename).
   d. Validate: `python -m py_compile`, then ONE invocation using the schtask's exact command line (read it from the task definition first) — expect exit 0 on clean/dry.
   e. Re-enable the task; watch the next tick complete; confirm NO ALERT flag (ALERT = recovery evidence, not the race control).
   f. `new_project.py` has no live executor — plain copy is fine.
3. plugin.json 2.6.1 → 2.6.2 (version file = `plugins/agent-protocol/.claude-plugin/plugin.json`), commit + push (origin multiagent ONLY — never AE-personal-pa).
4. `claude plugin marketplace update multiagent`; in EACH workspace dir: `claude plugin uninstall agent-protocol@multiagent -s project` + `claude plugin install agent-protocol@multiagent -s project`; verify `claude plugin list` shows 2.6.2 + grep installed cache for "Verify the wall clock".
5. SYNC_MANIFEST.md updates:
   - tools row `{mirror_check,new_project,reviewer_poller,wave_coverage_check}`: CANDIDATE → "CONFIRMED @ v1.2.1 (new_project + reviewer_poller byte-copied 2026-07-10; mirror_check + wave_coverage_check verified same-content)". NOTE: verify mirror_check/wave_coverage_check byte-delta at this step; if they differ, keep CANDIDATE for those two and say so.
   - scale/adopt row: confirm or annotate.
   - Add row: `— | docs/CREATOR-SEAT-BOOTSTRAP.{md,html}, docs/SOP-REGISTRY.md | PUBLIC-ONLY by design (generalized from private ops; no private twin needed — private keeps the live SOPs/runbooks themselves)`.
   - channel-core clause parity note in the skill-tree row.
   - "Last checked against: public v1.2.1 + tag" line.
6. Commit private (pathspec-explicit), push multiagent.

## C. Relays (after A+B)

1. Orch (ccd): land report + the two new channel rules + finding-4 ask (r-DTR3/4 gpt-5.5 trail) + request team-1 seats intake timestamp rule.
2. Engine (inbox file `creator_to_engine_V121_LANDED_2026-07-10.md`): land report + explicit "timestamp drift recurred in E316/E284/consult stamps ~+40min post-diagnosis — rule now protocol text, please intake + relay builder".
3. The principal: final change log + disclosure lines (branch-protection bypass; orch consult folded/outstanding status).
