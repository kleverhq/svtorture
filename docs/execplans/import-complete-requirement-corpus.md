# Import the complete IEEE 1800-2023 requirement corpus

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the `exec-plan` skill.

## Purpose / Big Picture

After this change, SVTORTURE will load the consolidated IEEE 1800-2023 requirement extraction instead of only the small initial chapter subset. Maintainers will also have the extraction's waiver dispositions, materialization guidance, and historical revision evidence beside the requirement catalog for later review and case authoring. A user can verify the result by loading the catalog through the normal repository checks and observing that every published chapter or annex requirement is present exactly once, while session manifests are absent and waiver records do not alter coverage or dashboard calculations.

## Non-Goals

This work does not make waivers part of runtime catalog models, campaign coverage operands, scoring, publication bundles, or dashboard behavior. It does not import extraction session manifests, RPC logs, usage records, licensed IEEE PDFs, generated standard text, or machine-local paths. It does not redesign requirement schemas or rewrite extracted requirement prose unless a duplicate must be resolved to preserve the existing catalog's valid case references and semantics.

## Progress

- [x] (2026-08-03 07:49Z) Created branch `feat/import-complete-requirement-corpus` from a clean `main` working tree.
- [x] (2026-08-03 07:49Z) Read repository guidance and the annotation and methodology documentation.
- [x] (2026-08-03 08:02Z) Audited both catalogs: 12 current IDs, 6,719 incoming IDs, no ID collisions, and 12 semantic duplicates resolved against the annotated IEEE 1800-2023 corpus.
- [x] (2026-08-03 08:02Z) Selected `standards/{waivers,materialization-hints,historical-evidence}` as archival sidecar locations with no runtime loader or metric integration.
- [x] (2026-08-03 08:02Z) Imported 49 requirement files and all 168 approved sidecar files byte-for-byte; no session manifest was imported.
- [x] (2026-08-03 08:02Z) Expanded the requirement part index, documented the sidecars, remapped all 12 cases, and adjusted the affected catalog test fixture; no tag or schema-model change was needed.
- [x] (2026-08-03 08:16Z) Validated catalog loading, exact source copies, counts, unique IDs, case references, schema regeneration, and the full 16,963-anchor annotation index; `just smoke` and `just precommit` passed.
- [x] (2026-08-03 08:16Z) Ran `just ci`: 185 non-Docker Python tests, 81 dashboard tests, 11 fake-Docker tests, and the production dashboard build passed; only the final real-tool smoke was blocked by a Docker Hub DNS timeout while pulling `ubuntu:24.04`.
- [x] (2026-08-03 08:26Z) Completed two focused review lanes and a fresh clean control review, committed the implementation and plan, pushed `feat/import-complete-requirement-corpus`, and opened pull request `https://github.com/kleverhq/svtorture/pull/1`.

## Surprises & Discoveries

- Observation: The two catalogs have no common IDs, but all 12 current requirements semantically overlap the consolidated publication and all 12 are primary requirements of existing cases.
  Evidence: Anchor comparison found 23 current-to-incoming overlap pairs involving 20 incoming records; clause-level review found an exact or decomposed replacement for every current case oracle.

- Observation: Some legacy requirements combined several atomic rules, so correct deduplication requires one primary and multiple related requirements rather than retaining a second composite record.
  Evidence: `ch13-output-copyout-width` now maps assignment-like argument conversion as primary plus narrowing and transfer timing as related rules; `ch26-multifile-package-import` maps lookup order as primary plus three package/wildcard rules.

- Observation: All incoming requirement tags are empty and all 10,771 incoming citations resolve to the committed anchor index.
  Evidence: The parsed audit found zero unknown tags and zero missing anchors among 8,696 unique cited anchors, so neither `standards/tags.toml` nor generated schema enums need a change.

- Observation: Sidecar files cover 56 parts even though only 49 parts contain requirements.
  Evidence: Chapter 41 and annexes C, D, E, O, P, and Q have intentionally empty materialization and historical requirement lists but still carry waiver or empty-part evidence.

