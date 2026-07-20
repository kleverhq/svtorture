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
    Expectation,
    OracleKind,
    Phase,
    RepositoryIdentity,
    Requirement,
    RequirementChapter,
    RequirementInventory,
    StandardsIndex,
    SuiteDefinition,
    TagRegistry,
    ToolRegistry,
    model_to_jsonable,
)


class CatalogError(ValueError):
    """The corpus or registry cannot be trusted."""


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
    inventory: RequirementInventory
    tags: TagRegistry
    cases: dict[str, LoadedCase]
    suites: dict[str, SuiteDefinition]
    suite_cases: dict[str, tuple[str, ...]]
    tools: ToolRegistry

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
        return hash_json(model_to_jsonable(self.inventory))

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


def _annotated_standard_anchors(standards: Path) -> frozenset[str]:
    path = standards / "ieee-1800-2023-annotated" / "anchors.json"
    value = _read_json(path)
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise CatalogError(f"{path}: unsupported anchor index schema version")
    if value.get("edition") != "2023":
        raise CatalogError(f"{path}: anchor index must describe edition 2023")

    anchors: list[str] = []
    for section in ("clauses", "annexes"):
        entries = value.get(section)
        if not isinstance(entries, list):
            raise CatalogError(f"{path}: {section} must be an array")
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("anchors"), list):
                raise CatalogError(f"{path}: malformed {section} entry")
            entry_anchors = entry["anchors"]
            if any(not isinstance(anchor, str) for anchor in entry_anchors):
                raise CatalogError(f"{path}: anchors must be strings")
            if type(entry.get("anchor_count")) is not int or entry["anchor_count"] != len(
                entry_anchors
            ):
                raise CatalogError(f"{path}: inconsistent {section} anchor count")
            anchors.extend(entry_anchors)

    unique = frozenset(anchors)
    if len(unique) != len(anchors):
        raise CatalogError(f"{path}: duplicate anchors")
    if type(value.get("anchor_count")) is not int or value["anchor_count"] != len(anchors):
        raise CatalogError(f"{path}: inconsistent total anchor count")
    return unique


def _parse(path: Path, model_type: type[Any]) -> Any:
    try:
        return model_type.model_validate(_read_toml(path))
    except ValidationError as error:
        raise CatalogError(f"{path}: {error}") from error


def _load_requirements(root: Path) -> RequirementInventory:
    standards = root / "standards"
    index = _parse(standards / "index.toml", StandardsIndex)
    requirements_directory = standards / "requirements"
    expected_paths = {
        requirements_directory / f"chapter-{chapter:02d}.toml" for chapter in index.chapters
    }
    actual_paths = set(requirements_directory.glob("chapter-*.toml"))
    if actual_paths != expected_paths:
        missing = sorted(path.name for path in expected_paths - actual_paths)
        extra = sorted(path.name for path in actual_paths - expected_paths)
        raise CatalogError(
            f"{requirements_directory}: chapter index mismatch; missing={missing}, extra={extra}"
        )
    requirements: list[Requirement] = []
    for chapter, path in zip(index.chapters, sorted(expected_paths), strict=True):
        document = _parse(path, RequirementChapter)
        if document.chapter != chapter:
            raise CatalogError(
                f"{path}: declared chapter {document.chapter} does not match index {chapter}"
            )
        requirements.extend(document.requirements)
    try:
        inventory = RequirementInventory(
            schema_version=index.schema_version,
            authority=index.authority,
            requirements=tuple(requirements),
        )
    except ValidationError as error:
        raise CatalogError(f"{standards}: {error}") from error

    available_anchors = _annotated_standard_anchors(standards)
    for requirement in inventory.requirements:
        unknown = [anchor for anchor in requirement.anchors if anchor not in available_anchors]
        if unknown:
            raise CatalogError(
                f"{requirement.id}: anchors absent from pinned annotated standard: "
                f"{', '.join(unknown)}"
            )
    return inventory


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


def load_catalog(root: Path) -> Catalog:
    root = root.resolve()
    inventory = _load_requirements(root)
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

    tools = _parse(root / "tools" / "tools.toml", ToolRegistry)
    rules_path = root / "tools" / "diagnostic-rules.toml"
    if not rules_path.is_file() or rules_path.is_symlink():
        raise CatalogError("missing or unsafe adapter diagnostic rules")
    from svtorture.adapters.registry import AdapterError, adapter_for

    for tool in tools.tools:
        try:
            adapter_for(tool.adapter, rules_path=rules_path)
        except AdapterError as error:
            raise CatalogError(f"tool {tool.id}: {error}") from error
        recipe_paths = (
            *((tool.dockerfile,) if tool.dockerfile is not None else ()),
            *tool.recipe_files,
        )
        for relative in recipe_paths:
            recipe_path = (root / relative).resolve()
            try:
                recipe_path.relative_to(root)
            except ValueError as error:
                raise CatalogError(f"tool {tool.id}: image recipe escapes repository") from error
            if not recipe_path.is_file() or recipe_path.is_symlink():
                raise CatalogError(f"tool {tool.id}: missing or unsafe recipe file {relative}")
    return Catalog(
        root=root,
        inventory=inventory,
        tags=tags,
        cases=loaded_cases,
        suites=suites,
        suite_cases=suite_cases,
        tools=tools,
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

    from svtorture.models import Campaign, NormalizedResult  # local to avoid cycles

    tag_values = [tag.id for tag in _parse(root / "standards" / "tags.toml", TagRegistry).tags]
    case_schema = CaseDefinition.model_json_schema()
    case_schema["properties"]["tags"]["items"]["enum"] = tag_values
    requirements_schema = RequirementInventory.model_json_schema()
    requirements_schema["$defs"]["Requirement"]["properties"]["tags"]["items"]["enum"] = tag_values
    chapter_schema = RequirementChapter.model_json_schema()
    chapter_schema["$defs"]["Requirement"]["properties"]["tags"]["items"]["enum"] = tag_values
    schemas = {
        "campaign.schema.json": Campaign.model_json_schema(),
        "case.schema.json": case_schema,
        "requirement-chapter.schema.json": chapter_schema,
        "requirements.schema.json": requirements_schema,
        "result.schema.json": NormalizedResult.model_json_schema(),
        "standards-index.schema.json": StandardsIndex.model_json_schema(),
        "suite.schema.json": SuiteDefinition.model_json_schema(),
        "tags.schema.json": TagRegistry.model_json_schema(),
        "tools.schema.json": ToolRegistry.model_json_schema(),
    }
    output.mkdir(parents=True, exist_ok=True)
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
            {catalog.requirements[item.primary_requirement].chapter for item in definitions}
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
