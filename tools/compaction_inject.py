#!/usr/bin/env python3
"""compaction_inject.py — compaction-boundary injection hook + nonce
sidecar. Part 2 (the memory failsafe) of the plan-ledger system specified
in docs/PLAN-LEDGER.md.

Two modes, wired to two harness events:

  --mark    (PreCompact hook)   Records that a compaction boundary is about
            to occur for this session: writes the SESSION-KEYED
            plans/.compaction_pending.<key> {session_id, marked_at}
            (session-keyed so concurrent seats cannot stomp each other's
            state). From this instant, the enforcement gate (plan_gate.py,
            deferred to its own release) BLOCKS gated action classes for
            this session until the digest demonstrably rides into the
            post-compaction context. If the mark WRITE FAILS, a durable
            fail-closed sentinel (.plan_gate_mark_failed.<key> at the
            WORKSPACE ROOT) is left instead so the gate still refuses
            gated classes — a failed mark must not report rc 0 having
            armed nothing; only if BOTH writes fail does the
            hook exit 1 (loud; the harness log is then the only record).

  --inject  (SessionStart hook, matcher "compact")   Renders the typed
            open-plan digest (steps/gates/clocks/constraints + the
            done-record — a projection of typed fields, never a summary),
            emits it as hookSpecificOutput.additionalContext so the harness
            injects it into the fresh context, and writes the SESSION-KEYED
            plans/.last_injection.<key> {session_id, nonce, injected_at,
            acked: false}. Review-hardened: that sidecar does NOT open the
            gate and the injector does NOT clear the pending mark. A
            sidecar can only ever prove the INJECTOR ran — never that the
            harness DELIVERED the digest into context (injected context is
            never serialized anywhere the filesystem can attest) — and the
            file is writable by any seat, so an earlier revision was
            defeated by a hand-written sidecar re-opening the gate.
            The gate stays CLOSED until an evidence-bearing ack —
            the `--ack` command of the ENFORCEMENT GATE (plan_gate.py,
            deferred to its own release), NOT a mode of this tool; this
            tool's modes are `--mark | --inject` only — echoes the nonce
            out of the injected digest (or supplies a fresh
            ledger sha). Further: the ack does NOT clear
            the mark either — the mark is RETAINED so the gate re-derives
            the ledger sha against the acked receipt at every subsequent
            gated call (a post-ack plan edit re-closes the gate as STALE);
            the mark is superseded by the next --mark. And it is
            NOT swept by the 7-day hygiene pass once the session
            holds an acked receipt — that sweep used to delete the retained
            mark while the receipt survived, which ended the "every
            subsequent gated call" binding silently (see _cleanup_stale).

Fail direction: both modes fail OPEN for the session (exit 0 — a wedged
injector must never freeze session start; wedged-hook session freezes are
a measured failure class), with ONE exception: --mark exits 1 when the
mark write AND the fail-closed sentinel write both fail, so the harness
log carries the only record. A failed --inject deliberately does NOT
write the sidecar and does NOT
clear the pending mark — so the enforcement gate keeps failing CLOSED for gated
classes until the ledger is re-read. The open/closed pair composes into a
safe chain. Internal watchdog budget (default 2.5 s, PLAN_GATE_BUDGET_S
to override), loud stderr.

Imports: standard library + PyYAML only.
"""

from __future__ import annotations

# Watchdog armed BEFORE heavy imports (same rationale as plan_gate.py).
import os
import sys
import threading
import time

_T0 = time.monotonic()
BUDGET_S = float(os.environ.get("PLAN_GATE_BUDGET_S", "2.5"))
_phase = {"v": "import"}


def _hard_exit() -> None:
    sys.stderr.write(
        f"[compaction_inject WEDGE] internal budget {BUDGET_S}s exceeded during "
        f"phase '{_phase['v']}' (internal elapsed {time.monotonic() - _T0:.2f}s) "
        "— fail-OPEN for the session (exit 0); the "
        "injection sidecar was NOT written, so plan_gate keeps gated classes "
        "fail-CLOSED until plans/ is re-read.\n")
    sys.stderr.flush()
    os._exit(0)


_TIMER = threading.Timer(BUDGET_S, _hard_exit)
_TIMER.daemon = True
_TIMER.start()

import json     # noqa: E402
import secrets  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_common as pc  # noqa: E402


