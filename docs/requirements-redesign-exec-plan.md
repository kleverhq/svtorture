# Redesign the Requirements evidence browser

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the repository's `exec-plan` skill.

## Purpose / Big Picture

The Requirements tab must remain useful when the catalog grows from a few requirements to thousands. After this work, a user can browse the complete named IEEE Std 1800-2023 hierarchy on the left, select one or more chapters or clauses to filter the requirements, click a section title to jump to its first visible requirement, and scroll compact requirement cards on the right. With one tool selected, the hierarchy gives an at-a-glance worst-result view of support by section. Requirement cards expose revision applicability and tags while keeping detailed anchors, tool evidence, and supporting cases collapsed until requested.

The same page will explain Requirements Coverage and Density as a relationship between standard anchors and requirements, and its chapter breakdown will use neutral, red, yellow, and green coverage bands. The Cases tab remains behaviorally unchanged.

## Non-Goals

This work does not redesign the Cases tab, remove its Advanced filters, change conformance or scoring semantics, add tag-click filtering, add subclause-level corpus coverage metrics, or change the canonical schema-version-5 campaign record. It does not commit the licensed IEEE PDF or generated annotated standard text.

## Progress

- [x] (2026-08-03 14:35Z) Inspected the Requirements rendering path, URL-backed filters, corpus metric UI, strict catalog and bundle models, annotator pipeline, schemas, fixtures, and relevant tests.
- [x] (2026-08-03 14:58Z) Confirmed that the annotator already retains every heading title while rendering `:H:` blocks and that the bundled local IEEE Std 1800-2023 PDF reproduces the committed anchor index.
- [x] (2026-08-03 15:02Z) Wrote this self-contained implementation plan and recorded the accepted interaction and status rules.
- [x] (2026-08-03 17:59Z) Milestone 1: materialized 1,740 named standard sections in anchor-index schema version 2, carried them through version-6 campaign catalogs and frontend datasets, regenerated the catalog schema and fixture, and passed focused annotator, Python, and loader tests.
- [x] (2026-08-03 18:04Z) Milestone 2: removed Advanced filters only from Requirements, made Requirements ignore stale Cases-only advanced URL values, retained all quick filters, and added the coverage context label and exact threshold row tones; 46 focused frontend tests and type checking passed.
- [x] (2026-08-03 18:19Z) Milestone 3: replaced the one-item selector with the complete expandable hierarchy and all-card scroller, added URL-backed tri-state subtree filtering, one-tool worst-status tones, applicability and tags, lazy collapsed evidence, responsive layout, and focused tests; all 91 frontend tests, type checking, production build, and desktop/mobile headless visual checks passed.
- [x] (2026-08-03 19:04Z) Milestone 4: passed authoritative annotation regeneration, `just smoke`, full Docker/network `just ci`, final production build, visual checks, and all delayed read-only review lanes; fixed every substantive correctness, accessibility, contract, and scaling finding and audited every acceptance criterion.
- [x] (2026-08-04 08:55Z) Follow-up: changed wide Requirements to global card scrolling with sticky TOC and evidence headers below the sticky quick filters, added a collapsed URL-backed tag cloud and clickable card tags with AND semantics, and fixed sticky-header scroll offsets and direct-URL tag canonicalization after focused review.

## Surprises & Discoveries

- Observation: The committed anchor index has all 16,963 anchors and heading locations but stores titles only for the 58 top-level chapters and annexes.
  Evidence: `standards/ieee-1800-2023-anchors.json` contains `:H:` anchors such as clause headings, while each top-level entry alone has a `title` field.

- Observation: No second PDF parser is needed to obtain subclause names. The annotator's `render_anchors_index()` receives rendered heading blocks whose content includes the complete title, including multiline titles.
  Evidence: A local generation against the bundled IEEE Std 1800-2023 PDF found 1,740 unique heading locations, including 33 multiline heading blocks, and reproduced the current committed index byte-for-byte before adding the new projection.

