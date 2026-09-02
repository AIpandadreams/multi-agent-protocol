#!/usr/bin/env python3
"""Arms for conformance_check.check_commit_identity.

    python -m unittest discover -s tests

⛔ WHY THIS FILE EXISTS, stated plainly because the omission is the lesson: the
commit-identity check shipped to a PUBLIC repo with ZERO coverage. Nothing in tests/
mentioned it. It then graded an ABSENT identity as a BLOCKER, which failed 11 tests on
the first bare CI runner to see it while passing on every developer machine -- because a
machine with a global git identity lends that identity to every synthetic fixture
workspace the suite builds. The gate was green only where its own precondition was
already satisfied, so the author's local run could not observe the defect at all.

The load-bearing arm is `test_absent_identity_is_not_a_blocker`. It is RED-BY-DESIGN
against the pre-fix checker, and it is the arm that makes the environment an EXPLICIT
input instead of ambient luck: every arm here sets or strips the resolved identity itself
rather than inheriting whatever the host happens to have configured
[[instrument-must-prove-it-fired]].
"""
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name, rel_path):
    spec = importlib.util.spec_from_file_location(mod_name, ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cc = _load("conformance_check", "tools/conformance_check.py")


def _sev(f, sev):
    """Findings at exactly this severity. Severity is read from the recorded tag, not
    inferred from a count -- a count cannot attribute a finding to the thing under test."""
    return [m for s, m in f.items if s == sev]


def _identity(msgs):
    """Only the findings this check emits, so an unrelated finding can never pass or fail
    an arm here. Every message from check_commit_identity is prefixed 'commit identity:'."""
    return [m for m in msgs if m.startswith("commit identity:")]


class _IdentityCase(unittest.TestCase):
    """Each arm runs with the resolved git identity under the arm's own control."""

    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in (
            "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM",
            cc.PERSONAL_EMAIL_MARKERS_ENV, cc.IDENTITY_ESCAPE,
        )}

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _strip_host_config(self):
        """Make the host's global/system git config unreadable to the subprocess.

        Verified to work in this environment (all of /dev/null, os.devnull and a
        nonexistent path yield rc=1 + empty), and the arms below assert the strip TOOK
        before grading anything -- a control that silently failed to strip would grade the
        host's identity and report green [[instrument-must-prove-it-fired]]."""
        os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
        os.environ["GIT_CONFIG_SYSTEM"] = os.devnull

    def _resolved(self, ws):
        r = subprocess.run(["git", "-C", str(ws), "config", "--get", "user.email"],
                           capture_output=True, text=True)
        return r.stdout.strip()

    def _repo(self, d, email=None):
        ws = Path(d)
        subprocess.run(["git", "-C", str(ws), "init", "-q"], check=True,
                       capture_output=True)
        if email is not None:
            subprocess.run(["git", "-C", str(ws), "config", "--local", "user.email",
                            email], check=True, capture_output=True)
        return ws

    def _run(self, ws):
        f = cc.Findings()
        cc.check_commit_identity(ws, f)
        return f


class AbsentIdentityTest(_IdentityCase):

    def test_absent_identity_is_not_a_blocker(self):
        """⭐ RED-BY-DESIGN against the pre-fix checker: this arm asserted 1 BLOCKER there.

        An absent EFFECTIVE identity cannot be a publication risk. The check resolves the
        full include chain, so a personal global address would be RETURNED and graded by
        the marker branch -- empty means there is nothing to inherit, and git refuses to
        create a commit with no identity, so nothing can reach a remote."""
        with tempfile.TemporaryDirectory() as d:
            ws = self._repo(d)                 # a repo with NO local user.email
            self._strip_host_config()
            self.assertEqual("", self._resolved(ws),
                             "the strip did not take; this arm would grade the HOST's "
                             "identity and its green would mean nothing")
            f = self._run(ws)
            self.assertEqual([], _identity(_sev(f, "BLOCKER")),
                             "an unresolvable identity must not block: nothing can leak "
                             "from an identity that does not exist")

    def test_absent_identity_is_still_REPORTED(self):
        """Downgraded is not dropped. Silence would make 'no identity' indistinguishable
        from 'identity verified', which is the failure this whole file refuses."""
        with tempfile.TemporaryDirectory() as d:
            ws = self._repo(d)
            self._strip_host_config()
            self.assertEqual("", self._resolved(ws), "the strip did not take")
            warns = _identity(_sev(self._run(ws), "WARN"))
            self.assertEqual(1, len(warns), f"expected exactly one WARN, got {warns}")
            self.assertIn("resolves to nothing", warns[0])
            self.assertIn("config --local user.email", warns[0],
                          "a block or warn that does not print its remedy is the kind "
                          "operators route around")


