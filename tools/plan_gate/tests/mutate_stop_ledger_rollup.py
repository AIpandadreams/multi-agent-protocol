"""Red-capability harness for BOTH stop_ledger_rollup batteries.

⛔ A GREEN BATTERY IS NOT EVIDENCE. Every leg passed on its first run against an
unmodified module, which is equally consistent with legs that assert nothing.
This harness breaks the module ONE CLAIM AT A TIME and requires the test named
for that claim to go RED, and every OTHER test's redness to be reported rather
than hidden [[mutation-test-discipline]].

⚠ IT ALSO COVERS THE HARNESS ITSELF. A first pass had a test for four claims
and no mutant for any of them — legs with no evidence they could ever fail,
invisible because the score only counts the mutants you wrote. Those four are
now seeded. A mutation score is a claim about the mutants, not about the tests
[[coverage-gate-ranges-over-rows-not-cures]].

⛔ IT NEVER TOUCHES THE LIVE FILE. Each mutant is a full copy of the tree shape
the test needs (`<tmp>/tools/plan_gate/{module,tests/test}`), because the test
resolves its import root from `__file__.parents[3]`. Patching the real module
in a shared working tree that peer sessions are committing from is how a
measurement becomes an outage.

⚠ A mutation that fails to APPLY is reported as VOID, not as a surviving
mutant: an unapplied substitution proves nothing about the test and must not
be read as one. [[honest-failure-outcomes]] [[instrument-must-prove-it-fired]]
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "stop_ledger_rollup.py"
# BOTH batteries. The first (de15af08b) asserted in prose that its legs "go RED
# against the pre-cure source"; that was never executable, so this harness is
# also the first machine check of those 11 legs. A mutant names whichever
# battery owns its claim, and the run is over the union.
TESTS = [HERE / "test_stop_ledger_rollup.py",
         HERE / "test_stop_ledger_rollup_projection.py"]

# (name, old, new, test that MUST go red)
MUTANTS = [
    ("skip-folded-in-as-a-measured-zero",
     'if row["runnable"] not in ("skip", "n/a", None):',
     'if True:',
     "test_skip_is_not_folded_in_as_a_measured_zero"),

    ("real-zero-no-longer-measured",
     'if row["runnable"] not in ("skip", "n/a", None):',
     'if row["runnable"] not in ("skip", "n/a", None, "0"):',
     "test_normal_receipts_aggregate"),

    ("unparseable-line-silently-dropped",
     'yield {"defect": f"unparseable-row:{path.name}"}',
     'pass',
     "test_unparseable_line_yields_a_defect"),

    ("unreadable-file-silently-dropped",
     'yield {"defect": f"unreadable:{path.name}:{exc.__class__.__name__}"}',
     'pass',
     "test_unreadable_log_yields_a_defect"),

    ("defects-stamped-onto-every-seat-day",
     'str(len(a["sessions"])), "-"]))',
     'str(len(a["sessions"])), (f"defects={len(defects)}" if defects else "-")]))',
     "test_a_parse_defect_is_not_stamped_onto_seat_rows"),

    ("orphan-row-always-emitted",
     'if defects:\n        out.append("\\t".join(',
     'if True:\n        out.append("\\t".join(',
     "test_no_defects_means_no_unattributable_row"),

    # ⚠ NARROWED after the first run. Deleting the whole alternation removed
    # the NAMED GROUP too, so `m.group("subagent")` raised on every line and 25
    # of 26 tests went red — a mutant that kills the battery proves the regex
    # matters, not that this test isolates the claim. Breaking only the LITERAL
    # keeps the shape intact and makes exactly one test go red.
    ("subagent-shape-unrecognised",
     r'(?P<subagent>SUBAGENT-EXEMPT)',
     r'(?P<subagent>SUBAGENT-NEVER-MATCHES)',
     "test_subagent_rows_are_excluded_without_being_defects"),

    ("header-column-renamed",
     'HEADER = ("date\\tseat\\tstops',
     'HEADER = ("day\\tseat\\tstops',
     "test_header_column_names_are_pinned_not_only_their_count"),

    ("would-block-no-longer-a-block",
     'if dec in ("block", "would-block"):',
     'if dec == "block":',
     "test_both_block_decisions_count"),

    ("announce-branches-reordered-so-v2-double-counts",
     'if "announce-own-act-v2" in kl:\n                a["ann_v2"] += 1\n            elif "announce-own-act" in kl',
     'if "announce-own-act" in kl:\n                a["ann_census"] += 1\n            elif "announce-own-act-v2" in kl',
     "test_v2_class_does_not_also_count_as_census"),

    # ⚠ THIS MUTANT WAS WRONG ON ITS FIRST RUN AND SURVIVED FOR THAT REASON.
    # It replaced only the message PREFIX; the continuation line still carried
    # "— instrument silent, NOT a measured zero", so the mutant rendered the
    # CORRECT behaviour and the test was right to stay green. A survivor
    # indicts the TEST only when the mutant actually implements the defect its
    # name claims — otherwise it indicts the mutation. Killing the branch is
    # the mutation the name promises. [[instrument-polarity-controls]]
    ("empty-day-renders-as-a-measured-looking-table",
     "if not rows:",
     "if False:",
     "test_empty_day_renders_silence_not_a_measured_zero"),

    ("unmeasured-seat-renders-as-zero",
     "wr = 'n/m'",
     "wr = '0'",
     "test_wholly_unmeasured_seat_renders_nm_not_zero"),

    ("partial-measurement-hides-its-denominator",
     "wr = f'{a[\"with_runnable\"]} <small>of {a[\"measured\"]} measured</small>'",
     "wr = str(a[\"with_runnable\"])",
     "test_partial_measurement_states_its_denominator"),

    ("measured-zero-relabelled-not-wired",
     "ann_cell = str(ann)",
     "ann_cell = str(ann) if ann else 'not wired'",
     "test_a_measured_zero_announce_renders_zero_not_not_wired"),

    ("tsv-appended-instead-of-regenerated",
     'out.write_text("\\n".join(rows) + "\\n", encoding="utf-8", newline="\\n")',
     'prev = out.read_text(encoding="utf-8") if out.exists() else ""\n'
     '    out.write_text(prev + "\\n".join(rows) + "\\n", encoding="utf-8", newline="\\n")',
     "test_the_tsv_is_regenerated_in_full_so_stale_seat_days_disappear"),

    ("crlf-reintroduced-at-the-write-site",
     'encoding="utf-8", newline="\\n")',
     'encoding="utf-8")',
     "test_written_file_carries_no_cr_bytes"),

    ("token-mode-also-writes",
     'if args.token:\n        print(render_token(agg, args.token))',
     'if args.token:\n        (ws / args.out).parent.mkdir(parents=True, exist_ok=True)\n'
     '        (ws / args.out).write_text("x", encoding="utf-8")\n'
     '        print(render_token(agg, args.token))',
     "test_token_mode_does_not_write_the_ledger"),

    ("seat-case-not-normalised",
     '"seat": (m.group("seat") or "").lower(),',
     '"seat": (m.group("seat") or ""),',
     "test_seat_case_is_normalised"),

    # ── added after a coverage check on the harness ITSELF: these four claims
    #    had tests but no mutant, so nothing showed their legs could go red.
    ("allowed-stop-miscounted-as-a-block",
     'if dec in ("block", "would-block"):',
     'if True:',
     "test_an_allowed_stop_is_not_a_block"),

    ("allow-announce-decision-path-removed",
     'elif "announce-own-act" in kl or dec.startswith("allow-announce"):',
     'elif "announce-own-act" in kl:',
     "test_allow_announce_decision_also_lands_in_census"),

    ("caveat-hoisted-above-the-table",
     "lines += ['</table>',",
     "lines = ['<p class=\"caveat\">x</p>'] + lines + ['</table>',",
     "test_the_caveat_ships_inside_the_block_after_the_table"),

    ("seat-day-key-collapses-the-date",
     'k = (row["date"], row["seat"])',
     'k = ("2026-08-30", row["seat"])',
     "test_seat_days_are_distinct_across_dates_and_seats"),
]


def run(mut_dir, expr=None):
    tdir = mut_dir / "tools" / "plan_gate" / "tests"
    cmd = [sys.executable, "-m", "pytest"] + [str(tdir / t.name) for t in TESTS] + [
        "-q", "--no-header", "-p", "no:cacheprovider"]
    if expr:
        cmd += ["-k", expr]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(mut_dir))
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    src = MOD.read_text(encoding="utf-8")
    results = []
    for name, old, new, target in MUTANTS:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pg = root / "tools" / "plan_gate" / "tests"
            pg.mkdir(parents=True)
            for t in TESTS:
                shutil.copy2(t, pg / t.name)
            if src.count(old) != 1:
                results.append((name, "VOID", target,
                                f"anchor matched {src.count(old)}x, expected 1"))
                continue
            (root / "tools" / "plan_gate" / MOD.name).write_text(
                src.replace(old, new, 1), encoding="utf-8")

            rc_t, out_t = run(root, target)
            rc_all, out_all = run(root)
            killed = rc_t != 0
            # how much ELSE went red -- reported, never hidden: a mutation that
            # reddens half the battery says the tests are entangled, which is a
            # finding about the tests, not a better score.
            nfail = 0
            for tok in out_all.splitlines():
                if " failed" in tok and "passed" in tok or tok.strip().endswith("failed"):
                    for part in tok.replace(",", " ").split():
                        if part.isdigit():
                            nfail = int(part)
                            break
                    break
            results.append((name, "KILLED" if killed else "SURVIVED", target,
                            f"{nfail} test(s) red overall"))

    w = max(len(r[0]) for r in results)
    print("=" * (w + 46))
    print("MUTATION RESULTS -- each mutant must be KILLED by its named test")
    print("=" * (w + 46))
    bad = 0
    for name, verdict, target, note in results:
        flag = "  " if verdict == "KILLED" else "!!"
        if verdict != "KILLED":
            bad += 1
        print(f"{flag} {name:<{w}}  {verdict:<9} {note}")
        print(f"   {'':<{w}}  -> {target}")
    print("-" * (w + 46))
    print(f"{len(results) - bad}/{len(results)} mutants killed"
          f"{'' if not bad else '   !! ' + str(bad) + ' NOT killed -- those claims are untested'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
