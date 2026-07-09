#!/usr/bin/env python3
"""Lightweight project-outline structural checker.

Run from a project root:
  python3 skills/project-outline/scripts/validate_project_outline.py

The script intentionally uses only the Python standard library. It performs
basic presence and shape checks on docs/project-outline.md; full coverage
and inference review remain a human gate in the skill.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


# Required H2 sections of docs/project-outline.md (§1-§8).
# Matched as a keyword appearing in any markdown heading line.
# §9 待确认项 is conditional (required when inference markers present).
REQUIRED_SECTIONS = [
    ("项目概览", "§1 项目概览"),
    ("技术栈", "§2 架构与技术栈"),
    ("模块", "§3 模块结构"),
    ("数据模型", "§4 数据模型"),
    ("功能与接口", "§5 功能与接口"),
    ("核心流程", "§6 核心流程"),
    ("业务规则", "§7 业务规则"),
    ("维护指南", "§8 维护指南"),
]

# §9 待确认项 is required only when the doc contains inference markers.
INFERENCE_SECTION = "待确认项"

# Coverage-accounting subsection (required by the gate to fight incomplete output).
COVERAGE_KEYWORD = "覆盖率核对"

INFERENCE_MARKERS = ("(推断)", "(高置信推断)")

PLACEHOLDER_MARKERS = ("TBD", "TODO", "占位", "待补", "FIXME")


def report(level: str, message: str) -> None:
    print(f"[{level}] {message}")


def heading_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.lstrip().startswith("#")]


def check_markdown(rel: str, text: str) -> tuple[int, int]:
    """Return (failures, warnings) for the project-outline markdown."""
    failures = 0
    warnings = 0
    headings = heading_lines(text)

    for keyword, label in REQUIRED_SECTIONS:
        if any(keyword in h for h in headings):
            report("PASS", f"{rel}: {label} heading present")
        else:
            failures += 1
            report("FAIL", f"{rel}: missing required section {label} (keyword '{keyword}')")

    has_inference = any(marker in text for marker in INFERENCE_MARKERS)
    has_inference_section = any(INFERENCE_SECTION in h for h in headings)
    if has_inference and not has_inference_section:
        warnings += 1
        report(
            "WARN",
            f"{rel}: contains inference markers but no §{INFERENCE_SECTION} section to list them",
        )

    if not any(COVERAGE_KEYWORD in h for h in headings):
        warnings += 1
        report(
            "WARN",
            f"{rel}: missing '{COVERAGE_KEYWORD}' subsection (gate requires per-dimension coverage accounting)",
        )
    else:
        report("PASS", f"{rel}: '{COVERAGE_KEYWORD}' subsection present")

    for marker in PLACEHOLDER_MARKERS:
        count = len(re.findall(re.escape(marker), text))
        if count:
            warnings += 1
            report("WARN", f"{rel}: found {count} placeholder marker '{marker}'")

    return failures, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Check project-outline artifact health.")
    parser.add_argument("--root", default=".", help="Project root containing docs/")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    docs = root / "docs"
    failures = 0
    warnings = 0

    if not docs.exists():
        report("FAIL", f"{docs} does not exist")
        return 1

    md = docs / "project-outline.md"
    if not md.exists():
        failures += 1
        report("FAIL", "docs/project-outline.md missing")
    else:
        report("PASS", "docs/project-outline.md exists")
        text = md.read_text(encoding="utf-8")
        f, w = check_markdown("project-outline.md", text)
        failures += f
        warnings += w

    if failures:
        report("FAIL", f"project-outline validator found {failures} failure(s), {warnings} warning(s)")
        return 1
    report("PASS", f"project-outline validator found no failures ({warnings} warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
