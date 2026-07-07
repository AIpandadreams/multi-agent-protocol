#!/usr/bin/env python3
"""Regression tests for reviewer_poller FIX-CONFIRMATION prompt framing.

A request file carrying a `ROUND-TYPE: FIX-CONFIRMATION` line must get a short
framing block ahead of the request payload (judge the named fixes only; end with
CONVERGED or NOT-CONVERGED); any other request must not. Stdlib unittest only,
importlib-loaded to match test_reviewer_watch.py:

    python -m unittest discover -s tests
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "reviewer_poller", ROOT / "tools" / "reviewer_poller.py")
rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rp)


class BuildPromptTest(unittest.TestCase):
    def test_fix_confirmation_marker_adds_framing(self):
        body = ("# review request — builder r02\n"
                "ROUND-TYPE: FIX-CONFIRMATION\n\n"
                "Findings F1, F2 from r01 and their fixes.\n")
        prompt = rp.build_prompt("review_request_builder_r02.md", body)
        self.assertIn("FIX-CONFIRMATION", prompt)
        self.assertIn("CONVERGED", prompt)
        self.assertIn("NOT-CONVERGED", prompt)
        self.assertIn("do not open new", prompt)
        # the original request body is still present after the framing
        self.assertIn("Findings F1, F2", prompt)

    def test_plain_request_gets_no_framing(self):
        body = ("# review request — builder r01\n"
                "ROUND-TYPE: FREEZE\n\n"
                "Please review parser-spec.md.\n")
        prompt = rp.build_prompt("review_request_builder_r01.md", body)
        self.assertNotIn(rp.FIX_CONFIRMATION_FRAMING, prompt)
        # header + body still assembled
        self.assertIn("REVIEW REQUEST", prompt)
        self.assertIn("Please review parser-spec.md", prompt)

    def test_marker_must_be_its_own_line(self):
        # a mention inside prose is not the marker — no false trigger
        body = ("# review request — builder r01\n\n"
                "This is not a ROUND-TYPE: FIX-CONFIRMATION reference in prose "
                "embedded mid-sentence.\n")
        prompt = rp.build_prompt("review_request_builder_r01.md", body)
        self.assertNotIn(rp.FIX_CONFIRMATION_FRAMING, prompt)


if __name__ == "__main__":
    unittest.main()
