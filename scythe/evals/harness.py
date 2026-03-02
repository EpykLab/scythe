import argparse
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from scythe.cli.main import main as scythe_main


def _load_scenarios(path: str) -> List[Dict[str, Any]]:
    scenarios: List[Dict[str, Any]] = []
    if not os.path.isdir(path):
        return scenarios
    for name in sorted(os.listdir(path)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(path, name), "r", encoding="utf-8") as f:
            scenarios.append(json.load(f))
    return scenarios


def run_eval(scenarios_dir: str, output_path: str) -> int:
    scenarios = _load_scenarios(scenarios_dir)
    results: List[Dict[str, Any]] = []
    passed = 0

    for scenario in scenarios:
        test_name = scenario.get("test_name", "eval_test")
        intent = scenario.get("intent", "api journey")
        create_code = scythe_main(
            ["new", test_name, "--from-intent", "--intent", intent]
        )
        check_code = scythe_main(["check", test_name, "--json"])
        ok = create_code == 0 and check_code == 0
        if ok:
            passed += 1
        results.append(
            {
                "id": scenario.get("id", test_name),
                "intent": intent,
                "create_exit_code": create_code,
                "check_exit_code": check_code,
                "ok": ok,
            }
        )

    payload = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "total": len(results),
        "passed": passed,
        "pass_rate": (passed / len(results)) if results else 0.0,
        "results": results,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(json.dumps(payload, indent=2))
    return 0 if passed == len(results) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Scythe AI eval harness")
    parser.add_argument(
        "--scenarios-dir",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "scenarios")),
        help="Directory containing eval scenario JSON files",
    )
    parser.add_argument(
        "--output",
        default="artifacts/evals/latest.json",
        help="Output report path",
    )
    args = parser.parse_args()
    return run_eval(args.scenarios_dir, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
