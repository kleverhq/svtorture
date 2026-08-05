"""Load and cross-validate the requirement inventory, cases, suites, and tools."""

from __future__ import annotations

import json
import subprocess
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import ValidationError

from svtorture.hashing import hash_json, sha256_bytes
from svtorture.models import (
    Applicability,
    CaseDefinition,
    CaseIdentity,
    CorpusMetrics,
    CorpusMetricSummary,
    CorpusPartMetric,
    CorpusRatio,
    Expectation,
    OracleKind,
    Phase,
    RepositoryIdentity,
    Requirement,
    RequirementInventory,
    RequirementPart,
    StandardPartKind,
    StandardSection,
    StandardsIndex,
    SuiteDefinition,
    TagRegistry,
    ToolDefinition,
    ToolIndex,
    ToolManifest,
    ToolRegistry,
    WaiverPart,
    model_to_jsonable,
    standard_location_sort_key,
)


class CatalogError(ValueError):
    """The corpus or registry cannot be trusted."""


@dataclass(frozen=True)
class _StandardPart:
    id: str
    kind: StandardPartKind
    title: str
    anchors: tuple[str, ...]


@dataclass(frozen=True)
class _StandardIndex:
    parts: tuple[_StandardPart, ...]
    sections: tuple[StandardSection, ...]


@dataclass(frozen=True)
class LoadedCase:
    definition: CaseDefinition
    directory: Path
    metadata_path: Path
    anchor_source: str | None
    anchor_line: int | None
    content_sha256: str


