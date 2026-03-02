import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from urllib.request import urlopen


def _load_openapi_source(source: str) -> Dict[str, Any]:
    parsed = urlparse(source)
    if parsed.scheme in ("http", "https"):
        with urlopen(source) as response:  # nosec B310 - user-requested endpoint
            return json.loads(response.read().decode("utf-8"))
    with open(source, "r", encoding="utf-8") as f:
        return json.load(f)


def discover_routes(
    source: str, probe_base_url: Optional[str] = None, timeout: int = 5
) -> List[Dict[str, Any]]:
    document = _load_openapi_source(source)
    paths = document.get("paths", {})
    routes: List[Dict[str, Any]] = []

    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, spec in methods.items():
            method_upper = str(method).upper()
            if method_upper not in {
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
                "HEAD",
                "OPTIONS",
            }:
                continue
            route: Dict[str, Any] = {
                "method": method_upper,
                "path": path,
                "operation_id": spec.get("operationId")
                if isinstance(spec, dict)
                else None,
                "tags": spec.get("tags", []) if isinstance(spec, dict) else [],
                "confidence": "openapi",
            }
            routes.append(route)

    if probe_base_url:
        try:
            import requests

            for route in routes:
                if route["method"] not in {"GET", "HEAD"}:
                    continue
                url = probe_base_url.rstrip("/") + route["path"]
                try:
                    response = requests.request(route["method"], url, timeout=timeout)
                    route["probe_result"] = {
                        "reachable": True,
                        "status_code": response.status_code,
                    }
                    route["confidence"] = "openapi+probed"
                except requests.RequestException:
                    route["probe_result"] = {"reachable": False}
        except Exception:
            pass

    return routes
