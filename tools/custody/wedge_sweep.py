#!/usr/bin/env python3
"""wedge_sweep — the supervisor layer for the PreToolUse hook wedge class
(commissioned and approved by the orchestrator).

⛔ WHY A SUPERVISOR AND NOT A BETTER HOOK. Three independent legs closed the
   in-process routes today: it is not slow cold start (1,750 launches, slowest
   3.688 s, against wedges of 2,610 / 449 / 2,788 s); it is not a shutdown-flush
   hang on the normal path (the emitter writes 0 bytes, so there is nothing to
   flush); and the emitter's own watchdog cannot reach it, because 6% of runs
   exceed the 1.5 s budget purely in the pre-arm window above the arming line.
   What is left is a stall at or before interpreter startup — and the only layer
   positioned to bound that is one OUTSIDE the wedged process, because it does
   not need to know where the process is stuck, only that a seat is.

⭐⭐ EMIT ON THE SYMPTOM, ATTRIBUTE SECOND (owner E1411 §3(b), the correction
   that matters most here). Owner's v1 detector made the orphaned hook a
   PRECONDITION for emitting, and was silent through a 46-minute wedge. Gating a
   symptom on successful attribution means any wedge you cannot attribute is a
   wedge you cannot SEE — and it fails silently, which is the one failure mode a
   watchdog may never have. So: the STALL is the symptom and it is emitted
   unconditionally; hook processes are named as CANDIDATES; and there is an
   explicit `cause UNKNOWN` branch when nothing joins.
   [[honest-failure-outcomes]] [[vacuity-cannot-attribute]]

⛔ THE JOIN IS SIGN-AGNOSTIC (owner E1411 §3(a)). v1 required the hook to be born
   BEFORE the stalled turn. Both orchestrator wedges had it born ~6 s before, so
   the sign was generalised from n=2 — and builder's hook was born 6 s AFTER,
   which is why it was missed. The window here is symmetric and its half-width
   is a named constant, not a fact about two incidents.
   [[findings-are-classes-not-citations]]

⛔ KILLING REQUIRES ALL THREE, AND TWO OF THREE IS NOT A DIAGNOSIS (owner E1410
   §3). Owner found PID 50844 carrying the FULL process signature — harness-
   spawned, parent dead, 0 CPU — while every session was producing turns, and
   correctly left it alive. A signature-only sweeper would have killed a healthy
   process and called it a rescue. The credibility of this alarm is the whole
   asset; over-firing spends it. [[watchdog-liveness-probes]]

⚠ SHIPS DISARMED. `--kill` is OFF by default and this module is not scheduled by
  its author. Arming (and any scheduled-task registration) is orch's hand under
  the staged-DISARMED protocol; builder stages, orch arms, first fire supervised.

⚠ IDENTITY CHECKS READ BYTES. Every transcript read here is
  binary. A locale decode cost a false sha mismatch against a perfectly correct
  object earlier today; a supervisor that mis-identifies its subject is worse
  than one that does not run.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Half-width of the symmetric spawn/stall join. Sign-agnostic by construction.
JOIN_HALFWIDTH_S = 90.0
# A turn older than this with a tool call still outstanding is a stall.
DEFAULT_STALL_S = 480.0
# How much of a transcript tail to read. Records are large; this is generous.
TAIL_BYTES = 262144
# Hook scripts whose processes are candidates. Matched against command lines.
#
# ⛔ AN ENUMERATED LIST IS THE MECHANISM THAT PRODUCED THE 2026-09-09 BLINDNESS,
#    not just its instance. For 3h20m this list reported "NO hook joins" on a
#    live wedge whose cause was `lane_append_hook.py` — a name it did not carry —
#    and blindness printed as ABSENCE, which is the one failure a watchdog may
#    never have. An orchestrator ruling asked for four names to be added. Four names cure
#    today; the NEXT hook dropped into tools/custody/ is invisible again, because
#    nothing makes the list grow with the directory.
#
# ⭐ THE WATCHDOG ALREADY SOLVED THIS AND THE SWEEP DID NOT AGREE WITH IT.
#    tools/hook_age_watchdog.ps1 matches its workspace class by PATH PATTERN
#    (`[\\/]tools[\\/](custody|plan_gate)[\\/][^\\/"]+\.py`), so a new hook is
#    covered on the day it lands. "The sweep and the watchdog agree on what a
#    wedge is" (the same ruling) has to mean the MATCHER as well as the signature —
#    two instruments that disagree about which processes exist cannot agree about
#    which are wedged. So the pattern below is the watchdog's, transcribed.
#
# ⚠ THE NAMES STAY, as an explicit FLOOR rather than as the mechanism: the six
#   below all live under tools/custody or tools/plan_gate and are therefore
#   already inside the pattern (measured, not assumed — the mirror leg in the
#   controls asserts it). Keeping them means a pattern that silently stops
#   matching cannot silently take the whole candidate set with it, and it keeps
#   that ruling's four names readable at the site as the ruling named them.
#   [[table-driven-enforcement-is-invisible-to-name-greps]]
HOOK_SCRIPTS = ("custody_emitter.py", "plan_gate.py", "seat_binder.py",
                "stop_observer.py", "stop_guard_wrapper.py", "compaction_inject.py",
                # the ruling's four, the ones the sweep was blind to on 2026-09-09:
                "lane_append_hook.py", "opus_effort_guard_hook.py",
                "git_guard_hook.py", "rm_guard_hook.py")
# The watchdog's own class matcher, transcribed. Forward or backslashes, because
# the harness spawns these with forward slashes and PowerShell reports backslashes.
HOOK_PATH_RE = re.compile(r"[\\/]tools[\\/](?:custody|plan_gate)[\\/][^\\/\"]+\.py",
                          re.IGNORECASE)

# ------------------------------------------------------- the never-ran signature
# ⛔ THIS FILE CLAIMED THREE CRITERIA IN FOUR PLACES AND APPLIED ONE. The header
#    ("KILLING REQUIRES ALL THREE"), the SLOW-OR-WEDGED grade ("parent dead, CPU
#    delta 0.000, exactly one process"), the suspect line ("signature incomplete")
#    and the kill summary ("nothing met all three criteria") all described a
#    conjunction; `actionable` filtered on `parent_dead` ALONE, and the process
#    query did not even COLLECT a thread count or a CPU time. The counterexample
#    the header is proudest of — PID 50844, full signature, correctly left alive —
#    could not have been expressed by the code that cites it.
#    [[prose-and-output-are-two-claims]] [[a-comment-citing-a-test-as-warrant-is-an-unchecked-claim]]
#
# The threshold pair is the watchdog's, so the two instruments grade one quantity:
# cpu < 0.05 s AND exactly one thread (tools/hook_age_watchdog.ps1:85). Parent
# death is kept as the third leg here, where the watchdog admits `age > 120 s` as
# an alternative — this side never kills on age alone.
NEVER_RAN_CPU_S = 0.05
NEVER_RAN_THREADS = 1
SIG_NEVER_RAN, SIG_RAN, SIG_UNMEASURED = "NEVER-RAN", "RAN", "UNMEASURED"


def never_ran(proc: dict) -> tuple[str, str]:
    """Grade one process against the never-ran signature.

    ⛔ AN UNMEASURED FIELD IS ITS OWN OUTCOME AND IS NOT ACTIONABLE. A fixture
       without these fields, a CIM query that stops returning them, an
       access-denied row — each yields UNMEASURED, never a silent NEVER-RAN
       (which would kill on one criterion again, the defect this cures) and never
       a silent RAN (which would disarm the sweep invisibly). It is REPORTED, in
       both branches, because a candidate nobody could grade is a hole in the
       sweep and not a clean bill. [[honest-failure-outcomes]]
    """
    threads, cpu = proc.get("threads"), proc.get("cpu_s")
    if threads is None or cpu is None:
        missing = [k for k, v in (("threads", threads), ("cpu_s", cpu)) if v is None]
        return SIG_UNMEASURED, "no %s on this row — not gradeable" % " or ".join(missing)
    if threads == NEVER_RAN_THREADS and cpu < NEVER_RAN_CPU_S:
        return SIG_NEVER_RAN, ("1 thread, %.3fs CPU — died before executing "
                               "anything of its own" % cpu)
    return SIG_RAN, ("%d thread(s), %.3fs CPU — this process RAN; whatever it is "
                     "doing, it is not the never-ran class" % (threads, cpu))

# ------------------------------------------------- lease x agency cross-check
# Per an orchestrator ruling correcting an earlier one. The commissioned synthetic wedge
# was "a fresh lease file + a stale transcript mtime" and that pair is close to
# UNREACHABLE: the lease is written PreToolUse with matcher `.*`
# (.claude/settings.json -> custody_emit_wrapper.sh:97 -> custody_emitter.py), so a
# fresh lease MEANS a tool call began within the TTL, and a tool call writes an
# `assistant` record, which freshens the transcript. A control keyed to that pair
# greens on a state the plumbing does not produce, which is the failure mode where
# a green tells you nothing at all. [[instrument-polarity-controls]]
#
# ⭐ THE MEASURED SIGNATURE IS THE OPPOSITE (the owner's measurement, four live seats): a
#   STALE agency clock beside a FRESH mailbox -- arrivals write to a wedged session
#   and answer nothing.
#
# ⛔ AND THE TWO CLOCKS ARE ONE QUANTITY WITH TWO WRITERS, WHICH IS THE POINT.
#   The custody lease and "age of the oldest unanswered tool_use" both start
#   ticking when a tool call is issued -- PreToolUse for the lease, the `assistant`
#   record for the transcript. They are not two dimensions. The value is the
#   REDUNDANCY, because the lease writer can fail SILENTLY: custody_emitter.py
#   swallows a failed touch() into outcome["how"] = "...|touch-failed" and returns
#   0, settings.json appends `|| exit 0`, and the wrapper fails open when python is
#   absent. Symptom on disk at commission time: 126 of 261 leases carry seat
#   `unknown`. A seat whose lease has gone dark while it is demonstrably working
#   DROPS OUT of every peer census, and nothing in the tree detects it, because the
#   lease-only leg (tools/dashboard/escalation_liveness.py) and the transcript-only
#   leg (this file) never meet. That state is EMITTER-DARK.
#
# ⛔ CORRECTED 2026-09-09 -- and the correction is what the commissioned review was
#   for (codex EOV-243c4fd9 + opus EOV-cce52f00, both SPLIT, reached independently).
#   This comment used to say the dark seat "still counts as a LIVE PEER to git_guard,
#   which is the condition that silently disarms the custody guard". BACKWARDS, and
#   the two files that settle it are both in this tree: custody_lease.live_peers does
#   `if age > ttl_seconds: continue` -- a stale lease is DROPPED, never counted -- and
#   git_guard:201-217 fails CLOSED on exactly that shape, in text that states the real
#   mechanism out loud: "an empty peer set is evidence about the PROBE, not about
#   peers ... 'No leases' and 'no live peers' are different facts."
#   So the hazard is the OMISSION: the dark peer leaves the census, and a peer whose
#   OWN lease is fresh reads the shortened census as clear. The state is worth
#   detecting either way; the sentence explaining WHY was the least-checked object in
#   the package, because everything downstream of it got the scrutiny.
#   [[accepted-reason-is-the-least-checked-object]]
#
# ⚠ TWO TTLs EXIST IN THIS FLEET FOR ONE LEASE, and this module does not get to
#   pick quietly. tools/custody/custody_ttl.py carries TTL_SECONDS = 1223.9, ADOPTED
#   BY THE PRINCIPAL in a fleet ruling; tools/dashboard/escalation_liveness.py grades the same
#   files at TTL_S = 900. The ruled number is used here and the divergence is REPORTED
#   -- on BOTH branches of the sweep's own output and in --json -- rather than
#   reconciled by this seat: two instruments disagreeing about when a lease is stale
#   is a fleet question, not a default. [[rulings-are-per-lane-derive-your-priors]]
#
# ⛔ THIS LINE USED TO NAME A `--lease-ttl-disclosure` FLAG. There is no such flag and
#   there never was; both review voices found it. A comment that sends a reader to an
#   option the argparse block does not define is a FALSE instruction, not a stale one.
#   [[a-comment-citing-a-test-as-warrant-is-an-unchecked-claim]]
try:
    from custody_ttl import TTL_SECONDS as LEASE_TTL_S       # the ruled number
except Exception:                                            # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from custody_ttl import TTL_SECONDS as LEASE_TTL_S
LEASE_TTL_OTHER = ("tools/dashboard/escalation_liveness.py", 900)

# Grades this cross-check can return. WEDGED is deliberately NOT among them: see
# grade_agency's docstring -- on both clocks a ten-minute codex dispatch and a
# ten-minute wedge are identical, and only process evidence promotes.
G_LIVE = "LIVE"
G_EMITTER_DARK = "EMITTER-DARK"
G_SLOW_OR_WEDGED = "SLOW-OR-WEDGED"
G_IDLE_OR_WEDGED = "IDLE-OR-WEDGED"
G_NO_AGENCY = "NO-PENDING-CALL"


# --------------------------------------------------------------- transcripts
def _tail_records(path: Path, nbytes: int = TAIL_BYTES) -> list[dict]:
    """Last complete JSONL records, read as BYTES.

    ⚠ The first partial line after the seek is discarded — a half record
      decoded as a whole one is a fabricated observation, and this function's
      whole job is to report what the session actually last did.
    """
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > nbytes:
                fh.seek(size - nbytes)
                fh.readline()          # discard the partial first line
            raw = fh.read()
    except OSError:
        return []
    out = []
    for line in raw.split(b"\n"):
        if not line.strip():
            continue
        try:
            rec = json.loads(line.decode("utf-8", errors="replace"))
        except Exception:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _stamp(rec: dict) -> float | None:
    """Record timestamp as epoch seconds.

    ⚠ ONE PARSER FOR EVERY FORM. The first version branched on a trailing 'Z'
      and hand-rolled the UTC case with mktime()-timezone — which is wrong under
      DST and would have skewed every join by an hour for half the year, in a
      module whose entire output is a ±90 s time comparison. fromisoformat
      handles Z and explicit offsets alike once Z is normalised.
    """
    return _iso_local(rec.get("timestamp") or "")


def _iso_local(ts: str) -> float | None:
    from datetime import datetime
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _has_pending_tool_use(rec: dict) -> bool:
    """Is this an assistant turn that issued a tool call and is awaiting it?

    ⛔ THIS IS THE FALSE-POSITIVE GUARD AND IT IS LOAD-BEARING. An IDLE session
       — one that finished its turn and is waiting for a human — also stops
       producing records, and looks identical to a wedged one on age alone. The
       difference is what the LAST record is: a wedged session's last record is
       an assistant message carrying a tool_use whose result never arrived; an
       idle session's is a completed turn. Without this the sweep would report
       every quiet seat as wedged, which is exactly the over-firing that
       destroys the alarm.
    """
    if rec.get("type") != "assistant":
        return False
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, list):
        return any(isinstance(b, dict) and b.get("type") == "tool_use" for b in content)
    return False


def emitter_dark_sweep(projects_dir: Path, repo: Path, now: float,
                       ttl: float = LEASE_TTL_S, stall_s: float = DEFAULT_STALL_S,
                       recent_s: float = 1800.0) -> list[dict]:
    """Seats that are demonstrably WORKING while their custody lease has gone dark.

    ⛔ THIS CANNOT REACH `stalled_sessions` AND MUST NOT LIVE INSIDE IT. That
       function filters to agency > stall_s -- a seat that is stalled. EMITTER-DARK
       is the opposite shape: the transcript clock is YOUNG (the seat is working)
       and the lease clock is old or gone. It would be filtered out of the stall
       list by construction, which is exactly why nothing in this tree has ever
       reported it: the lease-only leg and the transcript-only leg never meet.

    ⚠ ONLY RECENTLY-ACTIVE TRANSCRIPTS ARE CONSIDERED (`recent_s`). A months-old
      transcript has a dark lease for the honest reason that its seat is gone;
      reporting those would bury the one row worth having under the archive.
    """
    out: list[dict] = []
    if not projects_dir.is_dir():
        return out
    leases = read_leases(repo, now)
    for tp in sorted(projects_dir.glob("*.jsonl")):
        try:
            st = tp.stat()
        except OSError:
            continue
        mtime_age = now - st.st_mtime
        if mtime_age > recent_s:
            continue
        recs = _tail_records(tp)
        if not recs:
            continue
        agency = agency_age(recs, now)
        row = leases.get(tp.stem) or {}
        grade, why = grade_agency(row.get("age_s"), agency, mtime_age, ttl, stall_s)
        if grade != G_EMITTER_DARK:
            continue
        out.append({"session": tp.stem, "transcript": str(tp),
                    "seat": row.get("seat"), "lease_age_s": row.get("age_s"),
                    "lease_error": row.get("error"),
                    "agency_age_s": None if agency is None else round(agency, 1),
                    "mtime_age_s": round(mtime_age, 1),
                    "grade": grade, "why": why})
    return out


def _blocks(rec: dict) -> list:
    """The content blocks of a record.

    ⚠ MEASURED, not assumed (owner, 400 KB tail of a live owner session, 41
      tool_use / 41 tool_result, balanced): BOTH halves live under
      `message.content` -- `assistant` records carry `{"type":"tool_use","id":...}`
      and `user` records carry `{"type":"tool_result","tool_use_id":...}`. An
      earlier note of mine put the result half at a top-level
      `content`; that was wrong, and both spellings are read here so a harness
      that ever moves it does not silently zero this detector.
    """
    out = []
    for c in ((rec.get("message") or {}).get("content"), rec.get("content")):
        if isinstance(c, list):
            out.extend(b for b in c if isinstance(b, dict))
    return out


def unanswered_tool_uses(recs: list[dict]) -> list[tuple[str, float | None]]:
    """(tool_use id, issue timestamp) for every call with no result in `recs`.

    ⛔ THIS REPLACES A LAST-RECORD TEST THAT WAS BLIND AT THE MOMENT IT MATTERED.
       `_has_pending_tool_use(recs[-1])` asks only whether the FINAL record is an
       assistant tool_use. `queue-operation` records arrive OUT OF BAND and append
       AFTER a session has stalled -- they freshen the file and answer nothing --
       so on a genuinely wedged session the last record is usually one of those and
       the predicate returns False. The detector was blindest exactly when it was
       needed, and it fails SILENT. Pairing by id is immune to whatever trails.

    ⚠ THIS IS A LOWER BOUND ON AGENCY AGE, and the bound is the tail window. A
      call issued before the read window and never answered is not visible here,
      so a session stalled for longer than TAIL_BYTES of traffic reports the
      OLDEST call it can see, not the oldest that exists. It can therefore
      understate a stall; it cannot invent one. [[claim-bounding-discipline]]
    """
    issued: dict[str, float | None] = {}
    answered: set[str] = set()
    for rec in recs:
        for b in _blocks(rec):
            if b.get("type") == "tool_use" and b.get("id"):
                issued.setdefault(str(b["id"]), _stamp(rec))
            elif b.get("type") == "tool_result" and b.get("tool_use_id"):
                answered.add(str(b["tool_use_id"]))
    return [(i, ts) for i, ts in issued.items() if i not in answered]


def agency_age(recs: list[dict], now: float) -> float | None:
    """Age of the OLDEST unanswered tool call, or None when none is pending.

    ⭐ None is NOT "healthy" and must never be graded as such by a caller: a seat
       between turns has no pending call and neither does a seat that died after
       its last result arrived. It means THIS INSTRUMENT HAS NO READING, which is
       a different fact from a young one. [[refusing-to-guess-is-not-undeterminable]]

    ⚠ AN UNANSWERED CALL IS THE NORMAL STATE OF A WORKING SEAT. Measured on four
      live seats mid-work: builder 18.5 s, orchestrator 16.4 s, owner 20.9 s
      pending, creator none. Three of four had one. A control asserting the bare
      predicate "has a pending call" would redden on every healthy seat; only the
      AGE carries information. [[positive-control-is-the-act-the-census-detects]]
    """
    ages = [now - ts for _i, ts in unanswered_tool_uses(recs) if ts is not None]
    return max(ages) if ages else None


def read_leases(workspace: Path, now: float) -> dict[str, dict]:
    """{session_id: {seat, age_s, path, error}} from plans/.custody.<seat>.<session>.

    ⛔ THE LEASE GRAMMAR IS IMPORTED, NEVER RESTATED. custody_lease.py owns
       LEASE_RE, the two-line format (stamp on line 1, tree on line 2) and the
       future-dated refusal. A second parser here would be a second grammar free
       to drift from the writer's [[emitter-and-verifier-are-one-grammar]], on the
       one file whose disagreement this module exists to detect.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import custody_lease as _cl
    out: dict[str, dict] = {}
    d = Path(workspace) / _cl.LEASE_DIR_NAME
    if not d.is_dir():
        return out
    for p in sorted(d.glob(_cl.LEASE_PREFIX + "*")):
        m = _cl.LEASE_RE.match(p.name)
        if not m:
            continue
        seat, session = m.group(1), m.group(2)
        row = {"seat": seat, "path": str(p), "age_s": None, "error": None}
        try:
            age = _cl._age_of(p, now)
            row["age_s"] = None if age is None else round(age, 1)
        except Exception as exc:                              # corrupt / future-dated
            row["error"] = str(exc)
        out[session] = row
    return out