@dataclass(frozen=True)
class Catalog:
    root: Path
    anchor_index: Path
    inventory: RequirementInventory
    tags: TagRegistry
    cases: dict[str, LoadedCase]
    suites: dict[str, SuiteDefinition]
    suite_cases: dict[str, tuple[str, ...]]
    tools: ToolRegistry
    standard_sections: tuple[StandardSection, ...]
    waived_anchors: frozenset[str]

    @property
    def requirements(self) -> dict[str, Requirement]:
        return {item.id: item for item in self.inventory.requirements}

    def selected_cases(self, suite_id: str) -> tuple[LoadedCase, ...]:
        try:
            case_ids = self.suite_cases[suite_id]
        except KeyError as error:
            raise CatalogError(f"unknown suite {suite_id!r}") from error
        return tuple(self.cases[case_id] for case_id in case_ids)

    def case_manifest_hash(self, selected: Iterable[LoadedCase] | None = None) -> str:
        cases = tuple(selected) if selected is not None else tuple(self.cases.values())
        return hash_json(
            [
                {"id": case.definition.id, "content_sha256": case.content_sha256}
                for case in sorted(cases, key=lambda item: item.definition.id)
            ]
        )

    def requirement_manifest_hash(self) -> str:
        inventory = self.inventory.model_copy(
            update={
                "requirements": tuple(
                    sorted(
                        self.inventory.requirements,
                        key=lambda item: standard_location_sort_key(item.clause),
                    )
                )
            }
        )
        return hash_json(model_to_jsonable(inventory))

    def corpus_metrics(self) -> CorpusMetrics:
        parts = _standard_parts(self.anchor_index)
        anchor_parts = {anchor: (part.kind, part.id) for part in parts for anchor in part.anchors}
        requirement_links = {
            (requirement.id, anchor)
            for requirement in self.inventory.requirements
            for anchor in requirement.anchors
        }
        case_links = {
            (loaded.definition.id, requirement_id)
            for loaded in self.cases.values()
            for requirement_id in (
                loaded.definition.primary_requirement,
                *loaded.definition.related_requirements,
            )
        }

        requirement_breakdown: list[CorpusPartMetric] = []
        case_breakdown: list[CorpusPartMetric] = []
        for part in parts:
            identity = (part.kind, part.id)
            part_requirement_links = {
                link for link in requirement_links if anchor_parts[link[1]] == identity
            }
            covered_anchors = {anchor for _, anchor in part_requirement_links}
            waived_anchors = (set(part.anchors) & self.waived_anchors) - covered_anchors
            requirement_breakdown.append(
                CorpusPartMetric(
                    id=part.id,
                    kind=part.kind,
                    title=part.title,
                    coverage=CorpusRatio(
                        numerator=len(covered_anchors),
                        denominator=len(part.anchors) - len(waived_anchors),
                    ),
                    density=CorpusRatio(
                        numerator=len(part_requirement_links),
                        denominator=len(covered_anchors),
                    ),
                    waived=len(waived_anchors),
                )
            )

            part_requirements = {
                requirement.id
                for requirement in self.inventory.requirements
                if requirement.part == part.id
            }
            part_case_links = {link for link in case_links if link[1] in part_requirements}
            covered_requirements = {requirement_id for _, requirement_id in part_case_links}
            case_breakdown.append(
                CorpusPartMetric(
                    id=part.id,
                    kind=part.kind,
                    title=part.title,
                    coverage=CorpusRatio(
                        numerator=len(covered_requirements),
                        denominator=len(part_requirements),
                    ),
                    density=CorpusRatio(
                        numerator=len(part_case_links),
                        denominator=len(covered_requirements),
                    ),
                    waived=0,
                )
            )

        def summary(breakdown: list[CorpusPartMetric]) -> CorpusMetricSummary:
            return CorpusMetricSummary(
                coverage=CorpusRatio(
                    numerator=sum(part.coverage.numerator for part in breakdown),
                    denominator=sum(part.coverage.denominator for part in breakdown),
                ),
                density=CorpusRatio(
                    numerator=sum(part.density.numerator for part in breakdown),
                    denominator=sum(part.density.denominator for part in breakdown),
                ),
                breakdown=tuple(breakdown),
            )

        return CorpusMetrics(
            requirements=summary(requirement_breakdown),
            cases=summary(case_breakdown),
        )

    def case_identities(self, selected: Iterable[LoadedCase]) -> tuple[CaseIdentity, ...]:
        return tuple(
            CaseIdentity(id=item.definition.id, content_sha256=item.content_sha256)
            for item in selected
        )


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as stream:
            value = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise CatalogError(f"{path}: cannot read strict TOML: {error}") from error
    if not isinstance(value, dict):
        raise CatalogError(f"{path}: TOML root must be a table")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CatalogError(f"{path}: cannot read JSON: {error}") from error
    if not isinstance(value, dict):
        raise CatalogError(f"{path}: JSON root must be an object")
    return value


