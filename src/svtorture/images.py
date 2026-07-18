"""Build project-controlled tool images and capture immutable identities."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from pydantic import ValidationError

from svtorture.hashing import hash_json, sha256_file
from svtorture.models import ImageIdentity, ToolDefinition, ToolSelection, model_to_jsonable


class ImageError(RuntimeError):
    pass


def _run(argv: list[str], timeout: int = 3600) -> str:
    completed = subprocess.run(
        argv,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    if completed.returncode != 0:
        excerpt = completed.stdout[-12000:]
        raise ImageError(f"command failed ({completed.returncode}): {' '.join(argv)}\n{excerpt}")
    return completed.stdout


def _base_image(dockerfile: Path) -> str:
    for line in dockerfile.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\s*ARG\s+BASE_IMAGE=(\S+)", line)
        if match:
            return match.group(1)
    raise ImageError(f"{dockerfile}: BASE_IMAGE default is required")


def _inspect(reference: str, field: str) -> str:
    return _run(["docker", "image", "inspect", "--format", field, reference], 120).strip()


def _pull_base(base: str) -> tuple[str, str]:
    _run(["docker", "pull", "--platform=linux/amd64", base], 900)
    repo_digests = _inspect(base, "{{json .RepoDigests}}")
    values = json.loads(repo_digests)
    if not values:
        raise ImageError(f"base image {base} has no immutable repository digest")
    pinned = str(values[0])
    digest = pinned.rsplit("@", 1)[-1]
    return pinned, digest


def recipe_hash(root: Path, tool: ToolDefinition) -> str:
    assert tool.dockerfile is not None
    dockerfile = root / tool.dockerfile
    payload: dict[str, str] = {
        tool.dockerfile: sha256_file(dockerfile),
    }
    for relative in tool.recipe_files:
        payload[relative] = sha256_file(root / relative)
    return hash_json(payload)


def _cache_path(root: Path, tool: ToolDefinition, suffix: str) -> Path:
    return root / ".svtorture" / "images" / f"{tool.id}-{suffix}.json"


def load_cached_image(
    root: Path,
    tool: ToolDefinition,
    suffix: str,
    *,
    expected_base_image: str | None = None,
    expected_source_sha: str | None = None,
) -> ImageIdentity | None:
    path = _cache_path(root, tool, suffix)
    if not path.exists():
        return None
    try:
        value = ImageIdentity.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None
    if value.recipe_sha256 != recipe_hash(root, tool):
        return None
    if expected_base_image is not None and value.base_image != expected_base_image:
        return None
    try:
        current_id = _inspect(value.reference, "{{.Id}}")
        labels = json.loads(_inspect(value.reference, "{{json .Config.Labels}}"))
    except (ImageError, json.JSONDecodeError):
        return None
    if not isinstance(labels, dict):
        return None
    if current_id != value.image_id:
        return None
    if labels.get("org.svtorture.recipe-sha256") != value.recipe_sha256:
        return None
    if (
        expected_source_sha is not None
        and labels.get("org.opencontainers.image.revision") != expected_source_sha
    ):
        return None
    return value


def build_image(
    root: Path,
    tool: ToolDefinition,
    selection: ToolSelection | None,
    *,
    repository_override: str | None = None,
    push: bool = False,
    base_image_reference: str | None = None,
) -> ImageIdentity:
    if tool.dockerfile is None or tool.image_repository is None:
        raise ImageError(f"tool {tool.id} does not define an image recipe")
    dockerfile = root / tool.dockerfile
    recipe = recipe_hash(root, tool)
    # Cache keys and tags carry the full source/recipe identity; abbreviated
    # SHAs are display-only and must never select executable content.
    suffix = selection.resolved_sha if selection else f"bundled-{recipe}"
    cached = load_cached_image(
        root,
        tool,
        suffix,
        expected_base_image=base_image_reference,
        expected_source_sha=selection.resolved_sha if selection else None,
    )
    if cached is not None and not push:
        return cached
    repository = repository_override or tool.image_repository
    tag = f"{repository}:{suffix}"
    base = base_image_reference or _base_image(dockerfile)
    pinned_base, base_digest = _pull_base(base)
    if base_image_reference is not None and pinned_base != base_image_reference:
        raise ImageError("recorded base image did not resolve to its original repository digest")
    argv = [
        "docker",
        "build",
        "--pull=false",
        "--platform=linux/amd64",
        "--build-arg",
        f"BASE_IMAGE={pinned_base}",
        "--label",
        f"org.svtorture.recipe-sha256={recipe}",
        "-f",
        str(dockerfile),
        "-t",
        tag,
    ]
    if selection is not None:
        argv.extend(["--build-arg", f"TOOL_SHA={selection.resolved_sha}"])
    argv.append(str(root))
    _run(argv, 7200)
    image_id = _inspect(tag, "{{.Id}}")
    if not image_id.startswith("sha256:"):
        raise ImageError("Docker returned an invalid image id")
    try:
        labels = json.loads(_inspect(tag, "{{json .Config.Labels}}"))
    except json.JSONDecodeError as error:
        raise ImageError("Docker returned malformed image labels") from error
    if not isinstance(labels, dict):
        raise ImageError("Docker returned malformed image labels")
    if labels.get("org.svtorture.recipe-sha256") != recipe:
        raise ImageError("built image does not carry the exact recipe identity")
    if (
        selection is not None
        and labels.get("org.opencontainers.image.revision") != selection.resolved_sha
    ):
        raise ImageError("built image does not carry the exact upstream source identity")
    digest = image_id
    reference = image_id
    if push:
        _run(["docker", "push", tag], 3600)
        values = json.loads(_inspect(tag, "{{json .RepoDigests}}"))
        matching = [item for item in values if item.startswith(repository + "@")]
        if not matching:
            raise ImageError("pushed image has no repository digest")
        reference = matching[0]
        digest = reference.rsplit("@", 1)[1]
    identity = ImageIdentity(
        reference=reference,
        image_id=image_id,
        digest=digest,
        recipe_sha256=recipe,
        base_image=pinned_base,
        base_image_digest=base_digest,
        platform="linux/amd64",
    )
    cache_path = _cache_path(root, tool, suffix)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(model_to_jsonable(identity), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return identity
