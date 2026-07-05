# Transport profile: local-fs [PROTOCOL v2.5]

For agents running as local Claude Code sessions (IDE/CLI) on one machine.
Binds the abstract channel verbs to filesystem operations.

| verb | implementation |
|---|---|
| POLL | list the CHANNEL directory + read the peer file's tail; compare entry numbers to memory's last-seen. Cadence: each heartbeat + session start + after every completed unit |
| READ | read peer entries past last-seen from the shared directory |
| APPEND | append to YOUR outbound file (stage long text via file-write, then append — heredoc trap) |
| PUBLISH | no-op (the filesystem IS shared); a "publish" is complete when the append lands |
| INTEGRITY | channel-core checks against the files directly |

Other bindings, local flavor:
- **CHANNEL** = a shared directory both sessions can read/write
  (e.g. `path/to/review_inbox/`, or the workspace repo's own `channel/`).
- **MEMORY** = the harness memory dir per project
  (`~\.claude\projects\<proj>\memory\`).
- **HEARTBEAT** = a Claude Code scheduled task re-invoking the LIVE session
  (context intact). One per role, offset (e.g. :23 / :53).
- **REVIEWER** = local Codex via relay subagent (builder-style) and/or the
  harness stop-review gate (owner-style).
- **SIGNING** = `gpg-local`: probe warmth fail-fast before every commit batch
  (`gpg --pinentry-mode error --clearsign` on a throwaway string); cold →
  queue + tell the principal. Never bypass.
- **PRINCIPAL interface** = the principal types directly into each session.
- Known traps: see each role's ops-gotchas (Windows path dialects, BOM,
  heredocs, stale locks, pager pipes).

## Host profile (bind per machine)

Machine facts are TRANSPORT data, not protocol: each deployment records a
host profile alongside its bindings — drive letters and canonical paths;
shell dialect and its traps; signing agent state and probe procedure;
PDF/document tooling actually installed; reviewer-relay plugin state
locations and job-store keying; subagent/judge spawn caps. Role reference
files keep only protocol-inherent rules; when a machine fact appears in a
role's ops-gotchas, treat it as an EXAMPLE from the originating deployment,
and bind your own machine's facts here. Workpaper and artifact naming keys
to durable ids (job id, round, date) — never to session ids or other
host-ephemeral handles.
