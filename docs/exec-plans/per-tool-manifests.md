# Colocate tool manifests and local runner configuration

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the repository's `exec-plan` skill.

## Purpose / Big Picture

After this change, every simulator integration is understandable from one directory under `tools/`. A contributor adding Xcelium can copy the VCS directory shape, add one entry to the thin `tools/tools.toml` index, and keep machine-specific runner configuration beside the committed example without exposing it to Git. A user can verify the result with `just metadata`, configure VCS with `just runner-config vcs`, and run one combined campaign with `just all`.

The observable layout is `tools/<name>/tool.toml` plus that integration's Dockerfile, scripts, README, and optional `runner.example.toml`. The ignored `runner.toml` exists only on machines that can run a commercial tool. Diagnostic fallback rules are embedded in the owning `tool.toml` rather than stored in a shared root file.

## Non-Goals

This work does not add Xcelium or another simulator, change conformance evaluation, change the version-2 execution-plan/wrapper request protocol, publish commercial results, introduce recursive manifest includes, or create a plugin system. It does not move Python adapter implementations out of `src/svtorture/adapters/`.

## Progress

- [x] (2026-07-30 09:48Z) Inspected the registry, diagnostic fallback, commercial runner, replay, schema, documentation, and test execution paths.
- [x] (2026-07-30 09:48Z) Chose a minimal per-tool manifest and runner layout and recorded it in this plan.
- [x] (2026-07-30 09:50Z) Added red tests for strict thin-index loading, manifest-local paths, embedded diagnostic rules, and per-tool runner loading; initial collection failed on the intentionally absent APIs.
- [x] (2026-07-30 09:56Z) Implemented strict models and catalog loading while preserving the flattened `Catalog.tools` runtime API.
- [x] (2026-07-30 09:59Z) Migrated all tool metadata, VCS runner examples, diagnostic rules, ignore policy, commands, and documentation.
- [x] (2026-07-30 10:00Z) Regenerated public JSON Schema snapshots and passed focused tests.
- [x] (2026-07-30 10:09Z) Exercised commercial and combined 48-result campaigns and refreshed the local dashboard from the unified campaign.
- [x] (2026-07-30 10:11Z) Ran `just smoke` and `just ci`; all deterministic, frontend, Docker-fake, and real-tool checks passed.
- [x] (2026-07-30 10:22Z) Completed parallel code, architecture, and documentation review; fixed contract versioning, symlink boundaries, dynamic campaign membership, and documentation findings.
- [x] (2026-07-30 10:54Z) Ran two independent control reviews; removed all compatibility paths as explicitly required and fixed exact dashboard version validation, obsolete target aliases, and strict manifest shape.
- [x] (2026-07-30 10:56Z) Re-ran `just ci`, audited tracked and ignored files, and confirmed 157 unit, 11 Docker, and 67 dashboard tests pass without leaking local runner configuration.
- [x] (2026-07-30 10:58Z) Committed all requested work as `feat(tools): add per-tool integration manifests` and verified the resulting commit.

## Surprises & Discoveries

- Observation: diagnostic fallback policy is currently global in location but contains only two VCS-specific rules.
  Evidence: `tools/diagnostic-rules.toml` has two entries and both use `tool = "vcs"`.

- Observation: runtime and campaign code already consume a flattened `ToolRegistry`; only catalog construction needs to understand per-tool manifests if loaded paths are normalized back to repository-relative paths.
  Evidence: `Catalog.tools.tool(id)` is the downstream interface, and image recipe hashing reads `ToolDefinition.dockerfile` and `recipe_files` as repository-relative paths.

- Observation: a global `SVTORTURE_TOOL_CONFIG` override cannot naturally identify several per-tool runner files.
  Evidence: `load_private_config()` currently parses one aggregate file containing multiple `[[wrappers]]` entries.

- Observation: the latest Slang upstream started deriving dependency URLs from the Git remote and exposed that its Docker build invoked CMake outside `/src`.
  Evidence: the first `just all` failed cloning `fmtlib/fmt.git`; adding `cd /src` made the current upstream build and the 48-result combined campaign pass.

