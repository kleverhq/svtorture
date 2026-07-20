from pathlib import Path
from types import SimpleNamespace

import pytest

import svtorture.reproduce as reproduction
from svtorture.models import RepositoryIdentity

RECORDED_SHA = "1" * 40
CURRENT_SHA = "2" * 40


def test_initialize_submodules_updates_uninitialized_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def run(argv: list[str], **_kwargs: object) -> reproduction.subprocess.CompletedProcess[str]:
        calls.append(argv)
        if "status" in argv:
            return reproduction.subprocess.CompletedProcess(
                argv, 0, stdout=f"-{RECORDED_SHA} standards/annotated\n", stderr=""
            )
        return reproduction.subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(reproduction.subprocess, "run", run)
    reproduction._initialize_submodules(tmp_path)

    assert calls[-1][-3:] == ["update", "--init", "--recursive"]


def test_reused_replay_worktree_initializes_submodules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / ".svtorture" / "reproduce" / RECORDED_SHA
    destination.mkdir(parents=True)
    campaign = SimpleNamespace(repository=RepositoryIdentity(commit=RECORDED_SHA, dirty=False))

    monkeypatch.setattr(
        reproduction,
        "repository_identity",
        lambda path: RepositoryIdentity(
            commit=RECORDED_SHA if path == destination else CURRENT_SHA,
            dirty=False,
        ),
    )
    initialized: list[Path] = []
    monkeypatch.setattr(reproduction, "_initialize_submodules", initialized.append)

    assert reproduction._ensure_checkout(tmp_path, campaign) == destination
    assert initialized == [destination]
