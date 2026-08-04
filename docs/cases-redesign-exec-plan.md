# Redesign the Cases evidence browser

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the repository's `exec-plan` skill.

## Purpose / Big Picture

The Cases tab must provide the same scalable browsing model and visual language as the Requirements tab. After this work, a user can filter cases with an obvious expandable multi-tag cloud, browse cases through the complete named IEEE Std 1800-2023 hierarchy, select one or more branches, click a section title to jump to its first visible case, and scan every matching case as a compact card. Case cards will share the Requirements card structure: a clause/title/ID header with a copy link, visible revision applicability and clickable tags, followed by collapsed relationship, source/oracle, and tool-evidence disclosures.

The Cases corpus summary will explicitly read `Requirements vs cases:` before Coverage and Density, and its chapter breakdown will use the same gray, red, yellow, and green coverage bands as Requirements. The result can be seen by opening `http://localhost:4180/?view=evidence`, expanding Tags, selecting multiple tags, selecting hierarchy branches, and scrolling through cards while the filter panel, hierarchy, and card-list heading remain visible.

## Non-Goals

This work does not change case metadata, case execution, conformance judgments, corpus metric formulas, the complete standard hierarchy data contract, campaign schemas, the Requirements behavior, or the meaning of existing advanced Cases filters other than replacing the hidden single-tag selector with the new visible multi-tag cloud. It does not add dependencies or modify the licensed IEEE source material.

## Progress

- [x] (2026-08-04 09:05Z) Inspected the current selected-case list/detail path, Requirements tree/card path, filters, URL state, corpus summary, styles, and tests; resolved the intended symmetric Cases behavior in this plan.
- [x] (2026-08-04 09:17Z) Milestone 1: extracted the complete hierarchy presentation and tone logic into `StandardTree`, migrated Requirements without behavior changes, added canonical URL-backed Cases tags with AND semantics and cross-corpus isolation, replaced the legacy Cases Tag select with the emphasized cloud, and passed 60 focused tests plus type checking.
- [x] (2026-08-04 09:32Z) Milestone 2: replaced the selected-case split inspector with the complete case hierarchy and all matching compact cards; preserved requirements, oracle/source viewing, statuses, observations, reproduction, campaign links, and direct links behind lazy disclosures; detailed evidence now fetches only when opened.
- [x] (2026-08-04 09:32Z) Milestone 3: aligned Cases with Requirements card, tree, global-scroll, sticky, responsive, tag, and coverage presentation; removed the obsolete split-workspace hook and styles; passed 73 focused tests, type checking, production build, refreshed campaign export, and desktop/mobile visual checks.
- [x] (2026-08-04 10:09Z) Milestone 4: passed final `just smoke` with 121 focused Python and 105 frontend tests, type checking, production build and refreshed export; passed 188 non-Docker and 11 Docker tests in `just ci` before its network-only real-tool pull failure; completed correctness, accessibility, scaling, impacted-lane, and independent control reviews with every substantive finding fixed and no final findings.
- [x] (2026-08-04 10:20Z) Follow-up: extracted one shared `ToolEvidenceRow` and migrated Requirements from its bespoke profile buttons to the same expandable profile/status/reason rows used by Cases, retaining aggregated requirement semantics and the supporting-case navigation action.

## Surprises & Discoveries

- Observation: Cases currently uses a selected-item application model, while Requirements renders all matching cards.
  Evidence: `dashboard/src/EvidenceView.tsx` renders every case as a button in `.case-list` but only one `.evidence-pane` article, selected by `filters.caseId`.

- Observation: The complete named standard hierarchy is already published to the frontend and needs no data-contract change.
  Evidence: `Dataset.standard_sections` is consumed by `RequirementsView`; each case can be placed in the hierarchy through its primary requirement's `clause`.

- Observation: Cases already has a single tag selector inside Advanced filters, so adding a second tag control without removing or ignoring the first would create conflicting hidden filter state.
  Evidence: `dashboard/src/Filters.tsx` renders `<select value={filters.tag}>` only in Cases Advanced filters, and `filterCorpus()` applies it to requirement and case tags.

