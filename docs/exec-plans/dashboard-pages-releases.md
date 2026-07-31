# Publish latest dashboard data on Pages and archive every campaign in Releases

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the `exec-plan` skill.

## Purpose / Big Picture

After this work, a maintainer can manually start one GitHub Actions workflow that collects the publication-eligible tools, publishes each resulting conformance campaign as an immutable GitHub Release, rebuilds all historical trend points from the small Release summaries, and deploys a bounded GitHub Pages site. The public site contains complete drill-down data for only the campaign with the maximum `(finished_at, id)` while every older campaign remains downloadable and reproducible from its Release.

A maintainer can also run a local dashboard over any number of the same campaign ZIP files or unpacked bundle directories. The browser initially fetches only `data/index.json` and `data/trends.json`, then loads one selected campaign's manifest, catalog, and verdicts, and finally loads one case-centric evidence shard only when case detail is opened. The canonical schema-version-5 `Campaign` remains the local source of truth; the dashboard transport is a strict, derived schema-version-6 contract and does not alter evaluator or metric semantics.

The visible proof is threefold. `just dashboard-build <campaign.json...>` builds a local v6 site without `dataset.json`; `just dashboard-local <bundle-or-directory>...` serves one or more bundles with selectable campaigns and trends; and the manually dispatched GitHub workflow creates immutable `campaign-<id>` Releases and deploys a latest-only Pages artifact.

## Non-Goals

This work does not add a backend, database, object store, browser-side ZIP import, service worker, IndexedDB, React Query, a separate AI export, cross-release catalog deduplication, full-text evidence search, multipart archives, `.json.gz`, or speculative sharding of trends, catalog, or verdicts. It does not change conformance judgments, headline metric calculations, canonical `Campaign` schema version 5, or the public trust boundary. It does not migrate v5 public history: no such history exists, so v5 converters and compatibility fallbacks are deliberately omitted. It does not enable a scheduled dashboard update; publication is manual through `workflow_dispatch` only.

## Progress

- [x] (2026-07-31 20:30Z) Read the accepted proposal, repository guidance, architecture, methodology, reproduction workflow, current backend/frontend/publication code, tests, and disabled workflows.
- [x] (2026-07-31 20:35Z) Run the pre-change `just smoke` baseline: Python formatting/lint/type checks passed, metadata validated, 101 focused Python tests passed, 15 annotator utility tests passed, and 74 frontend tests passed.
- [x] (2026-07-31 20:42Z) Record the clarified standalone `CampaignSummary`, reusable summary schema, publisher-owned tag lifecycle, resumable draft rule, manual-only initial trigger, and explicit v5 removal in `docs/dashboard-pages-releases-proposal.md`.
- [ ] Commit this initial ExecPlan while keeping the user-owned proposal untracked.
- [ ] Milestone 1: implement and test the strict v6 bundle format, generated schemas, deterministic compact resources and reproducible ZIP.
- [ ] Review milestone 1 with focused read-only code, schema/architecture, and security/correctness reviewers; fix findings, run a clean control review, and commit the reviewed stage.
- [ ] Milestone 2: migrate the frontend and local assembly to index/trends and lazy campaign/evidence resources, with N-bundle local selection/comparison.
- [ ] Review milestone 2 with focused frontend correctness, architecture, and performance/loading reviewers; fix findings, run a clean control review, and commit the reviewed stage.
- [ ] Milestone 3: implement immutable Release publication, rebuild history from unchanged summaries, assemble latest-only Pages, enforce the size gate, activate ordinary CI, and add one manual dashboard workflow.
- [ ] Review milestone 3 with focused CI/security, release idempotency, and operational reviewers; fix findings, run a clean control review, and commit the reviewed stage.
- [ ] Milestone 4: support replay from a v6 ZIP or local/HTTPS manifest, remove every v5 dataset/history/worktree path, and update durable documentation.
- [ ] Review milestone 4 and the complete change with focused replay/security, documentation, and end-to-end control reviewers; fix findings and commit the reviewed stage.
- [ ] Run `just smoke`, `just unit`, `just frontend`, `just ci` where Docker/network are available, deterministic bundle checks, local HTTP loading checks, schema regeneration verification, and the final prompt-to-artifact completion audit.
- [ ] Push the commits, manually dispatch the dashboard publication workflow with `gh`, inspect its jobs, Release assets, tag target, deployed Pages data tree, and absence of regular schedule. Ask the user only if repository policy or environment approval blocks automation.