- Observation: Existing status priority is not exactly the hierarchy rule. In particular, existing aggregation can prefer an unsupported gray result over a conforming green result, while the accepted hierarchy rule says green plus gray remains green.
  Evidence: `dashboard/src/model.ts` orders unsupported statuses before `conforming` in `STATUS_PRIORITY`; the hierarchy therefore needs a small group-level aggregation rule rather than reusing that ordering unchanged.

- Observation: Advanced filters are shared today because both Requirements and Cases pass `mode="corpus"` to `dashboard/src/Filters.tsx`.
  Evidence: `dashboard/src/App.tsx` maps both `matrix` and `evidence` views to the same filter mode.

- Observation: Fifteen generated heading blocks carried visual-review marker lines that are useful to annotators but unsuitable as UI titles.
  Evidence: The first generated hierarchy projection contained `[FORMALISM_REQUIRES_VISUAL_REVIEW]`, `[LAYOUT_REQUIRES_VISUAL_REVIEW]`, or `[TEXT_ANNOTATION_REQUIRES_VISUAL_REVIEW]` in 15 titles. `heading_title()` now omits exact marker lines while retaining the source-owned heading text, and the regenerated hierarchy contains no marker suffixes.

- Observation: Native closed `<details>` elements hide content visually but React still constructs every child element, which scales poorly when thousands of cards each have profile and case lists.
  Evidence: The first compact-card implementation passed behavior tests but eagerly evaluated all evidence and supporting-case maps. `LazyDetails` now accepts a render callback and invokes it only after the disclosure opens.

- Observation: Compact parent-prefix selection alone cannot represent unchecking one child while preserving the parent's own requirement and selected sibling branches.
  Evidence: A checked `13` token means every descendant, so removing `13.5.1` requires representing the exact `13` node separately from full sibling subtrees. The URL codec now uses ordinary tokens for complete subtrees and an internal `=` prefix for an exact node.

- Observation: The existing exact-status aggregate is valid for evidence badges but not for the accepted tree grouping when one profile has both passing and gray case results.
  Evidence: Read-only control review found that `aggregateStatus()` ranks unsupported statuses above conforming. Tree tones now consume every underlying result status directly, and an integration test proves conforming plus unsupported-capability remains visibly and accessibly green.

- Observation: URL state can contain unknown section tokens from manual edits or older links.
  Evidence: Control review found that checking raw token count produced an empty card list even though decoding safely ignored all tokens. All/filtering state now uses the decoded selection size, and a regression test proves unknown-only selections show All and retain cards.

- Observation: Background color plus one common dot was not a sufficient non-color status cue.
  Evidence: Accessibility review required each tone to be distinguishable without color. Rows now show `✕`, `!`, `✓`, or `–` and expose a full `Section result:` accessible label.

- Observation: The independent performance and accessibility lanes completed after the first control handoff and exposed work that small fixtures could not show.
  Evidence: Filtering and per-profile evidence are now memoized independently of hierarchy navigation; cards are memoized with stable empty arrays and callbacks and use offscreen CSS containment; scroll effects avoid redundant updates; nested lists use native semantics and preserve indentation; live announcements are limited to the result count; and programmatic scrolling honors reduced motion.

- Observation: Historical omission compatibility must not permit newly exported incomplete section arrays.
  Evidence: `Catalog.standard_sections` is required for exporters, while `CampaignCatalog` accepts an omitted field only for old version-6 resources and rejects a present array unless it contains all 1,740 sections. A bundle-level regression removes the field, updates integrity metadata, and proves validation and assembly remain compatible.

## Decision Log

- Decision: Store the complete table of contents in `standards/ieee-1800-2023-anchors.json`, beside the runtime anchors, and generate it from the local annotated corpus.
  Rationale: This is the existing committed runtime source for standard structure and citations. `standards/index.toml` intentionally lists only chapters with maintained requirements and cannot represent the complete standard.
  Date/Author: 2026-08-03 / pi

- Decision: Represent the table of contents as one canonically ordered flat list of clause location and title records rather than a recursive JSON tree.
  Rationale: Dotted standard locations already encode ancestry. A flat list is smaller, easier to validate, and lets the browser derive a tree without duplicating parent-child relationships.
  Date/Author: 2026-08-03 / pi

