#!/usr/bin/env python3
"""Unit tests for build_facts.py — unified facts layer.

Run: python -m unittest skills.repo-wiki.tests.test_build_facts
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

_SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS))

import build_facts as bf  # noqa: E402


class TestBuildFactsBasics(unittest.TestCase):
    """P0-3: facts layer produces stable IDs, types, evidence."""

    def test_minimal_scan_produces_facts(self):
        """Even with just scan_data, should produce at least scan_mode assertion."""
        scan = {
            "repo_path": "/test",
            "branch": "main",
            "git_commit": "abc123",
            "dirty": False,
            "scan_mode": "git",
            "file_tree": "README.md\nsrc/main.py",
        }
        result = bf.build_facts(scan, None, None, "/test")
        self.assertEqual(result["schema_version"], 1)
        self.assertTrue(result["facts"])
        self.assertTrue(result["facts_hash"])
        self.assertEqual(result["repository"]["path"], "/test")
        self.assertEqual(result["repository"]["branch"], "main")
        self.assertIn("scan_mode", str([f["id"] for f in result["facts"]]))

    def test_module_facts_generated(self):
        """Module depends_on, runtime_role, is_deployable should become facts."""
        scan = {"repo_path": "/test", "scan_mode": "git", "file_tree": ""}
        modules = {
            "multi_module": True,
            "build_system": "maven",
            "module_count": 3,
            "leaf_count": 2,
            "modules": [
                {"id": "web", "title": "web", "type": "leaf",
                 "depends_on": ["lib"], "dep_evidence": [{"from": "web", "to": "lib", "signal": "maven"}],
                 "runtime_role": "service", "is_deployable": True,
                 "is_placeholder": False, "entry_points": ["com.example.App"],
                 "build_evidence": ["spring-boot-maven-plugin"],
                 "source_file_count": 5, "test_file_count": 2},
                {"id": "lib", "title": "lib", "type": "leaf",
                 "depends_on": [], "runtime_role": "library", "is_deployable": False,
                 "is_placeholder": False, "entry_points": [],
                 "build_evidence": [], "source_file_count": 3, "test_file_count": 1},
            ],
        }
        result = bf.build_facts(scan, None, modules, "/test")
        fact_ids = [f["id"] for f in result["facts"]]
        self.assertIn("fact.module.web.depends_on", fact_ids)
        self.assertIn("fact.module.web.runtime_role", fact_ids)
        self.assertIn("fact.module.web.is_deployable", fact_ids)
        self.assertIn("fact.module.lib.runtime_role", fact_ids)
        self.assertNotIn("fact.module.lib.is_deployable", fact_ids)
        # Assertion: single deployable
        self.assertIn("fact.assertion.single_deployable", fact_ids)

    def test_endpoint_facts_generated(self):
        """API entries should become endpoint facts with type classification."""
        scan = {"repo_path": "/test", "scan_mode": "git", "file_tree": ""}
        api = {
            "entries": [
                {"type": "inbound_http", "file": "Ctrl.java", "line": 10,
                 "framework": "spring", "method": "GET", "route": "/api/users",
                 "symbol": "Ctrl#getUsers"},
                {"type": "outbound_http_client", "file": "Client.java", "line": 5,
                 "framework": "spring-feign"},
                {"type": "scheduled_job", "file": "Job.java", "line": 20,
                 "framework": "spring-scheduled", "cron": "0 0 * * *"},
            ],
            "summary": {"by_type": {"inbound_http": 1, "outbound_http_client": 1, "scheduled_job": 1}},
        }
        result = bf.build_facts(scan, api, None, "/test")
        endpoint_facts = [f for f in result["facts"] if f["category"].startswith("endpoint_")]
        self.assertEqual(len(endpoint_facts), 3)
        types = set(f["value"]["type"] for f in endpoint_facts)
        self.assertEqual(types, {"inbound_http", "outbound_http_client", "scheduled_job"})

    def test_repository_rules_extracted(self):
        """AGENTS.md headings should become repository_rule facts."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "AGENTS.md"), "w", encoding="utf-8") as f:
                f.write("# Project Rules\n\n## Coding Standards\nUse 4 spaces.\n\n## Module Boundaries\nCross-module calls via facade.\n")
            scan = {"repo_path": d, "scan_mode": "walk", "file_tree": "AGENTS.md\nsrc/main.py"}
            result = bf.build_facts(scan, None, None, d)
            rules = [f for f in result["facts"] if f["type"] == "repository_rule"]
            self.assertTrue(rules, "No repository rules extracted from AGENTS.md")
            self.assertTrue(any("Standards" in r["value"] or "Boundaries" in r["value"] for r in rules))

    def test_facts_hash_deterministic(self):
        """Same inputs → same facts_hash."""
        scan = {"repo_path": "/test", "scan_mode": "git", "file_tree": "a.py"}
        r1 = bf.build_facts(scan, None, None, "/test")
        r2 = bf.build_facts(scan, None, None, "/test")
        self.assertEqual(r1["facts_hash"], r2["facts_hash"])

    def test_facts_hash_changes_with_different_input(self):
        """Different module data → different facts_hash."""
        scan = {"repo_path": "/test", "scan_mode": "git", "file_tree": ""}
        r1 = bf.build_facts(scan, None, None, "/test")
        modules = {"modules": [{"id": "x", "title": "x", "type": "leaf",
                                "is_deployable": True, "build_evidence": ["test"],
                                "runtime_role": "service", "depends_on": [],
                                "is_placeholder": False, "entry_points": [],
                                "source_file_count": 1, "test_file_count": 0}]}
        r2 = bf.build_facts(scan, None, modules, "/test")
        self.assertNotEqual(r1["facts_hash"], r2["facts_hash"])

    def test_conflict_detection(self):
        """Two facts with same ID but different values should appear in conflicts."""
        # This is hard to trigger through normal build_facts since IDs are unique
        # by construction. Test the helper directly.
        facts = [
            {"id": "fact.x", "type": "observed", "value": "A", "evidence": []},
            {"id": "fact.x", "type": "observed", "value": "B", "evidence": []},
        ]
        conflicts = bf._detect_conflicts(facts)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["fact_id"], "fact.x")

    def test_summary_counts(self):
        scan = {"repo_path": "/test", "scan_mode": "git", "file_tree": ""}
        modules = {"multi_module": True, "build_system": "maven", "modules": [
            {"id": "a", "title": "a", "type": "leaf", "is_deployable": True,
             "runtime_role": "service", "build_evidence": ["x"],
             "depends_on": [], "is_placeholder": False, "entry_points": [],
             "source_file_count": 1, "test_file_count": 0}]}
        result = bf.build_facts(scan, None, modules, "/test")
        self.assertEqual(result["summary"]["total_facts"], len(result["facts"]))
        self.assertIn("observed", result["summary"]["by_type"])
        self.assertEqual(result["summary"]["conflicts"], 0)