- Observation: review found that adding fields to serialized `ToolDefinition` requires a new exact campaign contract version.
  Evidence: campaign and dashboard dataset models now require version 5; no compatibility path for the replaced metadata layout is retained.

- Observation: checking only a referenced file's final component does not prevent an intermediate directory symlink from crossing a tool package boundary.
  Evidence: a regression test now replaces `tools/vcs` with a symlink and catalog loading rejects it.

## Decision Log

- Decision: keep `tools/tools.toml` as a strict, non-recursive index containing `manifests = [...]`.
  Rationale: one explicit list is easy to audit and avoids directory scanning, implicit ordering, and plugin complexity.
  Date/Author: 2026-07-30 / Pi

- Decision: name the committed descriptor `tool.toml` and the ignored machine-local file `runner.toml`, with `runner.example.toml` committed beside it.
  Rationale: `tool.toml` describes portable integration metadata; `runner.toml` clearly describes how this machine launches a licensed tool without using the vague security-oriented name `private.toml`.
  Date/Author: 2026-07-30 / Pi

- Decision: embed the small case-specific diagnostic fallback array in the owning `tool.toml`.
  Rationale: the rules are tool metadata, only VCS currently needs two, and a separate file adds indirection without a current requirement.
  Date/Author: 2026-07-30 / Pi

- Decision: resolve Dockerfile, recipe, and runner-config paths relative to each `tool.toml`, then normalize them to repository-relative paths in runtime `ToolDefinition` objects.
  Rationale: each directory becomes movable and self-contained while image, campaign, replay, and publication code retain their existing API.
  Date/Author: 2026-07-30 / Pi

- Decision: keep the existing `local-wrapper` execution backend and version-2 JSON protocol names.
  Rationale: the requested change concerns configuration/layout; renaming a serialized execution contract would be unrelated and break campaign compatibility.
  Date/Author: 2026-07-30 / Pi

- Decision: remove the aggregate config format and `SVTORTURE_TOOL_CONFIG` override rather than support two layouts.
  Rationale: retaining either path would preserve the global indirection being removed without a current requirement.
  Date/Author: 2026-07-30 / Pi

- Decision: require campaign and dashboard dataset contract version 5 exactly.
  Rationale: per-tool diagnostic and runner-locator fields are serialized evidence metadata, and the user explicitly rejected backward compatibility for this change.
  Date/Author: 2026-07-30 / Pi

- Decision: reject the replaced monolithic registry and aggregate runner formats everywhere, including replay.
  Rationale: one current layout is simpler and is the explicit acceptance criterion.
  Date/Author: 2026-07-30 / Pi

- Decision: derive `public`, `commercial`, and `all` Just selections from catalog metadata printed by `svtorture list tools`.
  Rationale: adding a future indexed Xcelium manifest must automatically affect targets claiming to run every commercial or available tool; shell selection is the smallest solution and tool IDs are strictly validated.
  Date/Author: 2026-07-30 / Pi

## Outcomes & Retrospective

The per-tool layout, runner migration, embedded diagnostics, dynamic campaign targets, and exact version-5 contracts are implemented without backward-compatibility paths. VCS completed all 12 cases, the combined campaign completed 48 tool-case executions, and the dashboard dataset contains that unified evidence. Two control reviews were resolved and final `just ci` passed with 157 unit, 11 Docker, and 67 dashboard tests. The work is committed as `feat(tools): add per-tool integration manifests`.

## Context and Orientation

`tools/tools.toml` is currently a monolithic registry containing every `ToolDefinition`. `src/svtorture/catalog.py::load_catalog` parses it directly into `ToolRegistry`, checks a shared `tools/diagnostic-rules.toml`, validates recipe files, and exposes the flattened registry as `Catalog.tools`. Adapters are selected by `src/svtorture/adapters/registry.py::adapter_for`, which currently reparses the shared diagnostic TOML and passes internal `DiagnosticFallback` values into adapters.

A diagnostic fallback is a reviewed rule used only when simulator output names a relevant message but omits a source location. It does not decide conformance; `src/svtorture/evaluator.py` remains the only conformance decision owner.

