# Route tool evidence to explanatory Cases

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current while implementation proceeds.

## Purpose / Big Picture

After this change, clicking a Tool/Profile row in Overview opens Cases instead of Requirements and applies that exact Tool and Profile. Clicking a Tool evidence row inside a Requirement also opens Cases, applies that Tool/Profile, and applies an explicit exact Requirement filter. The resulting Cases are the cases linked to the Requirement through either `primary_requirement` or `related_requirements`, so the drilldown explains the grouped Requirement verdict instead of relying on ambiguous free-text search.

The new Requirement filter is visible inside Advanced filters, URL-backed as `requirement=<ID>`, and automatically reveals Advanced filters when a drilldown sets it. Campaign and date context remain selected. Direct entity selection uses the existing `caseId` and `requirementId` URL parameters and remains distinct from the new corpus filter.

## Progress

- [x] (2026-07-27 11:38Z) Read dashboard guidance and traced Overview, Requirement evidence aggregation, URL filters, and Case filtering.
- [x] (2026-07-27 12:07Z) Added URL-backed exact linked-Requirement filtering to the model and Advanced filters, including automatic disclosure and related-only Case coverage.
- [x] (2026-07-27 12:07Z) Routed Overview rows and native-button Requirement Tool evidence rows to Cases with canonical Campaign/date/Tool/Profile/Requirement state.
- [x] (2026-07-27 12:07Z) Added model, filter, component, and App regressions for URL round-trip, related links, disclosure, callback payload, and both navigation paths; TypeScript and 64 frontend tests pass.
- [ ] Run focused review, repository gates, browser validation, remove this completed plan, and commit the final state.

## Surprises & Discoveries

- Observation: A Requirement/Profile verdict is not a direct Result row. `RequirementsView` gathers every currently visible supporting Case linked through primary or related Requirement IDs, retrieves each exact `case/tool/profile` Result, and calls `aggregateStatus()` using worst-first status priority.
  Evidence: `dashboard/src/RequirementsView.tsx` builds `casesByRequirement` from both link types and maps supporting Cases through `resultsByKey()`; `dashboard/src/model.ts` orders infrastructure error, failure, unclear, unsupported/not-applicable states, pass, then not-run.

- Observation: The existing `requirementId` filter is an entity selection, not a corpus constraint.
  Evidence: it controls the selected Requirement and canonical Copy link. Reusing it in Cases would conflate navigation state and filtering, so this plan introduces `requirement` as a separate exact linked-Requirement filter.

## Decision Log

- Decision: Add `Filters.requirement` and serialize it as the ordinary URL parameter `requirement`.
  Rationale: The name describes the user-visible Advanced filter and remains unambiguous beside `requirementId`, which selects a Requirement detail page.
  Date/Author: 2026-07-27 / assistant

- Decision: Exact Requirement matching includes both `primary_requirement` and `related_requirements`.
  Rationale: Tool evidence aggregates both link types; omitting related links would make the drilldown disagree with the verdict it is intended to explain.
  Date/Author: 2026-07-27 / assistant

- Decision: Drilldown starts from `EMPTY_FILTERS`, preserving Campaign and date bounds, then sets Tool/Profile and, for Requirement evidence, the exact Requirement filter.
  Rationale: Existing chapter, search, result, comparison, or selected-entity filters can hide the intended destination or be reinterpreted in Cases. A canonical explanatory drilldown must be predictable and shareable.
  Date/Author: 2026-07-27 / assistant

- Decision: Render Tool evidence rows as real buttons, not clickable generic containers.
  Rationale: Native buttons provide Enter/Space activation, focus semantics, and an accessible destination label without custom keyboard emulation.
  Date/Author: 2026-07-27 / assistant

## Outcomes & Retrospective

The two drilldown paths and exact Requirement filter are implemented. Unit and integration evidence covers a related-only Case from a Requirement Tool evidence button through the Cases detail and URL-backed opened Advanced filter. Review, production gates, and browser validation remain.

## Context and Orientation

`dashboard/src/App.tsx` owns URL-backed filter state and view changes. Its Overview callback currently sets Tool/Profile and opens the legacy-named `matrix` view, which now renders Requirements. `dashboard/src/HeadlineMetrics.tsx` renders the Overview table and invokes that callback.

`dashboard/src/RequirementsView.tsx` builds each Requirement/Profile aggregate. Its Tool evidence rows are currently noninteractive `<div>` elements. The component needs a callback carrying tool ID, profile ID, and the selected Requirement ID.

`dashboard/src/model.ts` defines `Filters`, `EMPTY_FILTERS`, generic URL parse/serialize helpers, and `filterCorpus()`. `filterCorpus()` deliberately computes primary-context `cases` for Cases and all-link-context `requirementCases` for Requirements. The exact Requirement constraint must be applied before returning Cases and must include both link types. The selected Requirement list should also reduce to that exact Requirement when this Advanced filter is manually used.

