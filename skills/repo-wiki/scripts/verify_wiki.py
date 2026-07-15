#!/usr/bin/env python3
"""Verify wiki output against structure.json — gate checks for generated docs.

Referenced by SKILL.md step 6. Replaces "let LLM self-check" with
scripted, deterministic verification. Ported concept from
or-workflow-guide/scripts/sdd_doctor.py.

Two gate types:
  - HARD: failure -> exit 1 (product is broken)
  - SOFT: failure -> exit 0 + warning (quality suggestion, not a blocker)

Usage:
    python3 verify_wiki.py <structure.json> [--wiki-dir docs/wiki]

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


# Overview page keywords for finding the overview file
OVERVIEW_KEYWORDS = ["overview", "概览", "概述", "介绍", "简介", "about", "关于", "introduction"]

# Filesystem-illegal characters that should never appear in filenames
ILLEGAL_FILENAME_CHARS = set('\\/:*?"<>|')


def sanitize_filename(title: str) -> str:
    """Same logic as export_wiki.sanitize_filename — duplicated to keep
    verify_wiki.py standalone (zero cross-file dependencies)."""
    safe = re.sub(r'[\\/:*?"<>|]', "_", title)
    safe = re.sub(r"\s+", "_", safe.strip())
    safe = re.sub(r"_+", "_", safe)
    return safe


def build_page_filename(page: dict) -> str:
    """Build expected filename for a page — standalone version."""
    title = page.get("title") or page.get("id", "unnamed")
    return sanitize_filename(title) + ".md"


def find_overview_file(wiki_dir: str, pages: list) -> str | None:
    """Find the overview .md file by keyword match in filename."""
    for page in pages:
        title_lower = page.get("title", "").lower()
        if any(kw in title_lower for kw in OVERVIEW_KEYWORDS):
            fname = build_page_filename(page)
            if os.path.isfile(os.path.join(wiki_dir, fname)):
                return fname
    # Fallback: search actual files for keyword match
    for fname in os.listdir(wiki_dir):
        if fname.endswith(".md"):
            fname_lower = fname.lower()
            if any(kw in fname_lower for kw in OVERVIEW_KEYWORDS):
                return fname
    return None


def count_mermaid_blocks(content: str) -> int:
    """Count mermaid code blocks in markdown content."""
    return len(re.findall(r"```mermaid\b", content))


def check_code_block_fences(content: str) -> list[str]:
    """Check that all code blocks have proper opening and closing fences.
    
    Returns list of errors found.
    """
    errors = []
    lines = content.split('\n')
    in_code_block = False
    block_start_line = 0
    block_lang = ""
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Check for code fence
        if stripped.startswith('```'):
            if not in_code_block:
                # Opening fence
                in_code_block = True
                block_start_line = i
                block_lang = stripped[3:].strip()
            else:
                # Closing fence
                in_code_block = False
                block_lang = ""
    
    # If still in code block at end, it's unclosed
    if in_code_block:
        errors.append(f"Unclosed code block starting at line {block_start_line} (language: {block_lang})")
    
    return errors


def check_bare_language_identifiers(content: str) -> list[str]:
    """Check for bare language identifiers without code fences.
    
    Detects patterns like:
    - Line starting with 'mermaid' (without ```)
    - Line starting with 'java' (without ```)
    - Line starting with 'python' (without ```)
    etc.
    
    Returns list of errors found.
    """
    errors = []
    lines = content.split('\n')
    in_code_block = False
    
    # Common language identifiers that might appear bare
    lang_identifiers = {
        'mermaid', 'java', 'python', 'javascript', 'typescript', 'go', 'rust',
        'c', 'cpp', 'csharp', 'ruby', 'php', 'sql', 'json', 'yaml', 'xml',
        'bash', 'shell', 'powershell', 'dockerfile', 'makefile'
    }
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Track code blocks
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            continue
        
        # Skip if inside code block
        if in_code_block:
            continue
        
        # Check if line is just a language identifier
        if stripped.lower() in lang_identifiers:
            errors.append(f"Line {i}: Bare language identifier '{stripped}' without code fences (should be ```{stripped})")
    
    return errors


def check_mermaid_direction(content: str) -> list[str]:
    """Check that mermaid diagrams use allowed directions.
    
    Only 'graph TD' and 'flowchart TD' are allowed.
    'LR', 'TB', 'BT' are forbidden.
    
    Returns list of errors found.
    """
    errors = []
    lines = content.split('\n')
    in_mermaid_block = False
    block_start_line = 0
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if stripped.startswith('```mermaid'):
            in_mermaid_block = True
            block_start_line = i
            continue
        
        if stripped == '```' and in_mermaid_block:
            in_mermaid_block = False
            continue
        
        if in_mermaid_block:
            # Check for forbidden directions
            if re.match(r'^(graph|flowchart)\s+(LR|TB|BT)\b', stripped):
                errors.append(f"Line {i}: Forbidden mermaid direction in block starting at line {block_start_line}: '{stripped}' (only 'graph TD' or 'flowchart TD' allowed)")
    
    return errors


def count_source_refs(content: str) -> int:
    """Count distinct source file references in '来源：[xxx](../../xxx)' format."""
    # Match 来源：[filename:line](path) or 来源：[filename](path)
    pattern = r"来源：\[([^\]]+)\]\([^)]+\)"
    matches = re.findall(pattern, content)
    # Extract just the filename part (before : if present) to count distinct files
    files = set()
    for m in matches:
        # Take the part before : (line number) as the file identifier
        fname = m.split(":")[0] if ":" in m else m
        files.add(fname.strip())
    return len(files)


