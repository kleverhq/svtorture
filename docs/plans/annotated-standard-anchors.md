# Adopt the pinned annotated IEEE 1800-2023 corpus

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the `exec-plan` skill.

## Purpose / Big Picture

After this change, every requirement cites one or more stable anchors from the repository-pinned annotated IEEE 1800-2023 corpus instead of carrying an informal `paragraph_anchor` sentence. A contributor can initialize the submodule, inspect the exact anchored text, and run `just smoke`; catalog loading will reject citations that are absent from the pinned `anchors.json` index. The generated JSON schemas and dashboard will expose the new `anchors` list.

## Non-Goals

This change does not rewrite case stimuli or oracles, change historical 2012/2017 applicability judgments, edit the annotated corpus, or add a second standards extraction mechanism. The parent repository only pins and consumes the external corpus.

## Progress

- [x] (2026-07-20 11:20Z) Inspected requirement models, catalog loading, generated schemas, dashboard consumers, workflows, documentation, and all twelve seed cases.
- [x] (2026-07-20 11:20Z) Inspected annotated corpus commit `e63112d2a9dfb4586d0e33769721238c8c619ece` and mapped each seed requirement to exact anchor candidates.
- [x] (2026-07-20 11:25Z) Added the annotated repository as `standards/ieee-1800-2023-annotated` and configured automated checkouts with non-persisted cross-repository credentials.
- [x] (2026-07-20 11:34Z) Replaced `paragraph_anchor` with a nonempty, unique `anchors` tuple and cross-validated every citation against the pinned anchor index.
- [x] (2026-07-20 11:37Z) Migrated seed metadata, dashboard consumers, generated schema-version-2 snapshots, replay checkout handling, tests, and durable contributor guidance.
- [x] (2026-07-20 12:10Z) Passed `just smoke`, all 92 non-Docker tests, dashboard production build, `just precommit`, diff checks, focused citation review, and implementation review.
- [x] (2026-07-20 13:40Z) Vendored the runtime anchor index, removed every normal submodule dependency, passed 93 non-Docker tests, and passed `just smoke` plus `just precommit` with the submodule directory physically absent.

## Surprises & Discoveries

- Observation: Anonymous HTTPS access to the annotated repository returns 404, while the configured GitHub SSH identity can read it.
  Evidence: `git ls-remote https://github.com/kleverhq/ieee-1800-2023-annotated` requested credentials; `git ls-remote git@github.com:kleverhq/ieee-1800-2023-annotated.git HEAD` returned `e63112d...`.
- Observation: Some requirements need more than one exact citation. Output copy-out is specified by `[2023:13.5:P005:p348]`, while its assignment-like conversion context is specified by `[2023:10.8:L007:p260]`.
  Evidence: both blocks are present in the pinned annotated text.
- Observation: The addition-width seed record pointed at `11.6.1`, but the direct normative prose tested by the case is in 11.6 and 11.6.2.
  Evidence: `[2023:11.6:P003:p299]` explicitly includes an assignment left-hand side in the largest operand, and `[2023:11.6.2:P001:p300]` states the interim-result rule.
- Observation: Two seed oracles crossed an additional scope or conversion boundary not captured by their first migration draft.
  Evidence: chapter 13 now cites the automatic truncation block, and chapter 26 now cites compilation-unit outer-scope lookup; focused citation re-review reported no substantive findings.

## Decision Log

- Decision: Pin the user-provided HTTPS URL in `.gitmodules`, using SSH only as a local transport workaround for the initial clone.
  Rationale: The repository contract should retain the requested portable URL rather than encode one developer's SSH setup.
  Date/Author: 2026-07-20 / coding agent.
- Decision: Validate citations against a byte-identical vendored copy of the annotated corpus's `anchors.json` during catalog loading.
  Rationale: Citation validation remains deterministic and exact without making a private authoring corpus a runtime dependency.
  Date/Author: 2026-07-20 / coding agent.
- Decision: Keep anchors ordered and require at least one unique value; the first anchor will state the main rule and later anchors may support related semantics.
  Rationale: Order communicates the primary citation while allowing compound requirements without introducing another metadata field.
  Date/Author: 2026-07-20 / coding agent.
