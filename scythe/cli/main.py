import argparse
import ast
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from scythe.cli.diagnostics import envelope, print_json_report
from scythe.cli.discover import discover_routes
from scythe.cli.doctor import run_ai_doctor
from scythe.cli.errors import build_error
from scythe.cli.fixers import apply_safe_fixes
from scythe.cli.intent import classify_intent
from scythe.cli.snippets import load_snippets, lookup_snippets
from scythe.fixtures.profiles import list_profiles, load_profile, load_profile_file

# Typer is used for the CLI. Import at module level for static analyzers; runtime guard in main.
try:
    import typer  # type: ignore
except Exception:  # pragma: no cover
    typer = None  # type: ignore


PROJECT_DIRNAME = ".scythe"
DB_FILENAME = "scythe.db"
TESTS_DIRNAME = "scythe_tests"
DEFAULT_TEST_KIND = "api-journey"


TEST_TEMPLATE_API_JOURNEY = """#!/usr/bin/env python3

import argparse
import sys
from typing import Optional, Tuple

from requests.exceptions import RequestException

from scythe.core.csrf import CSRFProtection
from scythe.journeys import ApiRequestAction, JourneyExecutor, Journey, Step

# defines which versions of the target software this test is compatible with
COMPATIBLE_VERSIONS = ["1.2.3"]


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--protocol", default="https", choices=["http", "https"], help="Target protocol")
    parser.add_argument("--port", type=int, help="Optional explicit target port")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds")
    parser.add_argument("--username", help="Optional username input")
    parser.add_argument("--password", help="Optional password input")
    parser.add_argument("--token", help="Optional bearer token input")
    parser.add_argument("--headless", action="store_true", help="Reserved for UI mode tests")
    parser.add_argument("--workers", type=int, help="Optional worker count")
    parser.add_argument("--replications", type=int, help="Optional replication count")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")


def check_url_available(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    import requests

    if not url or not str(url).strip():
        return False, "No URL provided (pass --url, e.g. --url https://demo.stellarbridge.app)", None

    normalized = str(url).strip()
    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        candidates = ["https://" + normalized, "http://" + normalized]
    else:
        candidates = [normalized]

    last_error = None
    for candidate in candidates:
        try:
            response = requests.get(candidate, timeout=15)
            if response.status_code < 500:
                return True, None, candidate.rstrip("/")
            last_error = "HTTP %s" % response.status_code
        except RequestException as exc:
            last_error = str(exc)

    return False, last_error, None


def check_version_in_response_header(args) -> bool:
    import requests

    url = args.url
    response = requests.get(url, timeout=max(1, int(getattr(args, "timeout", 15))))
    version = response.headers.get("x-scythe-target-version")

    if not version or version not in COMPATIBLE_VERSIONS:
        print("This test is not compatible with the target version in x-scythe-target-version.")
        print("Please update COMPATIBLE_VERSIONS in this script.")
        return False

    return True


def scythe_test_definition(args) -> int:
    csrf = CSRFProtection(
        extract_from="cookie",
        cookie_name="__Host-csrf_",
        header_name="X-Csrf-Token",
        inject_into="header",
    )

    test_public_routes = Step(
        name="Test public routes",
        description="Routes expected to be public",
        actions=[
            ApiRequestAction(
                method="GET",
                url="/api/v1/pricing",
                expected_status=200,
                expected_result=True,
            ),
        ],
    )

    test_private_routes = Step(
        name="Test private routes",
        description="Routes expected to require authentication",
        actions=[
            ApiRequestAction(
                method="GET",
                url="/api/v1/auth/me",
                expected_status=401,
                expected_result=True,
            ),
            ApiRequestAction(
                method="GET",
                url="/api/v1/dashboard/user/transfers/history",
                expected_status=401,
                expected_result=True,
            ),
        ],
    )

    journey = Journey(
        name="Route access policy",
        description="Validate public and private API route behavior",
        csrf_protection=csrf,
        steps=[test_private_routes, test_public_routes],
    )

    executor = JourneyExecutor(journey=journey, mode="API", target_url=args.url)
    executor.run()
    return executor.exit_code()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scythe API journey test")
    parser.add_argument("--url", help="Target URL")
    parser.add_argument(
        "--gate-versions",
        default=False,
        action="store_true",
        dest="gate_versions",
        help="Gate test execution by x-scythe-target-version",
    )
    add_common_args(parser)

    args = parser.parse_args()
    ok, error_message, resolved_url = check_url_available(args.url)

    if not ok:
        print("URL not available." + ((" " + error_message) if error_message else ""))
        sys.exit(1)

    if resolved_url:
        args.url = resolved_url

    if args.gate_versions and not check_version_in_response_header(args):
        print("No compatible version found in response header.")
        sys.exit(1)

    exit_code = scythe_test_definition(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
"""


TEST_TEMPLATE_API_AUTH_JOURNEY = """#!/usr/bin/env python3

import argparse
import sys
from typing import Optional, Tuple

from requests.exceptions import RequestException

from scythe.auth import CookieJWTAuth
from scythe.core.csrf import CSRFProtection
from scythe.journeys import Step, ApiRequestAction, Journey, JourneyExecutor

COMPATIBLE_VERSIONS = ["1.2.3"]


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds")
    parser.add_argument("--username", default="user@example.com", help="Login username/email")
    parser.add_argument("--password", default="ChangeMe123!", help="Login password")
    parser.add_argument("--auth-endpoint", default="/api/v1/auth/login-handler", help="Login endpoint path")
    parser.add_argument("--session-endpoint", default="/", help="Session warmup endpoint path")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")


def check_url_available(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    import requests

    if not url or not str(url).strip():
        return False, "No URL provided (pass --url, e.g. --url https://demo.stellarbridge.app)", None

    normalized = str(url).strip()
    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        candidates = ["https://" + normalized, "http://" + normalized]
    else:
        candidates = [normalized]

    last_error = None
    for candidate in candidates:
        try:
            response = requests.get(candidate, timeout=15)
            if response.status_code < 500:
                return True, None, candidate.rstrip("/")
            last_error = "HTTP %s" % response.status_code
        except RequestException as exc:
            last_error = str(exc)

    return False, last_error, None


def check_version_in_response_header(args) -> bool:
    import requests

    response = requests.get(args.url, timeout=max(1, int(getattr(args, "timeout", 15))))
    version = response.headers.get("x-scythe-target-version")
    if not version or version not in COMPATIBLE_VERSIONS:
        print("This test is not compatible with the target version in x-scythe-target-version.")
        print("Please update COMPATIBLE_VERSIONS in this script.")
        return False
    return True


def scythe_test_definition(args) -> int:
    csrf = CSRFProtection(
        extract_from="cookie",
        cookie_name="__Host-csrf_",
        header_name="X-Csrf-Token",
        inject_into="header",
    )

    auth = CookieJWTAuth(
        login_url="%s%s" % (args.url, args.auth_endpoint),
        username_field="email",
        password_field="password",
        username=args.username,
        password=args.password,
        cookie_name="stellarbridge",
        jwt_source="cookie",
        content_type="json",
        csrf_protection=csrf,
        session_endpoint="%s%s" % (args.url, args.session_endpoint),
    )

    test_authenticated_access = Step(
        name="Authenticated access",
        description="Protected endpoint should be reachable after login",
        actions=[
            ApiRequestAction(
                method="GET",
                url="/api/v1/dashboard/user/transfers/history",
                expected_status=200,
                expected_result=True,
            )
        ],
    )

    journey = Journey(
        name="Authenticated API journey",
        description="Validate a protected route with cookie JWT auth",
        authentication=auth,
        steps=[test_authenticated_access],
        csrf_protection=csrf,
    )

    executor = JourneyExecutor(journey=journey, mode="API", target_url=args.url)
    executor.run()
    return executor.exit_code()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scythe authenticated API journey test")
    parser.add_argument("--url", help="Target URL")
    parser.add_argument(
        "--gate-versions",
        default=False,
        action="store_true",
        dest="gate_versions",
        help="Gate test execution by x-scythe-target-version",
    )
    add_common_args(parser)

    args = parser.parse_args()
    ok, error_message, resolved_url = check_url_available(args.url)
    if not ok:
        print("URL not available." + ((" " + error_message) if error_message else ""))
        sys.exit(1)

    if resolved_url:
        args.url = resolved_url

    if args.gate_versions and not check_version_in_response_header(args):
        print("No compatible version found in response header.")
        sys.exit(1)

    exit_code = scythe_test_definition(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
"""


