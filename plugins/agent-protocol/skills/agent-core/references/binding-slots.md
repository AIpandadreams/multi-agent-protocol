# Binding-slot glossary [PROTOCOL v2.6]

> The skills define ROLES and PROTOCOLS; each project supplies BINDINGS. Slots
> are shared vocabulary across all role skills; each role's START_SESSION
> carries the role-relevant subset. Bindings live in the project's persistent
> memory / instantiated start file — never hard-coded in skills.

| slot | what it binds | notes |
|---|---|---|
| ROLE_LOCK | this session's role on this project (owner / builder / orchestrator) | recorded at first bind; a session finding a different role locked must stop and ask the principal |
| SIDE_NAMES | the short names used in filenames and entry headers (e.g. `engine`, `builder`, `orch`) | ALL sessions bind the same set |
| CANONICAL_REPO | the work repo/artifact the OWNER owns (path + remote + branch) | read-only to everyone else |
| CHANNEL | the channel transport instance: shared directory (local-fs; a git-synced channel repo variant is on the roadmap) + the per-direction files per the filename grammar | see `transports/` in the multi-agent-protocol repo |
| MEMORY | each role's persistent memory (index + verbatim log/topic files) | the workspace repo's committed `memory/<role>/` — persistent state lives in git (principle #2) |
| REVIEWER | per side: mechanism (relayed / harness-gate) + model + verdict location + next round number in that side's series | see review-core.md |
| PRINCIPAL | the human gate-holder; where each role's gated-items queue lives; how the principal is reached (notifications) | |
| PINNED_RESOURCES | exact external resources (IDs/paths) a role may touch — everything else is forbidden, including reads | |
| SHARED_ARTIFACTS | the ONLY artifacts writable across ownership boundaries; per artifact: path, writer(s), conditions (kept out of the commit surface, principal per-batch go, re-read immediately before edit, writes announced in the channel) | usually empty |
| SIGNING | how canonical commits stay trustworthy: `gpg-local` (probe warmth first) / `webflow-api` (PR merged via GitHub-signed web flow) / `sign-on-merge` (principal merges) — never bypassed, only queued | |
| HEARTBEAT | each role's periodic wake mechanism + cadence, offset from the others'; e.g. a scheduled task re-poking the live session, or a scheduled headless run spawning a cold successor | delete stale ones; delete at window end |
| AUTONOMY | the autonomy dial level for this role: `attended` / `semi-autonomous` / `standing-duties` / `never-idle` | default `semi-autonomous`; `never-idle` requires a WATCHER binding — see `never-idle-core.md` |
| WATCHER | per-role monitor mechanism + the list of lanes it watches + the cycle cadence | required when AUTONOMY = `never-idle`; the settled-change guard is the transport's own (channel-core / poller half-write rule) |
| MODEL | the live model matrix — see `profiles/MODELS.md` in the multi-agent-protocol repo: per-role default + allowed alternates + escalation rules + quality presets; adjustable at instantiation, per task, and on the principal's word (change logged in git) | |
| EMBARGOES / GATES | the standing list of what may never be written/named/sent without a go; size tripwires | |
| PROXY_AUTH | `off` (default) or `on` + an ENUMERATED reversible/internal gate-class list and explicit exclusions — set/changed/revoked only by the principal speaking directly in the orchestrator session; never relayable. The irreversible/outward super-classes (outward-facing/publish, email SEND, new-money/new-recipient, destructive-to-others, canonical-repo merge, PROXY_AUTH/gate/embargo/protocol changes) are never listable or relayable | see proxy-auth-core.md; wildcards invalid |
| AUTH_PROVENANCE | how auth-log writer identity is proven: `per-role-identity` (per-role keys/accounts + path protection + CI author check; default when gate classes include irreversible/outward) or `single-identity` (trust-based; principal's acceptance recorded; mandatory compensating checks) | see proxy-auth-core.md §Provenance |
| PROTOCOL_VERSION | the protocol version all sessions run (stamped on entries) | mismatch = park + flag |
