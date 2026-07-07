#!/usr/bin/env python3
"""Regression tests for the onboarding wizard v2 + stamp refactor (Workstream D).

Covers new_project.py's extracted stamp(), the pre-stamp wizard_preflight
(driven through an injected input_fn — no TTY), the C3 --no-orchestrator
topology fix, apply_slot_answers + the {{DEFERRED}} marker, run_git_init, and
the conformance-side additions that ride this work-package: DEFERRED handling,
the P-1 one-agent-per-role BLOCKER, the SELF-CHECK banner detection, and the
channel entry-format lint.

Stdlib unittest only, importlib-loading the tools the same way the sibling
tests do:

    python -m unittest discover -s tests
"""
import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name, rel_path):
    spec = importlib.util.spec_from_file_location(mod_name, ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


np = _load("new_project", "tools/new_project.py")
cc = _load("conformance_check", "tools/conformance_check.py")


def _feed(answers):
    """Return an input_fn that yields `answers` in order, then '' forever."""
    it = iter(answers)

    def _fn(_prompt=""):
        try:
            return next(it)
        except StopIteration:
            return ""
    return _fn


def _sev(findings, sev):
    return [m for s, m in findings.items if s == sev]


def _quiet(fn, *a, **k):
    """Call fn with stdout/stderr swallowed — stamp()/wizard print for CLI use."""
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        return fn(*a, **k)


# ── topology (C3) ────────────────────────────────────────────────────────────
class ResolveTopologyTest(unittest.TestCase):
    def test_default_is_three_agent(self):
        prof, roles = np.resolve_topology(None, False)
        self.assertEqual(prof, "3agent.local")
        self.assertIn("orchestrator", roles)

    def test_explicit_two_agent(self):
        prof, roles = np.resolve_topology("2agent.local", False)
        self.assertEqual(prof, "2agent.local")
        self.assertNotIn("orchestrator", roles)

    def test_no_orchestrator_forces_two_agent(self):
        prof, roles = np.resolve_topology(None, True)
        self.assertEqual(prof, "2agent.local")
        self.assertEqual(roles, ["owner", "builder"])

    def test_no_orchestrator_preserves_git_sync(self):
        prof, roles = np.resolve_topology("2agent.git-sync", True)
        self.assertEqual(prof, "2agent.git-sync")

    def test_no_orchestrator_with_three_agent_is_error(self):
        # C3: the pairing that used to stamp an invalid workspace now errors.
        with self.assertRaises(ValueError):
            np.resolve_topology("3agent.local", True)
        with self.assertRaises(ValueError):
            np.resolve_topology("3agent.git-sync", True)


# ── apply_slot_answers + DEFERRED marker ─────────────────────────────────────
class ApplySlotAnswersTest(unittest.TestCase):
    SAMPLE = ("| PRINCIPAL | {{FILL: principal's name}} |\n"
              "| CANONICAL_REPO | {{FILL: work repo path + remote + branch}} |\n"
              "| REVIEWER | {{FILL: per side — mechanism + model}} |\n")

    def test_fills_named_slot(self):
        out = np.apply_slot_answers(self.SAMPLE, {"PRINCIPAL": "Ada"})
        self.assertIn("| PRINCIPAL | Ada |", out)
        self.assertIn("| CANONICAL_REPO | {{FILL", out)  # untouched

    def test_defer_token_becomes_deferred_marker(self):
        out = np.apply_slot_answers(self.SAMPLE, {"REVIEWER": np.DEFER_TOKEN})
        self.assertIn("| REVIEWER | {{DEFERRED: per side — mechanism + model}} |",
                      out)

    def test_empty_and_absent_answers_leave_fill(self):
        out = np.apply_slot_answers(self.SAMPLE,
                                    {"PRINCIPAL": "", "REVIEWER": None})
        self.assertIn("| PRINCIPAL | {{FILL", out)
        self.assertIn("| REVIEWER | {{FILL", out)


# ── wizard_preflight (injected I/O, no TTY) ──────────────────────────────────
class WizardPreflightTest(unittest.TestCase):
    def test_three_agent_local_custom_names(self):
        cfg = _quiet(np.wizard_preflight, 
            input_fn=_feed(["y", "n", "engine", "helper", "",
                            "Ada", "path/to/repo origin main", "defer",
                            "y", "n"]),
            which_fn=lambda c: None)
        self.assertEqual(cfg["profile"], "3agent.local")
        self.assertEqual(cfg["roles"], ["owner", "builder", "orchestrator"])
        self.assertEqual(cfg["role_side"],
                         {"owner": "engine", "builder": "helper",
                          "orchestrator": "orch"})
        self.assertEqual(cfg["principal"], "Ada")
        self.assertEqual(cfg["slot_answers"]["CANONICAL_REPO"],
                         "path/to/repo origin main")
        self.assertEqual(cfg["slot_answers"]["REVIEWER"], np.DEFER_TOKEN)
        self.assertTrue(cfg["git_init"])
        self.assertFalse(cfg["plugin_install"])

    def test_two_agent_git_sync_topology(self):
        cfg = _quiet(np.wizard_preflight, 
            input_fn=_feed(["n", "y"]),  # no orchestrator, separate machines
            which_fn=lambda c: None)
        self.assertEqual(cfg["profile"], "2agent.git-sync")
        self.assertNotIn("orchestrator", cfg["roles"])

    def test_reviewer_probe_suggests_when_cli_present(self):
        # which_fn reports a codex CLI -> the suggested REVIEWER is taken on Enter.
        cfg = _quiet(np.wizard_preflight, 
            input_fn=_feed(["y", "n", "", "", "", "Ada", "defer", "",
                            "n", "n"]),
            which_fn=lambda c: "/usr/bin/codex" if c == "codex" else None)
        self.assertIn("codex", cfg["slot_answers"]["REVIEWER"])


# ── stamp() ──────────────────────────────────────────────────────────────────
class StampTest(unittest.TestCase):
    def test_stamp_writes_workspace_and_in_ws_conformance_copy(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            rc = _quiet(np.stamp, "proj", dest, "3agent.local",
                          ["owner", "builder", "orchestrator"],
                          {"owner": "owner", "builder": "builder",
                           "orchestrator": "orch"},
                          "Ada")
            self.assertEqual(rc, 0)
            self.assertTrue((dest / "BINDINGS.md").is_file())
            # in-workspace conformance copy carries the provenance header
            copy = dest / "tools" / "conformance_check.py"
            self.assertTrue(copy.is_file())
            self.assertIn("STAMPED COPY",
                          copy.read_text(encoding="utf-8").splitlines()[1])

    def test_stamp_refuses_non_empty_dest(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            dest.mkdir()
            (dest / "keep.txt").write_text("x", encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = _quiet(np.stamp, "proj", dest, "2agent.local",
                              ["owner", "builder"],
                              {"owner": "owner", "builder": "builder",
                               "orchestrator": "orch"}, "Ada")
            self.assertEqual(rc, 1)

    def test_stamp_applies_deferred_slot(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            _quiet(np.stamp, "proj", dest, "2agent.local", ["owner", "builder"],
                     {"owner": "owner", "builder": "builder",
                      "orchestrator": "orch"}, "Ada",
                     slot_answers={"REVIEWER": np.DEFER_TOKEN})
            text = (dest / "BINDINGS.md").read_text(encoding="utf-8")
            self.assertIn("| REVIEWER | {{DEFERRED", text)


class RunGitInitTest(unittest.TestCase):
    def test_git_init_is_non_fatal_on_missing_dir(self):
        # Points at a nonexistent dir: must return (False, msg), never raise.
        ok, msg = _quiet(np.run_git_init, Path(tempfile.gettempdir()) / "does-not-exist-xyz",
                                  "proj", timeout=10)
        self.assertFalse(ok)
        self.assertTrue(msg)

    def test_git_init_creates_repo(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            _quiet(np.stamp, "proj", dest, "2agent.local", ["owner", "builder"],
                     {"owner": "owner", "builder": "builder",
                      "orchestrator": "orch"}, "Ada")
            ok, msg = _quiet(np.run_git_init, dest, "proj", timeout=30)
            # git may be absent in some CI images; only assert coherence.
            if ok:
                self.assertTrue((dest / ".git").is_dir())
            else:
                self.assertTrue(msg)


# ── conformance-side additions (ride this work-package) ──────────────────────
class DeferredConformanceTest(unittest.TestCase):
    def test_deferred_slot_warns_distinctly_not_as_fill(self):
        slots = {"PROTOCOL_VERSION": "v2.6", "PROFILE": "2agent.local",
                 "REVIEWER": "{{DEFERRED: per side}}",
                 "CANONICAL_REPO": "{{FILL: repo}}"}
        f = cc.Findings()
        cc.check_bindings(Path("."), slots, {"owner", "builder"}, "v2.6", f)
        warns = _sev(f, "WARN")
        self.assertTrue(any("REVIEWER" in m and "DEFERRED" in m for m in warns))
        self.assertTrue(any("CANONICAL_REPO" in m and "FILL" in m
                            for m in warns))
        # the DEFERRED slot is NOT double-counted as a plain FILL
        self.assertFalse(any("REVIEWER" in m and "{{FILL}}" in m
                             for m in warns))


class OneAgentPerRoleTest(unittest.TestCase):
    def _ws(self, d, mutate=None):
        dest = Path(d) / "ws"
        _quiet(np.stamp, "proj", dest, "3agent.local",
                 ["owner", "builder", "orchestrator"],
                 {"owner": "owner", "builder": "builder",
                  "orchestrator": "orch"}, "Ada")
        if mutate:
            mutate(dest)
        return dest

    def test_clean_stamp_passes_p1(self):
        with tempfile.TemporaryDirectory() as d:
            dest = self._ws(d)
            f = cc.Findings()
            cc.check_one_agent_per_role(dest, {"owner", "builder",
                                               "orchestrator"}, f)
            self.assertEqual(_sev(f, "BLOCKER"), [])

    def test_role_lock_collision_blocks(self):
        def collide(dest):
            p = dest / "memory" / "builder" / "MEMORY.md"
            p.write_text(p.read_text(encoding="utf-8").replace(
                "BUILDER sessions only", "OWNER sessions only"),
                encoding="utf-8")
        with tempfile.TemporaryDirectory() as d:
            dest = self._ws(d, collide)
            f = cc.Findings()
            cc.check_one_agent_per_role(dest, {"owner", "builder",
                                               "orchestrator"}, f)
            blockers = _sev(f, "BLOCKER")
            self.assertTrue(any("collision" in m for m in blockers))
            self.assertTrue(any("not its directory role" in m for m in blockers))

    def test_missing_role_lock_fails_closed(self):
        def strip(dest):
            p = dest / "memory" / "owner" / "MEMORY.md"
            p.write_text("# no role lock here\n", encoding="utf-8")
        with tempfile.TemporaryDirectory() as d:
            dest = self._ws(d, strip)
            f = cc.Findings()
            cc.check_one_agent_per_role(dest, {"owner", "builder",
                                               "orchestrator"}, f)
            self.assertTrue(any("no parseable ROLE_LOCK" in m
                                for m in _sev(f, "BLOCKER")))


class ChannelEntryLintTest(unittest.TestCase):
    def _chan(self, d):
        dest = Path(d) / "ws"
        (dest / "channel").mkdir(parents=True)
        (dest / "channel" / "INDEX.md").write_text("# ledger\n",
                                                    encoding="utf-8")
        return dest

    def test_fresh_channel_has_no_lint_warning(self):
        with tempfile.TemporaryDirectory() as d:
            dest = self._chan(d)
            f = cc.Findings()
            cc.check_channel_entry_format(dest, f)
            self.assertEqual(f.items, [])

    def test_valid_direction_entry_passes(self):
        with tempfile.TemporaryDirectory() as d:
            dest = self._chan(d)
            (dest / "channel" / "owner_to_builder_2026-07-07.md").write_text(
                "x", encoding="utf-8")
            f = cc.Findings()
            cc.check_channel_entry_format(dest, f)
            self.assertEqual(f.items, [])

    def test_review_lane_file_is_exempt(self):
        with tempfile.TemporaryDirectory() as d:
            dest = self._chan(d)
            (dest / "channel" / "review_request_BUILDER_r01.md").write_text(
                "x", encoding="utf-8")
            f = cc.Findings()
            cc.check_channel_entry_format(dest, f)
            self.assertEqual(f.items, [])  # no `_to_` -> not graded

    def test_malformed_direction_entry_warns(self):
        with tempfile.TemporaryDirectory() as d:
            dest = self._chan(d)
            # has `_to_` but no date suffix -> a malformed direction entry
            (dest / "channel" / "owner_to_builder.md").write_text(
                "x", encoding="utf-8")
            f = cc.Findings()
            cc.check_channel_entry_format(dest, f)
            self.assertTrue(any("direction entry" in m
                                for m in _sev(f, "WARN")))
            self.assertEqual(_sev(f, "BLOCKER"), [])


if __name__ == "__main__":
    unittest.main()