class PersonalAddressTest(_IdentityCase):

    def test_configured_personal_address_still_BLOCKS(self):
        """POSITIVE CONTROL for the arms above. Without it, they could be passing because
        the gate stopped firing altogether, which is a different (worse) bug than the one
        being fixed [[instrument-polarity-controls]]."""
        with tempfile.TemporaryDirectory() as d:
            ws = self._repo(d, email="someone@example-personal.com")
            self._strip_host_config()
            os.environ[cc.PERSONAL_EMAIL_MARKERS_ENV] = "example-personal.com"
            os.environ.pop(cc.IDENTITY_ESCAPE, None)
            self.assertEqual("someone@example-personal.com", self._resolved(ws),
                             "the fixture's identity did not take")
            blockers = _identity(_sev(self._run(ws), "BLOCKER"))
            self.assertEqual(1, len(blockers), f"expected one BLOCKER, got {blockers}")
            self.assertIn("someone@example-personal.com", blockers[0],
                          "the blocker must name the address it objected to")

    def test_noreply_address_with_markers_armed_is_clean(self):
        """The gate must not fire on the identity it is telling operators to adopt."""
        with tempfile.TemporaryDirectory() as d:
            ws = self._repo(d, email="1234+someuser" + cc.NOREPLY_SUFFIX)
            self._strip_host_config()
            os.environ[cc.PERSONAL_EMAIL_MARKERS_ENV] = "example-personal.com"
            f = self._run(ws)
            self.assertEqual([], _identity(_sev(f, "BLOCKER")))
            self.assertEqual([], _identity(_sev(f, "WARN")),
                             "an armed marker list plus a clean address is the fully "
                             "verified case; it should be silent")


class MarkerVacuityTest(_IdentityCase):

    def test_unconfigured_markers_are_reported_not_silently_passed(self):
        """With no marker list the personal-address branch CANNOT FIRE. A green that means
        'nothing was checked' must not be indistinguishable from one that means 'checked
        and clean' [[honest-failure-outcomes]]."""
        with tempfile.TemporaryDirectory() as d:
            ws = self._repo(d, email="someone@example-personal.com")
            self._strip_host_config()
            os.environ.pop(cc.PERSONAL_EMAIL_MARKERS_ENV, None)
            f = self._run(ws)
            self.assertEqual([], _identity(_sev(f, "BLOCKER")),
                             "with no markers there is no list to have matched")
            warns = _identity(_sev(f, "WARN"))
            self.assertEqual(1, len(warns), f"expected one vacuity WARN, got {warns}")
            self.assertIn(cc.PERSONAL_EMAIL_MARKERS_ENV, warns[0],
                          "the vacuity WARN must name the variable that arms the check")
            self.assertIn("CANNOT FIRE", warns[0])

    def test_empty_marker_list_is_the_same_as_unset(self):
        """A present-but-empty variable is a configured nothing, and it must not read as
        an armed list -- that would make the check vacuous AND silent."""
        with tempfile.TemporaryDirectory() as d:
            ws = self._repo(d, email="someone@example-personal.com")
            self._strip_host_config()
            os.environ[cc.PERSONAL_EMAIL_MARKERS_ENV] = "   ,  , "
            f = self._run(ws)
            self.assertEqual([], _identity(_sev(f, "BLOCKER")))
            self.assertIn("CANNOT FIRE", " ".join(_identity(_sev(f, "WARN"))))


if __name__ == "__main__":
    unittest.main()