Commercial execution is represented by the serialized `local-wrapper` backend. `src/svtorture/campaign.py::load_private_config` currently reads one ignored `tools/private.toml` containing multiple wrappers. `src/svtorture/cli.py` uses that loader for normal runs and doctor output, while `src/svtorture/reproduce.py` uses it during replay. `src/svtorture/executor.py` writes a version-2 JSON request and invokes the configured command. This request protocol remains unchanged.

JSON Schema snapshots under `schemas/` are generated by `just schemas`; they must never be edited manually. `schemas/tools.schema.json` should describe the new thin index, while a new `schemas/tool.schema.json` should describe one committed `tool.toml`. Campaign schemas continue embedding normalized `ToolDefinition` metadata.

The working tree already contains requested improvements to `justfile` and `README.md` adding `public`, `commercial`, and combined `all` campaign targets, plus a necessary `tools/slang/Dockerfile` working-directory fix. Those changes are part of the final requested commit and must not be discarded.

## Open Questions

There are no unresolved design questions. If implementation reveals a publication invariant not visible during research, record it here and choose the smallest behavior that preserves evidence integrity without retaining replaced formats.

## Plan of Work

First, add model and catalog tests that describe the new file layout before production code supports it. The tests will require a thin index, one `tool.toml` per registered integration, relative recipe normalization, duplicate/unsafe/missing manifest rejection, embedded VCS fallback behavior, and strict rejection of malformed fields. Add runner tests requiring a missing per-tool file to mean unavailable, a valid `runner.toml` to load one command, and malformed or aggregate content to fail.

Second, add strict Pydantic models in `src/svtorture/models.py`: a thin tool index, a diagnostic-rule value, a flat per-tool manifest, and a single runner configuration. Keep `ToolDefinition` as the normalized campaign/runtime value and `ToolRegistry` as the flattened runtime collection. Add `diagnostic_rules` and optional normalized `runner_config` to `ToolDefinition`, enforcing that only local-wrapper tools can name a runner configuration.

Third, change `src/svtorture/catalog.py` to parse `tools/tools.toml`, resolve each listed manifest safely relative to `tools/`, reject symlinks/escapes/missing files and duplicate IDs, normalize manifest-local recipe and runner paths to repository-relative strings, construct the existing flattened registry, and validate adapter IDs using already parsed diagnostic values. Change `src/svtorture/adapters/registry.py` and the small call sites in campaign, CLI, and replay so they consume validated per-tool rules instead of a shared path.

Fourth, replace the aggregate runner loader with `load_runner_config(root, tool)`. It reads the optional normalized path from the tool definition, returns no runner when the file is absent, rejects malformed data, and creates the existing runtime wrapper shape without a redundant tool ID. Normal runs and replay use the same host-root configuration, and doctor reports readiness per commercial tool. Replace `private-config` with generic `runner-config <tool>`.

Fifth, split the monolithic metadata into `tools/*/tool.toml`, embed the two VCS diagnostic rules, add `tools/vcs/runner.example.toml`, migrate the current ignored VCS config to `tools/vcs/runner.toml`, update `.gitignore`, and delete obsolete aggregate files. Update only documentation that names the old layout or commands.

Finally, regenerate schemas, run focused tests, execute VCS and the combined campaign as end-to-end proof, refresh the ignored dashboard dataset from the combined campaign if necessary, run repository quality gates, inspect ignored/tracked status for secret leakage, and create one Conventional Commit.

### Concrete Steps

All commands run from the repository root.

Add tests, then run focused red tests:

    uv run pytest -q tests/test_catalog_models.py tests/test_campaign_metric.py tests/test_adapters.py tests/test_cli.py tests/test_reproduce.py

Before implementation, new layout/runner tests must fail for missing models or old behavior. After implementation, the same command must pass.

Regenerate schemas only through:

    just schemas

Validate deterministic repository behavior:

    just smoke

Exercise the licensed and combined paths when the local runner is configured:

    just commercial
    just all

