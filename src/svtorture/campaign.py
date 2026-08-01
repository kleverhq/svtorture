"""Campaign orchestration, immutable persistence, and integrity checks."""

from __future__ import annotations

import json
import os
import platform
import shlex
import shutil
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from typing import Any

from pydantic import ValidationError

from svtorture.adapters.registry import adapter_for
from svtorture.catalog import Catalog, LoadedCase, load_catalog, repository_identity
from svtorture.evaluator import evaluate, synthetic_result
from svtorture.executor import ExecutionError, execute_plan
from svtorture.hashing import hash_json
from svtorture.models import (
    Applicability,
    Campaign,
    CampaignTool,
    CampaignTrust,
    ExecutionPlan,
    ImageIdentity,
    ManifestHashes,
    NormalizedResult,
    ReasonCode,
    ResultStatus,
    RunnerConfig,
    ToolDefinition,
    ToolProfile,
    ToolSelection,
    model_to_jsonable,
    phase_reaches,
)
from svtorture.process import ProcessCancelled, run_process


class CampaignError(RuntimeError):
    pass


AGGREGATION_CONTRACT_VERSION = 5


@dataclass(frozen=True)
class PreparedTool:
    definition: ToolDefinition
    profile: ToolProfile
    selection: ToolSelection | None
    image: ImageIdentity | None
    reported_version: str | None
    wrapper: RunnerConfig | None = None
    fake_scenario: str = "conform"


def load_runner_config(root: Path, tool: ToolDefinition) -> RunnerConfig | None:
    if tool.runner_config is None:
        return None
    root = root.resolve()
    path = root / tool.runner_config
    try:
        path.resolve().relative_to(root)
        current = root
        for part in Path(tool.runner_config).parts:
            current /= part
            if current.is_symlink():
                raise OSError("symbolic links are not allowed")
    except (OSError, ValueError) as error:
        raise CampaignError(f"invalid runner configuration path {path}: {error}") from error
    if not path.exists():
        return None
    try:
        with path.open("rb") as stream:
            value = tomllib.load(stream)
        return RunnerConfig.model_validate(value)
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as error:
        raise CampaignError(f"invalid runner configuration {path}: {error}") from error


def wrapper_available(wrapper: RunnerConfig | None) -> bool:
    if wrapper is None:
        return False
    executable = wrapper.command[0]
    if "/" in executable:
        path = Path(executable).expanduser()
        executable_available = path.is_file() and os.access(path, os.X_OK)
    else:
        executable_available = shutil.which(executable) is not None
    return executable_available and all(
        bool(os.environ.get(name)) for name in wrapper.environment_allowlist
    )


def _campaign_trust() -> CampaignTrust:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return CampaignTrust(source="local")
    try:
        return CampaignTrust(
            source="github-actions",
            repository=os.environ.get("GITHUB_REPOSITORY"),
            workflow_run_id=os.environ.get("GITHUB_RUN_ID"),
            checkout_sha=os.environ.get("GITHUB_SHA"),
        )
    except ValidationError as error:
        raise CampaignError(f"incomplete GitHub Actions provenance: {error}") from error


def _reproduction_location(campaign_id: str, trust: CampaignTrust) -> str:
    if trust.source == "github-actions":
        assert trust.repository is not None
        tag = f"campaign-{campaign_id}"
        asset = f"svtorture-campaign-{campaign_id}.zip"
        return f"https://github.com/{trust.repository}/releases/download/{tag}/{asset}"
    return f".svtorture/campaigns/{campaign_id}/campaign.json"


def _attach_reproduction(
    results: Iterable[NormalizedResult],
    campaign_id: str,
    trust: CampaignTrust,
) -> tuple[NormalizedResult, ...]:
    location = _reproduction_location(campaign_id, trust)
    return tuple(
        result.model_copy(
            update={
                "reproduction_command": " ".join(
                    (
                        "just",
                        "reproduce",
                        shlex.quote(location),
                        shlex.quote(result.tool_id),
                        shlex.quote(result.profile_id),
                        shlex.quote(result.case_id),
                    )
                )
            }
        )
        for result in results
    )


