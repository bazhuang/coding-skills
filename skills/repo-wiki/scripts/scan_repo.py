#!/usr/bin/env python3
"""Scan a local repository and output file tree + README content as JSON.

Ported from deepwiki-open's /local_repo/structure endpoint.
No auth, no model config -- just filesystem scanning.

Usage:
    python3 scan_repo.py <repo_path> [--output <output.json>]

If --output is omitted, prints JSON to stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys


# Directories to always exclude
EXCLUDED_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", "node_modules", ".venv",
    "venv", ".idea", ".vscode", "dist", "build", ".next", "target",
    ".eggs", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
}

# File patterns to skip
EXCLUDED_FILE_SUFFIXES = (".pyc", ".pyo", ".class", ".o", ".so", ".dylib", ".dll", ".exe")
EXCLUDED_FILE_NAMES = {".DS_Store", "Thumbs.db", ".gitignore", ".gitkeep"}


def get_git_hash(repo_path: str) -> str:
    """Get the current git commit hash of the repo, or empty string if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of file content for change detection."""
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except Exception:
        pass
    return h.hexdigest()[:16]  # 16 chars is enough for change detection


def scan_repo(repo_path: str) -> dict:
    """Walk a repository directory and return file_tree, readme, git_hash, and file_hashes."""
    repo_path = os.path.abspath(repo_path)
    if not os.path.isdir(repo_path):
        print(f"Error: directory not found: {repo_path}", file=sys.stderr)
        sys.exit(1)

    file_tree_lines: list[str] = []
    file_hashes: dict[str, str] = {}
    readme_content = ""

    for root, dirs, files in os.walk(repo_path):
        # Filter directories in-place: only skip explicitly excluded dirs,
        # not all dot-prefixed dirs (e.g. .github, .config may contain
        # documentation-worthy content like CI/deploy configs).
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for file in sorted(files):
            if file in EXCLUDED_FILE_NAMES:
                continue
            if any(file.endswith(suffix) for suffix in EXCLUDED_FILE_SUFFIXES):
                continue
            # Skip empty __init__.py (package markers with no real content),
            # but keep non-empty ones since they often contain real exports/API.
            if file == "__init__.py":
                init_path = os.path.join(root, file)
                try:
                    with open(init_path, "r", encoding="utf-8", errors="replace") as f:
                        if not f.read().strip():
                            continue
                except Exception:
                    continue

            rel_dir = os.path.relpath(root, repo_path)
            rel_file = os.path.join(rel_dir, file) if rel_dir != "." else file
            file_tree_lines.append(rel_file)

            # Compute content hash for change detection (incremental update)
            abs_path = os.path.join(root, file)
            file_hashes[rel_file] = compute_file_hash(abs_path)

            # Find README (case-insensitive, first match)
            if file.lower().startswith("readme") and file.lower().endswith(".md") and not readme_content:
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        readme_content = f.read()
                except Exception:
                    pass

    file_tree_str = "\n".join(sorted(file_tree_lines))
    git_hash = get_git_hash(repo_path)

    return {
        "file_tree": file_tree_str,
        "readme": readme_content,
        "git_hash": git_hash,
        "file_hashes": file_hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan a local repo and output file tree + README as JSON")
    parser.add_argument("repo_path", help="Path to the repository root")
    parser.add_argument("--output", "-o", default=None, help="Output JSON file path (default: stdout)")
    args = parser.parse_args()

    result = scan_repo(args.repo_path)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
