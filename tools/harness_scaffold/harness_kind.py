# -*- coding: utf-8 -*-
"""ONE GRAMMAR for "is this file a harness, and does it stamp itself".

⛔ WHY THIS IS A LIBRARY AND NOT A COPY-PASTE. The classifier was born inline in the module
body of a census script in the private workspace, where it cannot be
imported without RUNNING the census. The scaffold check needs the same decision. Retyping it
gives two graders that agree today and drift silently later, and on the day they disagree
neither is wrong on its face -- the reader has no way to tell which one moved
[[emitter-and-verifier-are-one-grammar]]. So it lives here once, and the census and the
check are both readers of it.

⚠ THIS FILE MUST STAY A LIBRARY -- zero top-level executable work. That is not style: the
census and the check both classify it, and a library that acquired a top-level call would
classify ITSELF as a harness owing a stamp it cannot sensibly make. `provenance.py` carries
the same constraint for the same reason.

⚠ WHAT `classify` CANNOT DO, disclosed rather than implied. It is a STATIC read. A file whose
only top-level work hides behind `if __name__ == "__main__":` reads as work (an `If` is not
in the inert set) and is called a HARNESS -- deliberately, since running it is the point. A
file that imports a module with import-time side effects reads as a LIBRARY, because the work
is not ITS work. And `is_stamped` matches the CALL BY NAME: a harness that aliases the stamp
under another name would read as unstamped, and one that defines its own unrelated `stamp()`
would read as stamped. The name is the contract [[names-must-resolve-against-artifacts]].
"""
import ast

# Nodes that are DECLARATION, not work. A module whose top level is only these produces
# nothing for a reader to attribute, so it owes no provenance line.
_INERT = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
          ast.Assign, ast.AnnAssign)

HARNESS = "HARNESS"
LIBRARY = "LIBRARY"
UNPARSEABLE = "UNPARSEABLE"

# ⛔ A UTF-8 BOM IS DECODING NOISE, AND IT IS STRIPPED HERE RATHER THAN IN ANY READER.
# Read with plain `utf-8` a BOM'd file arrives as a leading U+FEFF, `ast.parse` raises
# `invalid non-printable character U+FEFF`, and the file is UNPARSEABLE -- reported honestly,
# never classified. Six files in this repo sat in that state until owner (19) stripped them.
#
# ⭐ WHY THE STRIP IS HERE AND NOT AT THE `io.open` CALLS. It was cured per-reader first:
# `scaffold_check.py` went to `utf-8-sig` under an orchestrator ruling (`2c16a4434`), and the SAME HOUR
# that made the two readers of this grammar DISAGREE about the same file -- classified in one,
# unparseable in the other -- which is the exact split this module's docstring exists to
# prevent. A per-reader cure multiplies with readers; the grammar site is the one page every
# reader walks by construction. After this, a THIRD reader inherits the cure with zero edits
# of its own, however it chooses to decode [[fixes-in-derived-copies-do-not-survive-rederivation]].
#
# ⚠ WHAT IT DOES NOT DO. It strips ONE leading U+FEFF and nothing else: a UTF-16 file, a
# cp1252 mojibake read, or a BOM in the middle of a file are all still exactly as unparseable
# as they were, and should be. This is not an encoding-guesser and must never become one.
_BOM = "\ufeff"


def top_level_work(tree):
    """The top-level statements that actually DO something, docstrings excluded.

    ⭐ BARE CALLS COUNT. That is the correction the first census owed: a script whose entire
    body is `foo()` lines has no assignment and no def, and a classifier keyed to those
    excused it as a LIBRARY. It was wrong in the flattering direction -- it shrank the
    population that could hold a finding -- which is why it is written down here at the site
    rather than quietly fixed.
    """
    work = []
    for n in tree.body:
        if isinstance(n, _INERT):
            continue
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant):
            continue                        # module docstring or a bare string
        work.append(n)
    return work


def is_stamped(tree):
    """True if anything anywhere in the file CALLS something named `stamp`."""
    return any(
        isinstance(n, ast.Call) and (
            (isinstance(n.func, ast.Name) and n.func.id == "stamp")
            or (isinstance(n.func, ast.Attribute) and n.func.attr == "stamp"))
        for n in ast.walk(tree))


def classify(src):
    """-> (kind, stamped, detail). `stamped` is None when the source will not parse, because
    an unparseable file is UNKNOWN, not unstamped -- collapsing the two would report a
    tooling failure as a finding about the file [[honest-failure-outcomes]].

    A single leading U+FEFF is stripped first, so every reader of this grammar agrees about a
    BOM'd file no matter how it decoded the bytes -- see `_BOM` above for why that belongs
    here and not at the readers."""
    if src.startswith(_BOM):
        src = src[len(_BOM):]
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return UNPARSEABLE, None, str(e)[:60]
    kind = LIBRARY if not top_level_work(tree) else HARNESS
    return kind, is_stamped(tree), ""