def grade_agency(lease_age, agency, mtime_age, ttl=LEASE_TTL_S,
                 stall_s=DEFAULT_STALL_S) -> tuple[str, str]:
    """Cross the two clocks. Returns (grade, why).

    ⛔ NO BRANCH RETURNS "WEDGED", AND THAT IS THE POINT. A legitimately long tool
       call -- a codex dispatch, a long test run -- leaves a tool_use unanswered
       for minutes AND stops refreshing the lease, because during one long call
       there are no further calls. ON BOTH CLOCKS A TEN-MINUTE DISPATCH AND A
       TEN-MINUTE WEDGE ARE IDENTICAL. Past the bound the grade says
       SLOW-OR-WEDGED and names what settles it; only PROCESS evidence promotes
       (parent dead, CPU delta 0.000 sampled >=3 s apart, exactly one process on
       the command line) -- the same three-of-three rule this file already applies
       at its kill gate. A false WEDGED costs a killed dispatch and the work inside
       it; the false LIVE cost sixteen minutes on 2026-09-08. Inherited from the
       sentinel's dead bound rather than re-earned. [[refusing-to-guess-is-not-undeterminable]]
    """
    lease_fresh = lease_age is not None and lease_age <= ttl
    if agency is None:
        return (G_NO_AGENCY,
                "no unanswered tool call in the read window — this instrument has "
                "no reading here; it is not a clean bill of health (lease %s)"
                % ("fresh" if lease_fresh else "stale/absent"))
    if lease_fresh and agency <= stall_s:
        return (G_LIVE, "lease %.0fs (ttl %.0fs) and oldest unanswered call %.0fs — "
                        "both clocks young" % (lease_age, ttl, agency))
    if not lease_fresh and agency <= stall_s:
        return (G_EMITTER_DARK,
                "the beacon stopped and the seat did not: lease %s past a %.0fs ttl "
                "while the oldest unanswered call is only %.0fs old. The lease writer "
                "fails OPEN (custody_emitter swallows a failed touch and returns 0), so "
                "this seat has DROPPED OUT of every peer census while still working — a "
                "peer whose own lease is fresh reads the shortened census as clear. "
                "Nothing else in the tree sees this state."
                % ("absent" if lease_age is None else "%.0fs" % lease_age, ttl, agency))
    if mtime_age is not None and mtime_age < agency / 2.0:
        return (G_SLOW_OR_WEDGED,
                "oldest unanswered call %.0fs (> %.0fs bound) beside a transcript "
                "written %.0fs ago — arrivals are landing and answering nothing, the "
                "2026-09-08 signature. NOT a wedge verdict: a long dispatch reads "
                "identically. Settled only by process evidence (parent dead, CPU delta "
                "0.000 over >=3s, exactly one matching process)."
                % (agency, stall_s, mtime_age))
    return (G_IDLE_OR_WEDGED,
            "oldest unanswered call %.0fs (> %.0fs bound) and no recent traffic either "
            "way — weaker than the fresh-mailbox case and deliberately not promoted"
            % (agency, stall_s))