- Observation: Detailed evidence can be fetched lazily per case, but the former selected-pane effect fetched immediately whenever selection changed.
  Evidence: The rewritten `CaseCard` keeps a per-card request guard and invokes `loadCaseEvidence(testCase.id)` only from the Tool evidence disclosure's opening callback; `EvidenceView.test.tsx` proves no request occurs before opening.

- Observation: Once Cases adopted the Requirements workspace, `useSplitWorkspace.ts` and all `.case-list`, `.evidence-pane`, and `.evidence-workspace` styles had no consumers.
  Evidence: Repository search after the rewrite returned no TypeScript/TSX references, so the hook and obsolete selectors were deleted rather than retained as dead compatibility code.

- Observation: Lazy per-card requests need both retry semantics and campaign generations; merely clearing state on campaign change can either admit stale results or leave an open disclosure without a new request.
  Evidence: Review-driven tests now prove a transient rejection retries after close/reopen and an open disclosure automatically requests the new campaign while ignoring the older promise.

- Observation: Full `just ci` reached the final real-tool smoke after all deterministic, frontend, build, and Docker-fake gates passed, but Docker Hub token retrieval timed out.
  Evidence: `docker pull --platform=linux/amd64 ubuntu:24.04` failed with `unable to decode token response: context cancellation while reading body`; this is an external network failure after 188 non-Docker tests, 105 frontend tests, production build, and 11 Docker tests passed.

- Observation: Moving observations inside semantic case-card articles made the old observation `<article>` elements nested articles without independent headings.
  Evidence: The delayed design-path research identified the semantic nesting; observations now use neutral `<div className="observation">` containers while preserving all content and styles.

## Decision Log

- Decision: Use each case's primary requirement clause as its single hierarchy location. Related requirements remain visible relationships but do not place one case in multiple branches.
  Rationale: A case has exactly one scoring requirement, so this gives stable counts and avoids duplicate cards or misleading coverage placement.
  Date/Author: 2026-08-04 / pi

- Decision: Reuse the existing URL-backed `sections` selection for both Requirements and Cases rather than introduce a second hierarchy parameter.
  Rationale: The same standard tree and selection grammar apply in either tab, and one active `view` parameter makes the URL unambiguous while preserving branch context when switching tabs.
  Date/Author: 2026-08-04 / pi

- Decision: Add a dedicated canonical `caseTags` URL field, combine selected values with AND semantics, and ignore `requirementTags` on Cases and `caseTags` on Requirements.
  Rationale: The user asked for symmetric multi-tag behavior, while separate fields prevent stale tag selections from one corpus hiding the other corpus. AND semantics match the accepted Requirements interaction.
  Date/Author: 2026-08-04 / pi

- Decision: Remove the single Tag select from Cases Advanced filters but retain Search, Revision, Standard part, Clause, Phase, Expectation, Case presence, Requirement, Exact result, and Reason.
  Rationale: The visible tag cloud supersedes only the old tag control; all other existing Cases capabilities remain required.
  Date/Author: 2026-08-04 / pi

- Decision: Extract a shared standard-tree presentation and shared tree-tone helpers rather than duplicate the Requirements implementation. Keep case-specific and requirement-specific card bodies separate but style both through the same card classes and structure.
  Rationale: There are now two real consumers with identical tree behavior. Cards have different domain content, so forcing one generalized card component would add conditional complexity without improving consistency.
  Date/Author: 2026-08-04 / pi

- Decision: Case cards visibly show clause, title, stable ID, copy link, description, all three revision-applicability values, and clickable tags. Requirements relationships, oracle and sources, and tool evidence start collapsed.
  Rationale: This mirrors the scan-first Requirements structure while retaining every capability of the current selected inspector on demand.
  Date/Author: 2026-08-04 / pi

- Decision: Fetch detailed case evidence only when Tool evidence is first opened for that card. Compact status badges continue to come from the campaign summary already in memory.
  Rationale: Thousands of visible cards must not trigger thousands of network requests, but opening evidence must preserve the existing observation and reproduction UI.
  Date/Author: 2026-08-04 / pi

- Decision: Requirements and Cases render each Tool evidence profile through the same `ToolEvidenceRow` component. A Case row expands to its detailed observation; a Requirement row expands to its aggregate case count and existing `View supporting cases` navigation.
  Rationale: Profile, status, and reason presentation must be exactly consistent, while the body must remain honest about the different evidence granularity.
  Date/Author: 2026-08-04 / pi

