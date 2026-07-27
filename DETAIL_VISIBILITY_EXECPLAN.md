# Keep selected corpus entities visible

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the `exec-plan` skill.

## Purpose / Big Picture

A copied Case or Requirement link already opens the correct view, entity, and campaign, but the selected row can remain outside the viewport. The Cases desktop layout also uses the page scrollbar for both the list and details, so browsing lower cases pushes the selected details away. After this work, opening a deep link reveals the selected Requirement row or Case item immediately. On desktop, Cases uses a one-third/two-thirds composition with independent vertical scrolling for the case list and detail pane; scrolling one column does not move the other or the page. A recipient can therefore open a shared link and inspect the intended evidence without first hunting through the corpus.

## Non-Goals

This change does not alter URL parameters, campaign selection, filtering semantics, datasets, campaign schemas, evidence evaluation, the Requirements inspector contents, or mobile navigation structure. It does not add a dependency or replace TanStack Virtual. At widths of 900 px or less, the existing stacked Cases layout remains and the global page scrollbar remains available.

## Progress

- [x] (2026-07-27 10:08Z) Confirmed the required desktop behavior, including an independently scrollable details pane when its content exceeds the viewport.
- [ ] Add selection-reveal behavior to the virtualized Requirements matrix and test a non-first selected row.
- [ ] Add selection-reveal behavior to Cases and test initial and changed selections.
- [ ] Change the desktop Cases workspace to one-third/two-thirds columns with bounded, independent vertical scroll regions and preserve the stacked mobile/short-viewport fallback.
- [ ] Run focused review, repository gates, and wide/mobile browser validation; remove this completed plan.

## Surprises & Discoveries

- Observation: Requirements uses `useWindowVirtualizer`, so a deep-linked row might not exist in the DOM and cannot be revealed reliably with only `Element.scrollIntoView()`.
  Evidence: `dashboard/src/MatrixView.tsx` renders only `virtualizer.getVirtualItems()`. Selection reveal must first use `virtualizer.scrollToIndex()`.

- Observation: Cases currently has no bounded workspace height or column scroll containers.
  Evidence: `.evidence-workspace` defines only a two-column grid, while `.case-list` and `.evidence-pane` have no vertical overflow policy; scrolling therefore moves the global page and sends details above the viewport.

## Decision Log

- Decision: Use TanStack Virtual's existing `scrollToIndex()` for Requirements and native `scrollIntoView({block: "nearest"})` for Case buttons.
  Rationale: The virtualizer is the only reliable owner of rows that have not yet been mounted. All Case buttons are mounted, so native reveal is the smallest solution there.
  Date/Author: 2026-07-27 / assistant

- Decision: At desktop widths above 900 px and viewport heights above 600 px, bound the Cases workspace to the remaining viewport and give both columns independent vertical overflow with contained scroll chaining.
  Rationale: The user explicitly requested that list browsing not move details and confirmed that long details may have their own scrollbar. The existing mobile and short-height fallbacks need global flow to avoid unusably small nested regions.
  Date/Author: 2026-07-27 / assistant

- Decision: Set the desktop grid to `minmax(320px, 1fr) minmax(0, 2fr)`.
  Rationale: This gives the case list approximately one third of available width, never narrower than 320 px, while leaving two thirds for evidence details.
  Date/Author: 2026-07-27 / assistant

## Outcomes & Retrospective

Implementation has not started. Completion requires observable selection reveal in both views, stable details while the Case list scrolls, independent access to long details, no page-level horizontal overflow, and clean tests/reviews.

## Context and Orientation

The repository root is `/home/esynr3z/projects/sv-torture`. The React dashboard lives in `dashboard/src/`. `dashboard/src/App.tsx` parses URL filters and passes `filters.requirementId` to `MatrixView` and `filters.caseId` to `EvidenceView`. `dashboard/src/MatrixView.tsx` renders a horizontally scrollable Requirements matrix and virtualizes rows against the browser window with `useWindowVirtualizer`. When a requirement is selected, a sticky `.matrix-inspector` appears on the right. `dashboard/src/EvidenceView.tsx` renders all cases as buttons in `.case-list` and the selected case in `.evidence-pane`. `dashboard/src/styles.css` owns responsive layout and defines 900 px as the breakpoint where these workspaces stack.

A “deep link” here means a dashboard URL containing `view=matrix&requirementId=...` or `view=evidence&caseId=...`, optionally with `campaign=...`. “Reveal” means moving only as much as needed so the selected row or item is visible. An “independent scroll region” means an element with a bounded height and `overflow-y: auto`; wheel or touch scrolling inside it changes that element's `scrollTop` rather than the document's `scrollY`.

The sticky site header and workspace controls expose CSS variable `--content-sticky-top`, calculated from the site-header height, measured workspace-bar height, and gap. The desktop Cases workspace can use `calc(100dvh - var(--content-sticky-top) - 16px)` as its available height after those sticky controls. The panel already clips overflow and has a border, so the two child columns can own vertical scrolling without another wrapper.

## Open Questions

None. The user confirmed that long Case details should use their own scrollbar. Mobile remains stacked; desktop list/details become independently scrollable.

## Plan of Work

