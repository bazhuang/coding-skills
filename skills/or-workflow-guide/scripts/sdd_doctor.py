#!/usr/bin/env python3
"""Lightweight SDD artifact doctor.

Run from a project root:
  python3 skills/or-workflow-guide/scripts/sdd_doctor.py

The script intentionally uses only the Python standard library. It performs
basic presence and JSON-shape checks; stage-specific gates remain in each skill.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


AUTHORITATIVE_SPECS = [
    "ontology_schema.json",
    "requirements-baseline.json",
    "contracts/app-contract.yaml",
    "contracts/db-schema.sql",
]

DERIVED_VIEWS = [
    "brd.md",
    "app-design.md",
    "db-schema.md",
    "contracts/acceptance-tests.yaml",
]

JSON_ARTIFACTS = [
    "ontology_schema.json",
    "requirements-baseline.json",
    "traceability.json",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> tuple[bool, Any | str]:
    try:
        return True, json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report parse error to user
        return False, str(exc)


def report(level: str, message: str) -> None:
    print(f"[{level}] {message}")


def check_json_shape(rel: str, data: Any) -> list[str]:
    issues: list[str] = []
    if rel == "requirements-baseline.json":
        if not isinstance(data, dict):
            return ["requirements-baseline.json must be a JSON object"]
        if data.get("approved") is not True:
            issues.append("requirements-baseline.json approved is not true")
        requirements = data.get("requirements")
        if not isinstance(requirements, list) or not requirements:
            issues.append("requirements-baseline.json requirements[] is missing or empty")
        else:
            for req in requirements:
                if not isinstance(req, dict):
                    issues.append("requirements[] contains a non-object item")
                    continue
                if not req.get("id"):
                    issues.append("a requirement is missing id")
                if req.get("priority") == "MUST" and not req.get("acceptance_criteria"):
                    issues.append(f"{req.get('id', '<unknown>')} is MUST but lacks acceptance_criteria")
    elif rel == "traceability.json":
        if not isinstance(data, dict):
            return ["traceability.json must be a JSON object"]
        for key in ["objects", "rules", "sops", "requirements"]:
            if key not in data:
                issues.append(f"traceability.json missing {key}")
        if data.get("confidence") == "degraded":
            issues.append("traceability confidence is degraded")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Check SDD artifact health.")
    parser.add_argument("--root", default=".", help="Project root containing docs/")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    docs = root / "docs"
    failures = 0
    warnings = 0

    if not docs.exists():
        report("FAIL", f"{docs} does not exist")
        return 1

    state = docs / "sdd-state.yaml"
    legacy_progress = docs / "workflow-progress.md"
    if state.exists():
        report("PASS", "docs/sdd-state.yaml exists")
    elif legacy_progress.exists():
        warnings += 1
        report("WARN", "docs/sdd-state.yaml missing; using legacy docs/workflow-progress.md")
    else:
        failures += 1
        report("FAIL", "no docs/sdd-state.yaml or docs/workflow-progress.md")

    report("INFO", "authoritative spec fingerprints:")
    for rel in AUTHORITATIVE_SPECS:
        path = docs / rel
        if path.exists():
            report("PASS", f"{rel} sha256={sha256(path)[:16]}")
        else:
            warnings += 1
            report("WARN", f"{rel} missing")

    for rel in JSON_ARTIFACTS:
        path = docs / rel
        if not path.exists():
            continue
        ok, result = load_json(path)
        if not ok:
            failures += 1
            report("FAIL", f"{rel} is invalid JSON: {result}")
            continue
        report("PASS", f"{rel} parses as JSON")
        for issue in check_json_shape(rel, result):
            if "degraded" in issue or "approved is not true" in issue:
                warnings += 1
                report("WARN", issue)
            else:
                failures += 1
                report("FAIL", issue)

    acceptance = docs / "contracts/acceptance-tests.yaml"
    if acceptance.exists():
        report("INFO", "contracts/acceptance-tests.yaml exists as a derived test view")

    for rel in DERIVED_VIEWS:
        path = docs / rel
        if path.exists():
            report("INFO", f"{rel} exists (derived view)")

    if failures:
        report("FAIL", f"SDD doctor found {failures} failure(s), {warnings} warning(s)")
        return 1
    report("PASS", f"SDD doctor found no failures ({warnings} warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