# ── session CLASS, read from the transcript's own `entrypoint` ───────────────
#
# ⭐ NOT EVERY TRANSCRIPT IS A SEAT. The security-guidance plugin runs a Stop-time
#    REVIEW leg as a headless SDK session in this same projects directory, and its
#    transcript is shaped exactly like a seat's: outstanding tool call, no further
#    records, stall clock running. Orch identified one in an earlier review (session
#    89dc6685, `entrypoint: sdk-py`, last call 17:29:14, a PowerShell `python -c`)
#    that had been alarming as a STALLED SEAT while all four real seats were moving.
#    A review leg that ends mid-call freezes nobody; alarming on it at seat volume
#    spends the alarm's credibility on something no one can or should act on.
#
# ⚠ THE CLASS IS READ, NEVER INFERRED. `entrypoint` is a field the harness writes
#   on most records including the last, so the tail this module already holds
#   carries it; a transcript that does not state one gets `None` and stays in the
#   SEAT alarm. Failing toward the alarm is the right direction: an unclassified
#   session wrongly demoted is a wedge nobody sees, while an unclassified session
#   wrongly alarmed is a line a human reads and dismisses.
PLUGIN_ENTRYPOINTS = {"sdk-py": "plugin review leg"}


def _entrypoint(recs: list[dict]) -> str | None:
    """The newest `entrypoint` in the records held, or None.

    Newest rather than oldest because these are TAIL records -- the oldest one in
    this window is simply the oldest the window happened to reach, which is a fact
    about TAIL_BYTES and not about the session.
    """
    for r in reversed(recs or []):
        if isinstance(r, dict):
            ep = r.get("entrypoint")
            if isinstance(ep, str) and ep:
                return ep
    return None


