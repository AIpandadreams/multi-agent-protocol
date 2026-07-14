# Environment gotchas — the pattern, plus seed examples [PROTOCOL v2.6]

> **Tier: once per project** — then maintain the per-project list in memory and
> consult it when symptoms match.
> Machine-specific facts in here (paths, shells, tooling) are EXAMPLES from
> the originating deployment — the binding home for your machine's facts is
> the transport's **Host profile** section (`transports/local-fs.md`).

Every long-running multi-agent project accumulates environment-specific traps. The
PATTERN is the transferable part:

1. **Keep a living gotchas list in project memory** (not in this skill). Every trap that
   costs real time gets one line: symptom → cause → what to do instead.
2. **Read the list at session start.** A successor session repeating a burned lesson is
   a memory-discipline failure, not bad luck.
3. **Generalize each trap into its class** so you recognize the next instance early.

## Seed examples by class (from live operation — bind/replace per project)

**Signing / credentials time-box.** Signed commits can HANG non-interactively when the
key agent's cache is cold. Probe before every commit batch with a command that fails
fast instead of hanging (e.g. `gpg --pinentry-mode error --clearsign` on a throwaway
string). Cold → queue the commit and tell the principal; never disable signing. If the
principal must warm it, they run the command themselves in their own prompt (in Claude
Code, a `!`-prefixed command; a command pasted as a chat message did NOT run).

**Path dialect mismatches.** Tools disagree about path syntax on the same machine
(e.g. Windows Python rejects Git-Bash `/x/...` drive paths → use the native
`<drive>:/...` form). Misdiagnosis risk: the error looks like a missing/unsynced file.

**Encoding defaults.** Console codepages break on non-ASCII output (set
`PYTHONIOENCODING=utf-8` or equivalent before scripts that print arbitrary text).
The *rules* about encoding — shared files are UTF-8 without BOM; machine-read
artifacts are gated as BYTES with strict decode, a parse, and their exclusions
enumerated — are normative in `../../agent-core/references/channel-core.md`, and
bind you whatever shell you are in. What follows is only what YOUR shell does to
them. PowerShell round-trips inject BOM + mojibake (`â€"`, `Â§`) into transcribed
verdicts and ledgers — repair before the file is cited anywhere.

⚠ **The "utf8" flag that writes a BOM.** The obvious fix for a UTF-16 default is
the shell's own utf8 flag — and on Windows PowerShell 5.1 that flag
(`-Encoding utf8`) emits UTF-8 **WITH a BOM** (`EF BB BF`). It does not solve the
encoding problem; it trades a UTF-16 artifact for a BOM artifact, which is worse
because a BOM is invisible to every line-oriented tool while strict parsers reject
it outright (`json.loads` → *"Unexpected UTF-8 BOM"*; Node `JSON.parse` →
SyntaxError). Never reach for it on a machine-read artifact.

Write no-BOM **explicitly**. Two traps in one line: method arguments are
expression-mode (pass variables, never bare words), and `[IO.File]` resolves a
RELATIVE path against the process working directory, not `Get-Location` — so a
relative name silently lands somewhere you are not standing. Pass an absolute path.

```powershell
[IO.File]::WriteAllText($path, $text, [Text.UTF8Encoding]::new($false))  # PS 5+, $path ABSOLUTE
Set-Content -LiteralPath $path -Value $text -Encoding utf8NoBOM          # PS 6+
```

Detect a BOM only at the **byte** level — read the first four bytes and match the
longest signature first (UTF-32's mark is 4 bytes and shares UTF-16 LE's opening
two, so three bytes cannot tell them apart); `Get-Content` in its default text
mode cannot see one, the same blind spot as stray CR bytes:

```powershell
[IO.File]::ReadAllBytes($path)[0..3]                              # PS 5+
Get-Content -LiteralPath $path -Encoding Byte -TotalCount 4       # PS 5.1 (dropped in 6+)
Get-Content -LiteralPath $path -AsByteStream -TotalCount 4        # PS 6+
```

**Version-tag every shell snippet you publish — and get the boundary right.**
Handing a 5.1 reader a 6+-only parameter (`-AsByteStream`, `utf8NoBOM`) fails
exactly like the flag it was warning about. This file has now shipped that class
twice: once recommending the BOM-writing flag, once mis-tagging its replacement.
An untagged snippet is a trap with a green face; a wrongly-tagged one is worse.

