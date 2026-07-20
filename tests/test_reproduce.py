from pathlib import Path

import pytest

import svtorture.reproduce as reproduction


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
