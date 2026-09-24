#!/usr/bin/env python3
"""sleep_gate — mechanical refusal at the /sleep boundary (a fleet ruling, Phase B').

This is the half that REFUSES. A seat may not write a checkpoint while it owns
runnable ledger steps it has not explained. The turn-end boundary could not carry
a refusal — all four SOP-7 verdicts said so, because a turn-end block either
exempts nearly every interactive turn or interrupts the principal
mid-conversation. A /sleep is never the principal mid-conversation, so the
exemption problem does not arise here at all.

HONEST BOUND, carried in the code rather than discovered later: this gate lives
in a SKILL, not in the harness. It is mechanical (a program decides, not a
disposition) but it is NOT harness-enforced — a seat that never calls it is not
stopped by it. That is the difference between this and a Stop hook, and it is
stated to the principal in the same words.

EXPLAINING is not a bypass. A reason must NAME the step and its referent, and the
reason is written into the checkpoint record where it can be read back and
graded. An unexplained non-empty projection is the only refusal condition.

  --check           exit 0 = clear to checkpoint; exit 3 = REFUSED (reason on
                    stdout); exit 0 with a NOTE = degraded (see below)
  --explain "<step> <type>:<referent>"   record an explanation for one step
  --list            print this seat's runnable projection and any explanations

DEGRADED-OPEN, deliberately, and NARROWED (by the orchestrator's review): if the seat cannot be
resolved, or the explanation store itself cannot be read, this gate does NOT
refuse — it prints a loud NOTE and exits 0. A checkpoint is how work SURVIVES;
a gate that blocks checkpoints on its own malfunction would destroy the thing
it protects.

⛔ But that reason names the INSTRUMENT — states where the gate cannot know
what it is judging. A plan file that does not parse is NOT the gate's
malfunction; it is the LEDGER's state, and it is exactly the state a checkpoint
must not ride over unexplained, because the unparseable file may BE the
unexplained edit. A `load-error:` on a plan file therefore REFUSES, naming the
file and the parse error verbatim, unless it is EXPLAINED — through the
mechanism that already exists, an explanation keyed to the failing file. The
seat is never locked out: the way through a refusal is one explanation line,
which is this gate's whole purpose.

That explanation expires by itself. It is bound to the ledger sha like every
other, so it counts while the file is still unparseable and stops counting the
moment the file parses — the ledger changes, the sha changes, the entry goes
stale. The mirror of the NO_LEDGER rule in explanations().
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_common as pc  # noqa: E402
from stop_observer import resolve_seat, runnable  # noqa: E402

VALID_TYPES = {"blocked", "awaiting", "lane-down", "handoff", "hold", "not-mine"}

# ONE grammar for "there was no ledger to bind to", shared by the WRITER in
# main() and the READER in explanations(). It is a value no real digest can
# take (a ledger sha is 64 hex chars), which is what lets an unconditional
# equality carry the whole staleness test -- the same shape ruled for
# ledger_sha's empty case in a fleet ruling. Emitter and verifier must not be
# able to drift apart, so neither side spells the literal.
NO_LEDGER = "no-ledger"


def explanations(workspace: Path, seat: str) -> dict[str, str]:
    """Explanations are per-seat and expire with the ledger: an entry recorded
    against a different ledger state is stale and does not count. Otherwise an
    explanation written once would license every future checkpoint.

    FAILS CLOSED on an unreadable ledger (per a fleet ruling). The guard used to
    read `if cur and sha != cur`, and `cur and` short-circuits when ledger_sha
    returns None -- so the staleness test did not run at all, and an
    explanation recorded under ledger A still counted once the ledger became
    unreadable. The comparison is now UNCONDITIONAL, against the same NO_LEDGER
    sentinel the writer already records, which gives all four states one rule:

        recorded under A,         ledger reads A    -> counts
        recorded under A,         ledger reads B    -> stale
        recorded under A,         UNREADABLE        -> stale  (was: counted)
        recorded under NO_LEDGER, UNREADABLE        -> counts (only while so)

    MEASURED BOUND, carried here because this cure reads bigger than it is: it
    changes NO answer main() gives today. Every state that makes the ledger
    unreadable also makes load_plans report a load error, and main() returns 0
    with a NOTE on any load error BEFORE it consults this mapping -- so at the
    GATE the checkpoint was, and still is, licensed by the documented
    degrade-open, not by this short-circuit. What the cure fixes is this
    function's own honesty and --list, which reports explanations directly.
    tools/tests/sleep_gate_failclosed_controls.py carries both halves: the
    state table above, and gate-level legs that stop the wider claim from being
    made on this cure's behalf.
    """
    return read_explanations(workspace, seat)[0]


def read_explanations(workspace: Path, seat: str) -> tuple[dict[str, str], bool]:
    """(mapping, store_readable) — the same read, with the INSTRUMENT signal.

    "No explanations recorded" and "the explanation store cannot be read" are
    opposite states that the old single `except OSError: pass` collapsed into
    one empty mapping. Only the second is a gate malfunction, and only the
    second may degrade the gate open (per the orchestrator's review); an absent file is the
    ordinary case and must still be able to produce a refusal.
    """
    path = workspace / "plans" / f".sleep_explain.{seat}"
    cur = pc.ledger_sha(workspace) or NO_LEDGER
    out: dict[str, str] = {}
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return out, True
    except OSError:
        return out, False
    try:
        for line in raw.splitlines():
            parts = line.split("\t")
            if len(parts) != 4:
                continue
            sha, step, typ, ref = parts
            if sha != cur:
                continue  # stale: the ledger moved under this explanation
            out[step] = f"{typ}:{ref}"
    except OSError:
        return out, False
    return out, True


def load_errors(notes: list[str]) -> list[tuple[str, str]]:
    """[(plan filename, the note verbatim)] for every plan file that would not
    load. The filename is the key an explanation must use, and it is the same
    FILENAME-keyed form the runnable projection already uses for steps."""
    out = []
    for n in notes:
        if not n.startswith("load-error:"):
            continue
        detail = n[len("load-error:"):].strip()
        out.append((detail.split(":", 1)[0].strip(), detail))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--explain")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--workspace")
    ap.add_argument("--session", default="sleep")
    a = ap.parse_args()

    ws = Path(a.workspace or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    seat, how = resolve_seat(ws, a.session)
    if seat is None:
        print(f"NOTE sleep_gate: seat unresolved ({how}) — cannot establish a "
              f"refusal, so NOT refusing. Checkpoint proceeds unguarded.")
        return 0

    if a.explain:
        bits = a.explain.split(None, 1)
        if len(bits) != 2 or ":" not in bits[1]:
            print('REFUSED-MALFORMED: need "<plan/step> <type>:<referent>", '
                  f'types: {sorted(VALID_TYPES)}')
            return 2
        step, rest = bits[0], bits[1]
        typ, _, ref = rest.partition(":")
        if typ not in VALID_TYPES:
            print(f"REFUSED-MALFORMED: unknown type {typ!r}; "
                  f"valid: {sorted(VALID_TYPES)}")
            return 2
        if not ref.strip():
            print(f"REFUSED-MALFORMED: type {typ!r} needs a referent after ':' "
                  "— a bare type explains nothing")
            return 2
        sha = pc.ledger_sha(ws) or NO_LEDGER
        ok = pc.append_line(ws / "plans" / f".sleep_explain.{seat}",
                            f"{sha}\t{step}\t{typ}\t{ref.strip()}")
        print(f"recorded: {step} -> {typ}:{ref.strip()}" if ok
              else "WARN: explanation could not be written")
        return 0 if ok else 2

    ids, notes = runnable(ws, seat)
    known, store_ok = read_explanations(ws, seat)
    bad = load_errors(notes)
    if a.list:
        print(f"seat={seat}({how}) runnable={len(ids)}")
        for i in ids:
            print(f"  {i}  [{known.get(i, 'UNEXPLAINED')}]")
        for f, detail in bad:
            print(f"  load-error {f}  [{known.get(f, 'UNEXPLAINED')}]  {detail}")
        for n in notes:
            print(f"  note: {n}")
        return 0

    # The ONLY degrade-open left, and it is an INSTRUMENT state: the gate
    # cannot read what has been explained, so it cannot know what it would be
    # refusing over. A plan file that will not parse is NOT this case -- that
    # is the ledger's state, and it is handled below.
    if not store_ok:
        print("NOTE sleep_gate: the explanation store for this seat exists but "
              "cannot be read — this gate cannot know what has been explained, "
              "so it is NOT refusing. Checkpoint proceeds unguarded.")
        return 0

    unexplained = [i for i in ids if i not in known]
    unexplained_bad = [(f, d) for f, d in bad if f not in known]
    if not unexplained and not unexplained_bad:
        line = (f"CLEAR: seat={seat} runnable={len(ids)} "
                f"explained={len(ids)}")
        if bad:
            line += ("; " + str(len(bad)) + " unparseable plan file(s) "
                     "EXPLAINED: "
                     + ", ".join(f"{f} -> {known[f]}" for f, _ in bad))
        print(line + " — checkpoint may proceed")
        return 0
    owed = []
    if unexplained:
        owed.append(f"{len(unexplained)} unexplained runnable step(s)")
    if unexplained_bad:
        owed.append(f"{len(unexplained_bad)} unparseable plan file(s)")
    print(f"REFUSED: seat={seat} owns " + " and ".join(owed)
          + ". Work them, or explain each:")
    for i in unexplained:
        print(f"  {i}")
    for f, detail in unexplained_bad:
        print(f"  {f}  (will not load: {detail})")
    print('  explain with: python tools/plan_gate/sleep_gate.py --explain '
          '"<plan/step> <type>:<referent>"')
    print(f'  types: {sorted(VALID_TYPES)} — the referent must name what is '
          'actually holding it (a gate id, a dispatch, a seat, an auth id).')
    return 3


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"NOTE sleep_gate: non-fatal error ({exc}) — not refusing.")
        sys.exit(0)
