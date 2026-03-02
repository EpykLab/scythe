import json
import os
from typing import Any, Dict, List


def _profiles_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "builtin_profiles"))


def list_profiles() -> List[str]:
    out: List[str] = []
    directory = _profiles_dir()
    if not os.path.isdir(directory):
        return out
    for name in sorted(os.listdir(directory)):
        if name.endswith(".json"):
            out.append(name[:-5])
    return out


def load_profile(profile_name: str) -> Dict[str, Any]:
    path = os.path.join(_profiles_dir(), f"{profile_name}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_profile_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
