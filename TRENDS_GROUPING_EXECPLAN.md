# Group corpus trends and add chapter filtering

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current while work proceeds. Maintain it according to the repository `exec-plan` skill, then remove it after completion because completed plans are not retained.

## Purpose / Big Picture

The Trends view currently offers five choices and charts Requirements and Cases separately. After this change it offers exactly three choices: Pass rate, Coverage, and Density. Coverage and Density each draw two lines, Requirements and Cases, in the same single interactive plot. Pass rate keeps Tool/Profile quick facets. Coverage and Density replace those facets with a compact `CHAPTER` dropdown that supports All by default or any combination of IEEE 1800-2023 chapters and annexes.

The 100% reference label becomes simply `100%`. Percent plots retain their current 0–110 vertical domain for headroom, but never display a `110%` tick label. Hovering a left-rail trend option explains its meaning, with the same explanation available to assistive technology.

Historical chapter filters must be honest. Campaign schema version 4 therefore stores all 58 per-part Coverage and Density operand rows for both Requirements and Cases. Schema version 3 is rejected without fallback or migration. The sole current campaign is deleted and one new full multi-tool schema-version-4 campaign is collected.

## Non-Goals

This work does not add multiple chart widgets, overlay Pass rate with corpus lines, preserve schema-version-3 campaigns, reconstruct removed history, activate GitHub Actions, add dependencies, change the four corpus formulas, or change conformance judgments. It does not display `110%`; the hidden 10% remains only as visual headroom.

## Progress

- [x] (2026-07-26 19:54Z) Confirmed product decisions: one Coverage chart with two lines, one Density chart with two lines, chapters plus annexes, and strict campaign replacement.
- [x] (2026-07-26 20:08Z) Added strict schema-version-4 per-part campaign snapshots, made publication use the shared typed snapshot, regenerated the campaign schema, and passed 76 focused backend tests plus metadata validation.
- [x] (2026-07-26 20:18Z) Reduced Trends to three choices, implemented two-line corpus plots, hover/accessibility descriptions, hidden 110% label, and URL-backed chapter/annex multiselect facets; typecheck, 48 frontend tests, and production build pass.
- [ ] Delete the schema-version-3 campaign, collect one full schema-version-4 campaign, and rebuild the dataset.
- [ ] Run focused reviews, full gates, and desktop/mobile browser validation; remove this completed plan.

## Surprises & Discoveries

- Observation: The current top-level `Dataset.corpus_coverage` already contains every chapter and annex row, but each campaign stores only four aggregate ratios.
  Evidence: `src/svtorture/publish.py::_corpus_coverage()` exports breakdown rows while `Campaign.corpus_metrics` contains only `requirements.coverage`, `requirements.density`, `cases.coverage`, and `cases.density`. Historical chapter filtering cannot use the replaceable top-level snapshot.

- Observation: Per-part operand sums reproduce aggregate formulas without double counting.
  Evidence: requirement links are assigned by each anchor's owning standard part, and case links are assigned by the linked requirement's owning chapter. Standard parts are disjoint, so selected-row numerators and denominators can be summed before division.

## Decision Log

