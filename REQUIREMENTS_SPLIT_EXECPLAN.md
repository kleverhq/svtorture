# Replace the Requirements matrix with list and details

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the `exec-plan` skill.

## Purpose / Big Picture

The Requirements tab currently allocates one table column per tool/profile. That layout becomes progressively harder to read and requires horizontal scrolling as tools are added. After this change, Requirements behaves like Cases: a one-third list remains visible on the left, two-thirds details remain visible on the right, and each column scrolls independently. The list uses compact profile verdict indicators while the detail pane presents anchors, linked cases, and tool/profile evidence vertically, so adding tools increases vertical evidence rather than page width.

Existing copied links such as `?view=matrix&requirementId=...&campaign=...` continue to open the same Requirement and campaign. The internal URL token `matrix` remains only for compatibility; no matrix or table remains in the rendered interface.

## Non-Goals

This work does not change dataset schemas, campaign evidence, filters, scoring, case definitions, campaign selection, copied-link parameters, or backend publication. It does not add a list/matrix mode toggle. It does not keep the old table as a hidden or secondary view. It does not rename the `view=matrix` URL token because doing so would break links already copied by users.

## Progress

- [x] (2026-07-27 10:45Z) Confirmed complete table removal and a Cases-style Requirements layout.
- [x] (2026-07-27 11:00Z) Extracted shared viewport sizing and selection reveal/detail reset into `useSplitWorkspace.ts`; Cases now consumes the shared hooks.
- [x] (2026-07-27 11:04Z) Replaced `MatrixView` with `RequirementsView`, including compact accessible verdicts and vertical tool/profile evidence.
- [x] (2026-07-27 11:06Z) Removed table/virtualizer code, 288 lines of matrix CSS, and both TanStack dependencies; updated root/dashboard documentation.
- [x] (2026-07-27 11:08Z) Added focused coverage for deep-link reveal, scroll reset through shared behavior, related-case mapping, six profiles, links, and absence of the table.
- [ ] Run focused reviews, full gates, and desktop/mobile/many-tool browser validation; remove this completed plan.

## Surprises & Discoveries

- Observation: The current table is the only consumer of both `@tanstack/react-table` and `@tanstack/react-virtual`.
  Evidence: repository search finds imports only in `dashboard/src/MatrixView.tsx` and its test. Complete table removal permits removing both runtime dependencies.

- Observation: Current Requirement status and “Supporting cases” mapping includes only `primary_requirement`.
  Evidence: `MatrixView` builds `casesByRequirement` from `testCase.primary_requirement` only, while the corpus contract also exposes `related_requirements`. The new view must map both so it does not omit valid evidence.

- Observation: Cases already owned the required viewport-aware split-pane behavior, including actual-top measurement, independent scrolling, selection reveal, and detail reset.
  Evidence: `EvidenceView` implemented these effects directly. They now live in `useSplitWorkspace.ts` and both views consume the same lifecycle.

- Observation: Six active profile identities fit the new composition without increasing page width.
  Evidence: a temporary six-tool dataset at 1840×1004 rendered six list verdicts and six vertical detail rows, zero Requirements tables, body width1825 for viewport1840, and no runtime errors. The workspace remained exactly 586/1172 px.

- Observation: Requirement-scoped Case filtering cannot reuse the primary-only Case result unchanged.
  Evidence: focused review showed a Case whose primary Requirement is Chapter13 and related Requirement is Chapter5 disappeared under `chapter=5`. `filterCorpus()` now applies one shared Case predicate to primary context for Cases and primary+related context for Requirements, returning separate collections.

- Observation: A ref-backed layout effect does not initialize if an empty view later mounts its workspace.
  Evidence: focused review found the original shared hook ran once with `ref.current=null`. It now uses a callback ref and state-backed node dependency; a test renders an empty Requirement result, rerenders one item, and observes `--split-workspace-height` being measured.

- Observation: Cross-view drilldown cannot preserve filters whose meaning depends on the source entity context.
  Evidence: control review found that clicking a related Chapter5 supporting Case preserved `chapter=5`, while Cases correctly interprets chapter through the Case's primary Chapter13 Requirement and hid the target. Drilldown now clears corpus predicates while preserving campaign/date/tool/profile and the target ID; an App test proves the Case opens and `chapter` leaves the URL.

