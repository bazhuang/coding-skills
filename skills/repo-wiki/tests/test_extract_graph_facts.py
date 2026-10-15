#!/usr/bin/env python3
"""Focused unit tests for optional CBM fact extraction.

All CBM responses are inline mocks. No test application is maintained here.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

_SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS))

import extract_graph_facts as egf  # noqa: E402


def _completed(argv, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


class CbmMock:
    def __init__(self, repo: str, *, version="0.10.0", index_fails=False,
                 search_results=None):
        self.repo = repo
        self.version = version
        self.index_fails = index_fails
        self.search_results = search_results
        self.calls: list[list[str]] = []

    def calls_for(self, tool: str) -> list[list[str]]:
        return [c for c in self.calls if len(c) > 2 and c[1:3] == ["cli", tool]]

    def __call__(self, argv, **_kwargs):
        argv = list(argv)
        self.calls.append(argv)
        if "--version" in argv:
            return _completed(argv, stdout=f"codebase-memory-mcp {self.version}\n")
        tool = argv[2]
        if tool == "index_repository":
            if self.index_fails:
                return _completed(argv, returncode=1, stderr="daemon unavailable")
            return _completed(argv, stdout=json.dumps({
                "project": "indexed-project", "status": "indexed",
                "skipped_count": 0, "excluded": {"dirs": []},
            }))
        if tool == "get_architecture":
            return _completed(argv, stdout=json.dumps({
                "hotspots": [{
                    "qualified_name": "indexed-project.pkg.Service.work", "fan_in": 4,
                }],
            }))
        if tool == "search_graph":
            results = self.search_results
            if results is None:
                results = [{
                    "qualified_name": "indexed-project.pkg.Controller.handle",
                    "label": "Method",
                    "file_path": os.path.join(self.repo, "src", "Controller.java"),
                    "route_path": "/api/hello",
                    "route_method": "GET",
                }]
            return _completed(argv, stdout=json.dumps({"results": results}))
        if tool == "trace_path":
            return _completed(argv, stdout=json.dumps({
                "callees": [{
                    "qualified_name": "indexed-project.pkg.Service.work",
                    "name": "work", "hop": 1,
                }],
            }))
        if tool == "get_code_snippet":
            qn = argv[argv.index("--qualified-name") + 1]
            filename = "Controller.java" if ".Controller." in qn else "Service.java"
            line = 12 if filename == "Controller.java" else 8
            return _completed(argv, stdout=json.dumps({
                "file_path": os.path.join(self.repo, "src", filename),
                "start_line": line,
                "end_line": line + 2,
            }))
        return _completed(argv, returncode=1, stderr=f"unexpected tool: {tool}")


class ExtractGraphFactsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = os.path.join(self.temp.name, "repo")
        os.makedirs(self.repo)
        self.scan = self._write("scan.json", {
            "repo_path": self.repo,
            "git_commit": "abc123",
            "dirty": False,
        })
        self.api = self._write("api.json", {"entries": [{
            "type": "inbound_http",
            "file": "src/Controller.java",
            "line": 12,
            "framework": "spring",
            "method": "GET",
            "route": "/api/hello",
            "symbol": "Controller#GetMapping",
        }]})
        self.output = os.path.join(self.temp.name, "graph_facts.json")
        self.marker = os.path.join(self.temp.name, "marker.json")

    def _write(self, name: str, data: dict) -> str:
        path = os.path.join(self.temp.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        return path

    def _args(self, *extra: str) -> list[str]:
        return [
            "--repo", self.repo,
            "--scan", self.scan,
            "--api", self.api,
            "--output", self.output,
            "--marker", self.marker,
            *extra,
        ]

    def _result(self) -> dict:
        with open(self.output, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def test_user_disable_never_invokes_cbm(self):
        with mock.patch("shutil.which", side_effect=AssertionError("must not probe")), \
                mock.patch("subprocess.run", side_effect=AssertionError("must not run")):
            self.assertEqual(egf.main(self._args("--no-cbm")), 0)
        self.assertEqual(self._result(), {
            "available": False, "reason": "disabled_by_user", "facts": [],
        })

    def test_unavailable_and_old_version_degrade(self):
        with mock.patch("shutil.which", return_value=None):
            self.assertEqual(egf.main(self._args()), 0)
        self.assertEqual(self._result()["reason"], "not_installed")

        runner = CbmMock(self.repo, version="0.8.9")
        with mock.patch("shutil.which", return_value="cbm"), \
                mock.patch("subprocess.run", runner):
            self.assertEqual(egf.main(self._args()), 0)
        self.assertEqual(self._result()["reason"], "version_too_low")

    def test_non_object_json_is_rejected(self):
        with mock.patch("subprocess.run", return_value=_completed([], stdout="[]")):
            self.assertIsNone(egf.run_cbm(["get_architecture"], 1))

    def test_index_failure_is_non_blocking(self):
        runner = CbmMock(self.repo, index_fails=True)
        with mock.patch("shutil.which", return_value="cbm"), \
                mock.patch("subprocess.run", runner):
            self.assertEqual(egf.main(self._args()), 0)
        result = self._result()
        self.assertTrue(result["degraded"])
        self.assertEqual(result["reason"], "index_failed")
        self.assertEqual(result["facts"], [])

    def test_fresh_marker_skips_index(self):
        self._write("marker.json", {
            "project": "indexed-project",
            "requested_project": "repo",
            "commit": "abc123",
            "cbm_version": "0.10.0",
            "mode": "fast",
            "coverage": {},
        })
        runner = CbmMock(self.repo)
        with mock.patch("shutil.which", return_value="cbm"), \
                mock.patch("subprocess.run", runner):
            self.assertEqual(egf.main(self._args()), 0)
        self.assertFalse(self._result()["reindexed"])
        self.assertEqual(runner.calls_for("index_repository"), [])

    def test_mapping_annotation_resolves_handler_by_route(self):
        runner = CbmMock(self.repo)
        with mock.patch("shutil.which", return_value="cbm"), \
                mock.patch("subprocess.run", runner):
            self.assertEqual(egf.main(self._args()), 0)
        result = self._result()
        chains = [f for f in result["facts"] if f["category"] == "graph_call_chain"]
        self.assertEqual(len(chains), 1)
        self.assertEqual(
            chains[0]["value"]["entry_qualified_name"],
            "indexed-project.pkg.Controller.handle",
        )
        trace_argv = runner.calls_for("trace_path")[0]
        self.assertNotIn("GetMapping", trace_argv)
        search_argv = runner.calls_for("search_graph")[0]
        fields_index = search_argv.index("--fields")
        self.assertEqual(
            json.loads(search_argv[fields_index + 1]),
            ["route_path", "route_method"],
        )

    def test_ambiguous_route_is_not_guessed(self):
        candidates = []
        for method in ("first", "second"):
            candidates.append({
                "qualified_name": f"indexed-project.pkg.Controller.{method}",
                "label": "Method",
                "file_path": os.path.join(self.repo, "src", "Controller.java"),
                "route_path": "/api/hello",
                "route_method": "GET",
            })
        with mock.patch.object(egf, "run_cbm", return_value={"results": candidates}):
            self.assertIsNone(egf.search_handler_qn(
                "indexed-project", {"file": "src/Controller.java",
                "symbol": "Controller#GetMapping", "route": "/api/hello",
                "method": "GET"}, self.repo,
            ))

    def test_every_emitted_fact_has_source_line_evidence(self):
        runner = CbmMock(self.repo)
        with mock.patch("shutil.which", return_value="cbm"), \
                mock.patch("subprocess.run", runner):
            self.assertEqual(egf.main(self._args()), 0)
        facts = self._result()["facts"]
        self.assertTrue(facts)
        for fact in facts:
            self.assertTrue(egf.validate_fact(fact), fact)
            for evidence in fact["evidence"]:
                self.assertFalse(os.path.isabs(evidence["source"]))
                self.assertGreater(evidence["line"], 0)

    def test_entry_outside_repository_is_rejected(self):
        with open(self.api, "w", encoding="utf-8") as handle:
            json.dump({"entries": [{
                "type": "inbound_http",
                "file": os.path.join(self.temp.name, "outside", "Controller.java"),
                "line": 1,
                "symbol": "Controller#handle",
            }]}, handle)
        errors = []
        with open(self.api, "r", encoding="utf-8") as handle:
            api_data = json.load(handle)
        with mock.patch.object(egf, "run_cbm", side_effect=AssertionError("must not query")):
            facts = egf.extract_call_chains("project", api_data, 10, self.repo, errors)
        self.assertEqual(facts, [])
        self.assertEqual(errors[0]["reason"], "missing_entry_location")


class SkillFlowContractTest(unittest.TestCase):
    def test_extract_command_and_structure_placeholders_are_complete(self):
        skill_dir = os.path.abspath(os.path.join(_SCRIPTS, ".."))
        with open(os.path.join(skill_dir, "SKILL.md"), "r", encoding="utf-8") as handle:
            skill = handle.read()
        self.assertIn("extract_graph_facts.py --repo <仓库路径>", skill)

        with open(
            os.path.join(skill_dir, "references", "structure-prompt.md"),
            "r", encoding="utf-8",
        ) as handle:
            template = handle.read()
        placeholders = set(re.findall(r"\{[A-Z_]+\}", template))
        expected = {
            "{REPO_NAME}", "{FILE_TREE}", "{README}",
            "{API_ENTRIES}", "{MODULES}", "{FACTS_SUMMARY}",
        }
        self.assertEqual(placeholders, expected)
        for placeholder in expected:
            self.assertIn(placeholder, skill)
            template = template.replace(placeholder, "test-value")
        self.assertIsNone(re.search(r"\{[A-Z_]+\}", template))


if __name__ == "__main__":
    unittest.main()
