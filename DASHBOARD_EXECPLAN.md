# Refactor the dashboard into an evidence-first investigation console

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the `exec-plan` skill. It is intentionally stored at the repository root while active because completed files under `docs/plans/` were removed by explicit maintainer request. After the work is complete and this plan's final outcome has been committed, remove this file in the final cleanup commit; the Git history will retain the execution record without leaving a completed plan in the documentation tree.

## Purpose / Big Picture

SVTORTURE's dashboard currently presents sound conformance evidence through a spacious, dark, promotional layout. A user must pass large slogans, repeated explanatory prose, many bordered cards, and a detailed status legend before reaching the working data. After this refactor, the first screen will instead answer practical questions: which campaign is selected, which tools ran, how many results pass or need attention, what changed, and where to inspect the evidence. The requirements matrix will become the primary compact work surface, evidence will use a master-detail investigation layout, and history will summarize changes rather than relying on a chart alone.

The user will also be able to select `Auto`, `Light`, or `Dark` from a visible theme control. `Auto` will be the default when no preference has been saved and will follow the browser/operating-system `prefers-color-scheme` setting. Explicit light or dark choices will persist locally across reloads.

The result is observable by running `just dashboard-build <campaign.json>`, then `just dashboard-serve`, and opening `http://localhost:4173`. At desktop and mobile widths the useful data should begin near the top, controls should remain available while scrolling, status categories should be easy to scan, and all four views should work in both light and dark themes.

## Non-Goals

This work will not change campaign, requirement, result, metric, or publication schemas. It will not change the evaluator's conformance semantics or collapse detailed statuses in stored data. The five broad status groups are a presentation and filtering aid only; detailed statuses and reasons remain visible in evidence. It will not add a server, mutable dashboard state, external font downloads, a design-system dependency, Storybook, or a permanent browser-automation dependency. It will not modify the trusted publication checks. It will not claim meaningful trend analysis when the dataset has only one campaign.

## Progress

- [x] (2026-07-21 11:14Z) Read the supplied `review.md`, current dashboard components, model, tests, stylesheet, package configuration, local guidance, and current aggregate dataset.
- [x] (2026-07-21 11:17Z) Captured matrix, evidence, history, and campaign desktop baselines plus matrix/evidence mobile baselines under `/tmp/svtorture-dashboard-visual-before/` and inspected them.
- [x] (2026-07-21 11:20Z) Added Auto/Light/Dark preference state and persistence, pre-render application, five grouped statuses, URL-backed `statusGroup`/`caseId`, comparable-campaign change analysis, and deterministic tests (12 frontend tests pass).
- [ ] Replace the promotional top section and scattered controls with a compact overview and sticky global control bar.
- [ ] Refactor the requirements matrix into a dense sticky-column table with a separate detail inspector.
- [ ] Refactor case evidence into a master-detail investigation surface and connect matrix drill-down to it.
- [ ] Add change analysis to history and simplify campaign provenance into compact drill-down content.
- [ ] Replace the dark-only decorative stylesheet with semantic light/dark tokens and compact responsive layouts.
- [ ] Exercise all views and interactive states visually in Auto, Light, and Dark at desktop and mobile widths.
- [ ] Run all frontend and repository gates, perform focused reviews and a fresh control review, fix findings, record outcomes, commit the implementation, and remove this completed plan.

## Surprises & Discoveries

- Observation: The current local dataset is unusually useful for matrix and evidence validation because it is one complete aggregate campaign containing Icarus, Slang, and Verilator: 12 requirements, 12 cases, 36 results, and three metric points.
  Evidence: `dashboard/dist/data/dataset.json` reports campaign `20260721T103601Z-5c523fd5a0275145` with three tools and 36 results.
- Observation: The repository has Chrome 145 and Firefox 152 installed but no Playwright, Cypress, Storybook, or screenshot package.
  Evidence: browser executable inspection found `/usr/bin/google-chrome` and `/usr/bin/firefox`; `npm --prefix dashboard ls --depth=0` found no browser automation dependency.
- Observation: The stylesheet names `Manrope` and `DM Mono`, but neither font is bundled or loaded.
  Evidence: the only font references are `font-family` declarations in `dashboard/src/styles.css`. The redesign must use reliable system UI and monospace stacks so screenshots do not depend on untracked host fonts.
- Observation: Most dashboard navigation state already lives in the query string, which makes deterministic screenshots of views and filters practical without adding browser automation.
  Evidence: `dashboard/src/model.ts` implements `filtersFromSearch` and `filtersToSearch`; `dashboard/src/App.tsx` reads `view` from the query string.
