#!/usr/bin/env python3

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
    """
    Login bruteforce test using API mode.
    This test attempts to bruteforce login credentials via direct API calls.
    """
    from scythe.payloads.generators import FilePayloadGenerator
    from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
    
    # Load passwords from credentials file
    if not args.credentials_file or not os.path.exists(args.credentials_file):
        print(f"Error: Credentials file not found: {args.credentials_file}")
        return False
    
    # Create payload generator from file
    password_gen = FilePayloadGenerator(args.credentials_file)
    
    # Create TTP in API mode
    login_ttp = LoginBruteforceTTP(
        payload_generator=password_gen,
        username='admin',  # Default username to test
        execution_mode='api',  # IMPORTANT: Use API mode instead of Selenium
        api_endpoint='/login',  # Adjust this to match your login endpoint
        username_field='username',  # JSON field name for username in request
        password_field='password',  # JSON field name for password in request
        success_indicators={
            'status_code': 200,  # Successful login returns 200
            'response_not_contains': 'invalid'  # Failed login contains 'invalid'
        },
        expected_result=False  # We expect security controls to prevent bruteforce
    )
    
    # Execute the TTP
    executor = TTPExecutor(ttp=login_ttp, target_url=args.url, headless=True)
    executor.run()
    
    # Return True if test passed (results matched expectations)
    return executor.was_successful()


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
