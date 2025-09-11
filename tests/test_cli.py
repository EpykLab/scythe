import io
import json
import os
import sqlite3
import sys
import tempfile
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

    def test_init_creates_structure_and_db(self):
        code = scythe_main(["init", "--path", self.root])
        self.assertEqual(code, 0)
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".scythe")))
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".scythe", "scythe_tests")))
        db_path = os.path.join(self.root, ".scythe", "scythe.db")
        self.assertTrue(os.path.exists(db_path))
        # verify tables exist
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tests'")
            self.assertIsNotNone(cur.fetchone())
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='runs'")
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
        scythe_main(["new", "bravo_test"])  # template exits 0
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
            cur.execute("SELECT name_of_test, result FROM runs ORDER BY rowid DESC LIMIT 1")
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
        scythe_main(["new", "delta_test"])  # template includes COMPATIBLE_VERSIONS=["1.2.3"]
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
            cur.execute("SELECT compatible_versions FROM tests WHERE name=?", ("delta_test.py",))
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
        content = content.replace("COMPATIBLE_VERSIONS = \"[\"1.2.3\"]\"", "")
        # The above replacement string might not match due to quoting; do a safer removal by filtering lines
        lines = [ln for ln in content.splitlines() if not ln.strip().startswith("COMPATIBLE_VERSIONS")]
        with open(test_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        # run sync-compat
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = scythe_main(["db", "sync-compat", "echo_test"])  # should succeed gracefully
        self.assertEqual(code, 0)
        # verify DB updated with empty string
        db_path = os.path.join(self.root, ".scythe", "scythe.db")
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT compatible_versions FROM tests WHERE name=?", ("echo_test.py",))
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