- Observation: The baseline confirms the review quantitatively: at 1440×1200 the matrix header only begins around the bottom 275 pixels, after the hero, 255-pixel metrics, filters, tabs, and a ten-item legend.
  Evidence: `/tmp/svtorture-dashboard-visual-before/matrix-desktop.png` shows no requirement rows in the initial viewport.
- Observation: The current 390-pixel layout has page-level clipping before the working interface is reached.
  Evidence: `/tmp/svtorture-dashboard-visual-before/matrix-mobile.png` crops the hero sentence and wide metric content at the right edge, and the first viewport contains branding plus only part of two metric cards.
- Observation: The server repeatedly requests a missing favicon during every screenshot route.
  Evidence: the baseline server log records HTTP 404 for `/favicon.ico`; a small inline or committed local favicon can remove avoidable console/network noise without adding a dependency.
- Observation: This Node 25/Vitest environment exposed a nonfunctional built-in `window.localStorage` shim unless a storage file is configured.
  Evidence: the first component test run warned about `--localstorage-file` and its `getItem`, `setItem`, and `clear` members were not functions. The production theme code already fails safely; tests now install a deterministic in-memory `Storage` implementation.

## Decision Log

- Decision: Treat the review's design recommendations as one evidence-first workflow rather than a cosmetic color refresh.
  Rationale: The complaint concerns information hierarchy, density, taxonomy, and navigation. Changing colors alone would preserve the root problem.
  Date/Author: 2026-07-21 / coding agent.
- Decision: Keep detailed result statuses unchanged but map them into five top-level UI groups: Pass, Fail, Unsupported, Infra/unclear, and Unscored.
  Rationale: The first scan needs fewer categories, while evidence and methodology still require exact distinctions such as unsupported revision, inconclusive, harness error, not applicable, and unavailable.
  Date/Author: 2026-07-21 / coding agent.
- Decision: Add a separate `statusGroup` URL-backed filter while preserving the existing exact `status` filter under advanced filters.
  Rationale: This keeps existing deep-link semantics and enables quick top-level chips without overloading one field with two meanings.
  Date/Author: 2026-07-21 / coding agent.
- Decision: Implement theme selection with repository code and CSS custom properties, not a dependency. Store only explicit `auto`, `light`, or `dark` in local storage under `svtorture-theme`; missing or invalid data means `auto`.
  Rationale: The platform already provides `prefers-color-scheme`, CSS variables, and local storage. No current requirement justifies a theme library.
  Date/Author: 2026-07-21 / coding agent.
- Decision: Make matrix detail a separate inspector next to the virtualized table rather than expanding variable-height rows.
  Rationale: Constant compact row height makes virtualization predictable, keeps scanning dense, and gives anchors/cases enough space without inflating every row.
  Date/Author: 2026-07-21 / coding agent.
- Decision: Keep selected evidence case URL-backed and let matrix case actions navigate directly to that case in the evidence view.
  Rationale: Investigation state should be shareable and the expected user path is summary, anomaly, drill-down, proof.
  Date/Author: 2026-07-21 / coding agent.
- Decision: Compare a selected campaign only with the newest earlier campaign containing the same tool/profile set.
  Rationale: Comparing an aggregate three-tool campaign with an unrelated single-tool smoke campaign would manufacture changes from selection differences rather than tool behavior.
  Date/Author: 2026-07-21 / coding agent.
- Decision: Use installed headless Chrome and temporary scripts under `/tmp` for visual evidence; do not add Playwright yet.
  Rationale: URL-backed states and native screenshot support are sufficient for this concrete redesign. A permanent dependency is justified only if maintainers later request committed visual regression baselines.
  Date/Author: 2026-07-21 / coding agent.

## Outcomes & Retrospective

The foundation milestone is complete without schema or dependency changes. Theme state defaults safely to Auto and is applied before React renders; exact statuses now have a tested five-group presentation mapping; URL state includes grouped status and selected evidence case; and campaign comparison refuses unrelated tool/profile sets. Layout and palette work remain.

## Context and Orientation

SVTORTURE turns SystemVerilog tool runs into immutable campaign JSON files. `src/svtorture/publish.py` exports one or more campaigns into `dashboard/dist/data/dataset.json`. The React application fetches that file through `dashboard/src/useDataset.ts`; there is no live backend. `dashboard/src/types.ts` describes the exported data, and those types must remain compatible.