def stalled_sessions(projects_dir: Path, stall_s: float, now: float) -> list[dict]:
    """Every session whose last record is an OUTSTANDING tool call older than
    stall_s. Symptom-first: this list is computed with no reference whatsoever
    to what processes exist."""
    out = []
    if not projects_dir.is_dir():
        return out
    for tp in sorted(projects_dir.glob("*.jsonl")):
        recs = _tail_records(tp)
        if not recs:
            continue
        last = recs[-1]
        # ⛔ THE STALL CLOCK IS NOW THE OLDEST UNANSWERED CALL, NOT THE LAST
        #    RECORD'S TIMESTAMP, and the idle-guard is id pairing rather than
        #    "is the final record a tool_use". Both changes have one cause:
        #    `queue-operation` records append AFTER a session wedges, so the last
        #    record of a genuinely wedged session is usually not its outstanding
        #    call -- the old form freshened `age` off that arrival AND failed the
        #    guard, twice blind, silently, at the only moment it mattered.
        agency = agency_age(recs, now)
        ts = _stamp(last)
        mtime_age = None
        try:
            mtime_age = now - tp.stat().st_mtime
        except OSError:
            pass
        if agency is None:
            continue                            # idle or no reading; never "healthy"
        if agency < stall_s:
            continue
        ep = _entrypoint(recs)
        out.append({
            "_age": agency,
            "session": tp.stem,
            "entrypoint": ep,
            "session_class": PLUGIN_ENTRYPOINTS.get(ep or "", "seat"),
            "transcript": str(tp),
            "stalled_since": now - agency,
            "stall_age_s": round(agency, 1),
            "last_record_age_s": None if ts is None else round(now - ts, 1),
            "mtime_age_s": None if mtime_age is None else round(mtime_age, 1),
            "pending_calls": len(unanswered_tool_uses(recs)),
            "clock": "unanswered-tool_use (lower bound: tail window only)",
        })
    return out


