#!/usr/bin/env python3
"""stop_observer — turn-end receipt writer (fleet ruling item D1, Phase A).

WHAT IT IS: a Stop hook that NEVER blocks. On every turn end it computes the
bound seat's RUNNABLE projection from plans/*.plan.yaml and appends one receipt
line to plans/.stop_log.<session>. Its entire product is the RECORD; the daily
per-seat count of "stopped with runnable work" is what the sitrep reports.

WHY IT DOES NOT BLOCK: the design's blocking layer went two SOP-7 rounds and all
four verdicts said REVISE. A turn-end block either exempts nearly every
interactive turn (and catches nothing) or interrupts the principal
mid-conversation. Mechanical refusal lives at the /sleep boundary instead, where
that dilemma does not reach. Design + verdicts: in the private workspace.

KNOWN MIS-COUNT, BOTH DIRECTIONS — stated here so no reader has to rediscover it:
  UNDER: obligations living in channel entries, head dispatch regions and the
         auth-log are not ledgered, so a seat holding one counts clean. Ledgering
         your work is what makes you countable.
  OVER:  a stale `state: open` plan hits at every turn boundary; an in-flight
         dispatch (a codex round, a spawned agent) stays RUNNABLE while the seat
         MUST end the turn to receive the result.
An explanation duty attached to a raw non-zero count therefore fires on known
false positives. The duty starts only after a triage window separates those
classes (fleet ruling item D1).

EVERY path emits a receipt, including empty-RUNNABLE, unresolved seat, and load
failure — a silent allow would make the instrument's own death indistinguishable
from a quiet fleet. Exit is always 0.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_common as pc  # noqa: E402

# Canonical seats (frozen plan schema) + the wake resolver's alias tiers. An
# unrecognized value is NEVER guessed into a seat: it is recorded as a DEFECT
# and the receipt says so.
CANON = {"owner", "builder", "orchestrator", "creator", "sentinel", "intake"}
ALIASES = {"engine": "owner", "helper": "builder", "orch": "orchestrator"}
OPEN_STATUS = {"pending", "in-progress", "blocked"}


def resolve_seat(workspace: Path, session: str) -> tuple[str | None, str]:
    """Return (seat, how). Session-keyed first: a workspace-global file is
    misread by two concurrent sessions, which is why it is not the primary."""
    env = os.environ.get("PA_SEAT")
    if env:
        v = env.strip().lower()
        v = ALIASES.get(v, v)
        return (v, "env") if v in CANON else (None, f"env-unknown:{env.strip()}")
    lock = workspace / "plans" / f".seat.{pc.session_key(session)}"
    try:
        v = lock.read_text(encoding="utf-8").strip().lower()
        v = ALIASES.get(v, v)
        return (v, "session-lock") if v in CANON else (None, f"lock-unknown:{v}")
    except OSError:
        return (None, "unresolved")


# >>> -297 judgment_state (shared, byte-identical in 3 consumers) >>>
# Per a fleet ruling. A step closes BY JUDGMENT when its ruling says
# the machine bar is unreachable: no status flip and no evidence write come from
# its done_when. ANY malformation reads as ABSENT -- the row keeps today's
# behaviour (visible, dispatchable) and plan_lint reports the shape. Failing
# toward visibility is the design: a typo must never hide live work.
# Id grammars are open-ended (3+ / 4+ / 1+ digits) so they cannot age out.
# ASCII digits only: `\d` also admits other scripts' digits (SOP-7 r2 opus 1(a)).
_JUDGMENT_KEYS = frozenset(("ruling", "closed_record"))
_JUDGMENT_RULING_RE = re.compile(r"T2-RUL-(?:engine|builder)-[0-9]{3,}|auth-[0-9]{4,}")
_JUDGMENT_RECORD_RE = re.compile(r"E[0-9]+-[eb]")


def judgment_state(step):
    """(ruling, closed_record) for a WELL-FORMED `judgment` field, else
    (None, None). closed_record is None for an open judgment row."""
    if not isinstance(step, dict):
        return None, None
    j = step.get("judgment")
    if not isinstance(j, dict) or set(j) != _JUDGMENT_KEYS:
        return None, None
    ruling, rec = j["ruling"], j["closed_record"]
    if not (isinstance(ruling, str) and _JUDGMENT_RULING_RE.fullmatch(ruling)):
        return None, None
    if rec is None:
        return ruling, None
    if isinstance(rec, str) and _JUDGMENT_RECORD_RE.fullmatch(rec):
        return ruling, rec
    return None, None
# <<< -297 judgment_state <<<


def runnable(workspace: Path, seat: str) -> tuple[list[str], list[str]]:
    """(runnable step ids, notes). Notes carry every exclusion reason and every
    load error, so a green receipt can be told apart from an empty population."""
    notes: list[str] = []
    plans, errors = pc.load_plans(workspace)
    for e in errors:
        notes.append(f"load-error:{e}")
    opens = pc.open_plans(plans)
    notes.append(f"plans={len(plans)} open={len(opens)}")
    now = pc.utcnow()
    ids: list[str] = []
    parked = parked_by_constraints(opens, now, notes)
    for p in opens:
        pid = pc.plan_id(p)
        for step in p.get("steps", []) or []:
            if not isinstance(step, dict):
                notes.append(f"{pid}: non-mapping step (schema defect)")
                continue
            sid = step.get("id")
            owner = step.get("owner")
            if not isinstance(owner, str):
                # REQUIRED by the frozen schema; never fall back to owner_seat.
                notes.append(f"{pid}/{sid}: step has no owner (schema defect)")
                continue
            if ALIASES.get(owner.strip().lower(), owner.strip().lower()) != seat:
                continue
            status = step.get("status")
            if status not in OPEN_STATUS:
                continue
            j_ruling, j_record = judgment_state(step)
            if j_record is not None:
                # -297, per a fleet ruling: closed BY JUDGMENT on a lane record; its
                # done_when is unreachable by ruling, so it is not runnable.
                # Named in the notes so the exclusion is never silent.
                notes.append(f"{pid}/{sid}: judged-closed:{j_record} (ruling {j_ruling})")
                continue
            if status == "blocked":
                # Blocked-exit ruling cure: the believed-blocked exit
                # keys on an AUTHORED precondition that resolves to a
                # CURRENTLY-UNRULED GATE in this plan — the one authored form
                # that mechanically substantiates "blocked". The old key,
                # `blocked_by`, was derived and never authored: dead as an
                # escape for legitimate blocks, unchecked if ever populated.
                # Malformed/unknown/empty/step/clock preconditions never make
                # the believed list (anti-gaming: bare `blocked` still counts).
                # Bound, stated: the generic precond check below still excludes
                # ANY status on unmet/unknown refs — frozen FD-3 semantics,
                # pre-existing and untouched here.
                gates = pc.index_by_id(p, "gates")
                pres = step.get("preconditions")
                unruled = ([r for r in pres if isinstance(r, str) and r in gates
                            and gates[r].get("ruled") is None]
                           if isinstance(pres, list) else [])
                if unruled:
                    notes.append(f"{pid}/{sid}: blocked, believed "
                                 f"(unruled gate {','.join(unruled)})")
                    continue
                notes.append(f"{pid}/{sid}: blocked without unruled-gate "
                             f"precondition (counted)")
            try:
                if not pc.precond_satisfied(p, step, now):
                    continue
            except Exception as exc:  # a defect in one plan must not blind the rest
                notes.append(f"{pid}/{sid}: precond check failed: {exc}")
                continue
            full = f"{pid}/{sid}"
            if full in parked:
                # owner E1604 (2026-08-18): the "Runnable now" list is a
                # dispatch surface FZ1's reader census missed — it listed
                # three PARKED steps as runnable. A live constraint may
                # carry a `PARKS: <plan>/<step>, ...` token in its rule;
                # those steps are excluded here, with the constraint named,
                # so the exclusion is a measured reason and not a silence.
                notes.append(f"{full}: parked-by:{parked[full]}")
                continue
            ids.append(full)
    return ids, notes


PARKS_RE = re.compile(r"PARKS:\s*([A-Za-z0-9_/-]+(?:\s*,\s*[A-Za-z0-9_/-]+)*)")


def parked_by_constraints(opens: list[dict], now,
                          notes: list[str] | None = None) -> dict[str, str]:
    """{'<plan>/<step>': '<plan>/<constraint>'} for every step named in a
    `PARKS:` token of a LIVE constraint on ANY open plan (a fleet-wide freeze
    lives on one plan and parks steps on others). Token grammar: `PARKS:` then
    comma-separated `<plan_id>/<step_id>` ids; ends at the first character
    outside [A-Za-z0-9_/-] — so a trailing period or a `;` closes it. A
    constraint whose `until` is not live parks nothing (the freeze lifts when
    its gate rules, without anyone editing the rule text)."""
    parked: dict[str, str] = {}
    notes = notes if notes is not None else []
    known_steps = {f"{pc.plan_id(p)}/{s.get('id')}" for p in opens
                   for s in (p.get("steps") or []) if isinstance(s, dict)}
    for p in opens:
        pid = pc.plan_id(p)
        gates_map = pc.index_by_id(p, "gates")
        for c in p.get("constraints", []) or []:
            if not isinstance(c, dict):
                continue
            rule = c.get("rule")
            if not isinstance(rule, str) or "PARKS:" not in rule:
                continue
            if not pc.constraint_active(c, gates_map, now):
                continue
            cid = c.get("id")
            for m in PARKS_RE.finditer(rule):
                for tok in m.group(1).split(","):
                    tok = tok.strip()
                    if not tok:
                        continue
                    # owner E1606 (2026-08-18): a token that names no real
                    # step is INERT enforcement - the same shape as a gate
                    # `until` that never resolves. Every entry must carry a
                    # `/` and resolve to an existing <plan>/<step>; anything
                    # else is a LOUD note, never a silent drop.
                    if "/" not in tok:
                        notes.append(f"{pid}/{cid}: PARKS entry {tok!r} has no "
                                     f"'/' (needs <plan>/<step>) - parks NOTHING")
                        continue
                    if tok not in known_steps:
                        notes.append(f"{pid}/{cid}: PARKS entry {tok!r} names no "
                                     f"open step - parks NOTHING (typo/renamed?)")
                        continue
                    parked.setdefault(tok, f"{pid}/{cid}")
    return parked


def main() -> int:
    raw = ""
    try:
        raw = sys.stdin.read()
    except Exception:
        pass
    # lstrip the BOM: some shells prepend one on a pipe, and a payload that
    # fails to parse costs the receipt its session id — the field every later
    # reconciliation joins on.
    raw = raw.lstrip("﻿")
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    session = str(payload.get("session_id") or "unknown")
    workspace = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    # Subagents stop constantly and own no ledger steps; exempt by an explicit
    # field check, never by absence-of-wiring.
    if payload.get("agent_id") or payload.get("agent_type"):
        line = f"{pc.utcnow().isoformat()} session={session} SUBAGENT-EXEMPT"
        pc.append_line(workspace / "plans" / f".stop_log.{pc.session_key(session)}", line)
        return 0

    seat, how = resolve_seat(workspace, session)
    stamp = pc.utcnow().isoformat()
    if seat is None:
        line = (f"{stamp} session={session} seat=UNRESOLVED({how}) "
                f"runnable=n/a decision=allow-with-record")
    else:
        ids, notes = runnable(workspace, seat)
        line = (f"{stamp} session={session} seat={seat}({how}) "
                f"runnable={len(ids)} ids={';'.join(ids) if ids else '-'} "
                f"notes={' | '.join(notes) if notes else '-'} decision=allow-with-record")
    pc.append_line(workspace / "plans" / f".stop_log.{pc.session_key(session)}", line)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # never block a turn end, never die silently
        try:
            sys.stderr.write(f"[stop_observer] non-fatal: {exc}\n")
        except Exception:
            pass
        sys.exit(0)