`dashboard/src/App.tsx` owns the selected top-level view and URL-backed filters. It currently renders a sticky brand header, a large hero statement, tool metric cards, filters, tabs, a detailed legend, and one of four views. `dashboard/src/Filters.tsx` renders campaign/tool/search and advanced filters. `dashboard/src/model.ts` parses URL filters, selects campaigns, groups results, compares campaigns, and filters requirements/cases. `dashboard/src/model.test.ts` is the deterministic unit coverage for those transformations.

`dashboard/src/HeadlineMetrics.tsx` currently renders tall cards for headline tool metrics. `dashboard/src/MatrixView.tsx` uses TanStack Table and TanStack Virtual to render requirement rows; TanStack Virtual means only rows near the scroll viewport are mounted. `dashboard/src/EvidenceView.tsx` renders every case as a large card with expandable tool observations. `dashboard/src/HistoryView.tsx` renders an ECharts time series and metric table. `dashboard/src/CampaignView.tsx` renders campaign provenance cards. `dashboard/src/StatusBadge.tsx` maps detailed statuses to visual labels. `dashboard/src/styles.css` contains all visual and responsive behavior and is currently dark-only with many literal colors.

A status group is a broad UI category derived from an exact stored `Status`. `conforming` maps to Pass. `nonconforming` maps to Fail, including a known-fail annotation. Both unsupported statuses map to Unsupported. `harness-error` and `inconclusive` map to Infra/unclear because neither provides verified support. `not-applicable`, `skipped-unavailable`, and `not-run` map to Unscored. This mapping must never change campaign data or the evaluator.

A master-detail layout places a compact selectable list on the left and the complete selected record on the right. On narrow screens the list and detail stack vertically. A sticky control bar remains visible below the site header while content scrolls. A semantic color token is a CSS variable named for purpose, such as `--text`, `--surface`, or `--status-fail`, rather than for one hard-coded dark color.

The current local visual dataset is already built at `dashboard/dist/data/dataset.json` and is ignored by Git. If it is absent, first run a campaign such as `just latest verilator smoke`, copy the printed campaign path, and run `just dashboard-build "<campaign-path>"`. A multi-tool aggregate campaign gives better matrix coverage when available.

## Open Questions

There are no blocking product questions. The review establishes the direction, and the added requirement establishes theme behavior. During implementation, visual measurements may require small density adjustments; those decisions must be recorded here rather than deferred to the user.

## Plan of Work

First capture the current dashboard at representative desktop and mobile widths. Save screenshots outside the repository or in ignored `.svtorture/` storage, inspect them, and record objective issues such as the amount of vertical space before the matrix, clipping, weak contrast, and horizontal overflow. This baseline prevents an aesthetic refactor from being judged only from source code.

Next extend `dashboard/src/model.ts`. Add `StatusGroup`, the exact-status-to-group mapping, labels and symbols for the five groups, `statusGroup` and selected-case state to URL filters, grouped filter matching, and pure helpers that compare the selected campaign with its previous campaign. The change helper must identify regressions, new passes, other status changes, tool source changes, corpus/denominator changes, known failures, missing tools, and infrastructure results without changing scoring. Extend `dashboard/src/model.test.ts` and `dashboard/src/testDataset.ts` with multiple campaigns and representative statuses so every branch is deterministic.

Add `dashboard/src/ThemeControl.tsx`. It will export the `ThemePreference` type and a small accessible control labeled Theme. Its initializer reads `svtorture-theme`, accepts only `auto`, `light`, and `dark`, defaults to `auto`, and immediately sets `document.documentElement.dataset.theme`. Changes update both the root attribute and local storage. Add a component test proving default Auto, persistence, invalid-value fallback, and explicit Light/Dark behavior. Auto's effective palette remains CSS-driven so a live operating-system preference change does not require React state.

Refactor `dashboard/src/App.tsx`, `dashboard/src/Filters.tsx`, and `dashboard/src/HeadlineMetrics.tsx` around a compact workflow. The header keeps the small brand, dataset visibility, source link, and theme control. Remove the large hero and ideological footer sentence. Add a concise selected-campaign header with timestamp, completeness, campaign identifier, and only operational context. Make the headline area compact: requirements/cases/tools, grouped result counts, regressions, known failures, missing tools, and small per-tool coverage rows. Place tabs, search, campaign, tool/profile, grouped-status chips, changed toggle, advanced exact filters, and clear action into one sticky workspace control region. Keep all filters URL-backed and preserve absent/incomplete evidence.

Refactor `dashboard/src/MatrixView.tsx` as the primary work surface. Use constant compact virtual rows, sticky Clause and Requirement columns, one-line summaries with full text available by title, five grouped status cells, and clearer cell backgrounds. Selecting a requirement opens a separate inspector containing the full summary, anchors, supporting cases, phase/expectation tags, and actions that switch to the selected case in evidence. The table header and first columns remain visible while scrolling. On narrow screens, preserve horizontal scrolling and stack the inspector below the matrix instead of crushing columns.

