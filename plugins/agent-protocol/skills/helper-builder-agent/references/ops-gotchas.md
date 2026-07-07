# Ops gotchas — burned lessons [PROTOCOL v2.6]

> **Tier: once per project** — then maintain the per-project list in memory and
> consult it when symptoms match.
> Machine-specific facts in here (paths, shells, tooling) are EXAMPLES from
> the originating deployment — the binding home for your machine's facts is
> the transport's **Host profile** section (`transports/local-fs.md`).

Environment-level traps hit in the originating deployment (Windows + Claude Code +
background subagents + a relayed reviewer). Verify per environment, but check this list
FIRST when something looks broken — most of these masquerade as tool failures.

## Subagent output extraction

- Background agents' `tasks/<id>.output` files can be EMPTY (0 bytes) even when the
  agent succeeded. The real returns live in the session's transcript directory:
  `<project>/<session-id>/subagents/agent-<id>.jsonl`. Extract the LAST assistant text
  block, pull the fenced JSON, and **un-escape HTML entities** (`&amp;` `&gt;` `&lt;`)
  before parsing — the harness encodes them in transit.
- Keep a small extractor script (JSONL → per-group JSON files) and ship it with the
  wave record so returns are re-derivable.
- Never tail/Read a background agent's full JSONL transcript into context — it will
  blow the window. Parse it with a script.

## Reviewer relay quirks

- Reviewer sandbox file-writes get denied intermittently. Every relay prompt carries the
  fallback chain (native write → shell here-string → verbatim-in-transcript +
  builder transcription with banner). Check whether the verdict file actually landed
  before assuming either way.
- A stale "running" relay job can block new rounds on the serialized lane. The fix is in
  the relay plugin's CENTRAL state file (a `jobs[]` array), not only the per-job state
  file — repair the central record (with a backup) to free the lane.
- Relay completion notices sometimes truncate; the verdict file on disk is canonical.
- A poller/status read can report a job "completed" while it is actually still
  RUNNING (observed live: status said completed, result fetch said "No job found",
  `status --all` showed the job mid-run). Trust completion only when status AND a
  successful result fetch agree; a "completed" without a retrievable result is a lie.

## Shell and encoding traps (Windows)

- Bash heredocs (`<<'EOF'`) can fail to parse in Git Bash with long mixed-content
  markdown. For file appends, prefer the Edit tool (anchor on the file's current tail)
  or Write-to-temp + `cat temp >> target`.
- Set `PYTHONIOENCODING=utf-8` on any Python invocation whose output may carry
  non-ASCII (en-dashes, section marks) — otherwise prints crash mid-script.
- PowerShell 5.1: no `&&`/`||`, UTF-16 default file encoding (`-Encoding utf8` when
  other tools will read the file), and native-command stderr wrapping. Prefer the Bash
  tool for POSIX-shaped work.
- Write shared/channel files as **UTF-8 without BOM**. PowerShell round-trips inject
  BOM + mojibake (`â€"`, `Â§`) into transcribed verdicts and ledger rows — scan for and
  repair mojibake BEFORE the file is cited by a round, a record, or the peer.
- Edit-tool paths are case-sensitive in practice — match the on-disk casing exactly.
- PDF tooling: check what's actually installed before relying on harness PDF features
  (in the originating environment the Read tool's `pages` param was broken because
  poppler was missing; PyMuPDF via Python was the workaround).

## Two-session concurrency

- Shared artifacts (workbook, inbox files) may be written by the other session between
  your reads — re-read immediately before any authorized edit.
- Git commits may be GPG-gated: a cold gpg-agent HANGS non-interactive commits. Probe
  warmth first; if cold, queue the commit and tell the principal rather than bypassing
  signing.
- A banner saying "another session sent a message" often just marks YOUR OWN subagent
  reporting back — verify the sender id and transcript before treating it as external
  injection. A false alarm here once triggered a needless investigation.

## Memory & context hygiene

- Checkpoint memory BEFORE any risky long operation and after every shipped unit;
  compaction can land mid-pipeline, and the successor resumes from memory alone.
- Keep the memory index lean (state + pointers); verbatim round detail goes to topic
  files. When recalled memory names a file/flag, verify it still exists before acting
  on it.
