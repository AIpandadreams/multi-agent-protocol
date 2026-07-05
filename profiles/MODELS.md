# MODELS.md — live model matrix [template]

> Copy into each agent workspace at instantiation. This file is LIVE
> configuration: every value is adjustable (1) at instantiation, (2) per
> session/task by the orchestrator's auto-selection within the allowed set,
> and (3) at any moment on the principal's word — the orchestrator edits this
> file, the change takes effect at each agent's next wake, and git history
> records who/when/why. Nothing here is hardcoded anywhere else.

## Active setting

```yaml
active_preset: balanced        # or a custom preset name, or "custom:<name>"
overrides: {}                  # per-role overrides layered on the preset,
                               # e.g. { builder: claude-opus-4-8 }
```

## Quality presets (shipped defaults — edit freely, add your own)

| preset | orchestrator | owner | builder | reviewer | wave subagents | intent |
|---|---|---|---|---|---|---|
| maximum | claude-fable-5 | claude-fable-5 | claude-fable-5 | codex (high effort) | claude-sonnet-5 | highest-stakes work, cost no object |
| strong | claude-fable-5 | claude-fable-5 | claude-opus-4-8 | codex | claude-sonnet-5 | important multi-day programs |
| balanced | claude-fable-5 | claude-opus-4-8 | claude-sonnet-5 | codex | claude-sonnet-5 / haiku for mechanical reads | default day-to-day |
| economy | claude-sonnet-5 | claude-opus-4-8 (decisions/commits only) | claude-sonnet-5 | codex | claude-haiku-4-5 | budget pressure; cost-governor may auto-drop here and MUST report it |
| fast | claude-opus-4-8 (fast mode) | claude-opus-4-8 (fast mode) | claude-sonnet-5 | codex | claude-haiku-4-5 | quick low-stakes turnarounds |

Custom presets: add a row (or a `custom_presets:` block below) with any
name/mapping; switchable exactly like shipped ones ("run <name> today").

## Rules

- **Escalation:** the builder may escalate a single job to the owner's tier
  when a census/read is precision-critical — logged in the ledger row. The
  orchestrator may escalate any dispatch one tier for ambiguity/stakes —
  logged in its intent log.
- **Reviewer independence:** the reviewer is cross-vendor (Codex) whenever
  reachable; the fallback is a Claude model DIFFERENT from the artifact's
  author. Never author and review on the same model instance.
- **Cost governor:** the orchestrator tracks spend in the cost ledger; on
  crossing the bound budget threshold it may switch active_preset to economy,
  reports the switch to the principal the same cycle, and never silently
  downgrades the reviewer.
- **Transparency:** every agent echoes its own + peers' models into its memory
  bindings block at session start; review requests name the author's model so
  the ledger records which model produced and which gated each artifact.
