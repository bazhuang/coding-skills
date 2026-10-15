#!/usr/bin/env python3
"""Export wiki structure + generated page contents to docs/wiki/ directory.

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

    Returns "section/subsection/[subsubsection/]" for pages nested under
    sections. Supports up to 3 levels (full mode: 2, deep mode: 3).
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
    # Support up to 3 levels (deep mode: section > subsection > subsubsection)
    chain = chain[:3]
    if not chain:
        return ""
    # Use forward slashes so the value is safe both for Markdown links /
    # meta.yaml and for open() (Python accepts "/" on Windows too).
    return "/".join(chain)


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


def export_wiki(structure: dict, pages_dir: str, output_dir: str, scan_data: dict | None = None, incremental: bool = False, overview_only: bool = False, modules_data: dict | None = None) -> list[str]:
    """Write all wiki pages to output_dir. Overview page gets TOC merged in, uses title-based filename.

    Args:
        structure: Wiki structure dict (from parse_structure.py)
        pages_dir: Directory containing generated page markdown files
        output_dir: Output directory for wiki files
        scan_data: Optional scan data dict (from scan_repo.py) for meta.yaml generation
        incremental: If True, only regenerate pages whose source files have changed
        overview_only: If True, only generate overview page and meta.yaml (skip other pages)
        modules_data: Optional module tree (from scan_modules.py) enabling module-level
            incremental updates: when a module's aggregate hash is unchanged, all of its
            pages are skipped at once instead of being checked one by one.
    
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
            # page_dir already uses forward slashes; keep them so the value is
            # safe for Markdown links / meta.yaml (Python open() accepts "/" too).
            page_id_to_file[page["id"]] = f"{page_dir}/{filename}" if page_dir else filename

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

    # Module-level fast path: precompute the set of pages that belong to
    # modules whose aggregate hash is unchanged. These can be skipped in a
    # single check, avoiding a per-file hash lookup for every page.
    module_unchanged_pages: set[str] = set()
    if incremental and old_meta and modules_data and scan_data:
        file_hashes = scan_data.get("file_hashes", {})
        old_modules = {m["id"]: m for m in old_meta.get("modules", [])}
        for m in modules_data.get("modules", []):
            old_m = old_modules.get(m["id"])
            if not old_m:
                continue
            cur_hash = compute_module_hash(m.get("scope", []), file_hashes)
            if cur_hash and cur_hash == old_m.get("module_hash", ""):
                module_unchanged_pages.update(old_m.get("pages", []))

    # Write each page
    for page in pages_sorted:
        page_id = page["id"]
        filename = page_id_to_file[page_id]

        # Overview-only mode: skip non-overview pages
        if overview_only and page is not overview_page:
            continue

        # Incremental mode: check if page needs regeneration
        if incremental and old_meta:
            # Module-level fast path: skip pages under unchanged modules.
            if page_id in module_unchanged_pages:
                output_file = os.path.join(output_dir, filename)
                if os.path.isfile(output_file):
                    skipped_pages.append(page.get("title", page_id))
                    continue

            # Page-level fallback: compare the page's own source hash.
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
    Parses YAML manually to avoid PyYAML dependency. Supports both the
    pages section and the optional modules section.
    """
    meta_path = os.path.join(output_dir, "meta.yaml")
    if not os.path.isfile(meta_path):
        return None

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            content = f.read()

        meta = {"pages": [], "modules": []}
        section: str | None = None        # "pages" | "modules" | None
        current_page = None
        current_module = None
        current_list_key: str | None = None  # which sub-list we're inside

        def _val(s: str) -> str:
            return s.split(":", 1)[1].strip().strip('"')

        for line in content.split("\n"):
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue

            stripped = line.lstrip()

            # Top-level keys
            if line[:1] not in (" ", "\t"):
                current_list_key = None
                if stripped.startswith("repo_path:"):
                    meta["repo_path"] = _val(stripped)
                elif stripped.startswith("git_hash:"):
                    meta["git_hash"] = _val(stripped)
                elif stripped.startswith("generated_at:"):
                    meta["generated_at"] = _val(stripped)
                elif stripped.startswith("pages:"):
                    if current_page:
                        meta["pages"].append(current_page)
                    if current_module:
                        meta["modules"].append(current_module)
                    current_page = None
                    current_module = None
                    section = "pages"
                elif stripped.startswith("modules:"):
                    if current_page:
                        meta["pages"].append(current_page)
                    if current_module:
                        meta["modules"].append(current_module)
                    current_page = None
                    current_module = None
                    section = "modules"
                continue

            # A new list item starts a new page or module record.
            if stripped.startswith("- id:"):
                current_list_key = None
                if section == "pages":
                    if current_page:
                        meta["pages"].append(current_page)
                    current_page = {"id": _val(stripped), "source_files": []}
                elif section == "modules":
                    if current_module:
                        meta["modules"].append(current_module)
                    current_module = {"id": _val(stripped), "scope": [], "pages": []}
                continue

            if section == "pages" and current_page:
                if stripped.startswith("title:"):
                    current_page["title"] = _val(stripped)
                elif stripped.startswith("file:"):
                    current_page["file"] = _val(stripped)
                elif stripped.startswith("importance:"):
                    current_page["importance"] = _val(stripped)
                elif stripped.startswith("source_hash:"):
                    current_page["source_hash"] = _val(stripped)
                elif stripped.startswith("source_files:"):
                    current_list_key = "source_files"
                elif stripped.startswith("- "):
                    if current_list_key == "source_files":
                        current_page["source_files"].append(stripped.lstrip("- ").strip('"'))
            elif section == "modules" and current_module:
                if stripped.startswith("title:"):
                    current_module["title"] = _val(stripped)
                    current_list_key = None
                elif stripped.startswith("module_hash:"):
                    current_module["module_hash"] = _val(stripped)
                    current_list_key = None
                elif stripped.startswith("scope:"):
                    current_list_key = "scope"
                elif stripped.startswith("pages:"):
                    current_list_key = "pages"
                elif stripped.startswith("- ") and current_list_key:
                    current_module[current_list_key].append(stripped.lstrip("- ").strip('"'))

        # Flush the last record(s)
        if current_page:
            meta["pages"].append(current_page)
        if current_module:
            meta["modules"].append(current_module)

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


def _normalize_scope_prefix(scope: str) -> str:
    """Normalise a module scope value to a directory prefix with trailing /.

    scan_modules emits scopes like "module-a/" or "./". We compare file
    paths against these prefixes, so both "./" and "" mean "repo root".
    """
    if not scope or scope == "./":
        return ""
    s = scope.replace("\\", "/").strip()
    if not s.endswith("/"):
        s += "/"
    return s


def assign_pages_to_modules(pages: list, modules: list) -> dict[str, list[str]]:
    """Map each page to the module whose scope contains its source files.

    Returns {module_id: [page_id, ...]} for modules that own at least one
    page. Pages whose files match no module scope are not included (they
    fall back to page-level incremental handling). A page is assigned to
    the most specific (deepest) matching module to avoid a file being
    claimed by both a parent aggregate and its leaf child.
    """
    if not modules:
        return {}
    # Build (prefix, depth, module_id) for every module, aggregates and leaves.
    # Sort by depth descending so the deepest (most specific) match wins.
    candidates = []
    for m in modules:
        for scope in m.get("scope", []) or []:
            pref = _normalize_scope_prefix(scope)
            depth = pref.count("/")  # deeper dir = more specific
            candidates.append((pref, depth, m["id"]))
    candidates.sort(key=lambda c: -c[1])

    result: dict[str, list[str]] = {}
    for page in pages:
        assigned_module = None
        for pref, _depth, mod_id in candidates:
            if not pref:
                continue
            if any(fp.startswith(pref) for fp in page.get("filePaths", []) or []):
                assigned_module = mod_id
                break
        if assigned_module:
            result.setdefault(assigned_module, []).append(page["id"])
    return result


def compute_module_hash(module_scopes: list, file_hashes: dict) -> str:
    """Aggregate hash over all files under a module's scope prefixes.

    Unlike compute_source_hash (exact file list), this hashes every file in
    the repo whose path starts with one of the module's scope prefixes.
    This is the "module-level" granularity for incremental updates: if no
    file under the module changed, all of its pages can be skipped at once.
    """
    if not module_scopes or not file_hashes:
        return ""
    prefixes = [_normalize_scope_prefix(s) for s in module_scopes]
    prefixes = [p for p in prefixes if p]
    if not prefixes:
        return ""
    combined = ""
    for fpath, fhash in file_hashes.items():
        if any(fpath.startswith(p) for p in prefixes):
            combined += fhash
    if not combined:
        return ""
    import hashlib
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def compute_content_hash(file_path: str) -> str:
    """SHA-256 of a page .md file content, first 16 hex chars."""
    import hashlib
    try:
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return ""


def compute_structure_hash(structure: dict) -> str:
    """Deterministic hash of the structure JSON (page ids + titles + filePaths)."""
    import hashlib
    parts = []
    for p in sorted(structure.get("pages", []), key=lambda x: x.get("id", "")):
        parts.append(p.get("id", ""))
        parts.append(p.get("title", ""))
        parts.append(",".join(sorted(p.get("filePaths") or [])))
    for s in sorted(structure.get("sections", []), key=lambda x: x.get("id", "")):
        parts.append(s.get("id", ""))
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def read_used_sources(output_dir: str, page_id: str, page_file: str) -> list:
    """Read a page's used_sources sidecar if it exists.

    Sidecar path: same directory as the page .md, filename `{page_id}.used_sources.json`.
    Returns a list of {path, symbol, lines} dicts, or empty list if no sidecar.
    """
    sidecar = os.path.join(os.path.dirname(os.path.join(output_dir, page_file)),
                           f"{page_id}.used_sources.json")
    if not os.path.isfile(sidecar):
        return []
    try:
        import json as _json
        with open(sidecar, "r", encoding="utf-8") as f:
            data = _json.load(f)
        return data.get("used_sources", [])
    except Exception:
        return []


def generate_meta_yaml(structure: dict, page_id_to_file: dict, scan_data: dict | None,
                       output_dir: str, modules_data: dict | None = None,
                       facts_hash: str = "", skill_version: str = "",
                       prompt_hash: str = "", cbm_commit: str = "",
                       cbm_version: str = "") -> None:
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
            # v2 fields
            "content_hash": compute_content_hash(os.path.join(output_dir, file_path)),
            "actual_used_sources": read_used_sources(output_dir, page_id, file_path),
            "manual_edit_hash": "",
        })

    # Module-level metadata: enables module-granularity incremental updates
    # (skip an entire module's pages at once when none of its files changed).
    # Only written when modules data is available (deep mode / multi-module).
    meta["modules"] = []
    if modules_data and modules_data.get("modules"):
        page_to_module = {}
        mod_to_pages: dict[str, list[str]] = assign_pages_to_modules(pages, modules_data["modules"])
        for mod_id, page_ids in mod_to_pages.items():
            for pid in page_ids:
                page_to_module[pid] = mod_id
        for m in modules_data["modules"]:
            mod_hash = compute_module_hash(m.get("scope", []), file_hashes)
            meta["modules"].append({
                "id": m["id"],
                "title": m.get("title", ""),
                "scope": m.get("scope", []),
                "module_hash": mod_hash,
                "pages": mod_to_pages.get(m["id"], []),
            })

    # Write meta.yaml (YAML format, v2)
    meta_path = os.path.join(output_dir, "meta.yaml")
    struct_hash = compute_structure_hash(structure)
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write("# wiki 产物元数据 (schema v2)，用于增量更新\n")
        f.write(f"# 生成时间: {meta['generated_at']}\n")
        f.write(f"# 仓库: {meta['repo_path']}\n")
        f.write(f"# Git Hash: {meta['git_hash']}\n")
        f.write("\n")
        # Backward-compatible top-level fields (old readers look here)
        f.write(f"schema_version: 2\n")
        f.write(f"repo_path: \"{meta['repo_path']}\"\n")
        f.write(f"git_hash: \"{meta['git_hash']}\"\n")
        f.write(f"generated_at: \"{meta['generated_at']}\"\n")
        f.write("\n")
        # v2 repository section
        f.write("repository:\n")
        f.write(f"  path: \"{meta['repo_path']}\"\n")
        f.write(f"  branch: \"{(scan_data or {}).get('branch', '')}\"\n")
        f.write(f"  git_commit: \"{meta['git_hash']}\"\n")
        f.write(f"  dirty: {(scan_data or {}).get('dirty', False)}\n")
        f.write("\n")
        # v2 generator section
        f.write("generator:\n")
        f.write(f"  skill_version: \"{skill_version}\"\n")
        f.write(f"  prompt_hash: \"{prompt_hash}\"\n")
        f.write(f"  facts_hash: \"{facts_hash}\"\n")
        f.write(f"  structure_hash: \"{struct_hash}\"\n")
        if cbm_commit:
            f.write(f"  cbm_commit: \"{cbm_commit}\"\n")
        if cbm_version:
            f.write(f"  cbm_version: \"{cbm_version}\"\n")
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
            f.write(f"    content_hash: \"{p.get('content_hash', '')}\"\n")
            f.write(f"    manual_edit_hash: \"{p.get('manual_edit_hash', '')}\"\n")
            used = p.get("actual_used_sources") or []
            if used:
                f.write(f"    actual_used_sources:\n")
                for us in used:
                    f.write(f"      - path: \"{us.get('path', '')}\"\n")
                    if us.get("symbol"):
                        f.write(f"        symbol: \"{us['symbol']}\"\n")
                    if us.get("lines"):
                        f.write(f"        lines: {us['lines']}\n")
            else:
                f.write(f"    actual_used_sources: []\n")
        if meta["modules"]:
            f.write("\nmodules:\n")
            for m in meta["modules"]:
                f.write(f"  - id: \"{m['id']}\"\n")
                f.write(f"    title: \"{m['title']}\"\n")
                f.write(f"    scope:\n")
                for sc in m["scope"]:
                    f.write(f"      - \"{sc}\"\n")
                f.write(f"    module_hash: \"{m['module_hash']}\"\n")
                f.write(f"    pages:\n")
                for pid in m["pages"]:
                    f.write(f"      - \"{pid}\"\n")

    print(f"Generated meta.yaml at {meta_path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export wiki structure + pages to docs/wiki/")
    parser.add_argument("structure", help="Path to structure.json (from parse_structure.py)")
    parser.add_argument("pages_dir", nargs="?", default=None, help="Directory containing <page_id>.md content files (optional, not used in --overview-only mode)")
    parser.add_argument("--output", "-o", default="docs/wiki", help="Output directory (default: docs/wiki)")
    parser.add_argument("--scan", "-s", default=None, help="Path to scan.json from scan_repo.py (for meta.yaml generation)")
    parser.add_argument("--modules", "-m", default=None, help="Path to modules.json from scan_modules.py (enables module-level incremental updates)")
    parser.add_argument("--incremental", "-i", action="store_true", help="Only regenerate pages whose source files have changed")
    parser.add_argument("--overview-only", action="store_true", help="Only generate overview page and meta.yaml (skip other pages)")
    parser.add_argument("--facts", default=None, help="Path to wiki_facts.json from build_facts.py (enables facts_hash in meta v2)")
    parser.add_argument("--skill-version", default="", help="Skill version string for meta v2 generator section")
    parser.add_argument("--prompt-hash", default="", help="Prompt template hash for meta v2 generator section")
    args = parser.parse_args()

    with open(args.structure, "r", encoding="utf-8") as f:
        structure = json.load(f)

    # Load scan data if provided
    scan_data = None
    if args.scan and os.path.isfile(args.scan):
        with open(args.scan, "r", encoding="utf-8") as f:
            scan_data = json.load(f)

    # Load module tree if provided (deep mode / multi-module projects)
    modules_data = None
    if args.modules and os.path.isfile(args.modules):
        try:
            with open(args.modules, "r", encoding="utf-8") as f:
                modules_data = json.load(f)
        except Exception as e:
            print(f"Warning: failed to load modules file {args.modules}: {e}", file=sys.stderr)

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
            # page_dir already uses forward slashes; keep them so the value is
            # safe for Markdown links / meta.yaml (Python open() accepts "/" too).
            page_id_to_file[page["id"]] = f"{page_dir}/{filename}" if page_dir else filename

    # Load facts data if provided (for meta v2 facts_hash and optional CBM provenance)
    facts_hash = ""
    cbm_commit = ""
    cbm_version = ""
    if args.facts and os.path.isfile(args.facts):
        try:
            with open(args.facts, "r", encoding="utf-8") as f:
                facts_data = json.load(f)
            facts_hash = facts_data.get("facts_hash", "")
            graph_meta = facts_data.get("graph")
            if isinstance(graph_meta, dict):
                cbm_commit = graph_meta.get("cbm_commit", "")
                cbm_version = graph_meta.get("cbm_version", "")
        except Exception as e:
            print(f"Warning: failed to load facts file {args.facts}: {e}", file=sys.stderr)

    written = export_wiki(structure, args.pages_dir or "", args.output, scan_data, args.incremental, args.overview_only, modules_data)
    print(f"Written {len(written)} files to {args.output}:", file=sys.stderr)
    for fname in written:
        print(f"  - {fname}", file=sys.stderr)

    # Generate meta.yaml for incremental update (v2 format)
    generate_meta_yaml(structure, page_id_to_file, scan_data, args.output, modules_data,
                       facts_hash=facts_hash, skill_version=args.skill_version,
                       prompt_hash=args.prompt_hash, cbm_commit=cbm_commit,
                       cbm_version=cbm_version)


if __name__ == "__main__":
    main()
