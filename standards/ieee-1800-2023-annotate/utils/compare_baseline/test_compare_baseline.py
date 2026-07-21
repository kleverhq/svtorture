from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from compare_baseline import compare_corpora


PREAMBLE = """Synthetic annotation
part=1
title=Authored fixture

"""
ANCHOR_ONE = "[2023:1:H:p001]"
ANCHOR_TWO = "[2023:1.1:P001:p001]"


def corpus_text(second_content: str, anchors: tuple[str, ...] = (ANCHOR_ONE, ANCHOR_TWO)) -> str:
    contents = ["1. Authored fixture", second_content]
    return PREAMBLE + "".join(
        f"{anchor}\n{content}\n\n" for anchor, content in zip(anchors, contents, strict=True)
    )


def write_corpus(root: Path, text: str, index: dict[str, object] | None = None) -> None:
    (root / "txt").mkdir(parents=True)
    (root / "txt" / "01.txt").write_text(text)
    (root / "anchors.json").write_text(json.dumps(index or {"fixture": True}) + "\n")


class CompareBaselineTests(unittest.TestCase):
    def test_identical_corpora_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline"
            candidate = root / "candidate"
            text = corpus_text("Original fixture sentence.")
            write_corpus(baseline, text)
            write_corpus(candidate, text)

            result = compare_corpora(baseline, candidate)

            self.assertTrue(result.compatible)
            self.assertEqual(result.exact_blocks, 2)
            self.assertEqual(result.marked_differing_blocks, 0)

    def test_marked_content_difference_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline"
            candidate = root / "candidate"
            write_corpus(baseline, corpus_text("Original fixture sentence."))
            write_corpus(
                candidate,
                corpus_text(
                    "Best-effort fixture sentence.\n[TEXT_ANNOTATION_REQUIRES_VISUAL_REVIEW]"
                ),
            )

            result = compare_corpora(baseline, candidate)

            self.assertTrue(result.compatible)
            self.assertEqual(result.exact_blocks, 1)
            self.assertEqual(result.marked_differing_blocks, 1)

    def test_unmarked_content_difference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline"
            candidate = root / "candidate"
            write_corpus(baseline, corpus_text("Original fixture sentence."))
            write_corpus(candidate, corpus_text("Changed fixture sentence."))

            result = compare_corpora(baseline, candidate)

            self.assertFalse(result.compatible)
            self.assertEqual(result.unmarked_differences, [f"01.txt: {ANCHOR_TWO}"])

    def test_anchor_difference_fails_even_when_content_is_marked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline"
            candidate = root / "candidate"
            write_corpus(baseline, corpus_text("Original fixture sentence."))
            write_corpus(
                candidate,
                corpus_text(
                    "Changed fixture sentence.\n[TEXT_ANNOTATION_REQUIRES_VISUAL_REVIEW]",
                    anchors=(ANCHOR_ONE, "[2023:1.1:P002:p001]"),
                ),
            )

            result = compare_corpora(baseline, candidate)

            self.assertFalse(result.compatible)
            self.assertTrue(any("anchor sequence differs" in error for error in result.errors))

    def test_input_path_and_hash_differences_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline"
            candidate = root / "candidate"
            baseline_text = corpus_text("Original fixture sentence.").replace(
                "\n\n",
                "\nsource=baseline.pdf\nsource_sha256=aaaa\n\n",
                1,
            )
            candidate_text = corpus_text("Original fixture sentence.").replace(
                "\n\n",
                "\nsource=candidate.pdf\nsource_sha256=bbbb\n\n",
                1,
            )
            write_corpus(baseline, baseline_text, {"fixture": 1, "source_sha256": "aaaa"})
            write_corpus(candidate, candidate_text, {"fixture": 1, "source_sha256": "bbbb"})

            result = compare_corpora(baseline, candidate)

            self.assertTrue(result.compatible)

    def test_anchor_index_difference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline"
            candidate = root / "candidate"
            text = corpus_text("Original fixture sentence.")
            write_corpus(baseline, text, {"fixture": 1})
            write_corpus(candidate, text, {"fixture": 2})

            result = compare_corpora(baseline, candidate)

            self.assertFalse(result.compatible)
            self.assertTrue(
                any(error.startswith("anchors.json differs") for error in result.errors)
            )


if __name__ == "__main__":
    unittest.main()