- Decision: Bump the internal anchor-index format from schema version 1 to 2, but keep dashboard transport at version 6 with the new campaign-catalog field backward-readable as an empty default.
  Rationale: The committed runtime index is changed in a required way and should fail clearly if stale. A dashboard-wide version 7 migration would touch unrelated manifest, verdict, evidence, trend, release, and assembly contracts. The catalog exporter will always emit the complete hierarchy, while accepting an absent field permits replay and validation of existing immutable version-6 bundles. New generated schemas remain strict about malformed hierarchy entries when the field is present.
  Date/Author: 2026-08-03 / pi

- Decision: Keep all hierarchy selection in a dedicated URL field, with an empty value meaning All.
  Rationale: Dashboard guidance requires filters to be URL-backed. A dedicated field prevents the new multi-selection from colliding with the Cases-only single clause-prefix filter.
  Date/Author: 2026-08-03 / pi

- Decision: A section checkbox filters by that location and all descendants; redundant descendants are removed when a parent is selected. Selecting multiple unrelated branches uses OR semantics. Removing the final explicit selection returns to All.
  Rationale: This implements ordinary table-of-contents selection while keeping URLs canonical and compact.
  Date/Author: 2026-08-03 / pi

- Decision: Encode a completely selected subtree as its root location and a selected exact internal node as `=<location>` when a descendant has been unchecked.
  Rationale: This preserves ordinary tri-state checkbox behavior, including parent-owned requirements, without expanding a chapter selection into hundreds of URL values. The syntax is private to the URL-backed frontend state and unknown values are ignored safely.
  Date/Author: 2026-08-03 / pi

- Decision: A section title scrolls to the first currently rendered requirement in its subtree, a checkbox changes filtering, and a separate chevron expands or collapses children.
  Rationale: Navigation, filtering, and disclosure are independent user actions and must not have surprising side effects.
  Date/Author: 2026-08-03 / pi

- Decision: Keep the whole hierarchy visible. Show total and quick-filter-visible counts, and dim zero-match nodes rather than removing them.
  Rationale: The hierarchy is the standard's table of contents, not merely another result list. Keeping empty branches preserves orientation and makes gaps visible.
  Date/Author: 2026-08-03 / pi

- Decision: Color hierarchy rows only when `filters.tool` names one selected tool. Aggregate all currently selected profiles for that tool and use red for any fail or infrastructure error, yellow for any unclear result when no red exists, green for any pass when no red or yellow exists, and gray otherwise.
  Rationale: Aggregating multiple tools into one row color would make cross-tool support misleading. The accepted rule treats red as worst, unclear as caution, pass plus gray as pass, and all-gray as gray.
  Date/Author: 2026-08-03 / pi

- Decision: Keep each requirement header, three-revision applicability table, and tags visible. Put Standard anchors, Tool evidence, and Supporting cases in independently expandable detail sections.
  Rationale: This preserves useful scanning information while preventing thousands of full evidence inspectors from producing an unusably long initial page.
  Date/Author: 2026-08-03 / pi

- Decision: Requirements ignores all Cases-only advanced filter fields but preserves the existing quick filters Tools, Profile, Result, and Compare. Cases continues to use every existing advanced filter.
  Rationale: Hidden filters must not silently remove Requirements, and the user explicitly limited this refactor to Requirements.
  Date/Author: 2026-08-03 / pi

- Decision: On wide screens, requirement cards use global page scrolling; the TOC column and Requirement evidence header stick below the sticky filter panel. Cases retains its independent evidence scrollers, and narrow screens retain normal flow.
  Rationale: A single global scroll is the observed browsing path, so table context must remain visible instead of sliding beneath the quick filters.
  Date/Author: 2026-08-04 / pi

- Decision: Requirement tags use a dedicated canonical URL field and combine with AND semantics. Cases ignores this field. Both the tag cloud and card tag buttons toggle the same state.
  Rationale: Selecting multiple traits should narrow to requirements carrying every chosen tag, while preserving shareable URLs and avoiding a behavior change to Cases.
  Date/Author: 2026-08-04 / pi

## Outcomes & Retrospective

