# Profiles — configuration × transport

A profile binds a running instance: which roles run, which transport file
applies, and the model matrix. Instantiation copies the chosen profile +
`MODELS.md` into the project's agent workspace and fills the bindings.

| profile | roles running | transport | principal interface |
|---|---|---|---|
| `2agent.local` | owner + builder | `transports/local-fs.md` | principal speaks into each session directly; owner doubles as primary interface |
| `3agent.local` | orchestrator + owner + builder | `transports/local-fs.md` | principal speaks to the orchestrator; auth per proxy-authorization rules |

Notes:
- The orchestrator is purely additive: the 3-agent profile degrades to its
  2-agent sibling by simply not running the orchestrator, and a 2-agent
  workspace upgrades by adding the orchestrator role + its binding slots.
- One orchestrator can also front SEVERAL projects' worker pairs — bind
  `FLAVOR: global-pa` and register each project's workspace in its session
  registry (see `docs/CONFIGURATIONS.md`).
- The reviewer (Codex or fallback) is part of every profile — it is the
  fourth party, not an optional extra.
- Cloud profiles (scheduled cold-successor wakes over a git transport) exist
  upstream but are not part of this release; see the roadmap note in the
  README.
