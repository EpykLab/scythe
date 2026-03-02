import re
from typing import Dict, List


def apply_safe_fixes(source: str) -> Dict[str, List[str] | str]:
    updated = source
    applied: List[str] = []

    if 'if __name__ == "__main__":' not in updated:
        updated = updated.rstrip() + '\n\nif __name__ == "__main__":\n    main()\n'
        applied.append("add-main-guard")

    if re.search(r"def\s+scythe_test_definition\(args\)\s*:", updated):
        updated = re.sub(
            r"def\s+scythe_test_definition\(args\)\s*:",
            "def scythe_test_definition(args) -> int:",
            updated,
            count=1,
        )
        applied.append("annotate-test-definition-return-int")

    if "COMPATIBLE_VERSIONS" not in updated:
        insertion = 'COMPATIBLE_VERSIONS = ["1.2.3"]\n\n'
        if updated.startswith("#!/usr/bin/env python3\n"):
            updated = updated.replace(
                "#!/usr/bin/env python3\n", "#!/usr/bin/env python3\n\n" + insertion, 1
            )
        else:
            updated = insertion + updated
        applied.append("add-compatible-versions")

    has_url_arg = re.search(r"add_argument\(\s*['\"]--url['\"]", updated) is not None
    if (
        not has_url_arg
        and "argparse.ArgumentParser" in updated
        and "def main" in updated
    ):
        marker = "args = parser.parse_args()"
        if marker in updated:
            updated = updated.replace(
                marker,
                "parser.add_argument('--url', help='Target URL')\n    " + marker,
                1,
            )
            applied.append("add-url-arg")

    return {"source": updated, "applied": applied}
