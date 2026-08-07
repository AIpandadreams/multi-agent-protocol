#!/usr/bin/env python3
"""plan_common.py — shared plan-ledger access for the ledger hooks.

Consumed by compaction_inject.py (PreCompact / SessionStart) and by the
enforcement gate plan_gate.py (PreToolUse; deferred to its own release).
Reads the plan ledgers (schema: docs/PLAN-LEDGER.md) TOLERANTLY: the hook
is not the linter — malformed values degrade to "no claim", except that an
unreadable/unparseable plan FILE is surfaced as a load error so the caller
can apply its declared fail direction (closed for gated classes, open for
read-only).

Imports: standard library + PyYAML only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError as exc:   # PyYAML is the one non-stdlib prerequisite.
    if getattr(exc, "name", None) != "yaml":
        raise                # a present-but-BROKEN install (transitive import
                             # failure) is not "not installed" — surface it.
    yaml = None              # load_plans degrades to a load error (caller
                             # applies its declared fail direction) rather
                             # than crashing a session-start hook.

PLANS_DIRNAME = "plans"
PENDING_NAME = ".compaction_pending"    # written at PreCompact (--mark); SESSION-KEYED
SIDECAR_NAME = ".last_injection"        # written after successful injection; SESSION-KEYED
OVERRIDE_NAME = ".override_once"        # one-shot false-block override; SESSION-KEYED
MARK_FAIL_NAME = ".plan_gate_mark_failed"  # durable fail-closed sentinel at WS ROOT
BLOCK_LOG_NAME = ".block_log"           # false-block review ledger
TOUCH_LOG_NAME = ".touch_log"           # PASS touch records for gated actions

# Coordinate KIND -> plan coordinates field it is matched against.
KIND_FIELD = {"repo": "repos", "task": "ids", "name": "ids", "url": "ids"}


def plans_dir(workspace: str | Path) -> Path:
    return Path(workspace) / PLANS_DIRNAME


def sidecar_path(workspace: str | Path, name: str) -> Path:
    return plans_dir(workspace) / name


def session_key(session: str) -> str:
    """Filesystem-safe session key for session-keyed sidecars (session-keyed
    so concurrent seats cannot stomp each other's state).

    Review-hardened: an earlier form was `sanitize(session)[:40]`
    — two sessions sharing a 40-character prefix collided, and B's injection
    then DELETED A's pending mark, recreating the overlapping-compaction
    false accept. The key is now a truncated readable prefix PLUS a
    collision-resistant digest of the FULL session id, so distinct sessions
    can never share a key regardless of prefix length."""
    s = str(session)
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', s)[:32]
    return f"{safe}-{hashlib.sha256(s.encode('utf-8')).hexdigest()[:12]}"


def pending_path(workspace: str | Path, session: str) -> Path:
    return plans_dir(workspace) / f"{PENDING_NAME}.{session_key(session)}"


def injection_path(workspace: str | Path, session: str) -> Path:
    return plans_dir(workspace) / f"{SIDECAR_NAME}.{session_key(session)}"


def override_path(workspace: str | Path, session: str) -> Path:
    return plans_dir(workspace) / f"{OVERRIDE_NAME}.{session_key(session)}"


def mark_fail_sentinel(workspace: str | Path, session: str) -> Path:
    """WS ROOT, not plans/ — a failed write inside plans/ is exactly the case
    this sentinel must survive."""
    return Path(workspace) / f"{MARK_FAIL_NAME}.{session_key(session)}"


def ledger_sha(workspace: str | Path) -> str | None:
    """sha256 hex over every plans/*.plan.yaml (sorted by filename;
    each file contributes its name + NUL + bytes). Binds an --ack to the
    CURRENT ledger state. None if the ledger is unreadable."""
    pdir = plans_dir(workspace)
    if not pdir.is_dir():
        return None
    h = hashlib.sha256()
    try:
        for f in sorted(pdir.glob("*.plan.yaml")):
            h.update(f.name.encode("utf-8"))
            h.update(b"\0")
            h.update(f.read_bytes())
    except OSError:
        return None
    return h.hexdigest()


def load_plans(workspace: str | Path) -> tuple[list[dict], list[str]]:
    """Tolerant load of plans/*.plan.yaml.

    Returns (plans, errors). Each loaded plan dict gains '_path'.
    - plans dir missing entirely: legitimate pre-adoption state -> ([], []).
    - plans dir unlistable / a file: error (caller decides direction).
    - one file unreadable or unparseable: error for that file; others load.
    """
    pdir = plans_dir(workspace)
    plans: list[dict] = []
    errors: list[str] = []
    if yaml is None:
        errors.append(
            "PyYAML is not installed — plan ledgers cannot be read "
            "(pip install pyyaml); treating the ledger as unreadable")
        return plans, errors
    if not pdir.exists():
        return plans, errors
    if not pdir.is_dir():
        errors.append(f"{pdir} exists but is not a directory")
        return plans, errors
    try:
        files = sorted(pdir.glob("*.plan.yaml"))
    except OSError as exc:
        errors.append(f"cannot list {pdir}: {exc}")
        return plans, errors
    for f in files:
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"{f.name}: unreadable/unparseable: {exc}")
            continue
        if not isinstance(doc, dict):
            errors.append(f"{f.name}: not a YAML mapping")
            continue
        doc["_path"] = str(f)
        plans.append(doc)
    return plans, errors


def open_plans(plans: list[dict]) -> list[dict]:
    return [p for p in plans if p.get("state") == "open"]


def plan_id(plan: dict) -> str:
    pid = plan.get("project_id")
    return pid if isinstance(pid, str) else Path(plan.get("_path", "?")).name


def parse_dt(val: object) -> datetime | None:
    if not isinstance(val, str):
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except ValueError:
        return None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _entries(plan: dict, key: str) -> list[dict]:
    v = plan.get(key)
    if not isinstance(v, list):
        return []
    return [e for e in v if isinstance(e, dict)]


def index_by_id(plan: dict, key: str) -> dict[str, dict]:
    return {e["id"]: e for e in _entries(plan, key) if isinstance(e.get("id"), str)}


def precond_satisfied(plan: dict, step: dict, now: datetime) -> bool:
    """Frozen semantics (see docs/PLAN-LEDGER.md): step id = that step is done;
    gate id = that gate is ruled; clock id = not before that clock fires.
    Unknown reference -> conservatively unsatisfied."""
    steps = index_by_id(plan, "steps")
    gates = index_by_id(plan, "gates")
    clocks = index_by_id(plan, "clocks")
    pres = step.get("preconditions")
    if not isinstance(pres, list):
        return True
    for ref in pres:
        if ref in steps:
            if steps[ref].get("status") != "done":
                return False
        elif ref in gates:
            if gates[ref].get("ruled") is None:
                return False
        elif ref in clocks:
            c = clocks[ref]
            if c.get("fired") is None:
                dt = parse_dt(c.get("fires_at"))
                if dt is None or dt > now:
                    return False
        else:
            return False
    return True


def coord_values(coords: object, field: str) -> list[str]:
    if not isinstance(coords, dict):
        return []
    v = coords.get(field)
    if not isinstance(v, list):
        return []
    return [x for x in v if isinstance(x, str)]


def licensed_coords(opens: list[dict], field: str, now: datetime) -> dict[str, str]:
    """Coordinate value -> human-readable license source. Licensed = the
    plan's top-level coordinates, plus step-local coordinates of steps whose
    preconditions are satisfied (status pending/in-progress/done)."""
    out: dict[str, str] = {}
    for p in opens:
        pid = plan_id(p)
        for v in coord_values(p.get("coordinates"), field):
            out.setdefault(v, f"plan {pid} (top-level coordinates)")
        for s in _entries(p, "steps"):
            if s.get("status") in ("pending", "in-progress", "done") \
                    and precond_satisfied(p, s, now):
                for v in coord_values(s.get("coordinates"), field):
                    out.setdefault(v, f"plan {pid} step {s.get('id')}")
    return out


def coord_population(opens: list[dict], field: str) -> dict[str, str]:
    """ALL coordinates of this field across open plans (top-level + every
    step, regardless of status/preconditions). Non-empty population + no
    license = the CONTRADICT branch's evidence set."""
    out: dict[str, str] = {}
    for p in opens:
        pid = plan_id(p)
        for v in coord_values(p.get("coordinates"), field):
            out.setdefault(v, f"plan {pid} (top-level coordinates)")
        for s in _entries(p, "steps"):
            for v in coord_values(s.get("coordinates"), field):
                out.setdefault(v, f"plan {pid} step {s.get('id')}")
    return out


def unmet_step_license(opens: list[dict], field: str, value: str,
                       now: datetime) -> tuple[str, str] | None:
    """If `value` appears in a step whose preconditions are UNMET, return
    (plan_id, step_id) so the block can say which gate/step is owed."""
    for p in opens:
        for s in _entries(p, "steps"):
            if value in coord_values(s.get("coordinates"), field) \
                    and not precond_satisfied(p, s, now):
                return plan_id(p), str(s.get("id"))
    return None


def done_coord_index(plans: list[dict], field: str) -> dict[str, dict]:
    """Duplicate-execution index: coordinate value -> the DONE step that
    already produced it (status done + non-null evidence), across ALL plans
    including closed/aborted ones."""
    out: dict[str, dict] = {}
    for p in plans:
        pid = plan_id(p)
        for s in _entries(p, "steps"):
            if s.get("status") == "done" and isinstance(s.get("evidence"), dict):
                for v in coord_values(s.get("coordinates"), field):
                    out.setdefault(v, {
                        "plan": pid,
                        "step": str(s.get("id")),
                        "ran": s["evidence"].get("ran"),
                        "log_path": s["evidence"].get("log_path"),
                    })
    return out


def constraint_active(constraint: dict, gates_map: dict[str, dict],
                      now: datetime) -> bool:
    """`until: close` -> active while the plan is open. `until: gate:<id>`
    -> active while that gate is unruled (unknown gate -> active,
    conservative). `until: <datetime>` -> active before that instant
    (unparseable -> active, conservative — the linter owns form)."""
    until = constraint.get("until")
    if until is None or until == "close":
        return True
    if isinstance(until, str) and until.startswith("gate:"):
        g = gates_map.get(until[len("gate:"):])
        return g is None or g.get("ruled") is None
    dt = parse_dt(until)
    return dt is None or now < dt


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_json(path: Path, obj: object) -> bool:
    """ATOMIC write: temp file in the same
    directory + os.replace, so a concurrent reader never observes a
    half-written sidecar and a crashed writer never truncates the previous
    state. Falls back to nothing — a failed write returns False and the
    callers' fail-CLOSED direction takes over."""
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    try:
        tmp.write_text(json.dumps(obj, indent=1), encoding="utf-8")
        os.replace(tmp, path)
        return True
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        return False


def append_line(path: Path, line: str) -> bool:
    """Best-effort single-line append (byte-append discipline: open in append
    mode, never rewrite)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line.rstrip("\n") + "\n")
        return True
    except OSError:
        return False


# -------------------------------------------------------------------- digest

def render_digest(plans: list[dict], errors: list[str], nonce: str,
                  now: datetime) -> str:
    """Typed digest of every OPEN plan: open steps, unruled gates, unfired
    clocks, active constraints, authorities — a projection of typed fields,
    never a summary. May drop nothing that is open/pending/unruled/unfired
    (the digest contract in docs/PLAN-LEDGER.md)."""
    lines = [
        f"=== PLAN LEDGER DIGEST (typed, non-lossy carrier; injection nonce {nonce}) ===",
        "This digest is rendered from plans/*.plan.yaml by compaction_inject.py.",
        "The compaction summary is lossy; THIS block is the carrier of record for",
        "open coordinates, gates, clocks, and constraints. Verify against the",
        "ledger files before any gated side effect.",
    ]
    for e in errors:
        lines.append(f"!! PLAN LOAD ERROR (digest incomplete): {e}")
    opens = open_plans(plans)
    if not opens:
        lines.append("(no open plans)")
    for p in opens:
        pid = plan_id(p)
        lines.append("")
        lines.append(f"PLAN {pid} [open] owner_seat={p.get('owner_seat')} — {p.get('title')}")
        coords = p.get("coordinates")
        for field in ("repos", "paths", "branches", "ids"):
            vals = coord_values(coords, field)
            if vals:
                lines.append(f"  coordinates.{field}: {vals}")
        gates_map = index_by_id(p, "gates")
        for s in _entries(p, "steps"):
            if s.get("status") in ("done", "superseded"):
                continue
            lines.append(f"  STEP {s.get('id')} [{s.get('status')}] owner={s.get('owner')} — {s.get('desc')}")
            sc = s.get("coordinates")
            for field in ("repos", "paths", "branches", "ids"):
                vals = coord_values(sc, field)
                if vals:
                    lines.append(f"    coordinates.{field}: {vals}")
            pres = s.get("preconditions")
            if pres:
                lines.append(f"    preconditions: {pres}")
        for g in _entries(p, "gates"):
            if g.get("ruled") is None:
                lines.append(f"  GATE {g.get('id')} UNRULED ruler={g.get('ruler')} unblocks={g.get('unblocks')} — {g.get('question')}")
        for k in _entries(p, "clocks"):
            if k.get("fired") is None:
                lines.append(f"  CLOCK {k.get('id')} [{k.get('kind')}] fires_at={k.get('fires_at')} — {k.get('action')}")
        for c in _entries(p, "constraints"):
            if constraint_active(c, gates_map, now):
                blocks = c.get("blocks") or {}
                lines.append(
                    f"  CONSTRAINT {c.get('id')} ACTIVE blocks tool={blocks.get('tool')} "
                    f"pattern={blocks.get('arg_pattern')!r} until={c.get('until')} — {c.get('rule')}"
                )
        for a in _entries(p, "authorities"):
            lines.append(f"  AUTHORITY {a.get('auth')} — {a.get('scope')}")
    # The digest also carries the done-record (already-produced
    # coordinates across ALL plans incl. closed), so an agent reasoning from
    # the injected context alone still sees what was already delivered.
    done_lines: list[str] = []
    for field in ("repos", "paths", "branches", "ids"):
        for v, d in sorted(done_coord_index(plans, field).items()):
            done_lines.append(
                f"  DONE coordinates.{field}: {v} <- plan {d['plan']} step "
                f"{d['step']} ran {d['ran']} (do NOT re-create)")
    if done_lines:
        lines.append("")
        lines.append("ALREADY-DONE COORDINATES (duplicate index, all plans incl. closed):")
        lines.extend(done_lines)
    lines.append("")
    lines.append(f"=== END PLAN LEDGER DIGEST (nonce {nonce}, rendered {now.isoformat(timespec='seconds')}) ===")
    return "\n".join(lines)
