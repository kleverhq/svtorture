"""SVTORTURE command-line interface."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated

import typer

from svtorture import __version__
from svtorture.adapters.registry import adapter_for
from svtorture.campaign import (
    CampaignError,
    PreparedTool,
    aggregate_campaigns,
    create_preparation_failure_campaign,
    load_campaign,
    load_campaign_location,
    load_private_config,
    report_image_version,
    report_wrapper_version,
    run_campaign,
    wrapper_available,
)
from svtorture.catalog import (
    Catalog,
    CatalogError,
    load_catalog,
    mvp_audit,
    write_json_schema,
)
from svtorture.evaluator import exit_code_for_results
from svtorture.images import ImageError, build_image, load_cached_image, recipe_hash
from svtorture.models import (
    Distribution,
    ExecutionBackend,
    ExitPolicy,
    ToolSelection,
    model_to_jsonable,
)
from svtorture.publish import (
    PublicationError,
    publish_pages_tree,
    write_dataset,
)
from svtorture.reproduce import ReproductionError, reproduce_case
from svtorture.resolver import ResolutionError, parse_requested_tool, resolve_tool_ref

ROOT = Path(__file__).resolve().parents[2]
app = typer.Typer(
    name="svtorture",
    help="Standards-driven SystemVerilog conformance campaigns.",
    no_args_is_help=True,
)
dashboard_app = typer.Typer(help="Build, inspect, and publish static dashboard data.")
app.add_typer(dashboard_app, name="dashboard")


def _catalog() -> Catalog:
    try:
        return load_catalog(ROOT)
    except CatalogError as error:
        typer.echo(f"validation error: {error}", err=True)
        raise typer.Exit(2) from error


def _profile_overrides(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if value.count("=") != 1:
            raise typer.BadParameter("profiles must have the form tool=profile")
        tool, profile = value.split("=", 1)
        if not tool or not profile or tool in result:
            raise typer.BadParameter("profile overrides must be unique and nonempty")
        result[tool] = profile
    return result


def _save_selection(selection: ToolSelection) -> Path:
    path = ROOT / ".svtorture" / "selections" / f"{selection.tool}-{selection.resolved_sha}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(model_to_jsonable(selection), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _prepare(
    catalog: Catalog,
    specification: str,
    profile_id: str | None,
    *,
    build: bool,
    push: bool,
    repository: str | None,
    fake_scenario: str,
) -> PreparedTool:
    tool_id, requested_ref = parse_requested_tool(specification)
    try:
        tool = catalog.tools.tool(tool_id)
    except KeyError as error:
        raise typer.BadParameter(str(error)) from error
    try:
        profile = tool.profile(profile_id) if profile_id else tool.headline_profile
    except KeyError as error:
        raise typer.BadParameter(str(error)) from error
    selection = None
    image = None
    wrapper = None
    reported_version = None
    if tool.execution is ExecutionBackend.LOCAL_WRAPPER:
        if requested_ref != "local":
            raise typer.BadParameter("local-wrapper tools use the explicit ref 'local'")
        private = load_private_config(ROOT)
        wrapper = private.wrapper(tool.id) if private else None
    elif tool.distribution is Distribution.INTERNAL:
        if requested_ref != "bundled":
            raise typer.BadParameter("internal fake tool uses the ref 'bundled'")
        suffix = f"bundled-{recipe_hash(ROOT, tool)}"
        image = (
            build_image(ROOT, tool, None, repository_override=repository, push=push)
            if build
            else load_cached_image(ROOT, tool, suffix)
        )
    else:
        selection = resolve_tool_ref(tool, requested_ref)
        _save_selection(selection)
        image = (
            build_image(
                ROOT,
                tool,
                selection,
                repository_override=repository,
                push=push,
            )
            if build
            else load_cached_image(
                ROOT,
                tool,
                selection.resolved_sha,
                expected_source_sha=selection.resolved_sha,
            )
        )
    adapter = adapter_for(
        tool.adapter,
        rules_path=ROOT / "toolchains" / "diagnostic-rules.toml",
    )
    if tool.execution is ExecutionBackend.DOCKER:
        if image is None:
            raise ImageError(f"no prepared image is cached for {tool.id}")
        reported_version = report_image_version(
            image,
            adapter.version_argv(),
            ROOT / ".svtorture" / "version-work" / tool.id,
        )
    elif wrapper is not None and wrapper_available(wrapper):
        reported_version = report_wrapper_version(
            wrapper,
            tool.id,
            adapter.version_argv(),
            ROOT / ".svtorture" / "version-work" / tool.id,
        )
    return PreparedTool(
        definition=tool,
        profile=profile,
        selection=selection,
        image=image,
        reported_version=reported_version,
        wrapper=wrapper,
        fake_scenario=fake_scenario,
    )


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the installed SVTORTURE version."),
    ] = False,
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command("validate")
def validate(
    schemas: Annotated[
        bool,
        typer.Option("--schemas/--no-schemas", help="Also verify committed JSON schemas."),
    ] = True,
) -> None:
    catalog = _catalog()
    counts = mvp_audit(catalog)
    if schemas:
        with tempfile.TemporaryDirectory(prefix="svtorture-schema-") as temporary:
            generated = Path(temporary)
            write_json_schema(ROOT, generated)
            committed = ROOT / "schemas"
            for path in sorted(generated.glob("*.json")):
                counterpart = committed / path.name
                if not counterpart.exists() or counterpart.read_bytes() != path.read_bytes():
                    typer.echo(
                        f"schema mismatch: {path.name}; run svtorture schemas --write",
                        err=True,
                    )
                    raise typer.Exit(2)
    typer.echo(
        "validated " + ", ".join(f"{name}={value}" for name, value in sorted(counts.items()))
    )


@app.command("schemas")
def schemas(
    write: Annotated[
        bool, typer.Option("--write", help="Regenerate committed public schemas.")
    ] = False,
) -> None:
    _catalog()
    if not write:
        typer.echo("pass --write to regenerate schemas")
        return
    write_json_schema(ROOT, ROOT / "schemas")
    typer.echo("wrote schemas/")


@app.command("list")
def list_items(
    kind: Annotated[str, typer.Argument(help="One of: requirements, cases, suites, tools.")],
) -> None:
    catalog = _catalog()
    if kind == "requirements":
        for requirement in catalog.inventory.requirements:
            typer.echo(f"{requirement.id}\t{requirement.clause}\t{requirement.summary}")
    elif kind == "cases":
        for loaded_case in catalog.cases.values():
            typer.echo(
                f"{loaded_case.definition.id}\t"
                f"{loaded_case.definition.target_phase.value}\t"
                f"{loaded_case.definition.expectation.value}"
            )
    elif kind == "suites":
        for suite in catalog.suites.values():
            typer.echo(f"{suite.id}\t{len(suite.cases)}\t{suite.description}")
    elif kind == "tools":
        for tool in catalog.tools.tools:
            profiles = ",".join(profile.id for profile in tool.profiles)
            typer.echo(f"{tool.id}\t{tool.distribution.value}\t{tool.execution.value}\t{profiles}")
    else:
        raise typer.BadParameter("kind must be requirements, cases, suites, or tools")


@app.command("doctor")
def doctor() -> None:
    _catalog()
    failures = 0
    locations: dict[str, str | None] = {}
    for command in ("git", "docker", "uv", "npm", "just"):
        location = shutil.which(command)
        locations[command] = location
        typer.echo(f"{command}: {location or 'missing'}")
        failures += location is None
    docker_available = False
    if locations["docker"] is not None:
        docker = subprocess.run(
            ["docker", "info"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        docker_available = docker.returncode == 0
    typer.echo(f"docker-daemon: {'available' if docker_available else 'unavailable'}")
    failures += not docker_available
    private = load_private_config(ROOT)
    typer.echo(f"private-tool-config: {'configured' if private else 'not configured'}")
    if failures:
        raise typer.Exit(1)


@app.command("ci-matrix")
def ci_matrix(
    publish_only: Annotated[
        bool,
        typer.Option(
            "--publish-only/--all-ci",
            help="Require publication eligibility in addition to CI eligibility.",
        ),
    ] = True,
) -> None:
    """Emit a GitHub matrix selected entirely from public tool policy metadata."""

    catalog = _catalog()
    tools = [
        tool
        for tool in catalog.tools.tools
        if tool.ci
        and tool.distribution is Distribution.OPEN_SOURCE
        and tool.execution is ExecutionBackend.DOCKER
        and (tool.publish or not publish_only)
    ]
    typer.echo(
        json.dumps(
            {"include": [{"tool": tool.id} for tool in sorted(tools, key=lambda item: item.id)]},
            separators=(",", ":"),
        )
    )


@app.command("resolve")
def resolve(
    selection: Annotated[str, typer.Argument(help="Public tool selection, e.g. slang@latest.")],
) -> None:
    catalog = _catalog()
    tool_id, requested_ref = parse_requested_tool(selection)
    try:
        tool = catalog.tools.tool(tool_id)
    except KeyError as error:
        raise typer.BadParameter(str(error)) from error
    resolved = resolve_tool_ref(tool, requested_ref)
    path = _save_selection(resolved)
    typer.echo(json.dumps(model_to_jsonable(resolved), indent=2, sort_keys=True))
    typer.echo(f"saved {path.relative_to(ROOT)}")


@app.command("prepare")
def prepare(
    selection: Annotated[str, typer.Argument(help="Tool selection to resolve and build.")],
    push: Annotated[
        bool,
        typer.Option("--push", help="Push and record repository digest."),
    ] = False,
    repository: Annotated[
        str | None,
        typer.Option("--repository", help="Override the image repository (for GHCR)."),
    ] = None,
) -> None:
    catalog = _catalog()
    prepared = _prepare(
        catalog,
        selection,
        None,
        build=True,
        push=push,
        repository=repository,
        fake_scenario="conform",
    )
    typer.echo(
        json.dumps(
            {
                "tool": prepared.definition.id,
                "profile": prepared.profile.id,
                "selection": (
                    model_to_jsonable(prepared.selection)
                    if prepared.selection is not None
                    else None
                ),
                "image": (
                    model_to_jsonable(prepared.image) if prepared.image is not None else None
                ),
                "reported_version": prepared.reported_version,
            },
            indent=2,
            sort_keys=True,
        )
    )


@app.command("run")
def run(
    tools: Annotated[
        list[str],
        typer.Option("--tool", help="Repeatable tool selection, e.g. icarus@latest."),
    ],
    profiles: Annotated[
        list[str] | None,
        typer.Option("--profile", help="Optional tool=profile override."),
    ] = None,
    suite: Annotated[str, typer.Option("--suite", help="Suite id.")] = "smoke",
    exit_policy: Annotated[ExitPolicy, typer.Option("--exit-policy")] = ExitPolicy.INFRA_ONLY,
    build: Annotated[
        bool, typer.Option("--build/--no-build", help="Build or reuse prepared images.")
    ] = True,
    fake_scenario: Annotated[
        str,
        typer.Option("--fake-scenario", hidden=True),
    ] = "conform",
    push: Annotated[
        bool,
        typer.Option("--push", help="Push the prepared image and record its digest."),
    ] = False,
    repository: Annotated[
        str | None,
        typer.Option("--repository", help="Image repository override for a pushed run."),
    ] = None,
) -> None:
    if not tools:
        raise typer.BadParameter("at least one --tool is required")
    if push and (len(tools) != 1 or not build):
        raise typer.BadParameter("--push requires one tool and an enabled build")
    catalog = _catalog()
    overrides = _profile_overrides(profiles or [])
    prepared = tuple(
        _prepare(
            catalog,
            selection,
            overrides.get(parse_requested_tool(selection)[0]),
            build=build,
            push=push,
            repository=repository,
            fake_scenario=fake_scenario,
        )
        for selection in tools
    )
    campaign = run_campaign(catalog, prepared, suite_id=suite)
    counts: dict[str, int] = {}
    for result in campaign.results:
        counts[result.status.value] = counts.get(result.status.value, 0) + 1
        typer.echo(
            f"{result.tool_id}/{result.profile_id} {result.case_id}: "
            f"{result.status.value} ({result.reason.value})"
        )
    typer.echo(f"campaign: .svtorture/campaigns/{campaign.id}/campaign.json")
    typer.echo("summary: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    raise typer.Exit(exit_code_for_results(campaign.results, exit_policy.value))


@app.command("aggregate")
def aggregate(
    paths: Annotated[list[Path], typer.Argument(help="Campaign JSON files or directories.")],
    expected_tools: Annotated[
        list[str] | None,
        typer.Option("--expect-tool", help="Expected tool id for completeness."),
    ] = None,
) -> None:
    campaigns = tuple(load_campaign(path) for path in paths)
    aggregate_campaign = aggregate_campaigns(
        ROOT,
        campaigns,
        expected_tools=tuple(expected_tools or ()),
    )
    typer.echo(f".svtorture/campaigns/{aggregate_campaign.id}/campaign.json")


@app.command("record-missing")
def record_missing(
    tool: Annotated[str, typer.Option("--tool", help="Expected tool id.")],
    suite: Annotated[str, typer.Option("--suite", help="Suite id.")] = "all",
) -> None:
    """Record normalized pre-execution failures for one expected tool."""

    catalog = _catalog()
    campaign = create_preparation_failure_campaign(
        catalog,
        suite_id=suite,
        tool_id=tool,
    )
    typer.echo(f".svtorture/campaigns/{campaign.id}/campaign.json")


@app.command("reproduce")
def reproduce(
    campaign_path: Annotated[
        str,
        typer.Argument(help="Recorded campaign path or trusted public HTTPS URL."),
    ],
    tool: Annotated[str, typer.Option("--tool")],
    profile: Annotated[str, typer.Option("--profile")],
    case: Annotated[str, typer.Option("--case")],
) -> None:
    campaign = load_campaign_location(campaign_path)
    report = reproduce_case(ROOT, campaign, tool_id=tool, profile_id=profile, case_id=case)
    typer.echo(
        f"recorded={report.recorded.status.value}/{report.recorded.reason.value} "
        f"replayed={report.replayed.status.value}/{report.replayed.reason.value}"
    )
    if report.differences:
        for difference in report.differences:
            typer.echo(f"difference: {difference}")
        raise typer.Exit(1)
    typer.echo("reproduction matches recorded normalized judgment")


@dashboard_app.command("export")
def dashboard_export(
    campaigns: Annotated[list[Path], typer.Argument(help="Campaign JSON paths.")],
    output: Annotated[
        Path,
        typer.Option("--output", help="Dataset output path."),
    ] = ROOT / ".svtorture" / "dashboard" / "data" / "dataset.json",
    visibility: Annotated[str, typer.Option("--visibility")] = "local",
) -> None:
    catalog = _catalog()
    loaded = tuple(load_campaign(path) for path in campaigns)
    write_dataset(catalog, loaded, output, visibility=visibility)
    typer.echo(str(output))


@dashboard_app.command("serve")
def dashboard_serve(
    directory: Annotated[
        Path, typer.Option("--directory", help="Built/exported dashboard directory.")
    ] = ROOT / ".svtorture" / "site",
    port: Annotated[int, typer.Option("--port", min=1, max=65535)] = 4173,
) -> None:
    if not (directory / "index.html").exists():
        raise typer.BadParameter("dashboard directory has no index.html")
    raise typer.Exit(
        subprocess.run(
            ["python3", "-m", "http.server", str(port), "--directory", str(directory)],
            check=False,
        ).returncode
    )


@dashboard_app.command("publish-tree")
def dashboard_publish_tree(
    campaigns: Annotated[list[Path], typer.Argument(help="Trusted campaign JSON paths.")],
    pages_tree: Annotated[Path, typer.Option("--pages-tree")],
    built_site: Annotated[Path, typer.Option("--built-site")] = ROOT / "dashboard" / "dist",
) -> None:
    catalog = _catalog()
    loaded = tuple(load_campaign(path) for path in campaigns)
    publish_pages_tree(catalog, loaded, built_site, pages_tree)
    typer.echo(str(pages_tree))


def entrypoint() -> None:
    try:
        app()
    except (
        CampaignError,
        ImageError,
        PublicationError,
        ReproductionError,
        ResolutionError,
    ) as error:
        typer.echo(f"error: {error}", err=True)
        raise SystemExit(2) from None


if __name__ == "__main__":
    entrypoint()