**Quoting cliffs.** Inline heredocs/strings break on mixed-quote content — stage long
text via a file-write tool, then append/pipe it.

**Pipes that look hung.** Long-running processes piped through pagers/tail in background
tasks buffer until EOF and look frozen. Redirect to per-run log files instead.

**Stale locks.** Crashed/parallel sessions leave stale lock files (e.g. zero-byte
`.git/index.lock`). Verify no live process, then remove and retry.

**Shared live trees (index sweeps).** In a repo another agent session actively works,
`git add <file>` + a bare `git commit` commits the ENTIRE index — the peer's
staged-but-uncommitted work rides your commit silently. Always commit with an explicit
pathspec (`git commit -- <paths> -m "..."`) in shared trees. If a sweep happens:
disclose to the peer immediately; never rewrite shared history unilaterally.
Two more traps in the same class: (a) **peer pull-rebase re-hash** — when a
peer's pull-rebase carries your local commit to the remote, the LANDED sha
differs from the one you minted; cite the remote sha, never your pre-rebase
local one. (b) When the shared tree holds a peer's live uncommitted WIP,
publish via an **isolated worktree** instead of committing in place: fetch →
`git worktree add <tmp> origin/<branch>` → cherry-pick your commit there →
push from the worktree → remove it (your local duplicate dedups on the next
rebase).

**Silent credential prompts.** Credential-manager outages make git network operations
HANG on an invisible username prompt (no error, no output — looks like a wedged push).
Keep `GIT_TERMINAL_PROMPT=0` in agent shells so they fail fast instead; repair the
credential helper (e.g. `gh auth setup-git`) rather than retrying the hang.

**Harness-hook wedges.** A stuck harness hook process (spawned per tool call,
blocking on a pipe) can freeze a session mid-turn INDEFINITELY — stuck tool
spinner, queued messages unprocessed, the harness waiting on the hook forever.
Diagnose: an orphaned hook process with an old creation time and ~0 CPU. Kill
the HOOK process (not the session) — the session self-resumes within seconds
and the interrupted tool call errors back cleanly. Prevention: hooks need hard
kill-timers and exit-after-write; a scheduled janitor that kills over-age hook
processes converts a fleet-freezing class into a non-event.

**Tool-capability holes.** Some harness tools silently depend on binaries the machine
lacks (e.g. PDF page rendering needing poppler). Record the working alternative next to
the broken path.

**Reviewer relay quirks.** (Applies when your REVIEWER binding is a relayed
reviewer.) (a) Sandbox file-writes get denied intermittently — every relay
prompt carries the fallback chain: native write → shell write →
verbatim-in-transcript + your transcription with a banner; check whether the
verdict file actually landed before assuming either way. (b) A stale "running"
relay job can block new rounds on the serialized lane — the fix is in the relay
plugin's CENTRAL state file (a `jobs[]` array), not only the per-job state
file; repair the central record (with a backup) to free the lane. (c) Relay
completion notices sometimes truncate; the verdict file on disk is canonical.
(d) Relay job stores are keyed PER WORKSPACE ROOT — a status/result poll run
from another directory reports "No job found" even while the job runs; cd
into the job's workspace before every poll (shell cwd resets between calls).
(e) A status read can report "completed" while the job is still RUNNING
(observed: status said completed, result fetch said "No job found",
`status --all` showed it mid-run) — trust completion only when status AND a
successful result fetch agree.

**Subagent quirks.** (a) Subagents finish work and idle WITHOUT relaying their summary —
check for the deliverable file, then message them to relay. (b) Drafter subagents make
confident false claims — verify number-bearing claims. (c) Peer/teammate message banners
look like external-session intrusions but fire for your OWN subagents too — check the
sender before alarming. (d) Editing a file can require an in-conversation Read first,
even if you've seen its content through other tools.

**Scanner false-positives.** Security/lint plugins flag benign patterns (fixture names,
test constants). Record the known-benign list so successors don't re-investigate.

**Long jobs vs CI.** Anything wall-clock-heavy and hardware-bound (live evals, embedding
runs) stays manual-only; CI gets the deterministic/recorded equivalents.
