# Replace Changes with strict historical Trends

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the repository's `exec-plan` skill. It is temporary: after every acceptance criterion is verified, remove it so completed plans and `docs/plans/` do not remain in the repository.

## Purpose / Big Picture

After this change, the dashboard tab currently labelled `Changes` becomes `Trends`. A user can choose exactly one of five historical measurements from a compact selector: Tool pass rate, Requirements coverage, Cases coverage, Requirements density, or Cases density. The default remains Tool pass rate. The selected measurement occupies the existing full-page interactive chart and retains the current UTC date ranges, slider, wheel or pinch zoom, drag pan, keyboard point navigation, provenance inspector, and URL-backed investigation state.

Pass-rate and coverage charts display a labelled horizontal 100% reference with a small amount of vertical headroom. Density charts display labelled 1× and 2× references and enough headroom to keep the 2× reference visible. Tool and Profile facets affect Tool pass rate only; they remain visible but disabled with an explanation for corpus-wide trends.

Historical corpus values must be honest. Each new immutable campaign records the four exact numerator/denominator pairs from the catalog used for collection. Campaign schema version 3 and dashboard dataset schema version 3 are strict replacements: no parser, fallback, aliases, migrations, optional fields, or old-history accommodation remains. The four current local version-2 campaigns are deleted, one new full multi-tool campaign is collected, and the generated dashboard dataset contains only that campaign.

## Non-Goals

This work does not add more than one visible chart, multi-select trend overlays, new chart dependencies, automated workflow activation, historical reconstruction from removed campaigns, legacy `Changes` or `history` URL aliases, or compatibility with campaign/dataset schema version 2. It does not change conformance judgment, requirement weighting, the corpus summary strips, or the meaning of the four corpus formulas.

## Progress

- [x] (2026-07-26 12:13Z) Researched the campaign, publication, metric, dashboard, URL, ECharts, responsive, accessibility, and test paths.
- [x] (2026-07-26 12:13Z) Chose a strict campaign-owned corpus snapshot and a single selected trend with no compatibility path.
- [x] (2026-07-26 12:27Z) Added strict campaign schema version 3 corpus metrics, regenerated the campaign schema, and updated backend tests and durable documentation; 68 focused tests pass.
- [x] (2026-07-26 12:36Z) Replaced Changes/history terminology and URL state with Trends, implemented the five-option selector and generic single chart, and updated frontend tests/documentation; typecheck, 48 tests, and production build pass.
- [x] (2026-07-26 12:48Z) Deleted all current local campaigns, collected one clean full schema-v3 campaign, and rebuilt a schema-v3 dashboard dataset containing only that campaign.
- [ ] Run focused review, repository gates, browser validation, and completion audit; remove this completed ExecPlan (completed: two focused lanes and first fresh control review, all five findings fixed, focused follow-ups clean, browser validation, 128 non-Docker tests, `just smoke`, 48 frontend tests, and 11 Docker tests; remaining: second/final control review, final gates, and plan removal).

## Surprises & Discoveries

- Observation: The existing `Dataset.corpus_coverage` is only the catalog snapshot at export time and cannot reconstruct historical values after catalog changes.
  Evidence: `src/svtorture/publish.py::merge_datasets()` replaces that top-level object with the newest export, while historical `Campaign` and `MetricPoint` records currently contain no coverage/density snapshot.

- Observation: Campaign schema version currently reuses the version-2 execution/result alias, although campaigns need to change without changing execution plans or normalized results.
  Evidence: `src/svtorture/models.py::Campaign.schema_version` uses `ContractSchemaVersion`; adapters and evaluator also correctly remain version 2.

- Observation: The current Changes chart is already a single ECharts instance with UTC ranges, inside and slider data zoom, wheel/pinch zoom, drag pan, keyboard navigation, provenance, and viewport-filling desktop layout.
  Evidence: `dashboard/src/HistoryView.tsx` and the `.dashboard--history` rules in `dashboard/src/styles.css`; the feature should generalize this path rather than create parallel charts.