- Observation: The larger corpus exposed a latent mismatch between requirement-manifest hashing and dashboard catalog ordering.
  Evidence: Bundle validation failed because `Catalog.requirement_manifest_hash()` hashed requirement-file/ID order while `bundle._catalog()` and `CampaignCatalog` use standard clause order. With one or two requirements per part these orders had happened to coincide; the 6,719-record corpus made them diverge. Canonicalizing the hash to the existing dashboard order restored all 118 focused tests.

## Decision Log

- Decision: Work on `feat/import-complete-requirement-corpus` based on current `main`.
  Rationale: The user explicitly approved this branch name, and the starting working tree was clean and synchronized with `origin/main` according to `git status --short --branch`.
  Date/Author: 2026-08-03 / Pi

- Decision: Treat the imported sidecars as maintained corpus evidence, but do not add them to runtime loading or metrics in this change.
  Rationale: The user explicitly requested all sidecars except session manifests and explicitly deferred waiver integration into dashboard coverage and related calculations. Keeping these files outside the runtime path is the smallest change that preserves the artifacts without changing behavior.
  Date/Author: 2026-08-03 / Pi

- Decision: Use the consolidated publication's 6,719 records as the final corpus and remove all 12 legacy records after remapping their cases.
  Rationale: Keeping all records would produce 6,731 unique IDs but retain 12 semantic duplicates. IEEE 1800-2023 clause and anchor review proved that each legacy oracle is represented by one incoming requirement or by an incoming primary plus related atomic requirements. This preserves case behavior while achieving semantic deduplication.
  Date/Author: 2026-08-03 / Pi

- Decision: Copy publication requirement and sidecar files byte-for-byte rather than introducing sidecar schemas and loaders.
  Rationale: Existing runtime validation fully handles schema-version-3 requirements, while the user requested transfer—not runtime consumption—of sidecars. Validation-only model layers would add public schemas and code without a current execution requirement. Exact source comparison and inventory checks prove transfer fidelity with less complexity.
  Date/Author: 2026-08-03 / Pi

- Decision: Canonicalize `Catalog.requirement_manifest_hash()` in standard clause order.
  Rationale: Campaign catalogs are already required to serialize requirements in standard clause order and bundle validation rehashes that projection. Making the source manifest hash use the same existing canonical order fixes the root cause rather than weakening bundle integrity or changing dashboard contracts.
  Date/Author: 2026-08-03 / Pi

## Outcomes & Retrospective

The implementation is complete and locally validated. SVTORTURE now loads 6,719 unique consolidated requirements across 49 nonempty parts. All 12 pre-existing cases retain their original sources and oracles while referring to consolidated primary and related requirements; the 12 old semantic duplicates are gone. The repository retains 56 files apiece of waiver, materialization-hint, and historical-evidence sidecars, byte-identical to the publication, with no session manifests or machine-local paths. Sidecars remain outside runtime coverage, scoring, bundle, and dashboard paths.

The larger corpus exposed and fixed one latent ordering defect: requirement manifest hashes now use the same standard clause order already required by campaign catalogs. `just annotate-check`, `just smoke`, and `just precommit` pass. The internally controlled portions of `just ci` pass: 185 non-Docker Python tests, 81 dashboard tests, 11 fake-Docker tests, and a production dashboard build. The final real-tool smoke could not pull `ubuntu:24.04` because Docker Hub DNS resolution timed out; this is an external network limitation, not a test or implementation failure.

The branch is pushed and the requested pull request is open at `https://github.com/kleverhq/svtorture/pull/1`. No implementation work remains.

## Context and Orientation

The repository root is `/home/esynr3z/projects/sv-torture`. The current runtime requirement catalog lives in `standards/requirements/`, with one TOML file per numbered chapter or lettered annex. `standards/index.toml` declares which parts must exist; `src/svtorture/catalog.py` rejects a mismatch between that index and the files on disk, validates every requirement against Pydantic models in `src/svtorture/models.py`, checks cited anchors against `standards/ieee-1800-2023-anchors.json`, and checks tags against `standards/tags.toml`.

