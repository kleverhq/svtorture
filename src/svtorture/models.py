"""Strict, versioned public data models used throughout SVTORTURE."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
REQUIREMENT_ID_RE = re.compile(r"^SV-(?:2012|2017|2023)-(?:[0-9]{2}|[A-Q])-[A-Z0-9-]+$")
TOP_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HEX_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
CAMPAIGN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[A-Za-z0-9](?:[A-Za-z0-9-]{0,126}[A-Za-z0-9])?$")
STANDARD_PART_PATTERN = r"^(?:[1-9]|[1-3][0-9]|4[01]|[A-Q])$"
STANDARD_LOCATION_PATTERN = r"^(?:(?:[1-9]|[1-3][0-9]|4[01])(?:\.[0-9]+)*|[A-Q](?:\.[0-9]+)*)$"
STANDARD_ANCHOR_PATTERN = (
    r"^\[2023:(?:(?:[1-9]|[1-3][0-9]|4[01])(?:\.[0-9]+)*|"
    r"[A-Q](?:\.[0-9]+)*):[A-Z][A-Z0-9]*(?:[-.][A-Z0-9]+)*:"
    r"p[0-9]{3,4}(?:-[0-9]{3,4})?\]$"
)
SafeText = Annotated[str, Field(min_length=1, max_length=4096)]
StandardPart = Annotated[str, Field(pattern=STANDARD_PART_PATTERN)]
StandardLocation = Annotated[str, Field(pattern=STANDARD_LOCATION_PATTERN)]
StandardAnchor = Annotated[str, Field(pattern=STANDARD_ANCHOR_PATTERN)]
MetadataSchemaVersion = Annotated[int, Field(strict=True, ge=1, le=1)]
ContractSchemaVersion = Annotated[int, Field(strict=True, ge=2, le=2)]
CampaignSchemaVersion = Annotated[int, Field(strict=True, ge=4, le=4)]
RequirementSchemaVersion = Annotated[int, Field(strict=True, ge=3, le=3)]


class StrictModel(BaseModel):
    """Base class that rejects unknown fields and accidental mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


class StandardRevision(StrEnum):
    IEEE_1800_2012 = "1800-2012"
    IEEE_1800_2017 = "1800-2017"
    IEEE_1800_2023 = "1800-2023"


class Applicability(StrEnum):
    APPLICABLE = "applicable"
    SAME_RULE_DIFFERENT_CLAUSE = "same-rule-different-clause"
    CHANGED_EXPECTATION = "changed-expectation"
    NOT_APPLICABLE = "not-applicable"
    NOT_ASSESSED = "not-assessed"


class Phase(StrEnum):
    PREPROCESS = "preprocess"
    PARSE = "parse"
    ELABORATE = "elaborate"
    SIMULATE = "simulate"


PHASE_ORDER = (
    Phase.PREPROCESS,
    Phase.PARSE,
    Phase.ELABORATE,
    Phase.SIMULATE,
)


def phase_reaches(attempted_through: Phase, target: Phase) -> bool:
    """Return whether one invocation can attempt the target pipeline phase."""

    return PHASE_ORDER.index(attempted_through) >= PHASE_ORDER.index(target)


class EvidenceMode(StrEnum):
    DIRECT = "direct"
    CUMULATIVE = "cumulative"
    NOT_OBSERVED = "not-observed"