## Decision Log

- Decision: Remove the Requirements table entirely and do not add a mode switch.
  Rationale: The user explicitly requested the Cases presentation without the table. Keeping both would retain width-scaling problems and duplicate interaction/testing paths.
  Date/Author: 2026-07-27 / assistant

- Decision: Preserve the URL view value `matrix` while renaming the React component and user-facing terminology to Requirements.
  Rationale: Existing shared links are a public behavior. The token is harmless implementation history; changing it would break otherwise valid links.
  Date/Author: 2026-07-27 / assistant

- Decision: Show one compact verdict indicator per active tool/profile in each list item and one vertically stacked aggregate result per active tool/profile in details.
  Rationale: Compact indicators preserve cross-tool scanning without width-per-tool columns. Full labels and grouped statuses remain legible in the detail pane as tool count grows.
  Date/Author: 2026-07-27 / assistant

- Decision: Treat both primary and related requirement links as supporting evidence.
  Rationale: This matches corpus linkage semantics and prevents a Requirement from appearing unsupported when a Case references it as related.
  Date/Author: 2026-07-27 / assistant

- Decision: Extract only the two behaviors genuinely shared by Cases and Requirements: viewport workspace sizing and selected-list-item reveal/detail reset.
  Rationale: Both consumers need identical lifecycle and scroll-boundary handling. Broader generic list/detail components would add abstraction without a third layout or divergent need.
  Date/Author: 2026-07-27 / assistant

- Decision: Give the Requirement list listbox/option semantics with roving tabindex and Arrow/Home/End navigation.
  Rationale: Without roving focus, keyboard users would tab through every remaining Requirement before reaching details. One selected tab stop preserves fast access to details while arrow keys retain list navigation.
  Date/Author: 2026-07-27 / assistant

- Decision: Split `filterCorpus()` output into primary-context `cases` and all-link-context `requirementCases` while sharing one predicate implementation.
  Rationale: Cases must retain primary Requirement chapter/search semantics, while Requirements must not lose evidence linked through `related_requirements`. Shared result/phase/revision logic avoids drift.
  Date/Author: 2026-07-27 / assistant

## Outcomes & Retrospective

Implementation, browser validation, focused-review fixes, and control-review fixes are complete. Existing `view=matrix` links select and reveal the requested Requirement, but the rendered view contains no table. At 1840×1004 the workspace is 586/1172 px with the last selected item visible and three vertical profile rows. At 1100×620 list and details independently scroll in a 273 px workspace while document y remains zero. A temporary six-tool dataset rendered six compact verdicts and six vertical evidence rows without horizontal overflow. At 390×844 the one-column global-flow fallback reveals the selected item and body width remains375.

Code and UX review found four issues: related-only evidence under requirement-context filters, stale selected IDs, workspace mounting after an empty result, and excessive keyboard tab stops. All are fixed with App-level regressions, callback-ref measurement, automatic first-visible recovery, and roving listbox focus. Both focused follow-ups returned no substantive findings. Fresh control review found one cross-view related-Case filter leak; it was fixed and a narrow fresh recheck returned no substantive findings. Final production build and `just smoke` pass. Only completion audit and plan removal remain.

## Context and Orientation

The repository root is `/home/esynr3z/projects/sv-torture`. The React dashboard is in `dashboard/src/`. `App.tsx` calls the current `MatrixView` when the URL-backed view is `matrix`; the visible tab label is already Requirements. `filters.requirementId` carries the selected identity and `CopyLinkButton` emits canonical links using `view=matrix`, `requirementId`, and the selected campaign.

`MatrixView.tsx` currently uses TanStack React Table to create clause, requirement, and one column per profile. TanStack Virtual renders rows against the global browser window. The right inspector shows the selected Requirement's summary, standard anchors, and primary supporting cases. `aggregateStatus()` in `model.ts` combines multiple Case results into one Requirement/profile status according to existing priority rules. `profileKeys()` returns ordered `tool/profile` identities. `resultsByKey()` maps each exact Case/tool/profile result.