- Decision: Bump only `CampaignSchemaVersion` from exactly 3 to exactly 4; execution/result contracts remain version 2 and dashboard dataset remains strict version 3.
  Rationale: Campaign evidence changes shape, while execution evidence and the dataset envelope do not. Old campaigns are deleted rather than supported.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Add a required ordered 58-row `breakdown` to both `CorpusMetricSummary` objects in each campaign.
  Rationale: This mirrors the existing dashboard coverage shape, avoids duplicated part metadata inside a third structure, and makes each campaign self-contained for historical filters.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Move all aggregate and per-part corpus calculation into `Catalog.corpus_metrics()` and serialize that same typed object for campaign and top-level dataset coverage.
  Rationale: Collection, verification, trend history, and summary strips must share one formula implementation rather than recomputing parallel dictionaries.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Keep three strict trend identifiers: `pass-rate`, `coverage`, and `density`; remove all five old identifiers and URL interpretations.
  Rationale: The user requested a direct replacement and repository policy rejects compatibility aliases.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Represent All chapter selection as an empty array and selected parts as stable keys `chapter:<number>` or `annex:<letter>` in repeated `chapter` URL parameters.
  Rationale: Empty state is compact and naturally means no restriction. Kind-qualified keys remain unambiguous and preserve chapter/annex identity.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Coverage and Density produce exactly two series named `Requirements` and `Cases`. Each selected part set is reduced by summing exact row operands, then applying the active formula.
  Rationale: This gives the requested two lines while preserving mathematically correct combined Coverage or Density for arbitrary part combinations.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Retain y-axis maximum 110 for percent headroom, return an empty axis label above 100, and label the reference line `100%`.
  Rationale: The visible plot spacing remains unchanged while `110%` and `saturation` disappear.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Use native `title` hover text on each trend option plus an `aria-describedby` hidden explanation.
  Rationale: This supplies the requested hover tooltip and an equivalent keyboard/screen-reader description without another tooltip dependency.
  Date/Author: 2026-07-26 / coding assistant

## Outcomes & Retrospective

The backend and frontend milestones are complete. `Catalog.corpus_metrics()` owns aggregate and ordered 58-row calculations for both scopes; campaign schema version 4 requires coherent breakdowns and publication serializes the same snapshot. Trends now has Pass rate, Coverage, and Density; corpus selections produce Requirements and Cases lines from summed selected operands. Pass rate shows Tool/Profile while corpus trends show a chapter/annex multiselect, all state is URL-backed, option descriptions work on hover and through ARIA, the 100% reference is concise, and 110% is unlabeled while headroom remains. Replacement evidence and final validation remain.

## Context and Orientation

`src/svtorture/models.py` defines strict frozen Pydantic contracts. `CorpusMetrics` currently contains two `CorpusMetricSummary` values; each summary has aggregate Coverage and Density ratios. `src/svtorture/catalog.py::Catalog.corpus_metrics()` computes those four aggregates. `src/svtorture/publish.py::_corpus_coverage()` separately reads the committed anchor index and computes the 58-row breakdown. `src/svtorture/campaign.py` writes and verifies campaign snapshots. `schemas/campaign.schema.json` is generated only by `just schemas`.

Requirements Coverage is unique referenced anchors divided by all anchors. Requirements Density is unique requirement–anchor pairs divided by covered anchors. Cases Coverage is unique linked requirements divided by all catalog requirements. Cases Density is unique case–requirement pairs divided by covered requirements. For selected parts, add each selected row's numerator and denominator separately and then divide. Zero denominators yield unavailable points, not zero.

The standard index has 41 chapter rows and 17 annex rows. Requirements rows use each anchor's actual owning part, so supporting annex anchors contribute to annexes. Cases rows use the linked requirement's numeric owning chapter; annex case rows remain zero until annex-owned requirements exist.

`dashboard/src/model.ts` owns trend kind/range/point URL state. `dashboard/src/App.tsx` coordinates Trends and quick facets. `dashboard/src/Filters.tsx` currently shows Tool/Profile facets and merely disables them for corpus trends. `dashboard/src/TrendsView.tsx` normalizes tool points or one corpus scope into ECharts series. `dashboard/src/styles.css` owns the full-page layout. Frontend tests mock ECharts and use `dashboard/src/testDataset.ts`.

The ignored current campaign is `.svtorture/campaigns/20260726T124655Z-ec42760bfad01a5c/campaign.json`. It is schema version 3 and must be deleted after implementation is committed. `just latest-all all` collects one full Slang/Icarus/Verilator campaign.

## Open Questions

There are no open product questions. The user confirmed two lines in each corpus plot, chapters plus annexes, and destructive strict campaign replacement.