All milestones are complete. The committed runtime index contains 1,740 source-derived section names and strict validation proves a one-to-one canonical match with every heading anchor. New campaign catalogs publish the hierarchy, old version-6 catalogs remain readable, the generated public schema describes the projection, and the dashboard loader carries it into `Dataset.standard_sections`. Requirements has only the accepted quick filters and ignores hidden Cases-only values; Cases retains Advanced filters. Requirements Coverage has the explanatory context and exact neutral/red/yellow/green boundaries. The Requirements browser presents the full expandable standard tree beside every matching compact card, with URL-backed subtree selection, one-tool raw-result status grouping, non-color status symbols, applicability, tags, and lazily mounted detail disclosures.

Final evidence is complete: `just annotate-check` regenerated 58 parts and 16,963 unique anchors and found the committed hierarchy byte-identical; `just ci` passed 187 non-Docker Python tests, 11 Docker tests, all metadata/type/lint gates, 91 frontend tests, a production build, and a real five-case Icarus campaign. After every early and delayed review fix, the tag/sticky follow-up's final `just smoke` passed 121 focused Python tests, all annotator checks, and 96 frontend tests. The follow-up also passed 54 focused frontend tests, type checking, production build, refreshed local campaign export, and a 1440×800 visual check. Correctness, performance, data-contract, accessibility, impacted-lane, sticky-layout, and final control reviewers were run; every substantive finding was fixed and retested. No required work remains.

## Context and Orientation

SVTORTURE turns a repository-owned catalog of normative SystemVerilog requirements and test cases into immutable campaign evidence. `src/svtorture/models.py` defines strict canonical records. `src/svtorture/catalog.py` loads `standards/index.toml`, requirement TOML files, cases, and the committed runtime anchor index. `src/svtorture/bundle.py` projects a canonical campaign into a portable version-6 static dashboard bundle. The browser first loads a campaign manifest and then its `catalog.json`, which contains requirements, cases, and corpus metrics.

The local authoring path begins in `standards/ieee-1800-2023-annotate/annotate.py`. It extracts the user-supplied IEEE Std 1800-2023 PDF into ignored rendered text and an `anchors.json`. The explicit `just annotate-update-anchors <pdf>` command copies only the generated anchor index to `standards/ieee-1800-2023-anchors.json`. The PDF and rendered text are licensed local inputs and must never be committed. The SystemVerilog skill provides an ignored local IEEE Std 1800-2023 PDF that can be passed explicitly to the existing command.

A standard location is a dotted identifier such as `7`, `7.2`, `7.2.1`, or `A.1`. Each requirement already has one primary `clause` location. A requirement belongs to that exact node and every ancestor prefix ending at a dot boundary. Related clauses are citations and do not change the requirement's primary location in the hierarchy.

`dashboard/src/App.tsx` owns the selected view and URL-backed `Filters`. It calls `filterCorpus()` from `dashboard/src/model.ts`, renders `Filters`, and passes filtered requirements to `dashboard/src/RequirementsView.tsx`. The current Requirements view renders a scrollable list on the left and one selected detail pane on the right. `dashboard/src/CorpusCoverage.tsx` renders the Requirements Coverage and Density summary and chapter/annex breakdown. `dashboard/src/styles.css` owns all dashboard presentation and responsive behavior. `dashboard/src/useDashboard.ts` validates and combines the lazy version-6 resources into the frontend `Dataset` declared in `dashboard/src/types.ts`.

The complete hierarchy has about 1,740 headings. The browser must therefore initially render only the 58 root chapter and annex rows, recursively mounting descendants as users expand branches. Requirement cards may number in the thousands; they should use ordinary document flow and collapsed details, while memoized maps avoid repeating requirement-to-case and requirement-to-result joins for every render. No new dependency is necessary.

## Open Questions

There are no unresolved product questions. If implementation reveals that a heading block cannot be normalized without losing meaningful text, preserve its rendered lines joined by one space and record the exact case in `Surprises & Discoveries` rather than inventing a title.

## Plan of Work

