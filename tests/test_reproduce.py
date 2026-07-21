from pathlib import Path
from types import SimpleNamespace

import pytest

import svtorture.reproduce as reproduction
from svtorture.catalog import Catalog
from tests.helpers import campaign_tool


class CatalogLoaded(Exception):
    pass


def test_replay_uses_the_current_vendored_anchor_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "current"
    checkout = tmp_path / "recorded"
    observed: dict[str, Path] = {}

    monkeypatch.setattr(reproduction, "_ensure_checkout", lambda *_args: checkout)

    def load_catalog(path: Path, *, anchor_index: Path) -> None:
        observed["checkout"] = path
        observed["anchor_index"] = anchor_index
        raise CatalogLoaded

    monkeypatch.setattr(reproduction, "load_catalog", load_catalog)
    with pytest.raises(CatalogLoaded):
        reproduction.reproduce_case(
            root,
            object(),
            tool_id="tool",
            profile_id="profile",
            case_id="case",
        )

    assert observed == {
        "checkout": checkout,
        "anchor_index": root / "standards" / "ieee-1800-2023-anchors.json",
    }


def test_rebuilt_image_must_match_recorded_image_id(
    catalog: Catalog,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool = campaign_tool(catalog.tools.tool("icarus"), ("simulator",))
    assert tool.image is not None
    monkeypatch.setattr(
        reproduction.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1),
    )
    monkeypatch.setattr(
        reproduction,
        "recipe_hash",
        lambda *_args: tool.image.recipe_sha256,
    )
    rebuilt = tool.image.model_copy(update={"image_id": "sha256:" + "f" * 64})
    monkeypatch.setattr(reproduction, "build_image", lambda *_args, **_kwargs: rebuilt)

    with pytest.raises(reproduction.ReproductionError, match="image ID differs"):
        reproduction._ensure_image(tmp_path, tool)