## Surprises & Discoveries

- Observation: every workflow is currently disabled by the `.yml.disabled` suffix, and the remote has no `gh-pages` branch or `campaign-*` tags.
  Evidence: `.github/workflows/ci.yml.disabled`, `.github/workflows/nightly.yml.disabled`, `.github/workflows/pages.yml.disabled`, plus the initial remote/ref inspection performed during planning.

- Observation: the old Pages path duplicates every full campaign in both `data/dataset.json` and `history/campaigns/<id>.json`, so deleting the old merge/worktree path is required rather than adapting it.
  Evidence: `src/svtorture/publish.py` functions `build_dataset`, `merge_datasets`, and `publish_pages_tree`.

- Observation: canonical `Campaign` already carries bounded excerpts, full-stream byte counts and hashes, truncation flags, portable argv, tool/image provenance, corpus operands, and materialized results. Only historical catalog definitions and Release metadata must be supplied while exporting the derived bundle.
  Evidence: `src/svtorture/models.py` models `CapturedStream`, `StageObservation`, `NormalizedResult`, `CampaignTool`, `CorpusMetrics`, and `Campaign`.

- Observation: the current frontend search includes stdout/stderr because all evidence is loaded at startup. In v6 ordinary search must intentionally use only catalog and verdict metadata.
  Evidence: `dashboard/src/useDataset.ts` fetches one monolith and `dashboard/src/model.ts` searches observation streams.

## Decision Log

- Decision: preserve canonical `Campaign` schema version 5 and introduce dashboard transport models in `src/svtorture/dashboard_models.py` at schema version 6.
  Rationale: the dashboard layout is a derived transport concern and must not force a canonical evidence contract migration.
  Date/Author: 2026-07-31 / coding agent, following the accepted proposal.

- Decision: use Python standard-library JSON, hashing, ZIP, filesystem, URL, and subprocess facilities plus the existing Pydantic and `gh` CLI; add no Python dependency.
  Rationale: all required deterministic serialization, safe extraction, HTTP loading, and GitHub orchestration can be implemented with existing platform tools. This is the smallest solution.
  Date/Author: 2026-07-31 / coding agent.

- Decision: use one `CampaignSummary` model for both `campaign-summary.json` and each `trends.json.campaigns[]`, including nested `schema_version: 6` and `kind: campaign-summary`.
  Rationale: standalone summaries remain self-describing and the Pages builder can append validated Release assets unchanged without a second projection path.
  Date/Author: 2026-07-31 / user clarification.

- Decision: create a reusable `campaign-summary.schema.json`; make `campaign-trends.schema.json` reference it and expose both in `data/index.json`.
  Rationale: this keeps one versioned contract rather than duplicate summary definitions.
  Date/Author: 2026-07-31 / user clarification.

- Decision: drop v5 outright after the v6 paths work; do not write a converter, dual loader, or compatibility fallback.
  Rationale: there is no public v5 history, and retaining two evidence formats would violate the accepted bounded-storage contract.
  Date/Author: 2026-07-31 / user clarification.

- Decision: let the publisher own a lightweight `campaign-<id>` tag and create a missing tag through Release creation with the full recorded commit as target. Never move a tag or replace an asset.
  Rationale: Release identity must remain anchored to the exact campaign checkout; GitHub ignores target commit when a tag already exists, so explicit peeled-commit checking is mandatory.
  Date/Author: 2026-07-31 / user clarification.

- Decision: make an interrupted draft resumable only when the peeled tag target and every existing expected asset match; upload only missing expected assets and reject extra or differing assets before publication.
  Rationale: this recovers safely from network interruption without introducing deletion, clobber, or mutable published identity.
  Date/Author: 2026-07-31 / coding agent resolution of the remaining operational edge case.