- Observation: Tool/Profile facets derive from historical metric points and already provide the desired pass-rate series filtering, but corpus trends are global and must not silently react to those facets.
  Evidence: `dashboard/src/Filters.tsx` builds historical tool/profile pairs for Trends. Native-disabled facet buttons plus an accessible scope explanation preserve toolbar geometry and make the distinction explicit.

- Observation: An ECharts mark-line label positioned at the line end was clipped by the right chart edge, even though the reference line itself was correct.
  Evidence: the first wide Chrome screenshot showed only `100%` while the SVG contained `100% saturation`. Moving the label to `insideEndTop` made the complete reference label visible without increasing margins.

- Observation: Pydantic integer fields remain coercive unless strictness is set on the fields, even inside this repository's frozen/extra-forbidden `StrictModel`.
  Evidence: focused contract review found that corpus operands could normalize strings, booleans, and integral floats despite the generated JSON Schema requiring integers. Both operands now use `Field(strict=True, ge=0)`, and all three coercible forms have rejection tests.

- Observation: The existing append-only dataset merge checked only the top-level schema number and treated missing arrays as empty.
  Evidence: focused contract review showed that a relabelled version-2 campaign or missing `metrics` could pass the version check and lose/preserve invalid history. Both merge inputs now require the complete collection envelope, valid strict v3 campaigns, exact campaign provenance, and metric identities tied to known campaigns.

- Observation: Manifest hashes are broader than active trend operands and therefore create false chart boundaries for hash-only metadata changes.
  Evidence: focused UI review found corpus boundary keys using manifest hashes. They now use only the active ratio numerator and denominator; tests prove hash-only stability and numerator-change boundaries.

- Observation: Dataset visibility was metadata rather than an enforced merge boundary, so a local dataset could be preserved when a new public dataset became the result envelope.
  Evidence: the first fresh control review found that `merge_datasets()` inherited the new visibility. Merge now requires identical visibility, public history requires GitHub Actions trust on every preserved campaign, and publication tests exercise both rejection paths.

- Observation: Stable metric identity checks do not prove a complete metric point is safe for the frontend.
  Evidence: the first fresh control review found that truncated/coercive/timestamp-invalid points, duplicates, and campaign-mismatched tool/profile pairs could survive. `PublishedMetricPoint` now validates every required field with strict counts/booleans and ISO timestamps before membership and uniqueness checks.

## Decision Log

- Decision: Add `CampaignSchemaVersion` fixed at integer 3 while leaving execution plans, observations, and normalized results on `ContractSchemaVersion` 2.
  Rationale: The user explicitly rejects compatibility and wants old campaigns replaced, but unrelated public contracts have not changed. A campaign-only version is the narrow strict break.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Add one required `corpus_metrics` object to every campaign, containing Requirements and Cases summaries, each with exact Coverage and Density integer ratios.
  Rationale: A campaign is the immutable evidence unit and already supplies timestamp, commit, manifest, trust, and aggregation provenance. Storing one corpus snapshot there avoids fabricated historical values and avoids redundant per-tool copies.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Compute corpus metrics once from `Catalog.corpus_metrics()` and require campaign verification and aggregation to preserve an exact match.
  Rationale: Collection, missing/preparation records, aggregation, and publication need one shared source of truth. Verification prevents a campaign snapshot from disagreeing with the requirement, case, or anchor catalog.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Bump the dashboard dataset to schema version 3 and make merge reject every other version without fallback.
  Rationale: Current campaign history will be deleted as requested; retaining optional fields or old merge behavior would be compatibility code with no valid consumer.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Rename the route and internal feature from `history` to `trends`, using URL parameters `trend`, `trendRange`, and `trendPoint`; do not recognize old names.
  Rationale: This is a replacement rather than a compatibility transition. Keeping old implementation vocabulary and URLs would make the durable contract misleading.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Keep exactly one ECharts instance and switch its normalized data/configuration according to the selected trend.
  Rationale: This directly satisfies the one-chart requirement and preserves the proven zoom, pan, resize, point-selection, and inspector behavior without parallel implementations.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Use a native radio group for the five-option selector, as a left rail on wide screens and a horizontal row on narrow screens.
  Rationale: Radio semantics guarantee one selection and keyboard behavior without custom state machinery; the responsive row preserves chart width on phones.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Disable Tool/Profile buttons for corpus trends while preserving their selected URL values.
  Rationale: Corpus measurements do not depend on tools. Visible disabled controls prevent toolbar jumps and preserve the user's pass-rate context when switching back.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Use a fixed 0–110% vertical domain for Tool pass rate and Coverage, and a density domain whose maximum is at least 2.25× and at least 10% above observed values.
  Rationale: The 100% line remains inside the plot with a small gap. Both 1× and 2× density references remain visible, while valid values above 2× are never clipped.
  Date/Author: 2026-07-26 / coding assistant