def _read_payload() -> dict:
    _phase["v"] = "stdin"
    try:
        payload = json.loads(sys.stdin.read())
        return payload if isinstance(payload, dict) else {}
    except ValueError:
        return {}


def _acked_receipt_keys(pdir) -> set:
    """Session keys whose injection sidecar is an ACKED receipt carrying a
    ledger sha — i.e. sessions whose pending mark is load-bearing."""
    keys = set()
    try:
        for f in pdir.glob(f"{pc.SIDECAR_NAME}.*"):
            body = pc.read_json(f)
            if isinstance(body, dict) and body.get("acked") is True \
                    and body.get("ledger_sha") is not None:
                keys.add(f.name[len(pc.SIDECAR_NAME) + 1:])
    except OSError:
        pass
    return keys


def _cleanup_stale(ws, max_age_s: float = 7 * 86400) -> None:
    """Best-effort removal of session-keyed sidecars older than a week
    (session keys accumulate one file per session).

    Review-hardened: the pending mark is RETAINED
    after the ack and is what makes plan_gate re-derive the ledger sha at
    every subsequent gated call. This sweep deleted pending marks on mtime
    ALONE, and a mark's mtime never refreshes (the sidecar's does, at every
    ack) — so any session older than seven days silently lost its mark to
    another session's `--mark`, the ACKED receipt survived, and a later plan
    edit then ALLOWED for that session with no STALE block. The continuous
    binding claim was true only up to the first sweep — a guard whose
    precondition can expire out from under it is not a guard.

    Two changes: (a) a pending mark whose session has an ACKED receipt is
    NEVER swept — it is live security state, not hygiene litter (the ack
    also touches the mark, see plan_gate._ack, so an active session's mark
    tracks its activity); (b) pending/sidecar are swept as a PAIR, so no half
    of an EXISTING pair is removed — either both go or neither does. Scope,
    stated precisely: the age list is built only over halves that EXIST
    (`if p.exists()`), so a mark whose sidecar is ABSENT (not merely fresh)
    is still swept alone. That is dominated by the ungated `rm` of the mark
    a seat could run directly, so no mechanism change is owed; the claim is
    narrowed to match. Known residual: acked pairs accumulate one small JSON
    pair per session for the life of the workspace."""
    pdir = pc.plans_dir(ws)
    if not pdir.is_dir():
        return
    now = time.time()
    keep = _acked_receipt_keys(pdir)

    def _age(p) -> float:
        try:
            return now - p.stat().st_mtime
        except OSError:
            return -1.0

    try:
        for f in pdir.glob(f"{pc.OVERRIDE_NAME}.*"):
            try:
                if _age(f) > max_age_s:
                    f.unlink()
            except OSError:
                pass
    except OSError:
        pass
    seen = set()
    for pat, name in ((f"{pc.PENDING_NAME}.*", pc.PENDING_NAME),
                      (f"{pc.SIDECAR_NAME}.*", pc.SIDECAR_NAME)):
        try:
            for f in pdir.glob(pat):
                seen.add(f.name[len(name) + 1:])
        except OSError:
            pass
    for key in seen:
        if key in keep:
            continue                     # live receipt: mark is load-bearing
        pend = pdir / f"{pc.PENDING_NAME}.{key}"
        side = pdir / f"{pc.SIDECAR_NAME}.{key}"
        ages = [_age(p) for p in (pend, side) if p.exists()]
        # min() = the FRESHEST half. Keep the pair while EITHER half is
        # inside the window; only when both are past it do both go.
        if not ages or min(ages) <= max_age_s:
            continue
        for p in (pend, side):
            try:
                p.unlink()
            except OSError:
                pass


