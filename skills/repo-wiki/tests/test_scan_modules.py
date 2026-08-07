#!/usr/bin/env python3
"""Unit tests for scan_modules.py — depends_on, runtime_role, deployable,
placeholder, entry points, source/test counts.

Run: python -m unittest skills.repo-wiki.tests.test_scan_modules
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

_SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS))

import scan_modules as sm  # noqa: E402


def _scan(files: dict[str, str], **kwargs) -> dict:
    """Create a temp repo with the given {rel_path: content} and scan modules."""
    with tempfile.TemporaryDirectory() as d:
        for rel, content in files.items():
            full = os.path.join(d, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)
        return sm.scan_modules(d, **kwargs)


def _module_by_title(result: dict, title: str) -> dict | None:
    for m in result.get("modules", []):
        if m["title"] == title:
            return m
    return None


class TestMavenDependsOn(unittest.TestCase):
    """P0-04: Maven module dependencies must be populated, not empty."""

    def test_maven_multimodule_depends_on(self):
        """web module depends on lib via <dependency>."""
        result = _scan({
            "pom.xml": """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>parent</artifactId>
  <version>1.0</version>
  <packaging>pom</packaging>
  <modules>
    <module>web</module>
    <module>lib</module>
  </modules>
</project>""",
            "web/pom.xml": """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>com.example</groupId>
    <artifactId>parent</artifactId>
    <version>1.0</version>
  </parent>
  <artifactId>web</artifactId>
  <packaging>jar</packaging>
  <dependencies>
    <dependency>
      <groupId>com.example</groupId>
      <artifactId>lib</artifactId>
      <version>1.0</version>
    </dependency>
  </dependencies>
</project>""",
            "web/src/main/java/com/example/App.java": "package com.example; public class App {}",
            "lib/pom.xml": """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>com.example</groupId>
    <artifactId>parent</artifactId>
    <version>1.0</version>
  </parent>
  <artifactId>lib</artifactId>
  <packaging>jar</packaging>
</project>""",
            "lib/src/main/java/com/example/Util.java": "package com.example; public class Util {}",
        })
        self.assertTrue(result["multi_module"])
        web = _module_by_title(result, "web")
        lib = _module_by_title(result, "lib")
        self.assertIsNotNone(web, "web module not found")
        self.assertIsNotNone(lib, "lib module not found")
        # web should depend on lib
        self.assertTrue(web["depends_on"],
                        f"web depends_on is empty: {web}")
        self.assertTrue(any("lib" in d for d in web["depends_on"]),
                        f"web does not depend on lib: {web['depends_on']}")
        # lib should have no deps
        self.assertEqual(lib["depends_on"], [],
                         f"lib should have no deps: {lib['depends_on']}")


class TestRuntimeRole(unittest.TestCase):
    """P0-04: runtime_role + is_deployable + is_placeholder."""

    def test_aggregator_pom_not_deployable(self):
        """A <packaging>pom</packaging> parent must be aggregator, not deployable."""
        result = _scan({
            "pom.xml": """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <artifactId>parent</artifactId>
  <packaging>pom</packaging>
  <modules><module>child</module></modules>
</project>""",
            "child/pom.xml": """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent><groupId>g</groupId><artifactId>parent</artifactId><version>1</version></parent>
  <artifactId>child</artifactId>
  <packaging>jar</packaging>
</project>""",
            "child/src/main/java/App.java": "public class App {}",
        })
        parent = _module_by_title(result, "parent")
        self.assertIsNotNone(parent)
        self.assertEqual(parent["runtime_role"], "aggregator")
        self.assertFalse(parent["is_deployable"])

    def test_spring_boot_module_is_service(self):
        """A module with spring-boot-maven-plugin should be service + deployable."""
        result = _scan({
            "pom.xml": """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <artifactId>parent</artifactId>
  <packaging>pom</packaging>
  <modules><module>server</module></modules>
