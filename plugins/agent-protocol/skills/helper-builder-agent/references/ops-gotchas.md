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
- PowerShell 5.1: no `&&`/`||`, UTF-16 default file encoding, and native-command
  stderr wrapping. Prefer the Bash tool for POSIX-shaped work.
- ⚠ **Do NOT "fix" that UTF-16 default with `-Encoding utf8`** — on PS 5.1 that flag
  writes UTF-8 **WITH a BOM** (`EF BB BF`), trading one bad artifact for a worse one:
  a BOM is invisible to line tools yet strict parsers reject it (`json.loads` →
  *"Unexpected UTF-8 BOM"*). Write no-BOM explicitly with
  `[IO.File]::WriteAllText($path, $text, [Text.UTF8Encoding]::new($false))` (**PS 5+**
  — method args are expression-mode, so pass VARIABLES not bare words, and pass an
  ABSOLUTE path: `[IO.File]` resolves a relative one against the process working
  directory, not `Get-Location`), or `-Encoding utf8NoBOM` (**PS 6+**), or an
  editor/file-write tool. Detect a BOM by reading the first four **bytes**, matched
  longest-first (UTF-32's mark is 4 bytes and shares UTF-16 LE's 2-byte prefix) —
  `[IO.File]::ReadAllBytes($path)[0..3]` (PS 5+), `Get-Content -Encoding Byte
  -TotalCount 4` (5.1) or `-AsByteStream -TotalCount 4` (6+); `Get-Content` in
  default text mode cannot see one (same blind spot as stray CRs).
- **Version-tag every shell snippet you publish, and get the boundary right.** Handing
  a 5.1 reader a 6+-only parameter (`-AsByteStream`, `utf8NoBOM`) fails exactly like
  the flag it warns about — and a wrongly-tagged snippet is worse than an untagged one.
- ⚠ **PowerShell SCRIPT FILES INVERT the no-BOM rule: there the BOM is REQUIRED.**
  PowerShell 5.1 decodes a BOM-*less* UTF-8 script as ANSI and mangles every non-ASCII
  byte (`§ — é` → `Â§ â€” Ã©` — that is where this mojibake is BORN, not just where it
  is seen). Strip the BOM to satisfy a "no BOM" rule and you have written the
  corruption yourself. Save scripts with a BOM (`[IO.File]::WriteAllText($p, $t,
  [Text.UTF8Encoding]::new($true))`, **PS 5+**) — or keep them pure ASCII, which needs
  no BOM because it has nothing to mangle. **Scope it by the readers, not the suffix
  that bit you: `.ps1`, `.psm1` and `.psd1` go through the 5.1 script reader, `.psrc`
  and `.pssc` through the engine's data-file reader (`Import-PowerShellDataFile`),
  and all five invert** (`.ps1xml` does not — .NET reads it as XML). Every other
  shared file stays no-BOM per `channel-core` corollary (d).
- The *rules* here — UTF-8 without BOM on shared files, byte gates with strict decode
  and enumerated exclusions — are normative in
  `../../agent-core/references/channel-core.md` and bind every role, shell or no
  shell. The bullets above are only what PowerShell does to them. PowerShell
  round-trips also inject mojibake (`â€"`, `Â§`) into transcribed verdicts and ledger
  rows — scan for and repair it BEFORE the file is cited by a round, a record, or the
  peer.
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
- In a repo another live session actively works, `git add <file>` + a bare
  `git commit` commits the ENTIRE index — the peer's staged-but-uncommitted work
  rides your commit silently. Always commit with an explicit pathspec
  (`git commit -- <paths> -m "..."`) in shared trees; if a sweep happens, disclose
  to the peer immediately and never rewrite shared history unilaterally.
- Same class, two more traps: (a) **peer pull-rebase re-hash** — when a peer's
  pull-rebase carries your local commit to the remote, the LANDED sha differs
  from the one you minted; cite the remote sha, never your pre-rebase local
  one. (b) When the shared tree holds a peer's live uncommitted WIP, publish
  via an **isolated worktree** instead of committing in place: fetch →
  `git worktree add <tmp> origin/<branch>` → cherry-pick your commit there →
  push from the worktree → remove it (your local duplicate dedups on the next
  rebase).
- Credential-manager outages make git network operations HANG on an invisible
  username prompt (no error, no output — looks like a wedged push). Keep
  `GIT_TERMINAL_PROMPT=0` in agent shells so they fail fast instead; repair the
  credential helper (e.g. `gh auth setup-git`) rather than retrying the hang.

## Harness-hook wedges

- A stuck harness hook process (spawned per tool call, blocking on a pipe) can freeze
  a session mid-turn INDEFINITELY — stuck tool spinner, queued messages unprocessed,
  the harness waiting on the hook forever. Diagnose: an orphaned hook process with an
  old creation time and ~0 CPU. Kill the HOOK process (not the session) — the session
  self-resumes within seconds and the interrupted tool call errors back cleanly.
- Prevention: hooks need hard kill-timers and exit-after-write; a scheduled janitor
  that kills over-age hook processes converts a fleet-freezing class into a non-event.

## Memory & context hygiene

- Checkpoint memory BEFORE any risky long operation and after every shipped unit;
  compaction can land mid-pipeline, and the successor resumes from memory alone.
- Keep the memory index lean (state + pointers); verbatim round detail goes to topic
  files. When recalled memory names a file/flag, verify it still exists before acting
  on it.