def _standard_index(path: Path) -> _StandardIndex:
    value = _read_json(path)
    if type(value.get("schema_version")) is not int or value["schema_version"] != 2:
        raise CatalogError(f"{path}: unsupported anchor index schema version")
    if value.get("edition") != "2023":
        raise CatalogError(f"{path}: anchor index must describe edition 2023")

    parts: list[_StandardPart] = []
    anchors: list[str] = []
    for section, kind, expected_ids in (
        ("clauses", StandardPartKind.CHAPTER, tuple(str(value) for value in range(1, 42))),
        ("annexes", StandardPartKind.ANNEX, tuple("ABCDEFGHIJKLMNOPQ")),
    ):
        entries = value.get(section)
        if not isinstance(entries, list) or len(entries) != len(expected_ids):
            raise CatalogError(f"{path}: {section} must contain {len(expected_ids)} entries")
        for entry, expected_id in zip(entries, expected_ids, strict=True):
            if not isinstance(entry, dict) or not isinstance(entry.get("anchors"), list):
                raise CatalogError(f"{path}: malformed {section} entry")
            part_id = entry.get("id")
            title = entry.get("title")
            if not isinstance(part_id, str) or not isinstance(title, str) or not title:
                raise CatalogError(f"{path}: malformed {section} identity")
            if part_id != expected_id:
                raise CatalogError(f"{path}: {section} IDs are not in canonical order")
            entry_anchors = entry["anchors"]
            if any(not isinstance(anchor, str) for anchor in entry_anchors):
                raise CatalogError(f"{path}: anchors must be strings")
            if type(entry.get("anchor_count")) is not int or entry["anchor_count"] != len(
                entry_anchors
            ):
                raise CatalogError(f"{path}: inconsistent {section} anchor count")
            parts.append(
                _StandardPart(
                    id=part_id,
                    kind=kind,
                    title=title,
                    anchors=tuple(entry_anchors),
                )
            )
            anchors.extend(entry_anchors)

    if len(set((part.kind, part.id) for part in parts)) != len(parts):
        raise CatalogError(f"{path}: duplicate standard parts")
    if len(frozenset(anchors)) != len(anchors):
        raise CatalogError(f"{path}: duplicate anchors")
    if type(value.get("anchor_count")) is not int or value["anchor_count"] != len(anchors):
        raise CatalogError(f"{path}: inconsistent total anchor count")

    raw_sections = value.get("sections")
    if not isinstance(raw_sections, list):
        raise CatalogError(f"{path}: sections must be an array")
    try:
        standard_sections = tuple(
            StandardSection.model_validate(section) for section in raw_sections
        )
    except ValidationError as error:
        raise CatalogError(f"{path}: malformed standard section: {error}") from error
    section_locations = [section.clause for section in standard_sections]
    if len(section_locations) != len(set(section_locations)):
        raise CatalogError(f"{path}: duplicate standard sections")
    if section_locations != sorted(section_locations, key=standard_location_sort_key):
        raise CatalogError(f"{path}: standard sections are not in canonical order")
    heading_locations = [anchor[1:-1].split(":", 3)[1] for anchor in anchors if ":H:" in anchor]
    if section_locations != heading_locations:
        raise CatalogError(f"{path}: standard sections do not match heading anchors")
    titles_by_clause = {section.clause: section.title for section in standard_sections}
    if any(titles_by_clause.get(part.id) != part.title for part in parts):
        raise CatalogError(f"{path}: standard part and section titles differ")
    return _StandardIndex(parts=tuple(parts), sections=standard_sections)


def _standard_parts(path: Path) -> tuple[_StandardPart, ...]:
    return _standard_index(path).parts


def _parse(path: Path, model_type: type[Any]) -> Any:
    try:
        return model_type.model_validate(_read_toml(path))
    except ValidationError as error:
        raise CatalogError(f"{path}: {error}") from error


def _load_requirements(root: Path, standard_index: _StandardIndex) -> RequirementInventory:
    standards = root / "standards"
    index = _parse(standards / "index.toml", StandardsIndex)
    requirements_directory = standards / "requirements"

    def requirement_path(part: str) -> Path:
        if part.isdigit():
            return requirements_directory / f"chapter-{int(part):02d}.toml"
        return requirements_directory / f"annex-{part}.toml"

    expected_paths = {requirement_path(part) for part in index.parts}
    actual_paths = {
        *requirements_directory.glob("chapter-*.toml"),
        *requirements_directory.glob("annex-*.toml"),
    }
    if actual_paths != expected_paths:
        missing = sorted(path.name for path in expected_paths - actual_paths)
        extra = sorted(path.name for path in actual_paths - expected_paths)
        raise CatalogError(
            f"{requirements_directory}: part index mismatch; missing={missing}, extra={extra}"
        )
    requirements: list[Requirement] = []
    for part in index.parts:
        path = requirement_path(part)
        document = _parse(path, RequirementPart)
        if document.part != part:
            raise CatalogError(f"{path}: declared part {document.part} does not match index {part}")
        requirements.extend(document.requirements)
    try:
        inventory = RequirementInventory(
            schema_version=index.schema_version,
            authority=index.authority,
            requirements=tuple(requirements),
        )
    except ValidationError as error:
        raise CatalogError(f"{standards}: {error}") from error

    available_anchors = frozenset(
        anchor for part in standard_index.parts for anchor in part.anchors
    )
    for requirement in inventory.requirements:
        unknown = [anchor for anchor in requirement.anchors if anchor not in available_anchors]
        if unknown:
            raise CatalogError(
                f"{requirement.id}: anchors absent from committed IEEE 1800-2023 index: "
                f"{', '.join(unknown)}"
            )
    return inventory


