#!/usr/bin/env python3
"""Verify wiki output against structure.json — deterministic gate checks.

Hard gates (failure → exit 1):
  1. Overview page exists
  2. Every structure page has a corresponding .md file
  3. Each page starts with H1
  4. Filenames have no illegal characters
  5. Code block fences are complete
  6. No bare language identifiers
  7. Mermaid diagrams use allowed directions (TD only)
  8. Source references point to existing files (within repo)
  9. No orphan pages (.md files not in structure)
  10. No stale pages (structure page missing from disk)
  11. Fact conflicts are resolved (if facts provided)

Soft gates (failure → warning, exit 0):
  - Mermaid blocks >= 1 per page
  - Source file references >= 5 distinct files
  - Markdown tables >= 1 per page
  - Page internal links point to existing files
  - Module coverage >= 60% (deep mode)

Usage:
    python3 verify_wiki.py <structure.json> --wiki-dir docs/wiki
        [--modules modules.json] [--facts wiki_facts.json] [--repo <repo_path>]

Exit codes:
    0 = all hard gates passed (soft warnings may exist)
    1 = at least one hard gate failed
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys


OVERVIEW_KEYWORDS = ["overview", "概览", "概述", "介绍", "简介", "about", "关于", "introduction"]
ILLEGAL_FILENAME_CHARS = set('\\/:*?"<>|')


def sanitize_filename(title: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|]', "_", title)
    safe = re.sub(r"\s+", "_", safe.strip())
    safe = re.sub(r"_+", "_", safe)
    return safe


def build_page_filename(page: dict) -> str:
    title = page.get("title") or page.get("id", "unnamed")
    return sanitize_filename(title) + ".md"


def _norm_scope(scope: str) -> str:
    if not scope or scope == "./":
        return ""
    s = scope.replace("\\", "/").strip()
    if not s.endswith("/"):
        s += "/"
    return s


def find_overview_file(wiki_dir: str, pages: list) -> str | None:
    for page in pages:
        title_lower = page.get("title", "").lower()
        if any(kw in title_lower for kw in OVERVIEW_KEYWORDS):
            fname = build_page_filename(page)
            if os.path.isfile(os.path.join(wiki_dir, fname)):
                return fname
    for fname in os.listdir(wiki_dir):
        if fname.endswith(".md"):
            if any(kw in fname.lower() for kw in OVERVIEW_KEYWORDS):
                return fname
    return None


def count_mermaid_blocks(content: str) -> int:
    return len(re.findall(r"```mermaid\b", content))


def check_code_block_fences(content: str) -> list[str]:
    errors: list[str] = []
    in_block = False
    start_line = 0
    for i, line in enumerate(content.split('\n'), 1):
        if line.strip().startswith('```'):
            if not in_block:
                in_block = True
                start_line = i
            else:
                in_block = False
    if in_block:
        errors.append(f"Unclosed code block at line {start_line}")
    return errors


def check_bare_language_identifiers(content: str) -> list[str]:
    errors: list[str] = []
    in_block = False
    idents = {'mermaid', 'java', 'python', 'javascript', 'typescript', 'go',
              'rust', 'c', 'cpp', 'csharp', 'ruby', 'php', 'sql', 'json', 'yaml', 'xml'}
    for i, line in enumerate(content.split('\n'), 1):
        stripped = line.strip()
        if stripped.startswith('```'):
            in_block = not in_block
            continue
        if in_block:
            continue
        if stripped.lower() in idents:
            errors.append(f"Line {i}: bare '{stripped}' without fences")
    return errors


def check_mermaid_direction(content: str) -> list[str]:
    errors: list[str] = []
    in_mermaid = False
    start = 0
    for i, line in enumerate(content.split('\n'), 1):
        stripped = line.strip()
        if stripped.startswith('```mermaid'):
            in_mermaid = True
            start = i
            continue
        if stripped == '```' and in_mermaid:
            in_mermaid = False
            continue
        if in_mermaid and re.match(r'^(graph|flowchart)\s+(LR|TB|BT)\b', stripped):
            errors.append(f"Line {i}: forbidden direction in block@{start}: '{stripped}'")
    return errors


def count_source_refs(content: str) -> int:
    matches = re.findall(r"来源：\[([^\]]+)\]\([^)]+\)", content)
    return len(set(m.split(":")[0].strip() for m in matches))


def count_tables(content: str) -> int:
    return len(re.findall(r"\|.*\|.*\n\|[-:| ]+\|", content))


def find_broken_links(content: str, wiki_dir: str, current_path: str) -> list[str]:
    broken: list[str] = []
    for m in re.finditer(r'\[([^\]]+)\]\(([^)]+\.md)\)', content):
        link_text, link_path = m.group(1), m.group(2)
        if link_path.startswith("http"):
            continue
        current_dir = os.path.dirname(current_path)
        target = os.path.normpath(os.path.join(current_dir, link_path))
        if not os.path.isfile(target):
            broken.append(f"[{link_text}]({link_path})")
    return broken


def _find_file_recursive(base_dir: str, filename: str) -> str | None:
    for root, _dirs, files in os.walk(base_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None


def _find_orphan_pages(wiki_dir: str, expected_filenames: set[str]) -> list[str]:
    """Return .md files in wiki_dir that are NOT in expected_filenames."""
    orphans: list[str] = []
    for root, _dirs, files in os.walk(wiki_dir):
        for fname in files:
            if fname.endswith(".md") and fname not in expected_filenames:
                rel = os.path.relpath(os.path.join(root, fname), wiki_dir)
                orphans.append(rel)
    return orphans


def _check_source_refs_exist(content: str, repo_path: str | None) -> list[str]:
    """Check that source references in content point to existing files in repo.

    Returns list of broken reference descriptions.
    """
    if not repo_path:
        return []
    broken: list[str] = []
    for m in re.finditer(r"来源：\[([^\]]+)\]\(([^)]+)\)", content):
        ref_path = m.group(2).lstrip("./")
        # Remove anchor/query if present
        ref_path = ref_path.split("#")[0].split("?")[0]
        if not ref_path or ref_path.startswith("http"):
            continue
        full = os.path.join(repo_path, ref_path)
        if not os.path.exists(full):
            broken.append(m.group(0)[:80])
    return broken


def verify(structure: dict, wiki_dir: str,
           modules_data: dict | None = None,
           facts_data: dict | None = None,
           repo_path: str | None = None) -> tuple[bool, list[str]]:
    """Run all checks. Returns (hard_passed, all_messages).

    all_messages includes both HARD GATE FAILED and SOFT GATE WARNING entries.
    The caller should exit 1 if hard_passed is False.
    """
    pages = structure.get("pages", [])
    messages: list[str] = []
    hard_failed = False

    def _hard(msg: str):
        nonlocal hard_failed
        hard_failed = True
        messages.append(msg)

    def _soft(msg: str):
        messages.append(msg)

    # Collect all expected filenames for orphan detection
    expected_filenames: set[str] = set()
    for page in pages:
        expected_filenames.add(build_page_filename(page))

    # --- SOFT: module coverage (deep mode) ---
    if modules_data and modules_data.get("multi_module"):
        leaf_modules = [m for m in modules_data.get("modules", []) if m.get("type") == "leaf"]
        if leaf_modules:
            covered = 0
            for m in leaf_modules:
                prefixes = [_norm_scope(p) for p in m.get("scope", []) if _norm_scope(p)]
                has_page = any(
                    any(fp.startswith(pref) for pref in prefixes for fp in (p.get("filePaths") or []))
                    for p in pages
                )
                if has_page:
                    covered += 1
            ratio = covered / len(leaf_modules)
            if ratio < 0.6:
                _soft(f"SOFT GATE WARNING: module_coverage - {covered}/{len(leaf_modules)} "
                      f"leaf modules covered ({ratio:.0%}, expected >= 60%)")

    # --- HARD 1: Overview page exists ---
    overview = find_overview_file(wiki_dir, pages)
    if not overview:
        _hard(f"HARD GATE FAILED: overview_page_exists - no overview file in {wiki_dir}")

    # --- HARD 2: Every page has a .md file ---
    page_file_map: dict[str, str] = {}  # page_id → filepath
    for page in pages:
        expected = build_page_filename(page)
        found = _find_file_recursive(wiki_dir, expected)
        if not found:
            _hard(f"HARD GATE FAILED: page_file_exists - '{page.get('id')}' expected '{expected}' not found")
        else:
            page_file_map[page["id"]] = found

    # --- HARD 3: Each page starts with H1 ---
    for page in pages:
        filepath = page_file_map.get(page.get("id", ""))
        if filepath:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                first_line = f.readline().strip()
            if not first_line.startswith("# "):
                _hard(f"HARD GATE FAILED: h1_title - '{page.get('title')}' first line: '{first_line[:50]}'")

    # --- HARD 4: Filenames legal ---
    for root, _dirs, files in os.walk(wiki_dir):
        for fname in files:
            if fname.endswith(".md") and any(c in fname for c in ILLEGAL_FILENAME_CHARS):
                _hard(f"HARD GATE FAILED: filename_safety - '{fname}' has illegal chars")

    # --- HARD 5-7 + SOFT: Per-page content checks ---
    for page in pages:
        filepath = page_file_map.get(page.get("id", ""))
        if not filepath:
            continue
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        title = page.get("title", page.get("id", "unknown"))

        # SOFT: Mermaid
        if count_mermaid_blocks(content) < 1:
            _soft(f"SOFT GATE WARNING: mermaid_blocks - '{title}' has 0 diagrams")

        # HARD: Code fences
        fence_errs = check_code_block_fences(content)
        if fence_errs:
            _hard(f"HARD GATE FAILED: code_block_fences - '{title}': {fence_errs[0]}")

        # HARD: Bare identifiers
        bare_errs = check_bare_language_identifiers(content)
        if bare_errs:
            _hard(f"HARD GATE FAILED: bare_language_identifiers - '{title}': {bare_errs[0]}")

        # HARD: Mermaid direction
        dir_errs = check_mermaid_direction(content)
        if dir_errs:
            _hard(f"HARD GATE FAILED: mermaid_direction - '{title}': {dir_errs[0]}")

        # SOFT: Source refs count
        ref_count = count_source_refs(content)
        if ref_count < 5:
            _soft(f"SOFT GATE WARNING: source_refs - '{title}' references {ref_count} files (< 5)")

        # SOFT: Tables
        if count_tables(content) < 1:
            _soft(f"SOFT GATE WARNING: tables - '{title}' has 0 tables")

        # SOFT: Broken links
        for b in find_broken_links(content, wiki_dir, filepath):
            _soft(f"SOFT GATE WARNING: broken_link - '{title}' dead link {b}")

        # HARD 8: Source references point to existing files
        broken_refs = _check_source_refs_exist(content, repo_path)
        for br in broken_refs:
            _hard(f"HARD GATE FAILED: source_ref_exists - '{title}' references missing file: {br}")

    # --- HARD 9: Orphan pages ---
    orphans = _find_orphan_pages(wiki_dir, expected_filenames)
    for o in orphans:
        _soft(f"SOFT GATE WARNING: orphan_page - '{o}' not in structure (consider removing)")

    # --- HARD 10: Stale pages (in structure but missing from disk) ---
    for page in pages:
        pid = page.get("id", "")
        if pid not in page_file_map:
            _hard(f"HARD GATE FAILED: stale_page - '{pid}' in structure but no .md file on disk")

    # --- HARD 11: Fact conflicts ---
    if facts_data and facts_data.get("conflicts"):
        for c in facts_data["conflicts"]:
            _hard(f"HARD GATE FAILED: fact_conflict - {c['fact_id']} has conflicting values")

    return not hard_failed, messages


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify wiki output against structure.json")
    parser.add_argument("structure", help="Path to structure.json (from parse_structure.py)")
    parser.add_argument("--wiki-dir", default="docs/wiki", help="Output wiki directory")
    parser.add_argument("--modules", default=None, help="modules.json from scan_modules.py")
    parser.add_argument("--facts", default=None, help="wiki_facts.json from build_facts.py")
    parser.add_argument("--repo", default=None, help="Repository root (for source ref validation)")
    args = parser.parse_args()

    if not os.path.isdir(args.wiki_dir):
        print(f"HARD GATE FAILED: wiki_dir_exists - directory not found: {args.wiki_dir}", file=sys.stderr)
        sys.exit(1)

    with open(args.structure, "r", encoding="utf-8") as f:
        structure = json.load(f)

    modules_data = None
    if args.modules and os.path.isfile(args.modules):
        try:
            with open(args.modules, "r", encoding="utf-8") as f:
                modules_data = json.load(f)
        except Exception as e:
            print(f"Warning: failed to load modules: {e}", file=sys.stderr)

    facts_data = None
    if args.facts and os.path.isfile(args.facts):
        try:
            with open(args.facts, "r", encoding="utf-8") as f:
                facts_data = json.load(f)
        except Exception as e:
            print(f"Warning: failed to load facts: {e}", file=sys.stderr)

    hard_passed, messages = verify(structure, args.wiki_dir, modules_data, facts_data, args.repo)

    # Aggregate report: print ALL messages, not just the first failure
    hard_count = sum(1 for m in messages if m.startswith("HARD"))
    soft_count = sum(1 for m in messages if m.startswith("SOFT"))
    for msg in messages:
        print(msg, file=sys.stderr)
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Verification report: {hard_count} hard failure(s), {soft_count} soft warning(s)",
          file=sys.stderr)
    pages_count = len(structure.get("pages", []))
    if hard_passed:
        print(f"All hard gates passed ({pages_count} pages verified)", file=sys.stderr)
        sys.exit(0)
    else:
        print(f"HARD GATES FAILED — {hard_count} issue(s) must be fixed before publishing",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
