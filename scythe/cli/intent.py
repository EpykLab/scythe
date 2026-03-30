from typing import Dict, List, Tuple


INTENT_RULES: List[Tuple[str, List[str]]] = [
    ("sb-mfa-gate", ["mfa", "non-compliance", "forbidden", "403"]),
    ("sb-org-rbac", ["rbac", "organization", "org", "role", "permission"]),
    ("sb-route-matrix", ["public", "private", "route", "matrix", "access"]),
    ("playwright-run", ["playwright", "browser test", "playwright test"]),
    ("playwright-wrap", ["playwright wrap", "playwright page", "playwright inline"]),
    ("api-auth-journey", ["authenticated", "login", "cookie", "jwt"]),
    ("ttp-api", ["bruteforce", "ttp", "payload", "api endpoint"]),
    ("api-journey", ["journey", "api", "step"]),
]


def classify_intent(
    intent: str, default_kind: str = "api-journey"
) -> Dict[str, object]:
    text = (intent or "").lower().strip()
    if not text:
        return {"kind": default_kind, "matched_rule": "default", "score": 0}

    best_kind = default_kind
    best_score = 0
    matched_rule = "default"
    for kind, keywords in INTENT_RULES:
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_kind = kind
            matched_rule = ", ".join([kw for kw in keywords if kw in text]) or "rule"

    return {"kind": best_kind, "matched_rule": matched_rule, "score": best_score}