def count_tables(content: str) -> int:
    """Count markdown tables in content."""
    # A markdown table has a header row, then a separator row with dashes
    return len(re.findall(r"\|.*\|.*\n\|[-:| ]+\|", content))


def find_broken_links(content: str, wiki_dir: str, current_path: str) -> list[str]:
    """Find .md links that point to non-existent files."""
    broken = []
    # Match [text](filename.md) but not URLs or anchors
    for m in re.finditer(r'\[([^\]]+)\]\(([^)]+\.md)\)', content):
        link_text = m.group(1)
        link_path = m.group(2)
        # Skip if it looks like a URL
        if link_path.startswith("http"):
            continue
        # Resolve relative to the directory of current_path
        current_dir = os.path.dirname(current_path)
        target = os.path.normpath(os.path.join(current_dir, link_path))
        if not os.path.isfile(target):
            broken.append(f"[{link_text}]({link_path})")
    return broken


def verify(structure: dict, wiki_dir: str) -> tuple[bool, list[str]]:
    """Run all checks. Returns (hard_passed, warnings)."""
    pages = structure.get("pages", [])
    warnings: list[str] = []

    # --- HARD GATE 1: Overview page exists ---
    overview = find_overview_file(wiki_dir, pages)
    if not overview:
        return False, [f"HARD GATE FAILED: overview_page_exists - no file with keywords {OVERVIEW_KEYWORDS} found in {wiki_dir}"]

    # --- HARD GATE 2: Every page has a corresponding .md file ---
    for page in pages:
        expected = build_page_filename(page)
        # File could be at root or in a subdirectory (section-based)
        found = _find_file_recursive(wiki_dir, expected)
        if not found:
            return False, [f"HARD GATE FAILED: page_file_exists - page '{page.get('id')}' (title: '{page.get('title')}') expected file '{expected}' not found in {wiki_dir}"]

    # --- HARD GATE 3: Each page starts with H1 ---
    for page in pages:
        expected = build_page_filename(page)
        filepath = _find_file_recursive(wiki_dir, expected)
        if filepath:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                first_line = f.readline().strip()
            if not first_line.startswith("# "):
                return False, [f"HARD GATE FAILED: h1_title - page '{page.get('title')}' first line is not H1: '{first_line[:50]}'"]

    # --- HARD GATE 4: Filenames have no illegal characters ---
    for fname in os.listdir(wiki_dir):
        if fname.endswith(".md"):
            if any(c in fname for c in ILLEGAL_FILENAME_CHARS):
                return False, [f"HARD GATE FAILED: filename_safety - '{fname}' contains illegal characters"]

    # --- SOFT GATES ---
    for page in pages:
        expected = build_page_filename(page)
        filepath = _find_file_recursive(wiki_dir, expected)
        if not filepath:
            continue  # Already caught by hard gate

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        title = page.get("title", page.get("id", "unknown"))

        # SOFT: Mermaid blocks >= 1
        mermaid_count = count_mermaid_blocks(content)
        if mermaid_count < 1:
            warnings.append(f"SOFT GATE WARNING: mermaid_blocks - page '{title}' has {mermaid_count} mermaid diagrams (expected >= 1)")

        # HARD: Code block fences must be complete
        fence_errors = check_code_block_fences(content)
        if fence_errors:
            return False, [f"HARD GATE FAILED: code_block_fences - page '{title}': {fence_errors[0]}"]

        # HARD: No bare language identifiers
        bare_lang_errors = check_bare_language_identifiers(content)
        if bare_lang_errors:
            return False, [f"HARD GATE FAILED: bare_language_identifiers - page '{title}': {bare_lang_errors[0]}"]

        # HARD: Mermaid diagrams must use allowed directions
        direction_errors = check_mermaid_direction(content)
        if direction_errors:
            return False, [f"HARD GATE FAILED: mermaid_direction - page '{title}': {direction_errors[0]}"]

        # SOFT: Source file references >= 5 distinct files
        ref_count = count_source_refs(content)
        if ref_count < 5:
            warnings.append(f"SOFT GATE WARNING: source_refs - page '{title}' references {ref_count} distinct source files (expected >= 5)")

        # SOFT: Markdown tables >= 1
        table_count = count_tables(content)
        if table_count < 1:
            warnings.append(f"SOFT GATE WARNING: tables - page '{title}' has {table_count} markdown tables (expected >= 1)")

        # SOFT: All .md links point to existing files
        broken = find_broken_links(content, wiki_dir, filepath)
        for b in broken:
            warnings.append(f"SOFT GATE WARNING: broken_link - page '{title}' has dead link {b}")

    return True, warnings


def _find_file_recursive(base_dir: str, filename: str) -> str | None:
    """Find a file by name, searching recursively (for section-based subdirectories)."""
    for root, _dirs, files in os.walk(base_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify wiki output against structure.json")
    parser.add_argument("structure", help="Path to structure.json (from parse_structure.py)")
    parser.add_argument("--wiki-dir", default="docs/wiki", help="Output wiki directory (default: docs/wiki)")
    args = parser.parse_args()

    if not os.path.isdir(args.wiki_dir):
        print(f"HARD GATE FAILED: wiki_dir_exists - directory not found: {args.wiki_dir}", file=sys.stderr)
        sys.exit(1)

    with open(args.structure, "r", encoding="utf-8") as f:
        structure = json.load(f)

    hard_passed, messages = verify(structure, args.wiki_dir)

    for msg in messages:
        print(msg, file=sys.stderr)

    pages_count = len(structure.get("pages", []))

    if hard_passed:
        print(f"All gates passed ({pages_count} pages verified)", file=sys.stderr)
        # Soft warnings don't affect exit code
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