The incoming publication is `/home/esynr3z/projects/sv-torture-req-loop-2/output`. Its `requirements/` directory contains schema-version-3 TOML documents. Its three sidecar directories are `waivers/`, `materialization-hints/`, and `historical-evidence/`. A sidecar is an artifact associated with a chapter or annex but not loaded as a normative requirement. The publication's `manifests/` directory records extraction sessions and is deliberately excluded from this import.

A duplicate means two records that represent the same normative obligation, normally detected first by identical requirement ID and then checked by location, anchors, summary, tags, test strategy, variants, and revision applicability. Deduplication must produce one valid record per ID. Existing case metadata may refer to current IDs, so those IDs cannot be removed or silently redirected without auditing all references.

The root `justfile` is the stable command interface. `just schemas` regenerates public JSON schemas and generated schema files must not be edited by hand. `just smoke` is the deterministic local gate; `just ci` is the complete handoff gate when Docker and network access are available. Requirement changes must also be checked against the locally materialized annotation corpus through `just annotate` when available, while ordinary catalog validation relies only on the committed anchor index.

## Open Questions

No open implementation questions remain. The catalogs have no ID collisions; the 12 semantic duplicates have explicit remappings; incoming tags require no registry changes; and the approved source artifacts require no path normalization.

## Plan of Work

First, inventory both catalogs and parse them with Python's standard `tomllib`. Compare records by ID and report identical entries, incoming-only entries, current-only entries, and field-level conflicts. Search all case TOML files for references to current IDs. Check every incoming tag against `standards/tags.toml`, every part against the committed anchor index, and every cited anchor for existence. Use those facts to choose a deterministic merge in which semantically distinct obligations remain separate and exact duplicates appear once.

Second, replace the catalog TOML files under `standards/requirements/` with the consolidated publication's byte-identical files, which are already sorted by requirement ID. Add every published part containing requirements to `standards/index.toml` in standard order. Remove the 12 semantically duplicate legacy records and remap each affected case to the corresponding consolidated primary requirement, adding related atomic requirements where the legacy record had combined several rules. Record the deduplication decision and representative decompositions in this plan.

Third, copy `output/waivers/`, `output/materialization-hints/`, and `output/historical-evidence/` into clearly named directories under `standards/`. Do not copy `output/manifests/`. Add concise README navigation that explains that these artifacts are extraction sidecars and are not runtime scoring inputs. Avoid adding loaders, model types, schemas, or dashboard code unless an existing repository contract proves they are required.

Fourth, run catalog and schema validation. If new requirement tags are valid but absent from `standards/tags.toml`, add only those tags with concise existing-style descriptions. Run `just schemas` only if model/tag changes make generated schemas differ, and inspect generated changes rather than editing them manually. Add focused tests or a small validation script only if existing checks do not prove deduplication and the intended inventory.

Finally, compare the committed destination against the source publication and the documented conflict decisions. Confirm there are no duplicate IDs, no unindexed requirement files, no session manifests, no machine-local paths, and no accidental coverage/dashboard changes. Run `just smoke`, `just precommit`, and, when Docker and network access are available, `just ci`. Review `git diff`, commit with a Conventional Commit message, push the branch to `origin`, and open a GitHub pull request summarizing counts, deduplication, sidecars, exclusions, and validation evidence.

### Concrete Steps

Run all commands from `/home/esynr3z/projects/sv-torture` unless stated otherwise.

Inspect and compare the inventories using Python so TOML structure, rather than line formatting, controls the comparison:

    python - <<'PY'
    # Parse standards/requirements and the publication requirements with tomllib,
    # index records by ID, and print overlap and conflict counts.
    PY

The expected result is a finite report covering all current and all 6,719 incoming requirements with no unclassified record.

After resolving the audit, copy only the three approved sidecar directories and write merged requirement documents. Then run:

    just schemas
    just smoke
    just precommit

If local Docker and network access are usable, also run:

    just ci

