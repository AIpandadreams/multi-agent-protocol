# Profiles — configuration × transport

A profile binds a running instance: which roles run, which transport file
applies, and the model matrix. Instantiation copies the chosen profile +
`MODELS.md` into the project's agent workspace and fills the bindings.

| profile | roles running | transport | principal interface |
|---|---|---|---|
| `3agent.local` | orchestrator + owner + builder | `transports/local-fs.md` | principal speaks to the orchestrator; auth per proxy-authorization rules |
| `2agent.local` | owner + builder | `transports/local-fs.md` | principal speaks to the owner, which runs dual-role (absorbs orchestrator interface/queue duties) |
| `3agent.git-sync` | orchestrator + owner + builder | `transports/git-sync.md` | same as `3agent.local`, but peers run on separate machines and synchronize over `WORKSPACE_REMOTE` |
| `2agent.git-sync` | owner + builder | `transports/git-sync.md` | same as `2agent.local`, but peers run on separate machines and synchronize over `WORKSPACE_REMOTE` |

Notes:
- The orchestrator duties are separable: nothing in the owner/builder
  contract changes whether they run as their own session (the default
  3-agent profile) or inside the owner (the 2-agent dual-role variant). The
  3-agent profile collapses to its 2-agent sibling by simply not running
  the orchestrator; a 2-agent workspace splits the role back out by adding
  the orchestrator role + its binding slots.
- One orchestrator can also front SEVERAL projects' worker pairs — bind
  `FLAVOR: global-pa` and register each project's workspace in its session
  registry (see `docs/CONFIGURATIONS.md`).
- The reviewer (Codex or fallback) is part of every profile — it is the
  fourth party, not an optional extra.
- The `.git-sync` profiles bind the same role sets as their `.local` twins;
  only the transport differs (a git remote instead of a shared filesystem),
  so they add a `WORKSPACE_REMOTE` binding and stamp `TRANSPORT: git-sync`.
  Scheduled cold-successor wakes over git and integrity-gated automerge are
  documented in `docs/CLOUD.md`; the transport verbs in
  `transports/git-sync.md`.
