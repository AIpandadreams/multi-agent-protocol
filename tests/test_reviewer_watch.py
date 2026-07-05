#!/usr/bin/env python3
"""Regression tests for reviewer_poller --watch settle/fallback semantics.

The interleaving here is easy to get subtly wrong (a mid-write channel must
never be swept — by either the settle path OR the periodic fallback path), so
it gets committed tests. Stdlib unittest only, to match the repo's no-extra-
dependency posture:

    python -m unittest discover -s tests
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "reviewer_poller", ROOT / "tools" / "reviewer_poller.py")
rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rp)


def _pairs(names):
    # plan_sweep only ever uses str(channel); a synthetic path is enough.
    return [(n, Path(n) / "channel") for n in names]


class PlanSweepTest(unittest.TestCase):
    def test_fallback_excludes_dirty(self):
        # THE regression: a fallback (timer) tick must not sweep a channel that
        # is mid-write, or it reintroduces the half-read race the settle path
        # was added to prevent.
        pairs = _pairs(["ws1", "ws2"])
        dirty = {str(Path("ws1") / "channel")}
        self.assertEqual(rp.plan_sweep(pairs, [], dirty, True), ["ws2"])

    def test_fallback_sweeps_all_when_none_dirty(self):
        pairs = _pairs(["ws1", "ws2"])
        self.assertEqual(rp.plan_sweep(pairs, [], set(), True), ["ws1", "ws2"])

    def test_settle_tick_sweeps_only_settled(self):
        pairs = _pairs(["ws1", "ws2"])
        self.assertEqual(rp.plan_sweep(pairs, ["ws1"], set(), False), ["ws1"])

    def test_noop_tick_returns_empty(self):
        pairs = _pairs(["ws1", "ws2"])
        self.assertEqual(rp.plan_sweep(pairs, [], set(), False), [])


class DetectSettledTest(unittest.TestCase):
    def test_change_then_settle(self):
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d) / "ws"
            chan = ws / "channel"
            chan.mkdir(parents=True)
            pairs = [(str(ws), chan)]
            sigs = {str(chan): rp.dir_signature(chan)}
            dirty = set()

            # Tick 1: a request appears -> channel goes dirty, nothing settles.
            (chan / "review_request_A_r01.md").write_text("body", encoding="utf-8")
            self.assertEqual(rp.detect_settled(pairs, sigs, dirty), [])
            self.assertIn(str(chan), dirty)

            # A fallback firing while it is still dirty must skip this channel.
            self.assertEqual(rp.plan_sweep(pairs, [], dirty, True), [])

            # Tick 2: no further writes -> signature holds one tick -> settles.
            self.assertEqual(rp.detect_settled(pairs, sigs, dirty), [str(ws)])
            self.assertNotIn(str(chan), dirty)

    def test_one_settles_while_other_still_writing(self):
        with tempfile.TemporaryDirectory() as d:
            ws1, ws2 = Path(d) / "ws1", Path(d) / "ws2"
            c1, c2 = ws1 / "channel", ws2 / "channel"
            c1.mkdir(parents=True)
            c2.mkdir(parents=True)
            pairs = [(str(ws1), c1), (str(ws2), c2)]
            sigs = {str(c1): rp.dir_signature(c1), str(c2): rp.dir_signature(c2)}
            dirty = set()

            # ws1 receives a request and stays put; ws2 is mid-write this tick.
            (c1 / "review_request_A_r01.md").write_text("x", encoding="utf-8")
            rp.detect_settled(pairs, sigs, dirty)          # both now dirty
            (c2 / "review_request_A_r01.md").write_text("y", encoding="utf-8")
            settled = rp.detect_settled(pairs, sigs, dirty)  # ws1 settles, ws2 moves

            self.assertEqual(settled, [str(ws1)])
            self.assertIn(str(c2), dirty)
            # A fallback on this same tick sweeps only the settled/clean ws1;
            # ws2, still mid-write, is left for a later tick.
            self.assertEqual(rp.plan_sweep(pairs, settled, dirty, True), [str(ws1)])


if __name__ == "__main__":
    unittest.main()