class TestOptionalGraphFacts(unittest.TestCase):
    def setUp(self):
        self.scan = {
            "repo_path": "/test",
            "scan_mode": "git",
            "git_commit": "abc123",
            "file_tree": "src/Service.java",
        }

    @staticmethod
    def _graph_fact(fact_id="fact.graph.hotspot.service", value=None):
        return {
            "id": fact_id,
            "type": "observed",
            "category": "graph_hotspot",
            "value": value if value is not None else {"qualified_name": "pkg.Service.work"},
            "evidence": [{
                "source": "src/Service.java",
                "signal": "cbm get_code_snippet",
                "line": 8,
            }],
            "confidence": 0.9,
            "source": "graph",
        }

    def test_valid_graph_fact_is_merged_with_provenance(self):
        graph = {
            "available": True,
            "degraded": False,
            "cbm_version": "0.10.0",
            "marker": {"commit": "abc123"},
            "facts": [self._graph_fact()],
        }
        result = bf.build_facts(self.scan, None, None, "/test", graph)
        self.assertIn("fact.graph.hotspot.service", [f["id"] for f in result["facts"]])
        self.assertEqual(result["graph"], {
            "cbm_commit": "abc123", "cbm_version": "0.10.0",
        })
        self.assertEqual(result["summary"]["graph_facts"], 1)

    def test_unavailable_graph_keeps_baseline_identical(self):
        baseline = bf.build_facts(self.scan, None, None, "/test")
        unavailable = bf.build_facts(
            self.scan, None, None, "/test",
            {"available": False, "reason": "not_installed", "facts": []},
        )
        self.assertEqual(unavailable, baseline)

    def test_graph_fact_without_line_is_ignored(self):
        invalid = self._graph_fact()
        del invalid["evidence"][0]["line"]
        result = bf.build_facts(self.scan, None, None, "/test", {
            "available": True, "degraded": False, "facts": [invalid],
        })
        self.assertNotIn("graph", result)
        self.assertNotIn(invalid["id"], [f["id"] for f in result["facts"]])

    def test_graph_fact_with_non_relative_source_is_ignored(self):
        for source in ("C:/outside/Service.java", "../Service.java"):
            with self.subTest(source=source):
                invalid = self._graph_fact()
                invalid["evidence"][0]["source"] = source
                result = bf.build_facts(self.scan, None, None, "/test", {
                    "available": True, "degraded": False, "facts": [invalid],
                })
                self.assertNotIn("graph", result)
                self.assertNotIn(invalid["id"], [f["id"] for f in result["facts"]])

    def test_conflicting_graph_value_uses_existing_conflict_detector(self):
        baseline = bf.build_facts(self.scan, None, None, "/test")
        existing = baseline["facts"][0]
        graph_fact = self._graph_fact(existing["id"], {"different": True})
        result = bf.build_facts(self.scan, None, None, "/test", {
            "available": True, "degraded": False, "facts": [graph_fact],
        })
        self.assertIn(existing["id"], [c["fact_id"] for c in result["conflicts"]])


if __name__ == "__main__":
    unittest.main()