- Decision: activate normal push/pull-request CI separately, but make the campaign collection/release/Pages workflow manual-only with no `schedule` or publication-on-push trigger.
  Rationale: the user explicitly wants working CI and GitHub Actions while deferring regular dashboard updates.
  Date/Author: 2026-07-31 / user objective.

## Outcomes & Retrospective

No implementation milestone is complete yet. The accepted transport and Release lifecycle decisions have been incorporated into the proposal, the baseline is green, and repository exploration found no legacy public history to preserve. Update this section after every reviewed milestone with observable behavior, test evidence, remaining risk, and any deviation from the proposal.

## Context and Orientation

SVTORTURE is a standards-driven SystemVerilog conformance framework. A canonical campaign is the immutable local JSON file `.svtorture/campaigns/<campaign-id>/campaign.json`, represented by `Campaign` in `src/svtorture/models.py`. Collection code in `src/svtorture/campaign.py` fills an exact case-by-tool/profile result grid. `src/svtorture/evaluator.py` alone decides conformance. `src/svtorture/metric.py::compute_metric` computes the published headline operands. `src/svtorture/publish.py::validate_public_campaign` is the public trust boundary: it rechecks observations, catalog manifests, GitHub Actions provenance, tool policy, image identity, private paths, secrets, and anonymous GHCR availability. These functions must be reused, not weakened or duplicated.

The current dashboard transport is a schema-version-5 monolith produced by `src/svtorture/publish.py::build_dataset`. `dashboard/src/useDataset.ts` fetches `data/dataset.json`, and most React views receive the whole `Dataset`. `src/svtorture/publish.py::publish_pages_tree` merges all campaigns into that monolith and writes another complete copy under `history/campaigns`. `scripts/publish_pages.py` creates a Git worktree and pushes `gh-pages`. The v6 change replaces all of these storage and loading assumptions.

A v6 campaign bundle is a portable directory `campaigns/<id>/` containing `manifest.json`, `catalog.json`, `verdicts.json`, and `evidence/0000.json` onward. The manifest contains campaign metadata, full tool definitions, materialized metrics, and hashes/byte sizes for every resource. The catalog is a self-contained historical requirement/case snapshot with source links tied to the recorded repository commit. Verdicts contain compact case-centric status/reason/evidence-mode records and the evidence shard href for each case. Evidence shards contain full results except the location-dependent `reproduction_command`; they preserve observations and bounded streams unchanged. Cases sort by ID and remain intact while packing: close a shard after at most 100 cases or before adding another case would take compact JSON past the 8 MiB target; one oversized case occupies its own shard. Filenames are zero-padded and deterministic.

The v6 site has `data/index.json`, `data/trends.json`, generated schemas, and zero or more copied campaign bundle trees. `DashboardIndex.campaigns` is the authority for complete drill-down availability. Public Pages has exactly one entry selected by maximum `(finished_at, id)`. A local site may have any number. `CampaignTrends` contains one `CampaignSummary` per campaign. Public summaries include archive tag, URLs, ZIP SHA-256, and byte size; local summaries may omit archive. Several campaigns may share a timestamp or day; gaps and backfill are not synthesized.

`src/svtorture/catalog.py::write_json_schema` owns generated schema snapshots and deletes retired JSON files. New dashboard schemas must be generated there and committed under `schemas/`; no generated JSON is hand-edited. The root `justfile` is the stable command interface. `scripts/` contains deterministic workflow bridges. `.github/workflows/` currently contains only disabled workflows, so enabled `.yml` files must be introduced deliberately.

Replay currently loads a complete local or HTTPS canonical campaign and calls `src/svtorture/reproduce.py::reproduce_case`. V6 replay introduces a small context containing manifest metadata, selected case/tool/profile, and one evidence result. The existing checkout, image, plan execution, evaluation, and comparison mechanics must be shared; canonical full-grid loading and verification remain unchanged.

## Open Questions