def do_mark() -> int:
    payload = _read_payload()
    session = payload.get("session_id") or "unknown-session"
    ws = payload.get("cwd") or os.getcwd()
    _phase["v"] = "mark-write"
    pdir = pc.plans_dir(ws)
    if not pdir.is_dir():
        sys.stderr.write(
            "[compaction_inject] no plans/ dir — pre-adoption workspace, "
            "nothing to protect, mark skipped (the enforcement gate does "
            "not enforce gated classes here either)\n")
        return 0
    _cleanup_stale(ws)
    ok = pc.write_json(pc.pending_path(ws, session), {
        "session_id": session,
        "marked_at": pc.utcnow().isoformat(timespec="seconds"),
    })
    if not ok:
        # A failed mark must leave a DURABLE fail-closed state,
        # not report rc 0 having armed nothing. The sentinel lives at the
        # WORKSPACE ROOT because plans/ is where the write just failed.
        sent_ok = pc.write_json(pc.mark_fail_sentinel(ws, session), {
            "session_id": session,
            "failed_at": pc.utcnow().isoformat(timespec="seconds"),
            "reason": "compaction-pending mark write failed",
        })
        if sent_ok:
            sys.stderr.write(
                "[compaction_inject] FAILED to write compaction-pending mark "
                "— durable fail-closed sentinel written instead; plan_gate "
                "will refuse gated classes for this session until an "
                "evidence-bearing --ack\n")
            return 0
        sys.stderr.write(
            "[compaction_inject] CRITICAL: mark write AND sentinel write "
            "both failed — the nonce gate is NOT armed for this "
            "compaction; exiting 1 so the harness log carries the only "
            "record\n")
        return 1
    return 0


def do_inject() -> int:
    payload = _read_payload()
    session = payload.get("session_id") or "unknown-session"
    ws = payload.get("cwd") or os.getcwd()
    now = pc.utcnow()

    _phase["v"] = "plan-load"
    test_sleep = float(os.environ.get("PLAN_GATE_TEST_SLEEP_S", "0") or 0)
    if test_sleep:  # slow-filesystem stub (test-only)
        time.sleep(test_sleep)
    plans, errors = pc.load_plans(ws)

    nonce = secrets.token_hex(8)
    _phase["v"] = "render"
    digest = pc.render_digest(plans, errors, nonce, now)

    _phase["v"] = "emit"
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": digest,
        }
    }))

    if errors:
        # Incomplete digest: refuse to certify the injection. Pending mark
        # stays; plan_gate keeps gated classes closed for this session.
        sys.stderr.write(
            "[compaction_inject] plan load errors — digest incomplete, "
            "sidecar NOT written (gated classes stay fail-CLOSED):\n"
            + "".join(f"  {e}\n" for e in errors))
        return 0

    _phase["v"] = "sidecar-write"
    ok = pc.write_json(pc.injection_path(ws, session), {
        "session_id": session,
        "nonce": nonce,
        "injected_at": now.isoformat(timespec="seconds"),
        "acked": False,
    })
    if not ok:
        sys.stderr.write(
            "[compaction_inject] FAILED to write injection sidecar — "
            "plan_gate will keep gated classes fail-CLOSED for this session\n")
        return 0
    # Review-hardened: the injector does NOT
    # clear the pending mark or the mark-fail sentinel. An earlier revision
    # did, which made the whole guarantee filesystem-only: writing a sidecar
    # (or hand-forging one) discharged the gate, and no receipt ever had to
    # come back THROUGH the model. The mark is
    # cleared by NOTHING in the discharge path — an evidence-bearing `--ack`
    # (nonce echoed from the injected digest, or a fresh ledger sha) writes
    # the receipt that SATISFIES the mark, and the mark is retained so
    # the gate keeps re-deriving the ledger sha for the rest of the
    # session. "For the rest of the session" is
    # true past day seven as well — _cleanup_stale no longer sweeps a
    # pending mark whose session holds an acked receipt, and sweeps
    # mark+sidecar as a pair otherwise. The injector's job ends at emitting
    # the digest and recording that it ran.
    sys.stderr.write(
        "[compaction_inject] digest emitted (nonce recorded). The gate stays "
        "CLOSED for gated classes until an evidence-bearing ack echoes the "
        "nonce out of the injected digest — the --ack command ships with the "
        "enforcement gate (plan_gate.py, its own reviewed release); until "
        f"then this receipt for session {session} simply records the "
        "injection.\n")
    return 0


def main() -> None:
    timer = _TIMER  # armed at module top, before imports
    if "--mark" in sys.argv:
        code = do_mark()
    elif "--inject" in sys.argv:
        code = do_inject()
    else:
        sys.stderr.write("usage: compaction_inject.py --mark | --inject\n")
        code = 0  # never block the session over a wiring typo — loudly open
    timer.cancel()
    sys.exit(code)


if __name__ == "__main__":
    main()