def report_image_version(
    image: ImageIdentity, version_argv: tuple[str, ...], work_root: Path
) -> str:
    work_root.mkdir(parents=True, exist_ok=True)
    argv = (
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=16m",
        image.reference,
        *version_argv,
    )
    result = run_process(
        argv,
        cwd=work_root,
        timeout_seconds=60,
        output_bytes=16384,
    )
    if result.outcome.value != "normal-exit" or result.exit_code != 0:
        return "unavailable"
    text = (result.stdout.data + b"\n" + result.stderr.data).decode("utf-8", errors="replace")
    return _version_line(text)


def _version_line(text: str) -> str:
    return next((line.strip()[:1000] for line in text.splitlines() if line.strip()), "unavailable")


def report_wrapper_version(
    wrapper: RunnerConfig,
    tool_id: str,
    version_argv: tuple[str, ...],
    work_root: Path,
) -> str:
    """Ask a local runner to execute the adapter's version argv."""

    work_root.mkdir(parents=True, exist_ok=True)
    request_path = work_root / "version-request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "kind": "version",
                "tool": tool_id,
                "argv": list(version_argv),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
    }
    for name in wrapper.environment_allowlist:
        environment[name] = os.environ[name]
    result = run_process(
        (*wrapper.command, "--request", str(request_path)),
        cwd=work_root,
        timeout_seconds=60,
        output_bytes=16384,
        environment=environment,
    )
    if result.outcome.value != "normal-exit" or result.exit_code != 0:
        return "unavailable"
    text = (result.stdout.data + b"\n" + result.stderr.data).decode("utf-8", errors="replace")
    return _version_line(text)


def _selection_payload(
    selection_name: str,
    case_ids: Iterable[str],
    tools: Iterable[CampaignTool],
    expected_tool_ids: Iterable[str],
) -> dict[str, Any]:
    return {
        "selection_name": selection_name,
        "case_ids": list(case_ids),
        "expected_tool_ids": sorted(expected_tool_ids),
        "tools": [
            {
                "definition": item.definition.id,
                "profiles": sorted(item.profile_ids),
                "selection": (
                    model_to_jsonable(item.selection) if item.selection is not None else None
                ),
                "image": model_to_jsonable(item.image) if item.image is not None else None,
                **(
                    {"preparation_error": item.preparation_error}
                    if item.preparation_error is not None
                    else {}
                ),
            }
            for item in sorted(tools, key=lambda value: value.definition.id)
        ],
    }


def campaign_selection_hash(
    selection_name: str,
    case_ids: Iterable[str],
    tools: Iterable[CampaignTool],
    expected_tool_ids: Iterable[str],
) -> str:
    """Hash the canonical campaign selection and tool identity payload."""

    return hash_json(_selection_payload(selection_name, case_ids, tools, expected_tool_ids))


def _campaign_tools(prepared: tuple[PreparedTool, ...]) -> tuple[CampaignTool, ...]:
    grouped: dict[str, list[PreparedTool]] = {}
    for item in prepared:
        grouped.setdefault(item.definition.id, []).append(item)
    result: list[CampaignTool] = []
    for tool_id in sorted(grouped):
        items = grouped[tool_id]
        first = items[0]
        if any(
            item.selection != first.selection
            or item.image != first.image
            or item.definition != first.definition
            for item in items[1:]
        ):
            raise CampaignError(f"tool {tool_id} profiles do not share one identity")
        result.append(
            CampaignTool(
                definition=first.definition,
                selection=first.selection,
                image=first.image,
                reported_version=first.reported_version,
                profile_ids=tuple(item.profile.id for item in items),
            )
        )
    return tuple(result)


def validate_plan_for_profile(
    plan: ExecutionPlan,
    case: LoadedCase,
    tool: ToolDefinition,
    profile: ToolProfile,
    *,
    image: str | None,
    wrapper: str | None,
) -> None:
    expected_context = (
        case.definition.id,
        tool.id,
        profile.id,
        case.definition.target_phase,
        tool.execution,
    )
    actual_context = (
        plan.case_id,
        plan.tool_id,
        plan.profile_id,
        plan.target_phase,
        plan.backend,
    )
    if actual_context != expected_context:
        raise ValueError("execution plan identity does not match its case and profile")
    if (plan.image, plan.wrapper) != (image, wrapper):
        raise ValueError("execution plan backend identity does not match the prepared tool")
    if not profile.supports(plan.target_phase):
        raise ValueError("execution plan target exceeds the profile phase ceiling")
    covering = next(
        stage
        for stage in plan.stages
        if phase_reaches(stage.attempted_through_phase, plan.target_phase)
    )
    direct = covering.attempted_through_phase is plan.target_phase
    if direct != (plan.target_phase in profile.direct_phases):
        raise ValueError("execution plan contradicts the profile's direct phase metadata")