def _load_waivers(root: Path, standard_index: _StandardIndex) -> frozenset[str]:
    directory = root / "standards" / "waivers"

    def waiver_path(part: _StandardPart) -> Path:
        if part.kind is StandardPartKind.CHAPTER:
            return directory / f"chapter-{int(part.id):02d}.json"
        return directory / f"annex-{part.id}.json"

    expected_paths = {waiver_path(part) for part in standard_index.parts}
    actual_paths = {*directory.glob("chapter-*.json"), *directory.glob("annex-*.json")}
    if actual_paths != expected_paths:
        missing = sorted(path.name for path in expected_paths - actual_paths)
        extra = sorted(path.name for path in actual_paths - expected_paths)
        raise CatalogError(f"{directory}: part index mismatch; missing={missing}, extra={extra}")

    anchors_by_part = {part.id: frozenset(part.anchors) for part in standard_index.parts}
    waiver_ids: set[str] = set()
    waived_anchors: set[str] = set()
    for part in standard_index.parts:
        path = waiver_path(part)
        try:
            document = WaiverPart.model_validate(_read_json(path))
        except ValidationError as error:
            raise CatalogError(f"{path}: {error}") from error
        if document.part != part.id:
            raise CatalogError(
                f"{path}: declared part {document.part} does not match index {part.id}"
            )
        for waiver in document.waivers:
            if waiver.id in waiver_ids:
                raise CatalogError(f"{path}: duplicate waiver id {waiver.id}")
            waiver_ids.add(waiver.id)
            unknown = [
                anchor for anchor in waiver.anchors if anchor not in anchors_by_part[part.id]
            ]
            if unknown:
                raise CatalogError(
                    f"{waiver.id}: anchors absent from declared IEEE 1800-2023 part: "
                    f"{', '.join(unknown)}"
                )
            waived_anchors.update(waiver.anchors)
    return frozenset(waived_anchors)


def _validate_controlled_tags(
    inventory: RequirementInventory,
    cases: Iterable[CaseDefinition],
    registry: TagRegistry,
) -> None:
    allowed = {tag.id for tag in registry.tags}
    for owner, tags in (
        *((requirement.id, requirement.tags) for requirement in inventory.requirements),
        *((case.id, case.tags) for case in cases),
    ):
        unknown = sorted(set(tags) - allowed)
        if unknown:
            raise CatalogError(f"{owner}: unknown tags: {', '.join(unknown)}")


def _expand_suite(
    suite: SuiteDefinition,
    case_ids: tuple[str, ...],
    path: Path,
) -> tuple[str, ...]:
    selected: list[str] = []
    seen: set[str] = set()
    for pattern in suite.cases:
        matches = tuple(case_id for case_id in case_ids if fnmatchcase(case_id, pattern))
        if not matches:
            raise CatalogError(f"{path}: case pattern {pattern!r} matched no cases")
        for case_id in matches:
            if case_id not in seen:
                selected.append(case_id)
                seen.add(case_id)
    return tuple(selected)


def _source_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise CatalogError(f"{path}: source is not readable UTF-8: {error}") from error


def _case_hash(definition: CaseDefinition, directory: Path) -> str:
    digest_payload: list[dict[str, str]] = []
    for source in definition.sources:
        source_path = directory / source
        digest_payload.append({"path": source, "sha256": sha256_bytes(source_path.read_bytes())})
    for include_dir in definition.include_dirs:
        directory_path = directory / include_dir
        for path in sorted(item for item in directory_path.rglob("*") if item.is_file()):
            digest_payload.append(
                {
                    "path": path.relative_to(directory).as_posix(),
                    "sha256": sha256_bytes(path.read_bytes()),
                }
            )
    return hash_json({"metadata": model_to_jsonable(definition), "files": digest_payload})