TEST_TEMPLATE_TTP_API = """#!/usr/bin/env python3

import argparse
import sys
from typing import Optional, Tuple

from requests.exceptions import RequestException

from scythe.core.executor import TTPExecutor
from scythe.payloads.generators import StaticPayloadGenerator
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP

COMPATIBLE_VERSIONS = ["1.2.3"]


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds")
    parser.add_argument("--username", default="admin", help="Username to test")
    parser.add_argument("--api-endpoint", default="/api/v1/auth/login-handler", help="Login API endpoint path")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")


def check_url_available(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    import requests

    if not url or not str(url).strip():
        return False, "No URL provided (pass --url, e.g. --url https://demo.stellarbridge.app)", None

    normalized = str(url).strip()
    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        candidates = ["https://" + normalized, "http://" + normalized]
    else:
        candidates = [normalized]

    last_error = None
    for candidate in candidates:
        try:
            response = requests.get(candidate, timeout=15)
            if response.status_code < 500:
                return True, None, candidate.rstrip("/")
            last_error = "HTTP %s" % response.status_code
        except RequestException as exc:
            last_error = str(exc)

    return False, last_error, None


def check_version_in_response_header(args) -> bool:
    import requests

    response = requests.get(args.url, timeout=max(1, int(getattr(args, "timeout", 15))))
    version = response.headers.get("x-scythe-target-version")
    if not version or version not in COMPATIBLE_VERSIONS:
        print("This test is not compatible with the target version in x-scythe-target-version.")
        print("Please update COMPATIBLE_VERSIONS in this script.")
        return False
    return True


def scythe_test_definition(args) -> int:
    password_gen = StaticPayloadGenerator(["password", "123456", "admin"])

    login_ttp = LoginBruteforceTTP(
        payload_generator=password_gen,
        username=args.username,
        execution_mode="api",
        api_endpoint=args.api_endpoint,
        username_field="email",
        password_field="password",
        success_indicators={"status_code": 200, "response_contains": "token"},
        expected_result=False,
    )

    executor = TTPExecutor(ttp=login_ttp, target_url=args.url, headless=True)
    executor.run()
    return executor.exit_code()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scythe API TTP test")
    parser.add_argument("--url", help="Target URL")
    parser.add_argument(
        "--gate-versions",
        default=False,
        action="store_true",
        dest="gate_versions",
        help="Gate test execution by x-scythe-target-version",
    )
    add_common_args(parser)

    args = parser.parse_args()
    ok, error_message, resolved_url = check_url_available(args.url)
    if not ok:
        print("URL not available." + ((" " + error_message) if error_message else ""))
        sys.exit(1)

    if resolved_url:
        args.url = resolved_url

    if args.gate_versions and not check_version_in_response_header(args):
        print("No compatible version found in response header.")
        sys.exit(1)

    exit_code = scythe_test_definition(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
"""


TEST_TEMPLATE_SB_ROUTE_MATRIX = """#!/usr/bin/env python3

import argparse
import sys
from typing import Optional, Tuple

from requests.exceptions import RequestException

from scythe.core.csrf import CSRFProtection
from scythe.journeys import ApiRequestAction, JourneyExecutor, Journey, Step

# defines which target versions this test supports
COMPATIBLE_VERSIONS = ["1.2.3"]


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds")
    parser.add_argument("--protocol", default="https", choices=["http", "https"], help="Target protocol")
    parser.add_argument("--port", type=int, help="Optional explicit target port")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")


def check_url_available(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    import requests

    if not url or not str(url).strip():
        return False, "No URL provided (pass --url)", None

    normalized = str(url).strip()
    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        candidates = ["https://" + normalized, "http://" + normalized]
    else:
        candidates = [normalized]

    last_error = None
    for candidate in candidates:
        try:
            response = requests.get(candidate, timeout=15)
            if response.status_code < 500:
                return True, None, candidate.rstrip("/")
            last_error = "HTTP %s" % response.status_code
        except RequestException as exc:
            last_error = str(exc)

    return False, last_error, None


def check_version_in_response_header(args) -> bool:
    import requests

    response = requests.get(args.url, timeout=max(1, int(getattr(args, "timeout", 15))))
    version = response.headers.get("x-scythe-target-version")
    if not version or version not in COMPATIBLE_VERSIONS:
        print("This test is not compatible with the target version in x-scythe-target-version.")
        print("Please update COMPATIBLE_VERSIONS in this script.")
        return False
    return True


def scythe_test_definition(args) -> int:
    csrf = CSRFProtection(
        extract_from="cookie",
        cookie_name="__Host-csrf_",
        header_name="X-Csrf-Token",
        inject_into="header",
    )

    test_public_routes = Step(
        name="Test public routes",
        description="Public endpoints should be accessible",
        actions=[
            ApiRequestAction(method="GET", url="/api/v1/pricing", expected_status=200, expected_result=True),
        ],
    )

    test_public_authz_required_routes = Step(
        name="Test public authz-required routes",
        description="Public endpoints still requiring authorization",
        actions=[
            ApiRequestAction(
                method="GET",
                url="/api/v1/public/download/info/fixture-transfer-id",
                expected_status=401,
                expected_result=True,
            ),
        ],
    )

    test_private_routes = Step(
        name="Test private routes",
        description="Private routes should reject anonymous access",
        actions=[
            ApiRequestAction(method="GET", url="/api/v1/auth/me", expected_status=401, expected_result=True),
            ApiRequestAction(
                method="GET",
                url="/api/v1/dashboard/user/transfers/history",
                expected_status=401,
                expected_result=True,
            ),
            ApiRequestAction(
                method="GET",
                url="/api/v1/dashboard/organization/users",
                expected_status=401,
                expected_result=True,
            ),
        ],
    )

    journey = Journey(
        name="Route matrix",
        description="Validate access policy across route categories",
        steps=[test_public_authz_required_routes, test_private_routes, test_public_routes],
        csrf_protection=csrf,
    )

    executor = JourneyExecutor(journey=journey, mode="API", target_url=args.url)
    executor.run()
    return executor.exit_code()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scythe route matrix test")
    parser.add_argument("--url", help="Target URL")
    parser.add_argument(
        "--gate-versions",
        default=False,
        action="store_true",
        dest="gate_versions",
        help="Gate test execution by x-scythe-target-version",
    )
    add_common_args(parser)

    args = parser.parse_args()
    ok, error_message, resolved_url = check_url_available(args.url)
    if not ok:
        print("URL not available." + ((" " + error_message) if error_message else ""))
        sys.exit(1)

    if resolved_url:
        args.url = resolved_url

    if args.gate_versions and not check_version_in_response_header(args):
        print("No compatible version found in response header.")
        sys.exit(1)

    exit_code = scythe_test_definition(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
"""


TEST_TEMPLATE_SB_MFA_GATE = """#!/usr/bin/env python3

import argparse
import sys
from typing import Optional, Tuple

from requests.exceptions import RequestException

from scythe.auth import CookieJWTAuth
from scythe.core.csrf import CSRFProtection
from scythe.journeys import Step, ApiRequestAction, Journey, JourneyExecutor

COMPATIBLE_VERSIONS = ["1.2.3"]


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds")
    parser.add_argument("--username", default="user@example.com", help="Login username/email")
    parser.add_argument("--password", default="ChangeMe123!", help="Login password")
    parser.add_argument("--auth-endpoint", default="/api/v1/auth/login-handler", help="Login endpoint path")
    parser.add_argument("--session-endpoint", default="/", help="Session endpoint path")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")


def check_url_available(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    import requests

    if not url or not str(url).strip():
        return False, "No URL provided (pass --url)", None

    normalized = str(url).strip()
    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        candidates = ["https://" + normalized, "http://" + normalized]
    else:
        candidates = [normalized]

    last_error = None
    for candidate in candidates:
        try:
            response = requests.get(candidate, timeout=15)
            if response.status_code < 500:
                return True, None, candidate.rstrip("/")
            last_error = "HTTP %s" % response.status_code
        except RequestException as exc:
            last_error = str(exc)

    return False, last_error, None


def check_version_in_response_header(args) -> bool:
    import requests

    response = requests.get(args.url, timeout=max(1, int(getattr(args, "timeout", 15))))
    version = response.headers.get("x-scythe-target-version")
    if not version or version not in COMPATIBLE_VERSIONS:
        print("This test is not compatible with the target version in x-scythe-target-version.")
        print("Please update COMPATIBLE_VERSIONS in this script.")
        return False
    return True


def scythe_test_definition(args) -> int:
    csrf = CSRFProtection(
        extract_from="cookie",
        cookie_name="__Host-csrf_",
        header_name="X-Csrf-Token",
        inject_into="header",
    )

    auth = CookieJWTAuth(
        login_url="%s%s" % (args.url, args.auth_endpoint),
        username_field="email",
        password_field="password",
        username=args.username,
        password=args.password,
        cookie_name="stellarbridge",
        jwt_source="cookie",
        content_type="json",
        csrf_protection=csrf,
        session_endpoint="%s%s" % (args.url, args.session_endpoint),
    )

    test_mfa_policy = Step(
        name="MFA policy enforcement",
        description="Authenticated but MFA-noncompliant user should be blocked",
        actions=[
            ApiRequestAction(
                method="GET",
                url="/api/v1/dashboard/security/mfa-enforcement",
                expected_status=403,
                expected_result=True,
            ),
        ],
    )

    journey = Journey(
        name="MFA gate",
        description="Ensure restricted access for MFA non-compliance",
        authentication=auth,
        steps=[test_mfa_policy],
        csrf_protection=csrf,
    )

    executor = JourneyExecutor(journey=journey, mode="API", target_url=args.url)
    executor.run()
    return executor.exit_code()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scythe MFA enforcement test")
    parser.add_argument("--url", help="Target URL")
    parser.add_argument(
        "--gate-versions",
        default=False,
        action="store_true",
        dest="gate_versions",
        help="Gate test execution by x-scythe-target-version",
    )
    add_common_args(parser)

    args = parser.parse_args()
    ok, error_message, resolved_url = check_url_available(args.url)
    if not ok:
        print("URL not available." + ((" " + error_message) if error_message else ""))
        sys.exit(1)

    if resolved_url:
        args.url = resolved_url

    if args.gate_versions and not check_version_in_response_header(args):
        print("No compatible version found in response header.")
        sys.exit(1)

    exit_code = scythe_test_definition(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
"""


