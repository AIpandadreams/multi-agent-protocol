# -*- coding: utf-8 -*-
r"""outpath_gate.py — where does an instrument's OUTPUT actually go?

WHY THIS EXISTS
---------------
Two defects found (2026-08-04; verdict N8, in an earlier review entry) are the same defect:

  * `rev5_manifest.py:326` — `Path('_STATIC.json').write_text(...)`
    A BARE RELATIVE NAME. It lands in the process CWD, not beside the script,
    while the file's own docstring says it writes "next to itself".
  * `rev5_trace.py:209` — `Path(sys.argv[0]).parent / "REV5-trace.json"`
    `argv[0]` is the script path AS INVOKED. It usually agrees with `__file__`,
    which is exactly why this survives review — it diverges only when a caller
    does not set `argv[0]` to the script (`''`, `'-c'`, a shim/symlink), and
    then it lands in the CWD or beside the shim, silently.

The rule they violate was written as PROSE in a lane entry: *derive output paths
from `__file__`, and print them absolute*. ⛔ Prose does not run. This is the
same rule as a program.

WHAT IT REFUSES TO DO
---------------------
It does not trust its own silence. `--selftest` runs fixtures whose answers are
known, INCLUDING a clean one, and **aborts** if it fails to flag a planted
defect or invents a finding in the clean fixture. A scanner that reports zero
findings and a scanner that is broken produce identical output; the only thing
that tells them apart is a control (result 435). `--selftest` runs by default
before any scan, so a scan CANNOT report clean without the control having passed.

USAGE
    python outpath_gate.py <path-or-dir> [...] [--no-selftest] [--quiet]
EXIT
    0 clean · 1 findings · 2 usage · 3 SELFTEST FAILED (never trust the run)
"""
import ast
import io
import pathlib
import sys

ARGV0 = "ARGV0-DERIVED"
BARE = "BARE-RELATIVE"
ANCHORED = "__file__-anchored"
UNKNOWN = "UNRESOLVED"
REPORT_BARE = "REPORT-BARE-NAME"
REPORT_UNRESOLVED = "REPORT-UNRESOLVED"
READ_BARE = "READ-BARE-RELATIVE"
READ_ARGV0 = "READ-ARGV0-DERIVED"

WRITE_BAD = (ARGV0, BARE)
REPORT_BAD = (REPORT_BARE, REPORT_UNRESOLVED)
READ_BAD = (READ_BARE, READ_ARGV0)
BAD = WRITE_BAD + REPORT_BAD + READ_BAD

LANDS = {
    ARGV0: "beside argv[0] — the CWD when a caller does not set it to the "
           "script",
    BARE: "in the process CWD, not beside the script",
    REPORT_BARE: "⚠ the run's own citation names no directory — a filename "
                 "read as an address",
    REPORT_UNRESOLVED: "⚠ the destination is printed unresolved — relative "
                       "invocation prints a relative path",
    READ_BARE: "reads from the process CWD — finds nothing, or finds a "
               "DIFFERENT file, depending on where it was launched",
    READ_ARGV0: "reads beside argv[0] — the CWD when a caller does not set it "
                "to the script",
}


IO_MODULES = {"io", "os", "codecs", "gzip", "bz2", "lzma", "tokenize"}