## Outcomes & Retrospective

The backend, frontend, and evidence-reset milestones are complete. Every campaign constructor records a typed, non-coercive corpus snapshot from `Catalog.corpus_metrics()`, catalog verification rejects changed operands, aggregation preserves the snapshot, dataset merging validates its strict v3 campaign/provenance envelope, and the generated campaign schema exposes the required object. The visible/internal route is now Trends; one native radio group drives one generic ECharts plot with pass-rate/coverage/density units, reference levels, URL state, disabled corpus facets, exact-operand boundaries, keyboard navigation, and provenance. The sole local campaign `20260726T124655Z-ec42760bfad01a5c` has 3 tools, 12 cases, 36 results, and operands 16/16963, 17/16, 12/12, and 12/12. Wide and 390 px Chrome checks show one plot, correct 100%/1×/2× references, no page overflow, no runtime/network errors, and URL-backed keyboard provenance. Two focused review lanes reported three findings; all were fixed and both follow-up reviews are clean. The first fresh control review found visibility-boundary and incomplete-metric validation gaps; both are fixed with strict tests. The second/final control review and plan removal remain.

## Context and Orientation

SVTORTURE is a standards-driven SystemVerilog conformance framework. `src/svtorture/models.py` defines strict frozen Pydantic public records. `src/svtorture/catalog.py` loads requirements, cases, tools, and the committed IEEE anchor index. `src/svtorture/campaign.py` collects and verifies immutable campaign JSON. `src/svtorture/publish.py` turns campaigns into the static dashboard dataset and append-merges public history. `schemas/campaign.schema.json` is generated from the campaign model by `just schemas`; it must never be edited manually.

A corpus ratio is an object with nonnegative integer `numerator` and `denominator`. Requirements Coverage is unique referenced anchors divided by all anchors in `standards/ieee-1800-2023-anchors.json`. Requirements Density is unique requirement–anchor pairs divided by unique referenced anchors. Cases Coverage is unique requirements linked by either `primary_requirement` or `related_requirements` divided by all requirements. Cases Density is unique case–requirement pairs divided by unique linked requirements. Coverage numerators cannot exceed their denominators. Within each summary, the density denominator equals the coverage numerator.

`dashboard/src/App.tsx` owns tabs, global URL state, campaign controls, and Tool/Profile facets. `dashboard/src/HistoryView.tsx` currently owns Changes. `dashboard/src/model.ts` parses and serializes URL state. `dashboard/src/Filters.tsx` renders Tool/Profile facets. `dashboard/src/styles.css` supplies the full-page chart layout. `dashboard/src/types.ts` describes the generated JSON. Frontend tests use `dashboard/src/testDataset.ts` and mock the modular ECharts imports.

A measurement boundary is a visible line break and diamond point where the operands defining a trend change. For Tool pass rate, the existing corpus case hash or denominator change remains the boundary. For corpus trends, any numerator or denominator change in the active ratio creates the boundary. A reference line is a labelled horizontal ECharts `markLine`: 100% for pass-rate/coverage or 1× and 2× for density.

The current ignored campaigns are under `.svtorture/campaigns/`. They are schema version 2 and must be deleted, not migrated. `just latest-all all` resolves and runs Slang, Icarus, and Verilator over the complete suite through Docker and writes one new multi-tool campaign. `just dashboard-build "$campaign" local` builds the frontend and exports the selected campaign to ignored `dashboard/dist/data/dataset.json`.

## Open Questions

There are no unresolved product questions. The user confirmed that exactly one trend is visible and explicitly required deletion rather than compatibility for current campaigns.