There are no known design questions requiring user input. GitHub repository policy, Actions write permissions, Pages environment approval, or private GHCR package visibility may require user action only if the final live run reports a concrete block. All implementation choices not fixed by the accepted proposal should follow the smallest deterministic solution and be recorded in the Decision Log.

## Plan of Work

### Milestone 1: strict bundle format

Create `src/svtorture/dashboard_models.py` with frozen, unknown-field-rejecting Pydantic models for `DashboardIndex`, `CampaignSummary`, `CampaignTrends`, `CampaignManifest`, `CampaignCatalog`, `CampaignVerdicts`, and `CampaignEvidenceShard`, plus their nested resource, archive, verdict, and catalog projection types. Reuse existing canonical nested models where their exact public shape is appropriate; define transport-specific result and case types only where fields are intentionally removed or added. Every top-level resource carries `schema_version: 6` and a constant `kind`.

Replace the v5 construction portion of `src/svtorture/publish.py` with small deterministic operations: compact JSON bytes, atomic file writing, canonical-to-bundle projection, case-centric shard packing, resource hashing, cross-resource bundle validation, summary projection, reproducible ZIP creation, safe ZIP extraction, and bundle loading. Keep `validate_public_campaign` intact. Local export calls `verify_campaign_against_catalog`; public export additionally calls `validate_public_campaign` before deriving any asset.

The exporter must verify that every canonical result occurs exactly once in evidence, each verdict agrees on coordinates/status/reason/evidence mode, all counts agree, metrics equal fresh `compute_metric` output, recorded judgments are still confirmed through existing catalog verification, and manifest/catalog/campaign hashes agree. Serialize with UTF-8 `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"))`. Create ZIP entries in sorted order with fixed timestamps, permissions, and path separators. Reject absolute paths, `..`, links, duplicate members, unexpected top-level layout, campaign-ID mismatch, unknown resources, wrong hashes/sizes, and duplicate IDs with differing content.

Extend `src/svtorture/catalog.py::write_json_schema` to generate dashboard index, summary, trends, manifest, catalog, verdicts, and evidence schemas. Ensure trends references the reusable summary schema. Regenerate snapshots only with `just schemas`. Replace obsolete v5 publication tests in `tests/test_publish.py` with strict model rejection, projection integrity, deterministic bytes and ZIP, packing boundaries, stream preservation, unsafe ZIP rejection, collision, and metric recomputation tests. Add a realistic synthetic scale test for 10,000 cases and 100,000 compact verdicts/evidence results without Docker or network access, recording output sizes and ensuring the packing and memory behavior remain practical.

At milestone acceptance, exporting the same canonical campaign twice yields byte-identical resource files and ZIP SHA-256; deleting or changing any resource byte makes validation fail; the ZIP contains only `campaigns/<id>/...`; evidence streams exactly match canonical bounded excerpts/sizes/hashes/truncation; generated schemas validate representative resources and reject extra fields. Run the focused Python test files, `just schemas`, `just metadata`, and `just smoke`. Then run parallel read-only code, schema/architecture, and security reviewers, fix all substantive findings, and run one fresh control review before committing.

### Milestone 2: frontend and local multi-campaign assembly

Add site assembly functions to `src/svtorture/publish.py` that accept any number of bundle ZIPs or unpacked bundle roots, safely materialize validated campaign trees, reject differing duplicate IDs, write an index containing every available campaign, and project one local summary per manifest with no archive. Add CLI wiring in `src/svtorture/cli.py` and stable root recipes. `just dashboard-local <bundle-or-directory>...` builds assets, assembles `dashboard/dist/data`, and starts the existing ordinary HTTP server. `just dashboard-build <campaign.json...>` remains a developer wrapper that exports temporary bundles and assembles the same site; it does not create a second transport.

Replace the frontend `Dataset` contract in `dashboard/src/types.ts` with the v6 resource types. Replace `dashboard/src/useDataset.ts` with a URL-keyed `Map<URL, Promise<validated-resource>>` loader/cache. The startup hook loads `./data/index.json` and its referenced trends file. Selecting an indexed campaign loads its manifest and then the relative catalog and verdict resource hrefs. Resource discriminants, campaign IDs, required arrays, and references are checked before a value reaches React; malformed or mismatched resources produce an explicit error rather than an unsafe cast.