def _open_call(n):
    """Normalise every spelling of `open` to (path_node, mode_or_None).

    ⛔ THE TRAP, caught only by reading output the selftest had certified:
       `p.open('w')` is `Path.open`, whose FIRST ARGUMENT IS THE MODE — the path
       is the receiver. Treating it like the builtin made the gate read the
       string 'w' as a filename and report it as a bare-relative path. Five
       copies of `migrate_workspace.py:367` were flagged on a mode string.
       ⚠ Twenty-two green fixtures never noticed, because not one of them
       used the method form.
    """
    f = n.func
    if isinstance(f, ast.Name) and f.id == "open":
        path = n.args[0] if n.args else None
        margs = n.args[1:]
    elif isinstance(f, ast.Attribute) and f.attr == "open":
        if isinstance(f.value, ast.Name) and f.value.id in IO_MODULES:
            path = n.args[0] if n.args else None      # io.open(path, mode)
            margs = n.args[1:]
        else:
            path = f.value                            # Path(...).open(mode)
            margs = n.args
    else:
        return None, None, False
    mode, present = None, False
    if margs:
        present = True
        if isinstance(margs[0], ast.Constant):
            mode = margs[0].value
    for kw in n.keywords:
        if kw.arg == "mode":
            present = True
            if isinstance(kw.value, ast.Constant):
                mode = kw.value.value
    # ⛔ (path, mode, mode_PRESENT) — the third value exists because
    #    `m = 'w'; open(p, m)` has a mode that is not statically known. The
    #    first version collapsed that onto "no mode given" and classified the
    #    site as a READ. A write reported as a read still shows up in the
    #    output, so it LOOKED like coverage — the reach prober even scored it a
    #    bonus, because it asked "detected?" and not "detected AS WHAT?".
    return path, mode, present


def _src(node):
    try:
        return ast.unparse(node)
    except Exception:                                    # pragma: no cover
        return "<unparseable>"


PATH_CTORS = {"Path", "PurePath", "PurePosixPath", "PureWindowsPath",
              "PosixPath", "WindowsPath"}


def _mentions(node, name, attr=None):
    """Does this expression mention `name` (optionally name.attr / name[...])?"""
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id == name:
            return True
        if attr and isinstance(n, ast.Attribute) and n.attr == attr:
            return True
    return False


def _ctor_name(call):
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else \
        (f.id if isinstance(f, ast.Name) else None)


def _anchor_refs(node, expanded=()):
    """Names/attributes that could anchor a path, with path-CONSTRUCTOR callees
    treated as transparent.

    ⛔ This is the bug the selftest caught: `_p.Path('_STATIC.json')` was read as
       anchored because `_p` is a Name and `_p.Path` is an Attribute. The module
       alias you call the constructor THROUGH anchors nothing — only what you
       pass it does.
    """
    refs, skip = [], set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and _ctor_name(n) in PATH_CTORS:
            for sub in ast.walk(n.func):          # the callee chain only
                skip.add(id(sub))
    for n in ast.walk(node):
        if id(n) in skip:
            continue
        # ⛔⛔ ATTEMPTED AND REVERTED — recorded because the failure is worth
        #    more than the fix would have been. Dataflow helps ARGV0 (which
        #    walks the resolved set for `sys.argv[0]`) but NOT BARE (which
        #    requires "nothing else anchors this"), so `d = 'o.json';
        #    open(d, 'w')` is missed while the argv[0] form of the same shape
        #    is caught. The obvious cure — stop counting a name as an anchor
        #    once it has been expanded — is UNSOUND: it suppresses the anchor
        #    even when the expansion does not bottom out in literals, so
        #    `(dest / "channel" / "INDEX.md").write_text(...)` reads as bare
        #    the moment `dest` appears anywhere in the module varmap.
        #    Corpus effect: 7 findings -> 82, all sampled ones false.
        #    ⭐ And the reach prober passed the broken version at exit 0,
        #    because it only ever sees synthetic fixtures. A change to a gate
        #    needs BOTH its fixtures and its corpus delta.
        #    ⇒ Limitation kept, sentence corrected. `expanded` is threaded
        #    through but deliberately unused; a sound version would require
        #    per-scope binding and a "resolution bottomed out in literals"
        #    test, which is a different instrument.
        if isinstance(n, ast.Name) and n.id not in PATH_CTORS:
            refs.append(n.id)
        elif isinstance(n, ast.Attribute) and n.attr not in PATH_CTORS:
            refs.append(n.attr)
    return refs


def _varmap(tree):
    """Last module-or-function-level binding of each simple name.
    Enough to follow `dest = <expr>` … `dest.write_text(...)`, which is the
    shape the REAL rev5_trace.py defect has — and the shape that escaped the
    first version of this gate entirely."""
    m = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    m[t.id] = n.value
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) \
                and n.value is not None:
            m[n.target.id] = n.value
    return m