class Expectation(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    DIAGNOSTIC = "diagnostic"


class EvidenceLevel(StrEnum):
    MANDATORY = "mandatory"
    EXPLORATORY = "exploratory"


class OracleKind(StrEnum):
    PHASE_EXIT = "phase-exit"
    RUNTIME_PASS_MARKER = "runtime-pass-marker"
    DIAGNOSTIC_AT_ANCHOR = "diagnostic-at-anchor"


class Distribution(StrEnum):
    OPEN_SOURCE = "open-source"
    COMMERCIAL = "commercial"
    INTERNAL = "internal"


class ExecutionBackend(StrEnum):
    DOCKER = "docker"
    LOCAL_WRAPPER = "local-wrapper"


class StageKind(StrEnum):
    COMPILE = "compile"
    RUN = "run"


class RawOutcome(StrEnum):
    NORMAL_EXIT = "normal-exit"
    SIGNAL = "signal"
    TIMEOUT = "timeout"
    LAUNCH_FAILURE = "launch-failure"
    CONTAINER_FAILURE = "container-failure"
    BACKEND_UNAVAILABLE = "backend-unavailable"


class ResultStatus(StrEnum):
    CONFORMING = "conforming"
    NONCONFORMING = "nonconforming"
    INCONCLUSIVE = "inconclusive"
    UNSUPPORTED_CAPABILITY = "unsupported-capability"
    UNSUPPORTED_REVISION = "unsupported-revision"
    NOT_APPLICABLE = "not-applicable"
    SKIPPED_UNAVAILABLE = "skipped-unavailable"
    HARNESS_ERROR = "harness-error"


class ReasonCode(StrEnum):
    EXPECTATION_MET = "expectation-met"
    UNEXPECTED_ACCEPT = "unexpected-accept"
    UNEXPECTED_REJECT = "unexpected-reject"
    MISSING_DIAGNOSTIC = "missing-diagnostic"
    OFF_TARGET_DIAGNOSTIC = "off-target-diagnostic"
    MISSING_PASS_MARKER = "missing-pass-marker"
    MULTIPLE_PASS_MARKERS = "multiple-pass-markers"
    PASS_MARKER_NONZERO = "pass-marker-with-nonzero-status"
    WRONG_RUNTIME_RESULT = "wrong-runtime-result"
    TIMEOUT = "timeout"
    CRASH = "crash"
    INTERNAL_ERROR = "internal-error"
    CONTAINER_FAILURE = "container-failure"
    LAUNCH_FAILURE = "launch-failure"
    MISSING_ARTIFACT = "missing-artifact"
    INVALID_EXECUTION_PLAN = "invalid-execution-plan"
    UNSUPPORTED_PHASE = "unsupported-phase"
    UNSUPPORTED_REVISION = "unsupported-revision"
    NOT_APPLICABLE = "not-applicable"
    TOOL_UNAVAILABLE = "tool-unavailable"
    MANIFEST_MISMATCH = "manifest-mismatch"
    OUTPUT_TRUNCATED = "output-truncated"
    TARGET_PHASE_UNPROVEN = "target-phase-unproven"
    TOOL_PREPARATION_FAILURE = "tool-preparation-failure"


class ExitPolicy(StrEnum):
    INFRA_ONLY = "infra-only"
    STRICT = "strict"
    ALWAYS_ZERO = "always-zero"


class RevisionRule(StrictModel):
    status: Applicability
    clause: StandardLocation | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def clause_is_complete(self) -> Self:
        if (
            self.status
            in {
                Applicability.APPLICABLE,
                Applicability.SAME_RULE_DIFFERENT_CLAUSE,
                Applicability.CHANGED_EXPECTATION,
            }
            and self.clause is None
        ):
            raise ValueError("applicable or changed revision rules require a clause")
        return self


def _check_revision_keys(value: dict[StandardRevision, Any]) -> dict[StandardRevision, Any]:
    expected = set(StandardRevision)
    if set(value) != expected:
        missing = sorted(item.value for item in expected - set(value))
        extra = sorted(str(item) for item in set(value) - expected)
        raise ValueError(
            f"revision applicability must be complete; missing={missing}, extra={extra}"
        )
    return value


class Requirement(StrictModel):
    id: str
    standard_revision: StandardRevision
    part: StandardPart
    clause: StandardLocation
    anchors: tuple[StandardAnchor, ...] = Field(
        min_length=1, json_schema_extra={"uniqueItems": True}
    )
    summary: SafeText
    related_clauses: tuple[StandardLocation, ...] = ()
    tags: tuple[str, ...] = ()
    revision_applicability: dict[StandardRevision, RevisionRule]

    @field_validator("id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        if not REQUIREMENT_ID_RE.fullmatch(value):
            raise ValueError("invalid stable requirement id")
        return value

    @field_validator("revision_applicability")
    @classmethod
    def complete_revisions(
        cls, value: dict[StandardRevision, RevisionRule]
    ) -> dict[StandardRevision, RevisionRule]:
        return _check_revision_keys(value)

    @field_validator("anchors")
    @classmethod
    def unique_anchors(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate requirement anchors")
        return value

    @field_validator("tags")
    @classmethod
    def valid_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate tags")
        if any(ID_RE.fullmatch(tag) is None for tag in value):
            raise ValueError("tags must use lowercase kebab-case")
        if tuple(sorted(value)) != value:
            raise ValueError("tags must be sorted")
        return value

    @model_validator(mode="after")
    def active_revision_matches(self) -> Self:
        if self.standard_revision is not StandardRevision.IEEE_1800_2023:
            raise ValueError("the active requirement authority must be IEEE 1800-2023")
        active = self.revision_applicability[self.standard_revision]
        if active.status is not Applicability.APPLICABLE or active.clause != self.clause:
            raise ValueError("active revision must be applicable at the declared clause")
        if self.anchors[0].split(":", 2)[1] != self.clause:
            raise ValueError("first requirement anchor must cite the declared clause")
        if self.clause.split(".", 1)[0] != self.part:
            raise ValueError("requirement clause does not match part field")
        id_part = f"{int(self.part):02d}" if self.part.isdigit() else self.part
        if not self.id.startswith(f"SV-2023-{id_part}-"):
            raise ValueError("requirement id part does not match part field")
        return self


class RequirementInventory(StrictModel):
    schema_version: RequirementSchemaVersion
    authority: StandardRevision
    requirements: tuple[Requirement, ...]

    @model_validator(mode="after")
    def unique_and_active(self) -> Self:
        if self.authority is not StandardRevision.IEEE_1800_2023:
            raise ValueError("inventory authority must be IEEE 1800-2023")
        ids = [requirement.id for requirement in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate requirement ids")
        return self


def standard_part_sort_key(part: str) -> tuple[int, int]:
    """Return the IEEE order for a numeric chapter or alphabetic annex."""

    return (0, int(part)) if part.isdigit() else (1, ord(part))


def standard_location_sort_key(location: str) -> tuple[int, int, tuple[int, ...]]:
    """Return the IEEE part and subclause order for a standard location."""

    part, *subclauses = location.split(".")
    return (*standard_part_sort_key(part), tuple(int(value) for value in subclauses))


class StandardsIndex(StrictModel):
    schema_version: RequirementSchemaVersion
    authority: StandardRevision
    parts: tuple[StandardPart, ...]

    @model_validator(mode="after")
    def valid_index(self) -> Self:
        if self.authority is not StandardRevision.IEEE_1800_2023:
            raise ValueError("standards authority must be IEEE 1800-2023")
        if (
            not self.parts
            or len(self.parts) != len(set(self.parts))
            or tuple(sorted(self.parts, key=standard_part_sort_key)) != self.parts
        ):
            raise ValueError("standards parts must be unique and canonically ordered")
        return self


class RequirementPart(StrictModel):
    schema_version: RequirementSchemaVersion
    part: StandardPart
    requirements: tuple[Requirement, ...]

    @model_validator(mode="after")
    def valid_part(self) -> Self:
        if not self.requirements:
            raise ValueError("requirement part must not be empty")
        ids = [requirement.id for requirement in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate requirement ids in part")
        if any(requirement.part != self.part for requirement in self.requirements):
            raise ValueError("requirement part does not match part file")
        if ids != sorted(ids):
            raise ValueError("requirements must be sorted by id")
        return self


class TagDefinition(StrictModel):
    id: str
    description: SafeText

    @field_validator("id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        if ID_RE.fullmatch(value) is None:
            raise ValueError("tag id must use lowercase kebab-case")
        return value


class TagRegistry(StrictModel):
    schema_version: MetadataSchemaVersion
    tags: tuple[TagDefinition, ...]

    @model_validator(mode="after")
    def unique_and_sorted(self) -> Self:
        ids = [tag.id for tag in self.tags]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("tag ids must be nonempty and unique")
        if ids != sorted(ids):
            raise ValueError("tag registry must be sorted by id")
        return self


class ResourceLimits(StrictModel):
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    output_bytes: int = Field(default=65536, ge=1024, le=1_048_576)
    memory_mb: int = Field(default=2048, ge=128, le=32768)
    pids: int = Field(default=256, ge=16, le=4096)


class Oracle(StrictModel):
    kind: OracleKind
    marker: str | None = Field(default=None, max_length=256)
    anchor: str | None = Field(default=None, max_length=256)


def safe_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or "\\" in value
        or "\x00" in value
    ):
        raise ValueError(f"unsafe relative path {value!r}")
    return value


class CaseDefinition(StrictModel):
    schema_version: MetadataSchemaVersion
    id: str
    title: SafeText
    description: SafeText
    primary_requirement: str
    related_requirements: tuple[str, ...] = ()
    standard_revision: StandardRevision
    revision_applicability: dict[StandardRevision, Applicability]
    target_phase: Phase
    expectation: Expectation
    evidence: EvidenceLevel
    sources: tuple[str, ...]
    top: str | None = None
    defines: tuple[str, ...] = ()
    include_dirs: tuple[str, ...] = ()
    runtime_args: tuple[str, ...] = ()
    limits: ResourceLimits = ResourceLimits()
    oracle: Oracle
    tags: tuple[str, ...] = ()

    @field_validator("id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        if ID_RE.fullmatch(value) is None:
            raise ValueError("case id must use lowercase kebab-case")
        return value

    @field_validator("primary_requirement")
    @classmethod
    def valid_primary_requirement(cls, value: str) -> str:
        if REQUIREMENT_ID_RE.fullmatch(value) is None:
            raise ValueError("invalid primary requirement id")
        return value

    @field_validator("related_requirements")
    @classmethod
    def valid_related_requirements(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate related requirement ids")
        if any(REQUIREMENT_ID_RE.fullmatch(item) is None for item in value):
            raise ValueError("invalid related requirement id")
        return value

    @field_validator("revision_applicability")
    @classmethod
    def complete_revisions(
        cls, value: dict[StandardRevision, Applicability]
    ) -> dict[StandardRevision, Applicability]:
        return _check_revision_keys(value)

    @field_validator("sources")
    @classmethod
    def valid_sources(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("sources must be nonempty and unique")
        safe = tuple(safe_relative_path(item) for item in value)
        basenames = [PurePosixPath(item).name for item in safe]
        if len(basenames) != len(set(basenames)):
            raise ValueError("source basenames must be unique for diagnostic identity")
        return safe

    @field_validator("include_dirs")
    @classmethod
    def valid_include_dirs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate include directories")
        return tuple(safe_relative_path(item) for item in value)

    @field_validator("top")
    @classmethod
    def valid_top(cls, value: str | None) -> str | None:
        if value is not None and TOP_RE.fullmatch(value) is None:
            raise ValueError("invalid top identifier")
        return value

    @field_validator("defines")
    @classmethod
    def valid_defines(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for define in value:
            name = define.split("=", 1)[0]
            if re.fullmatch(r"^[A-Za-z_][A-Za-z0-9_$]*$", name) is None:
                raise ValueError(f"invalid define {define!r}")
            if "\n" in define or "\x00" in define:
                raise ValueError("unsafe define")
        return value

    @field_validator("tags")
    @classmethod
    def valid_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate case tags")
        if any(ID_RE.fullmatch(tag) is None for tag in value):
            raise ValueError("case tags must use lowercase kebab-case")
        if tuple(sorted(value)) != value:
            raise ValueError("case tags must be sorted")
        return value

    @model_validator(mode="after")
    def valid_oracle_combination(self) -> Self:
        if self.standard_revision is not StandardRevision.IEEE_1800_2023:
            raise ValueError("case authority must be IEEE 1800-2023")
        if self.revision_applicability[self.standard_revision] is not Applicability.APPLICABLE:
            raise ValueError("active case revision must be applicable")
        if self.primary_requirement in self.related_requirements:
            raise ValueError("primary requirement cannot also be related")
        expected_marker = f"SVTORTURE_PASS:{self.id}"
        expected_anchor = f"SVTORTURE_DIAG_ANCHOR:{self.id}"
        if self.target_phase is Phase.SIMULATE and self.expectation is Expectation.ACCEPT:
            if self.oracle.kind is not OracleKind.RUNTIME_PASS_MARKER:
                raise ValueError("simulation acceptance requires a runtime pass marker oracle")
            if self.oracle.marker != expected_marker or self.oracle.anchor is not None:
                raise ValueError("runtime marker must exactly match the case id")
        elif self.expectation in {Expectation.REJECT, Expectation.DIAGNOSTIC}:
            if self.oracle.kind is not OracleKind.DIAGNOSTIC_AT_ANCHOR:
                raise ValueError("negative and diagnostic cases require an anchor oracle")
            if self.oracle.anchor != expected_anchor:
                raise ValueError("diagnostic anchor must exactly match the case id")
            if self.expectation is Expectation.DIAGNOSTIC and self.target_phase is Phase.SIMULATE:
                if self.oracle.marker != expected_marker:
                    raise ValueError("runtime diagnostics require a success-path pass marker")
            elif self.oracle.marker is not None:
                raise ValueError("only runtime diagnostics can also declare a pass marker")
        else:
            if self.oracle.kind is not OracleKind.PHASE_EXIT:
                raise ValueError("phase acceptance requires a phase-exit oracle")
            if self.oracle.marker is not None or self.oracle.anchor is not None:
                raise ValueError("phase-exit oracle has no marker or anchor")
        if self.target_phase is not Phase.SIMULATE and self.runtime_args:
            raise ValueError("runtime_args are only valid for simulate cases")
        return self


class SuiteDefinition(StrictModel):
    schema_version: MetadataSchemaVersion
    id: str
    description: SafeText
    cases: tuple[str, ...]

    @field_validator("id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        if ID_RE.fullmatch(value) is None:
            raise ValueError("suite id must use lowercase kebab-case")
        return value

    @model_validator(mode="after")
    def valid_case_patterns(self) -> Self:
        if not self.cases or len(self.cases) != len(set(self.cases)):
            raise ValueError("suite case patterns must be nonempty and unique")
        if any(
            not pattern
            or "/" in pattern
            or "\\" in pattern
            or "\x00" in pattern
            or re.fullmatch(r"[a-z0-9*?\[\]-]+", pattern) is None
            for pattern in self.cases
        ):
            raise ValueError("suite case patterns must be safe case-id globs")
        return self


class ToolProfile(StrictModel):
    id: str
    phase_ceiling: Phase
    direct_phases: tuple[Phase, ...]
    headline: bool = False
    standard_revision: StandardRevision
    effective_language: str = Field(min_length=1, max_length=100)

    @field_validator("id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        if ID_RE.fullmatch(value) is None:
            raise ValueError("profile id must use lowercase kebab-case")
        return value

    @model_validator(mode="after")
    def coherent_phase_scope(self) -> Self:
        expected_ceiling = {
            "parser": Phase.PARSE,
            "elaborator": Phase.ELABORATE,
            "simulator": Phase.SIMULATE,
        }
        if self.id not in expected_ceiling:
            raise ValueError("profiles are limited to parser, elaborator, and simulator")
        if self.phase_ceiling is not expected_ceiling[self.id]:
            raise ValueError(f"profile {self.id} must end at {expected_ceiling[self.id].value}")
        if not self.direct_phases or len(self.direct_phases) != len(set(self.direct_phases)):
            raise ValueError("direct phases must be nonempty and unique")
        if tuple(sorted(self.direct_phases, key=PHASE_ORDER.index)) != self.direct_phases:
            raise ValueError("direct phases must follow pipeline order")
        if any(not phase_reaches(self.phase_ceiling, phase) for phase in self.direct_phases):
            raise ValueError("direct phase exceeds the profile ceiling")
        if self.phase_ceiling not in self.direct_phases:
            raise ValueError("profile ceiling must be directly assessable")
        return self

    def supports(self, target: Phase) -> bool:
        return phase_reaches(self.phase_ceiling, target)


class ToolDefinition(StrictModel):
    id: str
    display_name: SafeText
    adapter: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    distribution: Distribution
    execution: ExecutionBackend
    ci: bool
    publish: bool
    upstream_url: str | None = Field(default=None, max_length=500)
    default_branch: str | None = Field(default=None, max_length=200)
    dockerfile: str | None = None
    recipe_files: tuple[str, ...] = ()
    image_repository: str | None = Field(default=None, max_length=500)
    profiles: tuple[ToolProfile, ...]

    @field_validator("id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        if ID_RE.fullmatch(value) is None:
            raise ValueError("tool id must use lowercase kebab-case")
        return value

    @field_validator("dockerfile")
    @classmethod
    def valid_dockerfile(cls, value: str | None) -> str | None:
        return None if value is None else safe_relative_path(value)

    @field_validator("recipe_files")
    @classmethod
    def valid_recipe_files(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate image recipe files")
        return tuple(safe_relative_path(item) for item in value)

    @model_validator(mode="after")
    def policy_is_coherent(self) -> Self:
        profile_ids = [profile.id for profile in self.profiles]
        if not profile_ids or len(profile_ids) != len(set(profile_ids)):
            raise ValueError("tool profiles must be nonempty and unique")
        if sum(profile.headline for profile in self.profiles) != 1:
            raise ValueError("each tool needs exactly one headline profile")
        if self.execution is ExecutionBackend.DOCKER:
            if self.distribution is Distribution.COMMERCIAL:
                raise ValueError("commercial tools must use a private local wrapper")
            if not self.dockerfile or not self.image_repository:
                raise ValueError("Docker tools require image build metadata")
            if self.distribution is Distribution.OPEN_SOURCE and not all(
                (self.upstream_url, self.default_branch)
            ):
                raise ValueError("open-source Docker tools require upstream ref metadata")
        if self.execution is ExecutionBackend.LOCAL_WRAPPER and (self.ci or self.publish):
            raise ValueError("local-wrapper tools cannot be CI or publication eligible")
        if self.publish and (not self.ci or self.distribution is not Distribution.OPEN_SOURCE):
            raise ValueError("published tools must be CI-eligible open source")
        return self

    def profile(self, profile_id: str) -> ToolProfile:
        for profile in self.profiles:
            if profile.id == profile_id:
                return profile
        raise KeyError(f"unknown profile {self.id}/{profile_id}")

    @property
    def headline_profile(self) -> ToolProfile:
        return next(profile for profile in self.profiles if profile.headline)


class ToolRegistry(StrictModel):
    schema_version: ContractSchemaVersion
    tools: tuple[ToolDefinition, ...]

    @model_validator(mode="after")
    def unique_tools(self) -> Self:
        ids = [tool.id for tool in self.tools]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate tool ids")
        return self

    def tool(self, tool_id: str) -> ToolDefinition:
        for tool in self.tools:
            if tool.id == tool_id:
                return tool
        raise KeyError(f"unknown tool {tool_id}")


class WrapperDefinition(StrictModel):
    tool: str
    command: tuple[str, ...]
    environment_allowlist: tuple[str, ...] = ()

    @model_validator(mode="after")
    def valid_wrapper(self) -> Self:
        if not self.command or any(not part or "\x00" in part for part in self.command):
            raise ValueError("wrapper command must be a nonempty argv array")
        if len(self.environment_allowlist) != len(set(self.environment_allowlist)):
            raise ValueError("duplicate wrapper environment names")
        for name in self.environment_allowlist:
            if re.fullmatch(r"^[A-Z_][A-Z0-9_]*$", name) is None:
                raise ValueError(f"invalid wrapper environment name {name!r}")
        return self


class PrivateToolConfig(StrictModel):
    schema_version: MetadataSchemaVersion
    wrappers: tuple[WrapperDefinition, ...]

    @model_validator(mode="after")
    def unique_wrappers(self) -> Self:
        tools = [wrapper.tool for wrapper in self.wrappers]
        if len(tools) != len(set(tools)):
            raise ValueError("duplicate private wrappers")
        return self

    def wrapper(self, tool_id: str) -> WrapperDefinition | None:
        return next((item for item in self.wrappers if item.tool == tool_id), None)


class ToolSelection(StrictModel):
    tool: str
    requested_ref: str
    resolved_sha: str
    resolved_at: datetime
    exact_tags: tuple[str, ...] = ()
    nearest_tag: str | None = None
    default_branch: str | None = None

    @field_validator("resolved_sha")
    @classmethod
    def valid_sha(cls, value: str) -> str:
        if SHA_RE.fullmatch(value) is None:
            raise ValueError("resolved_sha must be a full lowercase SHA")
        return value


class ImageIdentity(StrictModel):
    reference: SafeText
    image_id: str | None = None
    digest: str | None = None
    recipe_sha256: str
    base_image: SafeText
    base_image_digest: str | None = None
    platform: SafeText

    @field_validator("image_id", "digest", "base_image_digest")
    @classmethod
    def valid_digest(cls, value: str | None) -> str | None:
        if value is not None and HEX_DIGEST_RE.fullmatch(value) is None:
            raise ValueError("image digest must be sha256:<64 lowercase hex>")
        return value

    @field_validator("recipe_sha256")
    @classmethod
    def valid_recipe_hash(cls, value: str) -> str:
        if SHA256_RE.fullmatch(value) is None:
            raise ValueError("invalid recipe sha256")
        return value


class ExecutionStage(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    kind: StageKind
    attempted_through_phase: Phase
    argv: tuple[str, ...]
    portable_argv: tuple[str, ...]
    timeout_seconds: int = Field(ge=1, le=300)
    output_bytes: int = Field(ge=1024, le=1_048_576)
    expected_artifact: str | None = None

    @field_validator("expected_artifact")
    @classmethod
    def valid_artifact(cls, value: str | None) -> str | None:
        return None if value is None else safe_relative_path(value)

    @model_validator(mode="after")
    def valid_command(self) -> Self:
        if self.kind is StageKind.RUN and self.attempted_through_phase is not Phase.SIMULATE:
            raise ValueError("runtime stages must attempt through simulation")
        if self.kind is StageKind.COMPILE and self.attempted_through_phase is Phase.SIMULATE:
            raise ValueError("compile stages cannot claim simulation evidence")
        if not self.argv or not self.portable_argv:
            raise ValueError("execution argv must not be empty")
        if len(self.argv) != len(self.portable_argv):
            raise ValueError("portable argv must have the same shape as argv")
        if any(not item or "\x00" in item for item in (*self.argv, *self.portable_argv)):
            raise ValueError("execution argv contains an empty or NUL argument")
        return self


class ExecutionPlan(StrictModel):
    schema_version: ContractSchemaVersion
    case_id: str
    tool_id: str
    profile_id: str
    target_phase: Phase
    backend: ExecutionBackend
    image: str | None = None
    wrapper: str | None = None
    stages: tuple[ExecutionStage, ...]

    @model_validator(mode="after")
    def valid_backend(self) -> Self:
        if not self.stages:
            raise ValueError("execution plan needs at least one stage")
        if self.backend is ExecutionBackend.DOCKER and not self.image:
            raise ValueError("Docker execution requires an image")
        if self.backend is ExecutionBackend.LOCAL_WRAPPER and not self.wrapper:
            raise ValueError("local-wrapper execution requires a wrapper")
        if self.image and self.wrapper:
            raise ValueError("execution plan cannot use image and wrapper together")
        ids = [stage.id for stage in self.stages]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate stage ids")
        if any(stage.kind is StageKind.RUN for stage in self.stages[:-1]):
            raise ValueError("runtime stage must be last")
        if not any(
            phase_reaches(stage.attempted_through_phase, self.target_phase) for stage in self.stages
        ):
            raise ValueError("execution plan does not attempt the target phase")
        return self


class CapturedStream(StrictModel):
    excerpt: str
    size_bytes: int = Field(ge=0)
    sha256: str
    truncated: bool

    @field_validator("sha256")
    @classmethod
    def valid_hash(cls, value: str) -> str:
        if SHA256_RE.fullmatch(value) is None:
            raise ValueError("invalid stream sha256")
        return value


class Diagnostic(StrictModel):
    severity: str = Field(pattern=r"^(error|warning|fatal|note|info)$")
    message: str = Field(max_length=4096)
    source: str | None = Field(default=None, max_length=500)
    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)
    code: str | None = Field(default=None, max_length=100)
    target_case_id: str | None = None


class StageObservation(StrictModel):
    stage_id: str
    kind: StageKind
    attempted_through_phase: Phase
    outcome: RawOutcome
    exit_code: int | None = Field(default=None, ge=0)
    signal: int | None = Field(default=None, ge=1)
    duration_seconds: float = Field(ge=0)
    stdout: CapturedStream
    stderr: CapturedStream
    diagnostics: tuple[Diagnostic, ...] = ()
    internal_error: bool = False
    artifact_present: bool | None = None
    portable_argv: tuple[str, ...]

    @model_validator(mode="after")
    def coherent_outcome(self) -> Self:
        if self.kind is StageKind.RUN and self.attempted_through_phase is not Phase.SIMULATE:
            raise ValueError("runtime observations must attempt through simulation")
        if self.kind is StageKind.COMPILE and self.attempted_through_phase is Phase.SIMULATE:
            raise ValueError("compile observations cannot claim simulation evidence")
        if self.outcome is RawOutcome.NORMAL_EXIT:
            if self.exit_code is None or self.signal is not None:
                raise ValueError("normal exit requires only a nonnegative exit_code")
        elif self.outcome is RawOutcome.SIGNAL:
            if self.signal is None or self.exit_code is not None:
                raise ValueError("signal outcome requires only a positive signal")
        elif self.exit_code is not None or self.signal is not None:
            raise ValueError("operational outcomes cannot carry exit status")
        if not self.portable_argv or any(
            not argument or "\x00" in argument for argument in self.portable_argv
        ):
            raise ValueError("observation portable argv must be a nonempty safe argv array")
        return self


class NormalizedResult(StrictModel):
    schema_version: ContractSchemaVersion
    case_id: str
    requirement_id: str
    tool_id: str
    profile_id: str
    target_phase: Phase
    evidence_mode: EvidenceMode
    status: ResultStatus
    reason: ReasonCode
    summary: SafeText
    evidence: EvidenceLevel
    observations: tuple[StageObservation, ...] = ()
    known_issue: str | None = Field(default=None, max_length=500)
    reproduction_command: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def coherent_judgment(self) -> Self:
        allowed_reasons = {
            ResultStatus.CONFORMING: {ReasonCode.EXPECTATION_MET},
            ResultStatus.NONCONFORMING: {
                ReasonCode.UNEXPECTED_ACCEPT,
                ReasonCode.UNEXPECTED_REJECT,
                ReasonCode.MISSING_DIAGNOSTIC,
                ReasonCode.OFF_TARGET_DIAGNOSTIC,
                ReasonCode.MISSING_PASS_MARKER,
                ReasonCode.MULTIPLE_PASS_MARKERS,
                ReasonCode.PASS_MARKER_NONZERO,
                ReasonCode.WRONG_RUNTIME_RESULT,
                ReasonCode.MISSING_ARTIFACT,
            },
            ResultStatus.INCONCLUSIVE: {
                ReasonCode.MISSING_DIAGNOSTIC,
                ReasonCode.OFF_TARGET_DIAGNOSTIC,
                ReasonCode.TIMEOUT,
                ReasonCode.CRASH,
                ReasonCode.INTERNAL_ERROR,
                ReasonCode.OUTPUT_TRUNCATED,
                ReasonCode.TARGET_PHASE_UNPROVEN,
            },
            ResultStatus.UNSUPPORTED_CAPABILITY: {ReasonCode.UNSUPPORTED_PHASE},
            ResultStatus.UNSUPPORTED_REVISION: {ReasonCode.UNSUPPORTED_REVISION},
            ResultStatus.NOT_APPLICABLE: {ReasonCode.NOT_APPLICABLE},
            ResultStatus.SKIPPED_UNAVAILABLE: {ReasonCode.TOOL_UNAVAILABLE},
            ResultStatus.HARNESS_ERROR: {
                ReasonCode.CONTAINER_FAILURE,
                ReasonCode.LAUNCH_FAILURE,
                ReasonCode.INVALID_EXECUTION_PLAN,
                ReasonCode.MANIFEST_MISMATCH,
                ReasonCode.TOOL_PREPARATION_FAILURE,
            },
        }
        if self.reason not in allowed_reasons[self.status]:
            raise ValueError(
                f"reason {self.reason.value} is incoherent with status {self.status.value}"
            )
        executable = {
            ResultStatus.CONFORMING,
            ResultStatus.NONCONFORMING,
            ResultStatus.INCONCLUSIVE,
        }
        if self.status in executable and not self.observations:
            raise ValueError("an executable judgment requires observations")
        covering = next(
            (
                observation
                for observation in self.observations
                if phase_reaches(observation.attempted_through_phase, self.target_phase)
            ),
            None,
        )
        expected_mode = EvidenceMode.NOT_OBSERVED
        if covering is not None:
            expected_mode = (
                EvidenceMode.DIRECT
                if covering.attempted_through_phase is self.target_phase
                else EvidenceMode.CUMULATIVE
            )
        if self.evidence_mode is not expected_mode:
            raise ValueError("evidence mode does not match the recorded observations")
        if self.status is ResultStatus.CONFORMING and covering is None:
            raise ValueError("conformance requires target-reaching evidence")
        synthetic_statuses = {
            ResultStatus.UNSUPPORTED_CAPABILITY,
            ResultStatus.UNSUPPORTED_REVISION,
            ResultStatus.NOT_APPLICABLE,
        }
        if self.status in synthetic_statuses and self.observations:
            raise ValueError("a structural synthetic result cannot carry observations")
        return self


class RepositoryIdentity(StrictModel):
    commit: str
    dirty: bool

    @field_validator("commit")
    @classmethod
    def valid_commit(cls, value: str) -> str:
        if value != "unborn" and SHA_RE.fullmatch(value) is None:
            raise ValueError("repository commit must be a full SHA or 'unborn'")
        return value


class ManifestHashes(StrictModel):
    requirements: str
    cases: str
    selection: str

    @field_validator("*")
    @classmethod
    def valid_hash(cls, value: str) -> str:
        if SHA256_RE.fullmatch(value) is None:
            raise ValueError("invalid manifest SHA-256")
        return value


class CaseIdentity(StrictModel):
    id: str
    content_sha256: str

    @field_validator("content_sha256")
    @classmethod
    def valid_hash(cls, value: str) -> str:
        if SHA256_RE.fullmatch(value) is None:
            raise ValueError("invalid case content SHA-256")
        return value


class CorpusRatio(StrictModel):
    numerator: int = Field(strict=True, ge=0)
    denominator: int = Field(strict=True, ge=0)


class CorpusMetricValues(StrictModel):
    coverage: CorpusRatio
    density: CorpusRatio

    @model_validator(mode="after")
    def valid_operands(self) -> Self:
        if self.coverage.numerator > self.coverage.denominator:
            raise ValueError("coverage numerator cannot exceed its denominator")
        if self.density.denominator != self.coverage.numerator:
            raise ValueError("density denominator must equal the coverage numerator")
        if self.density.numerator < self.density.denominator:
            raise ValueError("density numerator cannot be below its denominator")
        return self


class StandardPartKind(StrEnum):
    CHAPTER = "chapter"
    ANNEX = "annex"


class CorpusPartMetric(CorpusMetricValues):
    id: str
    kind: StandardPartKind
    title: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def valid_part_id(self) -> Self:
        if self.kind is StandardPartKind.CHAPTER:
            if re.fullmatch(r"[1-9][0-9]*", self.id) is None:
                raise ValueError("chapter metric needs a numeric part ID")
        elif re.fullmatch(r"[A-Q]", self.id) is None:
            raise ValueError("annex metric needs an A-Q part ID")
        return self


class CorpusMetricSummary(CorpusMetricValues):
    breakdown: tuple[CorpusPartMetric, ...] = Field(min_length=58, max_length=58)

    @model_validator(mode="after")
    def complete_breakdown(self) -> Self:
        identities = tuple((part.kind, part.id) for part in self.breakdown)
        expected = (
            *((StandardPartKind.CHAPTER, str(chapter)) for chapter in range(1, 42)),
            *((StandardPartKind.ANNEX, annex) for annex in "ABCDEFGHIJKLMNOPQ"),
        )
        if identities != expected:
            raise ValueError(
                "corpus metric breakdown must contain ordered chapters 1-41 and annexes A-Q"
            )
        if self.coverage.numerator != sum(
            part.coverage.numerator for part in self.breakdown
        ) or self.coverage.denominator != sum(part.coverage.denominator for part in self.breakdown):
            raise ValueError("coverage aggregate does not match its breakdown")
        if self.density.numerator != sum(
            part.density.numerator for part in self.breakdown
        ) or self.density.denominator != sum(part.density.denominator for part in self.breakdown):
            raise ValueError("density aggregate does not match its breakdown")
        return self


class CorpusMetrics(StrictModel):
    requirements: CorpusMetricSummary
    cases: CorpusMetricSummary

    @model_validator(mode="after")
    def matching_parts(self) -> Self:
        requirements = tuple(
            (part.kind, part.id, part.title) for part in self.requirements.breakdown
        )
        cases = tuple((part.kind, part.id, part.title) for part in self.cases.breakdown)
        if requirements != cases:
            raise ValueError("requirement and case metrics must describe the same parts")
        return self


class CampaignTool(StrictModel):
    definition: ToolDefinition
    selection: ToolSelection | None = None
    image: ImageIdentity | None = None
    reported_version: str | None = Field(default=None, max_length=1000)
    profile_ids: tuple[str, ...]
    preparation_error: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def coherent_identity(self) -> Self:
        if not self.profile_ids or len(self.profile_ids) != len(set(self.profile_ids)):
            raise ValueError("campaign tool profiles must be nonempty and unique")
        declared_profiles = {profile.id for profile in self.definition.profiles}
        if not set(self.profile_ids) <= declared_profiles:
            raise ValueError("campaign tool references an undeclared profile")
        if self.selection is not None and self.selection.tool != self.definition.id:
            raise ValueError("tool selection identity does not match its definition")
        if self.preparation_error is None:
            if self.definition.execution is ExecutionBackend.DOCKER and self.image is None:
                raise ValueError("Docker campaign tools require an image identity")
            if self.definition.distribution is Distribution.OPEN_SOURCE and self.selection is None:
                raise ValueError("open-source campaign tools require an exact source selection")
        elif any(
            value is not None for value in (self.selection, self.image, self.reported_version)
        ):
            raise ValueError(
                "a preparation failure cannot carry source, image, or version identity"
            )
        if self.definition.execution is ExecutionBackend.LOCAL_WRAPPER and self.image is not None:
            raise ValueError("private wrapper campaign tools cannot expose an image")
        return self


class CampaignTrust(StrictModel):
    source: str = Field(pattern=r"^(local|github-actions)$")
    repository: str | None = Field(default=None, max_length=300)
    workflow_run_id: str | None = Field(default=None, max_length=100)
    checkout_sha: str | None = None

    @field_validator("checkout_sha")
    @classmethod
    def valid_checkout_sha(cls, value: str | None) -> str | None:
        if value is not None and SHA_RE.fullmatch(value) is None:
            raise ValueError("checkout_sha must be a full lowercase SHA")
        return value

    @model_validator(mode="after")
    def coherent_source(self) -> Self:
        github_values = (self.repository, self.workflow_run_id, self.checkout_sha)
        if self.source == "github-actions":
            if not all(github_values):
                raise ValueError("GitHub Actions trust requires repository, run id, and SHA")
            assert self.repository is not None
            assert self.workflow_run_id is not None
            if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repository) is None:
                raise ValueError("invalid GitHub repository identity")
            if re.fullmatch(r"[0-9]+", self.workflow_run_id) is None:
                raise ValueError("invalid GitHub workflow run id")
        elif any(value is not None for value in github_values):
            raise ValueError("local trust cannot carry GitHub Actions identity")
        return self


class Campaign(StrictModel):
    schema_version: CampaignSchemaVersion
    id: str = Field(pattern=CAMPAIGN_ID_RE.pattern)
    started_at: datetime
    finished_at: datetime
    repository: RepositoryIdentity
    platform: SafeText
    selection_name: SafeText
    case_ids: tuple[str, ...]
    cases: tuple[CaseIdentity, ...]
    tools: tuple[CampaignTool, ...]
    expected_tool_ids: tuple[str, ...]
    missing_tool_ids: tuple[str, ...] = ()
    hashes: ManifestHashes
    corpus_metrics: CorpusMetrics
    results: tuple[NormalizedResult, ...]
    complete: bool
    trust: CampaignTrust

    @model_validator(mode="after")
    def internally_consistent(self) -> Self:
        if self.finished_at < self.started_at:
            raise ValueError("campaign finish precedes start")
        if len(self.case_ids) != len(set(self.case_ids)):
            raise ValueError("duplicate selected case ids")
        case_map = {case.id: case for case in self.cases}
        if set(case_map) != set(self.case_ids) or len(case_map) != len(self.cases):
            raise ValueError("case identity manifest does not match selected case ids")
        tool_ids = [tool.definition.id for tool in self.tools]
        if len(tool_ids) != len(set(tool_ids)):
            raise ValueError("duplicate campaign tools")
        if not self.expected_tool_ids or len(self.expected_tool_ids) != len(
            set(self.expected_tool_ids)
        ):
            raise ValueError("expected campaign tools must be nonempty and unique")
        expected_missing = set(self.expected_tool_ids) - set(tool_ids)
        if set(self.missing_tool_ids) != expected_missing or len(self.missing_tool_ids) != len(
            set(self.missing_tool_ids)
        ):
            raise ValueError("missing campaign tools do not match expected tools")
        if not set(tool_ids) <= set(self.expected_tool_ids):
            raise ValueError("an observed campaign tool was not expected")
        expected_results = {
            (case_id, tool.definition.id, profile_id)
            for case_id in self.case_ids
            for tool in self.tools
            for profile_id in tool.profile_ids
        }
        result_keys = [
            (result.case_id, result.tool_id, result.profile_id) for result in self.results
        ]
        if len(result_keys) != len(set(result_keys)) or set(result_keys) != expected_results:
            raise ValueError("campaign result grid is incomplete or contains duplicates")
        profile_map = {
            (tool.definition.id, profile_id)
            for tool in self.tools
            for profile_id in tool.profile_ids
        }
        preparation_failed = {
            tool.definition.id for tool in self.tools if tool.preparation_error is not None
        }
        for result in self.results:
            if (
                result.case_id not in case_map
                or (result.tool_id, result.profile_id) not in profile_map
            ):
                raise ValueError("result references an unknown case or tool profile")
            if result.tool_id in preparation_failed and (
                result.observations
                or result.status
                not in {
                    ResultStatus.HARNESS_ERROR,
                    ResultStatus.UNSUPPORTED_CAPABILITY,
                    ResultStatus.UNSUPPORTED_REVISION,
                    ResultStatus.NOT_APPLICABLE,
                }
                or (
                    result.status is ResultStatus.HARNESS_ERROR
                    and result.reason is not ReasonCode.TOOL_PREPARATION_FAILURE
                )
            ):
                raise ValueError(
                    "preparation-failure tools can only carry synthetic structural "
                    "or preparation results"
                )
        if self.complete and (
            self.missing_tool_ids
            or preparation_failed
            or any(
                result.status in {ResultStatus.HARNESS_ERROR, ResultStatus.SKIPPED_UNAVAILABLE}
                for result in self.results
            )
        ):
            raise ValueError("a complete campaign cannot contain missing or unavailable evidence")
        return self


class MetricBreakdown(StrictModel):
    label: str
    revision: StandardRevision
    tool_id: str
    profile_id: str
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    corpus_sha: str
    complete: bool
    valid: bool
    corpus_coverage: int = Field(ge=0)
    execution_coverage: int = Field(ge=0)
    conforming: int = Field(ge=0)
    nonconforming: int = Field(ge=0)
    inconclusive: int = Field(ge=0)
    unsupported: int = Field(ge=0)
    infrastructure_state: str

    @field_validator("corpus_sha")
    @classmethod
    def valid_corpus_hash(cls, value: str) -> str:
        if SHA256_RE.fullmatch(value) is None:
            raise ValueError("invalid corpus hash")
        return value


def model_to_jsonable(model: StrictModel) -> dict[str, Any]:
    """Return stable JSON-compatible data with enum values and ISO timestamps."""

    value = model.model_dump(mode="json", exclude_none=True)
    assert isinstance(value, dict)
    return value
