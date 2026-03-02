import json
from datetime import datetime
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "1.0"


def envelope(
    command: str,
    ok: bool,
    data: Dict[str, Any],
    diagnostics: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "ok": ok,
        "data": data,
        "diagnostics": diagnostics or [],
    }


def print_json_report(report: Dict[str, Any]) -> None:
    print(json.dumps(report, indent=2))