def _resolve(node, varmap, depth=5, seen=None):
    """The expression plus every definition it transitively references."""
    seen = seen if seen is not None else set()
    out = [node]
    if depth <= 0:
        return out
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id in varmap and n.id not in seen:
            seen.add(n.id)
            out += _resolve(varmap[n.id], varmap, depth - 1, seen)
    return out


def _uses_argv0(node):
    """sys.argv[0] — as a subscript of sys.argv, or of a bare `argv`."""
    for n in ast.walk(node):
        if not isinstance(n, ast.Subscript):
            continue
        v = n.value
        is_argv = (isinstance(v, ast.Attribute) and v.attr == "argv") or \
                  (isinstance(v, ast.Name) and v.id == "argv")
        if not is_argv:
            continue
        idx = n.slice
        if isinstance(idx, ast.Constant) and idx.value == 0:
            return True
    return False


def _bare_literal(nodes, expanded=()):
    """A path built from string literals carrying no directory component, with
    nothing else anchoring it — i.e. it resolves against the process CWD."""
    lits, refs = [], []
    for node in nodes:
        lits += [n.value for n in ast.walk(node)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        refs += _anchor_refs(node, expanded)
    if not lits:
        return False
    for s in lits:                     # any separator or drive ⇒ not bare
        if "/" in s or "\\" in s or (len(s) > 1 and s[1] == ":"):
            return False
    return not refs


DEVICES = {"nul", "con", "prn", "aux", "/dev/null", "/dev/stdout",
           "/dev/stderr", "con:", "nul:"}


def _resolver_wrapped(nodes):
    """`os.path.abspath(argv[0])` is ABSOLUTE BY CONSTRUCTION.

    ⛔ Caught by hand-checking findings the selftest had certified: three
       instruments read their OWN SOURCE via `src = os.path.abspath(argv[0])`,
       which is both correct and the standard self-hashing idiom. The gate
       flagged all three because `classify` never consulted the resolver set —
       I had applied it only on the report side. A resolver anywhere in the
       derivation makes the result absolute; that is the whole point of it.
    """
    for node in nodes:
        for n in ast.walk(node):
            if not isinstance(n, ast.Call):
                continue
            cn = n.func.attr if isinstance(n.func, ast.Attribute) else \
                (n.func.id if isinstance(n.func, ast.Name) else None)
            if cn in RESOLVERS:
                return True
    return False


def _is_device(nodes):
    for node in nodes:
        for n in ast.walk(node):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) \
                    and n.value.strip().lower() in DEVICES:
                return True
    return False


def classify(node, varmap=None):
    varmap = varmap or {}
    nodes = _resolve(node, varmap)
    expanded = {n.id for sub in nodes for n in ast.walk(sub)
                if isinstance(n, ast.Name) and n.id in varmap}
    if _is_device(nodes):
        return ANCHORED           # NUL / /dev/null is not a path in a tree
    if _resolver_wrapped(nodes):
        return ANCHORED
    if any(_uses_argv0(n) for n in nodes):
        return ARGV0
    if any(_mentions(n, "__file__") for n in nodes):
        return ANCHORED
    if _bare_literal(nodes, expanded):
        return BARE
    return UNKNOWN


def _write_targets(tree):
    """Yield (lineno, target_expr_node, how) for every write in the module."""
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        # X.write_text(...) / X.write_bytes(...)
        if isinstance(f, ast.Attribute) and f.attr in ("write_text",
                                                       "write_bytes"):
            yield n.lineno, f.value, f.attr
            continue
        path, mode, present = _open_call(n)
        if path is None:
            continue
        if isinstance(mode, str) and any(c in mode for c in "wax"):
            yield n.lineno, path, "open(%r)" % mode
        elif present and mode is None:
            # Mode given but not statically known ⇒ treat as a WRITE candidate.
            # Conservative on purpose: a write to the wrong place is the more
            # consequential half, so an unknown mode belongs on this face.
            yield n.lineno, path, "open(<mode not statically known>)"


