"""Raw-fd writes that either complete or say that they did not.

``os.write`` may return having written **fewer bytes than it was handed**. It
is not an all-or-nothing call, and treating it as one truncates files silently:
the bytes that did land are real, ``os.fsync`` reports success on them, and the
caller is told nothing.

Of this package's four raw-fd write sites, two checked the returned count and
two discarded it (measured 2026-08-19):

* ``queue_worker.py:640`` — checked; mints ``CAUSE_APPEND_SHORT_WRITE``.
* ``sidecar.py:364`` — checked; raises ``CAUSE_LEDGER_DAMAGED``.
* ``sidecar.py:468`` — **unchecked**.
* ``journal.py:273`` — **unchecked**, and followed by ``os.replace``, which
  promotes a short temp file to the real record name.

The check is made a property of the WRITER here so that no future caller has to
remember it. A rule that lives in four call sites is four chances to forget it
[[findings-are-classes-not-citations]].

⚠ **EINTR needs no handling.** Since PEP 475 (Python 3.5+) the interpreter
retries the syscall inside ``os.write`` itself, so a partial return here is a
genuine short write and never a signal artefact. Stated because a retry loop
that *also* guessed at EINTR would be reasonable-looking and wrong.

⛔ **THIS MODULE IMPORTS NOTHING FROM THE PACKAGE.** The import graph is
``journal → config``, ``sidecar → journal``, ``queue_worker → sidecar, journal``.
A leaf with no package imports is cycle-free by construction, whichever of the
three ends up calling it.
"""

import os


class IncompleteWrite(OSError):
    """A raw-fd write could not be completed.

    Carries the MEASURED landed count, because a caller writing a durable
    fault record needs the number that was actually observed — not one
    inferred later from an ``fstat`` that a concurrent writer may have moved
    [[measured-numbers-discipline]].

    ⚠ Subclasses ``OSError`` deliberately: every existing caller of these
    write sites already handles ``OSError`` from the surrounding ``os.open`` /
    ``os.fsync`` / ``os.close``, so an incomplete write cannot slip through a
    handler that was written to be exhaustive over I/O failure. Verified at
    the two call sites this package routes here: ``journal.atomic_write_json``
    escapes to ``queue_worker``, which contemplates exactly that
    (``queue_worker.py:968``).
    """

    def __init__(self, written, expected, path_hint=None):
        self.written = written
        self.expected = expected
        self.path_hint = path_hint
        super().__init__(
            "wrote %d of %d byte(s)%s"
            % (written, expected,
               "" if path_hint is None else " to %s" % (path_hint,))
        )


def write_all(fd, buf, *, path_hint=None):
    """Write every byte of ``buf`` to ``fd``, or raise `IncompleteWrite`.

    Returns ``len(buf)`` — a value that can only ever be the whole buffer, so a
    caller that ignores the return is still correct. The failure is carried by
    the exception, never by a count the caller must remember to compare
    [[invert-claim-gates-to-default-undischarged]].

    ⛔ **ZERO PROGRESS TERMINATES, and that arm is load-bearing.** A write
    returning 0 for a non-empty buffer would spin this loop forever — a hang,
    which is a worse failure than the truncation being cured. It is reported as
    an incomplete write and never retried [[honest-failure-outcomes]].

    ⚠ **A partial write is NOT rolled back.** The bytes that landed stay
    landed; this reports the shortfall, it does not repair the file. On an
    append-mode fd the file is left with a partial record, and the caller must
    decide what that means for its artifact — which is why the landed count is
    on the exception.
    """
    total = len(buf)
    if total == 0:
        return 0
    written = 0
    view = memoryview(buf)
    while written < total:
        n = os.write(fd, view[written:])
        if n <= 0:
            raise IncompleteWrite(written, total, path_hint)
        written += n
    return written
