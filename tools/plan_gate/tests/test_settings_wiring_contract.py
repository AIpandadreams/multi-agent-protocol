"""A fleet rule — the wiring contract between `settings_wiring.diff`
and the file that is actually deployed, `.claude/settings.json`.

⛔ THE DEFECT THIS MODULE EXISTS FOR. Three tests in `test_plan_gate.py`
read `settings_wiring.diff` (`_staged_harness_timeout`, C-17's
`_pretooluse_timeout_from`, `TestCure2WallCap._hooks_object`) and **not one
test in the tracked suite reads `.claude/settings.json`**. Enumerated at
r-032: every occurrence of the string `settings.json` in `tests/` is a
stderr assertion, a diff-header comment, or prose — zero disk reads. So the
suite grades a STAGED artifact against itself, and the deployed wiring is
unobserved by construction [[source-vs-deployment-readings]].

⚠ C-21 §(iii) reached this conclusion by a DIFFERENT route — "the whole
tracked suite is green in a tree with no `.claude/` directory". Re-measured
here: `.claude/settings.json` IS tracked (3,682 B) and IS present in a
`git archive HEAD` tree, so that premise is false as written. The
conclusion survives on the stronger mechanism: the file's presence is
irrelevant because nothing reads it [[stated-reason-must-discriminate]].

⭐ THE CONDITION (from the orchestrator's review): "a diff that reads like an inventory will
drift like one." Measured at r-032 — the live file carries NINE hook
commands, the diff stages FOUR, and the five it never mentions include the
two `SessionStart startup|resume` entries that invoke
`render_debt_guard.py --emit`. That is the very surface C-21 §(iii) and
`ORCH031_SITE_CENSUS.md` §5(iii) both point at: the diff's SILENCE is what
made it readable as an inventory.

The contract has two admissible shapes and this module enforces whichever
the diff declares:
  MIRROR          — the diff stages every live hook; or
  DECLARED SUBSET — the diff stages some, and NAMES every live hook it does
                    not stage, in `NOT-STAGED:` lines.
A live hook that is neither staged nor named is the drift. A `NOT-STAGED:`
line that resolves to no live hook is the declaration rotting into a
wish-list [[names-must-resolve-against-artifacts]], and fails too — the
contract is bidirectional or it is an inventory again.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

STREAM = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[3]
DIFF = STREAM / "settings_wiring.diff"
DIFF_TWIN = (REPO / "workpapers" / "memory-overhaul-2026-07-31" / "stream-c"
             / "settings_wiring.diff")
LIVE = REPO / ".claude" / "settings.json"

# THE CURE (from the orchestrator's review). The matcher field was `[^|]*?` and could not
# hold a pipe, so a hook whose matcher is an ALTERNATION -- `Bash|PowerShell`,
# the shape every custody guard uses -- was UNDECLARABLE BY CONSTRUCTION: the
# declaration form was narrower than the thing it exists to declare. git_guard
# was worked around by STAGING it instead; rm_guard got neither and surfaced as
# an orphan that read as "untracked and undeclared" when it was in fact both.
# Curing the grammar cures the class; staging rm_guard would have greened the
# symptom and bought a third instance [[cure-discipline]].
#
# The matcher is lazy-any and the script is anchored at end-of-line as the last
# token containing neither a pipe nor a space, so the LAST `|` is the field
# separator. RESIDUAL, stated: this necessarily cannot distinguish a matcher
# holding pipes from a line carrying surplus fields -- a 4-field line the old
# grammar rejected now parses with the surplus swallowed into the matcher. It
# is caught, not tolerated: such a matcher resolves to no deployed hook and
# test_every_declaration_resolves_to_a_deployed_hook fails. Scripts are paths;
# if one ever needs a space or a pipe this grammar must change again, loudly.
DECL_RE = re.compile(
    r'^NOT-STAGED:\s*(?P<event>\S+)\s*\|\s*(?P<matcher>.*?)\s*\|'
    r'\s*(?P<script>[^|\s]+)\s*$')
NO_MATCHER = "(none)"


# --------------------------------------------------------------------------
# r-5693 CONTROLS for the grammar cure itself. The first RED under the old
# `[^|]*?` field and GREEN under the new one; the second is the no-op control
# that proves the regex can still REJECT, so a grammar widened into `.*`
# (which would parse anything and declare nothing) fails here
# [[instrument-must-prove-it-fired]], [[unfalsifiable-by-construction]].
# --------------------------------------------------------------------------
def test_declaration_grammar_accepts_an_alternation_matcher():
    line = ("NOT-STAGED: PreToolUse | Bash|PowerShell | "
            "tools/custody/rm_guard_hook.py")
    m = DECL_RE.match(line)
    assert m, (
        "the NOT-STAGED grammar cannot parse an alternation matcher. Every "
        "custody guard uses one, so under this grammar they are undeclarable "
        "and can only be hidden by staging them -- the defect this cures.")
    assert m.group("matcher") == "Bash|PowerShell", (
        "the matcher field parsed as %r -- it must round-trip the WHOLE "
        "alternation, not its first branch. A truncated matcher would match no "
        "deployed hook and the declaration would cover nothing while looking "
        "like coverage." % m.group("matcher"))
    assert m.group("script") == "tools/custody/rm_guard_hook.py"


@pytest.mark.parametrize("bad", [
    "NOT-STAGED: PreToolUse | Bash",             # only one separator
    "NOT-STAGED: | Bash | tools/x.py",           # no event field
    "NOT-STAGED: PreToolUse | Bash | ",          # empty script field
    "NOT-STAGED: PreToolUse|Bash|tools/x.py|",   # trailing separator, no script
])
def test_declaration_grammar_still_rejects_malformed_lines(bad):
    assert DECL_RE.match(bad) is None, (
        "the widened grammar accepted %r. A field widened to `.*` parses "
        "everything and therefore declares nothing -- this control is the "
        "difference between a cure and a deletion." % bad)


def test_the_widening_is_bounded_and_its_residual_is_caught_downstream():
    """STATED RESIDUAL, not a silent one.

    Taking the LAST `|` as the separator is what lets a matcher hold pipes, and
    it necessarily costs the ability to tell `matcher-with-pipes` from
    `extra fields`. A 4-field line the OLD grammar rejected now parses, with the
    surplus swallowed into the matcher.

    That is acceptable ONLY because it cannot pass quietly: the resulting
    matcher resolves to no deployed hook, and
    test_every_declaration_resolves_to_a_deployed_hook fails. This control pins
    both halves -- the parse AND the reason it is safe -- so a future edit that
    removes the downstream resolve check cannot leave this widening unguarded
    [[disclosed-residual-is-still-a-hole]].
    """
    m = DECL_RE.match("NOT-STAGED: PreToolUse | Bash | tools/a.py | extra")
    assert m is not None and m.group("matcher") == "Bash | tools/a.py", (
        "the residual changed shape; re-derive whether the downstream resolve "
        "check still catches it before trusting this grammar.")
    assert not any(r["matcher"] == "Bash | tools/a.py" for r in declarations()), (
        "a surplus-field declaration is present in the real file. It parses, "
        "resolves to no deployed hook, and must be fixed at the source.")


# --------------------------------------------------------------------------
# Readers. Both fail CLOSED on absence: a missing artifact is the strongest
# possible drift and must never arrive as a skip [[honest-failure-outcomes]].
# --------------------------------------------------------------------------
def _read(path: Path, what: str) -> str:
    if not path.exists():
        pytest.fail(
            f"{what} not found at {path}. This is a FAILURE, not a skip: the "
            "wiring contract is unverifiable without it, and an unverifiable "
            "contract that reports green is the defect this module cures.")
    return path.read_text(encoding="utf-8")


def _hooks(obj: dict, source: str) -> list[dict]:
    """Flatten a settings `hooks` object to one row per hook COMMAND.

    One entry may hold several commands, so the row — not the entry — is the
    unit a contract can range over.
    """
    rows = []
    for event, entries in (obj.get("hooks") or {}).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                rows.append({
                    "event": event,
                    "matcher": entry.get("matcher"),
                    "command": hook.get("command", ""),
                    "timeout": hook.get("timeout"),
                    "source": source,
                })
    return rows


def staged_rows() -> list[dict]:
    """The diff's added lines, parsed as the `hooks` object they stage.

    ⚠ `+++ b/.claude/settings.json` is a diff HEADER that also starts with
    '+' — excluded explicitly, the same trap `TestCure2WallCap._hooks_object`
    names. The prose header (including `NOT-STAGED:` lines) is NOT '+'
    prefixed and so cannot reach this parse; `test_declarations_do_not_reach
    _the_staged_fragment` is the control on that.
    """
    raw = _read(DIFF, "settings_wiring.diff")
    added = [l[1:] for l in raw.splitlines()
             if l.startswith("+") and not l.startswith("+++")]
    frag = "\n".join(added).strip().rstrip(",")
    assert frag.startswith('"hooks"'), (
        f"settings_wiring.diff's added lines no longer begin with the "
        f'"hooks" key — got {frag[:60]!r}. Re-point this parse, do not '
        "delete it.")
    return _hooks(json.loads("{" + frag + "}"), "staged")


def live_rows() -> list[dict]:
    return _hooks(json.loads(_read(LIVE, ".claude/settings.json")), "live")


def declarations() -> list[dict]:
    raw = _read(DIFF, "settings_wiring.diff")
    out = []
    for n, line in enumerate(raw.splitlines(), 1):
        if not line.startswith("NOT-STAGED:"):
            continue
        m = DECL_RE.match(line.strip())
        assert m, (
            f"settings_wiring.diff:{n} is a NOT-STAGED line the contract "
            f"cannot parse: {line!r}\nExpected: "
            f"'NOT-STAGED: <event> | <matcher or {NO_MATCHER}> | <script>'. "
            "An unparseable declaration is not a declaration — it would "
            "silently cover nothing while looking like coverage.")
        out.append({
            "event": m.group("event"),
            "matcher": (None if m.group("matcher") == NO_MATCHER
                        else m.group("matcher")),
            "script": m.group("script"),
            "line": n,
        })
    return out


def _key(row: dict) -> tuple:
    return (row["event"], row["matcher"], row["command"])


def _fmt(row: dict) -> str:
    return (f'{row["event"]} matcher={row["matcher"]!r} '
            f't={row["timeout"]} :: {row["command"]}')


# --------------------------------------------------------------------------
# Leg 1 — MIRROR direction. Everything staged must be deployed.
# --------------------------------------------------------------------------
def test_every_staged_hook_is_live():
    """A staged hook absent from the deployed file is a diff describing a
    machine that does not exist. Green today; it is the CONTROL that makes
    leg 2 meaningful — a contract that only ever checks one direction cannot
    tell a faithful subset from an abandoned one."""
    live = {_key(r): r for r in live_rows()}
    missing = [r for r in staged_rows() if _key(r) not in live]
    assert not missing, (
        "settings_wiring.diff stages hooks that are NOT in the deployed "
        ".claude/settings.json:\n  " + "\n  ".join(_fmt(r) for r in missing))


def test_staged_hooks_carry_the_deployed_timeout():
    """Same key, different `timeout`, is the drift that would not show up as
    a missing hook — and the suite DERIVES an acceptance bar from this
    number, so a silent divergence grades the gate against a wall that is
    not in production."""
    live = {_key(r): r for r in live_rows()}
    drift = [(s, live[_key(s)]) for s in staged_rows()
             if _key(s) in live and s["timeout"] != live[_key(s)]["timeout"]]
    assert not drift, (
        "staged vs deployed `timeout` disagree:\n  " + "\n  ".join(
            f'{_fmt(s)}\n    deployed t={l["timeout"]}' for s, l in drift))


# --------------------------------------------------------------------------
# Leg 2 — SUBSET direction. This is the row's motivating defect.
# --------------------------------------------------------------------------
def test_every_live_hook_is_staged_or_declared():
    """⛔ THE REPLAY. Every deployed hook must be either staged by the diff
    or NAMED in a `NOT-STAGED:` declaration.

    Measured at r-032 before the cure: 9 live hooks, 4 staged, 0 declared —
    five deployed surfaces the diff is silent about, four of them running
    programs out of `tools/plan_gate/` itself. Silence is what let a reader
    take four-of-nine for the wiring."""
    staged = {_key(r) for r in staged_rows()}
    decls = declarations()
    orphans = []
    for row in live_rows():
        if _key(row) in staged:
            continue
        covered = [d for d in decls
                   if d["event"] == row["event"]
                   and d["matcher"] == row["matcher"]
                   and d["script"] in row["command"]]
        if not covered:
            orphans.append(row)
    assert not orphans, (
        f"{len(orphans)} deployed hook(s) are neither staged by "
        "settings_wiring.diff nor declared in a NOT-STAGED line:\n  "
        + "\n  ".join(_fmt(r) for r in orphans)
        + "\n\nThe diff is being read as an inventory of the wiring while "
          "describing part of it. Stage them, or declare them.")


def test_every_declaration_resolves_to_exactly_one_live_hook():
    """A declaration naming no live hook is a wish-list entry; one matching
    two is ambiguous and covers whichever the reader guesses. Both fail: the
    exclusion list is only evidence if it resolves against the artifact."""
    live = live_rows()
    bad = []
    for d in declarations():
        hits = [r for r in live
                if r["event"] == d["event"] and r["matcher"] == d["matcher"]
                and d["script"] in r["command"]]
        if len(hits) != 1:
            bad.append((d, len(hits)))
    assert not bad, (
        "NOT-STAGED declarations that do not resolve to exactly one deployed "
        "hook:\n  " + "\n  ".join(
            f'settings_wiring.diff:{d["line"]}  {d["event"]} '
            f'matcher={d["matcher"]!r} script={d["script"]} -> {n} live '
            f'match(es)' for d, n in bad))


def test_declarations_do_not_reach_the_staged_fragment():
    """CONTROL for the cure's own mechanism. `NOT-STAGED:` lines live in the
    diff's prose header; `staged_rows()` and `TestCure2WallCap._hooks_object`
    both build from '+'-prefixed lines. If a declaration were ever written
    with a leading '+', it would corrupt the JSON parse into a hard error
    while looking like documentation."""
    raw = _read(DIFF, "settings_wiring.diff")
    stray = [n for n, l in enumerate(raw.splitlines(), 1)
             if l.lstrip("+").startswith("NOT-STAGED:") and l.startswith("+")]
    assert not stray, (
        f"NOT-STAGED declaration(s) written as diff ADDITIONS at line(s) "
        f"{stray} — they would be applied into .claude/settings.json and "
        "would break the staged-fragment parse.")
    assert declarations() or staged_rows(), "diff carries neither"


# --------------------------------------------------------------------------
# Leg 3 — the derived acceptance bar. C-17's cure anchored it to the wrong
# artifact AND selected within it the wrong way; both legs are needed.
# --------------------------------------------------------------------------
def gate_backstop(rows: list[dict]) -> float:
    """The harness `timeout` of the PreToolUse hook that runs THIS gate,
    selected BY THE COMMAND IT RUNS.

    ⛔ Why not `min()` over the PreToolUse block — the shape
    `_pretooluse_timeout_from` still uses. Measured on the deployed file:
    PreToolUse holds TWO entries, `plan_gate.py` at t=10 and
    `custody_emit_wrapper.sh` at t=5, so the min-over-the-block derivation
    returns **5** — a wall that belongs to a different hook. It returns the
    right number against the DIFF only because the diff stages exactly one
    PreToolUse entry. `TestCure2WallCap._gate_matcher` already selects by
    command for the matcher; the timeout beside it did not
    [[control-passing-for-the-wrong-reason]].
    """
    hits = [r for r in rows
            if r["event"] == "PreToolUse" and "plan_gate.py" in r["command"]]
    assert len(hits) == 1, (
        f"expected exactly one PreToolUse hook invoking plan_gate.py, found "
        f"{len(hits)}: " + "; ".join(_fmt(r) for r in hits))
    return float(hits[0]["timeout"])


def test_the_suites_wall_bar_is_the_deployed_one():
    """⛔ THE SECOND REPLAY. `test_plan_gate.HARNESS_TIMEOUT_S` is derived
    from the staged diff and its docstring says it "cannot drift away from
    the thing it guards". The thing it guards is the DEPLOYED timeout. This
    asserts the two agree — turning today's coincidence into a checked
    fact."""
    assert gate_backstop(staged_rows()) == gate_backstop(live_rows()), (
        "the suite's wall backstop is derived from settings_wiring.diff "
        f"(t={gate_backstop(staged_rows())}) but production runs "
        f"t={gate_backstop(live_rows())}. Every wedge fixture is being "
        "graded against a wall that is not the one the harness enforces.")


def test_min_over_the_block_is_not_the_backstop():
    """MUTATION-GRADE CONTROL, standing. Asserts the discredited derivation
    and the sound one actually DISAGREE on the deployed file — so
    `gate_backstop` is not passing for the reason `min()` would. If a future
    edit collapses PreToolUse to one entry this test fails LOUDLY rather
    than going quietly inert [[discriminator-needs-an-independent-difference]].
    """
    live = live_rows()
    block = [float(r["timeout"]) for r in live if r["event"] == "PreToolUse"]
    assert len(block) > 1, (
        "the deployed PreToolUse block holds one hook, so min-over-the-block "
        "and select-by-command coincide and this discriminator is inert. "
        "Re-derive the bar before trusting any wall assertion.")
    assert min(block) != gate_backstop(live), (
        "min-over-the-block now equals the by-command backstop; the "
        "discriminator no longer discriminates.")


# --------------------------------------------------------------------------
# Leg 4 — the second copy. A cure applied to one of two tracked copies is
# not applied [[fixes-in-derived-copies-do-not-survive-rederivation]].
# --------------------------------------------------------------------------
def test_both_tracked_copies_of_the_diff_are_byte_identical():
    """`settings_wiring.diff` is tracked at TWO paths. The suite reads the
    `tools/plan_gate/` one; a reader following the round's workpapers reads
    the other. Nothing kept them equal — measured byte-identical at r-032,
    and now held so."""
    a = _read(DIFF, "settings_wiring.diff")
    b = _read(DIFF_TWIN, "settings_wiring.diff (stream-c copy)")
    assert a == b, (
        f"the two tracked copies of settings_wiring.diff have diverged:\n"
        f"  {DIFF} ({len(a)} chars)\n  {DIFF_TWIN} ({len(b)} chars)\n"
        "A contract enforced on one copy is not enforced on the copy a "
        "reader happens to open.")