def _read_targets(tree):
    """The mirror face (per an orchestrator ruling): a bare-relative name in a READ.

    `crosscheck_sweep.py:41` — `json.load(open("SWEEP-rows.json", …))` — is the
    live specimen. It is the same defect wearing the other mask: the write side
    puts a file where you did not mean, the read side looks where you did not
    mean. ⚠ The read face is the more dangerous of the two, because a missing
    file raises and a WRONG file does not.
    """
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Attribute) and f.attr in ("read_text",
                                                       "read_bytes"):
            yield n.lineno, f.value, f.attr
            continue
        path, mode, present = _open_call(n)
        if path is None:
            continue
        if not present:
            yield n.lineno, path, "open(default 'r')"
        elif isinstance(mode, str) and "r" in mode \
                and not any(c in mode for c in "wax"):
            yield n.lineno, path, "open(%r)" % mode


RESOLVERS = {"resolve", "absolute", "abspath", "realpath"}


def _report_sites(tree, written_names, dest_vars):
    """The OTHER half of the rule: does the run's own citation identify where
    the file went?

    ⛔ Originally scoped as a separate instrument. That was wrong — it needs the
       same destination model as the write side, and two programs sharing one
       model drift apart. `derive_exposure_sweep.py` is why it belongs here: the
       write is on :133 and the misleading citation is on :136, and only a pass
       that knows both can say the two are one defect.

    ⛔⛔ AND IT WAS WRONG A SECOND TIME, WHICH IS THE REASON THIS COMMENT IS
       LONG. The first working version flagged **122** sites. Sampling them
       killed it: `'F6 -- role dir CONTAINED, its auth-log.md links OUT'` is
       prose, `'argv : fixture_gate.py <subject>'` is a usage line,
       `'2. .gitattributes + .gitignore'` is a checklist item. It matched any
       sentence mentioning a filename the module happens to write.

       Worse, one of my own PLANTED fixtures asserted a defect that is not one:
       `__file__` is absolute in Python 3, so `print(Path(__file__).parent /
       'x')` already prints an absolute path. **The rule the fixture encoded was
       false, and twelve green fixtures did not notice, because every fixture
       was built from the same idea of the rule.**

       ⇒ Correct scope, and it is narrow on purpose: **a citation is only a
       defect when the destination it cites is ALREADY unanchored.** Report
       findings are RIDERS on write-side findings, never standalone. If the
       write is `__file__`-anchored, both the file and the sentence are fine.
    """
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        is_print = (isinstance(f, ast.Name) and f.id == "print") or \
                   (isinstance(f, ast.Attribute) and f.attr == "write" and
                    isinstance(f.value, ast.Attribute) and
                    f.value.attr in ("stdout", "stderr"))
        if not is_print:
            continue
        # Names appearing under a .resolve()/abspath() call are anchored.
        resolved = set()
        for c in ast.walk(n):
            if isinstance(c, ast.Call):
                cn = c.func.attr if isinstance(c.func, ast.Attribute) else \
                    (c.func.id if isinstance(c.func, ast.Name) else None)
                if cn in RESOLVERS:
                    for sub in ast.walk(c):
                        if isinstance(sub, ast.Name):
                            resolved.add(sub.id)
        for c in ast.walk(n):
            if isinstance(c, ast.Constant) and isinstance(c.value, str):
                for w in written_names:
                    if w and w in c.value and "/" not in c.value \
                            and "\\" not in c.value:
                        yield n.lineno, repr(c.value[:70]), REPORT_BARE, \
                            "names %r with no directory" % w
                        break
            elif isinstance(c, ast.Name) and c.id in dest_vars \
                    and c.id not in resolved:
                yield n.lineno, c.id, REPORT_UNRESOLVED, \
                    "destination printed without .resolve()"