`dashboard/src/Filters.tsx` renders corpus-only Advanced filters. It needs a Requirement field populated from `dataset.requirements`, preferably a select so IDs are exact and discoverable. A ref/effect should open the existing `<details>` whenever `filters.requirement` changes from empty to nonempty while still allowing a user to close it afterward.

`dashboard/src/App.test.tsx`, `dashboard/src/model.test.ts`, `dashboard/src/Filters.test.tsx`, and `dashboard/src/RequirementsView.test.tsx` contain the closest regression coverage. `dashboard/src/HeadlineMetrics.test.tsx` checks the row callback and accessible label.

## Plan of Work

First extend `Filters` and `EMPTY_FILTERS` in `dashboard/src/model.ts` with `requirement: string`. The generic URL parser and serializer already iterate the complete filter object, so the new value should round-trip automatically. In `filterCorpus()`, define a small linked-ID predicate using the Case primary and related Requirement IDs. Apply it to both Case collections when the exact filter is present, and require an exact ID match for Requirements. Keep all existing primary-context versus all-link-context behavior for every other filter.

Add a labeled Requirement select to corpus Advanced filters. Its options should use Requirement IDs as values and include concise summaries for recognition. Attach a ref to the Advanced `<details>` and open it in an effect when `filters.requirement` becomes nonempty. Test manual selection, callback state, and automatic disclosure.

Change the Overview accessible label from “View requirements” to “View cases.” In `App.tsx`, replace the current inline callback with a canonical Cases drilldown that resets local filters, preserves Campaign/date bounds, sets Tool/Profile, and opens `evidence`.

Add `onInspectEvidence(toolId, profileId, requirementId)` to `RequirementsView`. Parse each existing profile key and render each Tool evidence row as a button. In `App.tsx`, implement the callback with the same canonical reset plus the exact `requirement` filter. Open Cases. Preserve no stale selected Case or Requirement ID.

Update CSS so the button keeps the current full-width vertical evidence-row appearance, focus visibility, and responsive behavior. Do not add dependencies or a new navigation mode.

Add regressions proving: URL round-trip includes `requirement`; a related-only Case survives the exact Requirement filter; unrelated Cases do not; Overview row opens Cases with Tool/Profile and no stale local filters; Requirement evidence opens Cases with Tool/Profile and exact Requirement; Advanced filters opens and displays the selected ID; and the Tool evidence button has an accurate accessible label and callback payload.

## Concrete Steps

Work from `/home/esynr3z/projects/sv-torture`.

Implement model and UI changes, then run:

    npm --prefix dashboard run typecheck
    npm --prefix dashboard test
    npm --prefix dashboard run build
    just smoke
    git diff --check

Export the current local campaign after the production build and serve `dashboard/dist`. In Chrome, click an Overview Tool row and verify the Cases tab, Tool/Profile chips, and URL. Then click a Requirement Tool evidence row and verify Cases, the exact linked-Requirement select inside opened Advanced filters, no horizontal overflow, and no console/network errors at wide and mobile widths.

Request focused logic and accessibility reviews. Resolve findings, rerun affected tests and final gates, update this plan with evidence, then delete the completed plan as required by repository policy.

## Validation and Acceptance

Acceptance is behavioral. Overview Tool/Profile rows must navigate to Cases and expose `view=evidence&tool=<tool>&profile=<profile>` while retaining selected Campaign/date bounds. Requirement Tool evidence buttons must navigate to Cases and additionally expose `requirement=<exact ID>`. The Cases list must include Cases linked only through `related_requirements` and exclude unrelated Cases.

Advanced filters must visibly open after Requirement evidence drilldown and show the exact selected Requirement. Reloading the URL must reproduce the same view and filter. Enter and Space on a focused Tool evidence row must invoke the same navigation as a pointer click.

All existing deep links and Copy links must continue to work. All frontend tests, production build, `just smoke`, and `git diff --check` must pass. Browser inspection must find no page-level horizontal overflow or runtime errors.

## Idempotence and Recovery

All changes are ordinary source edits and test additions. Re-running tests, builds, exports, and browser checks is safe. Dashboard output remains ignored. If a test dataset mutation leaks between tests, construct a fresh `makeTestDataset()` value inside each test rather than sharing mutable objects.

## Artifacts and Notes

The stable view token remains `evidence` for Cases and `matrix` for Requirements. This feature does not rename those tokens because existing URLs are public investigation state.

Revision note (2026-07-27 11:38Z): Created the plan after tracing verdict aggregation and resolving the distinction between Requirement selection and exact linked-Requirement filtering.

Revision note (2026-07-27 12:07Z): Recorded completed implementation, canonical reset behavior, related-link regression coverage, and 64 passing frontend tests.
