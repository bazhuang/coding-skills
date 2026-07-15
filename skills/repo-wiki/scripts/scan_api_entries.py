#!/usr/bin/env python3
"""Scan a repository for API entry points (controllers, routes, handlers).

Uses grep-style pattern matching to identify API endpoints across
common frameworks. Output is JSON with file paths, HTTP methods,
route paths, and line numbers.

Usage:
    python3 scan_api_entries.py <repo_path> [--output <output.json>]

If --output is omitted, prints JSON to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

# Directories to skip
EXCLUDED_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", "node_modules", ".venv",
    "venv", ".idea", ".vscode", "dist", "build", ".next", "target",
    ".eggs", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
}

# File extensions to scan
SCAN_EXTENSIONS = (".py", ".java", ".ts", ".js", ".go", ".cs", ".kt", ".scala", ".rb")

# API entry patterns by framework.
# Each tuple: (regex, framework_name, method_group_idx_or_special, route_group_idx_or_None)
# method_group: int for capture group, "mapping" for Spring annotation, "method" for .NET, None for class
PATTERNS = [
    # Java / Spring - controller class
    (r'@(?:Rest)?Controller\b', "spring-controller", None, None),
    # Java / Spring - endpoint with path
    (r'@(?:Request|Get|Post|Put|Delete|Patch)Mapping\s*\((?:value\s*=\s*)?["\']([^"\']+)["\']', "spring", "mapping", 1),
    # Java / Spring - endpoint without explicit path
    (r'@(?:Get|Post|Put|Delete|Patch)Mapping', "spring-method", "mapping", None),
    # Python / FastAPI / Flask - endpoint with path
    (r'@(?:app|router|api)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', "fastapi", 1, 2),
    # Python / FastAPI - endpoint without explicit path
    (r'@(?:app|router|api)\.(get|post|put|delete|patch)\s*\(', "fastapi", 1, None),
    # Python / Django - URL patterns
    (r'path\s*\(\s*["\']([^"\']+)["\'].*?(?:views?\.|View)', "django", None, 1),
    (r're_path\s*\(\s*["\']([^"\']+)["\']', "django", None, 1),
    # Node / Express - endpoint with path
    (r'(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', "express", 1, 2),
    # Go / Gin - endpoint with path
    (r'(?:r|router|engine|api)\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*["\']([^"\']+)["\']', "gin", 1, 2),
    # Go / net/http
    (r'http\.HandleFunc\s*\(\s*["\']([^"\']+)["\']', "nethttp", None, 1),
    # C# / .NET - Http method attribute
    (r'\[(?:HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch)\s*(?:\(\s*["\']([^"\']+)["\']\)?)?', "dotnet", "method", 1),
    # C# / .NET - Route attribute
    (r'\[Route\s*\(\s*["\']([^"\']+)["\']\s*\)', "dotnet-route", None, 1),
    # Ruby / Rails - route definition
    (r'(?:get|post|put|delete|patch)\s+["\']([^"\']+)["\']\s*(?:=>|,)', "rails", "method", 1),
]


def scan_api_entries(repo_path: str) -> dict:
    """Walk repo and find API entry points. Returns JSON-serializable dict."""
    repo_path = os.path.abspath(repo_path)
    if not os.path.isdir(repo_path):
        print(f"Error: directory not found: {repo_path}", file=sys.stderr)
        sys.exit(1)

    entries = []
    controllers = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for fname in sorted(files):
            if not fname.endswith(SCAN_EXTENSIONS):
                continue

            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, repo_path)

            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except Exception:
                continue

            for i, line in enumerate(lines, 1):
                stripped = line.strip()

                for pattern, framework, method_group, route_group in PATTERNS:
                    m = re.search(pattern, stripped, re.IGNORECASE)
                    if not m:
                        continue

                    entry = {
                        "file": rel_path,
                        "line": i,
                        "framework": framework,
                    }

                    # Extract HTTP method
                    if method_group is None:
                        entry["method"] = "CLASS"
                    elif method_group == "mapping":
                        ann_m = re.match(r'@(\w+)Mapping', stripped)
                        if ann_m:
                            entry["method"] = ann_m.group(1).upper()
                        else:
                            entry["method"] = "ANY"
                    elif method_group == "method":
                        ann_m = re.match(r'\[Http(\w+)\]', stripped)
                        if ann_m:
                            entry["method"] = ann_m.group(1).upper()
                        else:
                            entry["method"] = "ANY"
                    else:
                        try:
                            entry["method"] = m.group(method_group).upper()
                        except (IndexError, AttributeError):
                            entry["method"] = "ANY"

                    # Extract route path
                    if route_group is not None:
                        try:
                            entry["route"] = m.group(route_group)
                        except (IndexError, AttributeError):
                            entry["route"] = ""
                    else:
                        entry["route"] = ""

                    if entry["method"] == "CLASS":
                        controllers.append(entry)
                    else:
                        entries.append(entry)

                    break  # one match per line

    return {
        "api_entries": entries,
        "controllers": controllers,
        "summary": {
            "total_endpoints": len(entries),
            "total_controllers": len(controllers),
            "frameworks_detected": sorted(set(
                e["framework"] for e in entries + controllers
            )),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan a repo for API entry points")
    parser.add_argument("repo_path", help="Path to the repository root")
    parser.add_argument("--output", "-o", default=None, help="Output JSON file path (default: stdout)")
    args = parser.parse_args()

    result = scan_api_entries(args.repo_path)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