TEST_TEMPLATE_SB_ORG_RBAC = """#!/usr/bin/env python3

import argparse
import sys
from typing import Optional, Tuple

from requests.exceptions import RequestException

from scythe.auth import CookieJWTAuth
from scythe.core.csrf import CSRFProtection
from scythe.journeys import Step, ApiRequestAction, Journey, JourneyExecutor

COMPATIBLE_VERSIONS = ["1.2.3"]


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds")
    parser.add_argument("--username", default="user@example.com", help="Login username/email")
    parser.add_argument("--password", default="ChangeMe123!", help="Login password")
    parser.add_argument("--auth-endpoint", default="/api/v1/auth/login-handler", help="Login endpoint path")
    parser.add_argument("--session-endpoint", default="/", help="Session endpoint path")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")


def check_url_available(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    import requests

    if not url or not str(url).strip():
        return False, "No URL provided (pass --url)", None

    normalized = str(url).strip()
    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        candidates = ["https://" + normalized, "http://" + normalized]
    else:
        candidates = [normalized]

    last_error = None
    for candidate in candidates:
        try:
            response = requests.get(candidate, timeout=15)
            if response.status_code < 500:
                return True, None, candidate.rstrip("/")
            last_error = "HTTP %s" % response.status_code
        except RequestException as exc:
            last_error = str(exc)

    return False, last_error, None


def check_version_in_response_header(args) -> bool:
    import requests

    response = requests.get(args.url, timeout=max(1, int(getattr(args, "timeout", 15))))
    version = response.headers.get("x-scythe-target-version")
    if not version or version not in COMPATIBLE_VERSIONS:
        print("This test is not compatible with the target version in x-scythe-target-version.")
        print("Please update COMPATIBLE_VERSIONS in this script.")
        return False
    return True


def scythe_test_definition(args) -> int:
    csrf = CSRFProtection(
        extract_from="cookie",
        cookie_name="__Host-csrf_",
        header_name="X-Csrf-Token",
        inject_into="header",
    )

    auth = CookieJWTAuth(
        login_url="%s%s" % (args.url, args.auth_endpoint),
        username_field="email",
        password_field="password",
        username=args.username,
        password=args.password,
        cookie_name="stellarbridge",
        jwt_source="cookie",
        content_type="json",
        csrf_protection=csrf,
        session_endpoint="%s%s" % (args.url, args.session_endpoint),
    )

    test_org_rbac = Step(
        name="Org RBAC",
        description="User should read org info but be denied admin-only org routes",
        actions=[
            ApiRequestAction(
                method="GET",
                url="/api/v1/dashboard/organization/user-org-info",
                expected_status=200,
                expected_result=True,
            ),
            ApiRequestAction(
                method="GET",
                url="/api/v1/dashboard/organization/users",
                expected_status=403,
                expected_result=True,
            ),
        ],
    )

    journey = Journey(
        name="Organization RBAC",
        description="Validate RBAC constraints for organization endpoints",
        authentication=auth,
        steps=[test_org_rbac],
        csrf_protection=csrf,
    )

    executor = JourneyExecutor(journey=journey, mode="API", target_url=args.url)
    executor.run()
    return executor.exit_code()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scythe organization RBAC test")
    parser.add_argument("--url", help="Target URL")
    parser.add_argument(
        "--gate-versions",
        default=False,
        action="store_true",
        dest="gate_versions",
        help="Gate test execution by x-scythe-target-version",
    )
    add_common_args(parser)

    args = parser.parse_args()
    ok, error_message, resolved_url = check_url_available(args.url)
    if not ok:
        print("URL not available." + ((" " + error_message) if error_message else ""))
        sys.exit(1)

    if resolved_url:
        args.url = resolved_url

    if args.gate_versions and not check_version_in_response_header(args):
        print("No compatible version found in response header.")
        sys.exit(1)

    exit_code = scythe_test_definition(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
"""

TEST_TEMPLATE_PLAYWRIGHT_RUN = """#!/usr/bin/env python3

import argparse
import sys
from typing import Optional, Tuple

from requests.exceptions import RequestException

# defines which versions of the target software this test is compatible with
COMPATIBLE_VERSIONS = ["1.2.3"]


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--protocol", default="https", choices=["http", "https"], help="Target protocol")
    parser.add_argument("--port", type=int, help="Optional explicit target port")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds")
    parser.add_argument("--username", help="Optional username input")
    parser.add_argument("--password", help="Optional password input")
    parser.add_argument("--token", help="Optional bearer token input")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--browser", default="chromium", choices=["chromium", "firefox", "webkit"], help="Browser engine")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")


def check_url_available(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    import requests

    if not url or not str(url).strip():
        return False, "No URL provided (pass --url, e.g. --url https://demo.stellarbridge.app)", None

    normalized = str(url).strip()
    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        candidates = ["https://" + normalized, "http://" + normalized]
    else:
        candidates = [normalized]

    last_error = None
    for candidate in candidates:
        try:
            response = requests.get(candidate, timeout=15)
            if response.status_code < 500:
                return True, None, candidate.rstrip("/")
            last_error = "HTTP %s" % response.status_code
        except RequestException as exc:
            last_error = str(exc)

    return False, last_error, None


def check_version_in_response_header(args) -> bool:
    import requests

    url = args.url
    response = requests.get(url, timeout=max(1, int(getattr(args, "timeout", 15))))
    version = response.headers.get("x-scythe-target-version")

    if not version or version not in COMPATIBLE_VERSIONS:
        print("This test is not compatible with the target version in x-scythe-target-version.")
        print("Please update COMPATIBLE_VERSIONS in this script.")
        return False

    return True


def scythe_test_definition(args) -> int:
    from scythe.playwright import Run

    # Run an existing pytest-playwright test file and assert results.
    # Replace the test_file path with your actual Playwright test.
    runner = Run(
        "tests/test_example.py",
        browser=args.browser,
        headed=not args.headless,
        env={"BASE_URL": args.url},
    )

    result = runner.execute()

    print(f"Playwright tests: {result.passed_count} passed, {result.failed_count} failed, {result.skipped_count} skipped")

    if result.errors:
        for err in result.errors[:5]:
            print(f"  ERROR: {err}")

    # Return 0 if tests match expectations, 1 otherwise
    if result.passed:
        print("All Playwright tests passed.")
        return 0
    else:
        print("Some Playwright tests failed.")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Scythe Playwright Run Test")
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--gate-versions", action="store_true", help="Gate on compatible version header")
    add_common_args(parser)
    args = parser.parse_args()

    ok, error, resolved_url = check_url_available(args.url)
    if not ok:
        print(f"URL not available: {error}")
        sys.exit(1)

    if resolved_url:
        args.url = resolved_url

    if args.gate_versions and not check_version_in_response_header(args):
        print("No compatible version found in response header.")
        sys.exit(1)

    exit_code = scythe_test_definition(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
"""

