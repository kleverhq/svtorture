"""Deterministic hashing helpers for manifests and evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from svtorture.models import StrictModel, model_to_jsonable


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def hash_json(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def hash_models(models: Iterable[StrictModel]) -> str:
    return hash_json([model_to_jsonable(model) for model in models])


def hash_paths(root: Path, paths: Iterable[Path]) -> str:
    """Hash ordered relative path names and bytes without host path leakage."""

    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(root).as_posix().encode()
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()
