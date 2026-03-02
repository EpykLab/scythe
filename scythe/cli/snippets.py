import json
import os
from typing import Any, Dict, List


def _pack_path() -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "snippets", "pack.json")
    )


def load_snippets() -> List[Dict[str, Any]]:
    with open(_pack_path(), "r", encoding="utf-8") as f:
        payload = json.load(f)
    snippets = payload.get("snippets", [])
    return snippets if isinstance(snippets, list) else []


def lookup_snippets(query: str) -> List[Dict[str, Any]]:
    q = (query or "").lower().strip()
    snippets = load_snippets()

    def score(snippet: Dict[str, Any]) -> int:
        sid = str(snippet.get("id", "")).lower()
        title = str(snippet.get("title", "")).lower()
        tags = [str(t).lower() for t in snippet.get("tags", [])]
        points = 0
        if q and sid == q:
            points += 100
        if q and q in title:
            points += 20
        points += sum(10 for t in tags if q and q in t)
        points += sum(1 for token in q.split() if token and token in title)
        return points

    ranked = sorted(snippets, key=lambda s: (score(s), s.get("id", "")), reverse=True)
    if not q:
        return ranked
    return [snippet for snippet in ranked if score(snippet) > 0]
