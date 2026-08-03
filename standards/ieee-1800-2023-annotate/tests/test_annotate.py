from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))

import annotate
from annotate import (
    PDF_ENVIRONMENT_VARIABLE,
    DocumentPart,
    apply_recipes,
    parse_rendered_text,
    render_anchored_text,
    render_anchors_index,
    resolve_pdf_path,
    validate_recipe_payload,
    warn_if_reference_source_differs,
)


MARKER = "[TEXT_ANNOTATION_REQUIRES_VISUAL_REVIEW]"
PREAMBLE = """Synthetic annotation
part=1
title=Authored fixture
"""


def rendered(*blocks: tuple[str, str]) -> str:
    body = "\n\n".join(f"{anchor}\n{content}" for anchor, content in blocks)
    return f"{PREAMBLE}\n{body}\n"


class RecipeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_recipes = annotate.RECIPES
        self.part = DocumentPart("1", 1, 1)

    def tearDown(self) -> None:
        annotate.RECIPES = self.original_recipes

    def test_parse_and_render_preserve_significant_layout(self) -> None:
        text = rendered(
            ("[2023:1:H:p001]", "1. Authored fixture"),
            ("[2023:1:C001:p001]", "   indented line\n\nnext line"),
        )

        preamble, records = parse_rendered_text(text)

        self.assertEqual(render_anchored_text(preamble, records), text)

    def test_recipe_payload_rejects_expected_source_text(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "non-structural text"):
            validate_recipe_payload(
                {
                    "schema_version": 1,
                    "review_marker": MARKER,
                    "content_overrides": ["copied fixture prose"],
                }
            )

    def test_content_recipe_preserves_source_and_adds_anchor_skeleton(self) -> None:
        source = "[2023:1:P001:p001]"
        added = "[2023:1:P901:p001]"
        annotate.RECIPES = {
            "review_marker": MARKER,
            "content_overrides": [{"source": source, "anchors": [source, added], "markers": {}}],
            "text_fixup_anchors": [],
            "existing_suffixes": [],
            "regions": {},
        }
        text = rendered(
            ("[2023:1:H:p001]", "1. Authored fixture"),
            (source, "Source-owned fixture content."),
        )

        output = apply_recipes(text, self.part)
        _, records = parse_rendered_text(output)

        self.assertEqual([record.anchor for record in records], ["[2023:1:H:p001]", source, added])
        self.assertIn("Source-owned fixture content.", records[1].content)
        self.assertTrue(records[1].content.endswith(MARKER))
        self.assertEqual(records[2].content, MARKER)

    def test_anchor_index_includes_ordered_multiline_heading_titles(self) -> None:
        parts = {
            "1": DocumentPart("1", 1, 1),
            "A": DocumentPart("A", 2, 2, annex=True),
        }
        part_texts = {
            "1": rendered(
                ("[2023:1:H:p001]", "1. Authored fixture"),
                (
                    "[2023:1.1:H:p001]",
                    f"1.1 First multiline\nheading\n{MARKER}",
                ),
                ("[2023:1.1:P001:p001]", "Fixture content."),
            ),
            "A": rendered(
                ("[2023:A:H:p002]", "Annex A\n(normative)\nFixture annex"),
                ("[2023:A.1:H:p002]", "A.1 Annex scope"),
            ),
        }

        with patch.object(annotate, "PARTS", parts):
            index = json.loads(render_anchors_index(part_texts, "0" * 64))

        self.assertEqual(index["schema_version"], 2)
        self.assertEqual(
            index["sections"],
            [
                {"clause": "1", "title": "Authored fixture"},
                {"clause": "1.1", "title": "First multiline heading"},
                {"clause": "A", "title": "Fixture annex"},
                {"clause": "A.1", "title": "Annex scope"},
            ],
        )

    def test_anchor_index_rejects_duplicate_heading_locations(self) -> None:
        parts = {"1": DocumentPart("1", 1, 1)}
        part_texts = {
            "1": rendered(
                ("[2023:1:H:p001]", "1. Authored fixture"),
                ("[2023:1:H:p002]", "1. Duplicate heading"),
            )
        }

        with (
            patch.object(annotate, "PARTS", parts),
            self.assertRaisesRegex(RuntimeError, "duplicate heading locations"),
        ):
            render_anchors_index(part_texts, "0" * 64)

    def test_region_recipe_preserves_unmatched_source_under_marked_anchor(self) -> None:
        start = "[2023:1:P001:p001]"
        removed = "[2023:1:P002:p001]"
        added = "[2023:1:P901:p001]"
        end = "[2023:1:P003:p001]"
        annotate.RECIPES = {
            "review_marker": MARKER,
            "content_overrides": [],
            "text_fixup_anchors": [],
            "existing_suffixes": [],
            "regions": {
                "1": [
                    {
                        "start": start,
                        "end": end,
                        "anchors": [start, added],
                        "markers": {},
                    }
                ]
            },
        }
        text = rendered(
            ("[2023:1:H:p001]", "1. Authored fixture"),
            (start, "First source fragment."),
            (removed, "Second source fragment."),
            (end, "Following exact block."),
        )

        output = apply_recipes(text, self.part)
        _, records = parse_rendered_text(output)

        self.assertEqual(
            [record.anchor for record in records],
            ["[2023:1:H:p001]", start, added, end],
        )
        self.assertIn("First source fragment.", records[1].content)
        self.assertIn("Second source fragment.", records[1].content)
        self.assertEqual(records[2].content, MARKER)
        self.assertEqual(records[3].content, "Following exact block.")


class PdfResolutionTests(unittest.TestCase):
    def test_argument_takes_precedence_over_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            argument = root / "argument.pdf"
            environment = root / "environment.pdf"
            argument.touch()
            environment.touch()
            parser = argparse.ArgumentParser()
            with patch.dict(os.environ, {PDF_ENVIRONMENT_VARIABLE: str(environment)}):
                self.assertEqual(resolve_pdf_path(parser, argument), argument)

    def test_environment_is_used_when_argument_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / "environment.pdf"
            pdf.touch()
            parser = argparse.ArgumentParser()
            with patch.dict(os.environ, {PDF_ENVIRONMENT_VARIABLE: str(pdf)}):
                self.assertEqual(resolve_pdf_path(parser, None), pdf)

    def test_missing_argument_and_environment_is_an_error(self) -> None:
        parser = argparse.ArgumentParser()
        stderr = StringIO()
        with (
            patch.dict(os.environ, {}, clear=True),
            redirect_stderr(stderr),
            self.assertRaises(SystemExit),
        ):
            resolve_pdf_path(parser, None)
        self.assertIn(PDF_ENVIRONMENT_VARIABLE, stderr.getvalue())

    def test_reference_hash_difference_warns_without_raising(self) -> None:
        stderr = StringIO()
        with redirect_stderr(stderr):
            warn_if_reference_source_differs(Path("fixture.pdf"), "0" * 64)
        self.assertIn("Annotation will continue", stderr.getvalue())
        self.assertIn("verify.py", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