- Decision: Correct the active addition-width clause from `11.6.1` to `11.6` while migrating its citations.
  Rationale: The annotated corpus places the directly tested normative statement in 11.6, and the active clause must identify the rule actually used by the oracle.
  Date/Author: 2026-07-20 / coding agent.
- Decision: Advance requirement metadata and dashboard datasets to schema version 2 with no version-1 compatibility path.
  Rationale: Replacing a required scalar with a required array is an intentionally breaking public-contract change. Catalog loading, dataset merge, and replay reject version-1 requirement data rather than translating or delegating it.
  Date/Author: 2026-07-20 / coding agent.
- Decision: Do not initialize or authenticate the annotated submodule in normal CI or runtime paths.
  Rationale: Only requirement authoring needs the full corpus. If it is initialized locally, pre-commit compares its anchor index byte-for-byte with the vendored runtime copy.
  Date/Author: 2026-07-20 / coding agent.

## Outcomes & Retrospective

The parent repository pins annotated commit `e63112d2a9dfb4586d0e33769721238c8c619ece` for optional requirement authoring and vendors its exact anchor index for runtime validation. All twelve seed requirements use verified complete anchors, including supporting conversion and scope blocks where their oracles span clauses. Catalog loading rejects a missing vendored index, malformed index counts, unknown citations, empty or duplicate anchor lists, wrong primary clauses, retired fields, and requirement schema version 1. Requirement and dashboard contracts are version 2; the dashboard searches and displays every anchor, and dataset publication rejects version-1 datasets.

Normal clones, CI, execution, replay, and publication never initialize or read the submodule. Replay validates requirements from detached historical worktrees against the current checkout's vendored index, including the initial schema-version-2 commit that predates the vendored file. When a requirement author initializes the submodule, pre-commit requires its `anchors.json` and the vendored file to be byte-for-byte identical. This was verified by passing `just smoke` and `just precommit` with the submodule directory absent, and by proving that a one-byte mismatch fails the new hook. No private-repository credential is needed for normal repository use.

## Context and Orientation

`standards/requirements/chapter-NN.toml` contains strict requirement records. `src/svtorture/models.py` defines their Pydantic public contract, and `src/svtorture/catalog.py` loads chapter files and cross-validates repository metadata. `just schemas` regenerates snapshots under `schemas/`. `src/svtorture/publish.py` exports requirements unchanged to the dashboard, whose TypeScript contract is `dashboard/src/types.ts` and whose search and display logic is in `dashboard/src/model.ts` and `dashboard/src/MatrixView.tsx`.

An anchor is a globally unique citation such as `[2023:4.9.4:P001:p070]`. The fields identify edition, clause, fragment, and printed page. The annotated submodule's generated `anchors.json` is the machine-readable membership index; `txt/NN.txt` gives the text following each anchor, and its PDF remains authoritative when a block carries a visual-review marker.

The seed inventory currently has twelve requirements in eleven chapter files. Every record has one informal `paragraph_anchor` string. The migration replaces it with TOML arrays named `anchors`, updates the strict model and dashboard, and rejects unknown citations before any campaign runs.

## Open Questions

There are no unresolved source-code questions. Access to the private annotated repository is needed only by contributors who add or revise requirements.

## Plan of Work

First add the git submodule at `standards/ieee-1800-2023-annotated`, preserving the requested HTTPS URL in `.gitmodules`, and vendor its `anchors.json` beside it. Normal workflows must not initialize the submodule. Then change `Requirement` in `src/svtorture/models.py` to expose a non-empty ordered tuple `anchors`, rejecting duplicates and the removed field through the existing strict-model behavior.

In `src/svtorture/catalog.py`, load the vendored `standards/ieee-1800-2023-anchors.json` once while assembling the inventory, verify its schema version and edition, ensure its declared count matches a duplicate-free set, and reject each requirement citation not found in that set. Tests copy the catalog without the submodule and prove that normal loading succeeds.

Migrate each chapter TOML to exact complete anchor strings. Most requirements need one anchor; addition width, output copy-out, and package import need supporting anchors because their tested behavior combines rules. Change the addition requirement's active clause and 2023 applicability clause to `11.6`; do not speculate about or alter historical revision clauses.

Update dashboard search, display, TypeScript types, and fixtures to consume `anchors`. Regenerate both requirement schemas through `just schemas`. Update `standards/AGENTS.md`, contributor documentation, architecture text, and root setup guidance so future interpretation starts from the pinned annotated corpus and complete anchors. Do not duplicate extracted standard prose in parent-repository docs.

