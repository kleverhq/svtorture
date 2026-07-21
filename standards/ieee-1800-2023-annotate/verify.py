#!/usr/bin/env python3
"""Verify the structure and deterministic regeneration of an annotated corpus.

The verifier checks the input PDF metadata, the exact 58-file inventory,
anchor grammar and uniqueness, printed-page coverage, deterministic
``anchors.json`` contents, visual-review marker counts, numbered table/figure/
Syntax inventories, grammar adjacency, and object page coverage. With
``--check-generated`` it regenerates every part and requires byte-for-byte
identity. It validates structural integrity and reproducibility; it does not
prove semantic fidelity for layouts explicitly marked for visual review.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from annotate import (
    ANCHOR_RE,
    DATA_DIRECTORY,
    OBJECT_ID_PATTERN,
    PARTS,
    add_pdf_argument,
    file_sha256,
    generate_part,
    part_title_from_heading,
    render_anchors_index,
    resolve_pdf_path,
    warn_if_reference_source_differs,
)

TABLE_FRAGMENT_RE = re.compile(rf"^T({OBJECT_ID_PATTERN})$")
TABLE_ROW_RE = re.compile(rf"^T({OBJECT_ID_PATTERN})\.R\d{{2,}}$")
FIGURE_FRAGMENT_RE = re.compile(rf"^F({OBJECT_ID_PATTERN})$")
SYNTAX_FRAGMENT_RE = re.compile(r"^S(\d+-\d+)$")
GRAMMAR_FRAGMENT_RE = re.compile(r"^G\d{3}$")
PAGE_RE = re.compile(r"^p(\d+)(?:-(\d+))?$")
EXPECTED_VISUAL_REVIEW_MARKERS = {
    "[TABLE_REQUIRES_VISUAL_REVIEW]": 201,
    "[FIGURE_REQUIRES_VISUAL_REVIEW]": 104,
    "[DIAGRAM_REQUIRES_VISUAL_REVIEW]": 84,
    "[WAVEFORM_REQUIRES_VISUAL_REVIEW]": 2,
    "[FORMALISM_REQUIRES_VISUAL_REVIEW]": 6,
    "[LAYOUT_REQUIRES_VISUAL_REVIEW]": 6,
    "[CODE_LAYOUT_REQUIRES_VISUAL_REVIEW]": 1,
    "[TEXT_ANNOTATION_REQUIRES_VISUAL_REVIEW]": 282,
}


@dataclass(frozen=True)
class Anchor:
    raw: str
    edition: str
    clause: str
    fragment: str
    first_page: int
    last_page: int
    content: str


@dataclass(frozen=True)
class ExpectedObject:
    kind: str
    object_id: str
    part: str
    printed_pages: tuple[int, ...]


def parse_metadata_and_anchors(path: Path) -> tuple[dict[str, str], list[Anchor]]:
    lines = path.read_text().splitlines()
    metadata: dict[str, str] = {}
    anchor_indexes: list[int] = []
    for index, line in enumerate(lines):
        if line.startswith("[2023:"):
            anchor_indexes.append(index)
        elif not anchor_indexes and "=" in line:
            key, value = line.split("=", 1)
            metadata[key] = value

    anchors: list[Anchor] = []
    for position, index in enumerate(anchor_indexes):
        raw = lines[index]
        if not ANCHOR_RE.fullmatch(raw):
            raise ValueError(f"{path}: malformed anchor {raw}")
        edition, clause, fragment, page_field = raw[1:-1].split(":")
        page_match = PAGE_RE.fullmatch(page_field)
        if not page_match:
            raise ValueError(f"{path}: malformed page field in {raw}")
        first_page = int(page_match.group(1))
        last_page = int(page_match.group(2) or page_match.group(1))
        next_index = (
            anchor_indexes[position + 1] if position + 1 < len(anchor_indexes) else len(lines)
        )
        content = "\n".join(lines[index + 1 : next_index]).strip()
        if not content:
            raise ValueError(f"{path}: anchor has no content: {raw}")
        anchors.append(Anchor(raw, edition, clause, fragment, first_page, last_page, content))
    return metadata, anchors


def load_expected_objects(path: Path) -> list[ExpectedObject]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [
        ExpectedObject(
            row["kind"],
            row["id"],
            row["top_level"],
            tuple(int(page) for page in row["printed_pages"].split(";")),
        )
        for row in rows
    ]


def metadata_errors(
    path: Path,
    metadata: dict[str, str],
    part_id: str,
    source_path: str,
    source_sha256: str,
    expected_title: str,
    required_status: str | None,
) -> list[str]:
    part = PARTS[part_id]
    expected = {
        "part": part.number,
        "title": expected_title,
        "source": source_path,
        "source_sha256": source_sha256,
        "pdf_pages": f"{part.first_pdf_page}-{part.last_pdf_page}",
        "printed_pages": f"{part.first_printed_page}-{part.last_printed_page}",
        "anchor_schema": "[edition:clause:fragment:printed_page_or_range]",
    }
    if required_status is not None:
        expected["status"] = required_status
    return [
        f"{path}: metadata {key}={metadata.get(key)!r}, expected {value!r}"
        for key, value in expected.items()
        if metadata.get(key) != value
    ]


def verify_directory(
    directory: Path,
    pdf: Path,
    inventory: Path,
    anchors_index: Path,
    required_status: str | None,
    check_generated: bool,
) -> tuple[list[str], Counter[str]]:
    errors: list[str] = []
    summary: Counter[str] = Counter()
    expected_files = {part.filename for part in PARTS.values()}
    actual_files = {path.name for path in directory.glob("*.txt")}
    missing_files = sorted(expected_files - actual_files)
    extra_files = sorted(actual_files - expected_files)
    if missing_files:
        errors.append(f"missing output files: {missing_files}")
    if extra_files:
        errors.append(f"unexpected output files: {extra_files}")

    source_sha256 = file_sha256(pdf)
    warn_if_reference_source_differs(
        pdf,
        source_sha256,
        require_follow_up=False,
    )
    parsed: dict[str, list[Anchor]] = {}
    parsed_metadata: dict[str, dict[str, str]] = {}
    all_raw_anchors: list[str] = []

    for part_id, part in PARTS.items():
        path = directory / part.filename
        if not path.exists():
            continue
        try:
            metadata, anchors = parse_metadata_and_anchors(path)
        except ValueError as error:
            errors.append(str(error))
            continue
        top_heading = [
            anchor for anchor in anchors if anchor.clause == part_id and anchor.fragment == "H"
        ]
        expected_title = metadata.get("title", "")
        if len(top_heading) == 1:
            try:
                expected_title = part_title_from_heading(top_heading[0].content, part)
            except RuntimeError as error:
                errors.append(f"{path}: {error}")
        errors.extend(
            metadata_errors(
                path,
                metadata,
                part_id,
                pdf.as_posix(),
                source_sha256,
                expected_title,
                required_status,
            )
        )
        parsed[part_id] = anchors
        parsed_metadata[part_id] = metadata
        all_raw_anchors.extend(anchor.raw for anchor in anchors)
        summary["files"] += 1
        summary["anchors"] += len(anchors)

        if len(top_heading) != 1:
            errors.append(f"{path}: expected one top-level heading, found {len(top_heading)}")
        elif top_heading[0].first_page != part.first_printed_page:
            errors.append(
                f"{path}: top-level heading is on p{top_heading[0].first_page}, "
                f"expected p{part.first_printed_page}"
            )

        covered_pages: set[int] = set()
        previous_first_page = part.first_printed_page
        for anchor in anchors:
            if anchor.edition != "2023":
                errors.append(f"{path}: wrong edition in {anchor.raw}")
            if not (anchor.clause == part_id or anchor.clause.startswith(f"{part_id}.")):
                errors.append(f"{path}: anchor belongs to another part: {anchor.raw}")
            if anchor.first_page < previous_first_page:
                errors.append(f"{path}: anchor page order regresses at {anchor.raw}")
            previous_first_page = anchor.first_page
            if anchor.first_page > anchor.last_page:
                errors.append(f"{path}: inverted page range in {anchor.raw}")
                continue
            if (
                anchor.first_page < part.first_printed_page
                or anchor.last_page > part.last_printed_page
            ):
                errors.append(f"{path}: anchor outside configured range: {anchor.raw}")
            covered_pages.update(range(anchor.first_page, anchor.last_page + 1))
        expected_pages = set(range(part.first_printed_page, part.last_printed_page + 1))
        if covered_pages != expected_pages:
            missing_pages = sorted(expected_pages - covered_pages)
            extra_pages = sorted(covered_pages - expected_pages)
            errors.append(
                f"{path}: anchor page coverage differs; "
                f"missing={missing_pages}, extra={extra_pages}"
            )

    duplicates = sorted(anchor for anchor, count in Counter(all_raw_anchors).items() if count > 1)
    if duplicates:
        errors.append(f"globally duplicate anchors: {duplicates[:10]}")

    summary["expected_anchor_indexes"] = 1
    if not anchors_index.is_file():
        errors.append(f"missing anchor index: {anchors_index}")
    elif len(parsed) == len(PARTS) and not duplicates:
        part_texts = {
            part_id: (directory / part.filename).read_text() for part_id, part in PARTS.items()
        }
        expected_index = render_anchors_index(part_texts, source_sha256)
        if anchors_index.read_text() != expected_index:
            errors.append(f"{anchors_index}: differs from deterministic regeneration")
        else:
            summary["anchor_indexes"] = 1

    actual_markers = Counter(
        marker
        for anchors in parsed.values()
        for anchor in anchors
        for marker in EXPECTED_VISUAL_REVIEW_MARKERS
        for _ in range(anchor.content.count(marker))
    )
    unknown_markers = sorted(
        {
            marker
            for anchors in parsed.values()
            for anchor in anchors
            for marker in re.findall(r"\[[A-Z_]+_REQUIRES_VISUAL_REVIEW\]", anchor.content)
            if marker not in EXPECTED_VISUAL_REVIEW_MARKERS
        }
    )
    if unknown_markers:
        errors.append(f"unknown visual-review markers: {unknown_markers}")
    if actual_markers != Counter(EXPECTED_VISUAL_REVIEW_MARKERS):
        errors.append(
            "visual-review marker inventory differs; "
            f"actual={dict(actual_markers)}, expected={EXPECTED_VISUAL_REVIEW_MARKERS}"
        )
    summary["visual_review_markers"] = sum(actual_markers.values())

    expected_objects = load_expected_objects(inventory)
    expected_by_part: dict[str, list[ExpectedObject]] = defaultdict(list)
    for item in expected_objects:
        expected_by_part[item.part].append(item)

    actual_objects: set[tuple[str, str, str]] = set()
    for part_id, anchors in parsed.items():
        for index, anchor in enumerate(anchors):
            table = TABLE_FRAGMENT_RE.fullmatch(anchor.fragment)
            figure = FIGURE_FRAGMENT_RE.fullmatch(anchor.fragment)
            syntax = SYNTAX_FRAGMENT_RE.fullmatch(anchor.fragment)
            if table:
                object_id = table.group(1)
                actual_objects.add(("Table", object_id, part_id))
                summary["tables"] += 1
                if (
                    object_id not in PARTS[part_id].reviewed_tables
                    and "[TABLE_REQUIRES_VISUAL_REVIEW]" not in anchor.content
                ):
                    errors.append(f"{part_id}: table {object_id} lacks its review marker")
                rows = [
                    candidate
                    for candidate in anchors
                    if (match := TABLE_ROW_RE.fullmatch(candidate.fragment))
                    and match.group(1) == object_id
                ]
                if not rows:
                    errors.append(f"{part_id}: table {object_id} has no annotation rows")
            elif figure:
                object_id = figure.group(1)
                actual_objects.add(("Figure", object_id, part_id))
                summary["figures"] += 1
                if "[FIGURE_REQUIRES_VISUAL_REVIEW]" not in anchor.content:
                    errors.append(f"{part_id}: figure {object_id} lacks its review marker")
            elif syntax:
                object_id = syntax.group(1)
                actual_objects.add(("Syntax", object_id, part_id))
                summary["syntax"] += 1
                if index == 0 or not GRAMMAR_FRAGMENT_RE.fullmatch(anchors[index - 1].fragment):
                    errors.append(
                        f"{part_id}: syntax {object_id} is not immediately preceded by grammar"
                    )
                else:
                    summary["syntax_with_grammar"] += 1

    expected_object_keys = {(item.kind, item.object_id, item.part) for item in expected_objects}
    missing_objects = sorted(expected_object_keys - actual_objects)
    extra_objects = sorted(actual_objects - expected_object_keys)
    if missing_objects:
        errors.append(f"missing numbered objects: {missing_objects[:20]}")
    if extra_objects:
        errors.append(f"unexpected numbered objects: {extra_objects[:20]}")

    for item in expected_objects:
        anchors = parsed.get(item.part, [])
        prefix = {"Table": "T", "Figure": "F", "Syntax": "S"}[item.kind]
        matches = [anchor for anchor in anchors if anchor.fragment == f"{prefix}{item.object_id}"]
        if len(matches) != 1:
            continue
        caption = matches[0]
        if caption.first_page != item.printed_pages[0]:
            errors.append(
                f"{item.part}: {item.kind} {item.object_id} caption on "
                f"p{caption.first_page}, expected p{item.printed_pages[0]}"
            )
        associated = [
            anchor
            for anchor in anchors
            if anchor.fragment == f"{prefix}{item.object_id}"
            or anchor.fragment.startswith(f"{prefix}{item.object_id}.")
        ]
        associated_pages = {
            page for anchor in associated for page in range(anchor.first_page, anchor.last_page + 1)
        }
        missing_object_pages = set(item.printed_pages) - associated_pages
        if missing_object_pages:
            errors.append(
                f"{item.part}: {item.kind} {item.object_id} lacks associated anchors on "
                f"pages {sorted(missing_object_pages)}"
            )

    if check_generated:
        for part_id, part in PARTS.items():
            path = directory / part.filename
            if not path.exists() or part_id not in parsed_metadata:
                continue
            status = parsed_metadata[part_id].get("status", "")
            regenerated = generate_part(pdf, source_sha256, part, status)
            if regenerated != path.read_text():
                errors.append(f"{path}: differs from deterministic regeneration")
            else:
                summary["regenerated"] += 1

    summary["expected_files"] = len(expected_files)
    summary["expected_tables"] = sum(item.kind == "Table" for item in expected_objects)
    summary["expected_figures"] = sum(item.kind == "Figure" for item in expected_objects)
    summary["expected_syntax"] = sum(item.kind == "Syntax" for item in expected_objects)
    return errors, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the IEEE 1800-2023 annotated corpus")
    parser.add_argument("directory", type=Path)
    add_pdf_argument(parser)
    parser.add_argument(
        "--inventory",
        type=Path,
        default=DATA_DIRECTORY / "objects.csv",
    )
    parser.add_argument(
        "--anchors-index",
        type=Path,
        help="anchor index path (defaults to anchors.json next to the text directory)",
    )
    parser.add_argument("--require-status")
    parser.add_argument(
        "--check-generated",
        action="store_true",
        help="regenerate every part and require byte-for-byte equality",
    )
    args = parser.parse_args()
    args.pdf = resolve_pdf_path(parser, args.pdf)
    return args


def main() -> None:
    args = parse_args()
    anchors_index = args.anchors_index or args.directory.parent / "anchors.json"
    errors, summary = verify_directory(
        args.directory,
        args.pdf,
        args.inventory,
        anchors_index,
        args.require_status,
        args.check_generated,
    )
    print(f"files: {summary['files']}/{summary['expected_files']}")
    print(f"anchors: {summary['anchors']} (globally unique if no errors below)")
    print(f"anchor index: {summary['anchor_indexes']}/{summary['expected_anchor_indexes']}")
    print(f"tables: {summary['tables']}/{summary['expected_tables']}")
    print(f"figures: {summary['figures']}/{summary['expected_figures']}")
    print(f"syntax captions: {summary['syntax']}/{summary['expected_syntax']}")
    grammar_captions = summary["syntax_with_grammar"]
    expected_syntax = summary["expected_syntax"]
    print(f"syntax captions preceded by grammar: {grammar_captions}/{expected_syntax}")
    print(f"visual-review markers: {summary['visual_review_markers']}")
    if args.check_generated:
        print(f"deterministic regenerations: {summary['regenerated']}/{summary['expected_files']}")
    if errors:
        print(f"errors: {len(errors)}")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("verification: PASS")


if __name__ == "__main__":
    main()
