> **Public-release copy.** Fleet record ids and private paths in this saved record are redacted (`[redacted]`) or shortened to their repo-relative form; nothing else is changed.

VERDICT: FIX-REQUIRED

1. File: `docs/SOP-REGISTRY.md`  
   Issue: The supposedly sanitized public example retains the concrete private authorization-log reference `[redacted]` (and its exact adoption date). This is an originating-deployment operational identifier, not a generic placeholder, so the package does not meet the no-private-leak requirement.  
   Severity: BLOCKER  
   Suggested fix: Replace the concrete reference and date with unmistakable placeholders such as `<adoption-date> (<auth-log-reference>)`, then repeat the release-surface privacy scan.

2. File: `docs/v121-wave/V121_WAVE_REPORT.md` (§4, step 2)  
   Issue: The private-mirror plan byte-copies `reviewer_poller.py` while the live five-minute scheduled task remains enabled and executes that file directly. A tick can start during a non-atomic overwrite and observe a partial file; the plan also asserts wrapper compatibility without first validating the scheduled action's exact arguments and exit-code expectations. This conflicts with the package's own freeze-before-cut rule in `docs/CREATOR-SEAT-BOOTSTRAP.md`.  
   Severity: BLOCKER  
   Suggested fix: Add a bounded swap window: disable the scheduled task, verify no instance is running, preserve/hash the current file, copy to a temporary sibling and atomically replace the target, run syntax validation plus one invocation through the scheduled task's exact command/arguments, then re-enable the task and confirm the next tick. Keep ALERT handling as recovery evidence, not as the primary race control.

3. File: `CHANGELOG.md` (`[1.2.1]`)  
   Issue: Several release claims have no corresponding change in the authorized package surface: the wake-monitor START_SESSION/session-card/`never-idle-core.md` hardening, the owner/builder `ops-gotchas.md` additions, and both `tools/migrate_workspace.py` additions/fixes. Under the requested diff-to-CHANGELOG reconciliation, these claims are unsubstantiated by the tracked diff or either new Markdown file.  
   Severity: MAJOR  
   Suggested fix: Either include the claimed source changes in the reviewed release surface or remove/move those claims from `[1.2.1]`; then reconcile every remaining Added/Hardened/Fixed bullet one-to-one against the final release diff.

4. File: `CHANGELOG.md` (`docs/CREATOR-SEAT-BOOTSTRAP.md` Added bullet)  
   Issue: The CHANGELOG claims seven incident case studies, but the new document contains eight: deaf seat, index sweep, silent credential outage, swallowed exit code, stale relay, scope trap, drifting clock, and log-residue false alarm.  
   Severity: MINOR  
   Suggested fix: Change “seven incident case studies” to “eight incident case studies.”

5. File: `docs/CREATOR-SEAT-BOOTSTRAP.md` (Part 8, item 6)  
   Issue: The reviewer-wiring checklist points readers to §6.5, which is the HALT/RESUME runbook; reviewer-lane outage/watchdog guidance is in §6.7.  
   Severity: MINOR  
   Suggested fix: Change the cross-reference from `6.5` to `6.7`.
