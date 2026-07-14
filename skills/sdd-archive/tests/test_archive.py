import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import yaml


SCRIPT = Path(__file__).parents[1] / "scripts" / "archive.py"


class ArchivePlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        docs = self.root / "docs"
        docs.mkdir()
        (docs / "requirements-baseline.json").write_text(json.dumps({"approved": True, "baseline_version": "v1.0", "requirements": [{"id": "F-001", "title": "A", "priority": "MUST", "acceptance_criteria": ["ok"]}]}), encoding="utf-8")
        (docs / "ontology_schema.json").write_text(json.dumps({"domain": "demo"}), encoding="utf-8")
        (docs / "sdd-state.yaml").write_text("schema_version: 1\nactive_scenario:\n  id: demo\n  name: Demo\n  requirement_ids: [F-001]\nstages:\n  code_verification:\n    status: complete\n    gate: passed\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args, "--root", str(self.root)], capture_output=True, text=True)

    def test_plan_is_read_only_and_deterministic(self):
        result = self.run_cli("plan", "--trigger", "verification-complete", "--date", "2026-07-13")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("archive_id: 2026-07-13-demo", result.stdout)
        self.assertFalse((self.root / "docs/archive").exists())
        self.assertFalse((self.root / "docs/requirements-baseline.json").read_text().find("delivered") >= 0)

    def test_missing_active_scenario_blocks_plan(self):
        state = self.root / "docs/sdd-state.yaml"
        state.write_text("schema_version: 1\n", encoding="utf-8")
        result = self.run_cli("plan", "--trigger", "manual")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scenario", result.stderr)

    def test_verify_empty_archive_passes(self):
        result = self.run_cli("verify")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_apply_commits_snapshot_and_verify_passes(self):
        (self.root / "docs/brd.md").write_text("demo", encoding="utf-8")
        plan_path = self.root / ".sdd-plan.yaml"
        result = self.run_cli("plan", "--trigger", "manual", "--date", "2026-07-13", "--output", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli("apply", "--plan", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / "docs/archive/2026-07-13-demo/manifest.yaml").exists())
        result = self.run_cli("verify")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / ".sdd/archive.lock").exists())

    def test_apply_rejects_changed_source(self):
        plan_path = self.root / ".sdd-plan.yaml"
        result = self.run_cli("plan", "--trigger", "manual", "--date", "2026-07-13", "--output", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.root / "docs/requirements-baseline.json").write_text("{}", encoding="utf-8")
        result = self.run_cli("apply", "--plan", str(plan_path))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "docs/archive/2026-07-13-demo").exists())

    def test_formal_apply_marks_only_declared_requirement_delivered(self):
        plan_path = self.root / ".sdd-plan.yaml"
        result = self.run_cli("plan", "--trigger", "verification-complete", "--date", "2026-07-13", "--output", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli("apply", "--plan", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        baseline = json.loads((self.root / "docs/requirements-baseline.json").read_text())
        self.assertEqual(baseline["requirements"][0]["status"], "delivered")
        self.assertEqual(baseline["requirements"][0]["scenario"], "demo")

    def test_register_upserts_ledger_and_renders_index(self):
        plan_path = self.root / ".sdd-plan.yaml"
        result = self.run_cli("plan", "--trigger", "verification-complete", "--date", "2026-07-13", "--output", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli("apply", "--plan", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        transaction = yaml.safe_load(result.stdout)["transaction_id"]
        result = self.run_cli("register", "--transaction", transaction)
        self.assertEqual(result.returncode, 0, result.stderr)
        ledger = yaml.safe_load((self.root / "docs/sdd-state.yaml").read_text())
        self.assertEqual(len(ledger["archives"]), 1)
        self.assertNotIn("active_scenario", ledger)
        index = (self.root / "docs/archive/index.md").read_text()
        self.assertIn("demo", index)
        result = self.run_cli("register", "--transaction", transaction)
        self.assertEqual(result.returncode, 0, result.stderr)
        ledger = yaml.safe_load((self.root / "docs/sdd-state.yaml").read_text())
        self.assertEqual(len(ledger["archives"]), 1)


if __name__ == "__main__":
    unittest.main()