- Decision: With one tool explicitly selected, the Cases tree uses the same red/yellow/green/gray worst-status rule and non-color symbols as Requirements, derived directly from case results in selected profiles.
  Rationale: Symmetric navigation should communicate result state identically, including pass plus gray remaining green.
  Date/Author: 2026-08-04 / pi

## Outcomes & Retrospective

All milestones are complete. Requirements and Cases consume the same corpus-neutral `StandardTree`; Cases has an independently URL-backed AND tag cloud and retains every non-tag Advanced filter. The old selected-list inspector and split-workspace code are gone. All matching cases render as aligned compact cards with lazy Requirements, Oracle and sources, and Tool evidence sections. Detailed evidence loads only on opening, retries transient failures, refetches for an open disclosure after campaign changes, and rejects stale campaign responses. Tree navigation and cross-tab requirement navigation move focus to the destination without later focus stealing.

The Cases summary reads `Requirements vs cases:` and uses shared threshold colors. Tool evidence profile rows now use one shared component in both card types; Requirements retains aggregate case evidence while matching Cases interaction and presentation exactly. Final `just smoke` passed 121 focused Python tests, all annotator checks, type checking, 105 frontend tests, and production build. `just ci` additionally passed 188 non-Docker tests and 11 Docker tests before the final real Icarus smoke was blocked solely by a Docker Hub network timeout. Desktop 1450×900 and mobile 430×932 screenshots passed, the local campaign export was refreshed, all multi-lane findings were fixed and retested, and an independent final control review reported `No substantive findings.` No required work remains.

## Context and Orientation

SVTORTURE publishes immutable campaign evidence to a static React dashboard. `dashboard/src/App.tsx` owns the active tab and the `Filters` object, writes that state to the URL through `filtersToSearch()`, derives a filtered corpus through `filterCorpus()`, and renders `EvidenceView` for `view=evidence`. `dashboard/src/model.ts` defines filter state and corpus matching. `dashboard/src/Filters.tsx` renders quick and advanced controls. `dashboard/src/CorpusCoverage.tsx` renders Coverage and Density summaries. `dashboard/src/styles.css` owns sticky offsets, tree layout, cards, and responsive behavior.

A standard section is a named clause such as `13.5 Subroutine arguments`. `Dataset.standard_sections` contains the complete ordered IEEE Std 1800-2023 hierarchy, including sections with no requirements or cases. A case does not store a clause directly. Its `primary_requirement` points to a `Requirement`; that requirement's `clause` determines the case's tree location. A tree branch selection includes the exact clause and all descendants. Multiple unrelated branches combine with OR. The compact URL grammar already supports full-subtree tokens such as `13` and exact internal-node tokens such as `=13` for tri-state unchecking.

`dashboard/src/RequirementsView.tsx` is the proven target interaction. It builds a complete expandable tree, derives total and filtered counts, displays status tones only for one selected tool, and renders all matching compact cards in global document flow. `dashboard/src/requirementHierarchy.ts` implements hierarchy building and URL selection semantics. `dashboard/src/EvidenceView.tsx` currently renders a scrollable `.case-list` and one selected `.evidence-pane`; it owns trusted source-link handling, embedded source viewing, detailed observations, and reproduction commands. Those capabilities must move into lazy card disclosures, not be removed.

The sticky offset `--content-sticky-top` is the combined site-header and workspace-filter height. Requirements uses global card scrolling on wide screens, a sticky tree below that offset, and a sticky card-list header at the same offset. Cases must use the same model. At widths of 900 pixels or less, both tree and cards remain in normal document flow, and anchor scroll margins account for the sticky site and filter headers.

## Open Questions

There are no unresolved product questions. If implementation shows that a current case-only detail cannot fit an existing planned disclosure, preserve it in the smallest additional collapsed disclosure and record the reason in `Surprises & Discoveries`; do not return to a one-selected-case inspector.

## Plan of Work