def _case_path(directory: Path, relative: str, *, kind: str) -> Path:
    candidate = directory / relative
    cursor = directory
    for part in PurePosixPath(relative).parts:
        cursor /= part
        if cursor.is_symlink():
            raise CatalogError(f"{candidate}: {kind} cannot contain a symbolic link")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(directory)
    except ValueError as error:
        raise CatalogError(f"{candidate}: {kind} escapes case directory") from error
    return resolved


def _load_case(path: Path, requirements: dict[str, Requirement]) -> LoadedCase:
    definition = _parse(path, CaseDefinition)
    if path.is_symlink() or path.parent.is_symlink():
        raise CatalogError(f"{path}: case metadata and directory cannot be symbolic links")
    directory = path.parent.resolve()
    if directory.name != definition.id:
        raise CatalogError(f"{path}: id must equal containing directory name")
    if definition.primary_requirement not in requirements:
        raise CatalogError(f"{path}: unknown primary requirement")
    for related in definition.related_requirements:
        if related not in requirements:
            raise CatalogError(f"{path}: unknown related requirement {related}")

    requirement = requirements[definition.primary_requirement]
    if requirement.standard_revision is not definition.standard_revision:
        raise CatalogError(f"{path}: case and primary requirement revisions differ")
    for revision, applicability in definition.revision_applicability.items():
        requirement_rule = requirement.revision_applicability[revision].status
        if applicability in {
            Applicability.APPLICABLE,
            Applicability.SAME_RULE_DIFFERENT_CLAUSE,
        } and requirement_rule not in {
            Applicability.APPLICABLE,
            Applicability.SAME_RULE_DIFFERENT_CLAUSE,
        }:
            raise CatalogError(
                f"{path}: case claims {revision.value} applicability beyond its requirement"
            )

    source_paths: list[Path] = []
    all_source_text = ""
    for source in definition.sources:
        source_path = _case_path(directory, source, kind="source")
        if not source_path.is_file():
            raise CatalogError(f"{path}: missing or unsafe source {source}")
        if source_path.suffix not in {".sv", ".svh", ".v", ".vh"}:
            raise CatalogError(f"{path}: unsupported source extension {source_path.suffix}")
        source_paths.append(source_path)
        all_source_text += _source_text(source_path)

    for include_dir in definition.include_dirs:
        include_path = _case_path(directory, include_dir, kind="include directory")
        if not include_path.is_dir():
            raise CatalogError(f"{path}: missing or unsafe include directory {include_dir}")
        if any(item.is_symlink() for item in include_path.rglob("*")):
            raise CatalogError(f"{path}: include directory contains a symbolic link")

    anchor_source: str | None = None
    anchor_line: int | None = None
    if definition.oracle.kind is OracleKind.RUNTIME_PASS_MARKER:
        assert definition.oracle.marker is not None
        if all_source_text.count(definition.oracle.marker) != 1:
            raise CatalogError(f"{path}: runtime pass marker must occur exactly once")
        if "$fatal" not in all_source_text:
            raise CatalogError(f"{path}: simulation acceptance must be self-checking")
    elif definition.oracle.kind is OracleKind.DIAGNOSTIC_AT_ANCHOR:
        assert definition.oracle.anchor is not None
        occurrences: list[tuple[Path, int]] = []
        for source_path in source_paths:
            for line_number, line in enumerate(_source_text(source_path).splitlines(), 1):
                if definition.oracle.anchor in line:
                    occurrences.append((source_path, line_number))
        if len(occurrences) != 1:
            raise CatalogError(f"{path}: diagnostic anchor must occur exactly once")
        anchor_source = occurrences[0][0].relative_to(directory).as_posix()
        anchor_line = occurrences[0][1]
        if definition.target_phase is Phase.SIMULATE:
            assert definition.oracle.marker is not None
            if all_source_text.count(definition.oracle.marker) != 1:
                raise CatalogError(
                    f"{path}: runtime diagnostic success marker must occur exactly once"
                )

    if definition.target_phase is Phase.SIMULATE and "$finish" not in all_source_text:
        raise CatalogError(f"{path}: runtime case must terminate explicitly")
    return LoadedCase(
        definition=definition,
        directory=directory,
        metadata_path=path.resolve(),
        anchor_source=anchor_source,
        anchor_line=anchor_line,
        content_sha256=_case_hash(definition, directory),
    )


