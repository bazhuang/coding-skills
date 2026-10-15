#!/usr/bin/env python3
"""Focused tests for optional CBM provenance in meta.yaml."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

_SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS))

import export_wiki as ew  # noqa: E402


class CbmMetaTest(unittest.TestCase):
    def _render(self, cbm_commit="", cbm_version="") -> str:
        structure = {"pages": [], "sections": []}
        with tempfile.TemporaryDirectory() as output:
            ew.generate_meta_yaml(
                structure, {}, None, output,
                facts_hash="facts-1",
                cbm_commit=cbm_commit,
                cbm_version=cbm_version,
            )
            with open(os.path.join(output, "meta.yaml"), "r", encoding="utf-8") as handle:
                return handle.read()

    def test_cbm_fields_are_written_when_graph_facts_were_merged(self):
        meta = self._render("abc123", "0.10.0")
        self.assertIn('  cbm_commit: "abc123"', meta)
        self.assertIn('  cbm_version: "0.10.0"', meta)

    def test_cbm_fields_are_omitted_for_baseline_run(self):
        meta = self._render()
        self.assertNotIn("cbm_commit", meta)
        self.assertNotIn("cbm_version", meta)


if __name__ == "__main__":
    unittest.main()
