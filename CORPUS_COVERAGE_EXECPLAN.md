# Add compact corpus coverage summaries

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the `exec-plan` skill. It is temporary implementation guidance and must be removed after the work is complete because this repository does not retain completed ExecPlans.

## Purpose / Big Picture

A dashboard reader should be able to see, at a glance, how much of IEEE 1800-2023 has been represented as formal SVTORTURE requirements and how much of that requirement catalog has executable cases. After this change, the Requirements and Cases tabs each show a compact, non-sticky strip with Coverage and Density values. Expanding the strip reveals the same measurements for every standard chapter and annex. Hovering a metric explains its operands and pseudo-formula. Scrolling moves the strip away while the existing filters remain sticky.

Requirements Coverage measures unique committed standard anchors referenced by the requirement catalog against all anchors in `standards/ieee-1800-2023-anchors.json`. Requirements Density measures unique requirement–anchor relationships per unique covered anchor. Cases Coverage measures unique requirements referenced by at least one case against every catalog requirement. Cases Density measures unique case–requirement relationships per unique covered requirement. A “relationship” is one unique pair, so accidental duplicate identifiers cannot inflate a metric.

## Non-Goals

This work does not change conformance scoring, campaign selection, tool results, requirement metadata, case metadata, URL state, or the standard anchor index. It does not add a runtime dependency, a second vertical scrollbar, a retained generated dataset, or a compatibility parser for an older dashboard dataset. It does not add annex requirements to the catalog model; annex rows are still shown and may have anchor coverage, but case coverage for annexes remains empty until the requirement model supports annex-owned requirements.

## Progress

- [x] (2026-07-26 11:24Z) Confirmed the formulas with the user; Requirements Density is requirements per covered anchor.
- [x] (2026-07-26 11:24Z) Mapped the anchor index, dashboard export pipeline, frontend types, sticky layout, and test surfaces.
- [x] (2026-07-26 11:38Z) Added deterministic corpus coverage and density operands to the generated dashboard dataset, including 58 ordered breakdown rows and related-requirement counting.
- [x] (2026-07-26 14:40Z) Added compact Requirements and Cases disclosure strips with hover formulas, accessible descriptions, and complete chapter/annex breakdowns.
- [ ] Add backend, frontend, documentation, responsive, and accessibility validation (completed: focused backend tests, frontend typecheck, 43 frontend tests, production build, desktop/mobile Chrome inspection; remaining: focused review and root smoke gate).
- [ ] Run the repository gates, remove this completed ExecPlan, and leave the working tree ready for handoff.

## Surprises & Discoveries

- Observation: The committed anchor index already provides the exact ordered breakdown needed by the feature.
  Evidence: `standards/ieee-1800-2023-anchors.json` contains 41 `clauses` entries and 17 `annexes` entries, with 16,963 unique anchors in total.

- Observation: A requirement’s supporting anchors can belong to a different standard part than its declared numeric chapter.
  Evidence: `SV-2023-26-PACKAGE-IMPORT` includes an anchor from Chapter 3, and `SV-2023-13-OUTPUT-COPYOUT` includes anchors from Chapters 10 and 6. Requirements breakdown must therefore group each relationship by the anchor’s actual index part, not by `Requirement.chapter`.

- Observation: The current corpus has 12 requirements, 17 unique requirement–anchor relationships, and 16 unique covered anchors. The shared Chapter 6 anchor makes Requirements Density 17/16 rather than 1.
  Evidence: a direct scan of the catalog gives Coverage 16/16,963 and Density 17/16.

- Observation: Cases expose both `primary_requirement` and `related_requirements`, although every current case has an empty related list.
  Evidence: `dashboard/src/types.ts::CaseDefinition` and `src/svtorture/models.py::CaseDefinition` define both fields. The implementation and tests must include both so future related links are counted correctly.

- Observation: The focused Python pre-commit gate still expected `.github/README.md`, which the user intentionally removed because GitHub displayed it instead of the root project README.
  Evidence: the first backend milestone commit attempt failed `test_repository_directories_have_navigation_readmes` in `tests/test_catalog_models.py`. The stale `.github` entry was removed from that navigation-README assertion; all other documented top-level directories remain covered.

## Decision Log

