"""Resolve latest or pinned upstream refs to one immutable full commit SHA."""

from __future__ import annotations

import re
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from svtorture.models import ToolDefinition, ToolSelection


class ResolutionError(RuntimeError):
    pass


def parse_requested_tool(value: str) -> tuple[str, str]:
    if value.count("@") != 1:
        raise ResolutionError("tool selection must have the form tool@ref")
    tool, requested = value.split("@", 1)
    if not tool or not requested or any(character.isspace() for character in value):
        raise ResolutionError("tool selection contains an empty or whitespace component")
    return tool, requested


def _git_ls_remote(url: str, *patterns: str, symref: bool = False) -> list[str]:
    argv = ["git", "ls-remote"]
    if symref:
        argv.append("--symref")
    argv.append(url)
    argv.extend(patterns)
    completed = subprocess.run(
        argv,
        check=False,
        text=True,
        capture_output=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise ResolutionError(completed.stderr.strip() or "git ls-remote failed")
    return completed.stdout.splitlines()


def _tags_at(url: str, sha: str) -> tuple[str, ...]:
    lines = _git_ls_remote(url, "refs/tags/*")
    direct: dict[str, str] = {}
    peeled: dict[str, str] = {}
    for line in lines:
        try:
            value, reference = line.split("\t", 1)
        except ValueError:
            continue
        if reference.endswith("^{}"):
            peeled[reference.removesuffix("^{}")] = value
        else:
            direct[reference] = value
    names = {
        reference.removeprefix("refs/tags/")
        for reference, value in direct.items()
        if value == sha and reference not in peeled
    }
    names.update(
        reference.removeprefix("refs/tags/") for reference, value in peeled.items() if value == sha
    )
    return tuple(sorted(names))


def _resolve_full_sha(url: str, requested: str) -> str:
    with tempfile.TemporaryDirectory(prefix="svtorture-ref-") as temporary:
        directory = Path(temporary)
        init = subprocess.run(
            ["git", "init", "-q", str(directory)],
            check=False,
            stderr=subprocess.PIPE,
            text=True,
        )
        if init.returncode != 0:
            raise ResolutionError(init.stderr.strip())
        fetch = subprocess.run(
            ["git", "-C", str(directory), "fetch", "-q", "--depth=1", url, requested],
            check=False,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300,
        )
        if fetch.returncode != 0:
            raise ResolutionError(
                f"commit {requested} is not fetchable from the configured upstream"
            )
        resolved = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "FETCH_HEAD^{commit}"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
    if resolved != requested:
        raise ResolutionError("requested full SHA did not resolve to itself")
    return resolved


def resolve_tool_ref(tool: ToolDefinition, requested_ref: str) -> ToolSelection:
    if not tool.upstream_url:
        raise ResolutionError(f"tool {tool.id} has no resolvable public upstream")
    default_branch: str | None = tool.default_branch
    if requested_ref == "latest":
        if not default_branch:
            raise ResolutionError(f"tool {tool.id} has no configured default branch")
        reference = f"refs/heads/{default_branch}"
        lines = _git_ls_remote(tool.upstream_url, reference)
        candidates: set[str] = set()
        for line in lines:
            try:
                value, returned_reference = line.split("\t", 1)
            except ValueError:
                continue
            if returned_reference == reference:
                candidates.add(value)
        if len(candidates) != 1:
            raise ResolutionError(
                f"configured default branch {default_branch!r} resolved to "
                f"{len(candidates)} commits"
            )
        sha = next(iter(candidates))
    elif re.fullmatch(r"[0-9a-f]{40}", requested_ref):
        sha = _resolve_full_sha(tool.upstream_url, requested_ref)
    else:
        patterns = (
            f"refs/heads/{requested_ref}",
            f"refs/tags/{requested_ref}",
            f"refs/tags/{requested_ref}^{{}}",
        )
        lines = _git_ls_remote(tool.upstream_url, *patterns)
        branches: set[str] = set()
        tags: set[str] = set()
        tag_object: str | None = None
        peeled: str | None = None
        for line in lines:
            try:
                value, reference = line.split("\t", 1)
            except ValueError:
                continue
            if reference.startswith("refs/heads/"):
                branches.add(value)
            elif reference.endswith("^{}"):
                peeled = value
            elif reference.startswith("refs/tags/"):
                tag_object = value
        if peeled is not None:
            tags.add(peeled)
        elif tag_object is not None:
            tags.add(tag_object)
        if branches and tags:
            raise ResolutionError(f"ref {requested_ref!r} is ambiguous between a branch and a tag")
        candidates = branches | tags
        if len(candidates) != 1:
            raise ResolutionError(f"ref {requested_ref!r} resolved to {len(candidates)} commits")
        sha = next(iter(candidates))
    if re.fullmatch(r"[0-9a-f]{40}", sha) is None:
        raise ResolutionError("upstream returned a malformed commit SHA")
    exact_tags = _tags_at(tool.upstream_url, sha)
    return ToolSelection(
        tool=tool.id,
        requested_ref=requested_ref,
        resolved_sha=sha,
        resolved_at=datetime.now(UTC),
        exact_tags=exact_tags,
        nearest_tag=exact_tags[-1] if exact_tags else None,
        default_branch=default_branch,
    )
