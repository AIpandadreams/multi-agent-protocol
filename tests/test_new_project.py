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
from types import SimpleNamespace
from unittest import mock

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
        # Full v2 interview: topology(2) → side names(3) → principal → repo →
        # reviewer → grouped FILL walk (day-one 2 + deferrable 3 + orch 5) →
        # git-init → plugin mode.
        cfg = _quiet(np.wizard_preflight,
            input_fn=_feed(["y", "n", "engine", "helper", "",
                            "Ada", "path/to/repo origin main", "defer",
                            "defer", "defer",           # EMBARGOES, SIGNING
                            "", "", "",                 # PINNED/HEARTBEAT/WATCHER
                            "", "", "", "", "",         # orch slots
                            "y", "n"]),                 # git-init, manual?(no)
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
        # v2: plugin choice is a MODE, not a print-bool; 'no' to manual =
        # marketplace.
        self.assertEqual(cfg["plugin_mode"], "marketplace")

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


# ── side-name validation at entry (G1) ───────────────────────────────────────
class SideNameEntryValidationTest(unittest.TestCase):
    def test_underscore_rejected_then_reprompt(self):
        # first answer has an underscore (illegal — it is the channel-filename
        # separator); the helper re-prompts and takes the next legal answer.
        name = _quiet(np._ask_side_name, "owner", "owner",
                      _feed(["bad_name", "engine"]))
        self.assertEqual(name, "engine")

    def test_non_charset_rejected(self):
        name = _quiet(np._ask_side_name, "builder", "builder",
                      _feed(["has space", "helper"]))
        self.assertEqual(name, "helper")

    def test_falls_back_to_default_after_many_bad(self):
        # a piped/hostile input that never yields a legal name must not loop
        # forever — it falls back to the default.
        name = _quiet(np._ask_side_name, "owner", "owner",
                      _feed(["a_b", "c_d", "e_f", "g_h", "i_j", "k_l"]))
        self.assertEqual(name, "owner")

    def test_wizard_reprompts_bad_side_name(self):
        # drive the whole preflight with an underscore owner-side name first.
        cfg = _quiet(np.wizard_preflight,
            input_fn=_feed(["n", "n",             # 2-agent local
                            "own_er", "engine",   # owner: reject, then accept
                            "builder",            # builder side
                            "Ada", "defer", "defer",
                            "defer", "defer",     # day-one
                            "", "", "",           # deferrable
                            "n", "n"]),
            which_fn=lambda c: None)
        self.assertEqual(cfg["role_side"]["owner"], "engine")


# ── reviewer "none" quality-lever warning (G2) ───────────────────────────────
class ReviewerNoneWarningTest(unittest.TestCase):
    def test_none_records_value_and_warns(self):
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            cfg = np.wizard_preflight(
                input_fn=_feed(["n", "n", "owner", "builder", "Ada",
                                "defer", "none",         # reviewer = none
                                "defer", "defer", "", "", "",
                                "n", "n"]),
                which_fn=lambda c: None)
        self.assertEqual(cfg["slot_answers"]["REVIEWER"], "none")
        self.assertIn("quality lever", buf.getvalue())


# ── grouped FILL walk (G3) ───────────────────────────────────────────────────
class WalkFillSlotsTest(unittest.TestCase):
    def test_day_one_value_kept_deferrable_defaults_to_defer(self):
        answers = {}
        _quiet(np.walk_fill_slots, ["owner", "builder"],
               _feed(["no prod deploys",   # EMBARGOES (day-one) — typed
                      "",                   # SIGNING (day-one) — Enter → defer
                      "", "", ""]),         # deferrable → defer
               answers)
        self.assertEqual(answers["EMBARGOES / GATES"], "no prod deploys")
        self.assertEqual(answers["SIGNING"], np.DEFER_TOKEN)
        self.assertEqual(answers["WATCHER"], np.DEFER_TOKEN)
        # a 2-agent walk never asks the orchestrator-only slots
        self.assertNotIn("TICKS", answers)

    def test_preflight_answer_is_not_overwritten(self):
        answers = {"SIGNING": "gpg-local"}
        _quiet(np.walk_fill_slots, ["owner", "builder"],
               _feed(["", "SHOULD-NOT-APPEAR", "", "", ""]), answers)
        self.assertEqual(answers["SIGNING"], "gpg-local")


# ── plugin-install mode shapes settings.json (G6) ────────────────────────────
class PluginModeTest(unittest.TestCase):
    def test_build_settings_marketplace_has_blocks(self):
        s = np.build_settings("marketplace")
        self.assertIn("extraKnownMarketplaces", s)
        self.assertIn("enabledPlugins", s)
        self.assertIn("permissions", s)

    def test_build_settings_manual_omits_blocks(self):
        s = np.build_settings("manual")
        self.assertNotIn("extraKnownMarketplaces", s)
        self.assertNotIn("enabledPlugins", s)
        self.assertIn("permissions", s)  # allowlist still stamped

    def test_stamp_manual_writes_settings_without_marketplace(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            _quiet(np.stamp, "proj", dest, "2agent.local", ["owner", "builder"],
                   {"owner": "owner", "builder": "builder",
                    "orchestrator": "orch"}, "Ada", plugin_mode="manual")
            s = json.loads((dest / ".claude" / "settings.json").read_text(
                encoding="utf-8"))
            self.assertNotIn("enabledPlugins", s)
            self.assertIn("permissions", s)


# ── main()'s wizard path end-to-end (G6 wiring — the KeyError guard) ──────────
class MainWizardPathTest(unittest.TestCase):
    """Drive main() with a patched TTY + input so the plugin_mode wiring is
    exercised end-to-end. A regression guard: wizard_preflight returns the key
    `plugin_mode`, and main() must read that (not the old `plugin_install`), or
    a live --wizard run KeyErrors after the whole interview."""

    def _run_wizard(self, dest, manual_answer):
        # git-init answered 'n' so no real (GPG-signable) git commit runs.
        answers = ["n", "n", "owner", "builder", "Ada",
                   "path/to/repo origin main", "defer",
                   "defer", "defer", "", "", "",     # day-one + deferrable
                   "n", manual_answer]                # git-init(no), manual?
        argv = ["new_project.py", "--name", "demo", "--dest", str(dest),
                "--wizard"]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(sys.stdin, "isatty", lambda: True), \
             mock.patch("builtins.input", _feed(answers)):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                return np.main()

    def test_wizard_manual_mode_wires_through_no_keyerror(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            rc = self._run_wizard(dest, "y")   # manual = yes
            self.assertEqual(rc, 0)            # no KeyError on plugin_mode
            s = json.loads((dest / ".claude" / "settings.json").read_text(
                encoding="utf-8"))
            self.assertNotIn("enabledPlugins", s)  # manual omitted the blocks

    def test_wizard_marketplace_mode_wires_through(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            rc = self._run_wizard(dest, "n")   # manual = no → marketplace
            self.assertEqual(rc, 0)
            s = json.loads((dest / ".claude" / "settings.json").read_text(
                encoding="utf-8"))
            self.assertIn("enabledPlugins", s)


# ── adoption appendix on a non-empty-dest refusal (G8) ───────────────────────
class AdoptionOnRefusalTest(unittest.TestCase):
    def test_wizard_refusal_prints_adoption_pointer(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            dest.mkdir()
            (dest / "existing.txt").write_text("x", encoding="utf-8")
            argv = ["new_project.py", "--name", "demo", "--dest", str(dest),
                    "--wizard"]
            # answers only need to carry the interview to the stamp attempt;
            # git-init 'n' avoids any real git.
            answers = ["n", "n", "owner", "builder", "Ada", "defer", "defer",
                       "defer", "defer", "", "", "", "n", "n"]
            out = io.StringIO()
            with mock.patch.object(sys, "argv", argv), \
                 mock.patch.object(sys.stdin, "isatty", lambda: True), \
                 mock.patch("builtins.input", _feed(answers)):
                with redirect_stdout(out), redirect_stderr(io.StringIO()):
                    rc = np.main()
            self.assertEqual(rc, 1)                       # refused non-empty dest
            self.assertIn("ADOPTION CHECKLIST", out.getvalue())


# ── wizard seeds from CLI flags (Codex M2) ───────────────────────────────────
class WizardSeedTest(unittest.TestCase):
    def test_flags_prefill_defaults_enter_accepts(self):
        # every question answered with Enter ('' forever) — the resolved config
        # must reflect the SEED (the parsed CLI flags), proving flags pre-fill
        # the defaults and Enter accepts them.
        seed = SimpleNamespace(profile="2agent.git-sync", no_orchestrator=False,
                               owner_side="engine", builder_side="helper",
                               orch_side="orch",
                               principal="Bob", plugin_install="manual")
        cfg = _quiet(np.wizard_preflight, input_fn=_feed([]),
                     which_fn=lambda c: None, seed=seed)
        self.assertEqual(cfg["profile"], "2agent.git-sync")
        self.assertNotIn("orchestrator", cfg["roles"])
        self.assertEqual(cfg["role_side"]["owner"], "engine")
        self.assertEqual(cfg["role_side"]["builder"], "helper")
        self.assertEqual(cfg["principal"], "Bob")
        self.assertEqual(cfg["plugin_mode"], "manual")

    def test_no_seed_keeps_original_defaults(self):
        # seed=None must behave exactly as before (3-agent local, marketplace).
        cfg = _quiet(np.wizard_preflight, input_fn=_feed([]),
                     which_fn=lambda c: None)
        self.assertEqual(cfg["profile"], "3agent.local")
        self.assertEqual(cfg["plugin_mode"], "marketplace")

    def test_bad_side_flag_not_seeded_as_default(self):
        # an illegal --owner-side flag must NOT become the prompt default; the
        # wizard falls back to the canonical default rather than pre-filling an
        # underscore that would fail entry validation forever.
        seed = SimpleNamespace(profile="2agent.local", no_orchestrator=False,
                               owner_side="bad_side", builder_side="builder",
                               orch_side="orch", principal="Ada",
                               plugin_install="marketplace")
        cfg = _quiet(np.wizard_preflight, input_fn=_feed([]),
                     which_fn=lambda c: None, seed=seed)
        self.assertEqual(cfg["role_side"]["owner"], "owner")  # fell back


# ── defer on PRINCIPAL (Codex M3) ────────────────────────────────────────────
class PrincipalDeferTest(unittest.TestCase):
    def test_defer_principal_stamps_deferred_marker(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            _quiet(np.stamp, "proj", dest, "2agent.local", ["owner", "builder"],
                   {"owner": "owner", "builder": "builder",
                    "orchestrator": "orch"}, np.DEFER_TOKEN)
            text = (dest / "BINDINGS.md").read_text(encoding="utf-8")
            self.assertIn("| PRINCIPAL | {{DEFERRED", text)
            self.assertNotIn("| PRINCIPAL | defer |", text)

    def test_deferred_principal_warns_in_conformance(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            _quiet(np.stamp, "proj", dest, "2agent.local", ["owner", "builder"],
                   {"owner": "owner", "builder": "builder",
                    "orchestrator": "orch"}, np.DEFER_TOKEN)
            slots = cc.parse_bindings(dest)
            f = cc.Findings()
            cc.check_bindings(dest, slots, {"owner", "builder"}, "v2.6", f)
            self.assertTrue(any("PRINCIPAL" in m and "DEFERRED" in m
                                for m in _sev(f, "WARN")))


# ── adoption appendix BOTH paths (G8 + peer MODERATE) ────────────────────────
class AdoptionAppendixPathsTest(unittest.TestCase):
    def test_refusal_path_is_direct(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            np._print_adoption_appendix("proj", "path/to/ws", refusal=True)
        out = buf.getvalue()
        self.assertIn("ADOPTION CHECKLIST", out)
        self.assertIn("IN PLACE", out)          # direct wording for the adopter

    def test_success_path_is_clearly_optional(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            np._print_adoption_appendix("proj", "path/to/ws", refusal=False)
        out = buf.getvalue()
        self.assertIn("ADOPTION CHECKLIST", out)
        self.assertIn("OPTIONAL", out)          # ignorable on the success path


if __name__ == "__main__":
    unittest.main()
