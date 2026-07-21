#!/usr/bin/env python3
"""Annotate an anchored IEEE 1800-2023 text corpus from a local PDF.

Annotation model
----------------
For each configured clause or annex, the annotator asks Poppler's
``pdftohtml -xml -hidden -i`` for positioned text fragments. It verifies page
footers, retains source coordinates and font provenance, removes headers and
footers, repairs overlapping fragments, and classifies headings, prose, lists,
notes, code, grammar, captions, tables, and figure labels. Blocks are rendered
with stable printed-page anchors. Finally, ``data/recipes.json`` restores the
expected anchor skeleton around layouts that cannot be reconstructed safely and
adds explicit visual-review markers instead of embedding replacement text.

The input PDF is selected by ``--pdf`` or, when the option is omitted, by the
``IEEE_1800_2023_PDF`` environment variable. The argument wins when both are
present. Source path and SHA-256 metadata always describe the actual input.
A hash or Poppler-version difference from the development reference emits a
warning but does not stop annotation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

PDF_ENVIRONMENT_VARIABLE = "IEEE_1800_2023_PDF"
REFERENCE_SOURCE_SHA256 = "203fbcccbbae90cef401a3acd31835c8cd1507e8f12b2e069046d4f316e317c9"
REFERENCE_PDFTOHTML_VERSION = "24.02.0"
DATA_DIRECTORY = Path(__file__).with_name("data")


@dataclass
class Fragment:
    pdf_page: int
    source_index: int
    top: int
    left: int
    width: int
    text: str
    source_text: str
    family: str
    size: int

    @property
    def source_id(self) -> tuple[int, int]:
        return self.pdf_page, self.source_index


@dataclass
class Line:
    pdf_page: int
    printed_page: int
    top: int
    left: int
    fragments: list[Fragment]
    text: str
    kind: str = "body"
    object_id: str | None = None

    @property
    def right(self) -> int:
        return max(fragment.left + fragment.width for fragment in self.fragments)

    @property
    def max_size(self) -> int:
        return max(
            (fragment.size for fragment in self.fragments if fragment.text.strip()), default=0
        )

    @property
    def courier_only(self) -> bool:
        meaningful = [fragment for fragment in self.fragments if fragment.text.strip()]
        return bool(meaningful) and all("Courier" in fragment.family for fragment in meaningful)

    @property
    def heading_style(self) -> bool:
        meaningful = [fragment for fragment in self.fragments if fragment.text.strip()]
        return bool(meaningful) and any(
            "Arial" in fragment.family and fragment.size >= 15 for fragment in meaningful
        )

    @property
    def small_text_only(self) -> bool:
        meaningful = [fragment for fragment in self.fragments if fragment.text.strip()]
        return bool(meaningful) and all(fragment.size <= 14 for fragment in meaningful)

    @property
    def footnote_style(self) -> bool:
        meaningful = [fragment for fragment in self.fragments if fragment.text.strip()]
        return bool(meaningful) and all(
            "TimesNewRoman" in fragment.family and fragment.size <= 12 for fragment in meaningful
        )

    @property
    def body_text_line(self) -> bool:
        return self.left <= 145 and any(
            "TimesNewRoman" in fragment.family and fragment.size >= 15
            for fragment in self.fragments
            if fragment.text.strip()
        )

    @property
    def full_body_line(self) -> bool:
        return self.body_text_line and self.right >= 430


@dataclass(frozen=True)
class DocumentPart:
    number: str
    first_pdf_page: int
    last_pdf_page: int
    annex: bool = False
    reviewed_tables: frozenset[str] = frozenset()

    @property
    def filename(self) -> str:
        return f"{int(self.number):02d}.txt" if self.number.isdigit() else f"{self.number}.txt"

    @property
    def first_printed_page(self) -> int:
        return self.first_pdf_page - 1

    @property
    def last_printed_page(self) -> int:
        return self.last_pdf_page - 1


@dataclass
class Block:
    kind: str
    clause: str
    lines: list[Line] = field(default_factory=list)
    object_id: str | None = None

    @property
    def first_page(self) -> int:
        return self.lines[0].printed_page

    @property
    def last_page(self) -> int:
        return self.lines[-1].printed_page


PART_ROWS = [
    ("1", 42, 48),
    ("2", 49, 50),
    ("3", 51, 62),
    ("4", 63, 73),
    ("5", 74, 88),
    ("6", 89, 146),
    ("7", 147, 179),
    ("8", 180, 220),
    ("9", 221, 247),
    ("10", 248, 269),
    ("11", 270, 314),
    ("12", 315, 335),
    ("13", 336, 354),
    ("14", 355, 372),
    ("15", 373, 383),
    ("16", 384, 503),
    ("17", 504, 522),
    ("18", 523, 575),
    ("19", 576, 619),
    ("20", 620, 654),
    ("21", 655, 704),
    ("22", 705, 727),
    ("23", 729, 774),
    ("24", 775, 780),
    ("25", 781, 807),
    ("26", 808, 818),
    ("27", 819, 829),
    ("28", 830, 860),
    ("29", 861, 871),
    ("30", 872, 895),
    ("31", 896, 924),
    ("32", 925, 934),
    ("33", 935, 949),
    ("34", 950, 969),
    ("35", 971, 985),
    ("36", 986, 998),
    ("37", 999, 1088),
    ("38", 1089, 1147),
    ("39", 1148, 1156),
    ("40", 1157, 1170),
    ("41", 1171, 1171),
]

ANNEX_ROWS = [
    ("A", 1173, 1219),
    ("B", 1220, 1221),
    ("C", 1222, 1225),
    ("D", 1226, 1232),
    ("E", 1233, 1234),
    ("F", 1235, 1257),
    ("G", 1258, 1259),
    ("H", 1260, 1292),
    ("I", 1293, 1302),
    ("J", 1303, 1306),
    ("K", 1307, 1323),
    ("L", 1324, 1326),
    ("M", 1327, 1337),
    ("N", 1338, 1345),
    ("O", 1346, 1349),
    ("P", 1350, 1352),
    ("Q", 1353, 1353),
]

PARTS = {
    number: DocumentPart(
        number,
        first,
        last,
        annex=False,
        reviewed_tables=frozenset({"3-1"}) if number == "3" else frozenset(),
    )
    for number, first, last in PART_ROWS
}
PARTS.update(
    {number: DocumentPart(number, first, last, annex=True) for number, first, last in ANNEX_ROWS}
)

# Some front-matter-style footnote references are not exposed as text boxes at
# their reference location. Keep the reviewed association local and explicit.
FOOTNOTE_CLAUSE_OVERRIDES = {
    ("1", "7"): "1.3",
    ("1", "8"): "1.3",
    ("1", "9"): "1.4",
    ("1", "10"): "1.5",
    ("1", "11"): "1.5",
}

# Edition-specific corrections are represented in data/recipes.json as anchor
# structure and review markers without copied source text.
OBJECT_ID_PATTERN = r"(?:\d+-\d+|[A-Q]\.\d+)"
HEADING_RE = re.compile(r"^((?:\d+|[A-Q])(?:\.\d+)*)\.?(?:\s+)(.+)$")
ANNEX_HEADING_RE = re.compile(r"^Annex\s+([A-Q])$")
LIST_RE = re.compile(r"^(—|–|•|[01xz]—|[a-zA-Z]\)|\d+\)|\[[A-Z]?\d+\])\s*(.*)$")
TABLE_CAPTION_RE = re.compile(rf"^Table\s+({OBJECT_ID_PATTERN})—")
SYNTAX_CAPTION_RE = re.compile(r"^Syntax\s+(\d+-\d+)—")
FIGURE_CAPTION_RE = re.compile(rf"^Figure\s+({OBJECT_ID_PATTERN})—")
TERMINAL_RE = re.compile(r"[.!?;:]\s*$")
SUPERSCRIPT_MARKER_RE = re.compile(r"\d+(?:,\s*\d+)*")
ANCHOR_RE = re.compile(
    r"^\[2023:"
    r"(?:\d+(?:\.\d+)*|[A-Q](?:\.\d+)*):"
    r"(?:H|SH\d{3}|FN\d{3}|[PELNCGD]\d{3}|"
    rf"S{OBJECT_ID_PATTERN}|T{OBJECT_ID_PATTERN}(?:\.(?:R\d{{2,}}|C\d{{2,}}))?|"
    rf"F{OBJECT_ID_PATTERN}(?:\.BODY\d{{0,2}})?):"
    r"p\d{3,}(?:-\d{3,})?\]$"
)

REVIEW_MARKER_RE = re.compile(r"\[[A-Z_]+REQUIRES_VISUAL_REVIEW\]")
RECIPE_FIELD_NAMES = {
    "schema_version",
    "review_marker",
    "content_overrides",
    "source",
    "anchors",
    "markers",
    "text_fixup_anchors",
    "existing_suffixes",
    "anchor",
    "regions",
    "start",
    "end",
}


def validate_recipe_payload(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not (
                key in RECIPE_FIELD_NAMES or key in PARTS or ANCHOR_RE.fullmatch(key)
            ):
                raise RuntimeError(f"invalid recipe field: {key!r}")
            validate_recipe_payload(item)
    elif isinstance(value, list):
        for item in value:
            validate_recipe_payload(item)
    elif isinstance(value, str):
        if not ANCHOR_RE.fullmatch(value) and not REVIEW_MARKER_RE.fullmatch(value):
            raise RuntimeError(f"recipe contains non-structural text: {value!r}")
    elif not isinstance(value, int):
        raise RuntimeError(f"invalid recipe value: {value!r}")


RECIPES = json.loads((DATA_DIRECTORY / "recipes.json").read_text())
if RECIPES.get("schema_version") != 1:
    raise RuntimeError("unsupported recipe schema")
validate_recipe_payload(RECIPES)


def add_pdf_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--pdf",
        type=Path,
        help=(f"input PDF path; defaults to the {PDF_ENVIRONMENT_VARIABLE} environment variable"),
    )


def resolve_pdf_path(
    parser: argparse.ArgumentParser,
    argument: Path | None,
) -> Path:
    value = argument or os.environ.get(PDF_ENVIRONMENT_VARIABLE)
    if not value:
        parser.error(f"provide --pdf or set the {PDF_ENVIRONMENT_VARIABLE} environment variable")
    path = Path(value)
    if not path.is_file():
        parser.error(f"PDF file does not exist: {path}")
    return path


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def warn_if_reference_source_differs(
    pdf: Path,
    source_sha256: str,
    *,
    require_follow_up: bool = True,
) -> None:
    if source_sha256 == REFERENCE_SOURCE_SHA256:
        return
    follow_up = (
        "Annotation will continue. Run verify.py on the complete generated corpus."
        if require_follow_up
        else "Verification will continue using this PDF."
    )
    print(
        "WARNING: input PDF SHA-256 differs from the development reference.\n"
        f"  input:     {pdf}\n"
        f"  actual:    {source_sha256}\n"
        f"  reference: {REFERENCE_SOURCE_SHA256}\n"
        f"{follow_up}",
        file=sys.stderr,
    )


@cache
def check_pdftohtml_version() -> None:
    result = subprocess.run(
        ["pdftohtml", "-v"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    match = re.search(r"pdftohtml version (\S+)", result.stdout)
    actual = match.group(1) if match else "unknown"
    if actual != REFERENCE_PDFTOHTML_VERSION:
        print(
            "WARNING: pdftohtml version differs from the development reference; "
            f"actual={actual}, reference={REFERENCE_PDFTOHTML_VERSION}. "
            "Annotation will continue; run verify.py afterwards.",
            file=sys.stderr,
        )


def run_pdftohtml(pdf: Path, first: int, last: int) -> ET.Element:
    check_pdftohtml_version()
    command = [
        "pdftohtml",
        "-f",
        str(first),
        "-l",
        str(last),
        "-xml",
        "-hidden",
        "-i",
        "-stdout",
        str(pdf),
    ]
    result = subprocess.run(command, check=True, capture_output=True)
    root = ET.fromstring(result.stdout)
    actual_pages = [int(page.attrib["number"]) for page in root.findall(".//page")]
    expected_pages = list(range(first, last + 1))
    if actual_pages != expected_pages:
        raise RuntimeError(
            f"pdftohtml returned physical pages {actual_pages}, expected {expected_pages}"
        )
    return root


def join_mixed_line(fragments: list[Fragment]) -> str:
    ordered = sorted(fragments, key=lambda item: item.left)
    consumed: set[int] = set()

    baseline_size = max((fragment.size for fragment in ordered), default=0)
    body_tops = [fragment.top for fragment in ordered if fragment.size == baseline_size]
    if baseline_size >= 13 and body_tops:
        baseline_top = max(body_tops)
        for index, fragment in enumerate(ordered):
            marker = fragment.text.strip()
            if (
                not SUPERSCRIPT_MARKER_RE.fullmatch(marker)
                or fragment.size > baseline_size - 2
                or fragment.top > baseline_top - 3
            ):
                continue
            previous = next(
                (candidate for candidate in reversed(ordered[:index]) if candidate.text.strip()),
                None,
            )
            is_exponent = bool(
                marker.isdigit()
                and previous
                and previous.text.rstrip()[-1:].isdigit()
                and fragment.left - (previous.left + previous.width) <= 3
            )
            fragment.text = ("^" if is_exponent else "[") + marker + ("" if is_exponent else "]")

    # Some symbol glyphs are separate boxes placed over placeholder spaces in a
    # larger text box. Fold those overlays into the placeholder before joining.
    for index, base in enumerate(ordered):
        raw = base.text.replace("\u00a0", " ")
        runs = list(re.finditer(r" {2,}", raw))
        if not runs:
            continue
        overlays = [
            (other_index, other)
            for other_index, other in enumerate(ordered[index + 1 :], start=index + 1)
            if other.left < base.left + base.width and other.text.strip()
        ]
        if not overlays:
            continue
        target = round((overlays[0][1].left - base.left) * len(raw) / max(base.width, 1))
        run = min(runs, key=lambda match: abs((match.start() + match.end()) / 2 - target))
        overlay_text = "".join(other.text.strip() for _, other in overlays)
        following = raw[run.end() :]
        separator = "" if following[:1] in ".,;:!?)]}" else " "
        base.text = raw[: run.start()] + " " + overlay_text + separator + following
        consumed.update(other_index for other_index, _ in overlays)

    output = ""
    previous_right: int | None = None
    for index, fragment in enumerate(ordered):
        if index in consumed:
            continue
        raw = fragment.text.replace("\u00a0", " ")
        if not raw:
            continue
        if output.endswith(("–", "—")):
            raw = raw.lstrip()
        if previous_right is not None:
            gap = fragment.left - previous_right
            if (
                gap > 2
                and output
                and not output[-1].isspace()
                and not raw[0].isspace()
                and raw[0] not in ",.;:!?)]}"
                and output[-1] not in "([{/$`'‘–—"
            ):
                output += " "
        output += raw
        previous_right = fragment.left + fragment.width
    return re.sub(r"[ \t]+", " ", output).strip()


def join_code_line(fragments: list[Fragment], origin: int = 165) -> str:
    meaningful = [fragment for fragment in fragments if fragment.text.strip()]
    if not meaningful:
        return ""

    output = ""
    previous_right: int | None = None
    first_left = min(fragment.left for fragment in meaningful)
    indent = max(0, round((first_left - origin) / 8.1))
    for fragment in sorted(meaningful, key=lambda item: item.left):
        raw = fragment.text.replace("\u00a0", " ")
        text = raw.strip()
        gap = fragment.left - previous_right if previous_right is not None else 0
        if (
            output
            and not output.endswith((" ", "."))
            and (
                raw[0].isspace()
                or gap >= 6
                or (text[0] not in ",.;:!?)]}" and output[-1] not in "([{/$`'‘")
            )
        ):
            output += " "
        output += text
        previous_right = fragment.left + fragment.width
    return " " * indent + output.rstrip()


def parse_lines(root: ET.Element) -> list[Line]:
    fonts: dict[str, tuple[str, int]] = {}
    lines: list[Line] = []
    previous_printed_page: int | None = None

    for page in root.findall(".//page"):
        pdf_page = int(page.attrib["number"])
        for spec in page.findall("fontspec"):
            fonts[spec.attrib["id"]] = (
                spec.attrib.get("family", ""),
                int(spec.attrib.get("size", "0")),
            )

        raw_fragments: list[Fragment] = []
        printed_page_numbers: list[int] = []
        for source_index, text_node in enumerate(page.findall("text")):
            top = int(text_node.attrib["top"])
            left = int(text_node.attrib["left"])
            width = int(text_node.attrib["width"])
            text = "".join(text_node.itertext())
            family, size = fonts[text_node.attrib["font"]]
            if top >= 1120 and text.strip().isdigit():
                printed_page_numbers.append(int(text.strip()))
            if 90 <= top < 1100:
                raw_fragments.append(
                    Fragment(
                        pdf_page,
                        source_index,
                        top,
                        left,
                        width,
                        text,
                        text,
                        family,
                        size,
                    )
                )

        if len(printed_page_numbers) != 1:
            raise RuntimeError(
                f"physical PDF page {pdf_page} has {len(printed_page_numbers)} printed page numbers"
            )
        printed_page = printed_page_numbers[0]
        if previous_printed_page is not None and printed_page != previous_printed_page + 1:
            raise RuntimeError(
                f"printed page sequence jumps from {previous_printed_page} to {printed_page}"
            )
        previous_printed_page = printed_page

        grouped: list[list[Fragment]] = []
        for fragment in sorted(raw_fragments, key=lambda item: (item.top, item.left)):
            if not fragment.text.strip():
                continue
            target = None
            for candidate in reversed(grouped[-4:]):
                if abs(candidate[0].top - fragment.top) <= 6:
                    target = candidate
                    break
            if target is None:
                grouped.append([fragment])
            else:
                target.append(fragment)

        for fragments in grouped:
            meaningful = [fragment for fragment in fragments if fragment.text.strip()]
            if not meaningful:
                continue
            meaningful.sort(key=lambda item: item.left)
            top = min(fragment.top for fragment in meaningful)
            left = min(fragment.left for fragment in meaningful)
            courier_only = all("Courier" in fragment.family for fragment in meaningful)
            text = join_code_line(meaningful) if courier_only else join_mixed_line(meaningful)
            if text:
                lines.append(Line(pdf_page, printed_page, top, left, meaningful, text))

    return lines


def trim_to_part(lines: list[Line], part: DocumentPart) -> list[Line]:
    if part.annex:
        expected = f"Annex {part.number}"
        candidates = [index for index, line in enumerate(lines) if line.text.strip() == expected]
    else:
        candidates = []
        for index, line in enumerate(lines):
            match = HEADING_RE.match(line.text)
            if line.heading_style and match and match.group(1) == part.number:
                candidates.append(index)
    if len(candidates) != 1:
        raise RuntimeError(f"part {part.number} has {len(candidates)} top-level heading candidates")
    start = candidates[0]
    if start and part.number != "1":
        prefix = " | ".join(line.text for line in lines[:start])
        raise RuntimeError(f"unexpected text before part {part.number} heading: {prefix}")
    return lines[start:]


def classify_lines(lines: list[Line], part: DocumentPart) -> None:
    in_note = False
    previous_line: Line | None = None
    for line in lines:
        text = line.text
        heading = HEADING_RE.match(text)
        is_part_heading = bool(
            heading
            and (heading.group(1) == part.number or heading.group(1).startswith(f"{part.number}."))
        )
        if line.heading_style and (is_part_heading or ANNEX_HEADING_RE.match(text)):
            line.kind = "heading"
            in_note = False
        elif TABLE_CAPTION_RE.match(text):
            line.kind = "table_caption"
            in_note = False
        elif SYNTAX_CAPTION_RE.match(text):
            line.kind = "syntax_caption"
            in_note = False
        elif FIGURE_CAPTION_RE.match(text):
            line.kind = "figure_caption"
            in_note = False
        elif text.startswith("NOTE—") or text.startswith("NOTE "):
            line.kind = "note"
            in_note = True
        elif (
            in_note
            and not line.courier_only
            and (
                line.small_text_only
                or (
                    previous_line is not None
                    and previous_line.pdf_page == line.pdf_page
                    and line.top - previous_line.top <= 20
                )
                or (
                    previous_line is not None
                    and previous_line.pdf_page + 1 == line.pdf_page
                    and previous_line.top >= 1000
                    and line.top <= 150
                )
            )
        ):
            line.kind = "note"
        elif line.footnote_style and line.top >= 950:
            line.kind = "footnote"
            in_note = False
        elif line.heading_style:
            line.kind = "subheading"
            in_note = False
        elif (list_match := LIST_RE.match(text)) and (
            list_match.group(1) not in {"—", "–", "•"} or line.left >= 145
        ):
            line.kind = "list"
            in_note = False
        elif line.courier_only:
            line.kind = "code"
            in_note = False
        else:
            line.kind = "body"
            in_note = False
        previous_line = line


def mark_indented_examples(lines: list[Line]) -> None:
    in_example = False
    for index, line in enumerate(lines):
        if index > 0 and lines[index - 1].text.rstrip().lower().endswith("example:"):
            in_example = True
        if not in_example:
            continue
        if line.kind == "body" and line.left >= 165:
            line.kind = "code"
        elif line.kind == "code":
            continue
        else:
            in_example = False


def same_page_close(previous: Line, current: Line, max_gap: int = 23) -> bool:
    return previous.pdf_page == current.pdf_page and current.top - previous.top <= max_gap


def crosses_page_at_margin(previous: Line, current: Line, allow_terminal: bool = False) -> bool:
    if not allow_terminal and TERMINAL_RE.search(previous.text):
        return False
    return current.pdf_page == previous.pdf_page + 1 and previous.top >= 1000 and current.top <= 150


def mark_grammar_regions(lines: list[Line], part: DocumentPart) -> None:
    caption_indexes: list[int] = []
    for index, line in enumerate(lines):
        match = SYNTAX_CAPTION_RE.match(line.text)
        if match:
            line.object_id = match.group(1)
            caption_indexes.append(index)

    for caption_index in caption_indexes:
        syntax_id = lines[caption_index].object_id
        reference_indexes = [
            index
            for index in range(caption_index)
            if f"Syntax {syntax_id}" in lines[index].text and lines[index].kind != "syntax_caption"
        ]
        if reference_indexes:
            search_start = reference_indexes[-1] + 1
        else:
            boundaries = [
                index
                for index in range(caption_index)
                if lines[index].kind in {"heading", "syntax_caption"}
            ]
            search_start = boundaries[-1] + 1 if boundaries else 0
        production_indexes = [
            index for index in range(search_start, caption_index) if "::=" in lines[index].text
        ]
        if not production_indexes:
            continue
        start = production_indexes[0]
        while start > search_start:
            previous = lines[start - 1]
            current = lines[start]
            if previous.kind in {"heading", "subheading", "note", "footnote"}:
                break
            if previous.pdf_page == current.pdf_page and current.top - previous.top > 30:
                break
            if previous.full_body_line and TERMINAL_RE.search(previous.text):
                break
            start -= 1
        for line in lines[start:caption_index]:
            if line.kind not in {"heading", "table_caption", "figure_caption", "syntax_caption"}:
                line.kind = "grammar"

    # Annex A is itself the complete formal grammar. Subclauses A.1 through A.9
    # contain productions; A.10 returns to prose/list clarifications.
    if part.number == "A":
        clause = "A"
        for line in lines:
            if line.kind == "heading":
                match = HEADING_RE.match(line.text)
                if match:
                    clause = match.group(1)
                continue
            if re.match(r"^A\.[1-9](?:\.|$)", clause) and line.kind not in {
                "note",
                "footnote",
                "subheading",
            }:
                line.kind = "grammar"

    # Preserve unnumbered BNF examples as grammar as well.
    for index, line in enumerate(lines):
        if "::=" not in line.text or line.kind == "grammar":
            continue
        line.kind = "grammar"
        cursor = index + 1
        previous = line
        while cursor < len(lines):
            candidate = lines[cursor]
            if candidate.kind in {
                "heading",
                "subheading",
                "note",
                "footnote",
                "table_caption",
                "figure_caption",
                "syntax_caption",
            }:
                break
            if candidate.pdf_page == previous.pdf_page:
                if candidate.top - previous.top > 30:
                    break
            elif not crosses_page_at_margin(previous, candidate, allow_terminal=True):
                break
            if candidate.full_body_line and TERMINAL_RE.search(candidate.text):
                break
            candidate.kind = "grammar"
            previous = candidate
            cursor += 1


def table_ends(previous: Line, current: Line) -> bool:
    if current.kind in {
        "heading",
        "note",
        "footnote",
        "syntax_caption",
        "figure_caption",
        "table_caption",
    }:
        return True
    if current.kind == "subheading" and current.left <= 145:
        return True
    if current.body_text_line:
        if current.pdf_page != previous.pdf_page:
            return True
        if current.top - previous.top > 26:
            return True
    return current.kind == "list" and (
        current.pdf_page != previous.pdf_page or current.top - previous.top > 26
    )


def mark_table_regions(lines: list[Line]) -> None:
    active_table: str | None = None
    seen_tables: set[str] = set()
    previous: Line | None = None

    for line in lines:
        match = TABLE_CAPTION_RE.match(line.text)
        if match:
            table_id = match.group(1)
            line.object_id = table_id
            if table_id in seen_tables:
                line.kind = "table_continuation"
            else:
                line.kind = "table_caption"
                seen_tables.add(table_id)
            active_table = table_id
            previous = line
            continue

        if active_table is not None and previous is not None:
            if table_ends(previous, line):
                active_table = None
            else:
                line.kind = "table_row"
                line.object_id = active_table
        previous = line


def mark_figure_regions(lines: list[Line]) -> None:
    caption_indexes: list[int] = []
    for index, line in enumerate(lines):
        match = FIGURE_CAPTION_RE.match(line.text)
        if not match:
            continue
        line.object_id = match.group(1)
        caption_indexes.append(index)

        cursor = index + 1
        previous = line
        while cursor < len(lines):
            continuation = lines[cursor]
            if (
                continuation.pdf_page == previous.pdf_page
                and continuation.top - previous.top <= 22
                and continuation.heading_style
                and continuation.left >= 150
                and not HEADING_RE.match(continuation.text)
            ):
                continuation.kind = "figure_caption_continuation"
                continuation.object_id = line.object_id
                previous = continuation
                cursor += 1
            else:
                break

    for caption_index in caption_indexes:
        object_id = lines[caption_index].object_id
        cursor = caption_index - 1
        scanned = 0
        while cursor >= 0 and scanned < 100:
            candidate = lines[cursor]
            scanned += 1
            if candidate.pdf_page != lines[caption_index].pdf_page:
                break
            if candidate.kind in {
                "heading",
                "note",
                "footnote",
                "list",
                "grammar",
                "syntax_caption",
                "table_caption",
                "table_continuation",
                "table_row",
                "figure_caption",
            }:
                break
            if candidate.body_text_line and TERMINAL_RE.search(candidate.text):
                break
            if (
                candidate.kind == "body"
                and cursor > 0
                and lines[cursor - 1].kind == "list"
                and candidate.left >= 180
            ):
                break
            if candidate.kind == "code" and (
                candidate.text.rstrip().endswith(";")
                or re.match(
                    r"^(?:end(?:module|sequence|property|class|function|task)|"
                    r"module|sequence|property|class|function|task)\b",
                    candidate.text.strip(),
                )
            ):
                break
            candidate.kind = "figure_body"
            candidate.object_id = object_id
            cursor -= 1


def mark_clause37_diagrams(lines: list[Line]) -> None:
    diagram_only_clauses = {
        "37.7",
        "37.55",
        "37.56",
        "37.62",
        "37.66",
        "37.67",
        "37.69",
        "37.70",
        "37.71",
        "37.73",
        "37.74",
        "37.76",
        "37.77",
        "37.78",
        "37.79",
        "37.83",
    }
    clause = ""
    diagram_start: int | None = None
    in_details = False

    def mark_diagram(start: int, end: int, object_id: str) -> None:
        for diagram_line in lines[start:end]:
            if diagram_line.kind not in {
                "heading",
                "table_caption",
                "figure_caption",
                "syntax_caption",
            }:
                diagram_line.kind = "diagram_body"
                diagram_line.object_id = object_id

    for index, line in enumerate(lines):
        if line.kind == "heading":
            if diagram_start is not None and clause in diagram_only_clauses:
                mark_diagram(diagram_start, index, clause)
            match = HEADING_RE.match(line.text)
            clause = match.group(1) if match else clause
            diagram_start = index + 1 if clause.startswith("37.") else None
            in_details = False
            continue

        if diagram_start is not None and "Details:" in line.text:
            mark_diagram(diagram_start, index, clause)
            line.text = "Details:"
            line.kind = "subheading"
            diagram_start = None
            in_details = True
            continue

        if diagram_start is not None and clause == "37.76" and line.text == "Example:":
            mark_diagram(diagram_start, index, clause)
            diagram_start = None

        if in_details and line.kind == "note" and not line.text.startswith("NOTE"):
            previous = lines[index - 1] if index else None
            if LIST_RE.match(line.text):
                line.kind = "list"
            elif previous is None or previous.kind != "note" or TERMINAL_RE.search(previous.text):
                line.kind = "body"

    if diagram_start is not None and clause in diagram_only_clauses:
        mark_diagram(diagram_start, len(lines), clause)


def annotate_special_regions(lines: list[Line], part: DocumentPart) -> None:
    if part.number == "37":
        mark_clause37_diagrams(lines)
    mark_grammar_regions(lines, part)
    mark_table_regions(lines)
    mark_figure_regions(lines)


def make_blocks(lines: list[Line], part: DocumentPart) -> list[Block]:
    blocks: list[Block] = []
    current: Block | None = None
    clause = ""
    index = 0
    footnote_clauses: dict[str, str] = {}

    def flush() -> None:
        nonlocal current
        if current is not None:
            blocks.append(current)
            current = None

    if part.annex:
        if not lines or lines[0].text.strip() != f"Annex {part.number}":
            raise RuntimeError(f"part {part.number} does not begin with its annex heading")
        heading_lines = [lines[0]]
        index = 1
        while index < len(lines) and len(heading_lines) < 3:
            heading_lines.append(lines[index])
            index += 1
        clause = part.number
        blocks.append(Block("heading", clause, heading_lines))

    while index < len(lines):
        line = lines[index]
        index += 1

        heading = HEADING_RE.match(line.text) if line.kind == "heading" else None
        if heading:
            flush()
            clause = heading.group(1)
            blocks.append(Block("heading", clause, [line]))
            continue

        if not clause:
            raise RuntimeError(f"content before first heading in part {part.number}: {line.text}")

        if line.kind != "footnote":
            for fragment in line.fragments:
                marker = fragment.text.strip().strip("[]")
                if marker.isdigit() and fragment.size <= 12 and line.max_size >= 15:
                    footnote_clauses[marker] = clause

        if line.kind in {
            "table_caption",
            "table_continuation",
            "syntax_caption",
            "figure_caption",
            "table_row",
        }:
            flush()
            blocks.append(Block(line.kind, clause, [line], line.object_id))
            continue

        if line.kind == "figure_caption_continuation":
            if (
                not blocks
                or blocks[-1].kind != "figure_caption"
                or blocks[-1].object_id != line.object_id
            ):
                raise RuntimeError(
                    f"orphan figure caption continuation on PDF page {line.pdf_page}"
                )
            blocks[-1].lines.append(line)
            continue

        if line.kind in {"figure_body", "diagram_body"}:
            if current and current.kind == line.kind and current.object_id == line.object_id:
                current.lines.append(line)
            else:
                flush()
                current = Block(line.kind, clause, [line], line.object_id)
            continue

        if line.kind == "subheading":
            if (
                not current
                and blocks
                and blocks[-1].kind == "heading"
                and same_page_close(blocks[-1].lines[-1], line, 25)
            ):
                blocks[-1].lines.append(line)
            elif (
                current
                and current.kind == "subheading"
                and same_page_close(current.lines[-1], line, 25)
            ):
                current.lines.append(line)
            else:
                flush()
                current = Block("subheading", clause, [line])
            continue

        if line.kind == "list":
            flush()
            current = Block("list", clause, [line])
            continue

        if current and current.kind == "list" and line.kind == "body":
            previous = current.lines[-1]
            if same_page_close(previous, line) or crosses_page_at_margin(previous, line):
                current.lines.append(line)
                continue

        if line.kind in {"code", "grammar"}:
            if current and current.kind == line.kind:
                previous = current.lines[-1]
                max_gap = 100 if line.kind == "grammar" else 45
                if same_page_close(previous, line, max_gap) or crosses_page_at_margin(
                    previous, line, allow_terminal=True
                ):
                    current.lines.append(line)
                    continue
            flush()
            current = Block(line.kind, clause, [line])
            continue

        if line.kind == "note":
            if (
                current
                and current.kind == "note"
                and (
                    same_page_close(current.lines[-1], line)
                    or crosses_page_at_margin(current.lines[-1], line)
                )
            ):
                current.lines.append(line)
            else:
                flush()
                current = Block("note", clause, [line])
            continue

        if line.kind == "footnote":
            marker_match = re.match(r"^(\d+)", line.text)
            starts_footnote = marker_match is not None
            marker = marker_match.group(1) if marker_match else ""
            footnote_clause = FOOTNOTE_CLAUSE_OVERRIDES.get(
                (part.number, marker), footnote_clauses.get(marker, clause)
            )
            if (
                current
                and current.kind == "footnote"
                and not starts_footnote
                and same_page_close(current.lines[-1], line, 18)
            ):
                current.lines.append(line)
            else:
                flush()
                current = Block("footnote", footnote_clause, [line])
            continue

        if line.kind == "body":
            if current and current.kind == "body":
                previous = current.lines[-1]
                if same_page_close(previous, line) or crosses_page_at_margin(previous, line):
                    current.lines.append(line)
                    continue
            flush()
            current = Block("body", clause, [line])
            continue

        raise RuntimeError(f"unhandled line kind {line.kind!r} on PDF page {line.pdf_page}")

    flush()
    return blocks


def prose_text(lines: list[Line], strip_list_marker: bool = False) -> str:
    parts: list[str] = []
    for index, line in enumerate(lines):
        text = line.text
        if index == 0 and strip_list_marker:
            match = LIST_RE.match(text)
            if match:
                text = f"{match.group(1)} {match.group(2)}"
        if index == 0 and lines[0].kind == "footnote":
            text = re.sub(r"^(\d+)(?=[^\d\s])", r"\1 ", text)
        if parts and (
            parts[-1].endswith("-") or (parts[-1].endswith(("–", "—")) and text[:1].isdigit())
        ):
            parts[-1] += text
        else:
            parts.append(text)
    return " ".join(parts)


def page_field(block: Block) -> str:
    if block.first_page == block.last_page:
        return f"p{block.first_page:03d}"
    return f"p{block.first_page:03d}-{block.last_page:03d}"


def validate_blocks(lines: list[Line], blocks: list[Block]) -> None:
    source_ids = [id(line) for line in lines]
    block_ids = [id(line) for block in blocks for line in block.lines]
    if sorted(source_ids) != sorted(block_ids):
        raise RuntimeError("annotated lines were lost or duplicated while making blocks")
    if any(not block.clause for block in blocks):
        raise RuntimeError("a block was emitted before its clause heading")


def validate_output(text: str) -> None:
    anchors = [line for line in text.splitlines() if line.startswith("[2023:")]
    malformed = [anchor for anchor in anchors if not ANCHOR_RE.fullmatch(anchor)]
    if malformed:
        raise RuntimeError(f"malformed anchor: {malformed[0]}")
    if len(anchors) != len(set(anchors)):
        duplicates = sorted({anchor for anchor in anchors if anchors.count(anchor) > 1})
        raise RuntimeError(f"duplicate anchors in generated output: {duplicates[:3]}")


@dataclass
class AnchoredContent:
    anchor: str
    content: str


def parse_rendered_text(text: str) -> tuple[str, list[AnchoredContent]]:
    lines = text.splitlines()
    anchor_indexes = [index for index, line in enumerate(lines) if ANCHOR_RE.fullmatch(line)]
    if not anchor_indexes:
        raise RuntimeError("rendered text contains no anchors")

    preamble = "\n".join(lines[: anchor_indexes[0]]).rstrip()
    records: list[AnchoredContent] = []
    for position, start in enumerate(anchor_indexes):
        end = anchor_indexes[position + 1] if position + 1 < len(anchor_indexes) else len(lines)
        content_lines = lines[start + 1 : end]
        if position + 1 < len(anchor_indexes) and content_lines[-1:] == [""]:
            content_lines.pop()
        records.append(
            AnchoredContent(
                lines[start],
                "\n".join(content_lines),
            )
        )
    return preamble, records


def render_anchored_text(preamble: str, records: list[AnchoredContent]) -> str:
    body = "\n\n".join(f"{record.anchor}\n{record.content}" for record in records)
    return f"{preamble}\n\n{body}\n"


def anchor_part(anchor: str) -> str:
    clause = anchor[1:-1].split(":", 3)[1]
    return clause.split(".", 1)[0]


def append_marker(record: AnchoredContent, marker: str) -> None:
    if marker not in record.content.splitlines():
        record.content = f"{record.content.rstrip()}\n{marker}" if record.content else marker


def apply_recipes(text: str, part: DocumentPart) -> str:
    preamble, records = parse_rendered_text(text)
    review_marker = RECIPES["review_marker"]
    review_targets: set[str] = set()
    preserved_markers: dict[str, list[str]] = defaultdict(list)

    for recipe in RECIPES["content_overrides"]:
        if anchor_part(recipe["source"]) != part.number:
            continue
        indexes = [
            index for index, record in enumerate(records) if record.anchor == recipe["source"]
        ]
        if len(indexes) != 1:
            raise RuntimeError(
                f"content recipe source {recipe['source']} matched {len(indexes)} times"
            )
        index = indexes[0]
        source_content = records[index].content
        replacement = [
            AnchoredContent(anchor, source_content if offset == 0 else "")
            for offset, anchor in enumerate(recipe["anchors"])
        ]
        records[index : index + 1] = replacement
        review_targets.update(recipe["anchors"])
        for anchor, markers in recipe["markers"].items():
            preserved_markers[anchor].extend(markers)

    for recipe in RECIPES["regions"].get(part.number, []):
        positions = {record.anchor: index for index, record in enumerate(records)}
        if recipe["start"] not in positions or recipe["end"] not in positions:
            raise RuntimeError(
                f"region recipe boundaries not found: {recipe['start']}, {recipe['end']}"
            )
        start = positions[recipe["start"]]
        end = positions[recipe["end"]]
        if start >= end:
            raise RuntimeError(f"region recipe is inverted at {recipe['start']}")

        source_records = records[start:end]
        expected = set(recipe["anchors"])
        by_anchor = {record.anchor: record.content for record in source_records}
        unmatched_content = [
            record.content
            for record in source_records
            if record.anchor not in expected and record.content
        ]
        replacement = [
            AnchoredContent(anchor, by_anchor.get(anchor, "")) for anchor in recipe["anchors"]
        ]
        if unmatched_content:
            fallback = "\n\n".join(unmatched_content)
            replacement[0].content = f"{replacement[0].content.rstrip()}\n\n{fallback}".strip()
        records[start:end] = replacement
        review_targets.update(recipe["anchors"])
        for anchor, markers in recipe["markers"].items():
            preserved_markers[anchor].extend(markers)

    review_targets.update(
        anchor for anchor in RECIPES["text_fixup_anchors"] if anchor_part(anchor) == part.number
    )
    for recipe in RECIPES["existing_suffixes"]:
        if anchor_part(recipe["anchor"]) == part.number:
            preserved_markers[recipe["anchor"]].extend(recipe["markers"])

    by_anchor = {record.anchor: record for record in records}
    if len(by_anchor) != len(records):
        raise RuntimeError(f"recipes created duplicate anchors in part {part.number}")
    missing_targets = (review_targets | set(preserved_markers)) - set(by_anchor)
    if missing_targets:
        raise RuntimeError(
            f"recipe anchors missing in part {part.number}: {sorted(missing_targets)}"
        )
    for anchor, markers in preserved_markers.items():
        for marker in markers:
            append_marker(by_anchor[anchor], marker)
    for anchor in review_targets:
        append_marker(by_anchor[anchor], review_marker)

    return render_anchored_text(preamble, records)


def part_title_from_heading(heading: str, part: DocumentPart) -> str:
    lines = [line.strip() for line in heading.splitlines() if line.strip()]
    if part.annex:
        title_lines = [
            line
            for line in lines
            if line != f"Annex {part.number}"
            and not re.fullmatch(r"\((?:normative|informative)\)", line)
        ]
        if not title_lines:
            raise RuntimeError(f"cannot derive title for Annex {part.number}")
        return " ".join(title_lines)

    match = re.fullmatch(rf"{re.escape(part.number)}\.\s+(.+)", " ".join(lines))
    if not match:
        raise RuntimeError(f"cannot derive title for Clause {part.number}: {heading!r}")
    return match.group(1)


def part_title_from_text(text: str, part: DocumentPart) -> str:
    lines = text.splitlines()
    anchor_indexes = [index for index, line in enumerate(lines) if line.startswith("[2023:")]
    if not anchor_indexes:
        raise RuntimeError(f"cannot derive title from part {part.number}: no anchors")
    first = anchor_indexes[0]
    end = anchor_indexes[1] if len(anchor_indexes) > 1 else len(lines)
    return part_title_from_heading("\n".join(lines[first + 1 : end]).strip(), part)


def render_anchors_index(part_texts: dict[str, str], source_sha256: str) -> str:
    missing_parts = set(PARTS) - set(part_texts)
    extra_parts = set(part_texts) - set(PARTS)
    if missing_parts or extra_parts:
        raise RuntimeError(
            "anchor index requires exactly the configured parts; "
            f"missing={sorted(missing_parts)}, extra={sorted(extra_parts)}"
        )

    clauses: list[dict[str, object]] = []
    annexes: list[dict[str, object]] = []
    all_anchors: list[str] = []
    for part_id, part in PARTS.items():
        text = part_texts[part_id]
        validate_output(text)
        anchors = [line for line in text.splitlines() if line.startswith("[2023:")]
        all_anchors.extend(anchors)
        entry = {
            "id": part.number,
            "title": part_title_from_text(text, part),
            "source": f"txt/{part.filename}",
            "anchor_count": len(anchors),
            "anchors": anchors,
        }
        (annexes if part.annex else clauses).append(entry)

    if len(all_anchors) != len(set(all_anchors)):
        raise RuntimeError("anchor index contains globally duplicate anchors")

    index = {
        "schema_version": 1,
        "edition": "2023",
        "source_sha256": source_sha256,
        "anchor_count": len(all_anchors),
        "clauses": clauses,
        "annexes": annexes,
    }
    return json.dumps(index, ensure_ascii=False, indent=2) + "\n"


def read_part_texts(directory: Path) -> dict[str, str]:
    missing = [
        part.filename for part in PARTS.values() if not (directory / part.filename).is_file()
    ]
    if missing:
        raise RuntimeError(f"cannot generate anchor index; missing files: {missing}")
    return {part_id: (directory / part.filename).read_text() for part_id, part in PARTS.items()}


def render_table_row(block: Block) -> str:
    fragments = sorted(block.lines[0].fragments, key=lambda item: item.left)
    columns: list[str] = []
    current = ""
    previous_right: int | None = None
    for fragment in fragments:
        text = fragment.text.strip()
        if not text:
            continue
        gap = fragment.left - previous_right if previous_right is not None else 0
        if current and gap >= 18:
            columns.append(current)
            current = text
        else:
            if current and text[0] not in ",.;:!?)]}^" and current[-1] not in "([{'\".":
                current += " "
            current += text
        previous_right = fragment.left + fragment.width
    if current:
        columns.append(current)
    return " | ".join(columns)


def render(
    blocks: list[Block],
    pdf: Path,
    source_sha256: str,
    part: DocumentPart,
    status: str,
) -> str:
    counters: dict[tuple[str, str], int] = defaultdict(int)
    table_rows: dict[str, int] = defaultdict(int)
    table_continuations: dict[str, int] = defaultdict(int)
    figure_bodies: dict[str, int] = defaultdict(int)
    top_heading = next(
        block for block in blocks if block.kind == "heading" and block.clause == part.number
    )
    title = part_title_from_heading(
        "\n".join(line.text for line in top_heading.lines),
        part,
    )
    output = [
        "IEEE Std 1800-2023 — annotated text corpus",
        f"part={part.number}",
        f"title={title}",
        f"source={pdf.as_posix()}",
        f"source_sha256={source_sha256}",
        f"pdf_pages={part.first_pdf_page}-{part.last_pdf_page}",
        f"printed_pages={part.first_printed_page}-{part.last_printed_page}",
        "anchor_schema=[edition:clause:fragment:printed_page_or_range]",
        f"status={status}",
        "",
    ]

    type_prefix = {
        "body": "P",
        "list": "L",
        "note": "N",
        "code": "C",
        "grammar": "G",
        "subheading": "SH",
        "footnote": "FN",
    }

    for block in blocks:
        if block.kind == "heading":
            fragment_id = "H"
            text = "\n".join(line.text for line in block.lines)
        elif block.kind == "table_caption":
            fragment_id = f"T{block.object_id}"
            text = prose_text(block.lines)
            if block.object_id not in part.reviewed_tables:
                text += "\n[TABLE_REQUIRES_VISUAL_REVIEW]"
        elif block.kind == "table_continuation":
            table_continuations[block.object_id] += 1
            fragment_id = f"T{block.object_id}.C{table_continuations[block.object_id]:02d}"
            text = prose_text(block.lines)
        elif block.kind == "table_row":
            row = table_rows[block.object_id]
            table_rows[block.object_id] += 1
            fragment_id = f"T{block.object_id}.R{row:02d}"
            text = render_table_row(block)
        elif block.kind == "syntax_caption":
            fragment_id = f"S{block.object_id}"
            text = prose_text(block.lines)
        elif block.kind == "figure_body":
            figure_bodies[block.object_id] += 1
            suffix = (
                ""
                if figure_bodies[block.object_id] == 1
                else f"{figure_bodies[block.object_id]:02d}"
            )
            fragment_id = f"F{block.object_id}.BODY{suffix}"
            text = "\n".join(line.text for line in block.lines)
        elif block.kind == "diagram_body":
            key = (block.clause, "D")
            counters[key] += 1
            fragment_id = f"D{counters[key]:03d}"
            text = "\n".join(line.text for line in block.lines)
            text += "\n[DIAGRAM_REQUIRES_VISUAL_REVIEW]"
        elif block.kind == "figure_caption":
            fragment_id = f"F{block.object_id}"
            text = prose_text(block.lines) + "\n[FIGURE_REQUIRES_VISUAL_REVIEW]"
        elif block.kind == "note" and any(
            line.courier_only or "//" in line.text for line in block.lines
        ):
            prefix = type_prefix[block.kind]
            key = (block.clause, prefix)
            counters[key] += 1
            fragment_id = f"{prefix}{counters[key]:03d}"
            text = "\n".join(line.text for line in block.lines)
        else:
            prefix = type_prefix[block.kind]
            key = (block.clause, prefix)
            counters[key] += 1
            fragment_id = f"{prefix}{counters[key]:03d}"
            if block.kind in {"code", "grammar"}:
                minimum_indent = min(
                    len(line.text) - len(line.text.lstrip()) for line in block.lines
                )
                text = "\n".join(line.text[minimum_indent:] for line in block.lines)
            else:
                text = prose_text(block.lines, strip_list_marker=block.kind == "list")

        suffix = None
        if (
            part.number == "38"
            and block.kind == "body"
            and text.strip().startswith("Type Description")
        ):
            suffix = "[TABLE_REQUIRES_VISUAL_REVIEW]"
        if suffix:
            text += f"\n{suffix}"
        output.extend(
            [
                f"[2023:{block.clause}:{fragment_id}:{page_field(block)}]",
                text,
                "",
            ]
        )

    return "\n".join(output).rstrip() + "\n"


def generate_part(pdf: Path, source_sha256: str, part: DocumentPart, status: str) -> str:
    root = run_pdftohtml(pdf, part.first_pdf_page, part.last_pdf_page)
    lines = trim_to_part(parse_lines(root), part)
    classify_lines(lines, part)
    mark_indented_examples(lines)
    annotate_special_regions(lines, part)
    blocks = make_blocks(lines, part)
    validate_blocks(lines, blocks)
    text = render(blocks, pdf, source_sha256, part, status)
    text = apply_recipes(text, part)
    validate_output(text)
    return text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create reviewable IEEE 1800-2023 clause and annex annotations"
    )
    parser.add_argument("part", nargs="?", choices=tuple(PARTS))
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--all", action="store_true", help="generate every configured part")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--anchors-from",
        type=Path,
        metavar="DIRECTORY",
        help="generate only the anchor index from a complete text corpus",
    )
    parser.add_argument(
        "--anchors-output",
        type=Path,
        help="anchor index path (defaults to anchors.json next to the text directory)",
    )
    parser.add_argument(
        "--status",
        default="machine-generated; requires textual and visual review",
        help="metadata status written to generated files",
    )
    add_pdf_argument(parser)
    args = parser.parse_args()

    if args.all:
        if (
            args.part is not None
            or args.output is not None
            or args.output_dir is None
            or args.anchors_from is not None
        ):
            parser.error("--all requires --output-dir and no positional arguments")
    elif args.anchors_from is not None:
        if args.part is not None or args.output is not None or args.output_dir is not None:
            parser.error("--anchors-from does not use positional arguments or --output-dir")
    elif args.part is None or args.output is None or args.output_dir is not None:
        parser.error("single-part mode requires PART OUTPUT and does not use --output-dir")
    elif args.anchors_output is not None:
        parser.error("--anchors-output is only valid with --all or --anchors-from")
    args.pdf = resolve_pdf_path(parser, args.pdf)
    return args


def main() -> None:
    args = parse_args()
    source_sha256 = file_sha256(args.pdf)
    warn_if_reference_source_differs(args.pdf, source_sha256)

    if args.all:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        part_texts: dict[str, str] = {}
        for part in PARTS.values():
            output = args.output_dir / part.filename
            print(f"annotating {part.number} -> {output}", flush=True)
            text = generate_part(args.pdf, source_sha256, part, args.status)
            output.write_text(text)
            part_texts[part.number] = text
        anchors_output = args.anchors_output or args.output_dir.parent / "anchors.json"
        anchors_output.parent.mkdir(parents=True, exist_ok=True)
        print(f"indexing anchors -> {anchors_output}", flush=True)
        anchors_output.write_text(render_anchors_index(part_texts, source_sha256))
    elif args.anchors_from is not None:
        anchors_output = args.anchors_output or args.anchors_from.parent / "anchors.json"
        anchors_output.parent.mkdir(parents=True, exist_ok=True)
        print(f"indexing anchors -> {anchors_output}", flush=True)
        anchors_output.write_text(
            render_anchors_index(read_part_texts(args.anchors_from), source_sha256)
        )
    else:
        part = PARTS[args.part]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(generate_part(args.pdf, source_sha256, part, args.status))


if __name__ == "__main__":
    main()