Before publishing, run inventory checks that print the final requirement count, unique ID count, sidecar file counts, and any forbidden manifest path. Acceptance requires equal requirement and unique-ID counts, 56 files in each sidecar corpus unless source audit justifies a documented exception, and zero imported manifest files.

Publish only after validation:

    git add standards docs/execplans/import-complete-requirement-corpus.md
    git commit -m "feat(standards): import complete requirement corpus"
    git push -u origin feat/import-complete-requirement-corpus
    gh pr create --base main --head feat/import-complete-requirement-corpus --title "feat(standards): import complete requirement corpus" --body-file <prepared-body>

### Validation and Acceptance

Catalog loading must succeed through the normal CLI or test path and report one record per requirement ID. Every destination requirement citation must resolve through `standards/ieee-1800-2023-anchors.json`, every used tag must be registered, and each destination file must correspond to a part listed in `standards/index.toml`.

The merged corpus audit must account for every existing and incoming requirement. Existing cases must still resolve their primary and related requirement IDs. The three approved sidecar directories must match their source inventories after any explicitly documented path normalization. No path named `manifests` and no session manifest JSON may be added.

`git diff` must show no changes to runtime coverage, campaign metric, publication bundle, or dashboard implementation solely to consume waivers. `just smoke` and `just precommit` must pass. `just ci` should pass when its external prerequisites are available; an unavailable external service must be recorded precisely rather than represented as a code success.

The final acceptance artifact is an open pull request from `feat/import-complete-requirement-corpus` to `main`, with the pushed commit and validation evidence in its description.

### Idempotence and Recovery

The comparison and validation scripts are read-only and safe to rerun. Copy sidecars with directory-level replacement from the immutable publication so retries cannot leave a mixture of versions. Generate merged TOML from parsed records or perform an audited whole-file replacement so rerunning produces byte-identical output. Never modify the source publication.

If a merge attempt fails validation, restore only the affected destination files from Git and rerun the audited merge; do not reset unrelated work. If schema generation changes unrelated files, inspect the generator and restore unrelated outputs. If pushing or PR creation fails, keep the local commits and retry the remote command without recreating the branch.

### Artifacts and Notes

Initial source publication inventory:

    requirements:          49 files, 6,719 records (publication README)
    waivers:               56 files, 1,900 records (publication README)
    materialization-hints: 56 files
    historical-evidence:   56 files
    manifests:              8 files (excluded)

The current catalog initially indexes chapters 4, 5, 6, 7, 11, 12, 13, 22, 23, 26, and 27. The final part list will be recorded after the merge audit because publication files are absent for parts with no normative testable requirements.

### Interfaces and Dependencies

No new runtime interface or dependency is planned. Parsing and merge audit utilities should use Python 3's standard `tomllib`, `json`, and `pathlib` modules. Existing catalog validation remains in `src/svtorture/catalog.py` and `src/svtorture/models.py`; existing Pydantic models remain the authoritative runtime contract. Generated schemas remain outputs of `just schemas`.

Revision note (2026-08-03): Created the initial plan after branch creation and repository-guidance review. Counts and conflict decisions remained explicitly pending the catalog and sidecar audits.

Revision note (2026-08-03 08:02Z): Updated the living plan after the semantic audit and import. Recorded the 6,719-record deduplicated outcome, case-remapping strategy, sidecar boundary, observed source facts, and remaining validation work.

Revision note (2026-08-03 08:08Z): Recorded the manifest-hash ordering defect exposed by the complete corpus, its root-cause fix, and the passing focused test gate.

Revision note (2026-08-03 08:20Z): Updated validation and outcomes after smoke, precommit, partial CI, and focused review. Recorded the external Docker Hub DNS timeout and narrowed remaining work to control review and publication.

Revision note (2026-08-03 08:24Z): Recorded the clean fresh control review. Only the final plan commit, branch push, and pull request remained.

Revision note (2026-08-03 08:26Z): Marked the ExecPlan complete after the branch push and creation of pull request #1.
