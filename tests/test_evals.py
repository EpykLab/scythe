import json
import os
import tempfile
import unittest

from scythe.evals.harness import run_eval


class TestEvalHarness(unittest.TestCase):
    def test_run_eval_writes_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scenarios_dir = os.path.join(tmpdir, "scenarios")
            os.makedirs(scenarios_dir, exist_ok=True)
            scenario_path = os.path.join(scenarios_dir, "one.json")
            with open(scenario_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "id": "one",
                        "test_name": "eval_one",
                        "intent": "test route matrix",
                    },
                    f,
                )

            root = os.path.join(tmpdir, "project")
            os.makedirs(root, exist_ok=True)
            old_cwd = os.getcwd()
            try:
                os.chdir(root)
                from scythe.cli.main import main as scythe_main

                scythe_main(["init", "--path", root])
                output_path = os.path.join(tmpdir, "report.json")
                code = run_eval(scenarios_dir, output_path)
                self.assertIn(code, (0, 1))
                self.assertTrue(os.path.exists(output_path))
                with open(output_path, "r", encoding="utf-8") as f:
                    report = json.load(f)
                self.assertIn("results", report)
                self.assertEqual(report["total"], 1)
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
