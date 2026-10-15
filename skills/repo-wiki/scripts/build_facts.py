#!/usr/bin/env python3
"""Build a unified, evidence-backed facts layer from scan outputs.

Merges scan_repo.json + scan_api_entries.json + scan_modules.json and an
optional CBM graph_facts.json into a
single wiki_facts.json where every claim carries a stable ID, a type
(observed / repository_rule / inferred), evidence pointers, and a
confidence score. Structure generation and page generation consume THIS
file instead of raw scan outputs, so key architectural conclusions are
defined once and traceable.

Fact types (Section 6.1 of the optimization plan):
  observed         -- directly from source or executable config
  repository_rule  -- from AGENTS.md / .ai/rules / CONTRIBUTING.md
  inferred         -- derived from multiple signals (carries confidence)
  planned          -- from design docs (not yet implemented in source)
  recommendation   -- a suggestion, not a current-state fact

Usage:
    python3 build_facts.py
        --scan docs/tmp/wiki_scan.json
        --api docs/tmp/wiki_api_entries.json
        --modules docs/tmp/wiki_modules.json
        [--graph .repo-wiki/graph_facts.json]
        [--output .repo-wiki/wiki_facts.json]
        [--repo <repo_path>]   (defaults to scan repo_path)

Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys


# --------------------------------------------------------------------------- #
# Fact ID helpers
# --------------------------------------------------------------------------- #
def _safe_id(s: str) -> str:
    """Make a string safe for use in a dot-separated fact ID."""
    return re.sub(r"[^a-zA-Z0-9._\-]", "_", s).strip("_")


def _fact_id(category: str, *parts: str) -> str:
    return _safe_id(".".join(["fact", category, *parts]))


# --------------------------------------------------------------------------- #
# Repository rules from AGENTS.md / .ai/rules / CONTRIBUTING.md
# --------------------------------------------------------------------------- #
_RULE_FILES = [
    "AGENTS.md", "CLAUDE.md", ".ai/rules", ".cursor/rules",
    "CONTRIBUTING.md", "CODE_OF_CONDUCT.md",
]


def _extract_rules(repo_path: str, file_tree: list[str]) -> list[dict]:
    """Read repository rule files and extract rule-like statements."""
    rules: list[dict] = []
    for rf in _RULE_FILES:
        # Check both root and one level deep
        candidates = [rf, f".ai/{rf}"] if not rf.startswith(".") else [rf]
        for cand in candidates:
            if cand in file_tree or any(f.endswith("/" + rf) for f in file_tree):
                full = os.path.join(repo_path, cand)
                if not os.path.isfile(full):
                    continue
                try:
                    with open(full, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception:
                    continue
                # Extract headings as rule summaries (best-effort)
                for m in re.finditer(r"^#{1,3}\s+(.+)$", content, re.M):
                    heading = m.group(1).strip()
                    rules.append({
                        "id": _fact_id("rule", _safe_id(rf), _safe_id(heading[:40])),
                        "type": "repository_rule",
                        "category": "repository_rule",
                        "value": heading,
                        "evidence": [{"source": cand, "signal": "heading"}],
                        "confidence": 1.0,
                    })
                break  # one match per rule file name
    return rules


# --------------------------------------------------------------------------- #
# Module facts
# --------------------------------------------------------------------------- #
def _module_facts(modules_data: dict | None) -> list[dict]:
    """Generate facts from scan_modules output."""
    if not modules_data or not modules_data.get("modules"):
        return []
    facts: list[dict] = []
    for m in modules_data["modules"]:
        mid = _safe_id(m.get("id", m.get("title", "unknown")))
        # Dependency facts
        deps = m.get("depends_on") or []
        if deps:
            facts.append({
                "id": _fact_id("module", mid, "depends_on"),
                "type": "observed",
                "category": "module_dependency",
                "value": deps,
                "evidence": m.get("dep_evidence", []),
                "confidence": 1.0,
            })
        # Runtime role
        role = m.get("runtime_role", "unknown")
        if role != "unknown":
            facts.append({
                "id": _fact_id("module", mid, "runtime_role"),
                "type": "observed",
                "category": "module_role",
                "value": role,
                "evidence": [{"source": "build_file", "signal": e}
                             for e in m.get("build_evidence", [])],
                "confidence": 1.0,
            })
        # Deployability
        if m.get("is_deployable"):
            facts.append({
                "id": _fact_id("module", mid, "is_deployable"),
                "type": "observed",
                "category": "module_deployability",
                "value": True,
                "evidence": [{"source": "build_file", "signal": e}
                             for e in m.get("build_evidence", ["unknown"])],
                "confidence": 1.0,
            })
        # Placeholder
        if m.get("is_placeholder"):
            facts.append({
                "id": _fact_id("module", mid, "is_placeholder"),
                "type": "observed",
                "category": "module_placeholder",
                "value": True,
                "evidence": [{"source": "file_count",
                              "signal": f"source={m.get('source_file_count',0)},test={m.get('test_file_count',0)}"}],
                "confidence": 1.0,
            })
        # Entry points
        for ep in m.get("entry_points") or []:
            facts.append({
                "id": _fact_id("module", mid, "entry_point", _safe_id(ep)),
                "type": "observed",
                "category": "module_entry_point",
                "value": ep,
                "evidence": [{"source": "source_scan", "signal": "startup_class_or_main"}],
                "confidence": 1.0,
            })
    return facts


# --------------------------------------------------------------------------- #
# Endpoint facts
# --------------------------------------------------------------------------- #
def _endpoint_facts(api_data: dict | None) -> list[dict]:
    """Generate facts from scan_api_entries output."""
    if not api_data:
        return []
    facts: list[dict] = []
    entries = api_data.get("entries") or api_data.get("api_entries") or []
    for e in entries:
        etype = e.get("type", "inbound_http")
        loc = f"{e.get('file','unknown')}:{e.get('line',0)}"
        fid = _fact_id("endpoint", _safe_id(etype), _safe_id(loc))
        value = {
            "type": etype,
            "framework": e.get("framework", ""),
        }
        if e.get("method"):
            value["method"] = e["method"]
        if e.get("route"):
            value["route"] = e["route"]
        if e.get("queue"):
            value["queue"] = e["queue"]
        if e.get("cron"):
            value["cron"] = e["cron"]
        if e.get("symbol"):
            value["symbol"] = e["symbol"]
        facts.append({
            "id": fid,
            "type": "observed",
            "category": f"endpoint_{etype}",
            "value": value,
            "evidence": [{"source": e.get("file", "unknown"), "signal": e.get("annotation", etype),
                          "line": e.get("line", 0)}],
            "confidence": 1.0,
        })
    return facts


# --------------------------------------------------------------------------- #
# Assertions (inferred facts about the architecture)
# --------------------------------------------------------------------------- #
def _build_assertions(modules_data: dict | None, api_data: dict | None,
                      scan_data: dict | None) -> list[dict]:
    """Generate high-level architectural assertions from observed facts."""
    assertions: list[dict] = []

    if modules_data and modules_data.get("modules"):
        mods = modules_data["modules"]
        deployable = [m for m in mods if m.get("is_deployable")]
        multi = modules_data.get("multi_module", False)

        # Single deployable assertion
        if len(deployable) == 1:
            assertions.append({
                "id": "fact.assertion.single_deployable",
                "type": "inferred",
                "category": "architecture",
                "value": f"唯一部署物：{deployable[0].get('title', deployable[0].get('id', 'unknown'))}",
                "evidence": [
                    {"source": f"fact.module.{_safe_id(deployable[0].get('id',''))}.is_deployable"},
                    {"source": "scan_modules", "signal": f"{len(deployable)} deployable out of {len(mods)} modules"},
                ],
                "confidence": 0.95,
            })
        elif len(deployable) > 1:
            names = [m.get("title", m.get("id", "?")) for m in deployable]
            assertions.append({
                "id": "fact.assertion.multi_deployable",
                "type": "inferred",
                "category": "architecture",
                "value": f"多个可部署模块：{', '.join(names)}",
                "evidence": [{"source": "scan_modules", "signal": f"{len(deployable)} deployable modules"}],
                "confidence": 0.95,
            })

        # Multi-module vs single
        if multi:
            leaf_count = modules_data.get("leaf_count", 0)
            assertions.append({
                "id": "fact.assertion.multi_module",
                "type": "observed",
                "category": "architecture",
                "value": f"多模块项目（{modules_data.get('module_count', 0)} 模块，{leaf_count} 叶子模块，构建系统: {modules_data.get('build_system', 'unknown')}）",
                "evidence": [{"source": "scan_modules", "signal": modules_data.get("build_system", "")}],
                "confidence": 1.0,
            })

        # Placeholder modules
        placeholders = [m for m in mods if m.get("is_placeholder")]
        if placeholders:
            names = [m.get("title", m.get("id", "?")) for m in placeholders]
            assertions.append({
                "id": "fact.assertion.placeholder_modules",
                "type": "observed",
                "category": "architecture",
                "value": f"占位模块（无源码）：{', '.join(names)}",
                "evidence": [{"source": "scan_modules", "signal": f"{len(placeholders)} placeholder modules"}],
                "confidence": 1.0,
            })

    if api_data:
        by_type = (api_data.get("summary") or {}).get("by_type", {})
        if by_type:
            parts = [f"{k}={v}" for k, v in sorted(by_type.items())]
            assertions.append({
                "id": "fact.assertion.entry_point_summary",
                "type": "observed",
                "category": "endpoints",
                "value": f"入口类型分布：{', '.join(parts)}",
                "evidence": [{"source": "scan_api_entries", "signal": "summary.by_type"}],
                "confidence": 1.0,
            })

    if scan_data:
        mode = scan_data.get("scan_mode", "unknown")
        assertions.append({
            "id": "fact.assertion.scan_mode",
            "type": "observed",
            "category": "repository",
            "value": f"扫描模式：{mode}",
            "evidence": [{"source": "scan_repo", "signal": f"scan_mode={mode}"}],
            "confidence": 1.0,
        })

    return assertions


# --------------------------------------------------------------------------- #
# Conflict detection
# --------------------------------------------------------------------------- #
def _detect_conflicts(facts: list[dict]) -> list[dict]:
    """Detect facts with the same ID but different values."""
    by_id: dict[str, list[dict]] = {}
    for f in facts:
        by_id.setdefault(f["id"], []).append(f)
    conflicts: list[dict] = []
    for fid, group in by_id.items():
        if len(group) > 1:
            values = [json.dumps(f.get("value"), sort_keys=True) for f in group]
            if len(set(values)) > 1:
                conflicts.append({
                    "fact_id": fid,
                    "conflicting_values": [f.get("value") for f in group],
                    "evidence": [f.get("evidence") for f in group],
                })
    return conflicts


# --------------------------------------------------------------------------- #
# Facts hash (for meta v2)
# --------------------------------------------------------------------------- #
def compute_facts_hash(facts: list[dict]) -> str:
    """Compute a deterministic hash over all fact IDs + values."""
    # Sort by ID for determinism
    sorted_facts = sorted(facts, key=lambda f: f["id"])
    combined = ""
    for f in sorted_facts:
        combined += f["id"] + json.dumps(f.get("value"), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# Optional CBM graph facts
# --------------------------------------------------------------------------- #
def _valid_graph_fact(fact: dict) -> bool:
    """Graph facts are accepted only when every evidence item has file:line."""
    if not isinstance(fact, dict) or fact.get("source") != "graph":
        return False
    if not all(fact.get(key) is not None for key in ("id", "type", "category", "value")):
        return False
    evidence = fact.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return False
    for item in evidence:
        if not isinstance(item, dict):
            return False
        source = item.get("source")
        if not isinstance(source, str) or not source.strip():
            return False
        normalized_source = source.replace("\\", "/")
        if (
            os.path.isabs(source)
            or normalized_source.startswith("/")
            or re.match(r"^[A-Za-z]:/", normalized_source)
            or ".." in normalized_source.split("/")
        ):
            return False
        line = item.get("line")
        if not isinstance(line, int) or line <= 0:
            return False
    return True


def _merge_graph_facts(facts: list[dict], graph_data: dict | None) -> tuple[int, dict | None]:
    """Merge valid graph facts and return accepted count + optional metadata."""
    if (
        not isinstance(graph_data, dict)
        or graph_data.get("available") is not True
        or graph_data.get("degraded")
    ):
        return 0, None

    by_id = {fact["id"]: fact for fact in facts}
    accepted = 0
    for graph_fact in graph_data.get("facts") or []:
        if not _valid_graph_fact(graph_fact):
            continue
        accepted += 1
        existing = by_id.get(graph_fact["id"])
        if existing is None:
            facts.append(graph_fact)
            by_id[graph_fact["id"]] = graph_fact
            continue
        if json.dumps(existing.get("value"), sort_keys=True, ensure_ascii=False) == json.dumps(
            graph_fact.get("value"), sort_keys=True, ensure_ascii=False
        ):
            existing_evidence = existing.setdefault("evidence", [])
            for item in graph_fact.get("evidence") or []:
                if item not in existing_evidence:
                    existing_evidence.append(item)
            existing["corroborated_by"] = "graph"
        else:
            facts.append(graph_fact)

    if accepted == 0:
        return 0, None
    marker = graph_data.get("marker")
    if not isinstance(marker, dict):
        marker = {}
    metadata = {
        "cbm_commit": marker.get("commit", ""),
        "cbm_version": graph_data.get("cbm_version", marker.get("cbm_version", "")),
    }
    return accepted, metadata


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def build_facts(scan_data: dict | None, api_data: dict | None,
                modules_data: dict | None, repo_path: str | None = None,
                graph_data: dict | None = None) -> dict:
    """Build the unified facts layer from scan outputs."""
    if repo_path is None:
        repo_path = (scan_data or {}).get("repo_path", "")

    file_tree: list[str] = []
    if scan_data and isinstance(scan_data.get("file_tree"), str):
        file_tree = scan_data["file_tree"].splitlines()

    facts: list[dict] = []

    # 1. Module facts
    facts.extend(_module_facts(modules_data))

    # 2. Endpoint facts
    facts.extend(_endpoint_facts(api_data))

    # 3. Repository rules
    if repo_path and os.path.isdir(repo_path):
        facts.extend(_extract_rules(repo_path, file_tree))

    # 4. Assertions (inferred high-level facts)
    facts.extend(_build_assertions(modules_data, api_data, scan_data))

    # 5. Optional CBM graph facts
    graph_count, graph_metadata = _merge_graph_facts(facts, graph_data)

    # 6. Detect conflicts
    conflicts = _detect_conflicts(facts)
    if conflicts:
        for c in conflicts:
            print(f"Warning: conflicting facts for {c['fact_id']}", file=sys.stderr)

    # 7. Build top-level structure
    result = {
        "schema_version": 1,
        "repository": {
            "path": repo_path,
            "branch": (scan_data or {}).get("branch", ""),
            "git_commit": (scan_data or {}).get("git_commit", ""),
            "dirty": (scan_data or {}).get("dirty", False),
        },
        "build": {
            "system": (modules_data or {}).get("build_system"),
            "multi_module": (modules_data or {}).get("multi_module", False),
        },
        "scan_mode": (scan_data or {}).get("scan_mode", "unknown"),
        "facts": facts,
        "facts_hash": compute_facts_hash(facts),
        "conflicts": conflicts,
        "summary": {
            "total_facts": len(facts),
            "by_type": _count_by_key(facts, "type"),
            "by_category": _count_by_key(facts, "category"),
            "conflicts": len(conflicts),
        },
    }
    if graph_metadata:
        result["graph"] = graph_metadata
        result["summary"]["graph_facts"] = graph_count
    return result


def _count_by_key(facts: list[dict], key: str) -> dict:
    counts: dict[str, int] = {}
    for f in facts:
        v = f.get(key, "unknown")
        counts[v] = counts.get(v, 0) + 1
    return counts


def _load_json(path: str | None) -> dict | None:
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: failed to read {path}: {e}", file=sys.stderr)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build unified facts layer from scan outputs")
    parser.add_argument("--scan", required=True, help="Path to scan_repo.json")
    parser.add_argument("--api", default=None, help="Path to scan_api_entries.json")
    parser.add_argument("--modules", default=None, help="Path to scan_modules.json")
    parser.add_argument("--graph", default=None,
                        help="Optional graph_facts.json from extract_graph_facts.py")
    parser.add_argument("--output", "-o", default=".repo-wiki/wiki_facts.json",
                        help="Output path (default: .repo-wiki/wiki_facts.json)")
    parser.add_argument("--repo", default=None,
                        help="Repository path (defaults to scan repo_path)")
    args = parser.parse_args()

    scan_data = _load_json(args.scan)
    if not scan_data:
        print(f"Error: cannot read scan file {args.scan}", file=sys.stderr)
        sys.exit(1)

    api_data = _load_json(args.api)
    modules_data = _load_json(args.modules)
    graph_data = _load_json(args.graph)
    repo_path = args.repo or scan_data.get("repo_path", "")

    result = build_facts(scan_data, api_data, modules_data, repo_path, graph_data)

    out_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Written to {args.output}", file=sys.stderr)
    print(f"Facts: {result['summary']['total_facts']} "
          f"(by type: {result['summary']['by_type']})", file=sys.stderr)
    if result["conflicts"]:
        print(f"Conflicts: {len(result['conflicts'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
