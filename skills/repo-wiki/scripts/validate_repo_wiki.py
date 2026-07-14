#!/usr/bin/env python3
"""Lightweight repo-wiki structural checker.

Run from a project root:
  python3 skills/repo-wiki/scripts/validate_repo_wiki.py

Checks docs/wiki/ for the per-module knowledge model with section directories:
  - 总览.md section tree overview exists
  - each section directory has 简介.md with frontmatter
  - each module .md in section dirs has frontmatter (description/module_id/section)
    + ## 概述 + ## 架构设计
  - ## 概述 is not a file-path list (heuristic check)
  - ## 关系 links (if present) resolve to existing module files
  - 仓库级约定/ has 6 category files + 简介.md (Chinese category names)

Standard library only. Full coverage review remains a human gate
(see references/coverage-gates.md).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

# Chinese category names for repo-knowledge
CATEGORIES = [
    "构建系统",
    "配置系统",
    "依赖管理",
    "异常处理",
    "日志系统",
    "前端风格",
]
REQUIRED_MODULE_FRONTMATTER = ("description", "module_id", "section")
REQUIRED_SECTION_FRONTMATTER = ("title", "description", "module_count")
REQUIRED_SECTIONS = ("概述", "架构设计")

# Chinese file/directory names
OVERVIEW_FILE = "总览.md"
SECTION_INTRO_FILE = "简介.md"
REPO_KNOWLEDGE_DIR = "仓库级约定"

# Directories that are not section directories
SPECIAL_DIRS = {REPO_KNOWLEDGE_DIR}


def report(level: str, message: str) -> None:
    print(f"[{level}] {message}")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Return frontmatter fields if the file starts with ---, else None."""
    if not text.lstrip().startswith("---"):
        return None
    end = text.find("\n---", text.lstrip().find("---") + 3)
    if end == -1:
        return None
    block = text[:end]
    fields: dict[str, str] = {}
    for line in block.splitlines():
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m:
            val = m.group(2).strip().strip('"').strip("'")
            fields[m.group(1)] = val
    return fields


def check_module_file(rel: str, text: str, section_dir: str) -> tuple[int, int]:
    """Validate one module .md. Returns (failures, warnings)."""
    failures = 0
    warnings = 0
    fm = parse_frontmatter(text)
    if fm is None:
        failures += 1
        report("FAIL", f"{rel}: missing frontmatter (need description/module_id/section)")
    else:
        for field in REQUIRED_MODULE_FRONTMATTER:
            if field not in fm or not fm[field]:
                failures += 1
                report("FAIL", f"{rel}: frontmatter missing/empty '{field}'")
        # Check section field matches directory name
        if fm and "section" in fm and fm["section"] != section_dir:
            warnings += 1
            report("WARN", f"{rel}: frontmatter section='{fm['section']}' but file is in directory '{section_dir}'")

    headings = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("#")]
    for sec in REQUIRED_SECTIONS:
        if any(f"## {sec}" in h for h in headings):
            continue
        failures += 1
        report("FAIL", f"{rel}: missing required section '## {sec}'")

    # Heuristic: ## 概述 should not be a file-path list
    overview_found = False
    in_overview = False
    overview_lines = []
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s == "## 概述" or s.startswith("## 概述 "):
            in_overview = True
            overview_found = True
            continue
        if in_overview:
            if s.startswith("## "):
                break
            overview_lines.append(s)
    if overview_found:
        overview_text = "\n".join(overview_lines)
        if re.search(r"source_files\s*:", overview_text):
            warnings += 1
            report("WARN", f"{rel}: ## 概述 contains 'source_files:' — should focus on business description, not path listing")
        path_lines = sum(1 for ln in overview_lines if "/" in ln or "\\" in ln)
        if path_lines > 3:
            warnings += 1
            report("WARN", f"{rel}: ## 概述 has {path_lines} path-like lines — consider focusing on business functions")

    # Empty sections warn
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("## ") and not s.startswith("### "):
            j = i + 1
            has_body = False
            while j < len(lines) and not lines[j].strip().startswith("#"):
                if lines[j].strip():
                    has_body = True
                    break
                j += 1
            if not has_body:
                warnings += 1
                report("WARN", f"{rel}: empty section '{s}' (should have content or be omitted)")

    return failures, warnings


def check_section_file(rel: str, text: str) -> tuple[int, int]:
    """Validate one _section.md. Returns (failures, warnings)."""
    failures = 0
    warnings = 0
    fm = parse_frontmatter(text)
    if fm is None:
        failures += 1
        report("FAIL", f"{rel}: missing frontmatter (need title/description/module_count)")
    else:
        for field in REQUIRED_SECTION_FRONTMATTER:
            if field not in fm or not fm[field]:
                failures += 1
                report("FAIL", f"{rel}: frontmatter missing/empty '{field}'")
    return failures, warnings


