import argparse
import ast
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

COMPATIBLE_VERSIONS = ["1.2.3"]

def check_url_available(url) -> bool | None:
    import requests
    if not url:
        return False
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "http://" + url
    try:
        r = requests.get(url, timeout=5)
        return r.status_code < 400
    except requests.exceptions.RequestException:
        return False

def check_version_in_response_header(args) -> bool:
    import requests
    url = args.url
    if url and not (url.startswith("http://") or url.startswith("https://")):
        url = "http://" + url
    r = requests.get(url)
    h = r.headers

    version = h.get('x-scythe-target-version')

    if not version or version not in COMPATIBLE_VERSIONS:
        print("This test is not compatible with the version of Scythe you are trying to run.")
        print("Please update Scythe and try again.")
        return False
    return True

def scythe_test_definition(args) -> bool:
    # TODO: implement your test using Scythe primitives.
    # Example placeholder that simply passes.
    
    # Example usage with TTPExecutor:
    # from scythe.core.executor import TTPExecutor
    # executor = TTPExecutor(ttp=my_ttp, target_url=args.url)
    # executor.run()
    # return executor.was_successful()  # Returns True if all results matched expectations
    
    # Example usage with JourneyExecutor:
    # from scythe.journeys.executor import JourneyExecutor
    # executor = JourneyExecutor(journey=my_journey, target_url=args.url)
    # executor.run()
    # return executor.was_successful()  # Returns True if journey succeeded as expected
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Scythe test script")
    parser.add_argument(
        '--url',
        help='Target URL')
    parser.add_argument(
        '--gate-versions',
        default=False,
        action='store_true',
        dest='gate_versions',
        help='Gate versions to test against')

    # Core Application Parameters
    parser.add_argument(
        '--protocol',
        default='https',
        choices=['http', 'https'],
        help='Protocol to use (http/https, default: https)')
    parser.add_argument(
        '--port',
        type=int,
        help='Port number for the target application')

    # Authentication Parameters
    parser.add_argument(
        '--username',
        help='Username for authentication')
    parser.add_argument(
        '--password',
        help='Password for authentication')
    parser.add_argument(
        '--token',
        help='Bearer token or API key')
    parser.add_argument(
        '--auth-type',
        choices=['basic', 'bearer', 'form'],
        help='Authentication method (basic, bearer, form, etc.)')
    parser.add_argument(
        '--credentials-file',
        help='Path to file containing multiple user credentials')

    # Test Data Parameters
    parser.add_argument(
        '--users-file',
        help='Path to CSV file containing user data')
    parser.add_argument(
        '--emails-file',
        help='Path to text file containing email addresses')
    parser.add_argument(
        '--payload-file',
        help='Path to file containing test payloads')
    parser.add_argument(
        '--data-file',
        help='Generic path to test data file')

    # Execution Control Parameters
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of operations per batch (default: 10)')
    parser.add_argument(
        '--max-batches',
        type=int,
        help='Maximum number of batches to run')
    parser.add_argument(
        '--workers',
        type=int,
        help='Number of concurrent workers/threads')
    parser.add_argument(
        '--replications',
        type=int,
        help='Number of test replications for load testing')
    parser.add_argument(
        '--timeout',
        type=int,
        help='Request timeout in seconds')
    parser.add_argument(
        '--delay',
        type=float,
        help='Delay between requests in seconds')

    # Browser/Execution Parameters
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (flag)')
    parser.add_argument(
        '--browser',
        choices=['chrome', 'firefox', 'safari', 'edge'],
        help='Browser type (chrome, firefox, etc.)')
    parser.add_argument(
        '--user-agent',
        help='Custom user agent string')
    parser.add_argument(
        '--proxy',
        help='Proxy server URL')
    parser.add_argument(
        '--proxy-file',
        help='Path to file containing proxy list')

    # Output and Reporting Parameters
    parser.add_argument(
        '--output-dir',
        help='Directory for output files')
    parser.add_argument(
        '--report-format',
        choices=['json', 'csv', 'html'],
        help='Report format (json, csv, html)')
    parser.add_argument(
        '--log-level',
        choices=['debug', 'info', 'warning', 'error'],
        help='Logging level (debug, info, warning, error)')
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output (flag)')
    parser.add_argument(
        '--silent',
        action='store_true',
        help='Suppress output except errors (flag)')

    # Test Control Parameters
    parser.add_argument(
        '--fail-fast',
        action='store_true',
        help='Stop immediately on first failure (flag)')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration without executing tests (flag)')
    parser.add_argument(
        '--test-type',
        choices=['load', 'security', 'functional'],
        help='Type of test to run (load, security, functional)')
    parser.add_argument(
        '--iterations',
        type=int,
        help='Number of test iterations')
    parser.add_argument(
        '--duration',
        type=int,
        help='Test duration in seconds')

    args = parser.parse_args()

    if check_url_available(args.url):
        if args.gate_versions:
            if check_version_in_response_header(args):
                ok = scythe_test_definition(args)
                sys.exit(0 if ok else 1)
            else:
                print("No compatible version found in response header.")
                sys.exit(1)
        else:
            ok = scythe_test_definition(args)
            sys.exit(0 if ok else 1)
    else:
        print("URL not available.")
        sys.exit(1)

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

