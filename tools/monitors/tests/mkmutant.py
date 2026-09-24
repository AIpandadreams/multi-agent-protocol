#!/usr/bin/env python3
"""Generate a single-point mutant FROM THE CURRENT LIBRARY, at run time.

⛔ WHY THIS EXISTS (codex cure verdict Q2, finding b). The first round shipped
mutants as CHECKED-IN FILES. Then the library was cured for E988 F-3.1/F-3.2 and
the stored mutants were not regenerated, so `MUTANT2_no_nul_delim.sh` became a
107-line copy of a 147-line library: it still carried the WITHDRAWN cost model
and lacked the UNREADABLE/regular-file cure. It went red — but on the missing
cure, not on its named single-point delta — and the acceptance runner reported
"all three mutants red" as if that were current evidence. A stale mutant does
not merely weaken a control; it manufactures a green.

The cure is structural, not vigilance: a mutant is DERIVED at run time from the
shipping library, so it cannot lag it. Staleness stops being a thing to notice.
[[fixes-in-derived-copies-do-not-survive-rederivation]] [[mutation-test-discipline]]

Usage: mkmutant.py <source> <out> <needle-file> <replacement-file>
Refuses unless the needle occurs EXACTLY once, and proves the delta landed.
Writes LF-only bytes (this repo's shell sources are LF; a CRLF rewrite would
show up as a whole-file diff — burned once already tonight).
"""
import pathlib
import sys


def main(argv):
    if len(argv) != 5:
        sys.stderr.write(__doc__)
        return 2
    src, out, nf, rf = (pathlib.Path(p) for p in argv[1:])
    body = src.read_bytes()
    needle = nf.read_bytes().replace(b"\r\n", b"\n").rstrip(b"\n")
    repl = rf.read_bytes().replace(b"\r\n", b"\n").rstrip(b"\n")

    n = body.count(needle)
    if n != 1:
        sys.stderr.write(
            "REFUSING: needle occurs %d time(s) in %s -- a mutation that is not "
            "single-point cannot attribute a red to the mechanism it names.\n"
            % (n, src))
        return 3

    mutated = body.replace(needle, repl)
    if mutated == body:
        sys.stderr.write("REFUSING: replacement left the bytes unchanged.\n")
        return 3
    out.write_bytes(mutated)

    # Landing proof, read back from DISK -- not from the variable we just wrote.
    disk = out.read_bytes()
    ok = disk == mutated and needle not in disk
    print("mutant %s: %d -> %d bytes (delta %+d); needle absent=%s; landed=%s"
          % (out.name, len(body), len(disk), len(disk) - len(body),
             needle not in disk, ok))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))