Milestone 1 makes the hierarchy an authoritative, validated data asset. In `standards/ieee-1800-2023-annotate/annotate.py`, extend anchor-index rendering to collect every `:H:` anchor's standard location and normalized heading content into a canonical flat array. Add focused tests in `standards/ieee-1800-2023-annotate/tests/test_annotate.py` for numbered and annex headings, multiline titles, ordering, and duplicate rejection. Regenerate `standards/ieee-1800-2023-anchors.json` from the local IEEE Std 1800-2023 PDF and verify that no generated text or PDF enters Git.

In `src/svtorture/models.py`, add the strict public value type used for a standard section. In `src/svtorture/catalog.py`, parse anchor-index schema version 2, require a unique canonically ordered section for every heading anchor, expose the sections on `Catalog`, and retain existing top-level metric title behavior. Add malformed-index tests in `tests/test_catalog_models.py`.

In `src/svtorture/dashboard_models.py`, add the ordered hierarchy to `CampaignCatalog`, with an empty tuple default only for reading historical version-6 bundles. In `src/svtorture/bundle.py`, always populate it from the current catalog. Extend `tests/test_bundle.py` and replay tests to prove current exports contain the complete hierarchy, malformed entries are rejected, deterministic hashes remain stable, and an old version-6 catalog without the optional field can still be read. Run `just schemas` and verify that only the intended generated catalog schema shape changes. Refresh the compact dashboard test fixture and its manifest resource hash and byte count through the repository's existing bundle/export helpers rather than hand-editing generated JSON.

Milestone 2 separates Requirements controls from Cases controls. In `dashboard/src/Filters.tsx`, replace the shared corpus mode with explicit Requirements and Cases modes. Both modes retain Tools, Profile, Result, and Compare. Only Cases renders Advanced filters and its auto-open behavior. In `dashboard/src/App.tsx` and `dashboard/src/model.ts`, project Requirements filtering onto quick fields only, so advanced values retained from a Cases URL cannot invisibly hide requirement cards. Add a dedicated URL-backed standard-section selection field to `Filters`, `filtersFromSearch()`, and `filtersToSearch()`.

In `dashboard/src/CorpusCoverage.tsx`, prefix the Requirements summary with `Standard anchors vs requirements:` while leaving Cases wording unchanged. Classify each breakdown row by its coverage ratio: denominator zero or exactly zero is gray, greater than zero and less than 30 percent is red, at least 30 and less than 80 percent is yellow, and at least 80 percent is green. Apply accessible classes and preserve text operands so color is never the sole information. Extend `dashboard/src/CorpusCoverage.test.tsx` and filter/App tests to prove exact boundaries and Cases compatibility.

Milestone 3 creates the new browser in `dashboard/src/RequirementsView.tsx`, extracting small local components or pure helpers only where tests or readability justify them. Build the hierarchy from the complete flat section list. Render an All checkbox followed by expandable chapter and annex roots. Each row has a disclosure chevron when children exist, a tri-state checkbox, a title button, total and quick-visible counts, and—only for one explicitly selected tool—a derived worst-status tone. Zero-match rows remain but are dimmed. Add pure tests for dotted-boundary ancestry, canonical multi-selection, parent indeterminate state, and status aggregation.

Filter right-side cards using the selected hierarchy prefixes. Clicking a row title uses stored card element references to scroll to the first rendered requirement in that subtree without changing selection. Deep-linked `requirementId` scrolls to its card and remains represented by each card's Copy link. Render all matching requirements as compact articles in standard-location order. Keep clause, summary, stable ID, revision applicability for 2012/2017/2023, and tags visible. Render Standard anchors, Tool evidence, and Supporting cases as collapsed sections that preserve existing evidence navigation callbacks and grouped status badges. Empty states distinguish no quick-filter matches from no requirements in selected branches.

Replace the old fixed split-pane CSS in `dashboard/src/styles.css` with a sticky, independently scrollable table-of-contents column and a scrolling card column on desktop. On narrow screens, use normal document flow with the hierarchy above cards so keyboard and touch users are not trapped in nested full-height scroll panes. Preserve focus indicators, semantic buttons and checkboxes, accessible names, and reduced-motion behavior. Tests in `dashboard/src/RequirementsView.test.tsx` and `dashboard/src/App.test.tsx` must exercise checkbox filtering, title navigation, multi-selection URL round trips, complete empty branches, one-tool status tones, collapsed details, applicability, tags, direct links, and existing evidence/case navigation.

