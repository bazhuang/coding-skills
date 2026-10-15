#!/usr/bin/env python3
"""Extract optional, evidence-backed graph facts from codebase-memory-mcp.

This is repo-wiki step 2.7. CBM is an optional accuracy enhancement: user
opt-out, missing/old binaries, transport failures and query failures all
degrade without blocking the existing repo-wiki pipeline.

Only facts with repository-relative file and positive line evidence are
emitted. The script does not replace repo-wiki's regex scanners.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

CBM_BIN = "codebase-memory-mcp"
MIN_VERSION = (0, 9, 0)
VERSION_TIMEOUT = 30
QUERY_TIMEOUT = 300
INDEX_TIMEOUT = 1800
INDEX_MODE = "fast"
DEFAULT_OUTPUT = ".repo-wiki/graph_facts.json"
DEFAULT_MARKER = ".repo-wiki/cbm_index_state.json"
STALE_WARNING = "含未提交代码，图谱可能滞后"
CALL_CHAIN_CONFIDENCE = 0.9
HOTSPOT_CONFIDENCE = 1.0

_MAPPING_METHOD_NAMES = {
    "requestmapping", "getmapping", "postmapping", "putmapping",
    "deletemapping", "patchmapping",
}


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._\-]", "_", value).strip("_")


def _load_json(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _write_json(path: str, obj: dict) -> None:
    out_dir = os.path.dirname(os.path.abspath(path))
    os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _parse_version(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text or "")
    if not match:
        return None
    return tuple(int(match.group(i)) for i in range(1, 4))


def _norm_path(path: str) -> str:
    return os.path.normcase(path.replace("\\", "/").strip())


def _repo_relative(repo: str, path: str | None) -> str | None:
    """Return a forward-slash repo-relative path, rejecting paths outside repo."""
    if not path:
        return None
    repo_abs = os.path.realpath(os.path.abspath(repo))
    candidate = path if os.path.isabs(path) else os.path.join(repo_abs, path)
    path_abs = os.path.realpath(os.path.abspath(candidate))
    try:
        if os.path.normcase(os.path.commonpath([repo_abs, path_abs])) != os.path.normcase(repo_abs):
            return None
    except ValueError:
        return None
    return os.path.relpath(path_abs, repo_abs).replace("\\", "/")


def _same_repo_file(repo: str, candidate: str | None, expected: str) -> bool:
    relative = _repo_relative(repo, candidate)
    return relative is not None and _norm_path(relative) == _norm_path(expected)


def _normalize_route(route: str | None) -> str:
    if not route:
        return ""
    normalized = "/" + route.strip().strip("/")
    return "/" if normalized == "/" else normalized.rstrip("/")


def run_cbm(tool_args: list[str], timeout: int) -> dict | None:
    """Run one CBM CLI command and return a JSON object or None on failure."""
    argv = [CBM_BIN, "cli"] + tool_args
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Warning: cbm spawn/timeout failure ({tool_args[0]}): {exc}", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"Warning: cbm {tool_args[0]} exited {proc.returncode}: "
            f"{(proc.stderr or '').strip()[:200]}",
            file=sys.stderr,
        )
        return None
    try:
        data = json.loads(proc.stdout)
    except (json.JSONDecodeError, TypeError):
        print(f"Warning: cbm {tool_args[0]} returned non-JSON stdout", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print(f"Warning: cbm {tool_args[0]} returned non-object JSON", file=sys.stderr)
        return None
    return data


def run_version() -> str | None:
    try:
        proc = subprocess.run(
            [CBM_BIN, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=VERSION_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def detect_availability(no_cbm: bool) -> dict:
    if no_cbm:
        return {"available": False, "reason": "disabled_by_user"}
    if not shutil.which(CBM_BIN):
        return {"available": False, "reason": "not_installed"}
    version_output = run_version()
    if version_output is None:
        return {"available": False, "reason": "not_installed"}
    version = _parse_version(version_output)
    if version is None or version < MIN_VERSION:
        return {"available": False, "reason": "version_too_low"}
    return {"available": True, "cbm_version": ".".join(str(v) for v in version)}


def load_marker(path: str) -> dict | None:
    return _load_json(path)


def write_marker(path: str, marker: dict) -> None:
    _write_json(path, marker)


def ensure_fresh_index(
    requested_project: str,
    repo: str,
    git_hash: str,
    marker_path: str,
    cbm_version: str,
) -> tuple[str, dict, dict | None, str]:
    """Return status, coverage, marker and the actual CBM project name."""
    marker = load_marker(marker_path)
    if (
        marker
        and git_hash
        and marker.get("commit") == git_hash
        and marker.get("cbm_version") == cbm_version
        and marker.get("mode") == INDEX_MODE
    ):
        marker_request = marker.get("requested_project", marker.get("project"))
        if marker_request == requested_project and marker.get("project"):
            return "fresh", marker.get("coverage") or {}, marker, marker["project"]

    response = run_cbm(
        [
            "index_repository",
            "--repo-path", repo,
            "--mode", INDEX_MODE,
            "--name", requested_project,
        ],
        INDEX_TIMEOUT,
    )
    if response is None or response.get("error") or response.get("status") != "indexed":
        return "index_failed", {}, marker, requested_project

    actual_project = response.get("project") or requested_project
    coverage = {
        "skipped_count": response.get("skipped_count", 0),
        "excluded_dirs": (response.get("excluded") or {}).get("dirs", []),
    }
    marker = {
        "project": actual_project,
        "requested_project": requested_project,
        "commit": git_hash,
        "cbm_version": cbm_version,
        "indexed_at": datetime.now().isoformat(),
        "mode": INDEX_MODE,
        "coverage": coverage,
    }
    write_marker(marker_path, marker)
    return "reindexed", coverage, marker, actual_project


def _symbol_parts(symbol: str) -> tuple[str, str]:
    class_name, separator, method_name = symbol.replace("#", ".").partition(".")
    return (class_name, method_name) if separator else (class_name, "")


def _is_mapping_annotation(method_name: str) -> bool:
    return method_name.lower() in _MAPPING_METHOD_NAMES


def construct_qn(project: str, file_path: str, symbol: str) -> str | None:
    class_name, method_name = _symbol_parts(symbol)
    if not class_name or not method_name or _is_mapping_annotation(method_name):
        return None
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", file_path).replace("\\", "/").replace("/", ".")
    return f"{project}.{stem}.{class_name}.{method_name}"


def search_handler_qn(project: str, entry: dict, repo: str) -> str | None:
    """Resolve a handler Method using class, file, HTTP method and route."""
    symbol = entry.get("symbol") or ""
    class_name, method_name = _symbol_parts(symbol)
    if not class_name:
        return None
    pattern = f".*{re.escape(class_name)}\\..*$"
    response = run_cbm(
        [
            "search_graph", "--project", project,
            "--name-pattern", pattern,
            "--fields", '["route_path","route_method"]',
        ],
        QUERY_TIMEOUT,
    )
    if not response or response.get("error"):
        return None

    expected_route = _normalize_route(entry.get("route"))
    expected_method = str(entry.get("method") or "").upper()
    file_candidates: list[dict] = []
    route_candidates: list[dict] = []
    name_candidates: list[dict] = []
    for result in response.get("results") or []:
        if not isinstance(result, dict) or result.get("label") != "Method":
            continue
        if not _same_repo_file(repo, result.get("file_path"), entry.get("file", "")):
            continue
        file_candidates.append(result)

        result_route = _normalize_route(result.get("route_path"))
        result_method = str(result.get("route_method") or "").upper()
        route_matches = bool(expected_route and result_route == expected_route)
        method_matches = not expected_method or expected_method == "ANY" or result_method == expected_method
        if route_matches and method_matches:
            route_candidates.append(result)

        qualified_name = result.get("qualified_name") or ""
        if method_name and not _is_mapping_annotation(method_name) and qualified_name.endswith(
            f".{class_name}.{method_name}"
        ):
            name_candidates.append(result)

    candidates = route_candidates or name_candidates
    if len(candidates) == 1:
        return candidates[0].get("qualified_name")
    if not candidates and len(file_candidates) == 1:
        only = file_candidates[0]
        if only.get("route_path") or (
            method_name and not _is_mapping_annotation(method_name)
        ):
            return only.get("qualified_name")
    return None


def get_node_location(
    project: str,
    qualified_name: str,
    repo: str,
    cache: dict[str, tuple[str, int] | None],
) -> tuple[str, int] | None:
    if qualified_name in cache:
        return cache[qualified_name]
    response = run_cbm(
        ["get_code_snippet", "--project", project, "--qualified-name", qualified_name],
        QUERY_TIMEOUT,
    )
    location = None
    if response and not response.get("error"):
        relative = _repo_relative(repo, response.get("file_path"))
        line = response.get("start_line")
        if relative and isinstance(line, int) and line > 0:
            location = (relative, line)
    cache[qualified_name] = location
    return location


def _graph_fact(
    fact_id: str,
    category: str,
    value,
    evidence: list[dict],
    confidence: float,
) -> dict:
    return {
        "id": fact_id,
        "type": "observed",
        "category": category,
        "value": value,
        "evidence": evidence,
        "confidence": confidence,
        "source": "graph",
    }


def _walk_callees(callees: list[dict], accumulator: list[dict]) -> None:
    for callee in callees:
        if not isinstance(callee, dict) or not callee.get("qualified_name"):
            continue
        accumulator.append(
            {
                "name": callee.get("name", ""),
                "qualified_name": callee["qualified_name"],
                "hop": callee.get("hop", 1),
            }
        )
        _walk_callees(callee.get("callees") or [], accumulator)


def extract_hotspots(project: str, repo: str, errors: list[dict]) -> list[dict]:
    """Extract only architecture hotspots that can be tied to source lines."""
    response = run_cbm(
        ["get_architecture", "--project", project, "--aspects", '["overview"]'],
        QUERY_TIMEOUT,
    )
    if response is None or response.get("error"):
        errors.append({"class": "architecture", "reason": "query_failed"})
        return []

    facts: list[dict] = []
    location_cache: dict[str, tuple[str, int] | None] = {}
    for hotspot in (response.get("hotspots") or [])[:10]:
        if not isinstance(hotspot, dict) or not hotspot.get("qualified_name"):
            continue
        qualified_name = hotspot["qualified_name"]
        location = get_node_location(project, qualified_name, repo, location_cache)
        if not location:
            errors.append({"class": "hotspot", "entry": qualified_name, "reason": "missing_location"})
            continue
        source, line = location
        facts.append(
            _graph_fact(
                f"fact.graph.hotspot.{_safe_id(qualified_name)}",
                "graph_hotspot",
                {
                    "name": hotspot.get("name", ""),
                    "qualified_name": qualified_name,
                    "fan_in": hotspot.get("fan_in", 0),
                },
                [{"source": source, "signal": "cbm get_architecture hotspot", "line": line}],
                HOTSPOT_CONFIDENCE,
            )
        )
    return facts


def extract_call_chains(
    project: str,
    api_data: dict,
    topn: int,
    repo: str,
    errors: list[dict],
) -> list[dict]:
    entries = [
        entry
        for entry in (api_data.get("entries") or api_data.get("api_entries") or [])
        if isinstance(entry, dict) and entry.get("type", "inbound_http") == "inbound_http"
    ]
    facts: list[dict] = []
    location_cache: dict[str, tuple[str, int] | None] = {}
    for entry in entries[:topn]:
        file_path = entry.get("file", "")
        entry_line = entry.get("line", 0)
        symbol = entry.get("symbol") or ""
        entry_source = _repo_relative(repo, file_path)
        if not entry_source or not isinstance(entry_line, int) or entry_line <= 0:
            errors.append({"entry": symbol or file_path, "reason": "missing_entry_location"})
            continue

        qualified_name = construct_qn(project, entry_source, symbol)
        response = None
        if qualified_name:
            response = run_cbm(
                [
                    "trace_path", "--project", project,
                    "--function-name", qualified_name,
                    "--direction", "outbound",
                    "--depth", "3",
                ],
                QUERY_TIMEOUT,
            )

        if response is None or response.get("error"):
            qualified_name = search_handler_qn(project, {**entry, "file": entry_source}, repo)
            if qualified_name:
                response = run_cbm(
                    [
                        "trace_path", "--project", project,
                        "--function-name", qualified_name,
                        "--direction", "outbound",
                        "--depth", "3",
                    ],
                    QUERY_TIMEOUT,
                )

        if not qualified_name or response is None or response.get("error"):
            errors.append({"entry": symbol or file_path, "reason": "handler_not_resolved"})
            continue

        raw_hops: list[dict] = []
        _walk_callees(response.get("callees") or [], raw_hops)
        located_hops: list[dict] = []
        evidence = [
            {"source": entry_source, "signal": "cbm trace_path entry", "line": entry_line}
        ]
        for hop in raw_hops:
            location = get_node_location(project, hop["qualified_name"], repo, location_cache)
            if not location:
                errors.append(
                    {"entry": hop["qualified_name"], "reason": "callee_missing_location"}
                )
                continue
            source, line = location
            located_hop = dict(hop)
            located_hop["file"] = source
            located_hop["line"] = line
            located_hops.append(located_hop)
            evidence.append(
                {"source": source, "signal": "cbm get_code_snippet", "line": line}
            )

        if not located_hops:
            errors.append({"entry": qualified_name, "reason": "no_located_callees"})
            continue

        facts.append(
            _graph_fact(
                f"fact.graph.call_chain.{_safe_id(qualified_name)}",
                "graph_call_chain",
                {
                    "entry": symbol,
                    "entry_file": entry_source,
                    "entry_line": entry_line,
                    "entry_qualified_name": qualified_name,
                    "hops": located_hops,
                },
                evidence,
                CALL_CHAIN_CONFIDENCE,
            )
        )
    return facts


def validate_fact(fact: dict) -> bool:
    if not all(fact.get(key) is not None for key in ("id", "type", "category", "value")):
        return False
    evidence = fact.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return False
    for item in evidence:
        if not isinstance(item, dict) or not item.get("source"):
            return False
        if fact.get("source") == "graph":
            line = item.get("line")
            if not isinstance(line, int) or line <= 0:
                return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract optional graph facts from CBM")
    parser.add_argument("--repo", required=True, help="Repository absolute path")
    parser.add_argument("--scan", required=True, help="wiki_scan.json")
    parser.add_argument("--api", required=True, help="wiki_api_entries.json")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--no-cbm", action="store_true")
    parser.add_argument("--topn", type=int, default=10)
    parser.add_argument("--marker", default=DEFAULT_MARKER)
    parser.add_argument("--project-name", default=None)
    args = parser.parse_args(argv)

    scan_data = _load_json(args.scan)
    if scan_data is None:
        print(f"Error: cannot read scan file {args.scan}", file=sys.stderr)
        return 1
    api_data = _load_json(args.api)
    if api_data is None:
        print(f"Error: cannot read api entries file {args.api}", file=sys.stderr)
        return 1

    availability = detect_availability(args.no_cbm)
    if not availability["available"]:
        output = {"available": False, "reason": availability["reason"], "facts": []}
        _write_json(args.output, output)
        return 0

    requested_project = args.project_name or os.path.basename(os.path.abspath(args.repo))
    git_hash = scan_data.get("git_commit") or scan_data.get("git_hash") or ""
    status, coverage, marker, project = ensure_fresh_index(
        requested_project,
        args.repo,
        git_hash,
        args.marker,
        availability["cbm_version"],
    )
    if status == "index_failed":
        output = {
            "schema_version": 1,
            "available": True,
            "cbm_version": availability["cbm_version"],
            "project": project,
            "fresh": False,
            "reindexed": False,
            "degraded": True,
            "reason": "index_failed",
            "coverage": {"errors": [{"class": "index", "reason": "index_failed"}]},
            "facts": [],
            "marker": marker,
        }
        _write_json(args.output, output)
        return 0

    errors: list[dict] = []
    facts = extract_hotspots(project, args.repo, errors)
    facts.extend(extract_call_chains(project, api_data, args.topn, args.repo, errors))
    facts = [fact for fact in facts if validate_fact(fact)]
    if scan_data.get("dirty"):
        for fact in facts:
            fact["stale_warning"] = STALE_WARNING

    output = {
        "schema_version": 1,
        "available": True,
        "cbm_version": availability["cbm_version"],
        "project": project,
        "fresh": True,
        "reindexed": status == "reindexed",
        "degraded": False,
        "reason": None,
        "coverage": {**coverage, "errors": errors},
        "facts": facts,
        "marker": marker,
    }
    _write_json(args.output, output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
