#!/usr/bin/env python3
"""Scan a repository for API entry points with language-aware classification.

Replaces the old "all regexes on all files" approach with per-language
dispatch, comment/string stripping, Spring class+method path merging, and
discriminated entry types:

  inbound_http         -- Spring/FastAPI/Express/Gin/.NET controllers
  outbound_http_client -- @FeignClient and similar outbound HTTP declarations
  message_consumer     -- @RabbitListener / @KafkaListener / @JmsListener / ...
  message_producer     -- rabbitTemplate.send / kafkaTemplate.send / ...
  scheduled_job        -- @Scheduled / Celery @task / node-cron / ...
  event_listener       -- @EventListener / EventEmitter.on / ...

Output JSON keeps backward-compatible `api_entries` (inbound_http only) and
adds `entries` (all types), `controllers`, `summary.by_type`, `scan_warnings`.

Usage:
    python3 scan_api_entries.py <repo_path> [--output <out.json>]
        [--scan <scan.json>] [--types inbound_http,scheduled_job,...]

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

# --------------------------------------------------------------------------- #
# Excluded dirs (kept in sync with scan_repo.py; standalone-safe)
# --------------------------------------------------------------------------- #
_EXCLUDED_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", "node_modules", ".venv",
    "venv", ".idea", ".vscode", "dist", "build", ".next", "target",
    ".eggs", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
}

_SCAN_EXTENSIONS = (".py", ".java", ".ts", ".js", ".go", ".cs", ".kt", ".scala", ".rb")

# Language detection by extension.
_LANG_MAP = {
    ".java": "java", ".kt": "java", ".scala": "java",
    ".py": "python",
    ".ts": "javascript", ".js": "javascript",
    ".go": "go",
    ".cs": "csharp",
    ".rb": "ruby",
}


# --------------------------------------------------------------------------- #
# Comment / string stripping (line-number-preserving)
# --------------------------------------------------------------------------- #
def strip_comments(lines: list[str], lang: str) -> list[str]:
    """Return a copy of *lines* with comments and string literals blanked out.

    Line numbers are preserved by replacing stripped characters with spaces.
    This prevents annotation examples inside Javadoc, Python docstrings, and
    JS template literals from being matched as real API entries.
    """
    result = list(lines)
    in_block = False  # /* ... */ (Java/JS/C#)
    for i, line in enumerate(result):
        original = line
        stripped = list(line)
        j = 0
        out = []
        while j < len(line):
            ch = line[j]
            pair = line[j:j + 2]

            if in_block:
                if pair == "*/":
                    in_block = False
                    out.extend("  ")
                    j += 2
                    continue
                out.append(" " if ch != "\n" else ch)
                j += 1
                continue

            # Not in block comment
            if lang in ("java", "javascript", "csharp") and pair == "//":
                # Rest of line is a comment
                out.extend(" " * (len(line) - j))
                break

            if lang in ("java", "javascript", "csharp") and pair == "/*":
                in_block = True
                out.extend("  ")
                j += 2
                continue

            if lang == "python" and ch == "#":
                out.extend(" " * (len(line) - j))
                break

            # String literals: skip their content but keep delimiters.
            # We only need to blank the *content* so annotation-like text
            # inside strings doesn't match. The delimiter char stays.
            if ch in ('"', "'"):
                quote = ch
                out.append(ch)
                j += 1
                while j < len(line):
                    if line[j] == "\\" and j + 1 < len(line):
                        out.extend("  ")
                        j += 2
                        continue
                    if line[j] == quote:
                        out.append(quote)
                        j += 1
                        break
                    out.append(" ")
                    j += 1
                continue

            # Backtick template literals (JS/TS)
            if lang == "javascript" and ch == "`":
                out.append("`")
                j += 1
                while j < len(line):
                    if line[j] == "\\" and j + 1 < len(line):
                        out.extend("  ")
                        j += 2
                        continue
                    if line[j] == "`":
                        out.append("`")
                        j += 1
                        break
                    out.append(" ")
                    j += 1
                continue

            out.append(ch)
            j += 1

        result[i] = "".join(out)
    return result


# --------------------------------------------------------------------------- #
# Per-language pattern definitions
# Each pattern: (regex, entry_type, framework, extract_fn)
# extract_fn(line_match, full_lines, line_idx) -> dict with keys like
#   method, route, class_path, annotation, symbol
# --------------------------------------------------------------------------- #

def _extract_http_method_from_annotation(ann: str) -> str:
    """@GetMapping -> GET, @PostMapping -> POST, etc."""
    m = re.match(r'@(?:Request)?(?:Get|Post|Put|Delete|Patch)Mapping', ann, re.I)
    if m:
        kw = re.search(r'(Get|Post|Put|Delete|Patch|Request)', ann, re.I)
        if kw:
            return kw.group(1).upper().replace("REQUEST", "ANY")
    return "ANY"


def _extract_route(text: str, ann: str) -> str:
    """Extract the first quoted path from annotation arguments."""
    # Try value=, path=, or bare quoted string
    for pat in (r'(?:value|path)\s*=\s*"([^"]+)"', r'(?:value|path)\s*=\s*\'([^\']+)\'',
                r'"(/[^"]+)"', r"'(/[^']+)'", r'"([^"]+)"', r"'([^']+)'"):
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return ""


def _find_enclosing_symbol(lines: list[str], idx: int) -> str:
    """Best-effort: scan backwards to find class/method name."""
    class_name = ""
    for i in range(idx, max(idx - 50, -1), -1):
        if i >= len(lines):
            continue
        m = re.search(r'\b(?:class|interface|enum|struct|record)\s+(\w+)', lines[i])
        if m and not class_name:
            class_name = m.group(1)
            break
    # Also try to find the method on the current or next line
    method_name = ""
    for i in range(idx, min(idx + 5, len(lines))):
        m = re.search(r'\b(?:public|private|protected)?\s*(?:\w+[<>.]\s*)?(\w+)\s*\(', lines[i])
        if m:
            method_name = m.group(1)
            break
    if class_name and method_name:
        return f"{class_name}#{method_name}"
    return class_name or method_name


# --- Java patterns ---
_JAVA_PATTERNS = [
    # Spring inbound HTTP: @GetMapping/@PostMapping/... with or without path
    (re.compile(r'@(?:Request|Get|Post|Put|Delete|Patch)Mapping\b', re.I),
     "inbound_http", "spring"),
    # Feign client
    (re.compile(r'@FeignClient\b', re.I),
     "outbound_http_client", "spring-feign"),
    # MQ consumers
    (re.compile(r'@(?:Rabbit|Kafka|Jms|Stream|Sqs)Listener\b', re.I),
     "message_consumer", "spring-mq"),
    # MQ producers (method calls, not annotations)
    (re.compile(r'\b(?:rabbitTemplate|kafkaTemplate|jmsTemplate|amqpTemplate)\.(?:convertAndSend|send|convertSendAndReceive)\b'),
     "message_producer", "spring-mq"),
    (re.compile(r'\b(?:applicationEventPublisher|eventPublisher|eventBus)\.publishEvent\b', re.I),
     "message_producer", "spring-event"),
    # Scheduled
    (re.compile(r'@Scheduled\b', re.I),
     "scheduled_job", "spring-scheduled"),
    # Event listener (Spring)
    (re.compile(r'@EventListener\b', re.I),
     "event_listener", "spring-event"),
]

# --- Python patterns ---
_PYTHON_PATTERNS = [
    # FastAPI / Flask: @app.get("/path"), @router.post(...)
    (re.compile(r'@(?:app|router|api)\.(get|post|put|delete|patch)\s*\(', re.I),
     "inbound_http", "fastapi"),
    # Django URL patterns
    (re.compile(r'\bpath\s*\(\s*["\']([^"\']+)["\']', re.I),
     "inbound_http", "django"),
    # Celery tasks (only scheduled ones get classified as scheduled_job;
    # plain @task is event_listener equivalent for now)
    (re.compile(r'@(?:app|celery)\.task\b|@shared_task\b', re.I),
     "scheduled_job", "celery"),
    # Pika / Kafka producer
    (re.compile(r'\b(?:channel|connection)\.(?:basic_publish|publish)\b'),
     "message_producer", "python-mq"),
    (re.compile(r'\bproducer\.send\b'),
     "message_producer", "python-mq"),
]

# --- JavaScript/TypeScript patterns ---
_JS_PATTERNS = [
    # Express: app.get("/path", ...), router.post(...)
    (re.compile(r'\b(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', re.I),
     "inbound_http", "express"),
    # NestJS: @Get("/path"), @Post(...)
    (re.compile(r'@(?:Get|Post|Put|Delete|Patch)\s*\(', re.I),
     "inbound_http", "nestjs"),
    # EventEmitter
    (re.compile(r'\b(?:EventEmitter|emitter|eventBus)\.on\s*\(\s*["\']', re.I),
     "event_listener", "node-event"),
    # BullMQ / node-cron
    (re.compile(r'\b(?:cron|schedule)\s*\(', re.I),
     "scheduled_job", "node-cron"),
    # Channel publish (AMQP)
    (re.compile(r'\bchannel\.publish\s*\('),
     "message_producer", "node-amqp"),
]

# --- Go patterns ---
_GO_PATTERNS = [
    # Gin: r.GET("/path", ...), router.POST(...)
    (re.compile(r'\b(?:r|router|engine|api|mux)\.(GET|POST|PUT|DELETE|PATCH|Handle|HandleFunc)\s*\(\s*["\']([^"\']+)["\']', re.I),
     "inbound_http", "gin"),
    # net/http
    (re.compile(r'\bhttp\.HandleFunc\s*\(\s*["\']([^"\']+)["\']', re.I),
     "inbound_http", "nethttp"),
]

# --- C# patterns ---
_CSHARP_PATTERNS = [
    (re.compile(r'\[(?:HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch)\b', re.I),
     "inbound_http", "dotnet"),
    (re.compile(r'\[Route\s*\(', re.I),
     "inbound_http", "dotnet"),
]

# --- Ruby patterns ---
_RUBY_PATTERNS = [
    (re.compile(r'\b(?:get|post|put|delete|patch)\s+["\']([^"\']+)["\']\s*(?:=>|,)', re.I),
     "inbound_http", "rails"),
]

_LANG_PATTERNS = {
    "java": _JAVA_PATTERNS,
    "python": _PYTHON_PATTERNS,
    "javascript": _JS_PATTERNS,
    "go": _GO_PATTERNS,
    "csharp": _CSHARP_PATTERNS,
    "ruby": _RUBY_PATTERNS,
}


# --------------------------------------------------------------------------- #
# Spring class-level path merging
# --------------------------------------------------------------------------- #
def _find_spring_class_path(lines: list[str], method_idx: int) -> str:
    """Scan backwards from method line to find @RequestMapping("/api") on class."""
    for i in range(method_idx, max(method_idx - 80, -1), -1):
        if i >= len(lines):
            continue
        line = lines[i].strip()
        # Class-level @RequestMapping with path
        if re.search(r'@(?:Rest)?Controller\b', line, re.I):
            # Found controller annotation, now look for @RequestMapping nearby
            for j in range(i, min(i + 10, len(lines))):
                m = re.search(r'@RequestMapping\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?["\']([^"\']+)["\']',
                              lines[j])
                if m:
                    return m.group(1)
            return ""
    return ""


def _join_paths(class_path: str, method_path: str) -> str:
    """Join Spring class-level and method-level paths."""
    if not class_path and not method_path:
        return ""
    if not class_path:
        return method_path
    if not method_path:
        return class_path
    cp = class_path.rstrip("/")
    mp = method_path.lstrip("/")
    return f"{cp}/{mp}"


# --------------------------------------------------------------------------- #
# Main scan
# --------------------------------------------------------------------------- #
def scan_api_entries(repo_path: str, scan_data: dict | None = None,
                     type_filter: list[str] | None = None) -> dict:
    repo_path = os.path.abspath(repo_path)
    if not os.path.isdir(repo_path):
        print(f"Error: directory not found: {repo_path}", file=sys.stderr)
        sys.exit(1)

    # Build file list: reuse scan_data if provided, else walk
    scan_files: list[str] | None = None
    if scan_data and isinstance(scan_data.get("file_tree"), str):
        scan_files = [ln for ln in scan_data["file_tree"].splitlines() if ln.strip()]

    entries: list[dict] = []
    controllers: list[dict] = []
    warnings: list[str] = []
    languages_seen: set[str] = set()

    if scan_files is None:
        scan_files = []
        for root, dirs, fnames in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS]
            for fname in sorted(fnames):
                if fname.endswith(_SCAN_EXTENSIONS):
                    rel = os.path.relpath(os.path.join(root, fname), repo_path)
                    scan_files.append(rel.replace(os.sep, "/"))

    for rel_path in scan_files:
        ext = os.path.splitext(rel_path)[1].lower()
        lang = _LANG_MAP.get(ext)
        if not lang:
            continue
        languages_seen.add(lang)
        patterns = _LANG_PATTERNS.get(lang, [])

        abs_path = os.path.join(repo_path, rel_path)
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                raw_lines = f.readlines()
        except Exception:
            continue

        clean_lines = strip_comments(raw_lines, lang)

        # Detect Spring controller class declarations (for controllers list)
        if lang == "java":
            for i, line in enumerate(clean_lines, 1):
                if re.search(r'@(?:Rest)?Controller\b', line):
                    class_m = re.search(r'\b(?:class|interface)\s+(\w+)', "".join(clean_lines[i-1:i+5]))
                    controllers.append({
                        "file": rel_path,
                        "line": i,
                        "framework": "spring-controller",
                        "class": class_m.group(1) if class_m else "",
                    })

        for i, line in enumerate(clean_lines):
            line_num = i + 1
            raw_line = raw_lines[i] if i < len(raw_lines) else line
            for regex, entry_type, framework in patterns:
                m = regex.search(line)
                if not m:
                    continue

                # Type filter
                if type_filter and entry_type not in type_filter:
                    break

                # Skip class-level Spring annotations (they're path prefixes,
                # not endpoints). Check if a class/interface/enum declaration
                # follows within the next few lines.
                if lang == "java" and entry_type == "inbound_http":
                    context = "".join(clean_lines[i:i + 5])
                    if re.search(r'\b(?:class|interface|enum)\s+\w+', context):
                        continue

                entry: dict = {
                    "type": entry_type,
                    "file": rel_path,
                    "line": line_num,
                    "framework": framework,
                }

                # Extract HTTP-specific fields.
                # IMPORTANT: use raw_line (not stripped) for route extraction,
                # because strip_comments blanks string-literal contents.
                if entry_type == "inbound_http":
                    if lang == "java":
                        ann_text = raw_line.strip()
                        entry["annotation"] = ann_text.split("(")[0].strip()
                        entry["method"] = _extract_http_method_from_annotation(entry["annotation"])
                        route = _extract_route(raw_line, entry["annotation"])
                        class_path = ""
                        if route:
                            class_path = _find_spring_class_path(raw_lines, i)
                        elif framework == "spring":
                            # @GetMapping without path — still get class-level prefix
                            class_path = _find_spring_class_path(raw_lines, i)
                        entry["class_path"] = class_path
                        entry["route"] = _join_paths(class_path, route)
                    elif lang == "python" and framework == "fastapi":
                        entry["method"] = m.group(1).upper() if m.lastindex else "ANY"
                        entry["route"] = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
                    elif lang == "python" and framework == "django":
                        entry["method"] = "ANY"
                        entry["route"] = m.group(1) if m.lastindex else ""
                    elif lang == "javascript" and framework == "express":
                        entry["method"] = m.group(1).upper() if m.lastindex else "ANY"
                        entry["route"] = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
                    elif lang == "go":
                        entry["method"] = m.group(1).upper() if m.lastindex else "ANY"
                        entry["route"] = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
                    elif lang == "csharp":
                        ann = raw_line.strip().lstrip("[")
                        entry["annotation"] = ann.split("(")[0].strip()
                        kw = re.search(r'Http(Get|Post|Put|Delete|Patch)', entry["annotation"], re.I)
                        entry["method"] = kw.group(1).upper() if kw else "ANY"
                        rt = _extract_route(raw_line, entry["annotation"])
                        entry["route"] = rt
                    elif lang == "ruby":
                        entry["method"] = "ANY"
                        entry["route"] = m.group(1) if m.lastindex else ""

                # Extract MQ consumer queue/topic (use raw_line: stripped blanks strings)
                if entry_type == "message_consumer":
                    qm = re.search(r'(?:queues|topics|destination|value|name)\s*=\s*["\']([^"\']+)["\']', raw_line)
                    if qm:
                        entry["queue"] = qm.group(1)

                # Extract scheduled cron (use raw_line for same reason)
                if entry_type == "scheduled_job":
                    cm = re.search(r'cron\s*=\s*["\']([^"\']+)["\']', raw_line)
                    if cm:
                        entry["cron"] = cm.group(1)
                    elif lang == "python":
                        entry["schedule"] = "celery-task"

                # Symbol hint
                entry["symbol"] = _find_enclosing_symbol(clean_lines, i)

                entries.append(entry)
                break  # one match per line

    # Build backward-compatible api_entries (inbound_http only)
    api_entries = [e for e in entries if e["type"] == "inbound_http"]

    # Summary
    by_type: dict[str, int] = {}
    by_framework: dict[str, int] = {}
    for e in entries:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
        by_framework[e["framework"]] = by_framework.get(e["framework"], 0) + 1

    return {
        "entries": entries,
        "api_entries": api_entries,  # backward compat
        "controllers": controllers,
        "summary": {
            "total_entries": len(entries),
            "total_endpoints": len(api_entries),  # backward compat
            "total_controllers": len(controllers),
            "by_type": by_type,
            "by_framework": by_framework,
            "frameworks_detected": sorted(by_framework.keys()),  # backward compat
            "languages_scanned": sorted(languages_seen),
        },
        "scan_warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan a repo for API entry points with language-aware classification")
    parser.add_argument("repo_path", help="Path to the repository root")
    parser.add_argument("--output", "-o", default=None,
                        help="Output JSON file path (default: stdout)")
    parser.add_argument("--scan", "-s", default=None,
                        help="Path to scan.json from scan_repo.py (reuses file list)")
    parser.add_argument("--types", default=None,
                        help="Comma-separated entry types to include (default: all)")
    args = parser.parse_args()

    scan_data = None
    if args.scan and os.path.isfile(args.scan):
        try:
            with open(args.scan, "r", encoding="utf-8") as f:
                scan_data = json.load(f)
        except Exception as e:
            print(f"Warning: failed to read scan file {args.scan}: {e}", file=sys.stderr)

    type_filter = None
    if args.types:
        type_filter = [t.strip() for t in args.types.split(",") if t.strip()]

    result = scan_api_entries(args.repo_path, scan_data, type_filter)

    if args.output:
        out_dir = os.path.dirname(os.path.abspath(args.output))
        os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