## Plan of Work

First, introduce the strict evidence contract. In `src/svtorture/models.py`, define `CampaignSchemaVersion` fixed at 3 plus strict `CorpusRatio`, `CorpusMetricSummary`, and `CorpusMetrics` models. Validate coverage bounds and the density-denominator relationship. Change only `Campaign.schema_version` to the new version and add required `corpus_metrics`.

In `src/svtorture/catalog.py`, add `Catalog.corpus_metrics()`. Build sets of requirement–anchor and case–requirement pairs so duplicates are naturally removed. Include primary and related case requirements. Use the catalog's validated explicit `anchor_index` so external runtime indexes remain supported. Return the typed snapshot.

In `src/svtorture/campaign.py`, create every ordinary, missing, preparation-failure, and aggregate campaign with schema version 3 and the snapshot. `verify_campaign_against_catalog()` must compare the campaign snapshot with `catalog.corpus_metrics()`. Aggregation must require identical snapshots and copy the first snapshot. Update `tests/helpers.py` and every direct constructor. Regenerate `schemas/campaign.schema.json` with `just schemas`. Add strict rejection tests for version 2, missing/extra/invalid ratios, altered snapshots, aggregation mismatch, duplicate links, related requirements, and explicit anchor-index use. Update `docs/architecture.md`, `docs/methodology.md`, and `docs/reproduction.md` to state that campaigns preserve the exact corpus trend operands.

In `src/svtorture/publish.py`, retain the detailed top-level breakdown but source its aggregate summary from `Catalog.corpus_metrics()` so summary strips and campaign history use the same formulas. Change dataset schema version and merge acceptance to exactly 3. Add tests that exported campaigns carry the snapshot, sequential merge retains it, collisions remain strict, and version 2 datasets are rejected.

Second, replace the frontend terminology and state. Rename `dashboard/src/HistoryView.tsx` and its test to `TrendsView.tsx` and `TrendsView.test.tsx`. In `dashboard/src/model.ts`, replace `HistoryRange`, `HistoryState`, and history URL helpers with trend equivalents. Define the five strict trend IDs. Parse only `trend`, `trendRange`, and `trendPoint` for `view=trends`; omit default Tool pass rate and default month from the URL. Use `tool:<campaign>:<tool>:<profile>` and `corpus:<campaign>` point keys. Generalize range bounds to accept timestamped objects so campaigns and metric points share one UTC domain.

In `dashboard/src/App.tsx`, use the `trends` view ID and visible label, retain disabled Campaign/From/To controls, own selected trend/range/point state, and clear invalid selections. Pass a facet-disabled flag to `Filters` for every non-tool trend. In `dashboard/src/Filters.tsx`, rename history mode to trends, retain historical pair choices, and native-disable all Tool/Profile facet buttons with one visually hidden description stating that they apply only to Tool pass rate.

In `dashboard/src/TrendsView.tsx`, define the five radio options and normalize either `Dataset.metrics` or `Dataset.campaigns` into one chart datum shape. Tool pass rate continues to group lines by tool/profile and filters on both facets. Corpus trends create exactly one line from campaign snapshots and ignore facets. Zero denominators produce unavailable points rather than zero values. Preserve existing date ranges, slider, inside zoom, pan, reset, resize, chart click, blank-canvas close, keyboard navigation, and inspector focus.

Register ECharts `MarkLineComponent`. Place reference markers in one silent helper series so they remain visible even with no valid data and are not repeated per tool series. Pass-rate/coverage charts use percent formatting and a 0–110 domain. Density uses × formatting and a dynamic maximum above both 2× and all observed data. Update the accessible chart-group label to name the active trend, unit, reference lines, and keyboard instructions. The inspector must show trend label, formatted value, exact operands, campaign ID/time, commit, requirement/case/selection hashes, and Tool provenance only for Tool pass rate.

In `dashboard/src/styles.css`, rename history selectors to trends, add a compact 150–170 px desktop selector rail, preserve one chart filling the remaining workspace, add the existing inspector as a third column, and turn the selector into a horizontal row at the existing narrow breakpoint. Do not add a nested chart scrollbar or a second chart.

