import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Typer is used for the CLI. Import at module level for static analyzers; runtime guard in main.
try:
    import typer  # type: ignore
except Exception:  # pragma: no cover
    typer = None  # type: ignore


PROJECT_DIRNAME = ".scythe"
DB_FILENAME = "scythe.db"
TESTS_DIRNAME = "scythe_tests"


TEST_TEMPLATE = """#!/usr/bin/env python3

# scythe test initial template

import argparse
import os
import sys
import time
from typing import List, Tuple

# Scythe framework imports
from scythe.core.executor import TTPExecutor
from scythe.behaviors import HumanBehavior


def scythe_test_definition(args):
    # TODO: implement your test using Scythe primitives.
    # Example placeholder that simply passes.
    return True


def main():
    parser = argparse.ArgumentParser(description="Scythe test script")
    parser.add_argument('--url', help='Target URL (overridden by localhost unless FORCE_USE_CLI_URL=1)')
    args = parser.parse_args()

    ok = scythe_test_definition(args)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
"""


class ScytheCLIError(Exception):
    pass


def _find_project_root(start: Optional[str] = None) -> Optional[str]:
    """Walk upwards from start (or cwd) to find a directory containing .scythe."""
    cur = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(cur, PROJECT_DIRNAME)):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def _db_path(project_root: str) -> str:
    return os.path.join(project_root, PROJECT_DIRNAME, DB_FILENAME)