def load_catalog(root: Path, *, anchor_index: Path | None = None) -> Catalog:
    root = root.resolve()
    anchor_index = (anchor_index or root / "standards" / "ieee-1800-2023-anchors.json").resolve()
    standard_index = _standard_index(anchor_index)
    inventory = _load_requirements(root, standard_index)
    waived_anchors = _load_waivers(root, standard_index)
    tags = _parse(root / "standards" / "tags.toml", TagRegistry)
    requirements = {item.id: item for item in inventory.requirements}

    loaded_cases: dict[str, LoadedCase] = {}
    for metadata_path in sorted((root / "cases").glob("*/case.toml")):
        loaded = _load_case(metadata_path, requirements)
        if loaded.definition.id in loaded_cases:
            raise CatalogError(f"duplicate case id {loaded.definition.id}")
        loaded_cases[loaded.definition.id] = loaded
    if not loaded_cases:
        raise CatalogError("no cases found")
    _validate_controlled_tags(
        inventory,
        (loaded.definition for loaded in loaded_cases.values()),
        tags,
    )

    suites: dict[str, SuiteDefinition] = {}
    suite_cases: dict[str, tuple[str, ...]] = {}
    case_ids = tuple(sorted(loaded_cases))
    for suite_path in sorted((root / "suites").glob("*.toml")):
        suite = _parse(suite_path, SuiteDefinition)
        if suite.id in suites:
            raise CatalogError(f"duplicate suite id {suite.id}")
        suites[suite.id] = suite
        suite_cases[suite.id] = _expand_suite(suite, case_ids, suite_path)
    if "all" not in suites or set(suite_cases["all"]) != set(loaded_cases):
        raise CatalogError("suite 'all' must contain every case exactly once")
    if "smoke" not in suites:
        raise CatalogError("suite 'smoke' is required")
    smoke = [loaded_cases[item].definition for item in suite_cases["smoke"]]
    smoke_checks = {
        "positive": any(item.expectation is Expectation.ACCEPT for item in smoke),
        "negative": any(item.expectation is Expectation.REJECT for item in smoke),
        "diagnostic": any(item.expectation is Expectation.DIAGNOSTIC for item in smoke),
        "runtime": any(item.target_phase is Phase.SIMULATE for item in smoke),
        "multi-file": any(len(item.sources) > 1 for item in smoke),
    }
    if not all(smoke_checks.values()):
        missing = sorted(name for name, present in smoke_checks.items() if not present)
        raise CatalogError(f"smoke suite misses required paths: {', '.join(missing)}")

    tools_directory = root / "tools"
    index_path = tools_directory / "tools.toml"

    def contains_symlink(base: Path, candidate: Path) -> bool:
        current = base
        if current.is_symlink():
            return True
        for part in candidate.relative_to(base).parts:
            current /= part
            if current.is_symlink():
                return True
        return False

    try:
        index = ToolIndex.model_validate(_read_toml(index_path))
    except ValidationError as error:
        raise CatalogError(f"{index_path}: {error}") from error

    def manifest_path(relative: str) -> Path:
        candidate = tools_directory / relative
        resolved = candidate.resolve()
        try:
            resolved.relative_to(tools_directory.resolve())
        except ValueError as error:
            raise CatalogError(f"tool manifest escapes tools directory: {relative}") from error
        if contains_symlink(tools_directory, candidate) or not resolved.is_file():
            raise CatalogError(f"missing or unsafe tool manifest: {relative}")
        return resolved

    def normalized_path(manifest: Path, relative: str, *, required: bool, tool_id: str) -> str:
        candidate = manifest.parent / relative
        resolved = candidate.resolve()
        try:
            resolved.relative_to(manifest.parent)
            normalized = resolved.relative_to(root).as_posix()
        except ValueError as error:
            raise CatalogError(f"tool {tool_id}: referenced path escapes tool directory") from error
        if contains_symlink(manifest.parent, candidate) or (required and not resolved.is_file()):
            raise CatalogError(f"tool {tool_id}: missing or unsafe referenced file {relative}")
        return normalized

    definitions: list[ToolDefinition] = []
    for relative in index.manifests:
        path = manifest_path(relative)
        manifest = _parse(path, ToolManifest)
        dockerfile = (
            normalized_path(path, manifest.dockerfile, required=True, tool_id=manifest.id)
            if manifest.dockerfile is not None
            else None
        )
        recipe_files = tuple(
            normalized_path(path, item, required=True, tool_id=manifest.id)
            for item in manifest.recipe_files
        )
        runner_config = (
            normalized_path(path, manifest.runner_config, required=False, tool_id=manifest.id)
            if manifest.runner_config is not None
            else None
        )
        value = manifest.model_dump(exclude={"schema_version"})
        value.update(
            dockerfile=dockerfile,
            recipe_files=recipe_files,
            runner_config=runner_config,
        )
        definitions.append(ToolDefinition.model_validate(value))

    try:
        tools = ToolRegistry(schema_version=2, tools=tuple(definitions))
    except ValidationError as error:
        raise CatalogError(f"{index_path}: {error}") from error
    from svtorture.adapters.registry import AdapterError, adapter_for

    for tool in tools.tools:
        try:
            adapter_for(tool.adapter, diagnostic_rules=tool.diagnostic_rules)
        except AdapterError as error:
            raise CatalogError(f"tool {tool.id}: {error}") from error
    return Catalog(
        root=root,
        anchor_index=anchor_index,
        inventory=inventory,
        tags=tags,
        cases=loaded_cases,
        suites=suites,
        suite_cases=suite_cases,
        tools=tools,
        standard_sections=standard_index.sections,
        waived_anchors=waived_anchors,
    )


