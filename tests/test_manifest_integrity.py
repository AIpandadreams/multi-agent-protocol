#!/usr/bin/env python3
"""Integrity gate for the two release manifests [PROTOCOL v2.6].

A release nearly shipped with a UTF-8 BOM prepended to both JSON manifests
(a Windows-PowerShell `Set-Content -Encoding utf8` artifact): `mirror_check`
was green and every other test passed, yet strict `JSON.parse` /
`json.loads(bytes.decode("utf-8"))` rejects `\\ufeff{`, so plugin/marketplace
discovery could fail on a "green" tree. No gate read the manifests as bytes.

This test closes that gap on the REAL committed files: they must be BOM-free,
strict-UTF-8 JSON, and carry the SAME version (the stale-manifest class that
shipped once already — a bump that lands in one manifest but not the other).
Stdlib unittest only, to match the repo's no-extra-dependency posture:

    python -m unittest discover -s tests
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFESTS = [
    ROOT / ".claude-plugin" / "marketplace.json",
    ROOT / "plugins" / "agent-protocol" / ".claude-plugin" / "plugin.json",
]
_BOM = b"\xef\xbb\xbf"


def _version(obj):
    """Version lives at the root in plugin.json, under metadata in marketplace.json."""
    if "version" in obj:
        return obj["version"]
    return obj.get("metadata", {}).get("version")


class ManifestIntegrityTest(unittest.TestCase):
    def test_manifests_exist(self):
        for m in MANIFESTS:
            self.assertTrue(m.is_file(), f"missing manifest: {m}")

    def test_no_utf8_bom(self):
        for m in MANIFESTS:
            head = m.read_bytes()[:3]
            self.assertNotEqual(
                head, _BOM,
                f"{m} starts with a UTF-8 BOM — strict JSON.parse will reject it")

    def test_strict_utf8_json_parses(self):
        # Decode as strict utf-8 (NOT utf-8-sig, which would silently eat a BOM),
        # exactly as a strict JSON consumer does.
        for m in MANIFESTS:
            text = m.read_bytes().decode("utf-8")
            self.assertFalse(
                text.startswith("﻿"),
                f"{m} decoded with a leading BOM code point")
            json.loads(text)  # raises on any parse defect

    def test_versions_match(self):
        versions = {}
        for m in MANIFESTS:
            obj = json.loads(m.read_bytes().decode("utf-8"))
            v = _version(obj)
            self.assertIsNotNone(v, f"{m} has no version field")
            versions[m.name] = v
        self.assertEqual(
            len(set(versions.values())), 1,
            f"manifest versions disagree: {versions}")


if __name__ == "__main__":
    unittest.main()
