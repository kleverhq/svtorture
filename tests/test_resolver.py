from __future__ import annotations

import pytest

import svtorture.resolver as resolver
from svtorture.catalog import Catalog
from svtorture.resolver import ResolutionError, parse_requested_tool, resolve_tool_ref


@pytest.mark.parametrize("value", ("slang", "slang@", "@latest", "a@b@c", "a@bad ref"))
def test_invalid_tool_selection_is_rejected(value: str) -> None:
    with pytest.raises(ResolutionError):
        parse_requested_tool(value)


def test_latest_resolves_to_full_default_branch_sha(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    sha = "a" * 40

    def fake_ls_remote(_url: str, *patterns: str, symref: bool = False) -> list[str]:
        assert not symref
        if patterns == ("refs/heads/master",):
            return [f"{sha}\trefs/heads/master"]
        if patterns == ("refs/tags/*",):
            return [f"{sha}\trefs/tags/v1.0.0"]
        raise AssertionError(patterns)

    monkeypatch.setattr(resolver, "_git_ls_remote", fake_ls_remote)
    selection = resolve_tool_ref(catalog.tools.tool("slang"), "latest")
    assert selection.resolved_sha == sha
    assert selection.default_branch == "master"
    assert selection.exact_tags == ("v1.0.0",)
    assert selection.nearest_tag == "v1.0.0"


def test_ambiguous_branch_and_tag_is_rejected(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = "a" * 40
    second = "b" * 40

    def fake_ls_remote(_url: str, *patterns: str, symref: bool = False) -> list[str]:
        del patterns, symref
        return [
            f"{first}\trefs/heads/candidate",
            f"{second}\trefs/tags/candidate",
        ]

    monkeypatch.setattr(resolver, "_git_ls_remote", fake_ls_remote)
    with pytest.raises(ResolutionError, match="ambiguous"):
        resolve_tool_ref(catalog.tools.tool("slang"), "candidate")


def test_exact_commit_is_verified_and_retained(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    sha = "c" * 40
    monkeypatch.setattr(resolver, "_resolve_full_sha", lambda _url, value: value)
    monkeypatch.setattr(resolver, "_tags_at", lambda _url, _sha: ())
    selection = resolve_tool_ref(catalog.tools.tool("icarus"), sha)
    assert selection.requested_ref == sha
    assert selection.resolved_sha == sha
