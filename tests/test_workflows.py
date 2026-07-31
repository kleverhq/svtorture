import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_enabled_ci_and_manual_dashboard_workflows_have_bounded_triggers() -> None:
    assert not list(WORKFLOWS.glob("*.disabled"))
    ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    assert "pull_request:" in ci
    assert "branches: [main]" in ci
    assert "contents: read" in ci

    publication = (WORKFLOWS / "publish-dashboard.yml").read_text(encoding="utf-8")
    trigger = publication.split("concurrency:", 1)[0]
    assert "workflow_dispatch:" in trigger
    assert publication.count("github.ref == 'refs/heads/main'") == 2
    assert "schedule:" not in trigger
    assert "push:" not in trigger
    assert "pull_request:" not in trigger
    assert "contents: write" in publication
    assert "packages: write" in publication
    assert "pages: write" in publication
    assert "id-token: write" in publication
    assert "actions/upload-pages-artifact" in publication
    assert "actions/deploy-pages" in publication
    assert "retention-days: 7" in publication
    assert "gh-pages" not in publication
    assert "--clobber" not in publication
    for workflow in (ci, publication):
        for action in re.findall(r"uses:\s+([^\s#]+)", workflow):
            assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", action), action


def test_publication_uses_stable_just_and_script_interfaces() -> None:
    publication = (WORKFLOWS / "publish-dashboard.yml").read_text(encoding="utf-8")
    assert "TOOL: ${{ matrix.tool }}" in publication
    assert 'run: just collect-public "$TOOL"' in publication
    assert "run: just aggregate-artifacts .nightly-artifacts" in publication
    assert 'run: just dashboard-publish "$(cat .svtorture/nightly-aggregate-path)"' in publication

    script = (ROOT / "scripts" / "publish_dashboard.py").read_text(encoding="utf-8")
    assert "Publish immutable campaign Releases" in script
    assert "publish_dashboard(" in script
    justfile = (ROOT / "justfile").read_text(encoding="utf-8")
    assert "--campaign-list {{quote(campaigns)}}" in justfile