`EvidenceView.tsx` is the model for the new presentation. It renders `.case-list` beside `.evidence-pane`, automatically reveals the selected Case, resets details to the top, measures the actual remaining viewport height, and uses independent contained scrolling on desktop. `styles.css` stacks the layout at widths of 900 px or less and viewport heights of 600 px or less.

A “profile verdict” means the grouped aggregate of all visible supporting Case results for one Requirement and one `tool/profile` identity. It uses the existing `aggregateStatus()` and `statusGroup()` functions and the existing symbols and colors. A “supporting Case” means a Case whose `primary_requirement` equals the Requirement ID or whose `related_requirements` contains that ID.

## Open Questions

None. The user selected complete table removal and a Cases-style layout.

## Plan of Work

Create `dashboard/src/useSplitWorkspace.ts` with two hooks. `useViewportWorkspaceHeight()` returns a ref for the workspace element and owns the existing actual-top measurement from `EvidenceView`: requestAnimationFrame coalescing, initial measurement, window resize/scroll listeners, ResizeObserver coverage of campaign/corpus/workspace controls, CSS property update, and complete cleanup. `useRevealSplitSelection()` accepts selected ID/index, a map of list-button refs, and a detail ref; it resets details to top and reveals the selected button with nearest alignment whenever identity or list position changes. Refactor `EvidenceView` to use both hooks without changing its rendered behavior.

Replace `dashboard/src/MatrixView.tsx` and `MatrixView.test.tsx` with `RequirementsView.tsx` and `RequirementsView.test.tsx`. Update `App.tsx` to import/render `RequirementsView`, but leave `View`, tab IDs, callbacks, and query serialization using `matrix`.

`RequirementsView` receives the same props as the old component. Build a de-duplicated map from every primary and related Requirement ID to its supporting Cases. Filter `profileKeys(campaign)` with the existing Tool/Profile filters. Build exact result lookup with `resultsByKey(campaign)`. Select the requested Requirement when present, otherwise the first Requirement when no identity was requested, matching Cases behavior. Render a `.requirements-workspace` containing a `.requirement-list` navigation region and `.requirement-pane` article.

Each Requirement list button shows clause, summary, ID, and a wrapping row of compact verdict indicators. Each indicator has an accessible label and title containing the profile and grouped status. Selecting a button updates the existing URL-backed Requirement ID. The selected button uses `aria-current` and the same selected surface treatment as Cases.

The detail pane shows clause, summary, ID, Copy link, anchors, supporting Cases, and “Tool evidence.” Tool evidence is a vertical list ordered by campaign tool/profile order. Every row shows the full `tool/profile` identity and grouped aggregate `StatusBadge`; its reason text summarizes exact contributing result reasons. If there are no active profiles, state that no tool evidence is available. Supporting Case buttons continue to navigate to Cases through `onInspectCase`.

In `styles.css`, delete all `.matrix__*` and `.matrix-inspector*` table/inspector rules. Keep generic anchor and supporting-case styles that the new details reuse. Apply the same one-third/two-thirds dimensions and independent desktop overflow behavior to `.requirements-workspace` and `.evidence-workspace`, and apply the same stacked border fallback at max-width 900 px and max-height 600 px. Add only local typography and status-row styles needed for Requirement list/detail content. Ensure verdict rows wrap for six or more profiles.

Remove `@tanstack/react-table` and `@tanstack/react-virtual` from `dashboard/package.json` and `dashboard/package-lock.json` using npm so the lockfile remains canonical. Update `dashboard/README.md` and root `README.md` to describe a Requirements list/detail evidence browser rather than a matrix, while explaining that investigation state remains URL-backed.

### Concrete Steps

Work from `/home/esynr3z/projects/sv-torture`.

Implement shared hooks and the new view, then run:

    npm --prefix dashboard uninstall @tanstack/react-table @tanstack/react-virtual
    npm --prefix dashboard run typecheck
    npm --prefix dashboard test

Expect all dashboard tests to pass. New tests must prove initial and changed Requirement selection reveal, detail scroll reset, primary and related Case inclusion, six profile indicators/evidence rows without table markup, and canonical copied links continuing to use `view=matrix`.

Build and export current data:

    npm --prefix dashboard run build
    uv run svtorture dashboard export \
      .svtorture/campaigns/20260726T201718Z-33850b3740767141/campaign.json \
      --visibility local \
      --output dashboard/dist/data/dataset.json