_VERSION_RE = re.compile(r"['\"]?X-Scythe-Target-Version['\"]?\s*:\s*['\"]?([\w.-]+)['\"]?")
_DETECTED_LIST_RE = re.compile(r"Target versions detected:\s*\[?([^]]*)\]?")

def _parse_version_from_output(output: str) -> Optional[str]:
    m = _VERSION_RE.search(output)
    if m:
        return m.group(1)
    # Try from Detected target versions: ["1.2.3"] or like str(list)
    m = _DETECTED_LIST_RE.search(output)
    if m:
        inner = m.group(1)
        # extract first version-like token
        mv = re.search(r"\d+(?:\.[\w\-]+)+", inner)
        if mv:
            return mv.group(0)
    return None


def _run_test(project_root: str, name: str, extra_args: Optional[List[str]] = None) -> Tuple[int, str, Optional[str]]:
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

    # Normalize extra args (strip a leading "--" if provided as a separator)
    cmd_args: List[str] = []
    if extra_args:
        cmd_args = list(extra_args)
        if len(cmd_args) > 0 and cmd_args[0] == "--":
            cmd_args = cmd_args[1:]

    # Execute the test as a subprocess using the same interpreter
    proc = subprocess.run(
        [sys.executable, test_path, *cmd_args],
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


def _test_file_path(project_root: str, name: str) -> str:
    filename = name if name.endswith(".py") else f"{name}.py"
    return os.path.join(project_root, PROJECT_DIRNAME, TESTS_DIRNAME, filename)


def _read_compatible_versions_from_test(test_path: str) -> Optional[List[str]]:
    if not os.path.exists(test_path):
        return None
    try:
        with open(test_path, "r", encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src, filename=test_path)
    except Exception:
        return None

    versions: Optional[List[str]] = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            # handle simple assignment COMPATIBLE_VERSIONS = [...]
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "COMPATIBLE_VERSIONS":
                    val = node.value
                    if isinstance(val, (ast.List, ast.Tuple)):
                        items: List[str] = []
                        for elt in val.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                items.append(elt.value)
                            elif isinstance(elt, ast.Str):  # py<3.8 compatibility style
                                items.append(elt.s)
                            else:
                                # unsupported element type; abort parse gracefully
                                return None
                        versions = items
                    elif isinstance(val, ast.Constant) and val.value is None:
                        versions = []
                    else:
                        return None
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "COMPATIBLE_VERSIONS" and node.value is not None:
                val = node.value
                if isinstance(val, (ast.List, ast.Tuple)):
                    items: List[str] = []
                    for elt in val.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            items.append(elt.value)
                        elif isinstance(elt, ast.Str):
                            items.append(elt.s)
                        else:
                            return None
                    versions = items
                elif isinstance(val, ast.Constant) and val.value is None:
                    versions = []
                else:
                    return None
    return versions


def _update_test_compatible_versions(project_root: str, name: str, versions: Optional[List[str]]) -> None:
    filename = name if name.endswith(".py") else f"{name}.py"
    test_path_rel = os.path.relpath(_test_file_path(project_root, filename), project_root)
    conn = _open_db(project_root)
    try:
        cur = conn.cursor()
        compat_str = json.dumps(versions) if versions is not None else ""
        cur.execute(
            "UPDATE tests SET compatible_versions=? WHERE name=?",
            (compat_str, filename),
        )
        if cur.rowcount == 0:
            # Insert a row if it doesn't exist yet
            cur.execute(
                "INSERT OR REPLACE INTO tests(name, path, created_date, compatible_versions) VALUES(?,?,?,?)",
                (
                    filename,
                    test_path_rel,
                    datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    compat_str,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def _sync_compat(project_root: str, name: str) -> Optional[List[str]]:
    test_path = _test_file_path(project_root, name)
    if not os.path.exists(test_path):
        raise ScytheCLIError(f"Test not found: {test_path}")
    versions = _read_compatible_versions_from_test(test_path)
    _update_test_compatible_versions(project_root, name, versions)
    return versions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scythe", description="Scythe CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize a new .scythe project")
    p_init.add_argument("--path", default=".", help="Target directory (default: .)")

    p_new = sub.add_parser("new", help="Create a new test in scythe_tests")
    p_new.add_argument("name", help="Name of the test (e.g., login_smoke or login_smoke.py)")

    p_run = sub.add_parser("run", help="Run a test from scythe_tests and record the run")
    p_run.add_argument("name", help="Name of the test to run (e.g., login_smoke or login_smoke.py)")
    p_run.add_argument(
        "test_args",
        nargs=argparse.REMAINDER,
        help="Arguments to pass to the test script (use -- to separate)",
    )

    p_db = sub.add_parser("db", help="Database utilities")
    sub_db = p_db.add_subparsers(dest="db_cmd", required=True)
    sub_db.add_parser("dump", help="Dump tests and runs tables as JSON")
    p_sync = sub_db.add_parser("sync-compat", help="Sync COMPATIBLE_VERSIONS from a test file into the DB")
    p_sync.add_argument("name", help="Name of the test (e.g., login_smoke or login_smoke.py)")

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
            extra = getattr(args, "test_args", []) or []
            if extra and len(extra) > 0 and extra[0] == "--":
                extra = extra[1:]
            code, output, version = _run_test(project_root, args.name, extra)
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
            if args.db_cmd == "sync-compat":
                versions = _sync_compat(project_root, args.name)
                filename = args.name if args.name.endswith(".py") else f"{args.name}.py"
                if versions is None:
                    print(f"No COMPATIBLE_VERSIONS found in {filename}; DB updated with empty value.")
                else:
                    print(f"Updated {filename} compatible_versions to: {json.dumps(versions)}")
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

    app = typer.Typer(
        add_completion=True,
        no_args_is_help=True,
        pretty_exceptions_show_locals=False,
        help="Scythe CLI")

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

    @app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
    def run(
        ctx: typer.Context,
        name: str = typer.Argument(..., help="Name of the test to run (e.g., login_smoke or login_smoke.py)"),
        test_args: List[str] = typer.Argument(
            None,
            help="Arguments to pass to the test script (you can pass options directly or use -- to separate)",
            metavar="[-- ARGS...]",
        ),
    ) -> int:
        """Run a test from scythe_tests and record the run"""
        project_root = _find_project_root()
        if not project_root:
            raise ScytheCLIError("Not inside a Scythe project. Run 'scythe init' first.")
        extra: List[str] = []
        if test_args:
            extra.extend(list(test_args))
        if getattr(ctx, "args", None):
            extra.extend(list(ctx.args))
        if extra and len(extra) > 0 and extra[0] == "--":
            extra = extra[1:]
        code, output, version = _run_test(project_root, name, extra)
        _record_run(project_root, name, code, output, version)
        print(output)
        return code

    db_app = typer.Typer(
        no_args_is_help=True,
        help="Database utilities")

    @db_app.command("dump")
    def dump() -> int:
        """Dump tests and runs tables as JSON"""
        project_root = _find_project_root()
        if not project_root:
            raise ScytheCLIError("Not inside a Scythe project. Run 'scythe init' first.")
        data = _dump_db(project_root)
        print(json.dumps(data, indent=2))
        return 0

    @db_app.command("sync-compat")
    def sync_compat(
        name: str = typer.Argument(..., help="Name of the test (e.g., login_smoke or login_smoke.py)")
    ) -> int:
        """Sync COMPATIBLE_VERSIONS from a test file into the DB"""
        project_root = _find_project_root()
        if not project_root:
            raise ScytheCLIError("Not inside a Scythe project. Run 'scythe init' first.")
        versions = _sync_compat(project_root, name)
        filename = name if name.endswith(".py") else f"{name}.py"
        if versions is None:
            print(f"No COMPATIBLE_VERSIONS found in {filename}; DB updated with empty value.")
        else:
            print(f"Updated {filename} compatible_versions to: {json.dumps(versions)}")
        return 0

    app.add_typer(db_app, name="db")

    try:
        rv = app()
        return int(rv) if isinstance(rv, int) else 0
    except ScytheCLIError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except SystemExit as e:
        # should not occur with standalone_mode=False, but handle defensively
        return int(getattr(e, "code", 0) or 0)