</project>""",
            "server/pom.xml": """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent><groupId>g</groupId><artifactId>parent</artifactId><version>1</version></parent>
  <artifactId>server</artifactId>
  <packaging>jar</packaging>
  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>""",
            "server/src/main/java/com/example/Application.java":
                "package com.example;\n"
                "import org.springframework.boot.SpringApplication;\n"
                "import org.springframework.boot.autoconfigure.SpringBootApplication;\n"
                "@SpringBootApplication\n"
                "public class Application {\n"
                "    public static void main(String[] args) {}\n"
                "}",
        })
        server = _module_by_title(result, "server")
        self.assertIsNotNone(server)
        self.assertEqual(server["runtime_role"], "service")
        self.assertTrue(server["is_deployable"])
        self.assertTrue(server["entry_points"],
                        f"No entry points detected: {server['entry_points']}")

    def test_placeholder_module_detected(self):
        """A module with no source files should be is_placeholder=True."""
        result = _scan({
            "pom.xml": """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <artifactId>parent</artifactId>
  <packaging>pom</packaging>
  <modules><module>empty</module></modules>
</project>""",
            "empty/pom.xml": """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent><groupId>g</groupId><artifactId>parent</artifactId><version>1</version></parent>
  <artifactId>empty</artifactId>
  <packaging>jar</packaging>
</project>""",
        })
        empty = _module_by_title(result, "empty")
        self.assertIsNotNone(empty)
        self.assertTrue(empty["is_placeholder"],
                        f"empty module should be placeholder: {empty}")

    def test_source_test_counts(self):
        """Source and test file counts should be correct."""
        result = _scan({
            "pom.xml": """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <artifactId>parent</artifactId>
  <packaging>pom</packaging>
  <modules><module>mod</module></modules>
</project>""",
            "mod/pom.xml": """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent><groupId>g</groupId><artifactId>parent</artifactId><version>1</version></parent>
  <artifactId>mod</artifactId>
</project>""",
            "mod/src/main/java/A.java": "public class A {}",
            "mod/src/main/java/B.java": "public class B {}",
            "mod/src/test/java/ATest.java": "public class ATest {}",
        })
        mod = _module_by_title(result, "mod")
        self.assertIsNotNone(mod)
        self.assertEqual(mod["source_file_count"], 2)
        self.assertEqual(mod["test_file_count"], 1)


class TestNpmWorkspaces(unittest.TestCase):
    """P0-04: npm workspaces depends_on from package.json dependencies."""

    def test_npm_workspace_depends_on(self):
        result = _scan({
            "package.json": json.dumps({
                "name": "monorepo",
                "private": True,
                "workspaces": ["packages/*"],
            }),
            "packages/a/package.json": json.dumps({
                "name": "@scope/a",
                "version": "1.0.0",
                "dependencies": {"@scope/b": "1.0.0"},
            }),
            "packages/a/index.js": "module.exports = {};",
            "packages/b/package.json": json.dumps({
                "name": "@scope/b",
                "version": "1.0.0",
            }),
            "packages/b/index.js": "module.exports = {};",
        })
        self.assertTrue(result["multi_module"])
        a_mod = _module_by_title(result, "a")
        self.assertIsNotNone(a_mod)
        self.assertTrue(any("b" in d for d in a_mod["depends_on"]),
                        f"a does not depend on b: {a_mod['depends_on']}")


class TestModuleIdStability(unittest.TestCase):
    """Module IDs must be deterministic across runs."""

    def test_id_stability(self):
        """Module ID suffixes (after root) must be deterministic across runs."""
        files = {
            "pom.xml": """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <artifactId>root</artifactId>
  <packaging>pom</packaging>
  <modules><module>core</module></modules>
</project>""",
            "core/pom.xml": """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent><groupId>g</groupId><artifactId>root</artifactId><version>1</version></parent>
  <artifactId>core</artifactId>
</project>""",
            "core/src/main/java/A.java": "public class A {}",
        }
        r1 = _scan(files)
        r2 = _scan(files)
        # Compare suffixes (strip the root tempdir name) — the structure
        # (root + /core) must be the same even though tempdir names differ.
        def _suffixes(result):
            root_id = result["modules"][0]["id"] if result["modules"] else ""
            return sorted(m["id"].replace(root_id, "") for m in result["modules"])
        self.assertEqual(_suffixes(r1), _suffixes(r2),
                         "Module ID structure not stable across runs")


if __name__ == "__main__":
    unittest.main()