The combined run must print one campaign containing Slang, Icarus, Verilator, and VCS. Build and verify the dashboard dataset from that one campaign:

    just dashboard-build ".svtorture/campaigns/<combined-id>/campaign.json"

Run the broad local gate if Docker and the network are available:

    just ci

Before committing, verify:

    git diff --check
    git status --short --ignored
    git diff -- . ':!schemas/*.json'

No `runner.toml`, license value, `.svtorture/` artifact, or dashboard dataset may be staged. Commit using a Conventional Commit subject reflecting the per-tool manifest feature.

### Validation and Acceptance

Acceptance is behavioral:

1. `tools/tools.toml` contains only its schema version and an explicit manifest list; every listed directory contains a strict `tool.toml`.
2. Loading the catalog returns the same five tool IDs and normalized repository-relative recipe paths as before.
3. VCS diagnostic fallback tests still identify the two locationless diagnostics, with no global diagnostic file.
4. `tools/vcs/runner.example.toml` is tracked, `tools/vcs/runner.toml` is ignored, and `just runner-config vcs` creates the latter without overwriting it.
5. With the local runner file present, doctor reports VCS available and `just commercial` executes all current cases. Without it, VCS remains registered and a selected run records unavailable evidence rather than invalidating the catalog.
6. `just all` produces one campaign with all four real tools on this machine.
7. Generated schemas, focused tests, and `just smoke` pass; `just ci` passes when external Docker/network inputs remain available.
8. The final commit contains no machine-local runner file, credentials, licensed artifacts, campaign files, or dashboard output.

### Idempotence and Recovery

Catalog and schema generation are deterministic. `just runner-config vcs` must use a non-overwriting copy so rerunning it preserves local settings. Campaign commands create new ignored campaign directories and can be retried safely. If an upstream image build fails, retain the source changes, record the evidence in `Surprises & Discoveries`, and retry after fixing only a reproducible integration issue. The old ignored `tools/private.toml` can be removed after its command has been copied into `tools/vcs/runner.toml`; it contains no license value in the current checkout.

### Artifacts and Notes

The pre-refactor combined campaign proved the intended execution topology:

    campaign: .svtorture/campaigns/20260730T091838Z-3faa477d4ad15dbc/campaign.json
    summary: conforming=40, nonconforming=1, unsupported-capability=7

The current machine's VCS runner reports:

    vcs script version : X-2025.06

### Interfaces and Dependencies

Use only Python's existing `tomllib`, `pathlib`, and Pydantic dependency. Do not add packages.

At completion, `src/svtorture/models.py` must expose strict equivalents of:

    class ToolIndex(StrictModel):
        schema_version: MetadataSchemaVersion
        manifests: tuple[str, ...]

    class DiagnosticRule(StrictModel):
        case: str
        contains: str
        severity: str | None = None

    class ToolManifest(ToolDefinition):
        schema_version: MetadataSchemaVersion

    class RunnerConfig(StrictModel):
        schema_version: MetadataSchemaVersion
        command: tuple[str, ...]
        environment_allowlist: tuple[str, ...] = ()

`load_catalog()` continues returning `Catalog.tools: ToolRegistry`. Add `load_runner_config(root: Path, tool: ToolDefinition) -> RunnerConfig | None` or an equally small runtime-compatible form. `adapter_for()` accepts already validated diagnostic rules and never opens metadata files itself.

Revision note (2026-07-30): Initial plan created after tracing all registry, runner, diagnostic, replay, schema, and documentation paths. It incorporates the user's requested per-tool package layout and the prior uncommitted campaign-target work so implementation can proceed from this document alone.

Revision note (2026-07-30): Updated after implementation, end-to-end execution, CI, and multi-lane review. Added the symlink-boundary, dynamic-selection, and contract-version decisions required by review evidence.

Revision note (2026-07-30): Removed all backward-compatibility work after the user explicitly required the new metadata and runner layout to be the only supported contract.

Revision note (2026-07-30): Recorded final control-review fixes and complete CI/audit evidence before commit.

Revision note (2026-07-30): Marked the plan complete after creating and verifying the requested Conventional Commit.
