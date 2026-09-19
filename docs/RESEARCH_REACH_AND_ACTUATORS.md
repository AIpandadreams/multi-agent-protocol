# Research: expanding the one-agent interface — OpenJarvis + Hermes (2026-07-04)

Question (principal): can OpenJarvis (github.com/open-jarvis/OpenJarvis) and
"Hermes agent" enhance the interface "so I can control more from one
interface and one agent"?

Finding: neither is the old voice/IoT Jarvis — both are 2026 LLM-agent
frameworks overlapping what this repo already builds (OpenJarvis natively
imports ~150 skills from Hermes Agent). Value = REACH (more ways to reach the
one orchestrator) and ACTUATORS (more things it can control), never a second
brain. Ranked by control-surface gained per unit of integration effort.
Star counts approximate [VERIFY before citing externally].

## 1. Hermes Agent gateway daemon — instant multi-channel REACH (adopt)

- NousResearch, MIT, `github.com/NousResearch/hermes-agent`. Persistent file
  memory, agentskills.io document skills, cron scheduler, subagent spawning,
  40+ tools, and a **gateway daemon** bridging one agent to Telegram / Discord
  / Slack / WhatsApp / Signal / CLI **with voice-memo transcription**.
  Claude-native. Extremely active (launched 2026-02-25; v0.18.0 /
  v2026.7.1 on 2026-07-01).
- Offer: "reach my agent from anywhere" becomes config — a phone chat app +
  voice memos transcribed into the TASKQUEUE = wake-word substitute with zero
  voice stack. Also the closest reference implementation of this repo's
  memory/cron/skills stack.
- Adopt the **gateway as the orchestrator's front door — transport only**.
  Constraint: the gateway couples to Hermes's own agent loop; run it purely
  as intake handing text to the orchestrator (or reimplement thinly on one
  messaging API). The auto-executing Hermes agent is NEVER the controller
  (audit-PII, cloud-DB hard rules, role separation).

## 2. MQTT bus via Wyoming / HA Assist — device + LAN ACTUATION (borrow pattern)

- The Snips/Rhasspy "Hermes" MQTT+JSON voice bus is the right PATTERN
  (language-agnostic pub/sub) but Snips is defunct — build on **Home
  Assistant Assist + Wyoming protocol** or plain Mosquitto.
- Offer: highest actuation surface per effort. Orchestrator subscribes
  `intent/text`, publishes `command/*` — one uniform bus driving home devices
  AND the ComfyUI rigs / RTX 3080+4080 boxes (tiny subscriber per machine:
  start renders, report GPU status).
- Borrow the bus pattern on the modern stack; skip Snips.

## 3. OpenJarvis engine layer — local GPU inference as a resource (borrow)

- Stanford Hazy Research / Scaling Intelligence Lab, Apache-2.0, "Intelligence
  Per Watt" (arXiv 2605.17172) [VERIFY]. Five composable layers; 8 built-in
  agents incl. `orchestrator`, `morning_digest`, `monitor_operative`. Alive
  (~7.3k stars, desktop-v1.0.2 2026-05-25). Full stack, not scaffolding.
- Offer: `InferenceEngine` abstraction (Ollama/vLLM/SGLang/llama.cpp/MLX
  behind one interface with energy/latency/cost telemetry) → the GPU boxes
  become a measured inference resource feeding MODELS.md; its digest/monitor
  presets are design references for the briefing + idle tick.
- Borrow the engine abstraction; optionally `jarvis serve` for a local
  OpenAI-compatible endpoint. Optimization, not new reach.

## 4. Room wake-word satellites (Willow / Wyoming satellites) — defer

True hands-free per-room voice; worst effort ratio (hardware + tuning).
Voice-memo-from-phone (#1) covers ~80% of voice control at ~5% of the effort.

## Protocol placement (v2.5 terms)

All four are TRANSPORT/ACTUATOR bindings, not roles: #1 is a PRINCIPAL-
interface intake binding (text lands in TASKQUEUE; it can never carry
authorization any more than a channel entry can — untrusted-input rule
applies to transcribed voice too); #2 is a PINNED_RESOURCES + dispatch
surface; #3 feeds MODELS.md. The orchestrator stays the sole controller;
owner/builder/reviewer separation and gates unchanged. Sequencing: candidate
work for Phase 4+ (PA live first); the principal picks if/when.