TEST_TEMPLATE_PLAYWRIGHT_WRAP = """#!/usr/bin/env python3

import argparse
import sys
from typing import Optional, Tuple

from requests.exceptions import RequestException

# defines which versions of the target software this test is compatible with
COMPATIBLE_VERSIONS = ["1.2.3"]


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--protocol", default="https", choices=["http", "https"], help="Target protocol")
    parser.add_argument("--port", type=int, help="Optional explicit target port")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds")
    parser.add_argument("--username", help="Optional username input")
    parser.add_argument("--password", help="Optional password input")
    parser.add_argument("--token", help="Optional bearer token input")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--browser", default="chromium", choices=["chromium", "firefox", "webkit"], help="Browser engine")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")


def check_url_available(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    import requests

    if not url or not str(url).strip():
        return False, "No URL provided (pass --url, e.g. --url https://demo.stellarbridge.app)", None

    normalized = str(url).strip()
    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        candidates = ["https://" + normalized, "http://" + normalized]
    else:
        candidates = [normalized]

    last_error = None
    for candidate in candidates:
        try:
            response = requests.get(candidate, timeout=15)
            if response.status_code < 500:
                return True, None, candidate.rstrip("/")
            last_error = "HTTP %s" % response.status_code
        except RequestException as exc:
            last_error = str(exc)

    return False, last_error, None


def check_version_in_response_header(args) -> bool:
    import requests

    url = args.url
    response = requests.get(url, timeout=max(1, int(getattr(args, "timeout", 15))))
    version = response.headers.get("x-scythe-target-version")

    if not version or version not in COMPATIBLE_VERSIONS:
        print("This test is not compatible with the target version in x-scythe-target-version.")
        print("Please update COMPATIBLE_VERSIONS in this script.")
        return False

    return True


def scythe_test_definition(args) -> int:
    from scythe.playwright import Wrap

    # Use Playwright's sync API directly with scythe lifecycle hooks.
    # Customize the browser interactions below for your test.
    try:
        with Wrap(headless=args.headless, browser_type=args.browser) as pw:
            pw.page.goto(f"{args.url}/")

            # Example: verify the page loaded
            pw.expect_element_visible("body")

            # TODO: Add your Playwright test logic here
            # pw.page.fill("#username", args.username or "admin")
            # pw.page.fill("#password", args.password or "password")
            # pw.page.click("button[type=submit]")
            # pw.expect_url_contains("/dashboard")

            print(f"Page loaded: {pw.page.url}")
            print(f"Assertions passed: {len(pw.assertions)}")
            return 0

    except Exception as e:
        print(f"Playwright test failed: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Scythe Playwright Wrap Test")
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--gate-versions", action="store_true", help="Gate on compatible version header")
    add_common_args(parser)
    args = parser.parse_args()

    ok, error, resolved_url = check_url_available(args.url)
    if not ok:
        print(f"URL not available: {error}")
        sys.exit(1)

    if resolved_url:
        args.url = resolved_url

    if args.gate_versions and not check_version_in_response_header(args):
        print("No compatible version found in response header.")
        sys.exit(1)

    exit_code = scythe_test_definition(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
"""


TEST_TEMPLATES: Dict[str, str] = {
    "api-journey": TEST_TEMPLATE_API_JOURNEY,
    "api-auth-journey": TEST_TEMPLATE_API_AUTH_JOURNEY,
    "ttp-api": TEST_TEMPLATE_TTP_API,
    "playwright-run": TEST_TEMPLATE_PLAYWRIGHT_RUN,
    "playwright-wrap": TEST_TEMPLATE_PLAYWRIGHT_WRAP,
    "sb-route-matrix": TEST_TEMPLATE_SB_ROUTE_MATRIX,
    "sb-mfa-gate": TEST_TEMPLATE_SB_MFA_GATE,
    "sb-org-rbac": TEST_TEMPLATE_SB_ORG_RBAC,
}


class ScytheCLIError(Exception):
    pass


class ExitWithCode(Exception):
    """Exception to exit with a specific code from within Typer commands."""

    def __init__(self, code: int):
        self.code = code
        super().__init__()


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


def _create_test(project_root: str, name: str, kind: str = DEFAULT_TEST_KIND) -> str:
    if not name:
        raise ScytheCLIError("Test name is required")
    template = TEST_TEMPLATES.get(kind)
    if template is None:
        options = ", ".join(sorted(TEST_TEMPLATES.keys()))
        raise ScytheCLIError(
            f"Unknown test template kind '{kind}'. Available kinds: {options}"
        )
    filename = name if name.endswith(".py") else f"{name}.py"
    tests_dir = os.path.join(project_root, PROJECT_DIRNAME, TESTS_DIRNAME)
    os.makedirs(tests_dir, exist_ok=True)
    filepath = os.path.join(tests_dir, filename)
    if os.path.exists(filepath):
        raise ScytheCLIError(f"Test already exists: {filepath}")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(template)
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


_VERSION_RE = re.compile(
    r"['\"]?X-Scythe-Target-Version['\"]?\s*:\s*['\"]?([\w.-]+)['\"]?"
)
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


def _run_test(
    project_root: str, name: str, extra_args: Optional[List[str]] = None
) -> Tuple[int, str, Optional[str]]:
    filename = name if name.endswith(".py") else f"{name}.py"
    test_path = os.path.join(project_root, PROJECT_DIRNAME, TESTS_DIRNAME, filename)
    if not os.path.exists(test_path):
        raise ScytheCLIError(f"Test not found: {test_path}")

    # Ensure the subprocess can import the in-repo scythe package when running from a temp project
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    if repo_root not in existing_pp.split(os.pathsep):
        env["PYTHONPATH"] = os.pathsep.join([p for p in [existing_pp, repo_root] if p])

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


def _record_run(
    project_root: str, name: str, code: int, output: str, version: Optional[str]
) -> None:
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
                            if isinstance(elt, ast.Constant) and isinstance(
                                elt.value, str
                            ):
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
            if (
                isinstance(node.target, ast.Name)
                and node.target.id == "COMPATIBLE_VERSIONS"
                and node.value is not None
            ):
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


def _update_test_compatible_versions(
    project_root: str, name: str, versions: Optional[List[str]]
) -> None:
    filename = name if name.endswith(".py") else f"{name}.py"
    test_path_rel = os.path.relpath(
        _test_file_path(project_root, filename), project_root
    )
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


def _resolve_test_reference(project_root: Optional[str], name: str) -> str:
    if not name:
        raise ScytheCLIError("Test name or path is required")

    if os.path.isabs(name):
        return name

    if os.path.exists(name):
        return os.path.abspath(name)

    if os.path.sep in name:
        return os.path.abspath(name)

    if project_root:
        return _test_file_path(project_root, name)

    return os.path.abspath(name if name.endswith(".py") else f"{name}.py")


def _make_diagnostic(
    code: str,
    message: str,
    line: Optional[int] = None,
    hint: Optional[str] = None,
) -> Dict[str, Any]:
    entry: Dict[str, Any] = {"code": code, "message": message}
    if line is not None:
        entry["line"] = line
    if hint:
        entry["hint"] = hint
    return entry


