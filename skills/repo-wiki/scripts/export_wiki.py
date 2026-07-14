#!/usr/bin/env python3
"""Export wiki structure + generated page contents to docs/wiki/ directory.

Ported from deepwiki-open's generate_markdown_export function.
Reads a structure JSON and a directory of per-page markdown files,
writes each page as a separate .md file. The overview page becomes
the overview page file with the table of contents merged in.

All output filenames are derived from page titles (sanitized for filesystem).

Usage:
    python3 export_wiki.py <structure.json> <pages_dir> [--output <docs/wiki>]

  structure.json  -- output of parse_structure.py
  pages_dir      -- directory containing <page_id>.md files with generated content
  --output       -- target directory (default: docs/wiki)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import shutil
from datetime import datetime


def sanitize_filename(title: str) -> str:
    """Convert a page title to a safe filesystem filename.

    Chinese characters are preserved; only filesystem-unsafe chars are replaced.
    """
    safe = re.sub(r'[\\/:*?"<>|]', "_", title)
    safe = re.sub(r"\s+", "_", safe.strip())
    safe = re.sub(r"_+", "_", safe)
    return safe


def build_page_filename(page: dict, used_filenames: set[str] | None = None) -> str:
    """Build the output filename for a page: <sanitized_title>.md

    If used_filenames is provided, append a numeric suffix when the
    sanitized title collides with an already-assigned filename, so that
    pages sharing the same title don't overwrite each other.
    """
    title = page.get("title") or page.get("id", "unnamed")
    base = sanitize_filename(title) + ".md"
    if used_filenames is None:
        return base
    if base not in used_filenames:
        used_filenames.add(base)
        return base
    # Collision: append _2, _3, ... until unique
    stem = sanitize_filename(title)
    n = 2
    while f"{stem}_{n}.md" in used_filenames:
        n += 1
    unique = f"{stem}_{n}.md"
    used_filenames.add(unique)
    return unique


def generate_anchor(heading: str) -> str:
    """Generate a Markdown anchor from heading text."""
    s = re.sub(r'<[^>]+>', '', heading)
    s = s.replace('`', '')
    s = s.lower()
    s = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', s, flags=re.UNICODE)
    s = re.sub(r'\s+', '-', s.strip())
    return s


def generate_page_toc(content: str) -> tuple[str | None, str]:
    """Extract H2/H3 headings from content, generate TOC, and insert HTML anchors.

    Returns (toc_markdown, content_with_anchors).
    toc_markdown is None if fewer than 2 headings found.
    content_with_anchors has <a id="xxx"></a> inserted before each heading.
    """
    lines = content.split('\n')
    in_code_block = False
    headings: list[tuple[int, str, str]] = []  # (level, title, anchor)
    heading_line_indices: list[int] = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        m = re.match(r'^(#{2,3})\s+(.+)', line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            # Use a simple anchor: heading-N
            anchor = f'heading-{len(headings) + 1}'
            headings.append((level, title, anchor))
            heading_line_indices.append(i)

    if len(headings) < 2:
        return None, content

    # Build TOC
    toc_lines: list[str] = []
    toc_lines.append('## 本页目录')
    toc_lines.append('')
    for level, title, anchor in headings:
        indent = '  ' * (level - 2)
        toc_lines.append(f'{indent}- [{title}](#{anchor})')
    toc_lines.append('')
    toc_lines.append('---')
    toc_lines.append('')
    toc_markdown = '\n'.join(toc_lines)

    # Insert HTML anchors before headings in content
    new_lines = list(lines)
    offset = 0
    for idx, (level, title, anchor) in zip(heading_line_indices, headings):
        anchor_line = f'<a id="{anchor}"></a>'
        new_lines.insert(idx + offset, anchor_line)
        offset += 1

    content_with_anchors = '\n'.join(new_lines)
    return toc_markdown, content_with_anchors


# Keywords to identify the overview/intro page
OVERVIEW_KEYWORDS = ["overview", "概览", "概述", "介绍", "简介", "about", "关于", "introduction"]


def find_overview_page(pages: list) -> dict | None:
    """Find the overview page by title keywords, falling back to first high-importance page."""
    # Try keyword match first
    for page in pages:
        title_lower = page.get("title", "").lower()
        if any(kw in title_lower for kw in OVERVIEW_KEYWORDS):
            return page
    # Fall back to first high-importance page
    for page in pages:
        if page.get("importance") == "high":
            return page
    # Fall back to first page
    return pages[0] if pages else None


def build_toc(structure: dict, page_id_to_file: dict, overview_page_id: str | None = None) -> list[str]:
    """Build table of contents lines from structure."""
    pages = structure.get("pages", [])
    sections = structure.get("sections", [])
    root_sections = structure.get("rootSections", [])
    lines: list[str] = []

    lines.append("## 目录")
    lines.append("")

    if sections and root_sections:
        section_map = {s["id"]: s for s in sections}
        for sec_id in root_sections:
            sec = section_map.get(sec_id)
            if not sec:
                continue
            lines.append(f"### {sec['title']}")
            lines.append("")
            _write_section_pages(sec, section_map, pages, page_id_to_file, lines, overview_page_id)
            for sub_id in sec.get("subsections") or []:
                sub = section_map.get(sub_id)
                if sub:
                    lines.append(f"#### {sub['title']}")
                    lines.append("")
                    _write_section_pages(sub, section_map, pages, page_id_to_file, lines, overview_page_id)
            lines.append("")
    else:
        for page in pages:
            if page["id"] == overview_page_id:
                lines.append(f"- {page['title']}（本页）")
            else:
                filename = page_id_to_file.get(page["id"], build_page_filename(page))
                lines.append(f"- [{page['title']}]({filename})")
        lines.append("")

    return lines


def _write_section_pages(section: dict, section_map: dict, pages: list, page_id_to_file: dict, out: list, overview_page_id: str | None = None) -> None:
    for page_id in section.get("pages") or []:
        page = next((p for p in pages if p["id"] == page_id), None)
        if page:
            if page_id == overview_page_id:
                # Overview page is the current page, no self-link
                out.append(f"- {page['title']}（本页）")
            else:
                filename = page_id_to_file.get(page_id, build_page_filename(page))
                out.append(f"- [{page['title']}]({filename})")
        else:
            out.append(f"- {page_id}")
    out.append("")


def export_wiki(structure: dict, pages_dir: str, output_dir: str) -> list[str]:
    """Write all wiki pages to output_dir. Overview page gets TOC merged in, uses title-based filename."""
    # Clean output directory to avoid leftover files from previous runs
    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    pages = structure.get("pages", [])
    wiki_title = structure.get("title", "")
    wiki_description = structure.get("description", "")

    # Sort pages by importance: high first, then medium, then low
    importance_order = {"high": 0, "medium": 1, "low": 2}
    pages_sorted = sorted(pages, key=lambda p: importance_order.get(p.get("importance", "medium"), 1))

    # Find overview page (content gets TOC merged in, but filename is normal)
    overview_page = find_overview_page(pages)

    # First pass: determine filenames - all pages use title-based filenames.
    # Track used filenames so that pages sharing the same title get a numeric
    # suffix instead of silently overwriting each other.
    used_filenames: set[str] = set()
    page_id_to_file: dict[str, str] = {}
    for page in pages:
        page_id_to_file[page["id"]] = build_page_filename(page, used_filenames)

    # Build TOC lines (referencing non-overview page filenames)
    toc_lines = build_toc(structure, page_id_to_file, overview_page["id"] if overview_page else None)

    written: list[str] = []
    missing_pages: list[str] = []

    # Write each page
    for page in pages_sorted:
        page_id = page["id"]
        filename = page_id_to_file[page_id]

        content = ""
        content_path = os.path.join(pages_dir, f"{page_id}.md")
        if os.path.isfile(content_path):
            with open(content_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = f"<!-- 内容未生成: {page.get('title', page_id)} -->\n"
            missing_pages.append(page.get("title", page_id))

        # Strip markdown code fences if present
        content = re.sub(r"^```(?:markdown)?\s*", "", content.strip(), flags=re.MULTILINE)
        content = re.sub(r"```\s*$", "", content.strip(), flags=re.MULTILINE)

        parts: list[str] = []

        if page is overview_page:
            # Overview page: merge title, description, TOC, and page content
            # Project title as H1 (replace the page's own H1 if present)
            content_no_h1 = re.sub(r"^# .+\n+", "", content, count=1)

            parts.append(f"# {wiki_title}" if wiki_title else f"# {page.get('title', '项目文档')}")
            parts.append("")
            if wiki_description:
                parts.append(wiki_description)
                parts.append("")
            parts.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            parts.append("")
            parts.append("---")
            parts.append("")
            # Table of contents
            parts.extend(toc_lines)
            parts.append("---")
            parts.append("")
            # Overview page: insert page TOC after content
            overview_toc, overview_anchored = generate_page_toc(content_no_h1)
            if overview_toc:
                parts.append(overview_anchored.strip())
                parts.append('')
                parts.append(overview_toc)
            else:
                parts.append(overview_anchored.strip())
        else:
            # Regular page: insert page TOC after H1, then content
            toc, content_anchored = generate_page_toc(content)
            if toc:
                h1_match = re.match(r'^(# .+)\n', content_anchored)
                if h1_match:
                    parts.append(h1_match.group(1))
                    parts.append('')
                    parts.append(toc)
                    parts.append(content_anchored[len(h1_match.group(0)):].strip())
                else:
                    parts.append(content_anchored)
            else:
                parts.append(content)

        # Related pages
        related = page.get("relatedPages", [])
        if related:
            parts.append("")
            parts.append("---")
            parts.append("")
            parts.append("### 相关页面")
            parts.append("")
            for rid in related:
                r_page = next((p for p in pages if p["id"] == rid), None)
                if r_page:
                    r_filename = page_id_to_file.get(rid, build_page_filename(r_page))
                    parts.append(f"- [{r_page['title']}]({r_filename})")
                else:
                    parts.append(f"- {rid}")
            parts.append("")

        file_path = os.path.join(output_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(parts))
        written.append(filename)

    if missing_pages:
        print(f"Warning: {len(missing_pages)} page(s) have no generated content:", file=sys.stderr)
        for title in missing_pages:
            print(f"  - {title}", file=sys.stderr)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Export wiki structure + pages to docs/wiki/")
    parser.add_argument("structure", help="Path to structure.json (from parse_structure.py)")
    parser.add_argument("pages_dir", help="Directory containing <page_id>.md content files")
    parser.add_argument("--output", "-o", default="docs/wiki", help="Output directory (default: docs/wiki)")
    args = parser.parse_args()

    with open(args.structure, "r", encoding="utf-8") as f:
        structure = json.load(f)

    written = export_wiki(structure, args.pages_dir, args.output)
    print(f"Written {len(written)} files to {args.output}:", file=sys.stderr)
    for fname in written:
        print(f"  - {fname}", file=sys.stderr)


if __name__ == "__main__":
    main()