def extract_links(text: str) -> list[str]:
    """Extract markdown link targets that look like module references."""
    return [
        m
        for m in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
        if m and not m.startswith("http") and not m.startswith("#")
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check repo-wiki artifact health.")
    parser.add_argument("--root", default=".", help="Project root containing docs/wiki/")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    wiki = root / "docs" / "wiki"
    failures = 0
    warnings = 0

    if not wiki.exists():
        report("FAIL", f"{wiki} does not exist")
        return 1

    # 总览.md
    index = wiki / OVERVIEW_FILE
    if not index.exists():
        failures += 1
        report("FAIL", f"docs/wiki/{OVERVIEW_FILE} missing")
    else:
        report("PASS", f"docs/wiki/{OVERVIEW_FILE} exists")

    # Scan section directories
    section_dirs: set[str] = set()
    module_files: set[str] = set()
    all_module_paths: dict[str, str] = {}  # stem -> relative path for link resolution

    for child in sorted(wiki.iterdir()):
        if not child.is_dir():
            continue
        if child.name in SPECIAL_DIRS or child.name.startswith("."):
            continue
        # This is a section directory
        section_dirs.add(child.name)

        # Check _简介.md
        section_md = child / SECTION_INTRO_FILE
        if not section_md.exists():
            failures += 1
            report("FAIL", f"{child.name}/{SECTION_INTRO_FILE} missing")
        else:
            text = section_md.read_text(encoding="utf-8")
            f, w = check_section_file(f"{child.name}/{SECTION_INTRO_FILE}", text)
            failures += f
            warnings += w
            report("PASS", f"{child.name}/{SECTION_INTRO_FILE} present")

        # Scan module files in this section directory (including nested subsections)
        for md_file in sorted(child.rglob("*.md")):
            if md_file.name == SECTION_INTRO_FILE or md_file.name.startswith("."):
                continue
            rel = md_file.relative_to(wiki)
            rel_str = str(rel)
            stem = md_file.stem
            module_files.add(stem)
            all_module_paths[stem] = str(rel.with_suffix(""))

            # Determine which section directory this file is in
            section_dir = md_file.parent.name
            # For nested sections, use the top-level section dir name
            try:
                top_section = md_file.relative_to(wiki).parts[0]
            except (ValueError, IndexError):
                top_section = section_dir

            text = md_file.read_text(encoding="utf-8")
            f, w = check_module_file(rel_str, text, top_section)
            failures += f
            warnings += w

    if section_dirs:
        report("PASS", f"{len(section_dirs)} section directories found")
    else:
        failures += 1
        report("FAIL", "No section directories found under docs/wiki/")

    if module_files:
        report("PASS", f"{len(module_files)} module knowledge files present")
    else:
        report("WARN", "No module knowledge files found")

    # Check relation links resolve
    for md_file in wiki.rglob("*.md"):
        if md_file.name.startswith(".") or md_file.name == OVERVIEW_FILE:
            continue
        if md_file.parent.name == REPO_KNOWLEDGE_DIR or REPO_KNOWLEDGE_DIR in md_file.parts:
            continue
        text = md_file.read_text(encoding="utf-8")
        for target in extract_links(text):
            # Resolve relative to the file's directory
            # Links now include .md suffix, e.g., [显示名](概览/项目概述.md)
            resolved = md_file.parent / target
            if not resolved.exists():
                warnings += 1
                report("WARN", f"{md_file.relative_to(wiki)}: relation link '{target}' has no matching file")

    # 仓库级约定/ (Chinese category names)
    rk = wiki / REPO_KNOWLEDGE_DIR
    if not rk.exists():
        failures += 1
        report("FAIL", f"docs/wiki/{REPO_KNOWLEDGE_DIR}/ missing")
    else:
        rk_index = rk / SECTION_INTRO_FILE
        if not rk_index.exists():
            failures += 1
            report("FAIL", f"{REPO_KNOWLEDGE_DIR}/{SECTION_INTRO_FILE} missing")
        else:
            report("PASS", f"{REPO_KNOWLEDGE_DIR}/{SECTION_INTRO_FILE} exists")
        for cat in CATEGORIES:
            cf = rk / f"{cat}.md"
            if not cf.exists():
                failures += 1
                report("FAIL", f"{REPO_KNOWLEDGE_DIR}/{cat}.md missing")
            else:
                report("PASS", f"{REPO_KNOWLEDGE_DIR}/{cat}.md present")

    # 工作基线文件（.模块树.md、.章节树.md）已删除，不再检查

    if failures:
        report("FAIL", f"repo-wiki validator found {failures} failure(s), {warnings} warning(s)")
        return 1
    report("PASS", f"repo-wiki validator found no failures ({warnings} warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