# ----------------------------------------------------------------- processes
_PS = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
       "Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine,"
       "ThreadCount,UserModeTime,KernelModeTime | "
       "ConvertTo-Json -Compress -Depth 3")


def _cpu_seconds(p: dict) -> float | None:
    """User+kernel time in SECONDS, or None when either is absent.

    ⚠ Win32_Process reports both in 100-NANOSECOND units. Reading them as
      milliseconds (the plausible guess) would make a 0.94 s process read as
      946,562 s and grade RAN for the wrong reason — a number that is never
      wrong in the direction that reddens anything.
    """
    u, k = p.get("UserModeTime"), p.get("KernelModeTime")
    if u is None or k is None:
        return None
    try:
        return (float(u) + float(k)) / 1e7
    except (TypeError, ValueError):
        return None


def match_script(cmdline: str) -> tuple[str, str] | None:
    """(script, matched_by) for a command line that is a hook, else None.

    Name FLOOR first, then the watchdog's path pattern. `matched_by` is carried
    so a reader can see WHICH leg admitted a process — if the pattern ever starts
    doing all the work alone, the floor has stopped matching, and that is worth
    seeing before it matters.

    ⛔ THIS IS A FUNCTION BECAUSE THE `--procs-from` SEAM BYPASSED THE MATCHER
       ENTIRELY. Fixtures are returned unfiltered, so every control that drove
       the module through that seam was handed a PRE-MATCHED candidate list — and
       a leg asserting "the four new hooks now join" passed identically against
       the version that had never heard of them. A test seam that skips the code
       under test manufactures greens. Both branches now go through here.
       [[fixture-derived-from-the-subject-is-mutation-blind]]
    """
    cl = cmdline or ""
    for s in HOOK_SCRIPTS:
        if s in cl:
            return s, "name"
    m = HOOK_PATH_RE.search(cl)
    if m:
        return m.group(0).replace("\\", "/").rsplit("/", 1)[-1], "path"
    return None


def hook_processes(procs_from: str | None = None) -> list[dict]:
    """Candidate hook processes: python, running one of HOOK_SCRIPTS.

    ⚠ `--procs-from` is a TESTING SEAM, and it exists so the acceptance fixtures
      can drive owner's replay cases without needing a real orphan on the
      machine — which is precisely the residual owner named on their own v2
      ("proven only by arithmetic replay, not by a live orphan").
    """
    if procs_from:
        try:
            rows = json.loads(Path(procs_from).read_bytes().decode("utf-8"))
        except Exception:
            return []
        # ⛔ THE SEAM IS FILTERED BY THE SAME MATCHER AS THE LIVE PATH. It used
        #    to return fixtures verbatim, which meant no control driving this
        #    seam could ever test HOOK_SCRIPTS or HOOK_PATH_RE — the fixture WAS
        #    the answer. A fixture may still supply the world; it may no longer
        #    supply a process the live path would never have seen.
        out = []
        for p in rows or []:
            hit = match_script(p.get("cmdline") or p.get("script") or "")
            if not hit:
                continue
            script, matched_by = hit
            out.append({**p, "script": p.get("script") or script,
                        "matched_by": matched_by})
        return out
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS],
                           capture_output=True, timeout=60)
        data = json.loads((r.stdout or b"{}").decode("utf-8", errors="replace") or "{}")
    except Exception:
        return []
    if isinstance(data, dict):
        data = [data]
    out = []
    for p in data or []:
        cl = p.get("CommandLine") or ""
        hit = match_script(cl)
        if not hit:
            continue
        script, matched_by = hit
        threads = p.get("ThreadCount")
        out.append({"pid": p.get("ProcessId"), "ppid": p.get("ParentProcessId"),
                    "created": _cim_time(p.get("CreationDate")), "script": script,
                    "matched_by": matched_by, "cmdline": cl,
                    # A fixture may carry `threads`/`cpu_s` directly; a live CIM
                    # row carries the raw fields. Neither is invented: absent
                    # stays None and grades UNMEASURED.
                    "threads": p.get("threads", threads),
                    "cpu_s": p.get("cpu_s", _cpu_seconds(p))})
    return out