### Concrete Steps

Run all commands from `/home/esynr3z/projects/sv-torture`.

Add the submodule using the requested URL with a one-command local URL rewrite if HTTPS authentication is unavailable:

    git -c url."git@github.com:".insteadOf=https://github.com/ submodule add \
      https://github.com/kleverhq/ieee-1800-2023-annotated \
      standards/ieee-1800-2023-annotated

Implement model, loader, metadata, dashboard, workflow, test, and documentation edits. Generate schemas and run deterministic checks:

    just schemas
    just smoke

Expect schema generation to leave only the intended generated snapshots changed and `just smoke` to complete all Python, metadata, focused test, TypeScript, and frontend test recipes without error. Also run the complete non-Docker unit suite if smoke passes:

    just unit

Finally verify migration and submodule state:

    rg -n 'paragraph_anchor' standards src dashboard schemas README.md AGENTS.md
    git submodule status
    git diff --check

The search should print nothing, submodule status should show `e63112d...` without a leading `-` or `+`, and `git diff --check` should be silent. Negative model tests intentionally retain the retired field name to prove strict rejection.

### Validation and Acceptance

`load_catalog` must accept all twelve migrated requirements when the pinned index is present. A focused test must prove that replacing a known anchor with an invented but well-formed anchor raises `CatalogError`; model tests must prove that an empty or duplicate anchor list and the retired `paragraph_anchor` field are rejected. Generated version-2 schemas must require a unique `anchors` array with at least one string and must not expose `paragraph_anchor`.

Dashboard type checking and tests must pass with `anchors: string[]`; search must include every anchor and the expanded requirement row must render all citations. GitHub Actions and runtime paths must not initialize or access the submodule. Contributor guidance must identify it as an optional requirement-authoring source and explain that complete anchors, not project-owned paraphrase anchors, are required.

### Idempotence and Recovery

Schema generation and tests are repeatable. If submodule addition fails after creating the directory, inspect `git status` and `.git/modules/standards`; use `git submodule deinit` and `git rm` only for the partially added path before retrying, never remove unrelated Git state. Do not edit any file inside the submodule. Test helpers create only temporary copies and must not mutate the pinned index.

### Artifacts and Notes

The annotated corpus is pinned at:

    e63112d2a9dfb4586d0e33769721238c8c619ece

Representative migrated citations are:

    SV-2023-04-NBA-RHS-CAPTURE -> [2023:4.9.4:P001:p070]
    SV-2023-13-OUTPUT-COPYOUT -> [2023:13.5:P005:p348], [2023:10.8:L007:p260], [2023:6.11.2:P004:p109-110]
    SV-2023-26-PACKAGE-IMPORT -> [2023:26.3:P001:p808], [2023:26.3:P004:p809], [2023:3.12.1:L007:p056]

### Interfaces and Dependencies

No new package dependency is needed. `Requirement.anchors` in `src/svtorture/models.py` is a frozen nonempty tuple of unique format-checked strings. `RequirementInventory`, `RequirementChapter`, and `StandardsIndex` use `RequirementSchemaVersion` 2. `_load_requirements` in `src/svtorture/catalog.py` consumes the standard-library `json` module to load the vendored index and raises `CatalogError` for a missing, malformed, inconsistent, or unmatched index. `scripts/check_annotated_anchors.py` performs the optional byte comparison during pre-commit. The dashboard `Requirement` interface exposes `anchors: string[]`, and dashboard datasets use schema version 2.

Revision note (2026-07-20): Initial self-contained plan created after repository and annotated-corpus inspection so implementation could proceed with exact citations and observable validation.

Revision note (2026-07-20 11:41Z): Updated the living plan after implementation, schema-version review, citation review, replay hardening, credential separation, and deterministic acceptance checks.

Revision note (2026-07-20 12:10Z): Removed all schema-version-1 compatibility and replay delegation after the transition was clarified as intentionally breaking.

Revision note (2026-07-20 13:40Z): Vendored the anchor index and removed the annotated submodule from every normal runtime and CI path; it remains optional for requirement authoring. Replay explicitly receives the current vendored index when loading a detached historical catalog.