def _validate_test_file(test_path: str) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "path": test_path,
        "ok": False,
        "errors": [],
        "warnings": [],
    }

    def add_error(
        code: str, message: str, line: Optional[int] = None, hint: Optional[str] = None
    ) -> None:
        report["errors"].append(_make_diagnostic(code, message, line, hint))

    def add_warning(
        code: str, message: str, line: Optional[int] = None, hint: Optional[str] = None
    ) -> None:
        report["warnings"].append(_make_diagnostic(code, message, line, hint))

    if not os.path.exists(test_path):
        add_error(
            "test_not_found",
            f"Test file not found: {test_path}",
            hint="Use `scythe new <name>` or pass an existing file path.",
        )
        return report

    try:
        with open(test_path, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError as exc:
        add_error("read_error", f"Failed reading test file: {exc}")
        return report

    try:
        tree = ast.parse(source, filename=test_path)
    except SyntaxError as exc:
        add_error(
            "syntax_error",
            exc.msg,
            line=exc.lineno,
            hint="Fix syntax errors before running `scythe run`.",
        )
        return report

    versions = _read_compatible_versions_from_test(test_path)
    if versions is None:
        add_error(
            "compatible_versions_missing_or_invalid",
            "Missing or invalid COMPATIBLE_VERSIONS assignment.",
            hint='Define `COMPATIBLE_VERSIONS = ["1.2.3"]` near the top of the file.',
        )
    elif not versions:
        add_warning(
            "compatible_versions_empty",
            "COMPATIBLE_VERSIONS is empty; version gating may reject all runs.",
        )

    has_url_arg = re.search(r"add_argument\(\s*['\"]--url['\"]", source) is not None
    if not has_url_arg:
        add_error(
            "url_arg_missing",
            "CLI parser does not define --url.",
            hint="Add `parser.add_argument('--url', help='Target URL')` in main().",
        )

    function_defs: Dict[str, ast.FunctionDef] = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }

    test_fn = function_defs.get("scythe_test_definition")
    if not test_fn:
        add_error(
            "missing_test_definition",
            "Missing `scythe_test_definition(args)` function.",
            hint="Define this function and return an integer exit code.",
        )
    else:
        arg_count = len(test_fn.args.args)
        if arg_count != 1:
            add_error(
                "test_definition_signature",
                "`scythe_test_definition` must accept exactly one argument (`args`).",
                line=test_fn.lineno,
            )

        has_int_return_annotation = (
            isinstance(test_fn.returns, ast.Name) and test_fn.returns.id == "int"
        )
        if not has_int_return_annotation:
            add_warning(
                "missing_int_return_annotation",
                "`scythe_test_definition` should be annotated as returning int.",
                line=test_fn.lineno,
                hint="Use `def scythe_test_definition(args) -> int:`.",
            )

        has_return_statement = any(
            isinstance(node, ast.Return) for node in ast.walk(test_fn)
        )
        if not has_return_statement:
            add_error(
                "missing_return",
                "`scythe_test_definition` must return an integer exit code.",
                line=test_fn.lineno,
            )

    main_fn = function_defs.get("main")
    if not main_fn:
        add_error(
            "missing_main",
            "Missing `main()` function.",
            hint="Define `main()` that parses args and calls `scythe_test_definition(args)`.",
        )
    else:
        if len(main_fn.args.args) != 0:
            add_warning(
                "main_signature",
                "`main` usually takes no arguments in Scythe test scripts.",
                line=main_fn.lineno,
            )

    has_main_guard = False
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare):
            continue
        if not (isinstance(test.left, ast.Name) and test.left.id == "__name__"):
            continue
        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
            continue
        if len(test.comparators) != 1:
            continue

        comparator = test.comparators[0]
        comparator_value = None
        if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
            comparator_value = comparator.value
        elif isinstance(comparator, ast.Str):
            comparator_value = comparator.s

        if comparator_value != "__main__":
            continue

        for body_node in node.body:
            if isinstance(body_node, ast.Expr) and isinstance(
                body_node.value, ast.Call
            ):
                called = body_node.value.func
                if isinstance(called, ast.Name) and called.id == "main":
                    has_main_guard = True
                    break
        if has_main_guard:
            break

    if not has_main_guard:
        add_warning(
            "main_guard_missing",
            'Missing `if __name__ == "__main__": main()` guard.',
        )

    report["ok"] = len(report["errors"]) == 0
    return report