Milestone 4 runs focused tests after each area, then the root deterministic suite. Inspect `git diff --check`, generated artifacts, and ignored files before each commit. Update `Progress`, `Surprises & Discoveries`, decisions, validation evidence, and this retrospective after every milestone. Commit coherent increments using Conventional Commits; do not combine unrelated cleanup.

### Concrete Steps

All commands run from `/home/esynr3z/orca/workspaces/sv-torture/fix-redesign_req_cases_tabs-2`.

First establish the data contract and regenerate the source index:

    uv run python -m unittest discover -s standards/ieee-1800-2023-annotate/tests -v
    just annotate-update-anchors /home/esynr3z/.pi/agent/skills/systemverilog/references/IEEE-1800-2023.pdf
    uv run pytest -q tests/test_catalog_models.py tests/test_bundle.py tests/test_reproduce.py
    just schemas

Expect annotator and Python tests to pass, the committed index to change only by schema version and the ordered hierarchy, and no files under `standards/ieee-1800-2023-annotate/generated/` to be staged.

Then implement and test each frontend slice:

    npm --prefix dashboard test -- CorpusCoverage.test.tsx
    npm --prefix dashboard test -- RequirementsView.test.tsx App.test.tsx useDashboard.test.tsx
    npm --prefix dashboard run typecheck
    npm --prefix dashboard run build

Finally run repository-wide deterministic checks:

    just smoke
    git diff --check
    git status --short

`just smoke` must complete with formatting, lint, typing, metadata validation, focused Python tests, annotator tests, frontend type checking, and frontend unit tests all passing. If Docker and network access are available at handoff, run `just ci`; otherwise record why its Docker/network-only stages were not run.

### Validation and Acceptance

A generated `standards/ieee-1800-2023-anchors.json` must contain one named entry for every `:H:` location, in canonical standard order, and `just annotate-check` against the same PDF must report no difference. Catalog loading must reject a missing, duplicate, out-of-order, or mismatched heading entry.

A newly exported campaign catalog must contain the complete hierarchy and validate against `schemas/campaign-catalog.schema.json`. A historical version-6 catalog without the hierarchy field must still parse for replay and assembly. Requirement, case, and selection corpus hashes must retain their existing semantics; the manifest catalog resource hash and byte count must reflect the larger catalog.

In the browser, the Requirements Coverage summary must read `Standard anchors vs requirements:` followed by Coverage and Density. Breakdown rows at 0 percent or undefined are gray, 1–29.999 percent red, 30–79.999 percent yellow, and 80–100 percent green. Numeric values and operands remain visible.

The Requirements tab must show no Advanced filters, while Cases must retain and apply them. Requirements must retain Tools, Profile, Result, and Compare and ignore stale Cases-only advanced fields. Selecting hierarchy branches must update the URL and show the OR-union of requirements in those branches; checking a parent includes descendants, partial descendants make the parent indeterminate, and removing the final selection returns to All.

The left side must expose all named IEEE Std 1800-2023 chapters, annexes, and expandable subclauses, including sections with zero catalog requirements. A title click must move the right pane to the first visible card in that subtree without changing checkboxes. With no explicit tool selected, rows have no conformance tone. With one tool selected, any fail or infrastructure error makes the containing branches red; otherwise unclear makes them yellow; otherwise at least one pass makes them green even alongside gray statuses; all-gray branches remain gray.

The right side must show every matching compact requirement card, not one selected inspector. Each card visibly shows clause, summary, ID, all three revision-applicability records, and tags. Anchors, tool evidence, and supporting cases start collapsed and remain navigable when expanded. Direct requirement links scroll to the linked card, and each card's Copy link continues to produce a shareable URL.

At desktop width, the hierarchy and cards scroll usefully without the old one-item inspector. At narrow width, both regions remain reachable in normal flow. Keyboard users can expand nodes, toggle checkboxes, activate title navigation, open details, and follow existing evidence actions with visible focus.