Refactor `dashboard/src/TrendsView.tsx` to consume only `CampaignTrends`; it must show historical provenance and archive links even when detail is unavailable. Refactor `dashboard/src/App.tsx`, `dashboard/src/model.ts`, `dashboard/src/Filters.tsx`, `dashboard/src/HeadlineMetrics.tsx`, `dashboard/src/RequirementsView.tsx`, `dashboard/src/CampaignView.tsx`, and `dashboard/src/EvidenceView.tsx` to use selected manifest/catalog/verdicts. Ordinary search uses catalog and verdict metadata only. Opening one case detail follows that case's `evidence_href`, loads exactly one shard through the shared cache, verifies the campaign/case membership, and displays the selected full result. Startup and ordinary list/filter views must not request evidence.

Preserve URL-backed filters. If a deep link requests a campaign present only in trends, do not silently select latest; show an unavailable-detail message and its archive link. Comparison and changed-since-previous logic may operate only on campaigns listed in the local index and should load only the two manifests/verdict documents involved. Avoid adding a generalized state framework or persistence layer.

Update dashboard tests to model staged requests, cache reuse, resource failure, campaign switching, no eager evidence, one-shard detail loading, unavailable historical deep links, archive links, local N-campaign selection and comparisons. Add a Python/CLI integration test that assembles two bundles, verifies two index entries and trend points, serves or reads the output, and proves `dataset.json` is absent. Update `dashboard/index.html` with the alternate JSON link. At milestone acceptance, browser/network tests show only index/trends at startup and one shard on case detail; one bundle yields one trend point and N bundles yield N; plain Vite build still contains no data. Run focused Python/frontend tests and `just smoke`, then parallel frontend correctness, architecture, and loading-performance reviews plus a fresh control review before committing.

### Milestone 3: Releases, latest-only Pages, and enabled Actions

Implement workflow-facing GitHub orchestration with the existing `gh` CLI in a small script under `scripts/`, leaving substantive validation and assembly in typed library functions. Given one or more canonical campaign paths, validate and export each bundle, create its deterministic ZIP, calculate SHA-256 and bytes, derive archive URLs from `GITHUB_REPOSITORY`, create a `CampaignSummary`, and manage the tag/draft/published Release contract.

Before creating or resuming a Release, use `gh api`/`gh release view` to verify the full target commit exists and peel any existing lightweight or annotated tag to exactly `repository.commit`. A missing tag is created by draft Release creation with `--target <40-character-sha>` and `--latest=false`. For an existing published Release, download/inspect `campaign-summary.json` and the named ZIP, validate content and digest, and return no-op only on exact match. For an existing draft, reject unexpected assets or any mismatch, retain matching assets, upload only missing expected assets without clobber, verify exactly both expected assets, then publish. Never move tags, delete Releases, overwrite assets, or let GitHub's Latest flag define dashboard latest.

Build public history by enumerating published `campaign-*` Releases and downloading only each `campaign-summary.json`. Validate every summary, require archive metadata, unique IDs, matching tag/asset URLs, and append the summary object unchanged. Sort by `(finished_at, id)`. Select the maximum by that key, download and hash-check its ZIP even when it is an older/backfilled Release, and assemble only that complete campaign under Pages `data/campaigns`. Copy frontend assets, generated schemas, index, and trends into a clean Pages tree. Print component sizes, largest evidence shard, each campaign component, and total tree bytes; reject a tree over 650 MiB before upload. Reject a ZIP at or above GitHub's 2 GiB per-asset limit; do not implement multipart output.

Replace the disabled normal CI file with enabled `.github/workflows/ci.yml` retaining pull-request/main-push behavior and read-only permissions. Replace the disabled nightly/pages pair and worktree script with one enabled manually triggered publication workflow, named for public campaign publication rather than cadence. It retains policy selection, matrix collection, missing-tool aggregation, short-lived full log artifacts, Release creation, Pages assembly, `actions/upload-pages-artifact`, and `actions/deploy-pages`. Give only needed job permissions: packages write for image publishing, contents write for Releases, pages write and ID token write for deployment. There must be no `schedule`, `gh-pages` branch push, publication-on-push, or separate Pages workflow. Use `just` recipes for all substantive commands.