In `dashboard/src/MatrixView.tsx`, derive the selected requirement's row index from the table rows. Add an effect keyed by the selected identity and index. When a valid selection changes, schedule `virtualizer.scrollToIndex(index, { align: "center" })` for the next animation frame and cancel that frame on cleanup. Do not scroll for an empty or filtered-out selection. Add `dashboard/src/MatrixView.test.tsx` with a local mock of `useWindowVirtualizer`; select a non-first requirement and assert that index is passed to `scrollToIndex`. The test must also confirm the selected inspector remains present.

In `dashboard/src/EvidenceView.tsx`, retain refs for case buttons by ID. Add an effect keyed by `selected?.id` that schedules the selected button's `scrollIntoView({ block: "nearest", inline: "nearest" })`. The nearest alignment avoids unnecessary movement when a user clicks an already visible item. Extend `dashboard/src/EvidenceView.test.tsx` to spy on native reveal for both initial deep-link selection and a rerender with another selected case.

In `dashboard/src/styles.css`, change the base desktop grid ratio to one-third/two-thirds. Inside a media query requiring both `min-width: 901px` and `min-height: 601px`, set `.evidence-workspace` to the remaining dynamic viewport height, stretch both columns, and apply `min-height: 0`, `overflow-y: auto`, `overscroll-behavior-y: contain`, and stable scrollbar gutters to `.case-list` and `.evidence-pane`. Keep horizontal overflow hidden in the detail pane. Existing max-width 900 px rules continue to stack columns; because bounded height and overflow are desktop-only, mobile retains global scrolling. Existing max-height 600 px behavior likewise remains global.

Update `dashboard/README.md` to describe deep-link reveal and desktop Cases column scrolling without duplicating CSS implementation details.

### Concrete Steps

Work from `/home/esynr3z/projects/sv-torture`.

First add focused component tests and implementation, then run:

    npm --prefix dashboard run typecheck
    npm --prefix dashboard test

Expect all dashboard test files to pass, including new tests proving a non-first Requirement index and selected Case button are revealed.

Build and export the current local campaign:

    npm --prefix dashboard run build
    uv run svtorture dashboard export \
      .svtorture/campaigns/20260726T201718Z-33850b3740767141/campaign.json \
      --visibility local \
      --output dashboard/dist/data/dataset.json

Use Chrome at a wide viewport such as 1840x1004. Open a direct Requirement URL whose row is near the end of the matrix and observe that the highlighted row is immediately visible while the inspector remains pinned. Open a direct Case URL whose item is near the end of the list and observe that the selected item is visible in the left column. Scroll the left column and verify the detail column's scroll position and `document.scrollY` do not change. Scroll the detail column and verify the list does not move. Measure the columns and confirm the list is approximately one third of the workspace. Repeat at 390x844 and confirm the stacked layout, global page scroll, and absence of horizontal overflow.

Finally run:

    just smoke
    git diff --check

Request focused frontend review, resolve every substantive finding, rerun affected gates, record evidence below, remove this completed plan, and commit the final removal.

### Validation and Acceptance

The feature is accepted only when all of the following are observable:

1. Loading a direct Requirement URL for a non-first row leaves that highlighted row in the visible browser viewport and keeps its inspector visible.
2. Loading a direct Case URL for a non-first case reveals that item in the left list and displays its details on the right.
3. At 1840x1004 and other desktop sizes above the breakpoints, the Case list is approximately one third of the workspace and details are approximately two thirds.
4. The Case list and details each have independent vertical scrolling. Scrolling either does not move the other and does not change the document scroll position. Scroll chaining at a column boundary does not move the page.
5. At 390x844 and at viewport heights of 600 px or less, Cases remains stacked in normal document flow with no page-level horizontal overflow.
6. Existing URL-backed campaign/entity selection, Copy link behavior, keyboard controls, source viewer, and tool observations remain functional.
7. Type checking, all frontend tests, production build, `just smoke`, and `git diff --check` pass; focused review has no unresolved substantive finding.

### Idempotence and Recovery

All edits are source and test changes and can be rerun safely. Production output under `dashboard/dist/` and local campaign data under `.svtorture/` are ignored. If browser validation changes the generated dataset, rerun the export command above. If a scheduled animation frame survives a rerender, the effect cleanup must cancel it; do not add timers without cleanup. If independent scrolling creates a short-viewport trap, keep it constrained to the combined desktop width/height media query rather than weakening the mobile fallback.

### Artifacts and Notes

Current failing visual behavior is captured in `/tmp/pi-clipboard-88debbc6-6858-4b3d-a17b-4f0663fad1c3.png`: the selected Case is low in the left list while the right details have scrolled entirely above the viewport, leaving a blank right pane.

Expected final evidence should record selected IDs, selected element rectangles, workspace and column widths, `scrollTop` values for both columns, unchanged `document.scrollY` while scrolling each column, body width versus viewport width, and runtime/network error arrays.

### Interfaces and Dependencies

Do not add dependencies. Continue using React effects and refs, TanStack Virtual's existing `scrollToIndex(index, { align: "center" })`, and native `Element.scrollIntoView()`.

`MatrixView` keeps its existing public props. Internally it gains selection-reveal scheduling through the object returned by `useWindowVirtualizer`.

`EvidenceView` keeps its existing public props. Internally it gains a `Map<string, HTMLButtonElement>` ref for case buttons and reveal scheduling.

No dataset, URL, or backend interface changes are permitted.

Revision note (2026-07-27 10:08Z): Created the self-contained plan after the user confirmed independent scrolling for long Case details.
