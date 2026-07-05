# Environment gotchas — the pattern, plus seed examples [PROTOCOL v2.5]

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
(e.g. Windows Python rejects Git-Bash `/x/...` drive paths → use the native `X:/...`
form). Misdiagnosis risk: the error looks like a missing/unsynced file.

**Encoding defaults.** Console codepages break on non-ASCII output (set
`PYTHONIOENCODING=utf-8` or equivalent before scripts that print arbitrary text).
Write shared/channel files as **UTF-8 without BOM**; PowerShell round-trips inject
BOM + mojibake (`â€"`, `Â§`) into transcribed verdicts and ledgers — repair before
the file is cited anywhere, and prefer the Bash tool or an explicit `-Encoding
utf8` for any file another tool will read.

**Quoting cliffs.** Inline heredocs/strings break on mixed-quote content — stage long
text via a file-write tool, then append/pipe it.

**Pipes that look hung.** Long-running processes piped through pagers/tail in background
tasks buffer until EOF and look frozen. Redirect to per-run log files instead.

**Stale locks.** Crashed/parallel sessions leave stale lock files (e.g. zero-byte
`.git/index.lock`). Verify no live process, then remove and retry.

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