Mock subprocess/API boundaries in deterministic tests. Cover missing/existing/wrong tags, missing commit, published no-op and collision, interrupted drafts, unchanged summary aggregation, malformed/duplicate releases, backfill latest selection, public index cardinality one, size reports/gates, and no clobber. Validate workflow YAML structurally in tests or a simple parser/grep check without adding a dependency. At milestone acceptance, local mocked tests prove idempotency and backfill behavior; workflow files have correct triggers and permissions; no code mentions a `gh-pages` worktree. Run `just smoke` and all publication tests, then parallel CI/security, release correctness, and operations reviews plus a fresh control review before committing.

### Milestone 4: v6 replay and legacy cleanup

Introduce `ReplayContext` in `src/svtorture/reproduce.py` containing campaign metadata needed by the existing checkout/image path, one selected catalog case, one selected tool/profile, and one full evidence result. Extend the loader to accept a canonical campaign JSON, a local Release ZIP, or a local/credential-free HTTPS v6 `manifest.json`. For v6, verify manifest resource hashes and sizes, load only catalog metadata and the shard referenced by the selected case verdict, reject redirects or URLs that violate existing credential/size safety rules, and derive the reproduction command from the current source location instead of storing it in evidence.

Refactor only the shared lower replay path so both full canonical `Campaign` and `ReplayContext` use the same checkout, image retrieval/rebuild, execution, evaluation, and result comparison. Canonical replay must continue to perform full campaign/grid/catalog verification. V6 replay verifies the selected transport context and recorded result without pretending it is a complete canonical campaign.

Delete v5 `build_dataset`, `write_dataset`, merge validation, `merge_datasets`, old Pages history writer, old frontend Dataset types/hooks/tests, `scripts/publish_pages.py`, disabled nightly/pages files, stale recipes, and every permanent `dataset.json` or `gh-pages` URL/path. Update `docs/architecture.md`, `docs/reproduction.md`, `dashboard/README.md`, `scripts/README.md`, `schemas/README.md`, root `README.md` where needed, and mark the accepted proposal as implemented. Do not duplicate methodology; link to its source-of-truth sections.

At milestone acceptance, all three replay input forms reach the same mocked execution path and detect hash/context tampering; repository search finds no old dataset/merge/worktree contract except historical explanation in the proposal/ExecPlan; all durable docs describe current behavior. Run focused replay/docs tests, `just schemas`, `just smoke`, `just unit`, `just frontend`, and `just ci` when Docker/network permit. Run replay/security and documentation reviews, then a final independent control review over the entire implementation and commit.

### Final live validation and completion audit

Push all reviewed commits to the public repository. Use authenticated `gh` commands to inspect workflow availability, dispatch the manual publication workflow, and follow it to completion. If GitHub blocks Pages environment deployment, GITHUB_TOKEN write access, or public GHCR visibility, report the exact setting and ask the user to change only that setting; resume immediately afterward.

Inspect the resulting tag target and Release through GitHub, download both assets, verify ZIP SHA-256 and summary equality, and inspect Pages over HTTPS starting from `data/index.json`. Confirm trends contains every valid campaign Release, index contains exactly latest, detail resources and one evidence shard load, no `dataset.json` exists, the deployment came from Actions artifact, and rerunning publication is a no-op. Confirm the workflow source has only `workflow_dispatch` for dashboard publication and no schedule.

Before declaring completion, translate every acceptance criterion in the proposal and every explicit user instruction into a prompt-to-artifact checklist. Map each item to concrete file paths, command output, GitHub run/Release/tag evidence, or HTTP responses. Treat any uncertain or weakly covered item as incomplete and continue work. Only after the audit has no gap should the goal be marked complete.

## Concrete Steps