def _cim_time(v) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        m = re.search(r"/Date\((\d+)", v)
        if m:
            return int(m.group(1)) / 1000.0
        return _iso_local(v)
    return None


def _alive(pid) -> bool:
    if not pid:
        return False
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                            "if (Get-Process -Id %d -ErrorAction SilentlyContinue) "
                            "{'Y'} else {'N'}" % int(pid)],
                           capture_output=True, timeout=30)
        return (r.stdout or b"").strip() == b"Y"
    except Exception:
        # ⛔ Unknown liveness must NOT read as "parent dead" — that would turn an
        #    instrument failure into a kill criterion.
        return True


def join(stall: dict, procs: list[dict], parent_alive, halfwidth: float) -> list[dict]:
    """Candidate hooks whose spawn sits within ±halfwidth of the stalled turn.

    ⛔ SYMMETRIC. Owner's v1 required `spawn <= stall` and missed builder's
       wedge, where the hook was born 6 s AFTER the stalled turn. The window is
       two-sided because nothing in the mechanism privileges a direction — that
       was an artefact of the first two cases sharing a sign.
    """
    hits = []
    for p in procs:
        c = p.get("created")
        if c is None:
            continue
        gap = c - stall["stalled_since"]
        if abs(gap) > halfwidth:
            continue
        sig, why = never_ran(p)
        hits.append({**p, "gap_s": round(gap, 1),
                     "parent_dead": not parent_alive(p.get("ppid")),
                     "signature": sig, "signature_why": why})
    return hits


