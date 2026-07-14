#!/usr/bin/env python3
"""Read-only planning and verification for SDD archives.

P1 deliberately has no apply/move operation.  It produces a deterministic
plan and verifies completed manifests without changing project files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import shutil
import uuid
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML>=6.0 is required for archive plan/verify") from exc

ARCHIVE_FILES = {
    "ontology_schema.json": ("specs/ontology_schema.json", "copy"),
    "requirements-baseline.json": ("specs/requirements-baseline.json", "copy"),
    "contracts/app-contract.yaml": ("specs/app-contract.yaml", "copy"),
    "contracts/db-schema.sql": ("specs/db-schema.sql", "copy"),
    "brd.md": ("views/brd.md", "copy"),
    "app-design.md": ("views/app-design.md", "copy"),
    "db-schema.md": ("views/db-schema.md", "copy"),
    "contracts/acceptance-tests.yaml": ("views/acceptance-tests.yaml", "copy"),
    "traceability.json": ("evidence/traceability.json", "copy"),
    "impl-plan.md": ("process/impl-plan.md", "move"),
    "workflow-progress.md": ("process/workflow-progress.md", "move"),
}
TRIGGERS = {"verification-complete", "new-scenario", "manual", "iteration"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def dump_yaml(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def canonical_baseline(value: Any) -> str:
    """Hash business content while ignoring archive lifecycle metadata."""
    if isinstance(value, dict):
        return {k: canonical_baseline(v) for k, v in sorted(value.items()) if k not in {"lifecycle"}}
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, dict):
                result.append({k: canonical_baseline(v) for k, v in sorted(item.items()) if k not in {"status", "scenario", "delivered_at"}})
            else:
                result.append(canonical_baseline(item))
        return result
    return value


def content_fingerprint(path: Path) -> str:
    value = json.loads(path.read_text(encoding="utf-8"))
    payload = json.dumps(canonical_baseline(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not result:
        raise ValueError("scenario slug is empty")
    return result


def state_value(state: dict[str, Any], key: str, default: Any = None) -> Any:
    value = state.get(key, default)
    return value if isinstance(value, dict) else default


def scenario_from(args: argparse.Namespace, state: dict[str, Any], baseline: dict[str, Any], ontology: dict[str, Any]) -> tuple[str, str, list[str]]:
    active = state_value(state, "active_scenario", {})
    scenario_id = args.scenario or active.get("id")
    name = active.get("name", "")
    requirement_ids = list(args.requirements or active.get("requirement_ids", []))
    if not scenario_id:
        scenario_id = baseline.get("scenario") or baseline.get("domain") or ontology.get("domain")
    if not scenario_id:
        raise ValueError("no scenario id; set active_scenario.id or --scenario")
    if not requirement_ids:
        raise ValueError("no explicit requirement IDs; set active_scenario.requirement_ids or --requirements")
    return slug(str(scenario_id)), str(name), sorted(set(map(str, requirement_ids)))


def base_context(args: argparse.Namespace) -> tuple[Path, Path, dict[str, Any], dict[str, Any], dict[str, Any], str, str, list[str]]:
    root = Path(args.root).resolve()
    docs = root / "docs"
    if not docs.is_dir():
        raise ValueError(f"missing docs directory: {docs}")
    state_path = docs / "sdd-state.yaml"
    state = load_yaml(state_path) if state_path.exists() else {}
    baseline_path = docs / "requirements-baseline.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else {}
    ontology_path = docs / "ontology_schema.json"
    ontology = json.loads(ontology_path.read_text(encoding="utf-8")) if ontology_path.exists() else {}
    scenario, name, ids = scenario_from(args, state, baseline, ontology)
    return root, docs, state, baseline, ontology, scenario, name, ids


def plan(args: argparse.Namespace) -> int:
    if args.trigger not in TRIGGERS:
        raise ValueError(f"invalid trigger: {args.trigger}")
    root, docs, state, baseline, ontology, scenario, name, ids = base_context(args)
    requirements = {str(item.get("id")): item for item in baseline.get("requirements", []) if isinstance(item, dict)}
    missing = sorted(set(ids) - requirements.keys())
    if missing:
        raise ValueError(f"requirement IDs missing from baseline: {', '.join(missing)}")
    active = state_value(state, "active_scenario", {})
    declared = sorted(map(str, active.get("requirement_ids", [])))
    if declared and declared != ids:
        raise ValueError("--requirements does not match active_scenario.requirement_ids")
    if args.trigger in {"verification-complete", "new-scenario"}:
        verification = state_value(state, "stages", {}).get("code_verification", {})
        if verification.get("status") != "complete" or verification.get("gate") != "passed":
            raise ValueError("formal archive requires code_verification status=complete and gate=passed")
    date = args.date or datetime.now(timezone.utc).date().isoformat()
    archive_id = f"{date}-{scenario}"
    archive_dir = docs / "archive" / archive_id
    if archive_dir.exists():
        raise ValueError(f"archive target already exists: {archive_dir}")
    files = []
    for source, (target, operation) in sorted(ARCHIVE_FILES.items()):
        source_path = docs / source
        if source_path.exists() and source_path.is_file():
            files.append({"source": f"docs/{source}", "archived": f"archive/{archive_id}/{target}", "operation": operation, "size": source_path.stat().st_size, "sha256": sha256(source_path)})
    baseline_fp = content_fingerprint(docs / "requirements-baseline.json") if (docs / "requirements-baseline.json").exists() else None
    plan_value = {"schema_version": 1, "archive_id": archive_id, "trigger": args.trigger, "scenario": {"id": scenario, "name": name, "requirement_ids": ids}, "source_content_fingerprint": baseline_fp, "files": files, "mutations": [{"file": "docs/requirements-baseline.json", "operation": "mark-delivered", "requirement_ids": ids}], "read_only": True}
    plan_value["plan_hash"] = hashlib.sha256(json.dumps(plan_value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    output = Path(args.output).resolve() if args.output else root / ".sdd" / "archive-plan.yaml"
    dump_yaml(plan_value, output)
    print(yaml.safe_dump(plan_value, allow_unicode=True, sort_keys=False), end="")
    return 0


def verify(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    docs = root / "docs"
    archive_root = docs / "archive"
    if not archive_root.is_dir():
        print("[PASS] no archive directory")
        return 0
    failures = 0
    for manifest_path in sorted(archive_root.glob("*/manifest.yaml")):
        manifest = load_yaml(manifest_path)
        if manifest.get("schema_version") != 1 or manifest.get("snapshot_state") != "complete":
            print(f"[FAIL] {manifest_path}: invalid schema_version or incomplete snapshot")
            failures += 1
            continue
        archive_dir = manifest_path.parent
        for item in manifest.get("files", []):
            target = archive_dir / Path(str(item.get("archived", "")).replace(f"archive/{archive_dir.name}/", "", 1))
            if not target.exists():
                print(f"[FAIL] {manifest_path}: missing {item.get('archived')}")
                failures += 1
            elif target.stat().st_size != item.get("size") or sha256(target) != item.get("sha256"):
                print(f"[FAIL] {manifest_path}: hash/size mismatch {item.get('archived')}")
                failures += 1
        print(f"[{'FAIL' if failures else 'PASS'}] {manifest_path}")
    return 8 if failures else 0


def transaction_dir(root: Path, transaction_id: str) -> Path:
    path = root / ".sdd" / "archive-txn" / transaction_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_plan(path: Path) -> dict[str, Any]:
    plan_value = load_yaml(path)
    if not isinstance(plan_value, dict) or plan_value.get("schema_version") != 1 or plan_value.get("read_only") is not True:
        raise ValueError("invalid archive plan")
    expected = dict(plan_value)
    actual_hash = expected.pop("plan_hash", None)
    computed = hashlib.sha256(json.dumps(expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if actual_hash != computed:
        raise ValueError("plan_hash mismatch; regenerate plan")
    return plan_value


def apply_plan(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    plan_value = load_plan(Path(args.plan).resolve())
    docs = root / "docs"
    archive_id = str(plan_value["archive_id"])
    archive_dir = docs / "archive" / archive_id
    txn_id = uuid.uuid4().hex
    txn = transaction_dir(root, txn_id)
    lock = root / ".sdd" / "archive.lock"
    if lock.exists():
        raise ValueError(f"archive lock exists: {lock}")
    lock.write_text(json.dumps({"transaction_id": txn_id, "pid": __import__("os").getpid()}), encoding="utf-8")
    state = {"transaction_id": txn_id, "archive_id": archive_id, "status": "staging", "archive_dir": str(archive_dir.relative_to(root))}
    (txn / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    try:
        if archive_dir.exists():
            raise ValueError(f"archive target already exists: {archive_dir}")
        payload = txn / "payload"
        for item in plan_value.get("files", []):
            source = root / str(item["source"])
            if not source.is_file() or sha256(source) != item["sha256"]:
                raise ValueError(f"source changed or missing after plan: {item['source']}")
            target = payload / Path(str(item["archived"]).split(f"archive/{archive_id}/", 1)[-1])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if target.stat().st_size != item["size"] or sha256(target) != item["sha256"]:
                raise ValueError(f"staged copy failed: {item['source']}")
        mutations = []
        baseline_path = docs / "requirements-baseline.json"
        if plan_value["trigger"] in {"verification-complete", "new-scenario"} and baseline_path.exists():
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
            ids = set(map(str, plan_value["scenario"]["requirement_ids"]))
            requirements = baseline.get("requirements", [])
            for requirement in requirements:
                if str(requirement.get("id")) in ids:
                    requirement["status"] = "delivered"
                    requirement["scenario"] = plan_value["scenario"]["id"]
                    requirement["delivered_at"] = datetime.now(timezone.utc).isoformat()
            if ids - {str(item.get("id")) for item in requirements}:
                raise ValueError("plan contains requirement ID absent from baseline")
            before = sha256(baseline_path)
            backup = txn / "baseline.before.json"
            shutil.copy2(baseline_path, backup)
            temp = txn / "requirements-baseline.json"
            temp.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(temp, baseline_path)
            mutations.append({"file": "docs/requirements-baseline.json", "operation": "mark-delivered", "requirement_ids": sorted(ids), "before_sha256": before, "after_sha256": sha256(baseline_path), "content_fingerprint_before": plan_value.get("source_content_fingerprint"), "content_fingerprint_after": content_fingerprint(baseline_path)})
        manifest = {"schema_version": 1, "archive_id": archive_id, "transaction_id": txn_id, "scenario": plan_value["scenario"], "archived_at": datetime.now(timezone.utc).isoformat(), "trigger": plan_value["trigger"], "snapshot_state": "complete", "fingerprint_policy": {"file": "sha256", "content": "canonical-json-v1"}, "files": plan_value.get("files", []), "active_mutations": mutations, "ledger_update": {"status": "pending", "archive_path": f"archive/{archive_id}"}}
        dump_yaml(manifest, payload / "manifest.yaml")
        archive_dir.parent.mkdir(parents=True, exist_ok=True)
        payload.rename(archive_dir)
        for item in plan_value.get("files", []):
            if item.get("operation") == "move":
                source = root / str(item["source"])
                backup = txn / "moved" / Path(str(item["source"]).removeprefix("docs/"))
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, backup)
                source.unlink()
        state["status"] = "files_committed"
        (txn / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
        (txn / "archive-result.yaml").write_text(yaml.safe_dump({"schema_version": 1, "transaction_id": txn_id, "archive_id": archive_id, "status": "files_committed", "manifest": f"archive/{archive_id}/manifest.yaml", "ledger_update": "pending"}, sort_keys=False), encoding="utf-8")
        lock.unlink(missing_ok=True)
        print(yaml.safe_dump({"transaction_id": txn_id, "archive_id": archive_id, "status": "files_committed", "ledger_update": "pending"}, sort_keys=False), end="")
        return 0
    except Exception:
        backup = txn / "baseline.before.json"
        if backup.exists():
            shutil.copy2(backup, docs / "requirements-baseline.json")
        if archive_dir.exists() and not (txn / "payload").exists():
            shutil.rmtree(archive_dir)
        moved_root = txn / "moved"
        if moved_root.exists():
            for backup_path in moved_root.rglob("*"):
                if backup_path.is_file():
                    relative = backup_path.relative_to(moved_root)
                    destination = docs / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_path, destination)
        lock.unlink(missing_ok=True)
        state["status"] = "rolled_back"
        (txn / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
        raise


def recover(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    txn_root = root / ".sdd" / "archive-txn"
    found = []
    paths = sorted(txn_root.glob("*/state.json")) if txn_root.exists() else []
    for state_path in paths:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("status") in {"staging", "files_committed", "recovery_required"}:
            archive_dir = root / state["archive_dir"]
            if state.get("status") == "files_committed" and archive_dir.exists():
                state["status"] = "recovery_required"
            else:
                payload = state_path.parent / "payload"
                if payload.exists():
                    shutil.rmtree(payload)
                state["status"] = "rolled_back"
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            found.append(state_path.parent.name)
    (root / ".sdd" / "archive.lock").unlink(missing_ok=True)
    print(yaml.safe_dump({"recovered": found}, sort_keys=False), end="")
    return 0


def finalize(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    txn_root = root / ".sdd" / "archive-txn"
    cleaned = []
    paths = sorted(txn_root.glob("*/state.json")) if txn_root.exists() else []
    for state_path in paths:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("status") == "registered":
            state["status"] = "finalized"
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            cleaned.append(state_path.parent.name)
    print(yaml.safe_dump({"finalized": cleaned}, sort_keys=False), end="")
    return 0


def register(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    txn = root / ".sdd" / "archive-txn" / str(args.transaction)
    state_path = txn / "state.json"
    if not state_path.exists():
        raise ValueError(f"transaction not found: {args.transaction}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("status") not in {"files_committed", "registered"}:
        raise ValueError(f"transaction is not registerable: {state.get('status')}")
    archive_dir = root / state["archive_dir"]
    manifest = load_yaml(archive_dir / "manifest.yaml")
    docs = root / "docs"
    ledger_path = docs / "sdd-state.yaml"
    if not ledger_path.exists():
        raise ValueError("docs/sdd-state.yaml is required for register")
    ledger = load_yaml(ledger_path)
    archives = ledger.get("archives")
    if not isinstance(archives, list):
        archives = []
    record = {"archive_id": manifest["archive_id"], "scenario": manifest["scenario"]["id"], "path": f"archive/{manifest['archive_id']}", "archived_at": manifest["archived_at"], "baseline_version": ledger.get("baseline_version", "unknown"), "trigger": manifest["trigger"]}
    replaced = False
    for index, item in enumerate(archives):
        if isinstance(item, dict) and (item.get("archive_id") == record["archive_id"] or item.get("path") == record["path"]):
            archives[index] = record
            replaced = True
            break
    if not replaced:
        archives.append(record)
    ledger["archives"] = archives
    if manifest["trigger"] in {"verification-complete", "new-scenario"}:
        ledger.pop("active_scenario", None)
    ledger["updated_at"] = datetime.now(timezone.utc).isoformat()
    temp_ledger = txn / "sdd-state.yaml"
    dump_yaml(ledger, temp_ledger)
    index_lines = ["# 归档索引", "", "| 场景 | 归档日期 | 触发 | baseline | 路径 |", "|---|---|---|---|---|"]
    for item in sorted(archives, key=lambda value: str(value.get("archived_at", ""))):
        index_lines.append(f"| {item.get('scenario', '')} | {str(item.get('archived_at', ''))[:10]} | {item.get('trigger', '')} | {item.get('baseline_version', '')} | [{item.get('path', '')}]({item.get('path', '')}/) |")
    temp_index = txn / "archive-index.md"
    temp_index.parent.mkdir(parents=True, exist_ok=True)
    temp_index.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    os.replace(temp_ledger, ledger_path)
    index_path = docs / "archive/index.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(temp_index, index_path)
    state["status"] = "registered"
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(yaml.safe_dump({"transaction_id": args.transaction, "archive_id": record["archive_id"], "status": "registered", "index": "docs/archive/index.md"}, sort_keys=False), end="")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SDD archive plan/apply/register/verify/recover/finalize")
    parser.add_argument("command", choices=["plan", "apply", "register", "verify", "recover", "finalize"])
    parser.add_argument("--root", default=".")
    parser.add_argument("--trigger", default="manual")
    parser.add_argument("--scenario")
    parser.add_argument("--requirements", nargs="*", help="explicit requirement IDs")
    parser.add_argument("--output")
    parser.add_argument("--plan")
    parser.add_argument("--transaction")
    parser.add_argument("--date")
    args = parser.parse_args()
    try:
        if args.command == "plan":
            return plan(args)
        if args.command == "apply":
            if not args.plan:
                raise ValueError("apply requires --plan")
            return apply_plan(args)
        if args.command == "recover":
            return recover(args)
        if args.command == "register":
            if not args.transaction:
                raise ValueError("register requires --transaction")
            return register(args)
        if args.command == "finalize":
            return finalize(args)
        return verify(args)
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