All commands run from `/home/esynr3z/projects/sv-torture` unless stated otherwise. Keep this list updated with the exact commands and observed summaries as milestones finish.

1. Preserve the baseline and commit only the execution plan. Keep `docs/dashboard-pages-releases-proposal.md` as an untracked user-owned artifact:

       just smoke
       git add docs/exec-plans/dashboard-pages-releases.md
       git commit -m "docs: plan dashboard release migration"

   The already observed baseline is green: 101 focused Python tests and 74 frontend tests passed in addition to formatting, typing, metadata, and annotator checks.

2. During milestone 1, regenerate rather than hand-edit schemas:

       just schemas
       uv run pytest -q tests/test_publish.py tests/test_catalog_models.py
       just metadata
       just smoke

   Expect deterministic export tests to compare two independently generated ZIP hashes and all strict rejection tests to pass.

3. During milestone 2, exercise local assembly:

       just dashboard-build ".svtorture/campaigns/<id>/campaign.json"
       test -f dashboard/dist/data/index.json
       test -f dashboard/dist/data/trends.json
       test ! -e dashboard/dist/data/dataset.json
       just dashboard-local "<bundle-a.zip>" "<bundle-b.zip>"

   From another shell, request `http://127.0.0.1:4173/data/index.json`; it must list both campaigns. Browser tests must show no evidence request until a case is opened.

4. During milestone 3, run mocked publication tests and inspect workflow syntax:

       uv run pytest -q tests/test_publish.py tests/test_cli.py
       just smoke
       rg -n "schedule|gh-pages|--clobber" .github/workflows scripts src justfile

   The publication workflow may contain none of the forbidden operations. Any `--clobber` occurrence is a failure. Dashboard publication has only `workflow_dispatch`.

5. During milestone 4 and final verification:

       uv run pytest -q tests/test_reproduce.py tests/test_publish.py
       just schemas
       just smoke
       just unit
       just frontend
       just ci
       rg -n "dataset\.json|merge_datasets|gh-pages|history/campaigns" . --glob '!docs/dashboard-pages-releases-proposal.md' --glob '!docs/exec-plans/dashboard-pages-releases.md' --glob '!.git/**'

   The repository search should return no stale runtime/documentation path. If Docker or network prevents `just ci`, preserve exact output, run every deterministic subset, and retry when the external prerequisite is available.

6. Live GitHub validation uses the actual workflow filename selected in milestone 3:

       git push origin main
       gh workflow list
       gh workflow run "<manual-publication-workflow>" --ref main
       gh run watch "<run-id>" --exit-status
       gh release view "campaign-<id>" --json tagName,targetCommitish,assets,url
       gh release download "campaign-<id>" --dir "<temporary-directory>"
       curl --fail --location "https://kleverhq.github.io/svtorture/data/index.json"
       curl --fail --location "https://kleverhq.github.io/svtorture/data/trends.json"

   Record the actual run ID, Release URL, tag peeled commit, asset hashes, Pages URL, and HTTP checks under `Artifacts and Notes`.

## Validation and Acceptance

The implementation is accepted only when all seventeen criteria from `docs/dashboard-pages-releases-proposal.md` are demonstrated, not merely when tests are green. In practical terms, Pages must deploy through an Actions artifact and contain complete data for exactly one timestamp-selected latest campaign; trends must contain unchanged summaries for all valid campaign Releases; local assembly must support N bundles and comparisons; startup must avoid evidence; case detail must load one case-centric shard preserving bounded stream metadata; public validation and evaluator semantics must remain intact; Release/tag behavior must be immutable and idempotent; the Pages size report and hard 650 MiB gate must execute; and no permanent v5 `dataset.json` evidence copy may remain.

Strict-model tests must reject unknown fields and mismatched resource kinds/IDs. Cross-resource tests must detect missing/duplicated results, verdict/evidence disagreement, forged metrics, wrong bytes/hashes, and unsafe ZIP members. Frontend tests must assert request order and explicit unavailable-history behavior. Replay tests must assert equivalent execution inputs and tamper rejection. Workflow tests and the live run must prove permissions, tag target, Release assets, latest-by-campaign-time selection, Pages deployment, and manual-only cadence.

