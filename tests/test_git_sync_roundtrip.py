#!/usr/bin/env python3
"""Roundtrip tests for tools/git_sync.py [PROTOCOL v2.6].

A bare repo stands in for the WORKSPACE_REMOTE; two clones stand in for two
machines. The four cases pin the load-bearing behaviors of the git-sync
transport (transports/git-sync.md):

  (a) see        — clone B sees A's published entry after poll().
  (b) contention — the push loser rebases; both entries survive; order is
                   deterministic (the first-landed commit is an ancestor).
  (c) conflict   — an overlapping edit to the SAME file aborts (DISCONTINUITY),
                   never auto-merges.
  (d) reservation— a contended reservation-class publish DROPS and re-verifies
                   instead of rebasing the CONSUMED forward.

Stdlib unittest only. Windows-safe: tempfile dirs, test-local git identity, GPG
signing forced off so a cold agent key never blocks the run.

    python -m unittest discover -s tests
"""
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "git_sync", ROOT / "tools" / "git_sync.py")
gs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gs)


def _git(cwd, *args, check=True):
    return subprocess.run(["git", *args], cwd=str(cwd), check=check,
                          capture_output=True, text=True)


def _configure(clone):
    _git(clone, "config", "user.email", "test@example.com")
    _git(clone, "config", "user.name", "Test")
    _git(clone, "config", "commit.gpgsign", "false")
    _git(clone, "config", "core.autocrlf", "false")


def _commit(clone, relpath, content, msg):
    (Path(clone) / relpath).write_text(content, encoding="utf-8")
    _git(clone, "add", relpath)
    _git(clone, "commit", "-m", msg)
    return _git(clone, "rev-parse", "HEAD").stdout.strip()


def _head(clone):
    return _git(clone, "rev-parse", "HEAD").stdout.strip()


class GitSyncRoundtripTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.remote = base / "remote.git"
        self.a = base / "A"
        self.b = base / "B"
        _git(base, "init", "--bare", str(self.remote))
        # Pin the remote's default branch to `main` regardless of this git's
        # init.defaultBranch, so every clone checks out `main` (not `master`).
        _git(self.remote, "symbolic-ref", "HEAD", "refs/heads/main")

        # A establishes main with an initial commit and pushes -u.
        _git(base, "clone", str(self.remote), str(self.a))
        _configure(self.a)
        _git(self.a, "checkout", "-B", "main")
        (self.a / "shared.md").write_text("line\n", encoding="utf-8")
        _git(self.a, "add", "shared.md")
        _git(self.a, "commit", "-m", "initial")
        _git(self.a, "push", "-u", "origin", "main")

        # B clones the now-populated remote (HEAD -> main, so B lands on main).
        _git(base, "clone", str(self.remote), str(self.b))
        _configure(self.b)
        _git(self.b, "checkout", "-B", "main")

    def tearDown(self):
        self._tmp.cleanup()

    # (a) ---------------------------------------------------------------
    def test_b_sees_a_published_entry(self):
        _commit(self.a, "entry_a.md", "A entry\n", "A: entry")
        res = gs.publish(self.a, "main", "append")
        self.assertTrue(res.ok)
        self.assertEqual(res.action, "pushed")

        poll = gs.poll(self.b, "main")
        self.assertTrue(poll.fetched)
        self.assertEqual(len(poll.new_commits), 1)
        # Integrate ff-only and the file is now present in B.
        _git(self.b, "merge", "--ff-only", "origin/main")
        self.assertTrue((self.b / "entry_a.md").is_file())

    # (b) ---------------------------------------------------------------
    def test_contention_loser_rebases_both_survive(self):
        a_sha = _commit(self.a, "entry_a.md", "A entry\n", "A: entry")
        # B commits its OWN file while still behind (does not fetch first).
        _commit(self.b, "entry_b.md", "B entry\n", "B: entry")

        self.assertTrue(gs.publish(self.a, "main", "append").ok)   # A lands
        res = gs.publish(self.b, "main", "append")                 # B loses, rebases
        self.assertTrue(res.ok)
        self.assertEqual(res.action, "pushed")
        self.assertEqual(res.attempts, 2)

        # Both files survive; remote history is initial + A + B = 3 commits.
        self.assertTrue((self.b / "entry_a.md").is_file())
        self.assertTrue((self.b / "entry_b.md").is_file())
        count = _git(self.b, "rev-list", "--count", "origin/main").stdout.strip()
        self.assertEqual(count, "3")
        # Deterministic order: A's commit is an ANCESTOR of B's rebased tip.
        anc = _git(self.b, "merge-base", "--is-ancestor", a_sha, _head(self.b),
                   check=False)
        self.assertEqual(anc.returncode, 0)

    # (c) ---------------------------------------------------------------
    def test_overlapping_edit_aborts_as_discontinuity(self):
        # Both edit the SAME line of shared.md — a writer touching a file it
        # does not own. The rebase MUST conflict and abort, never auto-merge.
        _commit(self.a, "shared.md", "A-line\n", "A: edit shared")
        _commit(self.b, "shared.md", "B-line\n", "B: edit shared")

        self.assertTrue(gs.publish(self.a, "main", "append").ok)
        res = gs.publish(self.b, "main", "append")
        self.assertFalse(res.ok)
        self.assertEqual(res.action, "conflict")

        # Rebase was aborted cleanly: no conflict markers, B keeps its own edit,
        # working tree is clean.
        self.assertEqual((self.b / "shared.md").read_text(encoding="utf-8"),
                         "B-line\n")
        status = _git(self.b, "status", "--porcelain").stdout.strip()
        self.assertEqual(status, "")

    # (d) ---------------------------------------------------------------
    def test_reservation_drops_instead_of_rebasing(self):
        _commit(self.a, "res_a.md", "A reserves\n", "A: CONSUMED")
        # B reserves the same grant while behind.
        _commit(self.b, "res_b.md", "B reserves\n", "B: CONSUMED")

        # A's CONSUMED publishes ALONE with mode="reservation" (the spec's
        # reservation-commits-publish-alone rule — honoured inside our own
        # fixture). Uncontended, so it lands on attempt 1.
        a_res = gs.publish(self.a, "main", "reservation")
        self.assertTrue(a_res.ok)
        self.assertEqual(a_res.action, "pushed")
        self.assertEqual(a_res.attempts, 1)
        res = gs.publish(self.b, "main", "reservation")
        self.assertFalse(res.ok)
        self.assertEqual(res.action, "reservation-dropped")

        # DROPPED, not rebased: B's reservation commit is gone, HEAD == the
        # fetched tip, and A's reservation is what's present.
        self.assertFalse((self.b / "res_b.md").exists())
        self.assertTrue((self.b / "res_a.md").is_file())
        self.assertEqual(_head(self.b),
                         _git(self.b, "rev-parse", "origin/main").stdout.strip())

    # (e) lane-down under real contention with a single attempt --------------
    def test_lane_down_on_exhausted_attempts_keeps_local_work(self):
        # max_attempts=1 + genuine contention: B rebases onto A's landed tip but
        # has no second attempt to re-push, so it exhausts -> lane-down. The
        # rebase is real work; assert it is NOT lost (both files local) and the
        # remote simply never received B yet.
        _commit(self.a, "entry_a.md", "A entry\n", "A: entry")
        b_sha = _commit(self.b, "entry_b.md", "B entry\n", "B: entry")

        self.assertTrue(gs.publish(self.a, "main", "append").ok)   # A lands
        res = gs.publish(self.b, "main", "append", max_attempts=1)
        self.assertFalse(res.ok)
        self.assertEqual(res.action, "lane-down")
        self.assertEqual(res.attempts, 1)

        # No work lost: B rebased, so both files are present locally and B's
        # change still lives in local history; the remote has only initial + A.
        self.assertTrue((self.b / "entry_a.md").is_file())
        self.assertTrue((self.b / "entry_b.md").is_file())
        remote_count = _git(self.b, "rev-list", "--count",
                            "origin/main").stdout.strip()
        self.assertEqual(remote_count, "2")   # initial + A only; B not pushed
        subj = _git(self.b, "log", "-1", "--format=%s").stdout.strip()
        self.assertEqual(subj, "B: entry")    # B's commit is still HEAD's tip

    # (f) broken remote: reject + failed fetch = transport-error, NOT a drop --
    def test_broken_remote_is_transport_error_not_dropped(self):
        # The MAJOR finding: with an unreachable remote, the push fails and the
        # follow-up fetch ALSO fails; the reject cause is unknown, so a
        # reservation-class publish must return transport-error and mutate
        # nothing — never hard-reset the local CONSUMED away.
        head_before = _commit(self.b, "res_b.md", "B reserves\n", "B: CONSUMED")
        base = Path(self._tmp.name)
        _git(self.b, "remote", "set-url", "origin",
             str(base / "does-not-exist.git"))

        res = gs.publish(self.b, "main", "reservation")
        self.assertFalse(res.ok)
        self.assertEqual(res.action, "transport-error")
        # Local reservation intact: file present, HEAD unmoved.
        self.assertTrue((self.b / "res_b.md").is_file())
        self.assertEqual(_head(self.b), head_before)

    # (g) server-side refusal: reject + unmoved remote = non-contention -------
    def test_server_refusal_is_non_contention_not_dropped(self):
        # A pre-receive hook that always rejects makes the push fail while the
        # remote never moves. fix 1(ii): the loser must see rejected-no-
        # contention and mutate nothing — not treat an unmoved remote as a lost
        # race. If Git-for-Windows does not fire the sh hook on this machine,
        # skip loudly (the transport-error case above still pins the sibling
        # no-mutate path).
        hooks = self.remote / "hooks"
        hooks.mkdir(exist_ok=True)
        hook = hooks / "pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n",
                        encoding="utf-8", newline="\n")
        os.chmod(hook, 0o755)

        head_before = _commit(self.b, "res_b.md", "B reserves\n", "B: CONSUMED")
        res = gs.publish(self.b, "main", "reservation")
        if res.action == "pushed":
            self.skipTest("pre-receive hook did not fire on this git build; "
                          "non-contention path is pinned by the broken-remote "
                          "transport-error test instead")
        self.assertFalse(res.ok)
        self.assertEqual(res.action, "rejected-no-contention")
        # Nothing mutated: reservation file present, HEAD unmoved.
        self.assertTrue((self.b / "res_b.md").is_file())
        self.assertEqual(_head(self.b), head_before)


if __name__ == "__main__":
    unittest.main()