- Decision: Export integer metric operands from Python rather than shipping all 16,963 anchors to the browser or hard-coding totals in React.
  Rationale: `src/svtorture/publish.py` already owns immutable dashboard dataset construction and can read the committed anchor index. Integer operands preserve provenance and allow the frontend to format without rounding drift while avoiding a large redundant payload.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Add a required `corpus_coverage` object to dashboard dataset schema version 2 without a legacy fallback or schema migration.
  Rationale: The dashboard dataset has no separately generated public schema or runtime compatibility parser. Every supported build generates the frontend and dataset together, and `merge_datasets()` starts from the new dataset before appending campaign history. This is a strict additive contract change, not a transition path.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Group Requirements breakdown relationships by the actual chapter or annex containing each anchor. Group Cases breakdown relationships by the owning requirement’s numeric chapter.
  Rationale: Requirements metrics describe standard anchors, while Cases metrics describe catalog requirements. This preserves the meaning of each denominator and handles cross-chapter supporting anchors correctly.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Insert the strip between the non-sticky campaign controls and the existing sticky workspace containing tabs and filters.
  Rationale: The strip then scrolls away naturally without changing sticky offsets, nested scrolling, or filter behavior. It appears only for Requirements and Cases.
  Date/Author: 2026-07-26 / coding assistant

- Decision: Use native `<details>` and `<summary>` for disclosure and native hover titles plus an `aria-describedby` explanation for formulas.
  Rationale: The repository already uses native disclosure controls. This supplies keyboard behavior and hover explanations without JavaScript state or another UI dependency.
  Date/Author: 2026-07-26 / coding assistant

## Outcomes & Retrospective

The dataset and frontend milestones are complete. Publication emits exact integer operands for both summaries and all 58 standard parts. Requirements shows 0.09% and 1.06; Cases shows 100% and 1. The compact and expanded layouts have been inspected in Chrome at 1840×1004 and 390×844 with no runtime, network, or page-overflow errors. Focused review and the root smoke gate remain.

## Context and Orientation

`standards/ieee-1800-2023-anchors.json` is the committed runtime index of the licensed standard extraction. Its root `anchor_count` is 16,963. Its ordered `clauses` and `annexes` arrays each contain an `id`, `title`, `anchor_count`, and complete `anchors` list. The licensed PDF is not needed.

`src/svtorture/catalog.py` loads and validates the standard index, requirement TOML files, and case TOML files into a frozen `Catalog`. A requirement has an ID, numeric chapter, clause, and one or more exact anchors. A case has one primary requirement and zero or more related requirements.

`src/svtorture/publish.py::build_dataset()` converts the catalog and selected campaigns into `dashboard/dist/data/dataset.json`. Generated datasets are ignored. `merge_datasets()` retains the newly generated corpus data and merges only historical campaigns and metric points, so the new corpus summary remains current even when Pages history is preserved.

`dashboard/src/types.ts::Dataset` is the TypeScript compile-time dataset contract. `dashboard/src/testDataset.ts::makeTestDataset()` supplies the common frontend fixture. `dashboard/src/App.tsx` renders a sticky site header, non-sticky Campaign/From/To controls, then a sticky `.workspace-bar` containing tabs and filters. The Requirements view ID is `matrix`; the Cases view ID is `evidence`.

A ratio in this plan is a pair of exact non-negative integers named `numerator` and `denominator`. Coverage formats that ratio as a percentage. Density formats it as a unit value. When a breakdown row has a zero denominator, the UI must show an em dash rather than `NaN` or an implied 100 percent, while still exposing `0 / 0` in the detail row.

## Open Questions

There are no open product questions. The user confirmed that Requirements Density means requirements per covered anchor. The implementation counts all primary and related case links and all requirement anchors.

## Plan of Work

First, extend `src/svtorture/publish.py` with a private builder that reads the validated committed anchor index from `catalog.root`. Preserve the index order while creating 58 part descriptors: 41 chapters followed by 17 annexes. Build a map from every anchor to its part. For requirements, create unique `(requirement_id, anchor)` pairs; overall Coverage is unique anchors divided by all index anchors, and Density is pairs divided by unique anchors. For each part, use only anchors and pairs mapped to that part. For cases, create unique `(case_id, requirement_id)` pairs from the primary and related fields; overall Coverage is unique linked requirement IDs divided by all catalog requirements, and Density is pairs divided by unique linked requirements. For each part, group by the linked requirement’s owning chapter. Return exact operands and ordered breakdown rows under `dataset["corpus_coverage"]`.