## Idempotence and Recovery

Bundle and site outputs are written to temporary directories and atomically replaced only after validation. Re-running export for the same canonical campaign produces identical bytes. Local assembly may be repeated after deleting only ignored `dashboard/dist/data` or `.local-dashboard`; it never changes bundle inputs.

Published Release identity is immutable. A matching published Release is a no-op. A matching partial draft may receive only missing expected assets and then be published. Any wrong tag target, changed asset, changed summary, extra asset, or duplicate campaign ID with different content stops without deletion or overwrite. Pages is a fully derived cache and may be rebuilt from Release summaries and the chosen ZIP at any time.

Git commits are made after each reviewed stage. If a stage fails review, fix it before advancing rather than stacking unresolved work. Do not rewrite or discard the user's pre-existing commit. Generated and ignored outputs remain outside commits.

## Artifacts and Notes

Initial baseline on 2026-07-31:

    just smoke
    ...
    All checks passed!
    Success: no issues found in 20 source files
    101 passed in 0.63s
    Test Files 12 passed (12)
    Tests 74 passed (74)

Current repository state at plan creation:

    ## main...origin/main [ahead 1]
    ?? docs/dashboard-pages-releases-proposal.md

The one pre-existing local commit is `2bb5c69 docs: remove execution plans`; it belongs to the user and must be preserved. Append milestone test summaries, review findings/fixes, commit IDs, bundle size measurements, GitHub run IDs, Release URLs, and Pages HTTP evidence here as work proceeds.

## Interfaces and Dependencies

`src/svtorture/dashboard_models.py` will expose strict Pydantic transport models named `DashboardIndex`, `CampaignSummary`, `CampaignTrends`, `CampaignManifest`, `CampaignCatalog`, `CampaignVerdicts`, and `CampaignEvidenceShard`. All inherit the repository's strict frozen model behavior, reject unknown fields, and use top-level version 6/kind discriminants. `CampaignSummary.archive` is optional in the model but required by public publisher context.

`src/svtorture/publish.py` will retain `validate_public_campaign(catalog: Catalog, campaign: Campaign) -> None` and expose minimal bundle/site operations. Exact helper names may be adjusted once implementation reveals the smallest coherent API, but the stable conceptual interfaces are:

    export_campaign_bundle(catalog: Catalog, campaign: Campaign, output: Path, *, public: bool = False) -> Path
    validate_campaign_bundle(bundle_root: Path) -> CampaignManifest
    write_campaign_archive(bundle_root: Path, output: Path) -> Path
    project_campaign_summary(manifest: CampaignManifest, archive: ArchiveMetadata | None = None) -> CampaignSummary
    assemble_dashboard_site(inputs: Iterable[Path], output_data: Path) -> DashboardIndex
    assemble_public_pages(built_site: Path, summaries: Iterable[CampaignSummary], latest_bundle: Path, output: Path, *, size_limit: int = 650 * 1024 * 1024) -> DashboardIndex

The local assembler accepts either a ZIP whose only tree is `campaigns/<id>/...`, an unpacked directory containing `campaigns/<id>/...`, or the direct `campaigns/<id>` directory for convenience. It normalizes all three through the same validator.

The frontend exports matching TypeScript interfaces and one resource loader/cache keyed by absolute resolved URL. It performs no browser ZIP import and has no persistent cache. Resource hrefs are resolved relative to the JSON document that owns them.

GitHub publication uses the already available `gh` executable and `GITHUB_TOKEN`. No Personal Access Token, backend, or third-party Release action is added. ZIP uses Python `zipfile`; HTTP replay uses the existing bounded credential-free standard-library loader pattern; hashing uses `hashlib`; file serving remains Python's ordinary HTTP server.

Plan revision note (2026-07-31): initial self-contained plan created after repository exploration and incorporation of the user's summary/tag/legacy/manual-trigger decisions. The four milestones intentionally match the accepted proposal and add a blocking focused review plus control pass after each stage. The proposal remains an untracked user-owned artifact; only English implementation artifacts are committed.