def _worker_count(requested: int, work_count: int) -> int:
    if requested < 0:
        raise CampaignError("jobs must be nonnegative")
    if work_count < 1:
        raise CampaignError("a campaign needs at least one tool/case combination")
    if requested:
        available = requested
    else:
        try:
            available = len(os.sched_getaffinity(0))
        except (AttributeError, OSError):
            available = os.cpu_count() or 1
    return min(max(1, available), work_count)


def _run_campaign_case(
    prepared_tool: PreparedTool,
    loaded: LoadedCase,
    work_root: Path,
    cancel_event: Event,
) -> NormalizedResult:
    if cancel_event.is_set():
        raise ProcessCancelled("campaign execution was cancelled")
    tool = prepared_tool.definition
    profile = prepared_tool.profile
    case = loaded.definition
    if not profile.supports(case.target_phase):
        return synthetic_result(
            loaded,
            tool.id,
            profile.id,
            ResultStatus.UNSUPPORTED_CAPABILITY,
            ReasonCode.UNSUPPORTED_PHASE,
            f"{tool.display_name}/{profile.id} cannot reach {case.target_phase.value}.",
        )
    applicability = case.revision_applicability[profile.standard_revision]
    if applicability is Applicability.NOT_APPLICABLE:
        return synthetic_result(
            loaded,
            tool.id,
            profile.id,
            ResultStatus.NOT_APPLICABLE,
            ReasonCode.NOT_APPLICABLE,
            f"The case is not applicable to {profile.standard_revision.value}.",
        )
    if applicability in {
        Applicability.NOT_ASSESSED,
        Applicability.CHANGED_EXPECTATION,
    }:
        return synthetic_result(
            loaded,
            tool.id,
            profile.id,
            ResultStatus.UNSUPPORTED_REVISION,
            ReasonCode.UNSUPPORTED_REVISION,
            (f"The 2023 source/oracle cannot be applied to {profile.standard_revision.value}."),
        )
    if tool.execution.value == "local-wrapper" and not wrapper_available(prepared_tool.wrapper):
        return synthetic_result(
            loaded,
            tool.id,
            profile.id,
            ResultStatus.SKIPPED_UNAVAILABLE,
            ReasonCode.TOOL_UNAVAILABLE,
            "The configured local runner is unavailable.",
        )
    adapter = adapter_for(
        tool.adapter,
        diagnostic_rules=tool.diagnostic_rules,
        fake_scenario=prepared_tool.fake_scenario,
    )
    image_reference = prepared_tool.image.reference if prepared_tool.image is not None else None
    wrapper_reference = (
        prepared_tool.wrapper.command[0] if prepared_tool.wrapper is not None else None
    )
    try:
        plan = adapter.build_plan(
            loaded,
            tool,
            profile,
            image=image_reference,
            wrapper=wrapper_reference,
        )
        validate_plan_for_profile(
            plan,
            loaded,
            tool,
            profile,
            image=image_reference,
            wrapper=wrapper_reference,
        )
        observations = execute_plan(
            plan,
            loaded,
            adapter,
            work_root / tool.id / profile.id / case.id,
            wrapper=prepared_tool.wrapper,
            cancel_event=cancel_event,
        )
        return evaluate(loaded, tool.id, profile.id, observations)
    except (ValueError, ValidationError, ExecutionError) as error:
        return synthetic_result(
            loaded,
            tool.id,
            profile.id,
            ResultStatus.HARNESS_ERROR,
            ReasonCode.INVALID_EXECUTION_PLAN,
            f"Invalid execution plan: {error}",
        )