Milestone 1 establishes shared navigation and filters. Extract the reusable tree row, tree container, count derivation, status tone derivation, and clause-navigation presentation from `dashboard/src/RequirementsView.tsx` into a small shared frontend module such as `dashboard/src/StandardTree.tsx`. The shared component receives the complete section list, total and visible item locations, selected URL tokens, optional per-item statuses, item labels, and callbacks for selection and navigation. It preserves separate chevron, checkbox, and title actions; native nested-list semantics; tri-state selection; all/total counts; empty-branch dimming; one-tool tones and symbols; and existing Requirements behavior. Keep selection grammar in `requirementHierarchy.ts` unless naming becomes actively misleading; renaming working pure helpers is not required.

Add `caseTags: string` to `Filters` and `EMPTY_FILTERS` in `dashboard/src/model.ts`. Normalize it during direct URL parsing exactly like `requirementTags`. Extend `filterCorpus()` so all selected case tags must appear on a case. Add explicit filter projections: Requirements ignores `caseTags`; Cases ignores `requirementTags` and the superseded legacy `tag`; unrelated tabs ignore both corpus-specific tag fields. Keep Cases advanced fields active. In `dashboard/src/Filters.tsx`, make the existing emphasized tag disclosure work for both Requirements and Cases, using the corresponding corpus tags, counts, URL field, and accessible group label. Remove only the old single Tag select from Advanced filters.

Wire Cases section and tag state in `dashboard/src/App.tsx`. Pass `Dataset.standard_sections`, all unfiltered cases, selected section tokens, selected case tags, and stable callbacks into `EvidenceView`. Filtering by tree selection may happen inside the view, as it does for Requirements, so quick/advanced-filter counts remain distinguishable from branch counts. Add tests proving direct URL canonicalization, tag AND semantics, cloud toggling, cross-tab tag isolation, old hidden `tag` isolation, hierarchy URL round trips, and no Requirements regression. Commit this coherent filter/tree foundation before replacing the inspector.

Milestone 2 rewrites `dashboard/src/EvidenceView.tsx` as the all-card Cases browser. Build a map from requirement IDs to requirements and derive one clause for every case from its primary requirement. Feed those locations to the shared tree. The tree keeps all named sections, displays visible/total case counts, and filters cards by decoded section selection. A title click and a direct `caseId` link expand tree ancestors as needed and scroll to the card without changing checkbox selection. Unknown requirement IDs remain explicit as an unknown-location fallback rather than crashing.

Define a memoized case card local to `EvidenceView.tsx`. Its visible structure uses the same classes and ordering as `RequirementCard`: header, revision-applicability table, tags, then lazy details. The header shows standard location, case title, stable ID, and `CopyLinkButton`. Keep description visible below the header. The revision table has rows for 1800-2012, 1800-2017, and 1800-2023 and uses the same human-readable status styling as Requirements. Tag buttons toggle `caseTags` and expose `aria-pressed`.

The Requirements disclosure contains the primary and related requirement buttons and retains `onInspectRequirement`. The Oracle and sources disclosure contains phase, expectation, evidence requirement, oracle kind/marker/anchor, source links, and the existing trusted embedded/external/unavailable behavior. An embedded source viewer stays inside its card and returns focus to the source trigger when closed. The Tool evidence disclosure lists each visible tool/profile with compact status, reason, and a nested detail disclosure. Opening Tool evidence invokes `loadCaseEvidence(caseId)` once for that card; loading, failure, absent result, known issue, observations, streams, and reproduction command retain the current explicit states. Use lazy render callbacks so closed details do not construct expensive evidence bodies.

Delete the obsolete selected-list refs, split-pane reveal hook, eager selected-case fetch effect, and inspector markup only after equivalent tests pass. Memoize requirement/result/profile maps and cards so expanding the tree or one card does not rerender or fetch every card. Preserve `content-visibility` for offscreen cards and avoid a new virtualization dependency.

Milestone 3 aligns presentation. In `dashboard/src/CorpusCoverage.tsx`, show `Requirements vs cases:` for Cases and apply `coverageTone()` classes to both metric kinds. Keep the existing Cases formula: unique requirements linked from cases divided by all catalog requirements, and case-requirement link density. Update tests at exact 0, below 30, 30, below 80, and 80 percent boundaries.

