#!/usr/bin/env python3
"""plan_common.py — shared plan-ledger access for the stream-c hooks.

Round memory-overhaul-r1, Stream C. Consumed by plan_gate.py (PreToolUse)
and compaction_inject.py (PreCompact / SessionStart). Reads the frozen
schema-v1 plan ledgers (SCHEMA_FREEZE.md, stream-a) TOLERANTLY: the hook is
not the linter — malformed values degrade to "no claim", except that an
unreadable/unparseable plan FILE is surfaced as a load error so the caller
can apply its declared fail direction (closed for gated classes, open for
read-only).

Imports: standard library + PyYAML only (stream charge hard rule).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

# Per an orchestrator ruling: graceful degradation, matching the canonical form. This module is
# imported by the SessionStart hook chain — a bare import crashed EVERY session start
# the moment PyYAML broke, which turns a library problem into a workspace outage. With
# yaml=None, load_plans reports every plan file as an error instead (loud, per-file,
# caller decides direction) and session start proceeds.
try:
    import yaml
except ImportError:
    yaml = None

PLANS_DIRNAME = "plans"
PENDING_NAME = ".compaction_pending"    # written at PreCompact (--mark); SESSION-KEYED (F7-3 cure)
SIDECAR_NAME = ".last_injection"        # written after successful injection; SESSION-KEYED (F7-3 cure)
OVERRIDE_NAME = ".override_once"        # one-shot false-block override (C4-1/C4-5 cure); SESSION-KEYED
MARK_FAIL_NAME = ".plan_gate_mark_failed"  # durable fail-closed sentinel at WS ROOT (F7-4 cure)
BLOCK_LOG_NAME = ".block_log"           # false-block review ledger (GAP_TESTS xc-4)
TOUCH_LOG_NAME = ".touch_log"           # PASS touch records for gated actions
HEARTBEAT_NAME = ".daemon_heartbeat"    # clock-daemon sweep stamp (written by tools/clock_daemon.py)

# Per the same orchestrator ruling. The clock daemon's staleness threshold, in SECONDS, as ONE constant.
#
# ⚠ THE COMPARISON IS IN SECONDS AND THE REPORT IS IN MINUTES, and that is not a
# cosmetic split: the wake procedure compares strictly-greater-than 900 s but prints
# the age in whole minutes ROUNDED UP, so the printed age can never read below the
# printed threshold. A consumer that compares minutes would call a 900.5 s stamp
# "15 min old, threshold 15" and pass it.
HEARTBEAT_STALE_S = 900

# Coordinate KIND -> plan coordinates field it is matched against.
KIND_FIELD = {"repo": "repos", "task": "ids", "name": "ids", "url": "ids"}


def plans_dir(workspace: str | Path) -> Path:
    return Path(workspace) / PLANS_DIRNAME


def sidecar_path(workspace: str | Path, name: str) -> Path:
    return plans_dir(workspace) / name


def session_key(session: str) -> str:
    """Filesystem-safe session key for session-keyed sidecars (F7-3 cure:
    concurrent seats must not stomp each other's F1 state).

    CURE-2 (codex delta finding 5): the r1 form was `sanitize(session)[:40]`
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
    this sentinel must survive (F7-4 cure)."""
    return Path(workspace) / f"{MARK_FAIL_NAME}.{session_key(session)}"


def ledger_sha(workspace: str | Path) -> str | None:
    """sha256 hex over every plans/*.plan.yaml (sorted by filename;
    each file contributes its name + NUL + bytes). Binds an --ack to the
    CURRENT ledger state (F7-2 cure). None if the ledger is unreadable."""
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


# ── Per an orchestrator ruling: time fields must be STRINGS, and a violation is LOUD ─────
# YAML's implicit resolver turns an UNQUOTED ISO timestamp into a datetime.
# `parse_dt` refuses non-strings by design (see its docstring -- it must not
# guess a timezone), returns None, and every caller then takes its conservative
# branch. For `fires_at` that branch is "precondition UNSATISFIED", so a clock
# that fired hours ago never satisfies anything and the dependent step is
# invisible FOREVER -- with no error, no note, and a plausible count of zero.
#
# Measured 2026-09-03 on a two-arm fixture differing only in quote marks:
#   fires_at: "<past>"  -> load-errors 0, runnable 1
#   fires_at:  <past>   -> load-errors 0, runnable 0   <- silent
#
# SCOPE IS MEASURED, NOT GUESSED. These are exactly the two plan-file fields
# `parse_dt` consumes (plan_common `clocks[].fires_at` in precond_satisfied,
# `constraints[].until` in constraint_active, and the same pair in
# runnable_cache.next_time_boundary). `fired` and `ruled` are tested with
# `is None` and never parsed, so typing them would be noise with no safety
# behind it [[claim-bounding-discipline]].
_TIME_FIELDS = (("clocks", "fires_at"), ("constraints", "until"))


def time_field_defects(plan: dict) -> list[str]:
    """Diagnostics for time fields YAML has typed into something parse_dt refuses.

    THE PLAN IS NOT DROPPED, and that is deliberate. Dropping it would remove
    every OTHER step it owns from the runnable projection -- a strictly LARGER
    under-count than the one being cured, in the direction that lets a stop
    through [[honest-failure-outcomes]]. What changes here is DETECTION: the
    value is refused at load and named, instead of being silently reinterpreted
    as "not yet due".

    RESIDUAL, STATED: the affected step is still absent from the count, so this
    makes the failure LOUD without making it SAFE. Making it safe means the
    defect must BLOCK a stop rather than merely annotate it -- a change to a
    live gate's semantics, proposed to orch rather than taken here.
    """
    out: list[str] = []
    for coll, field in _TIME_FIELDS:
        for e in _entries(plan, coll):
            if field not in e:
                continue
            v = e[field]
            if v is None or isinstance(v, str):
                continue
            out.append(
                '%s/%s: %s is %s, not a string -- YAML parsed an UNQUOTED '
                'timestamp into a native type. parse_dt refuses non-strings, so '
                'this field currently reads as UNRESOLVABLE and its dependents '
                'stay conservatively unsatisfied. Fix at the source: quote it '
                '-- %s: "%s"'
                % (coll, e.get("id", "?"), field, type(v).__name__, field, v))
    return out


def unblocks_edge_defects(plan: dict) -> list[str]:
    """Diagnostics for UNRULED gates whose `unblocks` names no step in this plan.

    `gates[].unblocks` is typed as a list of step ids and accepts any string, so
    a gate can carry an English phrase where an id belongs. An unruled gate whose
    edge resolves to nothing can never unblock anything: it is a permanent stall
    with a tidy type, invisible to every projection that resolves the edge rather
    than reading it.

    RULED GATES ARE EXEMPT, and the exemption is the design, not a softening: a
    ruled gate's effect is carried by its ruling text, so a prose edge on one is
    untidy rather than load-bearing. Measured 2026-09-08: all three unresolvable
    edges on the live ledger are on ruled gates, so an unruled-only rule lands
    green on the ledger it is adopted into.

    ⛔ THIS IS REPORTED THROUGH load_plans' ERROR CHANNEL, and plan_gate escalates
    ANY loader error to a WEDGE for gated action classes -- "ONE malformed file
    stops EVERY gated action in this workspace until repaired" (plan_gate.py's own
    declared C5-1 radius). That is deliberate: the row asks for a cure at WRITE
    time, and a gate minted by hand never passes through plan_set_status' lint
    gate, so the loader is the only surface every consumer shares. The cost is
    that a typo in a new gate stops gated work until it is typed. Repair is a
    one-line edit and the message names the gate and the string.

    THE PLAN IS KEPT, never dropped -- same reasoning as time_field_defects:
    dropping it removes every OTHER step it owns from the runnable projection,
    a strictly larger under-count in the direction that lets a stop through
    [[honest-failure-outcomes]].

    Resolution is PER-PLAN. A step id that exists in a sibling ledger does not
    satisfy an edge here; cross-plan edges are not expressible in the frozen
    schema and must not be laundered into existence by a laxer resolver.
    """
    out: list[str] = []
    steps = {s["id"] for s in _entries(plan, "steps")
             if isinstance(s.get("id"), str)}
    for g in _entries(plan, "gates"):
        if g.get("ruled") is not None:
            continue                      # ruled: the ruling text carries the effect
        unb = g.get("unblocks")
        if not isinstance(unb, list):
            continue                      # shape defect: plan_lint L1 owns it
        gid = g.get("id") if isinstance(g.get("id"), str) else "?"
        for sid in unb:
            if not isinstance(sid, str):
                continue                  # shape defect: plan_lint L1 owns it
            if sid not in steps:
                out.append(
                    'gates/%s: UNRULED gate names %r in `unblocks`, which is no '
                    'step id in this plan -- the edge resolves to nothing, so the '
                    'gate can never unblock anything and no digest can show it as '
                    'a blocker. Fix at the source: type the step id, or rule the '
                    'gate.' % (gid, sid))
    return out


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
    if yaml is None and files:
        # Not silence and not a crash: every plan present is REPORTED unreadable with
        # the true cause, so the digest says "N files could not load: PyYAML missing"
        # rather than rendering an empty ledger that reads as no-open-plans.
        errors.extend(f"{f.name}: unreadable: PyYAML is not importable" for f in files)
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
        # The plan is KEPT; only the FIELD is refused. See time_field_defects.
        errors.extend(f"{f.name}: {d}" for d in time_field_defects(doc))
        # Same contract, same channel: the plan is KEPT and the EDGE is refused.
        # See unblocks_edge_defects for why only UNRULED gates are graded and
        # what the WEDGE radius of this channel costs (UNBLOCKS-RESOLVE-LINT).
        errors.extend(f"{f.name}: {d}" for d in unblocks_edge_defects(doc))
        plans.append(doc)
    return plans, errors


def open_plans(plans: list[dict]) -> list[dict]:
    return [p for p in plans if p.get("state") == "open"]


def plan_id(plan: dict) -> str:
    pid = plan.get("project_id")
    return pid if isinstance(pid, str) else Path(plan.get("_path", "?")).name


def parse_dt(val: object) -> datetime | None:
    """C-10 CURE (2026-08-14; opus p2r1 F13). Returns an AWARE datetime or None
    — NEVER a naive one.

    A no-offset ISO string parses perfectly well and then explodes at the first
    comparison against an aware `now` (`TypeError: can't compare offset-naive
    and offset-aware datetimes`). Every guard downstream tests `dt is None`, so
    a value that is BETTER-formed than "unparseable" sailed past the guard
    written for it and crashed one operator later.

    ⛔ Deliberately NOT assumed to be UTC. The one thing this must not do is
    guess the operator's timezone: a naive PAST stamp read as UTC would EXPIRE
    a live constraint, which is a silent semantic change in the unsafe
    direction. Refusing to interpret it maps it onto the callers' existing,
    documented conservative branch — `constraint_live` -> active,
    `precond_satisfied` -> unsatisfied — where the row is then reported by the
    normal `[CONSTRAINT]` path that names it.

    ⚠ Scope checked, not assumed: the other four call sites read stamps THIS
    code wrote with `utcnow().isoformat()` (`compaction_inject.py:207,286`,
    `stop_guard.py:1129,1332`) and are aware by construction, so narrowing the
    contract here cannot move them."""
    if not isinstance(val, str):
        return None
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
    except ValueError:
        return None
    # `tzinfo is None` is the WHOLE test, deliberately: `fromisoformat` yields
    # either a naive datetime or one carrying a `datetime.timezone`, whose
    # `utcoffset()` is never None. A second limb for that case was written,
    # measured UNREACHABLE from this function's only constructor, and removed
    # rather than left as a guard no test could ever reach
    # [[guards-without-input-are-not-shipped]].
    if dt.tzinfo is None:
        return None
    return dt


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
    """Frozen semantics (SCHEMA_FREEZE FD-3): step id = that step is done;
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
    """F5 duplicate-execution index: coordinate value -> the DONE step that
    already produced it (status done + non-null evidence), across ALL plans
    including closed/aborted ones (GAP_TESTS F5)."""
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
    """ATOMIC write (CURE-2, codex delta finding 5): temp file in the same
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


# --------------------------------------------------------------- digest (M4)

# S11. RULED by a fleet ruling (the principal, 2026-09-18) on the Unit B fold at
# a commit in the private workspace: 104,000 B = the measured fold (97,108 B capped) + 7,000 B.
# This SUPERSEDES the provisional 16,896 of an earlier ruling. Still a watch
# threshold, not a limit anything enforces: nothing truncates or refuses at it.
# ⚠ The margin is an OSCILLATION allowance, not a growth one — the capped
# render measured -209 B/day over the 7 days to the fold, inside a 6,221 B
# band. Re-measure trigger: any plan state transition open<->closed re-runs
# FOLD_MEASURE and re-proposes; the open-plan set at the fold is pinned in
# tools/plan_gate/compaction_inject.py, which restates this cap at the call
# site and is the banner a reader actually sees.
DIGEST_CAP_BYTES = 104000


def render_digest(plans: list[dict], errors: list[str], nonce: str,
                  now: datetime, workspace: str | Path | None = None) -> str:
    """Typed digest of every OPEN plan: open steps, unruled gates, unfired
    clocks, active constraints, authorities — a projection of typed fields,
    never a summary. May drop nothing that is open/pending/unruled/unfired
    (PLAN_SCHEMA §4 M4 contract)."""

    def _plan_byte_contributions(rendered):
        """[(plan_id, bytes)] descending — what the over-cap banner names.

        Attribution walks the rendered lines rather than re-deriving from the
        plan dicts, so the figure is of the ARTIFACT being measured and not of
        a parallel computation that could disagree with it. Trailing blocks
        (the DONE-coordinate record) are non-indented, which closes the current
        plan's span — otherwise they would be billed to whichever plan happened
        to render last.
        """
        out, cur, n = [], None, 0
        for ln in rendered:
            if ln.startswith("PLAN "):
                if cur is not None:
                    out.append((cur, n))
                parts = ln.split()
                cur, n = (parts[1] if len(parts) > 1 else "?"), len(ln.encode("utf-8")) + 1
            elif cur is not None:
                if ln and not ln.startswith(" "):
                    out.append((cur, n))
                    cur, n = None, 0
                else:
                    n += len(ln.encode("utf-8")) + 1
        if cur is not None:
            out.append((cur, n))
        return sorted(out, key=lambda t: -t[1])

    def _prose(entry, canonical, fallback="desc"):
        """M4 non-lossy prose resolution (P0 fix, owner 2026-08-09).

        PLAN_SCHEMA names `canonical`; part of the live ledger writes the
        prose under `fallback` instead, and rendering only the canonical
        field printed a bare `None` — silently dropping the very content
        the digest exists to carry across a compaction.

        Fall back, but NEVER silently. A divergent row is MARKED, so
        normalizing the ledger stays visible work instead of being buried
        by the renderer that papers over it. Absent under both names is a
        loud ledger defect, never a `None`.
        """
        v = entry.get(canonical)
        if v is not None:
            return str(v)
        v = entry.get(fallback)
        if v is not None:
            return (f"{v}  [!! schema-divergent: prose read from `{fallback}`; "
                    f"schema field is `{canonical}`]")
        return (f"!! PROSE MISSING (neither `{canonical}` nor `{fallback}` "
                f"present) — ledger defect, not an empty rule")

    lines = [
        f"=== PLAN LEDGER DIGEST (typed, non-lossy carrier; injection nonce {nonce}) ===",
        "This digest is rendered from plans/*.plan.yaml by compaction_inject.py.",
        "The compaction summary is lossy; THIS block is the carrier of record for",
        "open coordinates, gates, clocks, and constraints. Verify against the",
        "ledger files before any gated side effect.",
    ]
    # Per an orchestrator ruling, arm (a): WHERE this was rendered from, unconditionally. A digest
    # that does not say which tree it measured cannot be checked by its reader,
    # and the failure it hides is silent by construction: the wrong workspace
    # renders the same bytes as an empty one. Declared even when the caller
    # passes nothing, so an unattributed render is VISIBLE rather than absent
    # [[empty-result-needs-its-count]].
    _no_plans_dir = False
    if workspace is None:
        lines.append("!! WORKSPACE NOT DECLARED BY CALLER — this digest does "
                     "not record which tree it measured; treat its coverage "
                     "as unverified.")
    else:
        _ws_abs = Path(workspace).resolve()
        _pdir = plans_dir(workspace)
        lines.append(f"rendered from workspace: {_ws_abs}")
        if not _pdir.is_dir():
            _no_plans_dir = True
            # Same ruling, arm (b): the honest answer. `load_plans` returns ([], [])
            # here by design ("pre-adoption"), which is indistinguishable from
            # a real empty ledger — so the DISTINCTION has to be made at the
            # only place that still knows it.
            lines.append(
                f"!! NO plans/ DIRECTORY AT {_pdir} — this is EITHER a "
                "pre-adoption workspace OR an injection that ran against the "
                "WRONG cwd. It is NOT evidence of an empty ledger, and no "
                "gated side effect may be taken on the strength of it. "
                "Re-run compaction_inject.py --inject from the workspace root "
                "and compare.")
    for e in errors:
        lines.append(f"!! PLAN LOAD ERROR (digest incomplete): {e}")
    opens = open_plans(plans)
    if not opens and not _no_plans_dir:
        # Same ruling, arm (b), IN PLACE OF rather than alongside: when there is no
        # plans/ directory the banner above REPLACES this line. Leaving both
        # would keep the false sentence in the artifact and rely on the reader
        # to notice it is contradicted three lines up — and "(no open plans)"
        # is the sentence a scanning reader acts on. This line now renders
        # only where it is TRUE: a ledger directory that was read and held no
        # open plan.
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
                lines.append(
                    f"  GATE {g.get('id')} UNRULED ruler={g.get('ruler')} "
                    f"unblocks={g.get('unblocks')} — {_prose(g, 'question')}"
                )
        for k in _entries(p, "clocks"):
            if k.get("fired") is None:
                lines.append(f"  CLOCK {k.get('id')} [{k.get('kind')}] fires_at={k.get('fires_at')} — {k.get('action')}")
        for c in _entries(p, "constraints"):
            if constraint_active(c, gates_map, now):
                blocks = c.get("blocks")
                if isinstance(blocks, dict) and blocks:
                    enf = (f"blocks tool={blocks.get('tool')} "
                           f"pattern={blocks.get('arg_pattern')!r}")
                else:
                    # plan_gate.check_constraints() opens with
                    #   blocks = con.get("blocks")
                    #   if not isinstance(blocks, dict) or not _tool_matches(...):
                    #       continue
                    # so a constraint carrying no `blocks` key is skipped and
                    # can NEVER block a call. Printing `tool=None pattern=None`
                    # reads like a configured matcher that happens to be empty;
                    # the carrier of record has to say the guard is inert.
                    enf = ("ENFORCEMENT=NONE (no `blocks` key — plan_gate "
                           "skips this constraint; advisory prose only)")
                lines.append(
                    f"  CONSTRAINT {c.get('id')} ACTIVE {enf} "
                    f"until={c.get('until')} — {_prose(c, 'rule')}"
                )
        for a in _entries(p, "authorities"):
            lines.append(f"  AUTHORITY {a.get('auth')} — {a.get('scope')}")
    # F7-6 cure: the digest also carries the F5 done-record (already-produced
    # coordinates across ALL plans incl. closed), so an agent reasoning from
    # the injected context alone does not keep that blind spot.
    done_lines: list[str] = []
    for field in ("repos", "paths", "branches", "ids"):
        for v, d in sorted(done_coord_index(plans, field).items()):
            done_lines.append(
                f"  DONE coordinates.{field}: {v} <- plan {d['plan']} step "
                f"{d['step']} ran {d['ran']} (do NOT re-create; F5)")
    if done_lines:
        lines.append("")
        lines.append("ALREADY-DONE COORDINATES (F5 duplicate index, all plans incl. closed):")
        lines.extend(done_lines)
    lines.append("")
    lines.append(f"=== END PLAN LEDGER DIGEST (nonce {nonce}, rendered {now.isoformat(timespec='seconds')}) ===")

    # -- S11 OVER-CAP BANNER (a fleet ruling, the principal, 2026-09-18) -------------
    # ⚠ The attribution moved. It read an earlier ruling's citation while the
    # figure it describes had been re-set by the later ruling, so the banner
    # credited a ruling to the line that ruling supersedes. Extended by
    # a further ruling on the pattern of an earlier one, with :723 and :743 below.
    # The digest is the CARRIER OF RECORD across a compaction, so the one thing
    # this banner must never do is make the carrier smaller or stop it being
    # injected. It therefore WARNS and never acts: no truncation, no refusal,
    # no early return. A size guard that dropped rows to fit would silently
    # violate the M4 non-lossy contract this same function exists to keep --
    # the cure would destroy exactly what the digest is for.
    #
    # The banner renders INSIDE the digest (after the header block, before the
    # first PLAN) so a reader who sees the carrier at all sees the warning; a
    # banner emitted outside the fences is not part of the record that survives.
    #
    # ⚠ The reported figure is the size of the digest WITHOUT this banner, and
    # it is labelled that way. Reporting the post-insertion size would be
    # self-referential (inserting the banner changes the number it reports), and
    # a figure that cannot be reproduced by measuring the artifact is worse than
    # a slightly conservative one [[measured-numbers-discipline]].
    body = "\n".join(lines)
    size = len(body.encode("utf-8"))
    if size > DIGEST_CAP_BYTES:
        # Per an orchestrator ruling, §4(c). The advice this banner carried (through 2026-08-09) named
        # two levers that recover EXACTLY ZERO bytes, measured both directions:
        #   "close done steps"          -> done/superseded steps are already
        #                                  skipped before any line is emitted
        #                                  (see the `continue` in the steps loop
        #                                  above). Re-closing all 41 already-done
        #                                  steps moved the render 0 B; un-hiding
        #                                  them ADDS ~17 KB, so the filter is real
        #                                  and there is no second helping of it.
        #   "retire satisfied constraints" -> every live constraint is
        #                                  `until: close`, which constraint_active()
        #                                  treats as unconditionally active while
        #                                  the plan is open. There is no satisfied
        #                                  state to retire short of closing.
        # A banner that names no-op cures spends its bytes teaching the reader to
        # do nothing. So it now reports the levers that MOVE, measured from the
        # render it is describing rather than pinned to numbers that go stale
        # [[measured-numbers-discipline]] [[carried-artifacts-expire]].
        contrib = _plan_byte_contributions(lines)
        step_b = sum(len(l.encode("utf-8")) + 1 for l in lines
                     if l.startswith("  STEP "))
        con_b = sum(len(l.encode("utf-8")) + 1 for l in lines
                    if l.startswith("  CONSTRAINT "))
        banner = [
            "",
            "!! OVER-CAP: this digest measures %d B against a RULED CAP of %d B "
            "(+%d B, %.0f%%)." % (size, DIGEST_CAP_BYTES, size - DIGEST_CAP_BYTES,
                                  100.0 * size / DIGEST_CAP_BYTES),
            "!! Nothing has been truncated and injection is NOT blocked -- the digest is the",
            "!! carrier of record and dropping rows to fit would break the M4 non-lossy",
            "!! contract. This is a signal to trim the ledger, not a failure of this render.",
            "!! ZERO-RECOVERY (do NOT reach for these): closing done steps recovers 0 B --",
            "!! done/superseded steps are already excluded from this render; retiring",
            "!! satisfied constraints recovers 0 B -- every live constraint is `until: close`",
            "!! and has no satisfied state short of the plan closing.",
            "!! WHAT ACTUALLY MOVES, measured on THIS render: open-step lines %d B (%.0f%%),"
            % (step_b, 100.0 * step_b / size if size else 0.0),
            "!! constraint lines %d B (%.0f%%). Levers: close whole PLANS, or shorten step"
            % (con_b, 100.0 * con_b / size if size else 0.0),
            "!! `desc` / constraint `rule` prose. Largest contributors right now:",
        ]
        for pid_, n_ in contrib[:3]:
            banner.append("!!   %-38s %6d B (%.0f%% of this digest)"
                          % (pid_, n_, 100.0 * n_ / size if size else 0.0))
        banner.append(
            "!! Authority: a principal ruling (2026-09-18)"
            "; it supersedes a provisional ruling. "
            "Figure measured PRE-banner and UNCAPPED.")
        # after the 5-line header block, before the first PLAN / error line
        lines[5:5] = banner
        return "\n".join(lines)
    return body