Add backend tests in `tests/test_publish.py`. Assert the current catalog’s exact global operands, 58 ordered rows, zero-valued annex case rows, the shared Chapter 6 requirement anchor producing two relationships over one covered anchor, and a copied catalog with one synthetic related requirement producing one additional case relationship. Assert that dataset merging retains the new summary from the newly generated dataset.

Next, extend `dashboard/src/types.ts` with ratio, breakdown-row, summary, and two-summary container interfaces. Make `Dataset.corpus_coverage` required. Update `dashboard/src/testDataset.ts` with small exact fixture operands and at least one chapter and annex row.

Create `dashboard/src/CorpusCoverage.tsx`. It accepts `kind` (`requirements` or `cases`) and one summary. Its collapsed native disclosure summary renders only `Coverage`, the formatted percent, `Density`, the formatted value, and a concise Breakdown label/chevron. Each metric has a native hover title containing the semantic pseudo-formula, exact operands, and displayed result. The disclosure references a visually hidden formula explanation for assistive technology. Its expanded semantic table lists Part, Coverage, and Density for every provided row, includes exact numerator/denominator operands, distinguishes Chapter from Annex, and uses an em dash when a denominator is zero.

Render this component in `dashboard/src/App.tsx` after `.campaign-overview` and before `.workspace-bar`, selecting `dataset.corpus_coverage.requirements` for `view === "matrix"` and `.cases` for `view === "evidence"`. Do not render it for Overview, Changes, or Campaigns. Add compact styles to `dashboard/src/styles.css`; keep the collapsed height near one control row, avoid sticky positioning, allow names to wrap on narrow screens, and use only the page’s global vertical scrollbar.

Add `dashboard/src/CorpusCoverage.test.tsx` to verify formatting, formulas, disclosure behavior, all supplied breakdown rows, and zero denominators. Extend `dashboard/src/App.test.tsx` to prove the strip appears only after selecting Requirements or Cases and remains absent from the other tabs. Update `dashboard/README.md` with the four formulas and the fact that expansion is grouped by all chapters and annexes.

Finally, run focused tests, rebuild the ignored local dataset from all local campaigns, and inspect desktop, short-desktop, and 390-pixel mobile views in Chrome. Verify that the strip scrolls away, the workspace remains sticky, disclosure works by mouse and keyboard, there is no page-level horizontal overflow, and no runtime or network error occurs. Run `just smoke`. Because GitHub Actions workflows are intentionally disabled and `just ci` requires Docker/network, do not alter workflow state for this feature.

### Concrete Steps

Work from `/home/esynr3z/projects/svtorture`.

1. Implement and test dataset operands:

       uv run pytest -q tests/test_publish.py

   Expect all publication tests to pass and new assertions to report overall Requirements `16/16963`, Requirements Density `17/16`, Cases Coverage `12/12`, and Cases Density `12/12` for the current corpus.

2. Implement frontend types, fixture, component, integration, and tests:

       npm --prefix dashboard run typecheck
       npm --prefix dashboard test

   Expect TypeScript to report no errors and all frontend tests, including the new coverage component tests, to pass.

3. Build the generated local dataset and frontend from all ignored campaigns:

       campaigns=$(find .svtorture/campaigns -mindepth 2 -maxdepth 2 -name campaign.json -print | sort | paste -sd' ' -)
       just dashboard-build "$campaigns"

   Inspect `dashboard/dist/data/dataset.json` only as generated evidence. It must contain `corpus_coverage` with 58 breakdown rows for each view. Do not add the generated file to Git.

4. Serve and inspect:

       just dashboard-serve

   Open `http://localhost:4173/?view=matrix` and `http://localhost:4173/?view=evidence`. Confirm compact collapsed strips, hover formulas, full disclosure rows, responsive wrapping, and sticky filters after scrolling.

5. Run the stable local gate:

       just smoke
       git diff --check

   Expect every command to succeed.