def scan_source(src, label):
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return [(0, "<unparseable>", UNKNOWN, "SyntaxError: %s" % exc.msg)]
    varmap = _varmap(tree)
    out, written_names, dest_vars = [], set(), set()
    for lineno, target, how in _write_targets(tree):
        cls = classify(target, varmap)
        out.append((lineno, _src(target), cls, how))
        # ⛔ ONLY destinations that are ALREADY unanchored can have a defective
        #    citation. An anchored write cited by name is not a finding.
        if cls not in WRITE_BAD:
            continue
        if isinstance(target, ast.Name):
            dest_vars.add(target.id)
        for sub in _resolve(target, varmap):
            for c in ast.walk(sub):
                if isinstance(c, ast.Constant) and isinstance(c.value, str) \
                        and "." in c.value and "/" not in c.value \
                        and "\\" not in c.value:
                    written_names.add(c.value)
    for lineno, target, how in _read_targets(tree):
        cls = classify(target, varmap)
        if cls == ARGV0:
            out.append((lineno, _src(target), READ_ARGV0, how))
        elif cls == BARE:
            out.append((lineno, _src(target), READ_BARE, how))

    seen = set()
    for lineno, expr, cls, how in _report_sites(tree, written_names,
                                                dest_vars):
        if (lineno, cls) in seen:
            continue
        seen.add((lineno, cls))
        out.append((lineno, expr, cls, how))
    return out


def scan_file(p):
    src = io.open(p, "rb").read().decode("utf-8", "replace")
    return [(p,) + row for row in scan_source(src, p.name)]


