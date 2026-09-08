from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "rule-and-excel-toolkit" / "scripts"
TOOLKIT = SCRIPTS / "toolkit.py"

sys.path.insert(0, str(SCRIPTS))
from common.log_fields import extract_fields
from common.registry import COMMANDS


class CliContractTests(unittest.TestCase):
    def test_command_ids_are_unique(self):
        ids = [c.command_id for c in COMMANDS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 11)

    def test_registered_scripts_exist(self):
        for spec in COMMANDS:
            self.assertTrue((SCRIPTS / spec.script).is_file(), spec.script)

    def test_output_commands_have_default_suffix(self):
        for spec in COMMANDS:
            if spec.supports_output:
                self.assertTrue(spec.output_suffix, spec.command_id)

    def test_option_flags_unique_per_command(self):
        for spec in COMMANDS:
            flags = [o.flag for o in spec.options]
            self.assertEqual(len(flags), len(set(flags)), spec.command_id)

    def test_output_commands_support_structured_verify(self):
        for spec in COMMANDS:
            if spec.supports_output:
                self.assertTrue(spec.supports_verify, spec.command_id)

    def test_toolkit_help(self):
        result = subprocess.run([sys.executable, str(TOOLKIT), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("rule", result.stdout)
        self.assertIn("excel", result.stdout)

    def test_split_help_exposes_selective_output_options(self):
        result = subprocess.run(
            [sys.executable, str(TOOLKIT), "excel", "split", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--keep-columns", result.stdout)
        self.assertIn("--tail-fields", result.stdout)
        self.assertIn("--no-full-sheet", result.stdout)

    def test_plain_kv_tail_extraction_is_configurable(self):
        log = (
            "x=1;dev_ip=10.104.11.19;raw_data=<46>Sep 04 host: "
            "dev_ip=10.104.11.19;agent_id=abc;msg=hello world"
        )
        scalar = extract_fields(log, ["raw_data", "dev_ip"])
        self.assertEqual(scalar["raw_data"], "<46>Sep 04 host: dev_ip=10.104.11.19")

        tail = extract_fields(log, ["raw_data", "dev_ip"], tail_fields={"raw_data"})
        self.assertEqual(tail["dev_ip"], "10.104.11.19")
        self.assertEqual(
            tail["raw_data"],
            "<46>Sep 04 host: dev_ip=10.104.11.19;agent_id=abc;msg=hello world",
        )

    def test_json_dry_run_schema(self):
        result = subprocess.run([
            sys.executable, str(TOOLKIT), "rule", "reuuid",
            "--input", "dummy.txt", "--dry-run", "--format", "json"
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["command"], "rule.reuuid")
        self.assertIn("verification", payload)
        self.assertIn("stats", payload)


if __name__ == "__main__":
    unittest.main()
