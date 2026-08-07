#!/usr/bin/env python3
"""Parse a wiki structure XML string into a JSON file.

Takes the raw LLM output (which may have markdown fences or extra text),
extracts <wiki_structure>...</wiki_structure>, and parses it into a
structured JSON with pages and sections.

Usage:
    python3 parse_structure.py <xml_file_or_string> [--output <structure.json>]

If the argument is a file path, reads from it; otherwise treats it as raw XML.
If --output is omitted, prints JSON to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from xml.etree import ElementTree as ET


def extract_xml(text: str) -> str:
    """Extract <wiki_structure>...</wiki_structure> from raw text."""
    # Strip markdown code fences
    text = re.sub(r"^```(?:xml)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text.strip(), flags=re.MULTILINE)

    match = re.search(r"<wiki_structure>[\s\S]*?</wiki_structure>", text, re.MULTILINE)
    if not match:
        # Try without closing tag (partial output)
        match = re.search(r"<wiki_structure>[\s\S]*", text, re.MULTILINE)
        if not match:
            raise ValueError("No <wiki_structure> XML found in input")
    return match.group(0)


def parse_structure(xml_text: str) -> dict:
    """Parse wiki structure XML into a dict with title, description, pages, sections."""
    xml_text = xml_text.strip()

    # Remove control characters that break XML parsing
    xml_text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", xml_text)

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"Warning: XML parse error: {e}", file=sys.stderr)
        print("Attempting regex-based fallback parsing...", file=sys.stderr)
        return parse_structure_fallback(xml_text)

    title = (root.findtext("title") or "").strip()
    description = (root.findtext("description") or "").strip()

    pages = []
    pages_el = root.find("pages")
    if pages_el is not None:
        for page_el in pages_el.findall("page"):
            page = {
                "id": page_el.get("id") or f"page-{len(pages) + 1}",
                "title": (page_el.findtext("title") or "").strip(),
                "description": (page_el.findtext("description") or "").strip(),
                "importance": _normalize_importance(page_el.findtext("importance")),
                "filePaths": [fp.text.strip() for fp in page_el.findall("relevant_files/file_path") if fp.text],
                "relatedPages": [r.text.strip() for r in page_el.findall("related_pages/related") if r.text],
                "parentSection": (page_el.findtext("parent_section") or "").strip(),
            }
            pages.append(page)

    sections = []
    root_section_ids = []
    sections_el = root.find("sections")
    if sections_el is not None:
        for section_el in sections_el.findall("section"):
            section_id = section_el.get("id") or f"section-{len(sections) + 1}"
            section = {
                "id": section_id,
                "title": (section_el.findtext("title") or "").strip(),
                "pages": [pr.text.strip() for pr in section_el.findall("pages/page_ref") if pr.text],
                "subsections": [sr.text.strip() for sr in section_el.findall("subsections/section_ref") if sr.text],
            }
            sections.append(section)

        # Determine root sections (not referenced by any other section)
        all_subsection_refs = set()
        for s in sections:
            for sub in s.get("subsections") or []:
                all_subsection_refs.add(sub)
        root_section_ids = [s["id"] for s in sections if s["id"] not in all_subsection_refs]

    return {
        "title": title,
        "description": description,
        "pages": pages,
        "sections": sections,
        "rootSections": root_section_ids,
    }


def _normalize_importance(value: str | None) -> str:
    if not value:
        return "medium"
    v = value.strip().lower()
    if v in ("high", "medium", "low"):
        return v
    return "medium"


def parse_structure_fallback(xml_text: str) -> dict:
    """Regex-based fallback when XML parsing fails."""
    title_m = re.search(r"<title>(.*?)</title>", xml_text, re.DOTALL)
    desc_m = re.search(r"<description>(.*?)</description>", xml_text, re.DOTALL)

    pages = []
    for page_m in re.finditer(r'<page\s+id="([^"]*)"[^>]*>(.*?)</page>', xml_text, re.DOTALL):
        page_body = page_m.group(2)
        p_title_m = re.search(r"<title>(.*?)</title>", page_body, re.DOTALL)
        p_desc_m = re.search(r"<description>(.*?)</description>", page_body, re.DOTALL)
        p_imp_m = re.search(r"<importance>(.*?)</importance>", page_body, re.DOTALL)
        file_paths = [m.group(1).strip() for m in re.finditer(r"<file_path>(.*?)</file_path>", page_body, re.DOTALL)]
        related = [m.group(1).strip() for m in re.finditer(r"<related>(.*?)</related>", page_body, re.DOTALL)]

        pages.append({
            "id": page_m.group(1),
            "title": p_title_m.group(1).strip() if p_title_m else "",
            "description": p_desc_m.group(1).strip() if p_desc_m else "",
            "importance": _normalize_importance(p_imp_m.group(1) if p_imp_m else None),
            "filePaths": file_paths,
            "relatedPages": related,
            "parentSection": "",
        })

    return {
        "title": title_m.group(1).strip() if title_m else "",
        "description": desc_m.group(1).strip() if desc_m else "",
        "pages": pages,
        "sections": [],
       "rootSections": [],
   }


def _create_fallback_sections(result: dict) -> dict:
    """Create sections based on page title keywords when XML has none.

    Falls back to importance-based grouping if keyword matching yields nothing.
    """
    pages = result.get("pages", [])
    if not pages:
        return result

    # Chinese and English keyword categories for common section types
    categories = [
        {"id": "overview", "title": "概览", "keywords": ["overview", "introduction", "about", "概览", "概述", "介绍", "简介", "关于"]},
        {"id": "architecture", "title": "系统架构", "keywords": ["architecture", "structure", "design", "system", "架构", "结构", "设计", "系统"]},
        {"id": "features", "title": "核心功能", "keywords": ["feature", "functionality", "core", "功能", "核心", "特性"]},
        {"id": "components", "title": "组件", "keywords": ["component", "module", "widget", "组件", "模块", "控件"]},
        {"id": "api", "title": "API 接口", "keywords": ["api", "endpoint", "service", "server", "接口", "服务", "端点"]},
        {"id": "data", "title": "数据流", "keywords": ["data", "flow", "pipeline", "storage", "数据", "流程", "管线", "存储"]},
        {"id": "models", "title": "模型集成", "keywords": ["model", "ai", "ml", "integration", "模型", "集成", "人工智能"]},
        {"id": "ui", "title": "用户界面", "keywords": ["ui", "interface", "frontend", "page", "界面", "前端", "页面"]},
        {"id": "setup", "title": "配置与部署", "keywords": ["setup", "config", "installation", "deploy", "配置", "安装", "部署", "基础设施"]},
    ]

    # Assign pages to categories
    clusters: dict[str, list] = {cat["id"]: [] for cat in categories}
    clusters["other"] = []

    for page in pages:
        title_lower = page.get("title", "").lower()
        assigned = False
        for cat in categories:
            if any(kw in title_lower for kw in cat["keywords"]):
                clusters[cat["id"]].append(page)
                assigned = True
                break
        if not assigned:
            clusters["other"].append(page)

    # Build sections from non-empty clusters
    sections = []
    root_section_ids = []
    cat_list = categories + [{"id": "other", "title": "其他"}]
    for cat in cat_list:
        cat_pages = clusters.get(cat["id"], [])
        if cat_pages:
            section_id = f"section-{cat['id']}"
            sections.append({
                "id": section_id,
                "title": cat["title"],
                "pages": [p["id"] for p in cat_pages],
                "subsections": [],
            })
            root_section_ids.append(section_id)
            for p in cat_pages:
                p["parentSection"] = section_id

    # Ultimate fallback: importance-based grouping
    if not sections:
        for imp, title in [("high", "核心组件"), ("medium", "关键功能"), ("low", "补充信息")]:
            imp_pages = [p for p in pages if p.get("importance") == imp]
            if imp_pages:
                section_id = f"section-{imp}"
                sections.append({
                    "id": section_id,
                    "title": title,
                    "pages": [p["id"] for p in imp_pages],
                    "subsections": [],
                })
                root_section_ids.append(section_id)
                for p in imp_pages:
                    p["parentSection"] = section_id

    result["sections"] = sections
    result["rootSections"] = root_section_ids
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse wiki structure XML into JSON")
    parser.add_argument("input", help="Path to XML file, or raw XML string")
    parser.add_argument("--output", "-o", default=None, help="Output JSON file path (default: stdout)")
    args = parser.parse_args()

    # Read input
    if args.input.startswith("<") or "<wiki_structure>" in args.input:
        xml_text = args.input
    else:
        with open(args.input, "r", encoding="utf-8") as f:
            xml_text = f.read()

    xml = extract_xml(xml_text)
    result = parse_structure(xml)

    # If no sections found, create fallback sections based on page title keywords
    if not result.get("sections") or not result.get("rootSections"):
        result = _create_fallback_sections(result)

    if args.output:
        # Ensure parent directory exists (e.g. docs/tmp/ may not have been
        # created by the caller); avoids FileNotFoundError on Windows/Unix.
        out_dir = os.path.dirname(os.path.abspath(args.output))
        os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
