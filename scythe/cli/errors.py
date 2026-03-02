from typing import Any, Dict, Optional


ERROR_CATALOG: Dict[str, Dict[str, str]] = {
    "SCYTHE-E-CHECK-001": {
        "category": "validation",
        "severity": "error",
        "hint": "Run `scythe check <name> --fix` or add the missing contract fields manually.",
    },
    "SCYTHE-E-CHECK-002": {
        "category": "validation",
        "severity": "warning",
        "hint": "Update the script to match the canonical test contract.",
    },
    "SCYTHE-E-RUN-001": {
        "category": "runtime",
        "severity": "error",
        "hint": "Inspect `raw_output` and rerun with `scythe run ... --json`.",
    },
    "SCYTHE-E-FIX-001": {
        "category": "io",
        "severity": "error",
        "hint": "Ensure the file is writable and retry `check --fix`.",
    },
    "SCYTHE-E-DISCOVER-001": {
        "category": "config",
        "severity": "error",
        "hint": "Provide a valid OpenAPI file path or URL.",
    },
    "SCYTHE-E-DOCTOR-001": {
        "category": "env",
        "severity": "warning",
        "hint": "Run `scythe init` in your project root.",
    },
    "SCYTHE-E-FIXTURE-001": {
        "category": "config",
        "severity": "error",
        "hint": "Use `scythe fixture serve --list-profiles` to inspect valid profiles.",
    },
}


def build_error(
    code: str, message: str, target: Optional[str] = None
) -> Dict[str, Any]:
    meta = ERROR_CATALOG.get(code, {})
    payload: Dict[str, Any] = {
        "code": code,
        "message": message,
        "category": meta.get("category", "unknown"),
        "severity": meta.get("severity", "error"),
        "hint": meta.get("hint", "No hint available."),
    }
    if target:
        payload["target"] = target
    return payload