def run_campaign(
    catalog: Catalog,
    prepared: tuple[PreparedTool, ...],
    *,
    suite_id: str,
    jobs: int = 1,
    progress: Callable[[int, int, str, str, str], None] | None = None,
) -> Campaign:
    if not prepared:
        raise CampaignError("a campaign needs at least one tool/profile")
    selected = catalog.selected_cases(suite_id)
    started = datetime.now(UTC)
    repository = repository_identity(catalog.root)
    campaign_tools = _campaign_tools(prepared)
    expected_tool_ids = tuple(item.definition.id for item in campaign_tools)
    selection_hash = campaign_selection_hash(
        suite_id,
        (item.definition.id for item in selected),
        campaign_tools,
        expected_tool_ids,
    )
    identity_hash = hash_json(
        {
            "started_at": started.isoformat(),
            "repository": model_to_jsonable(repository),
            "selection": selection_hash,
        }
    )
    campaign_id = f"{started:%Y%m%dT%H%M%SZ}-{identity_hash[:16]}"
    work_root = catalog.root / ".svtorture" / "work" / campaign_id
    total_cases = len(prepared) * len(selected)
    worker_count = _worker_count(jobs, total_cases)
    work_items = [
        (
            tool_index * len(selected) + case_index,
            prepared_tool,
            loaded,
        )
        for case_index, loaded in enumerate(selected)
        for tool_index, prepared_tool in enumerate(prepared)
    ]
    cancel_event = Event()

    def run_one(
        item: tuple[int, PreparedTool, LoadedCase],
    ) -> tuple[int, NormalizedResult]:
        result_index, prepared_tool, loaded = item
        return (
            result_index,
            _run_campaign_case(prepared_tool, loaded, work_root, cancel_event),
        )

    executor = ThreadPoolExecutor(max_workers=worker_count)
    futures: list[Future[tuple[int, NormalizedResult]]] = []
    indexed_results: list[tuple[int, NormalizedResult]] = []
    try:
        futures = [executor.submit(run_one, item) for item in work_items]
        for current, future in enumerate(as_completed(futures), start=1):
            result_index, result = future.result()
            indexed_results.append((result_index, result))
            if progress is not None:
                progress(current, total_cases, result.tool_id, result.profile_id, result.case_id)
    except BaseException:
        cancel_event.set()
        for future in futures:
            future.cancel()
        executor.shutdown(cancel_futures=True)
        raise
    else:
        executor.shutdown()
    results = [result for _, result in sorted(indexed_results)]
    finished = datetime.now(UTC)
    case_hash = catalog.case_manifest_hash(selected)
    hashes = ManifestHashes(
        requirements=catalog.requirement_manifest_hash(),
        cases=case_hash,
        selection=selection_hash,
    )
    trust = _campaign_trust()
    recorded_results = _attach_reproduction(results, campaign_id, trust)
    complete = not any(
        result.status in {ResultStatus.HARNESS_ERROR, ResultStatus.SKIPPED_UNAVAILABLE}
        for result in recorded_results
    )
    campaign = Campaign(
        schema_version=5,
        id=campaign_id,
        started_at=started,
        finished_at=finished,
        repository=repository,
        platform=f"{platform.system()} {platform.machine()}",
        selection_name=suite_id,
        case_ids=tuple(item.definition.id for item in selected),
        cases=catalog.case_identities(selected),
        tools=campaign_tools,
        expected_tool_ids=expected_tool_ids,
        missing_tool_ids=(),
        hashes=hashes,
        corpus_metrics=catalog.corpus_metrics(),
        results=recorded_results,
        complete=complete,
        trust=trust,
    )
    save_campaign(catalog.root, campaign)
    return campaign


