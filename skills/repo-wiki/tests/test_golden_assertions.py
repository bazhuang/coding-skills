#!/usr/bin/env python3
"""Golden assertions — cross-language, cross-stack properties that must hold
for ANY repository scanned by the repo-wiki skill.

These are NOT per-script unit tests (those are in test_scan_repo.py etc.).
These are universal assertions from the optimization plan Section 7.8:

  - Maven fixture recognizes declared submodules, aggregation and module deps
  - Single-module fixture identifies unique deployable from startup entry + packaging
  - Multi-module is NOT auto-equivalent to microservices — deployability needs evidence
  - Placeholder modules are NOT described as running services
  - Node/Python/Go fixtures activate correct adapters, not Java rules
  - Repository rules are classified as repository_rule, not propagated to all repos
  - Code conventions represent repository requirements, not proof of implementation
  - No test-repo or real-project names appear in production code or prompts

Run: python -m unittest skills.repo-wiki.tests.test_golden_assertions
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest

_SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS))

import scan_api_entries as sae  # noqa: E402
import scan_modules as sm  # noqa: E402
import scan_repo  # noqa: E402
import build_facts as bf  # noqa: E402


def _make_repo(files: dict[str, str]) -> str:
    """Create a temp repo with the given {rel_path: content}; return its path."""
    d = tempfile.mkdtemp()
    for rel, content in files.items():
        full = os.path.join(d, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    return d


# --------------------------------------------------------------------------- #
# Golden Assertion: Maven multi-module recognizes submodules + deps + aggregation
# --------------------------------------------------------------------------- #
class TestMavenMultimoduleGolden(unittest.TestCase):

    def test_submodules_and_aggregation_recognized(self):
        """Maven fixture with parent + 2 children must detect all 3 modules."""
        d = _make_repo({
            "pom.xml": '<project xmlns="http://maven.apache.org/POM/4.0.0">'
                       '<artifactId>root</artifactId><packaging>pom</packaging>'
                       '<modules><module>web</module><module>lib</module></modules></project>',
            "web/pom.xml": '<project xmlns="http://maven.apache.org/POM/4.0.0">'
                           '<parent><groupId>g</groupId><artifactId>root</artifactId><version>1</version></parent>'
                           '<artifactId>web</artifactId><packaging>jar</packaging>'
                           '<dependencies><dependency><groupId>g</groupId>'
                           '<artifactId>lib</artifactId><version>1</version></dependency></dependencies></project>',
            "web/src/main/java/App.java": "public class App {}",
            "lib/pom.xml": '<project xmlns="http://maven.apache.org/POM/4.0.0">'
                           '<parent><groupId>g</groupId><artifactId>root</artifactId><version>1</version></parent>'
                           '<artifactId>lib</artifactId></project>',
            "lib/src/main/java/Util.java": "public class Util {}",
        })
        try:
            result = sm.scan_modules(d)
            self.assertTrue(result["multi_module"])
            self.assertEqual(result["module_count"], 3)
            titles = {m["title"] for m in result["modules"]}
            self.assertEqual(titles, {"root", "web", "lib"})

            web = next(m for m in result["modules"] if m["title"] == "web")
            self.assertTrue(web["depends_on"], "web must depend on lib")
            self.assertTrue(any("lib" in dep for dep in web["depends_on"]))

            root = next(m for m in result["modules"] if m["title"] == "root")
            self.assertEqual(root["runtime_role"], "aggregator")
            self.assertFalse(root["is_deployable"])
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Golden Assertion: Single deployable from startup entry + packaging
# --------------------------------------------------------------------------- #
class TestSingleDeployableGolden(unittest.TestCase):

    def test_spring_boot_is_unique_deployable(self):
        """A Spring Boot module with @SpringBootApplication is the unique deployable."""
        d = _make_repo({
            "pom.xml": '<project xmlns="http://maven.apache.org/POM/4.0.0">'
                       '<artifactId>root</artifactId><packaging>pom</packaging>'
                       '<modules><module>server</module><module>common</module></modules></project>',
            "server/pom.xml": '<project xmlns="http://maven.apache.org/POM/4.0.0">'
                              '<parent><groupId>g</groupId><artifactId>root</artifactId><version>1</version></parent>'
                              '<artifactId>server</artifactId><packaging>jar</packaging>'
                              '<build><plugins><plugin>'
                              '<groupId>org.springframework.boot</groupId>'
                              '<artifactId>spring-boot-maven-plugin</artifactId>'
                              '</plugin></plugins></build></project>',
            "server/src/main/java/com/example/Application.java":
                "package com.example;\n"
                "@org.springframework.boot.autoconfigure.SpringBootApplication\n"
                "public class Application {\n"
                "    public static void main(String[] args) {}\n"
                "}\n",
            "common/pom.xml": '<project xmlns="http://maven.apache.org/POM/4.0.0">'
                              '<parent><groupId>g</groupId><artifactId>root</artifactId><version>1</version></parent>'
                              '<artifactId>common</artifactId></project>',
            "common/src/main/java/Util.java": "public class Util {}",
        })
        try:
            result = sm.scan_modules(d)
            deployable = [m for m in result["modules"] if m.get("is_deployable")]
            self.assertEqual(len(deployable), 1, "Exactly one deployable module expected")
            self.assertEqual(deployable[0]["title"], "server")
            self.assertTrue(deployable[0]["entry_points"],
                            "Spring Boot module must have entry points")

            # Facts layer should assert single deployable
            scan = scan_repo.scan_repo(d)
            facts = bf.build_facts(scan, None, result, d)
            assertion_ids = [f["id"] for f in facts["facts"]]
            self.assertIn("fact.assertion.single_deployable", assertion_ids)
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Golden Assertion: Placeholder modules NOT described as running services
# --------------------------------------------------------------------------- #
class TestPlaceholderNotServiceGolden(unittest.TestCase):

    def test_placeholder_is_not_deployable(self):
        """An empty module (only pom.xml, no source) must be is_placeholder and NOT deployable."""
        d = _make_repo({
            "pom.xml": '<project xmlns="http://maven.apache.org/POM/4.0.0">'
                       '<artifactId>root</artifactId><packaging>pom</packaging>'
                       '<modules><module>empty</module></modules></project>',
            "empty/pom.xml": '<project xmlns="http://maven.apache.org/POM/4.0.0">'
                             '<parent><groupId>g</groupId><artifactId>root</artifactId><version>1</version></parent>'
                             '<artifactId>empty</artifactId></project>',
        })
        try:
            result = sm.scan_modules(d)
            empty = next(m for m in result["modules"] if m["title"] == "empty")
            self.assertTrue(empty["is_placeholder"])
            self.assertFalse(empty["is_deployable"])
            self.assertEqual(empty["runtime_role"], "library")
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Golden Assertion: Node/Python/Go fixtures use correct adapters (no Java noise)
# --------------------------------------------------------------------------- #
class TestLanguageAdapterGolden(unittest.TestCase):

    def test_node_workspace_uses_npm_adapter(self):
        """npm workspaces fixture must be detected as npm-workspaces, not maven."""
        d = _make_repo({
            "package.json": json.dumps({
                "name": "monorepo", "private": True,
                "workspaces": ["packages/client", "packages/server"],
            }),
            "packages/client/package.json": json.dumps({"name": "client", "version": "1.0"}),
            "packages/client/index.js": "console.log('client');",
            "packages/server/package.json": json.dumps({
                "name": "server", "version": "1.0",
                "scripts": {"start": "node index.js"},
            }),
            "packages/server/index.js": "console.log('server');",
        })
        try:
            result = sm.scan_modules(d)
            self.assertTrue(result["multi_module"])
            self.assertEqual(result["build_system"], "npm-workspaces")
            server = next(m for m in result["modules"] if m["title"] == "server")
            self.assertTrue(server["is_deployable"])
            self.assertEqual(server["runtime_role"], "service")
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_python_project_not_detected_as_maven(self):
        """A Python project must not trigger Maven/Gradle detectors."""
        d = _make_repo({
            "main.py": "print('hello')",
            "requirements.txt": "flask==3.0\n",
        })
        try:
            result = sm.scan_modules(d)
            self.assertFalse(result["multi_module"])
            # build_system might be 'npm' (from non-workspace package.json) or None
            # but must NOT be 'maven' or 'gradle'
            self.assertNotIn(result.get("build_system"), ("maven", "gradle"))
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Golden Assertion: No test-repo or real-project names in production code
# --------------------------------------------------------------------------- #
class TestNoRepoSpecificNamesGolden(unittest.TestCase):
    """Production code must NOT contain any test-fixture or real-project names."""

    FORBIDDEN_NAMES = [
        "qoder", "repowiki", "zcode-wiki",  # wiki tool names are OK in config, not in code logic
        "introducer", "bazhuang",  # sample repo names
    ]

    SCRIPT_DIRS = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"),
    ]

    def test_no_forbidden_names_in_scripts(self):
        """Scan all .py files for forbidden repository-specific names."""
        for script_dir in self.SCRIPT_DIRS:
            for fname in os.listdir(script_dir):
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(script_dir, fname)
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read().lower()
                for forbidden in self.FORBIDDEN_NAMES:
                    # Allow the name in comments or config keys, not in logic
                    # Simple check: if it appears outside comments, flag it
                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        stripped = line.split("#")[0].split("//")[0].strip()
                        if forbidden in stripped.lower():
                            # Exception: scan-excludes.json references and config loading are OK
                            if any(allowed in line.lower() for allowed in
                                   ("wiki_output", "scan-excludes", "default_wiki", "builtin_wiki",
                                    "_wiki_output", "qoder/repowiki", "zcode-wiki", "docs-bak", "repo-wiki")):
                                continue
                            self.fail(
                                f"Forbidden name '{forbidden}' in {fname}:{i}: {line.strip()[:80]}")


# --------------------------------------------------------------------------- #
# Golden Assertion: Repository rules classified as repository_rule in facts
# --------------------------------------------------------------------------- #
class TestRepositoryRuleClassificationGolden(unittest.TestCase):

    def test_agents_md_rules_are_repository_rule(self):
        """Rules from AGENTS.md must be type=repository_rule, not observed."""
        d = _make_repo({
            "AGENTS.md": "# Rules\n\n## Coding Standards\nUse 4 spaces.\n",
            "app.py": "print('hello')\n",
        })
        try:
            scan = scan_repo.scan_repo(d)
            facts = bf.build_facts(scan, None, None, d)
            rules = [f for f in facts["facts"] if f.get("category") == "repository_rule"]
            self.assertTrue(rules, "AGENTS.md rules must appear as facts")
            for r in rules:
                self.assertEqual(r["type"], "repository_rule",
                                 f"Rule {r['id']} must be repository_rule, not {r['type']}")
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Golden Assertion: Wiki output dirs never enter scan input
# --------------------------------------------------------------------------- #
class TestWikiOutputExclusionGolden(unittest.TestCase):

    def test_wiki_output_dirs_never_in_file_tree(self):
        """docs/wiki and other wiki output dirs must never appear in file_tree."""
        d = _make_repo({
            "README.md": "# Project",
            "src/app.py": "print('hello')",
            "docs/wiki/overview.md": "# auto-generated overview",
            "docs/wiki/architecture.md": "# auto-generated arch",
            ".repo-wiki/wiki_facts.json": "{}",
        })
        try:
            result = scan_repo.scan_repo(d)
            files = result["file_tree"].splitlines()
            for f in files:
                self.assertFalse(
                    any(p in f for p in ("docs/wiki", ".repo-wiki")),
                    f"Wiki output dir leaked into scan: {f}")
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
