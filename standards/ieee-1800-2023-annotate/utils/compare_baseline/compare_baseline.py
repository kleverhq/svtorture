#!/usr/bin/env python3
"""Compare generated blocks with a separately stored reviewed baseline."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from annotate import ANCHOR_RE


ALLOWED_REVIEW_MARKERS = {
    "[GLYPH_REQUIRES_VISUAL_REVIEW]",
    "[TEXT_ANNOTATION_REQUIRES_VISUAL_REVIEW]",
    "[VECTOR_TOPOLOGY_REQUIRES_VISUAL_REVIEW]",
}


@dataclass(frozen=True)
class ParsedText:
    preamble: str
    anchors: tuple[str, ...]
    blocks: tuple[str, ...]


@dataclass
class CompatibilityResult:
    baseline_anchors: int = 0
    candidate_anchors: int = 0
    exact_blocks: int = 0
    marked_differing_blocks: int = 0
    unmarked_differences: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def compatible(self) -> bool:
        return not self.errors and not self.unmarked_differences


def parse_text(path: Path) -> ParsedText:
    lines = path.read_text().splitlines(keepends=True)
    indexes = [
        index for index, line in enumerate(lines) if ANCHOR_RE.fullmatch(line.rstrip("\r\n"))
    ]
    if not indexes:
        raise ValueError(f"{path}: no anchors")

    anchors: list[str] = []
    blocks: list[str] = []
    for position, start in enumerate(indexes):
        end = indexes[position + 1] if position + 1 < len(indexes) else len(lines)
        anchors.append(lines[start].rstrip("\r\n"))
        blocks.append("".join(lines[start:end]))
    return ParsedText("".join(lines[: indexes[0]]), tuple(anchors), tuple(blocks))


def block_has_review_marker(block: str) -> bool:
    return any(marker in block.splitlines() for marker in ALLOWED_REVIEW_MARKERS)


def normalized_preamble(preamble: str) -> str:
    ignored = {"source", "source_sha256", "status"}
    lines: list[str] = []
    for line in preamble.splitlines(keepends=True):
        key = line.split("=", 1)[0]
        lines.append(f"{key}=<input-specific>\n" if key in ignored else line)
    return "".join(lines)


def normalized_index(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text())
    value.pop("source_sha256", None)
    return value


def compare_corpora(baseline_root: Path, candidate_root: Path) -> CompatibilityResult:
    result = CompatibilityResult()
    baseline_txt = baseline_root / "txt"
    candidate_txt = candidate_root / "txt"
    baseline_files = {path.name for path in baseline_txt.glob("*.txt")}
    candidate_files = {path.name for path in candidate_txt.glob("*.txt")}
    if baseline_files != candidate_files:
        missing = sorted(baseline_files - candidate_files)
        extra = sorted(candidate_files - baseline_files)
        result.errors.append(f"text file inventory differs; missing={missing}, extra={extra}")

    baseline_index = baseline_root / "anchors.json"
    candidate_index = candidate_root / "anchors.json"
    if not baseline_index.is_file() or not candidate_index.is_file():
        result.errors.append("both corpus roots must contain anchors.json")
    elif normalized_index(baseline_index) != normalized_index(candidate_index):
        result.errors.append("anchors.json differs except for input-specific metadata")

    for filename in sorted(baseline_files & candidate_files):
        baseline_path = baseline_txt / filename
        candidate_path = candidate_txt / filename
        try:
            baseline = parse_text(baseline_path)
            candidate = parse_text(candidate_path)
        except ValueError as error:
            result.errors.append(str(error))
            continue

        result.baseline_anchors += len(baseline.anchors)
        result.candidate_anchors += len(candidate.anchors)
        if normalized_preamble(baseline.preamble) != normalized_preamble(candidate.preamble):
            result.errors.append(f"{filename}: metadata preamble differs")
        if baseline.anchors != candidate.anchors:
            baseline_set = set(baseline.anchors)
            candidate_set = set(candidate.anchors)
            result.errors.append(
                f"{filename}: anchor sequence differs; "
                f"missing={sorted(baseline_set - candidate_set)[:5]}, "
                f"extra={sorted(candidate_set - baseline_set)[:5]}"
            )
            continue

        for anchor, baseline_block, candidate_block in zip(
            baseline.anchors, baseline.blocks, candidate.blocks, strict=True
        ):
            if baseline_block == candidate_block:
                result.exact_blocks += 1
            elif block_has_review_marker(candidate_block):
                result.marked_differing_blocks += 1
            else:
                result.unmarked_differences.append(f"{filename}: {anchor}")

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare a generated corpus with a private reviewed baseline"
    )
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = compare_corpora(args.baseline, args.candidate)
    print(f"baseline anchors: {result.baseline_anchors}")
    print(f"candidate anchors: {result.candidate_anchors}")
    print(f"exact blocks: {result.exact_blocks}")
    print(f"marked differing blocks: {result.marked_differing_blocks}")
    print(f"unmarked differing blocks: {len(result.unmarked_differences)}")
    for difference in result.unmarked_differences[:20]:
        print(f"- {difference}")
    for error in result.errors:
        print(f"- {error}")
    print(f"anchor compatibility: {'PASS' if not result.errors else 'FAIL'}")
    print(f"compatibility: {'PASS' if result.compatible else 'FAIL'}")
    if not result.compatible:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