def repository_identity(root: Path) -> RepositoryIdentity:
    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    head = git("rev-parse", "HEAD")
    commit = head.stdout.strip() if head.returncode == 0 else "unborn"
    status = git("status", "--porcelain=v1", "--untracked-files=all")
    dirty = status.returncode != 0 or bool(status.stdout)
    return RepositoryIdentity(commit=commit, dirty=dirty)


def write_json_schema(root: Path, output: Path) -> None:
    """Write externally consumable model schemas deterministically."""

    from svtorture.dashboard_models import (
        CampaignCatalog,
        CampaignEvidenceShard,
        CampaignManifest,
        CampaignSummary,
        CampaignTrends,
        CampaignVerdicts,
        DashboardIndex,
    )
    from svtorture.models import Campaign, NormalizedResult, WaiverPart  # local to avoid cycles

    tag_values = [tag.id for tag in _parse(root / "standards" / "tags.toml", TagRegistry).tags]
    case_schema = CaseDefinition.model_json_schema()
    case_schema["properties"]["tags"]["items"]["enum"] = tag_values
    requirements_schema = RequirementInventory.model_json_schema()
    requirements_schema["$defs"]["Requirement"]["properties"]["tags"]["items"]["enum"] = tag_values
    part_schema = RequirementPart.model_json_schema()
    part_schema["$defs"]["Requirement"]["properties"]["tags"]["items"]["enum"] = tag_values
    dashboard_schemas = {
        "campaign-catalog.schema.json": CampaignCatalog.model_json_schema(),
        "campaign-evidence.schema.json": CampaignEvidenceShard.model_json_schema(),
        "campaign-manifest.schema.json": CampaignManifest.model_json_schema(),
        "campaign-summary.schema.json": CampaignSummary.model_json_schema(),
        "campaign-trends.schema.json": CampaignTrends.model_json_schema(),
        "campaign-verdicts.schema.json": CampaignVerdicts.model_json_schema(),
        "dashboard-index.schema.json": DashboardIndex.model_json_schema(),
    }
    for name, schema in dashboard_schemas.items():
        schema["$id"] = name
        required = schema.setdefault("required", [])
        schema["required"] = ["schema_version", "kind", *required]
    trends_schema = dashboard_schemas["campaign-trends.schema.json"]
    trends_schema.pop("$defs", None)
    trends_schema["properties"]["campaigns"]["items"] = {"$ref": "campaign-summary.schema.json"}
    schemas = {
        "campaign.schema.json": Campaign.model_json_schema(),
        **dashboard_schemas,
        "case.schema.json": case_schema,
        "requirement-part.schema.json": part_schema,
        "requirements.schema.json": requirements_schema,
        "result.schema.json": NormalizedResult.model_json_schema(),
        "standards-index.schema.json": StandardsIndex.model_json_schema(),
        "suite.schema.json": SuiteDefinition.model_json_schema(),
        "tags.schema.json": TagRegistry.model_json_schema(),
        "tool.schema.json": ToolManifest.model_json_schema(),
        "tools.schema.json": ToolIndex.model_json_schema(),
        "waiver-part.schema.json": WaiverPart.model_json_schema(),
    }
    output.mkdir(parents=True, exist_ok=True)
    for path in output.glob("*.json"):
        if path.name not in schemas:
            path.unlink()
    for name, value in schemas.items():
        (output / name).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def mvp_audit(catalog: Catalog) -> dict[str, int]:
    """Enforce the seed-corpus composition promised by the MVP brief."""

    definitions = [item.definition for item in catalog.cases.values()]
    counts = {
        "cases": len(definitions),
        "chapters": len(
            {
                requirement.part
                for item in definitions
                if (requirement := catalog.requirements[item.primary_requirement]).part.isdigit()
            }
        ),
        "simulation_acceptance": sum(
            item.target_phase is Phase.SIMULATE and item.expectation is Expectation.ACCEPT
            for item in definitions
        ),
        "static_acceptance": sum(
            item.target_phase is not Phase.SIMULATE and item.expectation is Expectation.ACCEPT
            for item in definitions
        ),
        "rejection": sum(item.expectation is Expectation.REJECT for item in definitions),
        "diagnostic": sum(item.expectation is Expectation.DIAGNOSTIC for item in definitions),
        "multi_file": sum(len(item.sources) > 1 for item in definitions),
        "preprocessing": sum(
            bool(item.include_dirs or item.defines) or any("preprocess" in tag for tag in item.tags)
            for item in definitions
        ),
    }
    minimums = {
        "chapters": 8,
        "simulation_acceptance": 4,
        "static_acceptance": 2,
        "rejection": 2,
        "diagnostic": 1,
        "multi_file": 1,
        "preprocessing": 1,
    }
    if not 10 <= counts["cases"] <= 12:
        raise CatalogError("MVP seed corpus must contain 10-12 cases")
    for name, minimum in minimums.items():
        if counts[name] < minimum:
            raise CatalogError(f"MVP seed corpus needs at least {minimum} {name} cases")
    if not any("four-state" in item.tags for item in definitions):
        raise CatalogError("MVP seed corpus must exercise four-state semantics")
    if not any("generate" in item.tags and item.top for item in definitions):
        raise CatalogError("MVP seed corpus must exercise explicit generate hierarchy")
    if not any(set(item.tags) & {"sizing", "scheduling", "copy-out"} for item in definitions):
        raise CatalogError("MVP seed corpus must exercise a subtle semantic area")
    return counts
