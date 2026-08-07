#!/usr/bin/env python3
"""Unit tests for scan_repo.py — git-aware scanning, exclusions, sensitive files.

Run: python -m unittest skills.repo-wiki.tests.test_scan_repo
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

# Make the scripts directory importable
_SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS))

import scan_repo  # noqa: E402


def _git_init(path: str):
    """Initialize a git repo and configure a dummy commit author."""
    subprocess.run(["git", "init"], cwd=path, capture_output=True, timeout=10)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True)


def _git_commit(path: str, msg: str = "init"):
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True, timeout=10)
    subprocess.run(["git", "commit", "-m", msg], cwd=path, capture_output=True, timeout=10)


class TestScanRepoGitAware(unittest.TestCase):
    """P0-01: git-aware scanning and fallback."""

    def test_git_repo_uses_git_mode(self):
        """A git repo should report scan_mode='git' and populate branch/commit."""
        with tempfile.TemporaryDirectory() as d:
            _git_init(d)
            (open(os.path.join(d, "hello.py"), "w", encoding="utf-8").close())
            _git_commit(d)
            result = scan_repo.scan_repo(d)
            self.assertEqual(result["scan_mode"], "git")
            self.assertTrue(result["git_commit"])
            self.assertEqual(result["git_hash"], result["git_commit"])  # back-compat
            self.assertTrue(result["branch"])

    def test_non_git_falls_back_to_walk(self):
        """A non-git directory should use scan_mode='walk'."""
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "hello.py"), "w", encoding="utf-8").close()
            result = scan_repo.scan_repo(d)
            self.assertEqual(result["scan_mode"], "walk")
            self.assertFalse(result["git_commit"])
            self.assertFalse(result["dirty"])

    def test_dirty_flag(self):
        """Uncommitted changes should set dirty=True."""
        with tempfile.TemporaryDirectory() as d:
            _git_init(d)
            open(os.path.join(d, "a.py"), "w", encoding="utf-8").close()
            _git_commit(d)
            # Now make a change without committing
            with open(os.path.join(d, "a.py"), "w", encoding="utf-8") as f:
                f.write("x = 1\n")
            result = scan_repo.scan_repo(d)
            self.assertTrue(result["dirty"])


class TestScanRepoExclusions(unittest.TestCase):
    """P0-01: wiki output dirs, build caches, and sensitive files excluded."""

    def test_wiki_output_dir_excluded(self):
        """docs/wiki files must not appear in file_tree."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "docs", "wiki"))
            open(os.path.join(d, "README.md"), "w", encoding="utf-8").close()
            with open(os.path.join(d, "docs", "wiki", "generated.md"), "w", encoding="utf-8") as f:
                f.write("auto-generated")
            result = scan_repo.scan_repo(d)
            files = result["file_tree"].splitlines()
            self.assertIn("README.md", files)
            self.assertFalse(any("docs/wiki" in f for f in files))
            wiki_excl = [e for e in result["excluded_paths"] if e["reason"] == "wiki_output"]
            self.assertTrue(wiki_excl)

    def test_build_cache_excluded(self):
        """target/ and node_modules/ should be excluded."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "target", "classes"))
            os.makedirs(os.path.join(d, "node_modules", "lib"))
            open(os.path.join(d, "src.py"), "w", encoding="utf-8").close()
            open(os.path.join(d, "target", "classes", "App.class"), "w", encoding="utf-8").close()
            open(os.path.join(d, "node_modules", "lib", "index.js"), "w", encoding="utf-8").close()
            result = scan_repo.scan_repo(d)
            files = result["file_tree"].splitlines()
            self.assertFalse(any("target/" in f for f in files))
            self.assertFalse(any("node_modules/" in f for f in files))

    def test_sensitive_files_excluded_and_counted(self):
        """.env and key files must not enter file_hashes and must be counted."""
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "app.py"), "w", encoding="utf-8").close()
            open(os.path.join(d, ".env"), "w", encoding="utf-8").close()
            open(os.path.join(d, "private.key"), "w", encoding="utf-8").close()
            result = scan_repo.scan_repo(d)
            files = result["file_tree"].splitlines()
            self.assertIn("app.py", files)
            self.assertNotIn(".env", files)
            self.assertNotIn("private.key", files)
            self.assertEqual(result["sensitive_file_count"], 2)
            # Sensitive content must not appear in file_hashes
            self.assertNotIn(".env", result["file_hashes"])
            self.assertNotIn("private.key", result["file_hashes"])

    def test_allow_dir_overrides_exclusion(self):
        """--allow-dir should re-include a wiki output dir."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "docs", "wiki"))
            with open(os.path.join(d, "docs", "wiki", "page.md"), "w", encoding="utf-8") as f:
                f.write("manual content")
            result = scan_repo.scan_repo(d, allow_dirs=["docs/wiki"])
            files = result["file_tree"].splitlines()
            self.assertTrue(any("docs/wiki/page.md" in f for f in files))


class TestScanRepoMetadata(unittest.TestCase):
    """P0-05: repo_path field present (previously missing)."""

    def test_repo_path_present(self):
        with tempfile.TemporaryDirectory() as d:
            result = scan_repo.scan_repo(d)
            self.assertTrue(result["repo_path"])
            self.assertEqual(os.path.abspath(result["repo_path"]), os.path.abspath(d))

    def test_file_hashes_deterministic(self):
        """Same file content → same hash."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "a.py"), "w", encoding="utf-8") as f:
                f.write("hello\n")
            r1 = scan_repo.scan_repo(d)
            r2 = scan_repo.scan_repo(d)
            self.assertEqual(r1["file_hashes"]["a.py"], r2["file_hashes"]["a.py"])

    def test_readme_deterministic_priority(self):
        """README.md should be chosen over readme.txt by priority."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as f:
                f.write("# Markdown README")
            with open(os.path.join(d, "readme.txt"), "w", encoding="utf-8") as f:
                f.write("Text readme")
            result = scan_repo.scan_repo(d)
            self.assertIn("Markdown README", result["readme"])
            self.assertNotIn("Text readme", result["readme"])


if __name__ == "__main__":
    unittest.main()
