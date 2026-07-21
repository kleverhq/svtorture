#!/usr/bin/env python3
"""Detect long reviewed-baseline token sequences in repository source files."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


TOKEN_RE = re.compile(r"[A-Za-z0-9_$]+(?:['.-][A-Za-z0-9_$]+)*")
TEXT_SUFFIXES = {".csv", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}


def normalized_tokens(text: str) -> list[str]:
    return [match.group(0).casefold() for match in TOKEN_RE.finditer(text)]


def baseline_tokens(path: Path) -> list[str]:
    lines: list[str] = []
    seen_anchor = False
    for line in path.read_text().splitlines():
        if line.startswith("[2023:"):
            seen_anchor = True
            continue
        if not seen_anchor or line.endswith("REQUIRES_VISUAL_REVIEW]"):
            continue
        lines.append(line)
    return normalized_tokens("\n".join(lines))


def baseline_ngrams(baseline_root: Path, size: int) -> set[tuple[str, ...]]:
    grams: set[tuple[str, ...]] = set()
    for path in sorted((baseline_root / "txt").glob("*.txt")):
        tokens = baseline_tokens(path)
        grams.update(tuple(tokens[index : index + size]) for index in range(len(tokens) - size + 1))
    return grams


def copied_ngrams(
    baseline_root: Path,
    candidates: list[Path],
    size: int,
) -> dict[Path, list[str]]:
    expected = baseline_ngrams(baseline_root, size)
    matches: dict[Path, list[str]] = {}
    for path in candidates:
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        tokens = normalized_tokens(path.read_text())
        found: list[str] = []
        seen: set[tuple[str, ...]] = set()
        for index in range(len(tokens) - size + 1):
            gram = tuple(tokens[index : index + size])
            if gram in expected and gram not in seen:
                found.append(" ".join(gram))
                seen.add(gram)
        if found:
            matches[path] = found
    return matches


def tracked_candidates() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    )
    return [Path(raw.decode()) for raw in result.stdout.split(b"\0") if raw]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find long reviewed-corpus token sequences in source files"
    )
    parser.add_argument("baseline", type=Path, help="private corpus root containing txt/")
    parser.add_argument(
        "paths", nargs="*", type=Path, help="files to scan; defaults to tracked files"
    )
    parser.add_argument("--words", type=int, default=8, help="token sequence length")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.words < 2:
        raise SystemExit("--words must be at least 2")
    candidates = args.paths or tracked_candidates()
    matches = copied_ngrams(args.baseline, candidates, args.words)
    print(f"candidate files: {len(candidates)}")
    print(f"matching files: {len(matches)}")
    for path, sequences in matches.items():
        print(f"{path}: {len(sequences)} match(es)")
        for sequence in sequences[:3]:
            print(f"  {sequence}")
    print(f"copied-text scan: {'FAIL' if matches else 'PASS'}")
    if matches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