## Plan of Work

First, change the evidence contract. In `src/svtorture/models.py`, set `CampaignSchemaVersion` to exactly 4. Define a strict part kind and part metric row containing stable ID, kind, title, Coverage, and Density. Add ordered breakdown rows to `CorpusMetricSummary`. Validate unique part keys, coherent per-row ratios, and exact equality between aggregate operands and sums of breakdown operands.

In `src/svtorture/catalog.py`, replace aggregate-only `Catalog.corpus_metrics()` with the complete calculation currently split across Catalog and publication. Read ordered part metadata and anchor ownership from the catalog's validated explicit `anchor_index`; emit every chapter and annex including zero rows. Group requirement links by anchor part and case links by linked requirement chapter. Return typed `CorpusMetrics` with summaries and ordered breakdowns.

In `src/svtorture/publish.py`, delete the parallel `_corpus_coverage()` calculation and serialize `Catalog.corpus_metrics()` for top-level `corpus_coverage`. Keep strict dataset history validation and semantic provenance. In `src/svtorture/campaign.py` and helpers, construct schema version 4. Regenerate `schemas/campaign.schema.json`. Update tests for all 58 rows, zero annexes, related requirements, duplicate links, explicit anchor index, aggregate-sum invariants, schema-3 rejection, campaign verification, publication self-merge, and strict malformed breakdown rejection. Update architecture/methodology/reproduction wording if needed.

Second, reduce frontend state. In `dashboard/src/model.ts`, define `TrendKind` as `pass-rate | coverage | density`. Add `parts: string[]` to `TrendState`, parse repeated validated `chapter` parameters only under `view=trends`, deduplicate them, and omit them for All. Update point keys so corpus points include both campaign and scope.

In `dashboard/src/App.tsx`, treat only Pass rate as tool-scoped. For Coverage/Density pass the selected parts and a chapter-selection callback. Validate corpus point keys against both Requirements and Cases. Preserve Tool/Profile values and chapter values while switching trends.

In `dashboard/src/Filters.tsx`, show Tool/Profile facets for Pass rate. For Coverage/Density replace them with one `CHAPTER` control using native disclosure and checkboxes. Its summary says All when no parts are selected, otherwise reports the chosen count. The menu lists all 41 chapters and 17 annexes in standard order, has an All option, supports any combination, and has bounded popup scrolling. Keep the page and chart free of new vertical scroll surfaces.

In `dashboard/src/TrendsView.tsx`, expose three radio options and attach concise `title` and `aria-describedby` definitions. Pass rate retains one line per selected tool/profile. Coverage and Density each normalize every campaign into two points/series, reducing selected breakdown rows by exact operand sums. Use Requirements and Cases in legend, tooltip, keyboard ordering, point URL keys, and inspector. Continue exact-operand boundary markers independently per line. Change the percent marker text to `100%` and use an axis formatter that hides values above 100 while preserving max 110.

Update styles for the three-item rail and chapter dropdown. Update frontend fixtures to contain complete breakdowns and tests for strict URLs, All/default behavior, arbitrary combinations including annexes, two corpus series, formulas, zero denominators, tool/chapter facet swapping, preserved selections, hover/accessibility descriptions, hidden 110 label, 100 marker, keyboard selection, and one chart.

Third, commit the implementation, delete `.svtorture/campaigns`, `.svtorture/work`, and generated dataset, then run `just latest-all all`. Build the dashboard from exactly the new campaign and verify schema version 4, 58 Requirements rows, 58 Cases rows, 3 tools, 12 cases, 36 results, and unchanged aggregate operands.

Finally, run focused backend/frontend tests, all non-Docker tests, `just smoke`, Docker tests, production export, and wide/mobile Chrome. Inspect Pass rate facets, Coverage/Density chapter combinations, both lines, `100%` without `110%`, 1×/2×, URL state, tooltips, keyboard provenance, and overflow. Run focused reviews plus a fresh control review, fix substantive findings, audit completion, update outcomes, and remove this plan.