Update `dashboard/src/types.ts` to require dataset schema 3 and campaign corpus metrics. Update `dashboard/src/testDataset.ts` with at least two campaigns whose corpus operands differ. Extend `dashboard/src/model.test.ts`, `dashboard/src/App.test.tsx`, `dashboard/src/Filters.test.tsx`, and the renamed chart tests for strict URLs, exactly one selected radio, every trend calculation, reference lines/headroom, disabled facet scope, boundaries, zero denominators, tool filtering, keyboard selection, provenance, and one chart instance. Update `dashboard/README.md` and root `README.md` to use Trends and document the five definitions.

Third, after implementation and deterministic checks pass, commit the source contract and dashboard changes. Remove `.svtorture/campaigns`, `.svtorture/work`, and the generated dataset. Run one clean full collection with `just latest-all all`. Confirm it contains schema version 3, all three public tools, 12 cases, 36 results, and the expected current corpus operands. Build the dashboard from exactly that campaign.

Finally, run focused backend/frontend tests, `just smoke`, all non-Docker tests, the production build, and Docker tests when available. Start `dashboard/dist` and inspect wide and mobile Chrome layouts: one plot, selector behavior, disabled facets, markers, zoom/pan, point provenance, no runtime/network errors, and no page-level horizontal overflow. Request focused code/UX review, fix every substantive finding, run a fresh control review, update this plan's outcomes, and delete the plan.

### Concrete Steps

Run commands from `/home/esynr3z/projects/sv-torture`.

During backend implementation:

    uv run pytest -q tests/test_catalog_models.py tests/test_campaign_metric.py tests/test_publish.py
    just schemas
    just metadata

Expected focused output is all selected tests passing and no generated-schema diff after a second `just schemas`.

During frontend implementation:

    npm --prefix dashboard run typecheck
    npm --prefix dashboard test
    npm --prefix dashboard run build

Expected output is a clean TypeScript check, all Vitest tests passing, and a production bundle under `dashboard/dist/`.

After source work is committed and the working tree is clean:

    rm -rf .svtorture/campaigns .svtorture/work dashboard/dist/data/dataset.json
    just latest-all all
    campaign="$(find .svtorture/campaigns -mindepth 2 -maxdepth 2 -name campaign.json -print -quit)"
    just dashboard-build "$campaign" local

Inspect the resulting JSON:

    python3 - <<'PY'
    import json
    from pathlib import Path
    campaign_path = next(Path('.svtorture/campaigns').glob('*/campaign.json'))
    campaign = json.loads(campaign_path.read_text())
    dataset = json.loads(Path('dashboard/dist/data/dataset.json').read_text())
    print(campaign['schema_version'], len(campaign['tools']), len(campaign['case_ids']), len(campaign['results']))
    print(campaign['corpus_metrics'])
    print(dataset['schema_version'], len(dataset['campaigns']))
    PY

Expected values are campaign schema `3`, three tools, 12 cases, 36 results, requirements Coverage `16/16963`, requirements Density `17/16`, cases Coverage `12/12`, cases Density `12/12`, dataset schema `3`, and one campaign.

Run final gates:

    uv run pytest -q -m 'not docker'
    just smoke
    npm --prefix dashboard run build
    git diff --check

If Docker is available, also run:

    just docker-fake

For browser validation, serve the already built output:

    just dashboard-serve 4173

Open `http://127.0.0.1:4173/?view=trends`. Confirm Tool pass rate is selected by default, the chart has a 100% reference below its top edge, Tool/Profile facets alter only that trend, each corpus option creates one series from campaign snapshots, density shows 1× and 2×, and the URL records non-default trend/range/point selections.

### Validation and Acceptance

The backend contract is accepted when campaign schema version 2 is rejected, campaign schema version 3 requires exact corpus metrics, catalog verification detects altered operands, aggregate inputs with different snapshots are rejected, generated schemas are current, and dataset merging accepts only version 3.

The Trends UI is accepted when the tab and URL use `Trends`/`view=trends`, exactly one of five radio options is selected, Tool pass rate is the default, and changing a radio keeps exactly one ECharts plot. Pass-rate and Coverage options must show a labelled 100% reference with visible headroom. Density options must show labelled 1× and 2× references with visible headroom. Tool/Profile facets must work for Tool pass rate and be visibly and accessibly disabled for the four corpus trends.