def main(argv=None) -> int:
    # ⛔ CODEC. Unattended launchers redirect stdout, which selects cp1252 on
    #    Windows, and the ONLY lines carrying unencodable glyphs are on the
    #    FINDING branch -- so this tool ran green for weeks because it had
    #    nothing to say, and would have died the first time it did. Measured
    #    2026-08-18 (owner DP8): stdout was 0 BYTES, not a truncated line --
    #    block-buffered output never flushes, so the crash destroys every
    #    earlier line too. And the crash exits 1, which is this tool's OWN
    #    alarm code -- indistinguishable from a healthy stall report.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--projects-dir", default=None,
                    help="override the transcript directory (testing seam)")
    ap.add_argument("--stall-s", type=float, default=DEFAULT_STALL_S)
    ap.add_argument("--join-halfwidth-s", type=float, default=JOIN_HALFWIDTH_S)
    ap.add_argument("--now", type=float, default=None, help="pin the clock (replay)")
    ap.add_argument("--procs-from", default=None, help="process list JSON (testing seam)")
    ap.add_argument("--assume-parent-dead", action="store_true",
                    help="replay seam: treat every candidate's parent as dead")
    ap.add_argument("--abandoned-after-s", type=float, default=14400.0,
                    help="a stall older than this is an ABANDONED transcript, "
                         "not a live wedge; counted, never alarmed on")
    ap.add_argument("--kill", action="store_true",
                    help="ACT. Off by default; arming is orch's hand, not the author's.")
    ap.add_argument("--kill-log", default=None,
                    help="RECORD intended kills to this file instead of executing "
                         "them. The acceptance battery always uses it — see the "
                         "note at the kill site.")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    repo = Path(a.repo)
    if not (repo / "plans").is_dir():
        print("wedge_sweep: UNREADABLE — %s has no plans/; refusing to report a "
              "clean fleet for a tree I did not read" % a.repo, file=sys.stderr)
        return 3

    projects = Path(a.projects_dir) if a.projects_dir else (
        Path.home() / ".claude" / "projects" / re.sub(r"[:\\/]", "-", str(repo.resolve())))
    now = a.now if a.now is not None else time.time()

    found = stalled_sessions(projects, a.stall_s, now)
    # The lease x agency cross-check. Computed here, PRINTED LAST (see the end of main).
    #
    # ⛔ IT IS NOT FOLDED INTO THE STALL LIST AND IT DOES NOT LEAD THE OUTPUT.
    #    Not folded: a dark lease on a WORKING seat is the opposite shape from a
    #    stall and `stalled_sessions` filters it out by construction. Not leading:
    #    tools/tests/wedge_sweep_codec_controls.py leg 2 asserts the FIRST stdout
    #    line opens with the ASCII token `STALL `, and printing this section first
    #    turned that leg red. The alarm leads; this is a secondary report, and the
    #    control was left untouched -- editing someone else's battery so my own
    #    change passes is the one repair this fleet does not allow itself.
    #    [[a-self-imposed-gate-faces-no-adversary]]
    dark = emitter_dark_sweep(projects, repo, now, stall_s=a.stall_s)
    # ⛔ A THIRD STATE, FOUND BY THE LIVE LEG AND NOT BY ANY FIXTURE. The first
    #    version modelled two states — idle and wedged — and the live fleet
    #    immediately produced a session whose last record is an outstanding tool
    #    call from 72 HOURS ago. That is not a wedge; it is an ABANDONED
    #    transcript, a seat that ended while a call was in flight. Alarming on it
    #    would mean this sweep fires forever on dead history, which is the
    #    over-firing that spends the alarm's credibility on day one.
    #
    #    They are separated by a NAMED CEILING rather than by cleverness, because
    #    nothing observable distinguishes "wedged for 72 h" from "abandoned 72 h
    #    ago" — a wedged session stops writing leases exactly like a dead one.
    #    So the ceiling is a stated assumption, and the abandoned COUNT is
    #    always reported rather than dropped. [[empty-result-needs-its-count]]
    #    [[stated-bound-is-an-open]]
    # ⭐ A THIRD SPLIT, ON THE SAME PRINCIPLE AS THE CEILING ABOVE: separated by a
    #    field the transcript STATES, not by cleverness. A `sdk-py` session is the
    #    plugin's own review leg, not a seat -- see PLUGIN_ENTRYPOINTS. It is
    #    reported, counted and never dropped; what changes is only that it does not
    #    occupy the seat alarm. [[collected-is-not-reported]]
    #
    # ⛔ AND IT IS NOT CALLED `DEAD`. An orchestrator review asked for "a session with no live
    #    process is DEAD, never STALLED". MEASURED 2026-09-09 against four seats
    #    demonstrably alive (all four writing transcripts, two within 20 s): the
    #    number of processes on this machine whose command line carries the session
    #    id was 1, 0, 0 and 11. Two LIVE seats would have graded DEAD. The id
    #    reaches a command line only incidentally -- through a scratchpad path a
    #    Bash tool call happens to name -- so its absence measures tooling, not
    #    liveness, and a DEAD verdict resting on it would be a false clear on the
    #    exact question this sweep exists to answer. The class split below is the
    #    part of that unit that survives measurement; the liveness half is reported
    #    back rather than built. [[refusing-to-guess-is-not-undeterminable]]
    in_window = [s for s in found if s["_age"] <= a.abandoned_after_s]
    stalls = [s for s in in_window if s.get("session_class") == "seat"]
    plugin_legs = [s for s in in_window if s.get("session_class") != "seat"]
    abandoned = [s for s in found if s["_age"] > a.abandoned_after_s]
    for s in found:
        s.pop("_age", None)
    procs = hook_processes(a.procs_from)
    parent_alive = (lambda _p: False) if a.assume_parent_dead else _alive

    report = {"now": now, "stall_threshold_s": a.stall_s,
              "sessions_examined": len(list(projects.glob("*.jsonl"))) if projects.is_dir() else 0,
              "stalls": [], "killed": [], "kill_failed": [],
              "kill_enabled": bool(a.kill)}

    for st in stalls:
        cands = join(st, procs, parent_alive, a.join_halfwidth_s)
        # ⛔ The three-way conjunction, APPLIED and no longer merely asserted:
        #    the join put it in `cands`, the stall is the row, and the SIGNATURE
        #    is now measured rather than described. Until 2026-09-09 this line
        #    read `if c["parent_dead"]` alone while four comment sites and the
        #    kill summary all said "all three".
        actionable = [c for c in cands
                      if c["parent_dead"] and c["signature"] == SIG_NEVER_RAN]
        # ⚠ Candidates nobody could grade are their own row. They are NOT
        #   actionable and they are NOT clean; a sweep whose signature leg
        #   silently stopped returning fields would otherwise report a quiet
        #   fleet forever. [[instrument-must-prove-it-fired]]
        ungraded = [c for c in cands if c["signature"] == SIG_UNMEASURED]
        row = {**st, "candidates": cands, "actionable": actionable,
               "ungraded": ungraded,
               "attribution": ("suspects" if actionable else "UNKNOWN")}
        report["stalls"].append(row)
        if a.kill:
            for c in actionable:
                # ⛔ --kill-log EXISTS BECAUSE MY OWN ACCEPTANCE BATTERY NEARLY
                #    TASKKILLED A FABRICATED PID ON THE LIVE MACHINE. A fixture
                #    invents process ids; `taskkill /PID 777 /T /F` does not know
                #    they were invented. Any test that drives the kill path must
                #    record intent, never execute it.
                #
                # ⚠ THIS BLOCK USED TO SAY THE INVOCATION WAS UNTESTED AND THE
                #   SELECTION WAS PROVEN. BOTH HALVES WERE WRONG, AND IN OPPOSITE
                #   DIRECTIONS — which is why the correction is worth its lines.
                #
                #   DRIVEN NOW: this invocation, against a throwaway this seat
                #   spawned and owned end to end. Live pid 47952 → rc=0, sole entry
                #   in `killed`, and pid 47952 plus its child 17924 both really gone
                #   (a kill, not a bookkeeping change). Already-dead pid 7096 →
                #   rc=128, filed in `kill_failed`, ABSENT from `killed`. No
                #   fabricated pid and no peer's process touched.
                #   (results in the private workspace, PASS C.)
                #
                # ⛔ UNTESTED NOW — and it is the half where the judgement lives:
                #   the SELECTION that decides which real process arrives here.
                #   Every drive, battery and census pass ran `--assume-parent-dead`,
                #   so the `parent_dead` conjunct at :323 — the third leg of the
                #   three-way conjunction above — has never once been exercised.
                #   Forcing a conjunct true does not test the conjunction. Access
                #   denied and recycled-pid also stay inferred, not driven.
                #   [[stated-bound-is-an-open]]
                if a.kill_log:
                    with open(a.kill_log, "a", encoding="utf-8") as fh:
                        fh.write("WOULD-KILL pid=%s script=%s gap=%+.1f\n"
                                 % (c["pid"], c["script"], c["gap_s"]))
                    report["killed"].append(c["pid"])
                    continue
                # ⛔ THE RC IS CHECKED, AND IT DID NOT USED TO BE (builder drive,
                #   an earlier round). This block ran `taskkill` and appended to
                #   `killed` UNCONDITIONALLY — so a kill that FAILED filed a
                #   receipt saying it succeeded. Driven, not argued: taskkill
                #   against an already-dead pid returns **rc=128**
                #   (results in the private workspace). Access
                #   denied and a recycled pid land the same way. An armed sweep
                #   whose report cannot distinguish "killed it" from "tried and
                #   could not" is asserting an outcome it never measured, and that
                #   report is what a human reads to decide the mechanism works.
                #   [[probe-discipline]] — a stop's RETURN is not a stopped process.
                try:
                    # /T is load-bearing: one dispatch owns more than one process.
                    # Never by name — four seats share this machine.
                    k = subprocess.run(["taskkill", "/PID", str(c["pid"]), "/T", "/F"],
                                       capture_output=True, timeout=30)
                    if k.returncode == 0:
                        report["killed"].append(c["pid"])
                    else:
                        report["kill_failed"].append(
                            {"pid": c["pid"], "script": c["script"], "rc": k.returncode,
                             "err": (k.stderr or k.stdout or b"").decode(
                                 "utf-8", "replace").strip()[:200]})
                except Exception as e:
                    # ⚠ The old `except: pass` recorded NOTHING — a taskkill that
                    #   never launched left no trace on either list.
                    report["kill_failed"].append(
                        {"pid": c["pid"], "script": c["script"], "rc": None,
                         "err": "%s: %s" % (type(e).__name__, e)})

    # ⛔ ASSIGNED BEFORE THE BRANCH, not after it. These three lines used to sit
    #    below the `if a.json:` dump, so `--json` serialized a report that had
    #    never been given them: the text branch reported EMITTER-DARK and the JSON
    #    branch silently did not. Found by BOTH review voices, and by neither of my
    #    own controls -- W-A9 drives emitter_dark_sweep() directly and never once
    #    runs the shipped CLI, so the whole delivery path was untested.
    #    W-A10 below now drives main(["--json", ...]) and parses what comes out.
    #    [[prose-and-output-are-two-claims]] [[collected-is-not-reported]]
    report["plugin_legs"] = plugin_legs
    report["emitter_dark"] = dark
    report["lease_ttl_s"] = LEASE_TTL_S
    report["lease_ttl_divergence"] = {"other": LEASE_TTL_OTHER[0],
                                      "other_ttl_s": LEASE_TTL_OTHER[1]}
    if a.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        if not stalls:
            print("wedge_sweep: no stalled sessions (%d transcript(s) examined, "
                  "threshold %.0fs)%s"
                  % (report["sessions_examined"], a.stall_s,
                     "" if not plugin_legs else
                     " — but %d plugin review leg(s) are outstanding, listed below; "
                     "'no stalled SEATS' is the claim, not 'nothing is outstanding'"
                     % len(plugin_legs)))
        if abandoned:
            print("   (%d ABANDONED transcript(s) past the %.0fs ceiling, not "
                  "alarmed on: %s — a seat that ended with a call in flight "
                  "looks identical to one wedged for the same duration, so the "
                  "ceiling is an assumption, not a measurement)"
                  % (len(abandoned), a.abandoned_after_s,
                     ", ".join(s["session"][:8] for s in abandoned[:5])))
        for row in report["stalls"]:
            print("STALL ⛔ STALLED SESSION %s — last tool call outstanding %.0fs (clock=%s)"
                  % (row["session"], row["stall_age_s"], row["clock"]))
            if row["attribution"] == "UNKNOWN":
                # ⭐ The branch owner's v1 could not express. A stall nobody can
                #    explain is still a stall, and saying so is the point.
                print("   NO hook joins — stall cause UNKNOWN. The symptom is "
                      "real and unattributed; do not read the absence of a "
                      "suspect as the absence of a wedge.")
            for c in row["candidates"]:
                if c in row["actionable"]:
                    mark = "  <- ACTIONABLE"
                elif c["signature"] == SIG_UNMEASURED:
                    mark = "  (signature UNMEASURED — NOT a diagnosis and NOT a clear)"
                elif not c["parent_dead"]:
                    mark = "  (parent alive — NOT a diagnosis)"
                else:
                    mark = "  (signature says RAN — NOT a diagnosis)"
                print("   suspect pid=%s %s [%s] spawn gap %+.1fs parent_dead=%s%s"
                      % (c["pid"], c["script"], c.get("matched_by", "name"),
                         c["gap_s"], c["parent_dead"], mark))
                print("      signature %s: %s" % (c["signature"], c["signature_why"]))
            if row["ungraded"]:
                print("   ⚠ %d candidate(s) could not be graded against the "
                      "never-ran signature — the sweep is BLIND on these, which "
                      "is a hole and not a quiet result." % len(row["ungraded"]))
        # Printed AFTER the stall section for the same reason the dark section is:
        # wedge_sweep_codec_controls leg 2 asserts the FIRST stdout line opens with
        # the ASCII token `STALL `, and the alarm leads.
        for row in plugin_legs:
            print("PLUGIN-LEG  %s  entrypoint=%s  outstanding %.0fs — %s, NOT a seat"
                  % (row["session"][:8], row["entrypoint"], row["stall_age_s"],
                     row["session_class"]))
            print("   Not alarmed as a stalled seat: a plugin review leg that ends "
                  "mid-call freezes no session. Liveness is NOT asserted either way "
                  "— see the note at the split in main(); the session-id process "
                  "probe grades live seats dead and is not used.")
        if report["killed"]:
            print("killed: %s" % report["killed"])
        elif a.kill:
            print("kill enabled, nothing met all three criteria")
        # --- the lease x agency cross-check, reported last ---
        for d in dark:
            print("EMITTER-DARK  %s  seat=%s  lease=%s  oldest unanswered "
                  "call=%ss  transcript written %ss ago"
                  % (d["session"][:8], d["seat"],
                     "ABSENT" if d["lease_age_s"] is None
                     else "%ss" % d["lease_age_s"],
                     d["agency_age_s"], d["mtime_age_s"]))
            print("   %s" % d["why"])
            if d.get("lease_error"):
                print("   lease read REFUSED: %s" % d["lease_error"])
        if dark:
            # ⚠ THE DIVERGENCE PRINTS ON THE FINDING BRANCH TOO. It used to print
            #   only under `if not dark:` -- i.e. exactly when there was no row for
            #   it to qualify, and never when a reader was looking at one. Both
            #   voices named that; the grade above rests on this number.
            print("   (graded at lease ttl %.1fs, the ruled number; %s grades "
                  "the same leases at %ds — a lease aged between the two reads "
                  "fresh here and stale there, so this row is the CONSERVATIVE "
                  "side of a divergence this module does not reconcile)"
                  % (LEASE_TTL_S, LEASE_TTL_OTHER[0], LEASE_TTL_OTHER[1]))
        if not dark:
            # ⚠ The empty case is PRINTED, with both TTLs named. A silent sweep and
            #   a sweep that found nothing are indistinguishable to a reader, and
            #   this one rests on a number two instruments in this fleet disagree
            #   about. [[empty-result-needs-its-count]] [[lane-silence-measures-the-lane]]
            print("emitter-dark sweep: none (lease ttl %.1fs, the ruled "
                  "number; %s grades the same leases at %ds and this module does "
                  "not reconcile that by default)"
                  % (LEASE_TTL_S, LEASE_TTL_OTHER[0], LEASE_TTL_OTHER[1]))
    # ⛔ THE RETURN CODE IS UNCHANGED AND EMITTER-DARK DOES NOT RAISE IT. This
    #    module's exit code is consumed (tools/ops_digest_source.py reads
    #    `return 1 if stalls else 0` by line), and a new alarm silently sharing
    #    the stall's code would make every existing consumer report a stall that
    #    is not one. Raising it is a fleet decision, not a side effect of adding
    #    a report. [[one-exit-code-can-carry-two-causes]]
    # 1 = at least one stall (the alarm), 0 = quiet, 3 = could not read.
    return 1 if stalls else 0


if __name__ == "__main__":
    sys.exit(main())
