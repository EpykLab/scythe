import io
import json
import os
import sqlite3
import socket
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout, redirect_stderr

from scythe.cli.main import main as scythe_main


class TestScytheCLI(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = self.tmpdir.name

    def _chdir(self, path):
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(path)

    def _free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    def test_init_creates_structure_and_db(self):
        code = scythe_main(["init", "--path", self.root])
        self.assertEqual(code, 0)
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".scythe")))
        self.assertTrue(
            os.path.isdir(os.path.join(self.root, ".scythe", "scythe_tests"))
        )
        db_path = os.path.join(self.root, ".scythe", "scythe.db")
        self.assertTrue(os.path.exists(db_path))
        # verify tables exist
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tests'"
            )
            self.assertIsNotNone(cur.fetchone())
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='runs'"
            )
            self.assertIsNotNone(cur.fetchone())
        finally:
            conn.close()

    def test_new_creates_test_file_and_db_entry(self):
        scythe_main(["init", "--path", self.root])
        self._chdir(self.root)
        code = scythe_main(["new", "alpha_test"])
        self.assertEqual(code, 0)
        test_path = os.path.join(self.root, ".scythe", "scythe_tests", "alpha_test.py")
        self.assertTrue(os.path.exists(test_path))
        with open(test_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("scythe_test_definition", content)
        # check DB entry
        db_path = os.path.join(self.root, ".scythe", "scythe.db")
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT name, path FROM tests WHERE name=?", ("alpha_test.py",))
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "alpha_test.py")
        finally:
            conn.close()

    def test_run_records_run_success(self):
        scythe_main(["init", "--path", self.root])
        self._chdir(self.root)
        scythe_main(["new", "bravo_test"])
        test_path = os.path.join(self.root, ".scythe", "scythe_tests", "bravo_test.py")
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(
                "#!/usr/bin/env python3\n"
                "import sys\n\n"
                'COMPATIBLE_VERSIONS = ["1.2.3"]\n\n'
                "def scythe_test_definition(args) -> int:\n"
                "    return 0\n\n"
                "def main() -> None:\n"
                "    sys.exit(scythe_test_definition(None))\n\n"
                'if __name__ == "__main__":\n'
                "    main()\n"
            )
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = scythe_main(["run", "bravo_test"])  # should succeed
        self.assertEqual(code, 0)
        out = buf.getvalue()
        self.assertIsInstance(out, str)
        # Check DB run entry
        db_path = os.path.join(self.root, ".scythe", "scythe.db")
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT name_of_test, result FROM runs ORDER BY rowid DESC LIMIT 1"
            )
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "bravo_test.py")
            self.assertEqual(row[1], "SUCCESS")
        finally:
            conn.close()

    def test_db_dump_outputs_json(self):
        scythe_main(["init", "--path", self.root])
        self._chdir(self.root)
        scythe_main(["new", "charlie_test"])  # at least one test row
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = scythe_main(["db", "dump"])  # dump as json
        self.assertEqual(code, 0)
        j = json.loads(buf.getvalue())
        self.assertIn("tests", j)
        self.assertIn("runs", j)
        self.assertTrue(any(row.get("name") == "charlie_test.py" for row in j["tests"]))

    def test_db_sync_compat_updates_versions(self):
        scythe_main(["init", "--path", self.root])
        self._chdir(self.root)
        scythe_main(
            ["new", "delta_test"]
        )  # template includes COMPATIBLE_VERSIONS=["1.2.3"]
        # run sync-compat
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = scythe_main(["db", "sync-compat", "delta_test"])  # should succeed
        self.assertEqual(code, 0)
        # verify DB updated
        db_path = os.path.join(self.root, ".scythe", "scythe.db")
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT compatible_versions FROM tests WHERE name=?", ("delta_test.py",)
            )
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], json.dumps(["1.2.3"]))
        finally:
            conn.close()

    def test_db_sync_compat_handles_missing(self):
        scythe_main(["init", "--path", self.root])
        self._chdir(self.root)
        scythe_main(["new", "echo_test"])  # create test
        # Remove the COMPATIBLE_VERSIONS line from the test file
        test_path = os.path.join(self.root, ".scythe", "scythe_tests", "echo_test.py")
        with open(test_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace('COMPATIBLE_VERSIONS = "["1.2.3"]"', "")
        # The above replacement string might not match due to quoting; do a safer removal by filtering lines
        lines = [
            ln
            for ln in content.splitlines()
            if not ln.strip().startswith("COMPATIBLE_VERSIONS")
        ]
        with open(test_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        # run sync-compat
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = scythe_main(
                ["db", "sync-compat", "echo_test"]
            )  # should succeed gracefully
        self.assertEqual(code, 0)
        # verify DB updated with empty string
        db_path = os.path.join(self.root, ".scythe", "scythe.db")
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT compatible_versions FROM tests WHERE name=?", ("echo_test.py",)
            )
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "")
        finally:
            conn.close()

    def test_new_supports_template_kind(self):
        scythe_main(["init", "--path", self.root])
        self._chdir(self.root)
        code = scythe_main(["new", "foxtrot_test", "--kind", "ttp-api"])
        self.assertEqual(code, 0)
        test_path = os.path.join(
            self.root, ".scythe", "scythe_tests", "foxtrot_test.py"
        )
        self.assertTrue(os.path.exists(test_path))
        with open(test_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("LoginBruteforceTTP", content)
        self.assertIn("def scythe_test_definition(args) -> int:", content)

    def test_new_supports_stellarbridge_template_kind(self):
        scythe_main(["init", "--path", self.root])
        self._chdir(self.root)
        code = scythe_main(["new", "hotel_test", "--kind", "sb-route-matrix"])
        self.assertEqual(code, 0)
        test_path = os.path.join(self.root, ".scythe", "scythe_tests", "hotel_test.py")
        self.assertTrue(os.path.exists(test_path))
        with open(test_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("/api/v1/public/download/info/fixture-transfer-id", content)
        self.assertIn("JourneyExecutor", content)

    def test_check_command_outputs_json(self):
        scythe_main(["init", "--path", self.root])
        self._chdir(self.root)
        scythe_main(["new", "golf_test"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = scythe_main(["check", "golf_test", "--json"])
        self.assertEqual(code, 0)
        report = json.loads(buf.getvalue())
        self.assertTrue(report["ok"])
        self.assertEqual(report["errors"], [])

    def test_check_command_reports_errors(self):
        scythe_main(["init", "--path", self.root])
        self._chdir(self.root)
        bad_path = os.path.join(self.root, ".scythe", "scythe_tests", "broken_test.py")
        with open(bad_path, "w", encoding="utf-8") as f:
            f.write("#!/usr/bin/env python3\nprint('broken')\n")

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = scythe_main(["check", "broken_test", "--json"])
        self.assertEqual(code, 1)
        report = json.loads(buf.getvalue())
        self.assertFalse(report["ok"])
        error_codes = {entry["code"] for entry in report["errors"]}
        self.assertIn("missing_test_definition", error_codes)
        self.assertIn("compatible_versions_missing_or_invalid", error_codes)

    def test_check_strict_fails_on_warnings(self):
        scythe_main(["init", "--path", self.root])
        self._chdir(self.root)
        warn_path = os.path.join(
            self.root, ".scythe", "scythe_tests", "warning_test.py"
        )
        with open(warn_path, "w", encoding="utf-8") as f:
            f.write(
                "#!/usr/bin/env python3\n"
                "import argparse\n"
                "import sys\n\n"
                'COMPATIBLE_VERSIONS = ["1.2.3"]\n\n'
                "def scythe_test_definition(args):\n"
                "    return 0\n\n"
                "def main():\n"
                "    parser = argparse.ArgumentParser()\n"
                "    parser.add_argument('--url')\n"
                "    args = parser.parse_args()\n"
                "    sys.exit(scythe_test_definition(args))\n\n"
                'if __name__ == "__main__":\n'
                "    main()\n"
            )

        non_strict = scythe_main(["check", "warning_test", "--json"])
        strict = scythe_main(["check", "warning_test", "--json", "--strict"])

        self.assertEqual(non_strict, 0)
        self.assertEqual(strict, 1)

    def test_fixture_serve_supports_auth_flow(self):
        import requests

        port = self._free_port()
        result_holder = {}

        def run_server():
            result_holder["code"] = scythe_main(
                [
                    "fixture",
                    "serve",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--max-requests",
                    "3",
                ]
            )

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

        base_url = f"http://127.0.0.1:{port}"
        session = requests.Session()
        pricing_response = None
        for _ in range(60):
            try:
                pricing_response = session.get(f"{base_url}/api/v1/pricing", timeout=1)
                break
            except requests.RequestException:
                time.sleep(0.05)

        if pricing_response is None:
            self.fail("Fixture server did not start in time")

        self.assertEqual(pricing_response.status_code, 200)
        self.assertEqual(
            pricing_response.headers.get("X-SCYTHE-TARGET-VERSION"), "1.2.3"
        )

        login_response = session.post(
            f"{base_url}/api/v1/auth/login-handler",
            json={"email": "user@example.com", "password": "ChangeMe123!"},
            timeout=1,
        )
        self.assertEqual(login_response.status_code, 200)

        me_response = session.get(f"{base_url}/api/v1/auth/me", timeout=1)
        self.assertEqual(me_response.status_code, 200)

        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result_holder.get("code"), 0)

    def test_new_from_intent_json_selects_kind(self):
        scythe_main(["init", "--path", self.root])
        self._chdir(self.root)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = scythe_main(
                [
                    "new",
                    "intent_test",
                    "--from-intent",
                    "--intent",
                    "test organization rbac permissions",
                    "--json",
                ]
            )
        self.assertEqual(code, 0)
        report = json.loads(buf.getvalue())
        self.assertEqual(report["command"], "new")
        self.assertEqual(report["data"]["kind"], "sb-org-rbac")

    def test_run_json_output(self):
        scythe_main(["init", "--path", self.root])
        self._chdir(self.root)
        scythe_main(["new", "run_json_test"])
        test_path = os.path.join(
            self.root, ".scythe", "scythe_tests", "run_json_test.py"
        )
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                'COMPATIBLE_VERSIONS = ["1.2.3"]\n'
                "def scythe_test_definition(args) -> int:\n"
                "    return 0\n"
                "def main() -> None:\n"
                "    sys.exit(0)\n"
                'if __name__ == "__main__":\n'
                "    main()\n"
            )
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = scythe_main(["run", "--json", "run_json_test"])
        self.assertEqual(code, 0)
        report = json.loads(buf.getvalue())
        self.assertEqual(report["command"], "run")
        self.assertTrue(report["ok"])
        self.assertEqual(report["data"]["summary"]["passed"], 1)

    def test_check_fix_applies_changes(self):
        scythe_main(["init", "--path", self.root])
        self._chdir(self.root)
        test_path = os.path.join(self.root, ".scythe", "scythe_tests", "fix_test.py")
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(
                "#!/usr/bin/env python3\n"
                "import argparse\n"
                "import sys\n"
                "def scythe_test_definition(args):\n"
                "    return 0\n"
                "def main():\n"
                "    parser = argparse.ArgumentParser()\n"
                "    args = parser.parse_args()\n"
                "    sys.exit(scythe_test_definition(args))\n"
            )
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = scythe_main(["check", "fix_test", "--json", "--fix"])
        self.assertEqual(code, 0)
        report = json.loads(buf.getvalue())
        self.assertIn("applied_fixes", report)
        self.assertTrue(len(report["applied_fixes"]) >= 1)

    def test_discover_routes_json_output(self):
        openapi_path = os.path.join(self.root, "openapi.json")
        with open(openapi_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "openapi": "3.0.0",
                    "paths": {
                        "/api/v1/pricing": {"get": {"operationId": "getPricing"}},
                        "/api/v1/auth/me": {"get": {"operationId": "getMe"}},
                    },
                },
                f,
            )
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = scythe_main(
                ["discover", "routes", "--openapi", openapi_path, "--json"]
            )
        self.assertEqual(code, 0)
        report = json.loads(buf.getvalue())
        self.assertEqual(report["command"], "discover")
        self.assertEqual(len(report["data"]["routes"]), 2)

    def test_snippet_lookup_json_output(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = scythe_main(["snippet", "lookup", "csrf", "--json"])
        self.assertEqual(code, 0)
        report = json.loads(buf.getvalue())
        self.assertEqual(report["command"], "snippet")
        self.assertGreaterEqual(report["data"]["count"], 1)

    def test_doctor_ai_json_output(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = scythe_main(["doctor", "ai", "--json"])
        self.assertEqual(code, 0)
        report = json.loads(buf.getvalue())
        self.assertEqual(report["command"], "doctor")
        self.assertIn("checks", report["data"])

    def test_fixture_list_profiles(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = scythe_main(["fixture", "serve", "--list-profiles"])
        self.assertEqual(code, 0)
        self.assertIn("minimal", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
