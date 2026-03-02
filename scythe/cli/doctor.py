import os
import sys
from typing import Any, Dict, List


def run_ai_doctor(project_root: str) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    py_ok = sys.version_info >= (3, 10)
    checks.append(
        {
            "id": "python-version",
            "status": "pass" if py_ok else "fail",
            "observed": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "required": ">=3.10",
            "code": "SCYTHE-E-DOCTOR-001" if not py_ok else "",
        }
    )

    project_ok = bool(project_root)
    checks.append(
        {
            "id": "project-root",
            "status": "pass" if project_ok else "warn",
            "observed": project_root or "not found",
            "required": "inside a Scythe project",
            "code": "SCYTHE-E-DOCTOR-001" if not project_ok else "",
        }
    )

    if project_root:
        db_path = os.path.join(project_root, ".scythe", "scythe.db")
        checks.append(
            {
                "id": "db",
                "status": "pass" if os.path.exists(db_path) else "warn",
                "observed": db_path,
                "required": "existing sqlite database",
                "code": "SCYTHE-E-DOCTOR-001" if not os.path.exists(db_path) else "",
            }
        )

    summary = {"pass": 0, "warn": 0, "fail": 0}
    for check in checks:
        summary[check["status"]] += 1

    return {"profile": "ai", "checks": checks, "summary": summary}