# --------------------------------------------------------------------------
# The control. These answers are known; if the gate disagrees it is WRONG,
# and a wrong gate must refuse to run rather than certify.
# --------------------------------------------------------------------------
FIXTURES = [
    ("planted: the _STATIC.json defect, verbatim in shape",
     "import pathlib as _p, json as _j\n"
     "_p.Path('_STATIC.json').write_text(_j.dumps({}), encoding='utf-8')\n",
     {BARE}),
    ("planted: the argv[0] destination, verbatim in shape",
     "import pathlib, sys\n"
     "dest = pathlib.Path(sys.argv[0]).parent / 'REV5-trace.json'\n"
     "dest.write_text('{}', encoding='utf-8')\n",
     {ARGV0}),
    ("planted: argv[0] via `from sys import argv`",
     "import pathlib\nfrom sys import argv\n"
     "pathlib.Path(argv[0]).parent.joinpath('x.json').write_text('')\n",
     {ARGV0}),
    ("planted: bare relative through open(...,'w')",
     "f = open('report.txt', 'w')\n",
     {BARE}),
    ("CONTROL — correct code, MUST yield no finding",
     "import pathlib\n"
     "dest = pathlib.Path(__file__).parent / 'report.json'\n"
     "dest.write_text('{}', encoding='utf-8')\n"
     "print('wrote %s' % dest.resolve())\n",
     set()),
    # ⚠ This fixture expected (clean) while the gate was write-only, and that
    #   expectation went STALE the moment the read face landed — result 437's
    #   shape (a check whose PRECONDITION quietly stops holding), except the
    #   control caught it instead of certifying through it. Its real intent —
    #   "a read must never be reported as a WRITE defect" — is preserved.
    ("CONTROL — reads are classified as READS, never as writes",
     "import io\n"
     "src = io.open('anything.txt', encoding='utf-8').read()\n"
     "data = open('other.txt').read()\n",
     {READ_BARE}),
    ("CONTROL — __file__ reached THROUGH a variable, MUST stay clean",
     "import pathlib\n"
     "here = pathlib.Path(__file__).parent\n"
     "dest = here / 'out.json'\n"
     "dest.write_text('{}', encoding='utf-8')\n",
     set()),
    ("CONTROL — a caller-supplied destination is not a defect",
     "import sys, pathlib\n"
     "dest = pathlib.Path(sys.argv[1])\n"
     "dest.write_text('x')\n",
     set()),
    # ---- report side: the derive_exposure_sweep.py shape, and its controls ----
    ("planted: writes to CWD, then cites the bare name (the :133/:136 shape)",
     "import json\n"
     "with open('SWEEP-rows.json', 'w', encoding='utf-8') as fh:\n"
     "    json.dump({}, fh)\n"
     "print('rows written to SWEEP-rows.json for the cross-check')\n",
     {BARE, REPORT_BARE}),
    ("planted: argv[0] destination, then printed unresolved",
     "import pathlib, sys\n"
     "dest = pathlib.Path(sys.argv[0]).parent / 'REV5-trace.json'\n"
     "dest.write_text('{}')\n"
     "print('trace written to %s' % dest)\n",
     {ARGV0, REPORT_UNRESOLVED}),
    # ---- the adversarial controls. These are the ones I did NOT write first,
    #      and their absence is why the first working version reported 122. ----
    ("CONTROL — ⛔ __file__ IS ALREADY ABSOLUTE; no .resolve() needed",
     "import pathlib\n"
     "dest = pathlib.Path(__file__).parent / 'out.json'\n"
     "dest.write_text('{}')\n"
     "print('wrote %s' % dest)\n",
     set()),
    ("CONTROL — ⛔ PROSE mentioning a written filename is not a citation",
     "import pathlib\n"
     "dest = pathlib.Path(__file__).parent / 'auth-log.md'\n"
     "dest.write_text('x')\n"
     "print('F6 -- role dir CONTAINED, its auth-log.md links OUT')\n",
     set()),
    ("CONTROL — ⛔ a USAGE line naming a .py file is not a citation",
     "import pathlib\n"
     "p = pathlib.Path(__file__).parent / 'out.txt'\n"
     "p.write_text('x')\n"
     "print('  argv     : fixture_gate.py <subject>')\n",
     set()),
    ("CONTROL — an absolute-literal destination cited by name",
     "import pathlib\n"
     "dest = pathlib.Path(r'C:\\\\round\\\\out.json')\n"
     "dest.write_text('{}')\n"
     "print('wrote out.json')\n",
     set()),
    ("CONTROL — printing an unrelated literal is not a citation",
     "import pathlib\n"
     "dest = pathlib.Path(__file__).parent / 'out.json'\n"
     "dest.write_text('{}')\n"
     "print('done; see the round directory')\n",
     set()),
    # ---- READ face (per an orchestrator ruling). ⭐ These controls were written BEFORE the
    #      detector, deliberately: writing fixtures from the same idea as the
    #      rule is what produced 122 false positives on the report side. ----
    ("planted: the crosscheck_sweep.py:41 shape — bare-relative READ",
     "import json\n"
     "rows = json.load(open('SWEEP-rows.json', encoding='utf-8'))\n",
     {READ_BARE}),
    ("planted: bare-relative read via read_text",
     "import pathlib\n"
     "txt = pathlib.Path('config.json').read_text()\n",
     {READ_BARE}),
    ("CONTROL — a caller-supplied path to READ is not a defect",
     "import sys\n"
     "data = open(sys.argv[1], encoding='utf-8').read()\n",
     set()),
    ("CONTROL — an __file__-anchored read is correct",
     "import pathlib\n"
     "src = (pathlib.Path(__file__).parent / 'in.json').read_text()\n",
     set()),
    ("CONTROL — ⛔ a loop/iteration variable is UNRESOLVED, not a finding",
     "import pathlib\n"
     "for p in pathlib.Path('.').glob('*.py'):\n"
     "    body = p.read_text(encoding='utf-8')\n",
     set()),
    ("CONTROL — an absolute-literal read is correct",
     "data = open(r'C:\\\\round\\\\in.json', encoding='utf-8').read()\n",
     set()),
    ("CONTROL — ⛔ a WRITE must never be classified as a read",
     "fh = open('out.json', 'w', encoding='utf-8')\n",
     {BARE}),
    # ---- the method form. ⛔ 22 green fixtures missed this; five copies of
    #      migrate_workspace.py:367 were reported on the string 'w'. ----
    ("CONTROL — ⛔ Path.open('w') — first arg is the MODE, not a path",
     "import pathlib\n"
     "p = pathlib.Path(__file__).parent / 'out.txt'\n"
     "fh = p.open('w', encoding='utf-8')\n",
     set()),
    ("planted: Path.open('w') on a BARE relative receiver",
     "import pathlib\n"
     "fh = pathlib.Path('out.txt').open('w', encoding='utf-8')\n",
     {BARE}),
    ("planted: Path.open() read on a BARE relative receiver",
     "import pathlib\n"
     "fh = pathlib.Path('in.txt').open(encoding='utf-8')\n",
     {READ_BARE}),
    ("CONTROL — io.open(path, 'w') keeps the MODULE form's argument order",
     "import io, pathlib\n"
     "fh = io.open(pathlib.Path(__file__).parent / 'o.txt', 'w')\n",
     set()),
    ("CONTROL — ⛔ abspath(argv[0]) is ABSOLUTE: self-read, not a defect",
     "import io, os\nfrom sys import argv\n"
     "src = os.path.abspath(argv[0])\n"
     "text = io.open(src, encoding='utf-8').read()\n",
     set()),
    ("CONTROL — ⛔ 'NUL' is a device, not a path in a tree",
     "raw = open('NUL', 'rb').read()\n",
     set()),
    ("planted: ⛔ a VARIABLE mode is a WRITE candidate, never a read",
     "m = 'w'\nfh = open('o.json', m)\n",
     {BARE}),
    ("CONTROL — variable mode on an anchored path stays clean",
     "import pathlib\nm = 'w'\n"
     "fh = open(pathlib.Path(__file__).parent / 'o.json', m)\n",
     set()),
    ("planted: argv[0] WITHOUT a resolver still lands beside argv[0]",
     "import io, pathlib\nfrom sys import argv\n"
     "src = pathlib.Path(argv[0]).parent / 'notes.txt'\n"
     "text = io.open(src, encoding='utf-8').read()\n",
     {READ_ARGV0}),
]