In `dashboard/src/styles.css`, make Requirements and Cases share the same two-column tree/card grid, sticky offsets, card borders, typography, applicability table, tag buttons, detail summaries, empty states, scroll margins, and narrow-screen flow. Use shared class names where possible rather than parallel values. Cases no longer uses `.case-list`, `.evidence-pane`, or fixed independent evidence scrollers. Ensure the obvious full-width Tags summary and rotating chevron remain identical in both tabs. Add no color-only meaning and preserve reduced-motion behavior.

Milestone 4 validates and audits. Run focused tests after each slice, then `just smoke`. Build the production dashboard, export the existing local campaign into ignored `dashboard/dist/data`, and inspect desktop and narrow screenshots for both tabs. Verify global scrolling with expanded filters and direct-link/tree navigation. Request independent correctness, accessibility, scaling, and regression review; fix every substantive finding and rerun impacted checks. Update this plan after each milestone and commit coherent increments with Conventional Commits.

### Concrete Steps

All commands run from `/home/esynr3z/orca/workspaces/sv-torture/fix-redesign_req_cases_tabs-2`.

Start with the shared tree and filter contract:

    npm --prefix dashboard test -- model.test.ts Filters.test.tsx requirementHierarchy.test.ts RequirementsView.test.tsx App.test.tsx
    npm --prefix dashboard run typecheck
    git diff --check

Expect all focused tests to pass and Requirements tree behavior to remain unchanged. Commit the shared tree/filter slice before rewriting EvidenceView.

Then implement and validate Cases cards and coverage:

    npm --prefix dashboard test -- EvidenceView.test.tsx CorpusCoverage.test.tsx App.test.tsx
    npm --prefix dashboard run typecheck
    npm --prefix dashboard run build

Expect direct links, source viewing, requirement navigation, lazy evidence, tag filtering, hierarchy filtering, card counts, and coverage labels/tones to pass. The production build may retain the repository's existing chunk-size warning but must exit successfully.

Finally run deterministic repository checks and refresh local viewing data:

    just smoke
    npm --prefix dashboard run build
    uv run svtorture dashboard export .svtorture/campaigns/20260803T154033Z-de7ee27f6b8fdfb8/campaign.json --output dashboard/dist/data
    git diff --check
    git status --short

`just smoke` must complete with Python formatting, lint, typing, metadata validation, 121 focused non-Docker Python tests unless the maintained suite count changes, annotator tests, frontend type checking, and all frontend tests. The data export must remain ignored. If Docker and network are available at final handoff, run `just ci`; otherwise record why it was not repeated.

### Validation and Acceptance

At `http://localhost:4180/?view=evidence`, the corpus summary reads `Requirements vs cases:` followed by Coverage and Density. Expanding Breakdown shows chapter and annex rows with gray for undefined or zero, red below 30 percent, yellow from 30 through below 80 percent, and green from 80 percent upward; numbers and operands remain visible.

The Cases controls retain Tools, Profile, Result, Compare, and Advanced filters. Below quick filters, Tags is a full-width bordered disclosure with a right chevron. Opening it shows every case tag and case count. Clicking `copy-out` then `output` leaves only cases carrying both tags, marks both buttons pressed, updates canonical `caseTags=copy-out%2Coutput` URL state, and does not set the legacy `tag` field. Switching to Requirements does not apply those case tags.

The Cases body has the complete IEEE Std 1800-2023 tree on the left and all matching case cards on the right. Sections without cases remain visible with zero counts. Parent checkboxes become indeterminate for partial child selections; unrelated selected branches form an OR union; All restores the full quick/advanced-filter result. Clicking a title scrolls to the first visible case in that subtree. With one tool selected, rows expose distinct symbols and accessible labels for red failure/infra, yellow unclear, green pass, and gray not evaluated/applicable states.

Each case card visibly aligns with a requirement card: standard location, title, ID, copy link, description, three revision rows, tag buttons, and collapsed details. Requirements navigation, source viewing, oracle facts, profile judgments, observation streams, known issues, and reproduction commands remain available after opening the corresponding disclosure. Before any Tool evidence disclosure opens, no detailed case resource is fetched. A direct `caseId` URL scrolls to the matching card, and Copy link retains the selected campaign.