In Chrome at 1840×1004, open a direct Requirement link near the end of the list. Confirm the selected item is visible, details are at top, list/detail widths are one-third/two-thirds, both scroll independently, document scroll does not move at their boundaries, and there is no Requirements table or horizontal status scrollbar. Validate at 390×844 and 1100×600 that the layout stacks and uses global flow.

For many-tool proof, create only a temporary ignored dashboard dataset or a frontend fixture that duplicates tool definitions/results under unique IDs until at least six profile identities exist. Confirm the list indicators wrap, details render six vertical evidence rows, and body width does not exceed the viewport. Restore the generated dataset with the export command above.

Finally run:

    just smoke
    git diff --check

Run focused code and responsive-UX reviews in parallel, fix every substantive finding, run clean follow-ups and a fresh control review, rerun affected gates, record evidence in this plan, then remove this completed plan.

### Validation and Acceptance

The feature is accepted only when all of the following are observable:

1. Requirements renders no table, matrix grid, virtualized rows, or horizontal profile columns.
2. Desktop Requirements uses approximately one-third list and two-thirds details with independent contained vertical scrolling.
3. A direct existing `view=matrix&requirementId=...&campaign=...` link reveals the selected Requirement and correct campaign immediately.
4. The list shows compact accessible verdicts for every active profile; with six profiles they wrap without page-level horizontal overflow.
5. Details show anchors, all primary/related supporting Cases, and vertically stacked aggregate tool/profile evidence.
6. Selecting another Requirement resets details to top and reveals that item without moving the other column.
7. Cases retains the behavior delivered before this change.
8. Widths at or below 900 px and heights at or below 600 px stack both views in global document flow.
9. TanStack table and virtual dependencies and all dead matrix CSS/code are absent.
10. Typecheck, all frontend tests, production build, `just smoke`, `git diff --check`, focused reviews, and control review pass.

### Idempotence and Recovery

Source edits and npm uninstall are repeatable. `npm uninstall` should be run from the repository root with `--prefix dashboard`; rerunning it after removal is harmless. Generated `dashboard/dist/` data and `.svtorture/` campaigns are ignored. Temporary many-tool data must not be committed; restore it with the normal export command. If the new view fails midway, the committed pre-change implementation is recoverable through Git, but do not retain both old and new views in the final tree.

### Artifacts and Notes

The current visual baseline for Cases-style composition is `/tmp/svtorture-cases-independent-wide.png`. The current Requirements table baseline is `/tmp/svtorture-requirement-revealed.png`; it visibly dedicates width to one column per profile and is the layout being removed.

Final evidence should capture list/detail widths, selected item and pane rectangles, list/detail/document scroll positions before and after wheel input, active profile indicator/evidence counts, table element count zero, body versus viewport width, and runtime/network error arrays.

### Interfaces and Dependencies

Do not add dependencies. Remove `@tanstack/react-table` and `@tanstack/react-virtual`.

`RequirementsView` keeps the old `MatrixView` prop contract:

    requirements: Requirement[]
    cases: CaseDefinition[]
    campaign?: Campaign
    toolFilter: string
    profileFilter: string
    selectedRequirementId: string
    onSelectRequirement(requirementId: string): void
    onInspectCase(caseId: string): void

`useViewportWorkspaceHeight<T extends HTMLElement>()` returns a React ref assigned to the split workspace.

`useRevealSplitSelection<T extends HTMLElement>()` receives selected identity/index, list item ref map, and detail element ref and owns detail reset plus nearest reveal.

No backend or public dataset interface changes.

Revision note (2026-07-27 10:45Z): Created the self-contained plan after confirmation that the Requirements matrix should be removed completely in favor of the Cases-style layout.

Revision note (2026-07-27 11:08Z): Recorded shared-hook extraction, complete table/dependency removal, focused tests, and wide/short/mobile/six-tool browser evidence.

Revision note (2026-07-27 11:20Z): Recorded focused-review findings and clean follow-ups, requirement-context Case filtering, stale-selection recovery, callback-ref sizing, and roving keyboard navigation.

Revision note (2026-07-27 11:29Z): Recorded control-review drilldown finding/fix, clean recheck, 61 frontend tests, production build, and final smoke evidence.