### Concrete Steps

Run from `/home/esynr3z/projects/sv-torture`:

    uv run pytest -q tests/test_catalog_models.py tests/test_campaign_metric.py tests/test_publish.py
    just schemas
    just metadata
    npm --prefix dashboard run typecheck
    npm --prefix dashboard test
    npm --prefix dashboard run build

After source commits and a clean tracked tree:

    rm -rf .svtorture/campaigns .svtorture/work dashboard/dist/data/dataset.json
    just latest-all all
    campaign="$(find .svtorture/campaigns -mindepth 2 -maxdepth 2 -name campaign.json -print -quit)"
    just dashboard-build "$campaign" local

Expected replacement evidence is one schema-version-4 campaign with three tools, 12 cases, 36 results, two 58-row breakdowns, aggregate operands `16/16963`, `17/16`, `12/12`, and `12/12`, plus a strict schema-version-3 dataset.

Final commands:

    uv run pytest -q -m 'not docker'
    just smoke
    just docker-fake
    git diff --check

Serve with `just dashboard-serve 4173` and open `http://127.0.0.1:4173/?view=trends`.

### Validation and Acceptance

Backend acceptance requires schema version 3 campaigns to fail loading, version 4 to require all typed breakdowns, every aggregate to equal row sums, every standard part including zero rows to be present, and strict history self-merge to validate the generated dataset.

UI acceptance requires exactly three radio options and one chart. Pass rate shows Tool/Profile facets. Coverage and Density show CHAPTER instead, default All, and accept any chapter/annex combination. Coverage and Density each show exactly Requirements and Cases lines computed from selected rows. The active URL preserves non-default repeated chapter selections.

Percent charts retain top headroom but contain no visible `110%` and label the reference `100%`. Density retains 1× and 2× references. Every trend option has a hover tooltip and accessible description. Existing zoom, pan, ranges, reset, keyboard navigation, provenance, full-page desktop layout, responsive narrow layout, and one-chart behavior remain.

Evidence acceptance requires exactly one new schema-version-4 full campaign and one generated dataset containing it. No old campaign or compatibility code remains.

### Idempotence and Recovery

Schema generation, tests, and builds are repeatable. The campaign deletion is intentionally destructive by confirmed user request. If collection fails, remove partial `.svtorture/campaigns` and `.svtorture/work`, then rerun `just latest-all all`; never edit campaign JSON. Tests may leave ignored fake campaigns, so preserve only the identified real replacement campaign before the final export.

### Artifacts and Notes

Current aggregates before the schema change are:

    Requirements Coverage  16 / 16963
    Requirements Density   17 / 16
    Cases Coverage          12 / 12
    Cases Density           12 / 12

The current schema-version-3 campaign is disposable and intentionally not migrated.

### Interfaces and Dependencies

Do not add dependencies. Use existing Pydantic, React native details/checkboxes, and modular ECharts.

Campaign schema version 4 must conceptually expose:

    CorpusPartMetric:
        id, kind, title, coverage, density

    CorpusMetricSummary:
        coverage, density, breakdown[58]

    CorpusMetrics:
        requirements, cases

Frontend trend IDs must be exactly:

    pass-rate
    coverage
    density

Selected part URL values must be stable keys such as:

    ?view=trends&trend=coverage&chapter=chapter%3A5&chapter=annex%3AA

Revision note (2026-07-26 19:54Z): Created the self-contained plan after the user confirmed two-line corpus plots, chapter-plus-annex filtering, and strict replacement evidence.

Revision note (2026-07-26 20:08Z): Recorded completion of the strict shared per-part campaign/publication contract and focused backend evidence.

Revision note (2026-07-26 20:18Z): Recorded completion of grouped frontend trends, part facets, tooltips, percent labeling, tests, and production build.
