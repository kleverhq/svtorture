#!/usr/bin/env python3
"""Publish trusted campaign data through the append-only Pages branch.

The Pages workflow invokes this helper after building the dashboard. It creates
a temporary ``gh-pages`` worktree, asks the strict publisher to merge new
campaigns with retained history, commits the resulting site, and pushes without
rewriting existing publication history.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from svtorture.campaign import load_campaign
from svtorture.catalog import load_catalog
from svtorture.publish import publish_pages_tree

ROOT = Path(__file__).resolve().parents[1]


def _git(*arguments: str, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(cwd), *arguments],
        check=False,
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("campaigns", nargs="+", type=Path)
    parser.add_argument(
        "--built-site",
        type=Path,
        default=ROOT / "dashboard" / "dist",
    )
    arguments = parser.parse_args()
    pages = ROOT / ".svtorture" / "gh-pages"
    if pages.exists():
        removal = _git("worktree", "remove", "--force", str(pages), check=False)
        if removal.returncode != 0:
            shutil.rmtree(pages)
            _git("worktree", "prune")

    fetched = _git("fetch", "--no-tags", "origin", "gh-pages", check=False)
    branch_exists = fetched.returncode == 0
    if branch_exists:
        _git("worktree", "add", "--detach", str(pages), "origin/gh-pages")
    else:
        _git("worktree", "add", "--detach", str(pages), "HEAD")
        _git("checkout", "--orphan", "gh-pages", cwd=pages)
        _git("rm", "-rf", ".", cwd=pages)

    try:
        catalog = load_catalog(ROOT)
        campaigns = tuple(load_campaign(path) for path in arguments.campaigns)
        publish_pages_tree(catalog, campaigns, arguments.built_site, pages)
        _git("config", "user.name", "github-actions[bot]", cwd=pages)
        _git(
            "config",
            "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com",
            cwd=pages,
        )
        _git("add", "--all", cwd=pages)
        if _git("diff", "--cached", "--quiet", cwd=pages, check=False).returncode == 0:
            print("gh-pages already contains this campaign")
            return 0
        run_id = os.environ.get("GITHUB_RUN_ID", "local")
        _git("commit", "-m", f"dashboard: append campaign from run {run_id}", cwd=pages)
        _git("push", "origin", "HEAD:gh-pages", cwd=pages)
        print("updated gh-pages without force")
        return 0
    finally:
        _git("worktree", "remove", "--force", str(pages), check=False)


if __name__ == "__main__":
    raise SystemExit(main())