def selftest(verbose=True):
    ok = True
    for name, src, expect in FIXTURES:
        got = {c for _, _, c, _ in scan_source(src, name) if c in BAD}
        good = got == expect
        ok &= good
        if verbose or not good:
            print("  %s %-52s expect %-24s got %s"
                  % ("ok " if good else "FAIL", name[:52],
                     sorted(expect) or "(clean)", sorted(got) or "(clean)"))
    return ok


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if not args:
        print(__doc__.strip().splitlines()[0])
        print("usage: outpath_gate.py <path-or-dir> [...] "
              "[--no-selftest] [--quiet]")
        return 2

    if "--no-selftest" not in flags:
        print("SELFTEST (the control runs before the scan, not after)")
        if not selftest(verbose="--quiet" not in flags):
            print("\n⛔ SELFTEST FAILED — this gate's silence is worthless. "
                  "Refusing to scan.")
            return 3
        print("  ✅ every planted defect caught; both controls clean\n")

    targets = []
    for a in args:
        p = pathlib.Path(a)
        if p.is_dir():
            targets += sorted(p.glob("**/*.py"))
        elif p.exists():
            targets.append(p)
        else:
            print("⚠ not found: %s" % a)

    findings, scanned = [], 0
    for p in targets:
        scanned += 1
        for row in scan_file(p):
            if row[3] in BAD:
                findings.append(row)

    print("scanned %d file(s); %d finding(s)" % (scanned, len(findings)))
    for p, lineno, expr, cls, how in findings:
        print("\n  ⛔ %s:%d  [%s]" % (p, lineno, cls))
        print("     target : %s" % expr[:150])
        print("     via    : %s" % how)
        print("     lands  : %s" % LANDS.get(cls, "?"))
    if findings:
        print("\n  ⇒ cure: derive from `pathlib.Path(__file__).parent`, and "
              "print the destination with `.resolve()` so the run's own "
              "citation is an address.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv))
