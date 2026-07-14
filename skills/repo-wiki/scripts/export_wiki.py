#!/usr/bin/env python3
"""Export wiki structure + generated page contents to docs/wiki/ directory.

Ported from deepwiki-open's generate_markdown_export function.
Reads a structure JSON and a directory of per-page markdown files,
writes each page as a separate .md file. The overview page becomes
the overview page file with the table of contents merged in.

All output filenames are derived from page titles (sanitized for filesystem).

Usage:
    python3 export_wiki.py <structure.json> <pages_dir> [--output <docs/wiki>] [--scan <scan.json>]

  structure.json  -- output of parse_structure.py
  pages_dir      -- directory containing <page_id>.md files with generated content
  --output       -- target directory (default: docs/wiki)
  --scan         -- scan.json from scan_repo.py (for incremental update)
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


def _find_parent_section(section_id: str, sections: list) -> dict | None:
    """Find the parent section that contains section_id in its subsections."""
    for s in sections:
        if section_id in (s.get("subsections") or []):
            return s
    return None


def build_page_dir(page: dict, sections: list) -> str:
    """Build the subdirectory path for a page based on its parent section.

    Returns "" (flat) when:
    - there are no sections (lite mode)
    - the page has no parentSection

    Returns "section_title/[subsection_title/]" for full mode pages
    nested under sections. Maximum depth is 2 levels.
    """
    if not sections:
        return ""

    parent_section_id = page.get("parentSection", "")
    if not parent_section_id:
        return ""

    section_map = {s["id"]: s for s in sections}
    chain: list[str] = []
    current_id = parent_section_id
    visited: set[str] = set()

    while current_id and current_id not in visited:
        visited.add(current_id)
        sec = section_map.get(current_id)
        if sec:
            chain.append(sanitize_filename(sec["title"]))
        parent = _find_parent_section(current_id, sections)
        current_id = parent["id"] if parent else None

    chain.reverse()
    # Limit to 2 levels max
    chain = chain[:2]
    return os.path.join(*chain) if chain else ""


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


def export_wiki(structure: dict, pages_dir: str, output_dir: str, scan_data: dict | None = None, incremental: bool = False, overview_only: bool = False) -> list[str]:
    """Write all wiki pages to output_dir. Overview page gets TOC merged in, uses title-based filename.
    
    Args:
        structure: Wiki structure dict (from parse_structure.py)
        pages_dir: Directory containing generated page markdown files
        output_dir: Output directory for wiki files
        scan_data: Optional scan data dict (from scan_repo.py) for meta.yaml generation
        incremental: If True, only regenerate pages whose source files have changed
        overview_only: If True, only generate overview page and meta.yaml (skip other pages)
    
    Returns:
        List of written file paths
    """
    # Read old meta.yaml for incremental comparison
    old_meta = None
    if incremental:
        old_meta = read_meta_yaml(output_dir)
        if old_meta:
            print(f"Incremental mode: comparing with previous generation from {old_meta.get('generated_at', 'unknown')}", file=sys.stderr)
        else:
            print("Incremental mode: no previous meta.yaml found, falling back to full generation", file=sys.stderr)
            incremental = False

    # Clean output directory to avoid leftover files from previous runs (only in full mode)
    if not incremental and not overview_only:
        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)
    else:
        # In incremental mode or overview-only mode, ensure output directory exists
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
    # In full mode, files go into section-based subdirectories.
    # The overview page stays at the root level (it's the entry point).
    sections = structure.get("sections", [])
    used_filenames: set[str] = set()
    page_id_to_file: dict[str, str] = {}
    for page in pages:
        filename = build_page_filename(page, used_filenames)
        # Overview page always at root; others in section subdirs (full mode)
        if overview_page and page["id"] == overview_page["id"]:
            page_id_to_file[page["id"]] = filename
        else:
            page_dir = build_page_dir(page, sections)
            page_id_to_file[page["id"]] = os.path.join(page_dir, filename) if page_dir else filename

    # Build TOC lines (referencing non-overview page filenames)
    toc_lines = build_toc(structure, page_id_to_file, overview_page["id"] if overview_page else None)

    written: list[str] = []
    missing_pages: list[str] = []
    skipped_pages: list[str] = []

    # Build old page hash map for incremental comparison
    old_page_hashes = {}
    if incremental and old_meta and "pages" in old_meta:
        for old_page in old_meta["pages"]:
            old_page_hashes[old_page["id"]] = old_page.get("source_hash", "")

    # Write each page
    for page in pages_sorted:
        page_id = page["id"]
        filename = page_id_to_file[page_id]

        # Overview-only mode: skip non-overview pages
        if overview_only and page is not overview_page:
            continue

        # Incremental mode: check if page needs regeneration
        if incremental and old_meta:
            current_hash = compute_source_hash(page.get("filePaths", []), scan_data.get("file_hashes", {}) if scan_data else {})
            old_hash = old_page_hashes.get(page_id, "")
            
            if current_hash == old_hash and current_hash != "":
                # Source files unchanged, skip regeneration
                output_file = os.path.join(output_dir, filename)
                if os.path.isfile(output_file):
                    skipped_pages.append(page.get("title", page_id))
                    continue
                # If file doesn't exist, we need to regenerate it
            # else: hash changed or no old hash, regenerate

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

        file_path = os.path.join(output_dir, page_id_to_file[page_id])
        # Ensure subdirectory exists (for section-based layout in full mode)
        file_dir = os.path.dirname(file_path)
        if file_dir and file_dir != output_dir:
            os.makedirs(file_dir, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(parts))
        written.append(page_id_to_file[page_id])

    if missing_pages:
        print(f"Warning: {len(missing_pages)} page(s) have no generated content:", file=sys.stderr)
        for title in missing_pages:
            print(f"  - {title}", file=sys.stderr)

    if skipped_pages:
        print(f"Incremental: {len(skipped_pages)} page(s) skipped (source files unchanged):", file=sys.stderr)
        for title in skipped_pages:
            print(f"  - {title}", file=sys.stderr)

    return written


def read_meta_yaml(output_dir: str) -> dict | None:
    """Read existing meta.yaml for incremental update comparison.

    Returns None if meta.yaml doesn't exist or is invalid.
    Parses YAML manually to avoid PyYAML dependency.
    """
    meta_path = os.path.join(output_dir, "meta.yaml")
    if not os.path.isfile(meta_path):
        return None

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse simple YAML structure manually
        meta = {"pages": []}
        current_page = None

        for line in content.split("\n"):
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue

            # Top-level fields
            if line.startswith("repo_path:"):
                meta["repo_path"] = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("git_hash:"):
                meta["git_hash"] = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("generated_at:"):
                meta["generated_at"] = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("  - id:"):
                # Start of a new page
                if current_page:
                    meta["pages"].append(current_page)
                current_page = {"id": line.split(":", 1)[1].strip().strip('"'), "source_files": []}
            elif current_page and line.startswith("    title:"):
                current_page["title"] = line.split(":", 1)[1].strip().strip('"')
            elif current_page and line.startswith("    file:"):
                current_page["file"] = line.split(":", 1)[1].strip().strip('"')
            elif current_page and line.startswith("    importance:"):
                current_page["importance"] = line.split(":", 1)[1].strip().strip('"')
            elif current_page and line.startswith("      - "):
                # Source file entry
                current_page["source_files"].append(line.strip().lstrip("- ").strip('"'))
            elif current_page and line.startswith("    source_hash:"):
                current_page["source_hash"] = line.split(":", 1)[1].strip().strip('"')

        # Don't forget the last page
        if current_page:
            meta["pages"].append(current_page)

        return meta
    except Exception as e:
        print(f"Warning: Failed to read meta.yaml: {e}", file=sys.stderr)
        return None


def compute_source_hash(source_files: list, file_hashes: dict) -> str:
    """Compute combined hash for a list of source files."""
    if not source_files or not file_hashes:
        return ""
    combined = ""
    for sf in source_files:
        if sf in file_hashes:
            combined += file_hashes[sf]
    if combined:
        import hashlib
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    return ""


def generate_meta_yaml(structure: dict, page_id_to_file: dict, scan_data: dict | None, output_dir: str) -> None:
    """Generate meta.yaml in docs/wiki/ for incremental update support.

    meta.yaml records:
    - repo_path: source repository path
    - git_hash: current commit hash
    - generated_at: generation timestamp
    - pages: list of page metadata (id, title, file, importance, source_files, source_hash)

    This enables incremental updates: next run compares current git_hash/file_hashes
    with meta.yaml to determine which pages need regeneration.
    """
    pages = structure.get("pages", [])
    git_hash = scan_data.get("git_hash", "") if scan_data else ""
    file_hashes = scan_data.get("file_hashes", {}) if scan_data else {}

    meta = {
        "repo_path": scan_data.get("repo_path", "") if scan_data else "",
        "git_hash": git_hash,
        "generated_at": datetime.now().isoformat(),
        "pages": [],
    }

    for page in pages:
        page_id = page["id"]
        file_path = page_id_to_file.get(page_id, build_page_filename(page))
        source_files = page.get("filePaths", [])

        # Compute combined hash of all source files for this page
        source_hash = ""
        if source_files and file_hashes:
            combined = ""
            for sf in source_files:
                if sf in file_hashes:
                    combined += file_hashes[sf]
            if combined:
                import hashlib
                source_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]

        meta["pages"].append({
            "id": page_id,
            "title": page.get("title", ""),
            "file": file_path,
            "importance": page.get("importance", "medium"),
            "source_files": source_files,
            "source_hash": source_hash,
        })

    # Write meta.yaml (YAML format, not JSON)
    meta_path = os.path.join(output_dir, "meta.yaml")
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write("# wiki 产物元数据，用于增量更新\n")
        f.write(f"# 生成时间: {meta['generated_at']}\n")
        f.write(f"# 仓库: {meta['repo_path']}\n")
        f.write(f"# Git Hash: {meta['git_hash']}\n")
        f.write("\n")
        f.write(f"repo_path: \"{meta['repo_path']}\"\n")
        f.write(f"git_hash: \"{meta['git_hash']}\"\n")
        f.write(f"generated_at: \"{meta['generated_at']}\"\n")
        f.write("\n")
        f.write("pages:\n")
        for p in meta["pages"]:
            f.write(f"  - id: \"{p['id']}\"\n")
            f.write(f"    title: \"{p['title']}\"\n")
            f.write(f"    file: \"{p['file']}\"\n")
            f.write(f"    importance: \"{p['importance']}\"\n")
            f.write(f"    source_files:\n")
            for sf in p["source_files"]:
                f.write(f"      - \"{sf}\"\n")
            f.write(f"    source_hash: \"{p['source_hash']}\"\n")

    print(f"Generated meta.yaml at {meta_path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export wiki structure + pages to docs/wiki/")
    parser.add_argument("structure", help="Path to structure.json (from parse_structure.py)")
    parser.add_argument("pages_dir", nargs="?", default=None, help="Directory containing <page_id>.md content files (optional, not used in --overview-only mode)")
    parser.add_argument("--output", "-o", default="docs/wiki", help="Output directory (default: docs/wiki)")
    parser.add_argument("--scan", "-s", default=None, help="Path to scan.json from scan_repo.py (for meta.yaml generation)")
    parser.add_argument("--incremental", "-i", action="store_true", help="Only regenerate pages whose source files have changed")
    parser.add_argument("--overview-only", action="store_true", help="Only generate overview page and meta.yaml (skip other pages)")
    args = parser.parse_args()

    with open(args.structure, "r", encoding="utf-8") as f:
        structure = json.load(f)

    # Load scan data if provided
    scan_data = None
    if args.scan and os.path.isfile(args.scan):
        with open(args.scan, "r", encoding="utf-8") as f:
            scan_data = json.load(f)

    # Build page_id_to_file mapping (same logic as in export_wiki)
    pages = structure.get("pages", [])
    sections = structure.get("sections", [])
    overview_page = find_overview_page(pages)
    used_filenames: set[str] = set()
    page_id_to_file: dict[str, str] = {}
    for page in pages:
        filename = build_page_filename(page, used_filenames)
        if overview_page and page["id"] == overview_page["id"]:
            page_id_to_file[page["id"]] = filename
        else:
            page_dir = build_page_dir(page, sections)
            page_id_to_file[page["id"]] = os.path.join(page_dir, filename) if page_dir else filename

    written = export_wiki(structure, args.pages_dir or "", args.output, scan_data, args.incremental, args.overview_only)
    print(f"Written {len(written)} files to {args.output}:", file=sys.stderr)
    for fname in written:
        print(f"  - {fname}", file=sys.stderr)

    # Generate meta.yaml for incremental update
    generate_meta_yaml(structure, page_id_to_file, scan_data, args.output)


if __name__ == "__main__":
    main()
