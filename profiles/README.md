# Profiles — configuration × transport

A profile binds a running instance: which roles run, which transport file
applies, and the model matrix. Instantiation copies the chosen profile +
`MODELS.md` into the project's agent workspace and fills the bindings.

| profile | roles running | transport | principal interface |
|---|---|---|---|
| `3agent.local` | orchestrator + owner + builder | `transports/local-fs.md` | principal speaks to the orchestrator; auth per proxy-authorization rules |
| `2agent.local` | owner + builder | `transports/local-fs.md` | principal speaks to the owner, which runs dual-role (absorbs orchestrator interface/queue duties) |

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
- Cloud profiles (scheduled cold-successor wakes over a git transport) exist
  upstream but are not part of this release; see the roadmap note in the
  README.