def _ensure_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tests (
            name TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            created_date TEXT NOT NULL,
            compatible_versions TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            datetime TEXT NOT NULL,
            name_of_test TEXT NOT NULL,
            x_scythe_target_version TEXT,
            result TEXT NOT NULL,
            raw_output TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _open_db(project_root: str) -> sqlite3.Connection:
    path = _db_path(project_root)
    conn = sqlite3.connect(path)
    _ensure_db(conn)
    return conn


def _init_project(path: str) -> str:
    root = os.path.abspath(path or ".")
    os.makedirs(root, exist_ok=True)

    project_dir = os.path.join(root, PROJECT_DIRNAME)
    tests_dir = os.path.join(project_dir, TESTS_DIRNAME)

    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(tests_dir, exist_ok=True)

    # Initialize the sqlite DB with required tables
    conn = sqlite3.connect(os.path.join(project_dir, DB_FILENAME))
    try:
        _ensure_db(conn)
    finally:
        conn.close()

    # Write a helpful README
    readme_path = os.path.join(project_dir, "README.md")
    if not os.path.exists(readme_path):
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(
                "Scythe project directory.\n\n"
                "- scythe.db: SQLite database for tests and runs logs.\n"
                f"- {TESTS_DIRNAME}: Create your test scripts here.\n"
            )

    # Gitignore the DB by default
    gitignore_path = os.path.join(project_dir, ".gitignore")
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("scythe.db\n")

    return root


def _create_test(project_root: str, name: str) -> str:
    if not name:
        raise ScytheCLIError("Test name is required")
    filename = name if name.endswith(".py") else f"{name}.py"
    tests_dir = os.path.join(project_root, PROJECT_DIRNAME, TESTS_DIRNAME)
    os.makedirs(tests_dir, exist_ok=True)
    filepath = os.path.join(tests_dir, filename)
    if os.path.exists(filepath):
        raise ScytheCLIError(f"Test already exists: {filepath}")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(TEST_TEMPLATE)
    os.chmod(filepath, 0o755)

    # Insert into DB
    conn = _open_db(project_root)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO tests(name, path, created_date, compatible_versions) VALUES(?,?,?,?)",
            (
                filename,
                os.path.relpath(filepath, project_root),
                datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return filepath


_VERSION_RE = re.compile(r"X-SCYTHE-TARGET-VERSION\s*[:=]\s*([\w\.-]+)")
_DETECTED_LIST_RE = re.compile(r"Detected target versions: \[?([^\]]*)\]?")


def _parse_version_from_output(output: str) -> Optional[str]:
    m = _VERSION_RE.search(output)
    if m:
        return m.group(1)
    # Try from Detected target versions: ["1.2.3"] or like str(list)
    m = _DETECTED_LIST_RE.search(output)
    if m:
        inner = m.group(1)
        # extract first version-like token
        mv = re.search(r"[\d]+(?:\.[\w\-]+)+", inner)
        if mv:
            return mv.group(0)
    return None


def _run_test(project_root: str, name: str) -> Tuple[int, str, Optional[str]]:
    filename = name if name.endswith(".py") else f"{name}.py"
    test_path = os.path.join(project_root, PROJECT_DIRNAME, TESTS_DIRNAME, filename)
    if not os.path.exists(test_path):
        raise ScytheCLIError(f"Test not found: {test_path}")

    # Ensure the subprocess can import the in-repo scythe package when running from a temp project
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    env = os.environ.copy()
    existing_pp = env.get('PYTHONPATH', '')
    if repo_root not in existing_pp.split(os.pathsep):
        env['PYTHONPATH'] = os.pathsep.join([p for p in [existing_pp, repo_root] if p])

    # Execute the test as a subprocess using the same interpreter
    proc = subprocess.run(
        [sys.executable, test_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=project_root,
        env=env,
    )
    output = proc.stdout
    version = _parse_version_from_output(output)
    return proc.returncode, output, version


def _record_run(project_root: str, name: str, code: int, output: str, version: Optional[str]) -> None:
    conn = _open_db(project_root)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO runs(datetime, name_of_test, x_scythe_target_version, result, raw_output) VALUES(?,?,?,?,?)",
            (
                datetime.utcnow().isoformat(timespec="seconds") + "Z",
                name if name.endswith(".py") else f"{name}.py",
                version or "",
                "SUCCESS" if code == 0 else "FAILURE",
                output,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _dump_db(project_root: str) -> Dict[str, List[Dict[str, str]]]:
    conn = _open_db(project_root)
    try:
        cur = conn.cursor()
        result: Dict[str, List[Dict[str, str]]] = {}
        for table in ("tests", "runs"):
            cur.execute(f"SELECT * FROM {table}")
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            result[table] = rows
        return result
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scythe", description="Scythe CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize a new .scythe project")
    p_init.add_argument("--path", default=".", help="Target directory (default: .)")

    p_new = sub.add_parser("new", help="Create a new test in scythe_tests")
    p_new.add_argument("name", help="Name of the test (e.g., login_smoke or login_smoke.py)")

    p_run = sub.add_parser("run", help="Run a test from scythe_tests and record the run")
    p_run.add_argument("name", help="Name of the test to run (e.g., login_smoke or login_smoke.py)")

    p_db = sub.add_parser("db", help="Database utilities")
    sub_db = p_db.add_subparsers(dest="db_cmd", required=True)
    sub_db.add_parser("dump", help="Dump tests and runs tables as JSON")

    return parser


def _legacy_main(argv: Optional[List[str]] = None) -> int:
    """Argparse-based fallback for environments without Typer installed."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            root = _init_project(args.path)
            print(f"Initialized Scythe project at: {root}")
            return 0

        if args.command == "new":
            project_root = _find_project_root()
            if not project_root:
                raise ScytheCLIError("Not inside a Scythe project. Run 'scythe init' first.")
            path = _create_test(project_root, args.name)
            print(f"Created test: {path}")
            return 0

        if args.command == "run":
            project_root = _find_project_root()
            if not project_root:
                raise ScytheCLIError("Not inside a Scythe project. Run 'scythe init' first.")
            code, output, version = _run_test(project_root, args.name)
            _record_run(project_root, args.name, code, output, version)
            print(output)
            return code

        if args.command == "db":
            project_root = _find_project_root()
            if not project_root:
                raise ScytheCLIError("Not inside a Scythe project. Run 'scythe init' first.")
            if args.db_cmd == "dump":
                data = _dump_db(project_root)
                print(json.dumps(data, indent=2))
                return 0

        raise ScytheCLIError("Unknown command")
    except ScytheCLIError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


def main(argv: Optional[List[str]] = None) -> int:
    """Typer-based CLI entry point. When called programmatically, returns an exit code int.

    This constructs a Typer app with subcommands equivalent to the previous argparse version,
    then dispatches using Click's command runner with standalone_mode=False to capture return codes.
    """
    try:
        import typer
    except Exception:
        # Fallback to legacy argparse-based implementation if Typer is not available
        return _legacy_main(argv)

    app = typer.Typer(add_completion=False, help="Scythe CLI")

    @app.command()
    def init(
        path: str = typer.Option(
            ".",
            "--path",
            "-p",
            help="Target directory (default: .)",
        )
    ) -> int:
        """Initialize a new .scythe project"""
        root = _init_project(path)
        print(f"Initialized Scythe project at: {root}")
        return 0

    @app.command()
    def new(
        name: str = typer.Argument(..., help="Name of the test (e.g., login_smoke or login_smoke.py)")
    ) -> int:
        """Create a new test in scythe_tests"""
        project_root = _find_project_root()
        if not project_root:
            raise ScytheCLIError("Not inside a Scythe project. Run 'scythe init' first.")
        path = _create_test(project_root, name)
        print(f"Created test: {path}")
        return 0

    @app.command()
    def run(
        name: str = typer.Argument(..., help="Name of the test to run (e.g., login_smoke or login_smoke.py)")
    ) -> int:
        """Run a test from scythe_tests and record the run"""
        project_root = _find_project_root()
        if not project_root:
            raise ScytheCLIError("Not inside a Scythe project. Run 'scythe init' first.")
        code, output, version = _run_test(project_root, name)
        _record_run(project_root, name, code, output, version)
        print(output)
        return code

    db_app = typer.Typer(help="Database utilities")

    @db_app.command("dump")
    def dump() -> int:
        """Dump tests and runs tables as JSON"""
        project_root = _find_project_root()
        if not project_root:
            raise ScytheCLIError("Not inside a Scythe project. Run 'scythe init' first.")
        data = _dump_db(project_root)
        print(json.dumps(data, indent=2))
        return 0

    app.add_typer(db_app, name="db")

    if argv is None:
        argv = sys.argv[1:]

    try:
        rv = app(prog_name="scythe", args=argv, standalone_mode=False)
        return int(rv) if isinstance(rv, int) else 0
    except ScytheCLIError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except SystemExit as e:
        # should not occur with standalone_mode=False, but handle defensively
        return int(getattr(e, "code", 0) or 0)