6. Update this living plan with evidence and outcomes, then remove `CORPUS_COVERAGE_EXECPLAN.md` before final handoff.

### Validation and Acceptance

The feature is accepted when all of the following are observable:

- Requirements displays `Coverage 0.09%` from `16 / 16,963` and `Density 1.06` from `17 / 16` for the current corpus.
- Cases displays `Coverage 100%` from `12 / 12` and `Density 1` from `12 / 12` for the current corpus.
- Hovering Coverage or Density exposes a readable pseudo-formula and exact operands; keyboard focus on the disclosure has an accessible formula description.
- Expanding either strip lists all 41 chapters and 17 annexes in standard-index order. Requirement relationships are assigned by actual anchor location; case relationships are assigned by requirement chapter.
- A zero-denominator case row renders an em dash and `0 / 0`, never `NaN`, `Infinity`, or a misleading percentage.
- The strip appears only in Requirements and Cases, scrolls away with normal document flow, and does not change the existing sticky filter behavior.
- Desktop and mobile have one global vertical scrollbar and no page-level horizontal overflow.
- Backend tests, frontend typecheck/tests/build, `just smoke`, and `git diff --check` pass.

### Idempotence and Recovery

Dataset construction is deterministic and reads only committed catalog/index inputs. Re-running export replaces ignored generated data without changing tracked source. The UI has no persisted disclosure state, so refresh safely returns it to collapsed. If an implementation step fails, revert only the current source edits and rerun the focused command; no migration, external service, or destructive operation is involved. Do not edit the anchor JSON, generated dashboard dataset, or campaign files.

### Artifacts and Notes

Current expected operands are:

    Requirements Coverage: 16 / 16,963 = 0.0943…%
    Requirements Density: 17 / 16 = 1.0625 requirements per covered anchor
    Cases Coverage: 12 / 12 = 100%
    Cases Density: 12 / 12 = 1 case per covered requirement

A useful cross-chapter proof is Chapter 6: two requirements reference the same Chapter 6 anchor, so its Requirements Coverage numerator is 1 while its Density numerator is 2. Chapter 3 receives a requirement anchor relationship from the Chapter 26 package-import requirement because breakdown follows anchor location.

### Interfaces and Dependencies

In `src/svtorture/publish.py`, define a private function with the stable responsibility:

    def _corpus_coverage(catalog: Catalog) -> dict[str, Any]: ...

It returns:

    {
      "requirements": {
        "coverage": {"numerator": int, "denominator": int},
        "density": {"numerator": int, "denominator": int},
        "breakdown": [
          {
            "kind": "chapter" | "annex",
            "id": str,
            "title": str,
            "coverage": {"numerator": int, "denominator": int},
            "density": {"numerator": int, "denominator": int}
          }
        ]
      },
      "cases": {same shape}
    }

`build_dataset()` must expose that value as required `corpus_coverage`.

In `dashboard/src/types.ts`, define matching `Ratio`, `CorpusCoveragePart`, `CorpusCoverageMetric`, and `CorpusCoverage` interfaces and add `corpus_coverage: CorpusCoverage` to `Dataset`.

In `dashboard/src/CorpusCoverage.tsx`, export:

    type CorpusCoverageKind = "requirements" | "cases";

    interface CorpusCoverageProps {
      kind: CorpusCoverageKind;
      metric: CorpusCoverageMetric;
    }

    export function CorpusCoverage({ kind, metric }: CorpusCoverageProps): JSX.Element;

Use only React, native HTML disclosure/table semantics, and existing CSS variables. No dependency changes are permitted.

Revision note (2026-07-26 11:24Z): Initial plan created after repository exploration and user confirmation of the Requirements Density direction.

Revision note (2026-07-26 11:38Z): Updated progress and outcomes after completing the deterministic dataset milestone; focused publication tests pass 12/12.

Revision note (2026-07-26 11:42Z): Recorded and corrected the stale test expectation for the intentionally removed `.github/README.md`, discovered by the milestone pre-commit gate.

Revision note (2026-07-26 14:40Z): Updated progress and outcomes after implementing the frontend strip, complete disclosure tables, formulas, documentation, tests, and responsive Chrome checks.
