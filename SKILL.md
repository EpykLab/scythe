---
name: scythe-ai-test-authoring
description: Use when an agent needs to create, validate, and run Scythe tests with the current AI authoring workflow (intent-based templates, check --fix, run --json, route discovery, snippets, doctor, fixture profiles, and eval harness).
---

# Scythe AI Test Authoring Skill

This skill teaches an agent how to reliably author and iterate on Scythe tests.

## When To Use

Use this skill when the user asks to:

- create a new Scythe test,
- generate tests from intent,
- validate or auto-fix test scripts,
- discover routes from OpenAPI,
- debug why a generated test fails,
- run prompt-to-pass evaluations.

## Core Workflow

Follow this loop unless the user asks for a different flow:

1. Initialize project context (if needed):
   - `scythe init`
2. Generate a starter script:
   - Deterministic template: `scythe new <name> --kind <kind>`
   - Intent-based: `scythe new <name> --from-intent --intent "<goal>" --json`
3. Edit generated script for real routes, statuses, and expectations.
4. Validate structure and contract:
   - `scythe check <name> --json`
5. Auto-fix safe issues where possible:
   - `scythe check <name> --json --fix`
6. Enforce strictness when requested:
   - `scythe check <name> --json --strict`
7. Execute test with diagnostics:
   - `scythe run <name> --json -- --url <target-url>`
8. Iterate on expectations based on observed API behavior.

## Playwright Integration

Scythe supports two Playwright primitives (requires `pip install 'scythe-ttp[playwright]'` + `playwright install`):

- **`plw.Run(test_file)`**: Execute an existing pytest-playwright test file and assert on results.
  ```python
  from scythe.playwright import Run
  Run("tests/test_login.py").expect(passed=True)
  Run("tests/test_login.py", browser="firefox").expect(passed=False)
  ```

- **`plw.Wrap()`**: Use Playwright's sync Page API directly with scythe lifecycle hooks.
  ```python
  from scythe.playwright import Wrap
  with Wrap(headless=True) as pw:
      pw.page.goto("https://target.com/login")
      pw.page.fill("#username", "admin")
      pw.page.click("button[type=submit]")
      pw.expect_url_contains("/dashboard")
  ```

- Both are also available as Journey Actions: `PlaywrightRunAction`, `PlaywrightWrapAction`.
- Snippet lookup: `scythe snippet lookup "playwright" --json`

## Authoring Aids

- Route discovery:
  - `scythe discover routes --openapi <file-or-url> --json`
  - optional live probe: `--probe-base-url <url>`
- Snippet lookup:
  - `scythe snippet lookup "<query>" --json`
  - `scythe snippet lookup --show <id> --json`
- Environment checks:
  - `scythe doctor ai --json`
- Deterministic local target:
  - `scythe fixture serve --profile minimal`
  - inspect profiles: `scythe fixture serve --list-profiles`

## Template Selection Guidance

Use these built-ins:

- `api-journey` (default): unauthenticated/public route checks.
- `api-auth-journey`: auth + CSRF workflows.
- `ttp-api`: API-mode TTP testing.
- `playwright-run`: run existing pytest-playwright test files with assertions.
- `playwright-wrap`: use Playwright's sync API directly in a scythe test.
- `sb-route-matrix`: Stellarbridge route policy matrix.
- `sb-mfa-gate`: MFA enforcement checks.
- `sb-org-rbac`: organization RBAC checks.

If intent is ambiguous, choose `api-journey` first and refine.
When the user mentions Playwright or browser testing with Playwright, choose `playwright-run` or `playwright-wrap`.

## Contract Requirements For Test Scripts

A valid AI-authored Scythe script should include:

- `COMPATIBLE_VERSIONS` list near top of file.
- `check_url_available(url)`.
- `check_version_in_response_header(args)` when version gating is used.
- `scythe_test_definition(args) -> int` returning an int exit code.
- `main()` parsing args and exiting with that return code.
- `if __name__ == "__main__": main()` guard.

Use `scythe check --json` as the source of truth.

## Troubleshooting Rules

When run output disagrees with expectations:

1. Trust observed status codes from `scythe run --json` diagnostics.
2. Update `expected_status` per route policy (public vs authz-required vs private).
3. Avoid assuming all protected routes return `401`; many return `403` or `404` intentionally.
4. Treat CSRF failures separately from auth failures for unsafe methods.
5. Re-run after each focused change.

### Known behavior notes

- Some apps do not support `HEAD` on root or probe endpoints; use GET-compatible checks.
- CSRF-protected unsafe requests may require both token header and same-origin `Referer`.

## Eval Harness

For nightly or batch prompt-to-pass checks:

- `python -m scythe.evals.harness --output artifacts/evals/nightly.json`
- scenario files live under `scythe/evals/scenarios/`

## Quality Bar

Before declaring done:

- `scythe check <name> --json` reports `"ok": true`.
- `scythe run <name> --json -- --url <target>` behavior matches route expectations.
- diagnostics are actionable and stable across reruns.

## Canonical Reference

- `docs/AI_TEST_AUTHORING.md`