On a wide viewport, global page scrolling keeps the quick-filter panel sticky and keeps the tree and Cases heading below it. The tree remains independently scrollable within viewport height while cards follow document flow. On a viewport at or below 900 pixels wide, tree and cards stack in normal flow, no sticky header obscures a deep-linked card, and all controls remain keyboard accessible with visible focus.

### Idempotence and Recovery

Frontend tests, type checking, builds, screenshots, and local dashboard export are safe to rerun. `npm --prefix dashboard run build` recreates `dashboard/dist` without campaign data, so always rerun the explicit export afterward before visual review. `dashboard/dist/data` and `.svtorture` remain ignored and must not be staged.

Refactor in two commits so the shared tree/filter foundation can be inspected independently from the inspector replacement. If the card rewrite fails mid-way, restore only unstaged `EvidenceView` edits or continue from the passing shared-tree commit; do not weaken tests or restore a duplicate second hierarchy. Before every commit, inspect `git status --short`, `git diff --cached --check`, and staged paths for generated data or unrelated files.

### Artifacts and Notes

A canonical Cases URL after two tags and two branches should resemble:

    ?view=evidence&caseTags=copy-out%2Coutput&sections=13.5%2C14

The case hierarchy derives locations without changing the public data contract:

    case.primary_requirement -> requirement.id -> requirement.clause

The card disclosure order is:

    visible header and description
    revision applicability
    tags
    Requirements
    Oracle and sources
    Tool evidence

### Interfaces and Dependencies

Do not add dependencies. Use React hooks and memoization, native details/buttons/checkboxes, the existing `CopyLinkButton`, `StatusBadge`, `requirementHierarchy.ts` selection helpers, campaign summary results, and `loadCaseEvidence` callback.

At the end of Milestone 1, `Filters` in `dashboard/src/model.ts` contains `caseTags: string`; `filtersFromSearch()` canonicalizes both corpus tag fields; `filterCorpus()` applies `caseTags` with AND semantics only to case tags. `Filters.tsx` renders one symmetric tag-cloud implementation for Requirements and Cases. The shared tree component accepts corpus-neutral labels (`itemLabel`, `itemsLabel`, and accessible names) and callbacks while preserving the existing Requirements interaction and tests.

At the end of Milestone 2, `EvidenceView` accepts `allCases`, `standardSections`, `selectedSections`, `onSelectedSectionsChange`, `selectedTags`, and `onToggleTag` in addition to its existing campaign/navigation/evidence inputs. It renders every section-filtered card and uses `selectedCaseId` only as a deep-link/navigation target, not as permission to hide other cards. Detailed evidence loads only from a user-opened card disclosure.

Revision note (2026-08-04 09:05Z): Initial Cases redesign plan created after inspecting the completed Requirements browser and current Cases inspector. It resolves hierarchy placement, shared navigation, tag isolation, retained advanced filters, compact card content, lazy evidence loading, coverage wording, sticky behavior, validation, and recovery before implementation begins.

Revision note (2026-08-04 09:17Z): Updated after Milestone 1 to record the shared tree extraction, Requirements migration, canonical Cases tag field, AND filtering, removal of the superseded single-tag control, cross-corpus isolation, and focused validation evidence.

Revision note (2026-08-04 09:32Z): Updated after Milestones 2 and 3 to record the all-card Cases browser, primary-clause hierarchy placement, lazy per-card evidence, retained source and relationship behavior, shared coverage wording/tones, obsolete split-layout deletion, focused test/build evidence, and desktop/mobile visual checks.

Revision note (2026-08-04 10:09Z): Completed Milestone 4 after correctness, accessibility, scaling, impacted-lane, and independent control review. Recorded fixes for corpus memo churn, unstable callbacks, campaign-safe request retry/refetch, accessible loading state, focus movement/consumption, tree semantics, final smoke/build/export evidence, and the network-only `just ci` real-tool pull failure.

Revision note (2026-08-04 10:15Z): Incorporated the delayed initial design-path report after completion. Its implementation recommendations were already covered; removed the remaining nested-article semantics in observation rows and recorded the evidence without changing behavior.

Revision note (2026-08-04 10:20Z): Added the requested exact Tool evidence row symmetry. Recorded the shared component decision, preserved different Requirement aggregate versus Case observation bodies, and removed the obsolete Requirements-only profile styling.