def _apply_validation_fixes(test_path: str) -> List[str]:
    if not os.path.exists(test_path):
        raise ScytheCLIError(f"Test file not found: {test_path}")
    try:
        with open(test_path, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError as exc:
        raise ScytheCLIError(f"Unable to read test file for fix: {exc}")

    fixed = apply_safe_fixes(source)
    updated_source = str(fixed.get("source", source))
    applied = [str(item) for item in fixed.get("applied", [])]
    if not applied:
        return []

    try:
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(updated_source)
    except OSError as exc:
        raise ScytheCLIError(f"Unable to write fixes to test file: {exc}")

    return applied


def _print_validation_report(report: Dict[str, Any], as_json: bool = False) -> None:
    if as_json:
        report_copy = dict(report)
        print_json_report(report_copy)
        return

    status = "PASS" if report.get("ok") else "FAIL"
    print(f"Validation {status}: {report.get('path', '')}")

    for error in report.get("errors", []):
        line = f" (line {error['line']})" if "line" in error else ""
        print(
            f"[ERROR] {error.get('code', 'unknown')}{line}: {error.get('message', '')}"
        )
        if error.get("hint"):
            print(f"        hint: {error['hint']}")

    for warning in report.get("warnings", []):
        line = f" (line {warning['line']})" if "line" in warning else ""
        print(
            f"[WARN] {warning.get('code', 'unknown')}{line}: {warning.get('message', '')}"
        )
        if warning.get("hint"):
            print(f"       hint: {warning['hint']}")


def _validation_ok(report: Dict[str, Any], strict: bool = False) -> bool:
    if not report.get("ok"):
        return False
    if strict and report.get("warnings"):
        return False
    return True


def _serve_fixture(
    host: str = "127.0.0.1",
    port: int = 8787,
    version: str = "1.2.3",
    username: str = "user@example.com",
    password: str = "ChangeMe123!",
    token: str = "fixture-token",
    max_requests: Optional[int] = None,
    profile: str = "minimal",
    profile_data: Optional[Dict[str, Any]] = None,
) -> int:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading

    if max_requests is not None and max_requests <= 0:
        raise ScytheCLIError("--max-requests must be greater than zero")

    active_profile = profile_data or {}
    route_entries = (
        active_profile.get("routes", []) if isinstance(active_profile, dict) else []
    )
    login_config = (
        active_profile.get("login", {}) if isinstance(active_profile, dict) else {}
    )

    class FixtureHandler(BaseHTTPRequestHandler):
        server_version = "ScytheFixture/1.0"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_json(
            self,
            status: int,
            payload: Dict[str, Any],
            extra_cookies: Optional[List[str]] = None,
        ) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-SCYTHE-TARGET-VERSION", version)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Set-Cookie", "__Host-csrf_=fixture-csrf-token; Path=/")
            if extra_cookies:
                for cookie_value in extra_cookies:
                    self.send_header("Set-Cookie", cookie_value)
            self.end_headers()
            self.wfile.write(body)

        def _cookie_map(self) -> Dict[str, str]:
            raw = self.headers.get("Cookie", "")
            cookies: Dict[str, str] = {}
            for part in raw.split(";"):
                item = part.strip()
                if not item or "=" not in item:
                    continue
                key, value = item.split("=", 1)
                cookies[key.strip()] = value.strip()
            return cookies

        def _is_authenticated(self) -> bool:
            return self._cookie_map().get("stellarbridge") == token

        def _find_route(self, method: str, path: str) -> Optional[Dict[str, Any]]:
            for entry in route_entries:
                if not isinstance(entry, dict):
                    continue
                if str(entry.get("method", "")).upper() != method.upper():
                    continue
                if str(entry.get("path", "")) == path:
                    return entry
            return None

        def _render_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            rendered: Dict[str, Any] = {}
            for key, value in payload.items():
                if isinstance(value, str) and value == "$username":
                    rendered[key] = username
                else:
                    rendered[key] = value
            return rendered

        def _read_json(self) -> Dict[str, Any]:
            length_raw = self.headers.get("Content-Length")
            if not length_raw:
                return {}
            try:
                length = int(length_raw)
            except ValueError:
                return {}
            if length <= 0:
                return {}
            payload = self.rfile.read(length)
            if not payload:
                return {}
            try:
                parsed = json.loads(payload.decode("utf-8"))
            except json.JSONDecodeError:
                return {}
            if isinstance(parsed, dict):
                return parsed
            return {}

        def _bump_and_maybe_shutdown(self) -> None:
            server = self.server
            count = getattr(server, "_scythe_request_count", 0) + 1
            setattr(server, "_scythe_request_count", count)
            limit = getattr(server, "_scythe_max_requests", None)
            if limit is not None and count >= limit:
                threading.Thread(target=server.shutdown, daemon=True).start()

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            is_authenticated = self._is_authenticated()

            matched = self._find_route("GET", path)
            if matched:
                auth = matched.get("auth")
                if isinstance(auth, dict) and auth.get("required"):
                    if is_authenticated:
                        authenticated = auth.get("authenticated", {})
                        status = int(authenticated.get("status", 200))
                        payload = self._render_payload(authenticated.get("json", {}))
                        self._send_json(status, payload)
                    else:
                        unauthenticated = auth.get("unauthenticated", {})
                        status = int(unauthenticated.get("status", 401))
                        payload = self._render_payload(
                            unauthenticated.get("json", {"error": "unauthorized"})
                        )
                        self._send_json(status, payload)
                    self._bump_and_maybe_shutdown()
                    return

                response = matched.get("response", {})
                status = int(response.get("status", 200))
                payload = self._render_payload(response.get("json", {}))
                self._send_json(status, payload)
                self._bump_and_maybe_shutdown()
                return

            if path == "/":
                self._send_json(200, {"service": "scythe-fixture", "status": "ok"})
            elif path == "/api/v1/pricing":
                self._send_json(200, {"plan": "free", "currency": "USD"})
            elif path.startswith("/api/v1/public/download/info/"):
                self._send_json(401, {"error": "unauthorized"})
            elif path == "/api/v1/auth/me":
                if is_authenticated:
                    self._send_json(200, {"email": username})
                else:
                    self._send_json(401, {"error": "unauthorized"})
            elif path == "/api/v1/dashboard/user/transfers/history":
                if is_authenticated:
                    self._send_json(200, {"items": []})
                else:
                    self._send_json(401, {"error": "unauthorized"})
            elif path == "/api/v1/dashboard/security/mfa-enforcement":
                if is_authenticated:
                    self._send_json(403, {"error": "mfa_required"})
                else:
                    self._send_json(401, {"error": "unauthorized"})
            elif path == "/api/v1/dashboard/organization/user-org-info":
                if is_authenticated:
                    self._send_json(200, {"org_id": "fixture-org", "role": "member"})
                else:
                    self._send_json(401, {"error": "unauthorized"})
            elif path == "/api/v1/dashboard/organization/users":
                if is_authenticated:
                    self._send_json(403, {"error": "forbidden"})
                else:
                    self._send_json(401, {"error": "unauthorized"})
            else:
                self._send_json(404, {"error": "not_found", "path": path})

            self._bump_and_maybe_shutdown()

        def do_POST(self) -> None:
            path = self.path.split("?", 1)[0]
            payload = self._read_json()

            login_path = str(login_config.get("path", "/api/v1/auth/login-handler"))
            username_field = str(login_config.get("username_field", "email"))
            password_field = str(login_config.get("password_field", "password"))

            matched = self._find_route("POST", path)
            if matched:
                response = matched.get("response", {})
                status = int(response.get("status", 200))
                body = self._render_payload(response.get("json", {}))
                self._send_json(status, body)
                self._bump_and_maybe_shutdown()
                return

            if path == login_path:
                incoming_username = payload.get(username_field) or payload.get(
                    "username"
                )
                incoming_password = payload.get(password_field)
                if incoming_username == username and incoming_password == password:
                    self._send_json(
                        200,
                        {"token": token, "status": "ok"},
                        extra_cookies=[f"stellarbridge={token}; Path=/; HttpOnly"],
                    )
                else:
                    self._send_json(401, {"error": "invalid_credentials"})
            elif path.startswith("/api/v1/bridge/") or path.startswith(
                "/api/v1/request/"
            ):
                self._send_json(401, {"error": "unauthorized"})
            else:
                self._send_json(404, {"error": "not_found", "path": path})

            self._bump_and_maybe_shutdown()

    try:
        server = ThreadingHTTPServer((host, port), FixtureHandler)
    except OSError as exc:
        raise ScytheCLIError(f"Failed to start fixture server on {host}:{port}: {exc}")

    setattr(server, "_scythe_request_count", 0)
    setattr(server, "_scythe_max_requests", max_requests)

    print(f"Fixture server listening at: http://{host}:{port}")
    print(f"Fixture target version: {version}")
    print(f"Fixture profile: {profile}")
    if max_requests is None:
        print("Press Ctrl+C to stop.")
    else:
        print(f"Will stop after {max_requests} request(s).")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scythe", description="Scythe CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize a new .scythe project")
    p_init.add_argument("--path", default=".", help="Target directory (default: .)")

    p_new = sub.add_parser("new", help="Create a new test in scythe_tests")
    p_new.add_argument(
        "name", help="Name of the test (e.g., login_smoke or login_smoke.py)"
    )
    p_new.add_argument(
        "--kind",
        default=DEFAULT_TEST_KIND,
        choices=sorted(TEST_TEMPLATES.keys()),
        help=(
            "Test template kind. "
            f"Available: {', '.join(sorted(TEST_TEMPLATES.keys()))}. "
            f"Default: {DEFAULT_TEST_KIND}."
        ),
    )
    p_new.add_argument(
        "--from-intent",
        default=False,
        action="store_true",
        help="Select template kind with local deterministic intent rules",
    )
    p_new.add_argument(
        "--intent",
        help="Natural language description used by --from-intent",
    )
    p_new.add_argument(
        "--json",
        dest="new_as_json",
        default=False,
        action="store_true",
        help="Emit machine-readable JSON output for template selection",
    )

    p_run = sub.add_parser(
        "run", help="Run a test from scythe_tests and record the run"
    )
    p_run.add_argument(
        "--json",
        dest="run_as_json",
        default=False,
        action="store_true",
        help="Emit machine-readable run diagnostics",
    )
    p_run.add_argument(
        "name", help="Name of the test to run (e.g., login_smoke or login_smoke.py)"
    )
    p_run.add_argument(
        "test_args",
        nargs=argparse.REMAINDER,
        help="Arguments to pass to the test script (use -- to separate)",
    )

    p_check = sub.add_parser(
        "check", help="Validate a test file against Scythe script conventions"
    )
    p_check.add_argument(
        "name",
        help="Test name in scythe_tests (or a path to a .py file)",
    )
    p_check.add_argument(
        "--json",
        dest="as_json",
        default=False,
        action="store_true",
        help="Emit machine-readable JSON diagnostics",
    )
    p_check.add_argument(
        "--strict",
        default=False,
        action="store_true",
        help="Treat warnings as failures",
    )
    p_check.add_argument(
        "--fix",
        default=False,
        action="store_true",
        help="Apply safe automatic fixes before validation",
    )

    p_fixture = sub.add_parser("fixture", help="Local deterministic fixture server")
    sub_fixture = p_fixture.add_subparsers(dest="fixture_cmd", required=True)
    p_fixture_serve = sub_fixture.add_parser(
        "serve", help="Run local HTTP fixture server"
    )
    p_fixture_serve.add_argument("--host", default="127.0.0.1", help="Bind host")
    p_fixture_serve.add_argument("--port", type=int, default=8787, help="Bind port")
    p_fixture_serve.add_argument(
        "--version",
        default="1.2.3",
        help="Value returned in X-SCYTHE-TARGET-VERSION",
    )
    p_fixture_serve.add_argument(
        "--username",
        default="user@example.com",
        help="Fixture login username/email",
    )
    p_fixture_serve.add_argument(
        "--password",
        default="ChangeMe123!",
        help="Fixture login password",
    )
    p_fixture_serve.add_argument(
        "--token",
        default="fixture-token",
        help="Fixture auth cookie token",
    )
    p_fixture_serve.add_argument(
        "--max-requests",
        type=int,
        help="Stop automatically after N requests",
    )
    p_fixture_serve.add_argument(
        "--profile",
        default="minimal",
        help="Built-in fixture profile name",
    )
    p_fixture_serve.add_argument(
        "--profile-file",
        help="Optional custom fixture profile JSON file",
    )
    p_fixture_serve.add_argument(
        "--list-profiles",
        default=False,
        action="store_true",
        help="List built-in fixture profiles and exit",
    )

    p_discover = sub.add_parser("discover", help="Discovery utilities")
    sub_discover = p_discover.add_subparsers(dest="discover_cmd", required=True)
    p_discover_routes = sub_discover.add_parser(
        "routes", help="Discover API routes from OpenAPI"
    )
    p_discover_routes.add_argument(
        "--openapi", required=True, help="OpenAPI file path or URL"
    )
    p_discover_routes.add_argument(
        "--probe-base-url", help="Optional base URL for safe live probing"
    )
    p_discover_routes.add_argument(
        "--timeout", type=int, default=5, help="Probe timeout in seconds"
    )
    p_discover_routes.add_argument(
        "--json",
        dest="discover_as_json",
        default=False,
        action="store_true",
        help="Emit machine-readable route discovery output",
    )

    p_snippet = sub.add_parser("snippet", help="Snippet utilities")
    sub_snippet = p_snippet.add_subparsers(dest="snippet_cmd", required=True)
    p_snippet_lookup = sub_snippet.add_parser(
        "lookup", help="Lookup known-good snippets"
    )
    p_snippet_lookup.add_argument("query", nargs="?", default="", help="Query text")
    p_snippet_lookup.add_argument("--show", help="Show snippet by exact id")
    p_snippet_lookup.add_argument(
        "--json",
        dest="snippet_as_json",
        default=False,
        action="store_true",
        help="Emit machine-readable snippet lookup output",
    )

    p_doctor = sub.add_parser("doctor", help="Environment diagnostics")
    p_doctor.add_argument("target", choices=["ai"], help="Doctor profile target")
    p_doctor.add_argument(
        "--json",
        dest="doctor_as_json",
        default=False,
        action="store_true",
        help="Emit machine-readable doctor output",
    )

    p_db = sub.add_parser("db", help="Database utilities")
    sub_db = p_db.add_subparsers(dest="db_cmd", required=True)
    sub_db.add_parser("dump", help="Dump tests and runs tables as JSON")
    p_sync = sub_db.add_parser(
        "sync-compat", help="Sync COMPATIBLE_VERSIONS from a test file into the DB"
    )
    p_sync.add_argument(
        "name", help="Name of the test (e.g., login_smoke or login_smoke.py)"
    )

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
                raise ScytheCLIError(
                    "Not inside a Scythe project. Run 'scythe init' first."
                )
            selected_kind = args.kind
            selection: Dict[str, Any] = {
                "kind": selected_kind,
                "matched_rule": "explicit",
                "score": 0,
            }
            if args.from_intent:
                selection = classify_intent(args.intent or "", default_kind=args.kind)
                selected_kind = str(selection.get("kind", args.kind))

            path = _create_test(project_root, args.name, selected_kind)
            if args.new_as_json:
                print_json_report(
                    envelope(
                        "new",
                        True,
                        {
                            "name": args.name,
                            "path": path,
                            "kind": selected_kind,
                            "selection": selection,
                        },
                    )
                )
                return 0
            print(f"Created test: {path}")
            return 0

        if args.command == "run":
            project_root = _find_project_root()
            if not project_root:
                raise ScytheCLIError(
                    "Not inside a Scythe project. Run 'scythe init' first."
                )
            extra = getattr(args, "test_args", []) or []
            if extra and len(extra) > 0 and extra[0] == "--":
                extra = extra[1:]
            code, output, version = _run_test(project_root, args.name, extra)
            _record_run(project_root, args.name, code, output, version)
            if args.run_as_json:
                diagnostics: List[Dict[str, Any]] = []
                if code != 0:
                    diagnostics.append(
                        build_error(
                            "SCYTHE-E-RUN-001",
                            "Test execution failed",
                            target=args.name,
                        )
                    )
                print_json_report(
                    envelope(
                        "run",
                        code == 0,
                        {
                            "name": args.name,
                            "exit_code": code,
                            "x_scythe_target_version": version or "",
                            "summary": {
                                "passed": 1 if code == 0 else 0,
                                "failed": 0 if code == 0 else 1,
                                "skipped": 0,
                                "duration_ms": None,
                            },
                            "results": [
                                {
                                    "test_id": args.name
                                    if args.name.endswith(".py")
                                    else f"{args.name}.py",
                                    "status": "pass" if code == 0 else "fail",
                                    "duration_ms": None,
                                    "message": "Execution completed"
                                    if code == 0
                                    else "Execution failed",
                                }
                            ],
                            "raw_output": output,
                        },
                        diagnostics,
                    )
                )
                return code
            print(output)
            return code

        if args.command == "check":
            project_root = _find_project_root()
            test_path = _resolve_test_reference(project_root, args.name)
            applied_fixes: List[str] = []
            if args.fix:
                applied_fixes = _apply_validation_fixes(test_path)
            report = _validate_test_file(test_path)
            report["applied_fixes"] = applied_fixes
            _print_validation_report(report, args.as_json)
            return 0 if _validation_ok(report, args.strict) else 1

        if args.command == "fixture":
            if args.fixture_cmd == "serve":
                if args.list_profiles:
                    for profile_name in list_profiles():
                        print(profile_name)
                    return 0
                try:
                    profile_data = (
                        load_profile_file(args.profile_file)
                        if args.profile_file
                        else load_profile(args.profile)
                    )
                except Exception as exc:
                    raise ScytheCLIError(f"Unable to load fixture profile: {exc}")
                return _serve_fixture(
                    host=args.host,
                    port=args.port,
                    version=args.version,
                    username=args.username,
                    password=args.password,
                    token=args.token,
                    max_requests=args.max_requests,
                    profile=args.profile,
                    profile_data=profile_data,
                )
            raise ScytheCLIError("Unknown fixture command")

        if args.command == "discover":
            if args.discover_cmd == "routes":
                routes = discover_routes(
                    args.openapi, args.probe_base_url, args.timeout
                )
                if args.discover_as_json:
                    print_json_report(
                        envelope(
                            "discover",
                            True,
                            {
                                "source": {
                                    "type": "openapi",
                                    "value": args.openapi,
                                },
                                "probe": {
                                    "enabled": bool(args.probe_base_url),
                                    "base_url": args.probe_base_url or "",
                                    "timeout": args.timeout,
                                },
                                "routes": routes,
                            },
                        )
                    )
                else:
                    print(json.dumps(routes, indent=2))
                return 0
            raise ScytheCLIError("Unknown discover command")

        if args.command == "snippet":
            if args.snippet_cmd == "lookup":
                if args.show:
                    results = [
                        item
                        for item in load_snippets()
                        if str(item.get("id", "")) == args.show
                    ]
                else:
                    results = lookup_snippets(args.query)
                if args.snippet_as_json:
                    print_json_report(
                        envelope(
                            "snippet",
                            True,
                            {
                                "query": args.query,
                                "count": len(results),
                                "results": results,
                            },
                        )
                    )
                else:
                    for item in results:
                        print(f"{item.get('id')}: {item.get('title')}")
                return 0
            raise ScytheCLIError("Unknown snippet command")

        if args.command == "doctor":
            if args.target == "ai":
                project_root = _find_project_root()
                report = run_ai_doctor(project_root or "")
                if args.doctor_as_json:
                    print_json_report(
                        envelope("doctor", report["summary"]["fail"] == 0, report)
                    )
                else:
                    print("AI doctor report")
                    for check in report["checks"]:
                        print(
                            f"- {check['id']}: {check['status']} ({check['observed']})"
                        )
                return 0 if report["summary"]["fail"] == 0 else 1
            raise ScytheCLIError("Unknown doctor target")

        if args.command == "db":
            project_root = _find_project_root()
            if not project_root:
                raise ScytheCLIError(
                    "Not inside a Scythe project. Run 'scythe init' first."
                )
            if args.db_cmd == "dump":
                data = _dump_db(project_root)
                print(json.dumps(data, indent=2))
                return 0
            if args.db_cmd == "sync-compat":
                versions = _sync_compat(project_root, args.name)
                filename = args.name if args.name.endswith(".py") else f"{args.name}.py"
                if versions is None:
                    print(
                        f"No COMPATIBLE_VERSIONS found in {filename}; DB updated with empty value."
                    )
                else:
                    print(
                        f"Updated {filename} compatible_versions to: {json.dumps(versions)}"
                    )
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

    This constructs a Typer app with subcommands equivalent to the previous argparse
    version, then dispatches with argv forwarding for testability and programmatic use.
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
        help="Scythe CLI",
    )

    @app.command()
    def init(
        path: str = typer.Option(
            ".",
            "--path",
            "-p",
            help="Target directory (default: .)",
        ),
    ) -> int:
        """Initialize a new .scythe project"""
        root = _init_project(path)
        print(f"Initialized Scythe project at: {root}")
        return 0

    @app.command()
    def new(
        name: str = typer.Argument(
            ..., help="Name of the test (e.g., login_smoke or login_smoke.py)"
        ),
        kind: str = typer.Option(
            DEFAULT_TEST_KIND,
            "--kind",
            "-k",
            help=(
                "Test template kind. "
                f"Available: {', '.join(sorted(TEST_TEMPLATES.keys()))}. "
                f"Default: {DEFAULT_TEST_KIND}."
            ),
        ),
        from_intent: bool = typer.Option(
            False,
            "--from-intent",
            help="Select template kind with local deterministic intent rules",
        ),
        intent: Optional[str] = typer.Option(
            None,
            "--intent",
            help="Natural language description used by --from-intent",
        ),
        as_json: bool = typer.Option(
            False,
            "--json",
            help="Emit machine-readable JSON output for template selection",
        ),
    ) -> int:
        """Create a new test in scythe_tests"""
        project_root = _find_project_root()
        if not project_root:
            raise ScytheCLIError(
                "Not inside a Scythe project. Run 'scythe init' first."
            )
        selected_kind = kind
        selection: Dict[str, Any] = {
            "kind": kind,
            "matched_rule": "explicit",
            "score": 0,
        }
        if from_intent:
            selection = classify_intent(intent or "", default_kind=kind)
            selected_kind = str(selection.get("kind", kind))

        path = _create_test(project_root, name, selected_kind)
        if as_json:
            print_json_report(
                envelope(
                    "new",
                    True,
                    {
                        "name": name,
                        "path": path,
                        "kind": selected_kind,
                        "selection": selection,
                    },
                )
            )
            return 0
        print(f"Created test: {path}")
        return 0

    @app.command(
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
    )
    def run(
        ctx: typer.Context,
        as_json: bool = typer.Option(
            False,
            "--json",
            help="Emit machine-readable run diagnostics",
        ),
        name: str = typer.Argument(
            ..., help="Name of the test to run (e.g., login_smoke or login_smoke.py)"
        ),
        test_args: List[str] = typer.Argument(
            None,
            help="Arguments to pass to the test script (you can pass options directly or use -- to separate)",
            metavar="[-- ARGS...]",
        ),
    ) -> int:
        """Run a test from scythe_tests and record the run"""
        project_root = _find_project_root()
        if not project_root:
            raise ScytheCLIError(
                "Not inside a Scythe project. Run 'scythe init' first."
            )
        extra: List[str] = []
        if test_args:
            extra.extend(list(test_args))
        if getattr(ctx, "args", None):
            extra.extend(list(ctx.args))
        if extra and len(extra) > 0 and extra[0] == "--":
            extra = extra[1:]
        code, output, version = _run_test(project_root, name, extra)
        _record_run(project_root, name, code, output, version)
        if as_json:
            diagnostics: List[Dict[str, Any]] = []
            if code != 0:
                diagnostics.append(
                    build_error(
                        "SCYTHE-E-RUN-001", "Test execution failed", target=name
                    )
                )
            print_json_report(
                envelope(
                    "run",
                    code == 0,
                    {
                        "name": name,
                        "exit_code": code,
                        "x_scythe_target_version": version or "",
                        "summary": {
                            "passed": 1 if code == 0 else 0,
                            "failed": 0 if code == 0 else 1,
                            "skipped": 0,
                            "duration_ms": None,
                        },
                        "results": [
                            {
                                "test_id": name
                                if name.endswith(".py")
                                else f"{name}.py",
                                "status": "pass" if code == 0 else "fail",
                                "duration_ms": None,
                                "message": "Execution completed"
                                if code == 0
                                else "Execution failed",
                            }
                        ],
                        "raw_output": output,
                    },
                    diagnostics,
                )
            )
            if code != 0:
                raise ExitWithCode(code)
            return 0
        print(output)
        # Raise exception to propagate exit code through Typer
        if code != 0:
            raise ExitWithCode(code)
        return 0

    @app.command("check")
    def check(
        name: str = typer.Argument(
            ..., help="Test name in scythe_tests (or a path to a .py file)"
        ),
        as_json: bool = typer.Option(
            False,
            "--json",
            help="Emit machine-readable JSON diagnostics",
        ),
        strict: bool = typer.Option(
            False,
            "--strict",
            help="Treat warnings as failures",
        ),
        fix: bool = typer.Option(
            False,
            "--fix",
            help="Apply safe automatic fixes before validation",
        ),
    ) -> int:
        """Validate a test file against Scythe script conventions"""
        project_root = _find_project_root()
        test_path = _resolve_test_reference(project_root, name)
        applied_fixes: List[str] = []
        if fix:
            applied_fixes = _apply_validation_fixes(test_path)
        report = _validate_test_file(test_path)
        report["applied_fixes"] = applied_fixes
        _print_validation_report(report, as_json)
        if not _validation_ok(report, strict):
            raise ExitWithCode(1)
        return 0

    fixture_app = typer.Typer(
        no_args_is_help=True, help="Local deterministic fixture server"
    )

    @fixture_app.command("serve")
    def fixture_serve(
        host: str = typer.Option("127.0.0.1", "--host", help="Bind host"),
        port: int = typer.Option(8787, "--port", help="Bind port"),
        version: str = typer.Option(
            "1.2.3",
            "--version",
            help="Value returned in X-SCYTHE-TARGET-VERSION",
        ),
        username: str = typer.Option(
            "user@example.com",
            "--username",
            help="Fixture login username/email",
        ),
        password: str = typer.Option(
            "ChangeMe123!",
            "--password",
            help="Fixture login password",
        ),
        token: str = typer.Option(
            "fixture-token",
            "--token",
            help="Fixture auth cookie token",
        ),
        max_requests: Optional[int] = typer.Option(
            None,
            "--max-requests",
            help="Stop automatically after N requests",
        ),
        profile: str = typer.Option(
            "minimal",
            "--profile",
            help="Built-in fixture profile name",
        ),
        profile_file: Optional[str] = typer.Option(
            None,
            "--profile-file",
            help="Optional custom fixture profile JSON file",
        ),
        list_only: bool = typer.Option(
            False,
            "--list-profiles",
            help="List built-in fixture profiles and exit",
        ),
    ) -> int:
        """Run local HTTP fixture server"""
        if list_only:
            for profile_name in list_profiles():
                print(profile_name)
            return 0
        try:
            profile_data = (
                load_profile_file(profile_file)
                if profile_file
                else load_profile(profile)
            )
        except Exception as exc:
            raise ScytheCLIError(f"Unable to load fixture profile: {exc}")
        return _serve_fixture(
            host=host,
            port=port,
            version=version,
            username=username,
            password=password,
            token=token,
            max_requests=max_requests,
            profile=profile,
            profile_data=profile_data,
        )

    discover_app = typer.Typer(no_args_is_help=True, help="Discovery utilities")

    @discover_app.command("routes")
    def discover_cli_routes(
        openapi: str = typer.Option(..., "--openapi", help="OpenAPI file path or URL"),
        probe_base_url: Optional[str] = typer.Option(
            None,
            "--probe-base-url",
            help="Optional base URL for safe live probing",
        ),
        timeout: int = typer.Option(5, "--timeout", help="Probe timeout in seconds"),
        as_json: bool = typer.Option(
            False,
            "--json",
            help="Emit machine-readable route discovery output",
        ),
    ) -> int:
        routes = discover_routes(openapi, probe_base_url, timeout)
        if as_json:
            print_json_report(
                envelope(
                    "discover",
                    True,
                    {
                        "source": {"type": "openapi", "value": openapi},
                        "probe": {
                            "enabled": bool(probe_base_url),
                            "base_url": probe_base_url or "",
                            "timeout": timeout,
                        },
                        "routes": routes,
                    },
                )
            )
        else:
            print(json.dumps(routes, indent=2))
        return 0

    snippet_app = typer.Typer(no_args_is_help=True, help="Snippet utilities")

    @snippet_app.command("lookup")
    def snippet_lookup(
        query: str = typer.Argument("", help="Query text"),
        show: Optional[str] = typer.Option(
            None, "--show", help="Show snippet by exact id"
        ),
        as_json: bool = typer.Option(
            False,
            "--json",
            help="Emit machine-readable snippet lookup output",
        ),
    ) -> int:
        if show:
            results = [
                item for item in load_snippets() if str(item.get("id", "")) == show
            ]
        else:
            results = lookup_snippets(query)
        if as_json:
            print_json_report(
                envelope(
                    "snippet",
                    True,
                    {"query": query, "count": len(results), "results": results},
                )
            )
        else:
            for item in results:
                print(f"{item.get('id')}: {item.get('title')}")
        return 0

    doctor_app = typer.Typer(no_args_is_help=True, help="Environment diagnostics")

    @doctor_app.command("ai")
    def doctor_ai(
        as_json: bool = typer.Option(
            False,
            "--json",
            help="Emit machine-readable doctor output",
        ),
    ) -> int:
        project_root = _find_project_root()
        report = run_ai_doctor(project_root or "")
        if as_json:
            print_json_report(
                envelope("doctor", report["summary"]["fail"] == 0, report)
            )
        else:
            print("AI doctor report")
            for check in report["checks"]:
                print(f"- {check['id']}: {check['status']} ({check['observed']})")
        if report["summary"]["fail"] > 0:
            raise ExitWithCode(1)
        return 0

    db_app = typer.Typer(no_args_is_help=True, help="Database utilities")

    @db_app.command("dump")
    def dump() -> int:
        """Dump tests and runs tables as JSON"""
        project_root = _find_project_root()
        if not project_root:
            raise ScytheCLIError(
                "Not inside a Scythe project. Run 'scythe init' first."
            )
        data = _dump_db(project_root)
        print(json.dumps(data, indent=2))
        return 0

    @db_app.command("sync-compat")
    def sync_compat(
        name: str = typer.Argument(
            ..., help="Name of the test (e.g., login_smoke or login_smoke.py)"
        ),
    ) -> int:
        """Sync COMPATIBLE_VERSIONS from a test file into the DB"""
        project_root = _find_project_root()
        if not project_root:
            raise ScytheCLIError(
                "Not inside a Scythe project. Run 'scythe init' first."
            )
        versions = _sync_compat(project_root, name)
        filename = name if name.endswith(".py") else f"{name}.py"
        if versions is None:
            print(
                f"No COMPATIBLE_VERSIONS found in {filename}; DB updated with empty value."
            )
        else:
            print(f"Updated {filename} compatible_versions to: {json.dumps(versions)}")
        return 0

    app.add_typer(db_app, name="db")
    app.add_typer(fixture_app, name="fixture")
    app.add_typer(discover_app, name="discover")
    app.add_typer(snippet_app, name="snippet")
    app.add_typer(doctor_app, name="doctor")

    try:
        app(args=argv)
        return 0
    except ExitWithCode as e:
        return e.code
    except ScytheCLIError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except SystemExit as e:
        # Click/Typer may still raise SystemExit for parser/help flows
        return int(getattr(e, "code", 0) or 0)
