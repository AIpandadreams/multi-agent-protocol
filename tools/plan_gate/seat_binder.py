#!/usr/bin/env python3
"""seat_binder — writes the production seat source (a fleet ruling's D1 follow-up,
commissioned by an orchestrator ruling after the measurement that nothing populates it).

MECHANISM, and why this hook point: the session itself cannot learn its own
session id (no env carries it), and at SessionStart the seat is not yet chosen —
but a PostToolUse hook on the Skill tool observes the /wake invocation, and its
payload carries BOTH the session id and the requested role. That is the one
moment both halves of `plans/.seat.<session_key>` exist in one place.

Writes the session-keyed lock the resolver already reads
(stop_observer.resolve_seat, second source). Session-keyed, never
workspace-global: every live seat shares this working tree, and a global file
would be misread by whichever seat stopped last.

NEVER blocks, exits 0 on every path, and is silent unless it binds — the wake
must not gain a failure mode from its own bookkeeping. An unrecognized role
string writes NOTHING (never guessed); the observer keeps saying UNRESOLVED,
which is the honest state.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_common as pc  # noqa: E402

CANON = {"owner", "builder", "orchestrator", "creator", "sentinel", "intake"}
ALIASES = {"engine": "owner", "helper": "builder", "orch": "orchestrator"}
WAKE_SKILLS = {"wake", "agent-protocol:wake"}


def seat_from_args(args: str) -> str | None:
    """First token of the skill args is the requested role; everything after is
    free text ('orchestrator — 7 PM sitrep...'). Unrecognized -> None, never a
    guess."""
    tok = (args or "").strip().split()
    if not tok:
        return None
    v = tok[0].strip().lower()
    v = ALIASES.get(v, v)
    return v if v in CANON else None


def main() -> int:
    try:
        raw = sys.stdin.read()
    except Exception:
        return 0
    raw = raw.lstrip("﻿")  # PowerShell pipes prepend a BOM; measured 08-07
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0

    tin = payload.get("tool_input") or {}
    if not isinstance(tin, dict):
        return 0
    skill = str(tin.get("skill") or "").strip().lower()
    if skill not in WAKE_SKILLS:
        return 0
    # Subagents never hold a seat; an agent-spawned wake must not bind one.
    #
    # ⭐ DELIBERATELY OPPOSITE to stop_guard.seat_from_transcript, which DOES
    #    let a subagent inherit its parent's seat. Ruled deliberate by an
    #    orchestrator ruling — do not align them. This site answers *may this session
    #    declare a seat identity?* (an agent must not mint one). That one
    #    answers *whose tree is this?* (a subagent holds the spawning seat's
    #    tree, so inheriting is correct). One rule forced onto both breaks
    #    whichever question it was not built for.
    if payload.get("agent_id") or payload.get("agent_type"):
        return 0

    seat = seat_from_args(str(tin.get("args") or ""))
    if seat is None:
        return 0  # honest UNRESOLVED beats a guessed binding

    session = str(payload.get("session_id") or "")
    if not session:
        return 0
    workspace = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    lock = workspace / "plans" / f".seat.{pc.session_key(session)}"
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(seat + "\n", encoding="utf-8")
        # The one line of output: visible in the transcript, greppable later.
        print(f"[seat_binder] bound session to seat={seat} ({lock.name})")
    except OSError:
        pass  # the observer keeps reporting UNRESOLVED; nothing worse happens
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # a wake must never fail on its own bookkeeping
        try:
            sys.stderr.write(f"[seat_binder] non-fatal: {exc}\n")
        except Exception:
            pass
        sys.exit(0)