Refactor `dashboard/src/EvidenceView.tsx` into master-detail. The left list shows compact case identity, requirement/clause, and grouped verdict indicators. The right pane shows the selected case's requirement, expectation, oracle, sources, exact per-tool verdicts, matched diagnostics, observations, hashes, and reproduction command. Detailed status text remains available here. Selection updates a URL parameter so reload and shared links preserve the investigation target. Empty filtered results receive an explicit message.

Refactor `dashboard/src/HistoryView.tsx` to accept the dataset and selected campaign, then place a compact change summary before the chart: regressions, new passes, other changed judgments, tool revision changes, and corpus/denominator boundaries. Keep the chart and table as secondary evidence. For one campaign, show an honest `No previous campaign` state. Refactor `dashboard/src/CampaignView.tsx` into a compact campaign list with provenance details hidden behind drill-down, retaining every current hash, trust, platform, tool, image, and preparation field.

Rewrite `dashboard/src/styles.css` around light-default semantic tokens plus a dark token override. `:root` supplies the light palette and `color-scheme: light`; `@media (prefers-color-scheme: dark)` applies dark tokens when the root theme is Auto; `[data-theme="dark"]` forces dark and `[data-theme="light"]` forces light. Use system UI and monospace stacks. Reduce panel borders, large radii, oversized text, repeated card backgrounds, padding, and vertical gaps. Improve text and separator contrast in both palettes. Keep focus-visible styles, minimum touch targets where controls require them, reduced-motion behavior, and responsive breakpoints.

Finally run visual and automated verification. Start the static server and capture each view in Auto/light/dark at desktop and mobile widths. Use URL-backed filters for failure-only, unsupported-only, changed, empty-result, and selected-case states. Use a temporary Chrome DevTools Protocol script only where a click/open state cannot be encoded in the URL. Inspect console errors, network failures, horizontal document overflow, sticky positioning, long code wrapping, and both palettes. Fix substantive issues before focused code and UX reviews, then run a fresh control review.

### Concrete Steps

Work from `/home/esynr3z/projects/sv-torture`.

1. Save and inspect the current visual baseline without modifying tracked output:

       just dashboard-serve 4173
       google-chrome --headless=new --window-size=1440,1200 \
         --screenshot=/tmp/svtorture-dashboard-before-matrix.png \
         'http://127.0.0.1:4173/?view=matrix'
       google-chrome --headless=new --window-size=390,844 \
         --screenshot=/tmp/svtorture-dashboard-before-mobile.png \
         'http://127.0.0.1:4173/?view=matrix'

   Expect both PNG files to exist and the dataset request to return HTTP 200.

2. Implement model and theme changes, then run:

       npm --prefix dashboard run typecheck
       npm --prefix dashboard test

   Expect all existing and new model/theme tests to pass.

3. Implement layout/view/CSS milestones incrementally. After each view, run:

       npm --prefix dashboard run typecheck
       npm --prefix dashboard test
       npm --prefix dashboard run build

   Expect TypeScript to report no errors, Vitest to pass, and Vite to create `dashboard/dist/index.html`.

4. Exercise the final application:

       just dashboard-build ".svtorture/campaigns/20260721T103601Z-5c523fd5a0275145/campaign.json"
       just dashboard-serve 4173

   If that ignored local campaign no longer exists, substitute any valid campaign path printed by `just latest verilator smoke`; use more than one compatible campaign when validating history.

5. Capture final screenshots for `matrix`, `evidence`, `history`, and `campaigns` at 1440×1200 and 390×844. Repeat at least the matrix and evidence views with `data-theme` forced through the UI to Light and Dark. Save temporary screenshots under `/tmp`, not the repository.

6. Run complete gates:

       just frontend
       just smoke
       just precommit
       just ci
       git diff --check

   Expect every command to exit zero. `just ci` may record ordinary tool nonconformance but must have no infrastructure failure.

### Validation and Acceptance

A fresh browser profile with no `svtorture-theme` key must show Theme = Auto. When the operating system requests dark, Auto must render the dark palette; when it requests light, Auto must render the light palette. Selecting Light or Dark must immediately switch the palette and survive reload. Selecting Auto again must resume the operating-system preference. All controls must have an accessible label and visible keyboard focus.

At 1440 pixels wide, useful campaign summary and controls must appear without a promotional hero. The control region must remain available while scrolling. The matrix must show sticky headers and first columns, compact one-line rows, grouped verdicts for all selected tool profiles, and a separate requirement inspector. Choosing a supporting case in that inspector must switch to Evidence and select the case.