Interaction is accepted when all existing named UTC ranges, reset, slider, wheel/pinch zoom, drag pan, point click, keyboard navigation, blank-canvas close, and provenance inspection remain functional. Corpus inspectors must expose exact operands and campaign provenance. Measurement changes must break lines and mark boundary points rather than implying continuity.

Layout is accepted when a wide viewport uses a left selector and a plot filling the remaining page workspace, a narrow viewport uses a horizontal selector without page-level horizontal overflow, no nested vertical chart scroller exists, and runtime/network consoles are clean.

Evidence reset is accepted when only one local version-3 campaign exists after collection and the generated dataset contains one campaign with the expected four corpus ratios. No version-2 campaign or compatibility parser remains.

### Idempotence and Recovery

Formatting, schema generation, tests, and frontend builds are repeatable. Campaign JSON is immutable, so never rerun a collection into an existing campaign ID. The explicit deletion command is destructive by user request and intentionally has no migration path. If full collection fails after writing a partial campaign, delete `.svtorture/campaigns` and `.svtorture/work` and rerun `just latest-all all`; do not edit campaign JSON by hand. If Docker/network preparation fails before a campaign is written, rerun after resolving the infrastructure issue.

`just dashboard-build` is safe to repeat for the same single campaign. Do not use a broad `find` after tests that create ignored fake campaigns; select the one real full campaign and verify its tools before export.

### Artifacts and Notes

Current catalog operands before implementation are:

    Requirements Coverage  16 / 16963
    Requirements Density   17 / 16
    Cases Coverage          12 / 12
    Cases Density           12 / 12

Current local evidence consists of four ignored schema-version-2 campaigns dated 2026-07-21 and 2026-07-22. These are intentionally disposable and must not be copied into the new dataset.

### Interfaces and Dependencies

Do not add runtime dependencies. Continue using Pydantic for strict backend models, React native radio controls for selection, and the existing modular ECharts package with `SVGRenderer`. Add only the already installed `MarkLineComponent` registration.

At completion, `src/svtorture/models.py` must expose conceptually equivalent strict interfaces:

    CampaignSchemaVersion = integer exactly 3

    CorpusRatio:
        numerator: nonnegative integer
        denominator: nonnegative integer

    CorpusMetricSummary:
        coverage: CorpusRatio
        density: CorpusRatio

    CorpusMetrics:
        requirements: CorpusMetricSummary
        cases: CorpusMetricSummary

    Campaign:
        schema_version: CampaignSchemaVersion
        corpus_metrics: CorpusMetrics
        ...existing required campaign fields...

`src/svtorture/catalog.py::Catalog.corpus_metrics()` must return `CorpusMetrics` from the full loaded catalog and explicit anchor index.

The frontend must expose these strict trend identifiers:

    tool-pass-rate
    requirements-coverage
    cases-coverage
    requirements-density
    cases-density

The non-default URL contract is `?view=trends&trend=<id>&trendRange=<range>&trendPoint=<key>`. No `view=history`, `historyRange`, or `historyPoint` interpretation remains.

Revision note (2026-07-26 12:13Z): Created the self-contained implementation plan after backend and frontend execution-path research and the user's explicit no-compatibility decision.

Revision note (2026-07-26 12:27Z): Recorded completion of the strict campaign/dataset contract milestone and its focused test evidence.

Revision note (2026-07-26 12:36Z): Recorded completion of the Trends frontend milestone, strict URL rename, chart behavior, and frontend test/build evidence.

Revision note (2026-07-26 12:50Z): Recorded destructive old-campaign reset, the clean full replacement campaign, initial browser evidence, and the clipped reference-label correction.

Revision note (2026-07-26 13:01Z): Recorded focused-review findings and verified fixes for strict operands, strict dataset merge envelopes, and exact-operand corpus boundaries, plus final Python/frontend/Docker gate evidence.

Revision note (2026-07-26 13:16Z): Recorded first-control findings and fixes for public/local visibility isolation and complete strict metric-point validation.