def save_campaign(root: Path, campaign: Campaign) -> Path:
    directory = root / ".svtorture" / "campaigns" / campaign.id
    path = directory / "campaign.json"
    serialized = json.dumps(model_to_jsonable(campaign), indent=2, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != serialized:
            raise CampaignError(f"immutable campaign {campaign.id} already differs")
        return path
    directory.mkdir(parents=True, exist_ok=False)
    path.write_text(serialized, encoding="utf-8")
    return path


def load_campaign(path: Path) -> Campaign:
    if path.is_dir():
        path = path / "campaign.json"
    try:
        campaign = Campaign.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise CampaignError(f"invalid campaign {path}: {error}") from error
    _verify_loaded_campaign(campaign)
    return campaign


def load_campaign_location(location: str) -> Campaign:
    """Load a local campaign or a bounded HTTPS public-history document."""

    parsed = urllib.parse.urlparse(location)
    if not parsed.scheme:
        return load_campaign(Path(location))
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise CampaignError("remote campaigns require a credential-free HTTPS URL")
    request = urllib.request.Request(
        location,
        headers={"User-Agent": "svtorture/0.1 campaign-reproduction"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            final_url = urllib.parse.urlparse(response.geturl())
            if final_url.scheme != "https":
                raise CampaignError("remote campaign redirected outside HTTPS")
            declared_size = response.headers.get("Content-Length")
            maximum = 16 * 1024 * 1024
            if declared_size is not None and int(declared_size) > maximum:
                raise CampaignError("remote campaign exceeds the 16 MiB safety limit")
            payload = response.read(maximum + 1)
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise CampaignError(f"cannot download remote campaign: {error}") from error
    if len(payload) > maximum:
        raise CampaignError("remote campaign exceeds the 16 MiB safety limit")
    try:
        campaign = Campaign.model_validate_json(payload)
    except ValidationError as error:
        raise CampaignError(f"invalid remote campaign: {error}") from error
    _verify_loaded_campaign(campaign)
    return campaign


def _verify_loaded_campaign(campaign: Campaign) -> None:
    identity_hash = hash_json(
        [
            {"id": item.id, "content_sha256": item.content_sha256}
            for item in sorted(campaign.cases, key=lambda item: item.id)
        ]
    )
    if identity_hash != campaign.hashes.cases:
        raise CampaignError("campaign case manifest hash mismatch")
    selection_hash = campaign_selection_hash(
        campaign.selection_name,
        campaign.case_ids,
        campaign.tools,
        campaign.expected_tool_ids,
    )
    if selection_hash != campaign.hashes.selection:
        raise CampaignError("campaign selection manifest hash mismatch")


def verify_result_against_case(
    loaded: LoadedCase,
    campaign_tool: CampaignTool,
    result: NormalizedResult,
) -> None:
    """Confirm one recorded result against its case, tool policy, plan, and oracle."""

    requirement_id = loaded.definition.primary_requirement
    if result.requirement_id != requirement_id:
        raise CampaignError(f"campaign result {result.case_id} has a wrong requirement")
    if result.evidence != loaded.definition.evidence:
        raise CampaignError(f"campaign result {result.case_id} has a wrong evidence level")
    if result.target_phase is not loaded.definition.target_phase:
        raise CampaignError(f"campaign result {result.case_id} has a wrong target phase")
    profile = campaign_tool.definition.profile(result.profile_id)
    case = loaded.definition
    structural_disposition: tuple[ResultStatus, ReasonCode] | None = None
    if not profile.supports(case.target_phase):
        structural_disposition = (
            ResultStatus.UNSUPPORTED_CAPABILITY,
            ReasonCode.UNSUPPORTED_PHASE,
        )
    else:
        applicability = case.revision_applicability[profile.standard_revision]
        if applicability is Applicability.NOT_APPLICABLE:
            structural_disposition = (
                ResultStatus.NOT_APPLICABLE,
                ReasonCode.NOT_APPLICABLE,
            )
        elif applicability in {
            Applicability.NOT_ASSESSED,
            Applicability.CHANGED_EXPECTATION,
        }:
            structural_disposition = (
                ResultStatus.UNSUPPORTED_REVISION,
                ReasonCode.UNSUPPORTED_REVISION,
            )
        elif campaign_tool.preparation_error is not None:
            structural_disposition = (
                ResultStatus.HARNESS_ERROR,
                ReasonCode.TOOL_PREPARATION_FAILURE,
            )
    if structural_disposition is not None:
        if result.observations or (result.status, result.reason) != structural_disposition:
            raise CampaignError(
                f"campaign structural result is invalid for "
                f"{result.tool_id}/{result.profile_id}/{result.case_id}"
            )
        return

    if not result.observations:
        unavailable_wrapper = (
            campaign_tool.definition.execution.value == "local-wrapper"
            and result.status is ResultStatus.SKIPPED_UNAVAILABLE
            and result.reason is ReasonCode.TOOL_UNAVAILABLE
        )
        if unavailable_wrapper:
            return
        raise CampaignError(f"campaign result {result.case_id} lacks executable observations")

    adapter = adapter_for(
        campaign_tool.definition.adapter,
        diagnostic_rules=campaign_tool.definition.diagnostic_rules,
    )
    image_reference = campaign_tool.image.reference if campaign_tool.image is not None else None
    wrapper_reference = (
        "$SVTORTURE_PRIVATE_WRAPPER"
        if campaign_tool.definition.execution.value == "local-wrapper"
        else None
    )
    try:
        plan = adapter.build_plan(
            loaded,
            campaign_tool.definition,
            profile,
            image=image_reference,
            wrapper=wrapper_reference,
        )
        validate_plan_for_profile(
            plan,
            loaded,
            campaign_tool.definition,
            profile,
            image=image_reference,
            wrapper=wrapper_reference,
        )
    except (ValueError, ValidationError) as error:
        raise CampaignError(
            f"campaign execution plan is invalid for "
            f"{result.tool_id}/{result.profile_id}/{result.case_id}: {error}"
        ) from error
    expected_provenance = tuple(
        (stage.id, stage.kind, stage.attempted_through_phase) for stage in plan.stages
    )
    recorded_provenance = tuple(
        (item.stage_id, item.kind, item.attempted_through_phase) for item in result.observations
    )
    if recorded_provenance != expected_provenance[: len(recorded_provenance)]:
        raise CampaignError(
            f"campaign phase provenance does not match its execution plan for "
            f"{result.tool_id}/{result.profile_id}/{result.case_id}"
        )

    reevaluated = evaluate(
        loaded,
        result.tool_id,
        result.profile_id,
        result.observations,
    )
    recorded = (
        result.status,
        result.reason,
        result.target_phase,
        result.evidence_mode,
    )
    expected = (
        reevaluated.status,
        reevaluated.reason,
        reevaluated.target_phase,
        reevaluated.evidence_mode,
    )
    if recorded != expected:
        raise CampaignError(
            f"campaign judgment does not match observations for "
            f"{result.tool_id}/{result.profile_id}/{result.case_id}"
        )


def verify_campaign_against_catalog(catalog: Catalog, campaign: Campaign) -> None:
    missing = set(campaign.case_ids) - set(catalog.cases)
    if missing:
        raise CampaignError(f"campaign cases are absent: {', '.join(sorted(missing))}")
    selected = tuple(catalog.cases[item] for item in campaign.case_ids)
    if catalog.case_manifest_hash(selected) != campaign.hashes.cases:
        raise CampaignError("current case content does not match the campaign")
    if catalog.requirement_manifest_hash() != campaign.hashes.requirements:
        raise CampaignError("current requirement inventory does not match the campaign")
    if catalog.corpus_metrics() != campaign.corpus_metrics:
        raise CampaignError("current corpus metrics do not match the campaign")
    for expected_tool_id in campaign.expected_tool_ids:
        try:
            catalog.tools.tool(expected_tool_id)
        except KeyError as error:
            raise CampaignError(f"campaign expects unknown tool {expected_tool_id!r}") from error
    for campaign_tool in campaign.tools:
        try:
            registered = catalog.tools.tool(campaign_tool.definition.id)
        except KeyError as error:
            raise CampaignError(
                f"campaign contains unknown tool {campaign_tool.definition.id!r}"
            ) from error
        if campaign_tool.definition != registered:
            raise CampaignError(
                f"campaign tool definition changed for {campaign_tool.definition.id}"
            )
    campaign_tools = {tool.definition.id: tool for tool in campaign.tools}
    for result in campaign.results:
        verify_result_against_case(
            catalog.cases[result.case_id],
            campaign_tools[result.tool_id],
            result,
        )


def create_missing_campaign(
    catalog: Catalog,
    *,
    suite_id: str,
    expected_tool_ids: tuple[str, ...],
) -> Campaign:
    """Persist an honest campaign when collection failed before a tool identity existed."""

    if not expected_tool_ids:
        raise CampaignError("a missing campaign needs at least one expected tool")
    for tool_id in expected_tool_ids:
        try:
            catalog.tools.tool(tool_id)
        except KeyError as error:
            raise CampaignError(f"unknown expected tool {tool_id!r}") from error
    selected = catalog.selected_cases(suite_id)
    now = datetime.now(UTC)
    repository = repository_identity(catalog.root)
    expected = tuple(sorted(set(expected_tool_ids)))
    selection_hash = campaign_selection_hash(
        suite_id,
        (item.definition.id for item in selected),
        (),
        expected,
    )
    identity_hash = hash_json(
        {
            "started_at": now.isoformat(),
            "repository": model_to_jsonable(repository),
            "selection": selection_hash,
            "missing": list(expected),
        }
    )
    campaign = Campaign(
        schema_version=5,
        id=f"{now:%Y%m%dT%H%M%SZ}-missing-{identity_hash[:12]}",
        started_at=now,
        finished_at=now,
        repository=repository,
        platform=f"{platform.system()} {platform.machine()}",
        selection_name=suite_id,
        case_ids=tuple(item.definition.id for item in selected),
        cases=catalog.case_identities(selected),
        tools=(),
        expected_tool_ids=expected,
        missing_tool_ids=expected,
        hashes=ManifestHashes(
            requirements=catalog.requirement_manifest_hash(),
            cases=catalog.case_manifest_hash(selected),
            selection=selection_hash,
        ),
        corpus_metrics=catalog.corpus_metrics(),
        results=(),
        complete=False,
        trust=_campaign_trust(),
    )
    save_campaign(catalog.root, campaign)
    return campaign


def create_preparation_failure_campaign(
    catalog: Catalog,
    *,
    suite_id: str,
    tool_id: str,
) -> Campaign:
    """Record a full result grid when tool preparation failed before execution."""

    try:
        tool = catalog.tools.tool(tool_id)
    except KeyError as error:
        raise CampaignError(f"unknown expected tool {tool_id!r}") from error
    profile = tool.headline_profile
    selected = catalog.selected_cases(suite_id)
    now = datetime.now(UTC)
    repository = repository_identity(catalog.root)
    preparation_error = "Collection failed before an immutable tool identity was prepared."
    campaign_tool = CampaignTool(
        definition=tool,
        selection=None,
        image=None,
        reported_version=None,
        profile_ids=(profile.id,),
        preparation_error=preparation_error,
    )
    results: list[NormalizedResult] = []
    for loaded in selected:
        case = loaded.definition
        if not profile.supports(case.target_phase):
            results.append(
                synthetic_result(
                    loaded,
                    tool.id,
                    profile.id,
                    ResultStatus.UNSUPPORTED_CAPABILITY,
                    ReasonCode.UNSUPPORTED_PHASE,
                    (f"{tool.display_name}/{profile.id} cannot reach {case.target_phase.value}."),
                )
            )
            continue
        applicability = case.revision_applicability[profile.standard_revision]
        if applicability is Applicability.NOT_APPLICABLE:
            results.append(
                synthetic_result(
                    loaded,
                    tool.id,
                    profile.id,
                    ResultStatus.NOT_APPLICABLE,
                    ReasonCode.NOT_APPLICABLE,
                    f"The case is not applicable to {profile.standard_revision.value}.",
                )
            )
            continue
        if applicability in {
            Applicability.NOT_ASSESSED,
            Applicability.CHANGED_EXPECTATION,
        }:
            results.append(
                synthetic_result(
                    loaded,
                    tool.id,
                    profile.id,
                    ResultStatus.UNSUPPORTED_REVISION,
                    ReasonCode.UNSUPPORTED_REVISION,
                    (
                        "The 2023 source/oracle cannot be applied to "
                        f"{profile.standard_revision.value}."
                    ),
                )
            )
            continue
        results.append(
            synthetic_result(
                loaded,
                tool.id,
                profile.id,
                ResultStatus.HARNESS_ERROR,
                ReasonCode.TOOL_PREPARATION_FAILURE,
                preparation_error,
            )
        )
    expected = (tool.id,)
    tools = (campaign_tool,)
    selection_hash = campaign_selection_hash(
        suite_id,
        (item.definition.id for item in selected),
        tools,
        expected,
    )
    identity_hash = hash_json(
        {
            "started_at": now.isoformat(),
            "repository": model_to_jsonable(repository),
            "selection": selection_hash,
            "preparation_failure": tool.id,
        }
    )
    campaign = Campaign(
        schema_version=5,
        id=f"{now:%Y%m%dT%H%M%SZ}-preparation-{identity_hash[:12]}",
        started_at=now,
        finished_at=now,
        repository=repository,
        platform=f"{platform.system()} {platform.machine()}",
        selection_name=suite_id,
        case_ids=tuple(item.definition.id for item in selected),
        cases=catalog.case_identities(selected),
        tools=tools,
        expected_tool_ids=expected,
        missing_tool_ids=(),
        hashes=ManifestHashes(
            requirements=catalog.requirement_manifest_hash(),
            cases=catalog.case_manifest_hash(selected),
            selection=selection_hash,
        ),
        corpus_metrics=catalog.corpus_metrics(),
        results=tuple(results),
        complete=False,
        trust=_campaign_trust(),
    )
    save_campaign(catalog.root, campaign)
    return campaign


def aggregate_campaigns(
    root: Path,
    campaigns: tuple[Campaign, ...],
    *,
    expected_tools: tuple[str, ...] = (),
) -> Campaign:
    if not campaigns:
        raise CampaignError("no campaigns to aggregate")
    catalog = load_catalog(root)
    for campaign in campaigns:
        verify_campaign_against_catalog(catalog, campaign)
    first = campaigns[0]
    for campaign in campaigns[1:]:
        if (
            campaign.repository != first.repository
            or campaign.selection_name != first.selection_name
            or campaign.case_ids != first.case_ids
            or campaign.cases != first.cases
            or campaign.hashes.requirements != first.hashes.requirements
            or campaign.hashes.cases != first.hashes.cases
            or campaign.corpus_metrics != first.corpus_metrics
        ):
            raise CampaignError("campaigns do not share one corpus snapshot")
    tools: list[CampaignTool] = []
    results: list[NormalizedResult] = []
    seen: set[str] = set()
    declared_expected = set(expected_tools)
    for campaign in campaigns:
        declared_expected.update(campaign.expected_tool_ids)
        retained_tool_ids: set[str] = set()
        for tool in campaign.tools:
            if tool.preparation_error is not None:
                continue
            if tool.definition.id in seen:
                raise CampaignError(f"duplicate aggregate tool {tool.definition.id}")
            seen.add(tool.definition.id)
            retained_tool_ids.add(tool.definition.id)
            tools.append(tool)
        results.extend(result for result in campaign.results if result.tool_id in retained_tool_ids)
    expected = tuple(sorted(seen | declared_expected))
    missing = tuple(sorted(set(expected) - seen))
    platforms = {campaign.platform for campaign in campaigns}
    aggregate_platform = (
        next(iter(platforms))
        if len(platforms) == 1
        else "Mixed aggregate: " + ", ".join(sorted(platforms))
    )
    identity_hash = hash_json(
        {
            "aggregation_contract": AGGREGATION_CONTRACT_VERSION,
            "campaigns": sorted(item.id for item in campaigns),
            "expected_tools": list(expected),
            "platform": aggregate_platform,
        }
    )
    finished = max(item.finished_at for item in campaigns)
    if all(item.trust.source == "github-actions" for item in campaigns):
        repository_names = {item.trust.repository for item in campaigns}
        run_ids = {item.trust.workflow_run_id for item in campaigns}
        checkout_shas = {item.trust.checkout_sha for item in campaigns}
        if (
            len(repository_names) != 1
            or len(run_ids) != 1
            or len(checkout_shas) != 1
            or None in repository_names | run_ids | checkout_shas
        ):
            raise CampaignError("GitHub Actions campaigns do not share one trust identity")
        trust = CampaignTrust(
            source="github-actions",
            repository=next(iter(repository_names)),
            workflow_run_id=next(iter(run_ids)),
            checkout_sha=next(iter(checkout_shas)),
        )
    else:
        trust = CampaignTrust(source="local")
    aggregate_tools = tuple(sorted(tools, key=lambda item: item.definition.id))
    selection_hash = campaign_selection_hash(
        first.selection_name,
        first.case_ids,
        aggregate_tools,
        expected,
    )
    aggregate_id = f"{finished:%Y%m%dT%H%M%SZ}-aggregate-{identity_hash[:12]}"
    aggregate_results = _attach_reproduction(results, aggregate_id, trust)
    aggregate = Campaign(
        schema_version=5,
        id=aggregate_id,
        started_at=min(item.started_at for item in campaigns),
        finished_at=finished,
        repository=first.repository,
        platform=aggregate_platform,
        selection_name=first.selection_name,
        case_ids=first.case_ids,
        cases=first.cases,
        tools=aggregate_tools,
        expected_tool_ids=expected,
        missing_tool_ids=missing,
        hashes=ManifestHashes(
            requirements=first.hashes.requirements,
            cases=first.hashes.cases,
            selection=selection_hash,
        ),
        corpus_metrics=first.corpus_metrics,
        results=aggregate_results,
        complete=not missing
        and not any(
            result.status in {ResultStatus.HARNESS_ERROR, ResultStatus.SKIPPED_UNAVAILABLE}
            for result in aggregate_results
        ),
        trust=trust,
    )
    save_campaign(root, aggregate)
    return aggregate
