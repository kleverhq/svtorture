"""Compare the vendored anchor index with an initialized annotated submodule.

The pre-commit hook calls this script to catch drift during requirement authoring.
A normal checkout has no submodule files, in which case the check succeeds silently.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDORED = ROOT / "standards" / "ieee-1800-2023-anchors.json"
ANNOTATED = ROOT / "standards" / "ieee-1800-2023-annotated" / "anchors.json"


def main() -> int:
    if not ANNOTATED.is_file():
        return 0
    if VENDORED.read_bytes() == ANNOTATED.read_bytes():
        return 0
    print(
        f"{VENDORED.relative_to(ROOT)} differs from {ANNOTATED.relative_to(ROOT)}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
