"""Strict versioned models for portable dashboard resources."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from svtorture.models import (
    CAMPAIGN_ID_RE,
    SHA256_RE,
    SHA_RE,
    CampaignTool,
    CampaignTrust,
    CaseDefinition,
    CorpusMetrics,
    EvidenceLevel,
    EvidenceMode,
    ManifestHashes,
    MetricBreakdown,
    Phase,
    ReasonCode,
    RepositoryIdentity,
    Requirement,
    ResultStatus,
    SafeText,
    StageObservation,
    StandardSection,
    StrictModel,
    standard_location_sort_key,
)

DashboardSchemaVersion = Annotated[int, Field(strict=True, ge=6, le=6)]
StrictCount = Annotated[int, Field(strict=True, ge=0)]
Sha256 = Annotated[str, Field(pattern=SHA256_RE.pattern)]
FullCommit = Annotated[str, Field(pattern=SHA_RE.pattern)]
Commit = Annotated[str, Field(pattern=rf"^(?:unborn|{SHA_RE.pattern[1:-1]})$")]
SafeHref = Annotated[str, Field(min_length=1, pattern=r"^[^/\\\x00][^\\\x00]*$")]
HttpsUrl = Annotated[str, Field(pattern=r"^https://[^\s]+$")]
SourceUrl = Annotated[
    str,
    Field(pattern=r"^(?:https://[^\s]+|data:text/plain;charset=utf-8,[^\s]*)$"),
]
ZipBasename = Annotated[str, Field(pattern=r"^[^/\\]+\.zip$")]


def _safe_href(value: str) -> str:
    parts = value.split("/")
    if (
        not value
        or value.startswith("/")
        or "\\" in value
        or "\x00" in value
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise ValueError("resource href must be a safe relative path")
    return value


def _require_sha256(value: str) -> str:
    if SHA256_RE.fullmatch(value) is None:
        raise ValueError("invalid SHA-256")
    return value


class DashboardResource(StrictModel):
    href: SafeHref
    sha256: Sha256
    bytes: StrictCount

    _valid_href = field_validator("href")(_safe_href)
    _valid_sha256 = field_validator("sha256")(_require_sha256)


class CountedDashboardResource(DashboardResource):
    case_count: StrictCount
    result_count: StrictCount


class CampaignResources(StrictModel):
    catalog: DashboardResource
    verdicts: CountedDashboardResource
    evidence: tuple[CountedDashboardResource, ...]

    @model_validator(mode="after")
    def unique_hrefs_and_matching_counts(self) -> Self:
        resources = (self.catalog, self.verdicts, *self.evidence)
        hrefs = [resource.href for resource in resources]
        if len(hrefs) != len(set(hrefs)):
            raise ValueError("campaign resources must have unique hrefs")
        if not self.evidence and self.verdicts.result_count:
            raise ValueError("campaign verdicts with results require evidence resources")
        if sum(resource.case_count for resource in self.evidence) != self.verdicts.case_count:
            raise ValueError("evidence case counts do not match verdicts")
        if sum(resource.result_count for resource in self.evidence) != self.verdicts.result_count:
            raise ValueError("evidence result counts do not match verdicts")
        return self


class DashboardMetric(MetricBreakdown):
    tool_sha: FullCommit | None = None
    exact_tags: tuple[str, ...] = ()
    nearest_tag: str | None = None
    reported_version: str | None = None
    image_digest: str | None = None

    @field_validator("tool_sha")
    @classmethod
    def valid_tool_sha(cls, value: str | None) -> str | None:
        if value is not None and SHA_RE.fullmatch(value) is None:
            raise ValueError("tool_sha must be a full lowercase SHA")
        return value


class SummaryRepository(StrictModel):
    commit: Commit

    @field_validator("commit")
    @classmethod
    def valid_commit(cls, value: str) -> str:
        if value != "unborn" and SHA_RE.fullmatch(value) is None:
            raise ValueError("summary repository commit must be a full lowercase SHA or 'unborn'")
        return value


class ArchiveMetadata(StrictModel):
    release_tag: Annotated[str, Field(pattern=r"^campaign-[^/\\]+$")]
    release_url: HttpsUrl
    asset_name: ZipBasename
    download_url: HttpsUrl
    sha256: Sha256
    bytes: StrictCount

    _valid_sha256 = field_validator("sha256")(_require_sha256)

    @model_validator(mode="after")
    def valid_archive_identity(self) -> Self:
        if not self.release_tag.startswith("campaign-"):
            raise ValueError("archive release tag must use the campaign- prefix")
        if (
            "/" in self.asset_name
            or "\\" in self.asset_name
            or not self.asset_name.endswith(".zip")
        ):
            raise ValueError("archive asset_name must be a ZIP basename")
        if not self.release_url.startswith("https://") or not self.download_url.startswith(
            "https://"
        ):
            raise ValueError("archive URLs must use HTTPS")
        return self


class CampaignSummary(StrictModel):
    schema_version: DashboardSchemaVersion = 6
    kind: Literal["campaign-summary"] = "campaign-summary"
    id: str = Field(pattern=CAMPAIGN_ID_RE.pattern)
    started_at: datetime
    finished_at: datetime
    complete: bool
    repository: SummaryRepository
    trust: CampaignTrust
    hashes: ManifestHashes
    corpus_metrics: CorpusMetrics
    tool_metrics: tuple[DashboardMetric, ...]
    archive: ArchiveMetadata | None = None

    @model_validator(mode="after")
    def coherent_summary(self) -> Self:
        if self.started_at.utcoffset() != timedelta(0) or self.finished_at.utcoffset() != timedelta(
            0
        ):
            raise ValueError("campaign summary timestamps must be UTC")
        if self.finished_at < self.started_at:
            raise ValueError("campaign summary finish precedes start")
        if self.archive is not None:
            if self.repository.commit == "unborn":
                raise ValueError("published campaign summary requires a committed repository")
            if self.archive.release_tag != f"campaign-{self.id}":
                raise ValueError("archive release tag does not match campaign id")
            if self.archive.asset_name != f"svtorture-campaign-{self.id}.zip":
                raise ValueError("archive asset name does not match campaign id")
        identities = [(metric.tool_id, metric.profile_id) for metric in self.tool_metrics]
        if identities != sorted(identities) or len(identities) != len(set(identities)):
            raise ValueError("campaign summary metrics must be unique and sorted")
        return self


class CampaignTrends(StrictModel):
    schema_version: DashboardSchemaVersion = 6
    kind: Literal["campaign-trends"] = "campaign-trends"
    campaigns: tuple[CampaignSummary, ...]

    @model_validator(mode="after")
    def unique_and_sorted_campaigns(self) -> Self:
        identities = [(campaign.finished_at, campaign.id) for campaign in self.campaigns]
        if identities != sorted(identities) or len(
            {campaign.id for campaign in self.campaigns}
        ) != len(self.campaigns):
            raise ValueError("campaign trends must be unique and sorted")
        return self


class DashboardIndexCampaign(StrictModel):
    id: str = Field(pattern=CAMPAIGN_ID_RE.pattern)
    manifest: SafeHref

    _valid_manifest = field_validator("manifest")(_safe_href)


class DashboardSchemas(StrictModel):
    summary: SafeHref
    trends: SafeHref
    campaign: SafeHref
    catalog: SafeHref
    verdicts: SafeHref
    evidence: SafeHref

    @field_validator("*")
    @classmethod
    def valid_schema_href(cls, value: str) -> str:
        return _safe_href(value)


class DashboardIndex(StrictModel):
    schema_version: DashboardSchemaVersion = 6
    kind: Literal["dashboard-index"] = "dashboard-index"
    default_campaign_id: str = Field(pattern=CAMPAIGN_ID_RE.pattern)
    campaigns: tuple[DashboardIndexCampaign, ...]
    trends: SafeHref
    schemas: DashboardSchemas

    _valid_trends = field_validator("trends")(_safe_href)

    @model_validator(mode="after")
    def coherent_index(self) -> Self:
        ids = [campaign.id for campaign in self.campaigns]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("dashboard index campaigns must be nonempty and unique")
        if self.default_campaign_id not in ids:
            raise ValueError("default campaign must be available in the dashboard index")
        return self


class DashboardCase(CaseDefinition):
    content_sha256: Sha256
    definition_sha256: Sha256
    source_links: dict[str, SourceUrl]

    _valid_content_hash = field_validator("content_sha256", "definition_sha256")(_require_sha256)

    @model_validator(mode="after")
    def complete_source_links(self) -> Self:
        if set(self.source_links) != set(self.sources):
            raise ValueError("case source links must match its source files")
        if any(not value for value in self.source_links.values()):
            raise ValueError("case source links must be nonempty")
        return self


class CampaignCatalog(StrictModel):
    schema_version: DashboardSchemaVersion = 6
    kind: Literal["campaign-catalog"] = "campaign-catalog"
    campaign_id: str = Field(pattern=CAMPAIGN_ID_RE.pattern)
    requirements: tuple[Requirement, ...]
    cases: tuple[DashboardCase, ...]
    corpus_metrics: CorpusMetrics
    standard_sections: Annotated[
        tuple[StandardSection, ...], Field(min_length=1740, max_length=1740)
    ] = ()

    @model_validator(mode="after")
    def unique_and_sorted_definitions(self) -> Self:
        requirement_ids = [requirement.id for requirement in self.requirements]
        if requirement_ids != [
            requirement.id
            for requirement in sorted(
                self.requirements, key=lambda item: standard_location_sort_key(item.clause)
            )
        ] or len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("catalog requirements must be unique and canonically sorted")
        case_ids = [case.id for case in self.cases]
        if case_ids != sorted(case_ids) or len(case_ids) != len(set(case_ids)):
            raise ValueError("catalog cases must be unique and sorted")
        section_locations = [section.clause for section in self.standard_sections]
        if section_locations != sorted(section_locations, key=standard_location_sort_key) or len(
            section_locations
        ) != len(set(section_locations)):
            raise ValueError("standard sections must be unique and canonically sorted")
        if self.standard_sections:
            missing_clauses = sorted(
                {requirement.clause for requirement in self.requirements} - set(section_locations),
                key=standard_location_sort_key,
            )
            if missing_clauses:
                raise ValueError(
                    "standard sections must contain every requirement clause: "
                    + ", ".join(missing_clauses)
                )
        return self


class CampaignVerdict(StrictModel):
    tool_id: str
    profile_id: str
    status: ResultStatus
    reason: ReasonCode
    evidence_mode: EvidenceMode
    summary: SafeText
    known_issue: str | None = Field(default=None, max_length=500)


class CampaignCaseVerdicts(StrictModel):
    case_id: str
    evidence_href: SafeHref
    results: tuple[CampaignVerdict, ...]

    _valid_evidence_href = field_validator("evidence_href")(_safe_href)

    @model_validator(mode="after")
    def unique_and_sorted_results(self) -> Self:
        identities = [(result.tool_id, result.profile_id) for result in self.results]
        if identities != sorted(identities) or len(identities) != len(set(identities)):
            raise ValueError("case verdict results must be unique and sorted")
        return self


class CampaignVerdicts(StrictModel):
    schema_version: DashboardSchemaVersion = 6
    kind: Literal["campaign-verdicts"] = "campaign-verdicts"
    campaign_id: str = Field(pattern=CAMPAIGN_ID_RE.pattern)
    case_count: StrictCount
    result_count: StrictCount
    cases: tuple[CampaignCaseVerdicts, ...]

    @model_validator(mode="after")
    def coherent_counts(self) -> Self:
        case_ids = [case.case_id for case in self.cases]
        if case_ids != sorted(case_ids) or len(case_ids) != len(set(case_ids)):
            raise ValueError("verdict cases must be unique and sorted")
        if self.case_count != len(self.cases):
            raise ValueError("verdict case_count does not match cases")
        if self.result_count != sum(len(case.results) for case in self.cases):
            raise ValueError("verdict result_count does not match results")
        return self


class DashboardEvidenceResult(StrictModel):
    schema_version: Annotated[int, Field(strict=True, ge=2, le=2)]
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


class CampaignEvidenceShard(StrictModel):
    schema_version: DashboardSchemaVersion = 6
    kind: Literal["campaign-evidence"] = "campaign-evidence"
    campaign_id: str = Field(pattern=CAMPAIGN_ID_RE.pattern)
    case_ids: tuple[str, ...]
    results: tuple[DashboardEvidenceResult, ...]

    @model_validator(mode="after")
    def coherent_results(self) -> Self:
        if not self.case_ids or list(self.case_ids) != sorted(self.case_ids):
            raise ValueError("evidence case_ids must be nonempty and sorted")
        if len(self.case_ids) != len(set(self.case_ids)):
            raise ValueError("evidence case_ids must be unique")
        identities = [
            (result.case_id, result.tool_id, result.profile_id) for result in self.results
        ]
        if identities != sorted(identities) or len(identities) != len(set(identities)):
            raise ValueError("evidence results must be unique and sorted")
        if not {result.case_id for result in self.results}.issubset(self.case_ids):
            raise ValueError("evidence results must belong to shard cases")
        return self


class DashboardCaseIdentity(StrictModel):
    id: str
    content_sha256: Sha256
    definition_sha256: Sha256

    _valid_hashes = field_validator("content_sha256", "definition_sha256")(_require_sha256)


class CampaignManifest(StrictModel):
    schema_version: DashboardSchemaVersion = 6
    kind: Literal["campaign-manifest"] = "campaign-manifest"
    id: str = Field(pattern=CAMPAIGN_ID_RE.pattern)
    started_at: datetime
    finished_at: datetime
    repository: RepositoryIdentity
    platform: SafeText
    selection_name: SafeText
    cases: tuple[DashboardCaseIdentity, ...]
    tools: tuple[CampaignTool, ...]
    expected_tool_ids: tuple[str, ...]
    missing_tool_ids: tuple[str, ...]
    hashes: ManifestHashes
    corpus_metrics: CorpusMetrics
    metrics: tuple[DashboardMetric, ...]
    complete: bool
    trust: CampaignTrust
    resources: CampaignResources

    @model_validator(mode="after")
    def coherent_manifest(self) -> Self:
        if self.started_at.utcoffset() != timedelta(0) or self.finished_at.utcoffset() != timedelta(
            0
        ):
            raise ValueError("campaign manifest timestamps must be UTC")
        if self.finished_at < self.started_at:
            raise ValueError("campaign manifest finish precedes start")
        case_ids = [case.id for case in self.cases]
        if case_ids != sorted(case_ids) or len(case_ids) != len(set(case_ids)):
            raise ValueError("manifest cases must be unique and sorted")
        tool_ids = [tool.definition.id for tool in self.tools]
        if tool_ids != sorted(tool_ids) or len(tool_ids) != len(set(tool_ids)):
            raise ValueError("manifest tools must be unique and sorted")
        metric_ids = [(metric.tool_id, metric.profile_id) for metric in self.metrics]
        expected_metric_ids = {
            (tool.definition.id, profile_id)
            for tool in self.tools
            for profile_id in tool.profile_ids
        }
        if (
            metric_ids != sorted(metric_ids)
            or len(metric_ids) != len(set(metric_ids))
            or set(metric_ids) != expected_metric_ids
        ):
            raise ValueError("manifest metrics must match campaign tool profiles")
        if set(tool_ids) - set(self.expected_tool_ids):
            raise ValueError("manifest contains an unexpected tool")
        if set(self.missing_tool_ids) != set(self.expected_tool_ids) - set(tool_ids):
            raise ValueError("manifest missing tools do not match expected tools")
        tools = {tool.definition.id: tool for tool in self.tools}
        for metric in self.metrics:
            tool = tools[metric.tool_id]
            selection = tool.selection
            image = tool.image
            if (
                metric.corpus_sha != self.hashes.cases
                or metric.tool_sha != (selection.resolved_sha if selection else None)
                or metric.exact_tags != (selection.exact_tags if selection else ())
                or metric.nearest_tag != (selection.nearest_tag if selection else None)
                or metric.reported_version != tool.reported_version
                or metric.image_digest != (image.digest if image else None)
            ):
                raise ValueError("manifest metric provenance does not match campaign tool")
        if self.resources.verdicts.case_count != len(self.cases):
            raise ValueError("manifest resource case count does not match selected cases")
        expected_result_count = len(self.cases) * sum(len(tool.profile_ids) for tool in self.tools)
        if self.resources.verdicts.result_count != expected_result_count:
            raise ValueError("manifest resource result count does not match campaign grid")
        return self