### Idempotence and Recovery

Annotator generation is deterministic. Re-running `just annotate-update-anchors` with the same PDF must produce an identical committed index. `just schemas` is also deterministic and may be repeated safely. If annotation fails, remove only the ignored `standards/ieee-1800-2023-annotate/generated/` directory and rerun; never modify or delete the external reference PDF.

Before committing, use `git status --short` and `git diff --cached` to ensure no PDF, generated standard text, `.svtorture/` output, logs, or unrelated files are staged. If a generated fixture becomes inconsistent, regenerate the bundle fixture from its source rather than repairing hashes by hand.

### Artifacts and Notes

The hierarchy source shape should remain conceptually small even though the generated array is long:

    "sections": [
      {"clause": "7", "title": "Aggregate data types"},
      {"clause": "7.1", "title": "..."},
      {"clause": "7.2", "title": "..."}
    ]

A canonical hierarchy URL should use one query parameter with comma-separated locations, for example:

    ?view=matrix&sections=7.2,12.4

The exact heading titles are derived from IEEE Std 1800-2023 and are stored only in the generated runtime index and campaign catalog. The licensed source PDF and complete generated text stay outside Git.

### Interfaces and Dependencies

Do not add frontend or Python dependencies. Use Pydantic strict models already defined by `src/svtorture/models.py`, React state and memoization already used by the dashboard, native `<details>`, `<button>`, and `<input type="checkbox">` controls, and existing status helpers where their semantics match.

At the end of Milestone 1, `src/svtorture/models.py` must define a strict standard-section value with a `clause` matching `StandardLocation` and a bounded nonempty `title`. `Catalog` must expose an immutable ordered tuple of these values. `CampaignCatalog` must expose the same tuple, defaulting to empty only while reading historical version-6 resources; `_catalog()` must always populate it for new exports. `dashboard/src/types.ts` must expose the corresponding `StandardSection` and `Dataset.standard_sections` values, and `useDashboard.datasetFrom()` must carry them through.

At the end of Milestone 3, hierarchy helpers must compare standard locations on dot boundaries rather than raw string prefixes, so `7.2` includes `7.2.1` but not `7.20`. Selection normalization must remove descendants already covered by a selected ancestor and sort locations in canonical IEEE order. Status aggregation must operate on displayed status groups and implement the accepted red, yellow, green, gray priority independently of the existing exact-status priority.

Revision note (2026-08-03): Initial plan created after repository and annotator research. It resolves storage location, compatibility, hierarchy interaction, filtering, status aggregation, card density, and validation from the user's accepted design before implementation begins.

Revision note (2026-08-03 17:59Z): Updated after Milestone 1 to record the completed hierarchy contract, validation evidence, and the discovered need to remove authoring-only visual-review markers from display titles.

Revision note (2026-08-03 18:04Z): Updated after Milestone 2 to record Requirements-only filter separation, hidden-filter semantics, coverage presentation, and focused frontend evidence.

Revision note (2026-08-03 18:19Z): Updated after Milestone 3 to record the completed hierarchy and card browser, exact-node URL encoding, lazy disclosure rendering, responsive visual evidence, and full frontend results.

Revision note (2026-08-03 18:52Z): Completed the initial Milestone 4 audit after full local CI, authoritative annotation comparison, and two control review passes. Recorded and resolved raw-status aggregation, unknown URL tokens, accessible status naming, and non-color status-symbol findings.

Revision note (2026-08-03 19:04Z): Reopened and completed Milestone 4 when delayed independent review lanes returned. Recorded and resolved repeated corpus filtering, large-card rerenders, offscreen rendering, scroll targeting/effects, native list semantics, live-region scope, reduced motion, nested indentation, complete-present catalog enforcement, and historical bundle integration coverage.

Revision note (2026-08-04 08:55Z): Added the requested global-scroll sticky table context and multi-tag filtering follow-up. Recorded AND semantics, shared cloud/card controls, Cases isolation, canonical URLs, sticky scroll margins, focused review, and refreshed local viewing data.