At 390 pixels wide, no page-level horizontal overflow is allowed. The matrix may scroll horizontally inside its own container because its columns are intentionally tabular. Controls and evidence master-detail must stack, text and commands must wrap or scroll inside bounded containers, and no control may be unreachable.

Grouped status chips must filter by the five presentation groups while Advanced filters can still select an exact stored status. Query-string reload must preserve view, campaign, tool, search, grouped status, exact status, changed/disagreement flags, and selected evidence case. Detailed evidence must continue to distinguish every exact status and reason.

History must summarize what changed relative to the previous campaign before presenting the chart. With no previous campaign it must state that comparison is unavailable, not display zero regressions as if a comparison occurred. Campaign provenance must retain all current facts but keep them in compact drill-down content.

Automated acceptance requires strict TypeScript, all Vitest tests, Vite build, `just frontend`, `just smoke`, `just precommit`, and `just ci` to pass. Visual acceptance requires before/after screenshots inspected in both themes and desktop/mobile layouts with no console errors, failed dataset request, accidental page overflow, illegible muted text, duplicate top-level status labels, or major clipping.

### Idempotence and Recovery

All source edits and test commands are repeatable. `dashboard/dist/`, `.svtorture/`, and `/tmp` screenshots are ignored or external and may be deleted and regenerated safely. Theme storage affects only the current browser origin and can be reset with `localStorage.removeItem('svtorture-theme')`. If a refactor milestone breaks the frontend, use `git diff` to isolate that milestone; do not edit generated dataset JSON or committed campaign/schema contracts to make the UI pass. Do not commit screenshots, browser profiles, generated `dist/`, or local campaign data.

The supplied `review.md` is an untracked task input. Do not silently commit it as durable product documentation. Preserve it while implementing; disposition can be confirmed at final cleanup if the maintainer has not already removed it.

### Artifacts and Notes

The baseline product diagnosis is: “beautiful static evidence brochure” where the desired result is a “sharp engineering investigation console.” The implementation principle is `Evidence first, chrome second`.

The current route shape is:

    http://localhost:4173/?view=matrix
    http://localhost:4173/?view=evidence
    http://localhost:4173/?view=history
    http://localhost:4173/?view=campaigns

The current aggregate local visual fixture is:

    .svtorture/campaigns/20260721T103601Z-5c523fd5a0275145/campaign.json

It contains three tools and is suitable for grouped matrix verdicts and evidence. It has only one timestamp, so it is not sufficient by itself to prove change analysis.

### Interfaces and Dependencies

Do not add runtime dependencies. Continue using React 19, TypeScript 7, Vite 8, TanStack Table, TanStack Virtual, and ECharts from `dashboard/package.json`.

In `dashboard/src/model.ts`, define and export:

    export type StatusGroup = "pass" | "fail" | "unsupported" | "issue" | "unscored";
    export function statusGroup(status: Status): StatusGroup;
    export function compareCampaigns(dataset: Dataset, selected?: Campaign): CampaignComparison;

Extend `Filters` with URL-backed `statusGroup` and `caseId` strings. `CampaignComparison` must be a plain typed object containing whether a prior campaign exists, counts and case identifiers for regressions/new passes/other changes, tool revision changes, and corpus boundary state. Keep these functions pure and deterministic.

In `dashboard/src/ThemeControl.tsx`, define:

    export type ThemePreference = "auto" | "light" | "dark";
    export function ThemeControl(): JSX.Element;

The component owns only browser preference state; it does not enter campaign URLs or datasets.

Change `MatrixView` to accept an inspection callback:

    onInspectCase: (caseId: string) => void

Change `EvidenceView` to accept selected-case state:

    selectedCaseId: string
    onSelectCase: (caseId: string) => void

Change `HistoryView` to receive the dataset and selected campaign so it can render change analysis without duplicating model logic. Preserve all current public dataset types in `dashboard/src/types.ts`.

Revision note (2026-07-21 11:14Z): Created the initial self-contained plan from `review.md`, the requested Auto/Light/Dark behavior, current frontend architecture, available browser tooling, and the local aggregate visual dataset.

Revision note (2026-07-21 11:17Z): Recorded baseline desktop/mobile screenshot evidence, initial-viewport density, mobile clipping, and the repeated missing-favicon request before implementation.

Revision note (2026-07-21 11:20Z): Recorded the completed theme/model foundation, comparable-campaign rule, deterministic storage test shim, and passing frontend tests.
