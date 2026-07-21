from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scan_copied_text import copied_ngrams


class CopiedTextScanTests(unittest.TestCase):
    def test_detects_long_sequence_but_ignores_short_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline"
            (baseline / "txt").mkdir(parents=True)
            (baseline / "txt" / "01.txt").write_text(
                "metadata=value\n\n"
                "[2023:1:P001:p001]\n"
                "alpha beta gamma delta epsilon zeta eta theta iota kappa\n"
            )
            copied = root / "copied.py"
            copied.write_text('value = "alpha beta gamma delta epsilon zeta eta theta"\n')
            short = root / "short.py"
            short.write_text('value = "alpha beta gamma delta"\n')

            matches = copied_ngrams(baseline, [copied, short], 8)

            self.assertIn(copied, matches)
            self.assertNotIn(short, matches)


if __name__ == "__main__":
    unittest.main()
