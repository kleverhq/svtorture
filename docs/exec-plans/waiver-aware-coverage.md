# Apply standard-anchor waivers to requirement coverage

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the repository's `exec-plan` skill.

## Purpose / Big Picture

After this change, Requirements Coverage measures requirement-linked standard anchors against only the anchors that remain eligible for an independent requirement. An anchor waived as unsuitable for an independent portable requirement is removed from the denominator, but it is not added to the numerator. The dashboard's chapter-and-annex breakdown shows one additional `Waived` count so a reader can see how many anchors were excluded in each part.

A maintainer can observe the result by running a new campaign, exporting its dashboard data, and opening the Requirements tab. The coverage summary uses the adjusted operands, while the expanded breakdown contains a Waived column. Chapters 1 and 2 also receive reviewed waiver sidecars for every anchor that is currently neither cited by a requirement nor already waived, leaving no undispositioned standard anchors in the committed catalog.

## Non-Goals

This change does not waive case failures, change evaluator judgments, alter Cases Coverage, alter Requirements Density, add a waiver browser, publish waiver reasons to the dashboard, add a waiver trend, migrate old immutable campaign files, or introduce metric-semantic versioning. The dashboard receives only the adjusted frozen operands and per-part waived counts stored by new campaigns; it does not read source waiver files at build time.

## Progress

- [x] (2026-08-05 18:35Z) Inspected the existing waiver sidecars, corpus metric path, campaign snapshots, bundle projection, dashboard coverage component, and trend computation.
- [x] (2026-08-05 18:35Z) Resolved the product semantics: covered anchors take precedence over waived anchors; only waiver-only anchors leave the denominator.
- [x] (2026-08-05 18:36Z) Committed the initial ExecPlan as `1a2ff7a`.
- [x] (2026-08-05 18:42Z) Materialized and verified all 16,963 anchors from the matching IEEE 1800-2023 PDF, then inspected generated text and PDF pages 42–50 for chapters 1 and 2.
- [x] (2026-08-05 18:50Z) Added complete chapter 1 and chapter 2 waiver sidecars with 10 grounded records covering all 162 formerly open anchors.
- [x] (2026-08-05 19:08Z) Added strict waiver models and catalog loading with exact part inventory, source identity, duplicate, and anchor ownership validation.
- [x] (2026-08-05 19:10Z) Adjusted Requirements Coverage and carried per-part effective waived counts through new campaign and bundle models while leaving Cases unchanged.
- [x] (2026-08-05 19:18Z) Added the Waived column only to the Requirements breakdown and updated concise metric documentation and copy.
- [x] (2026-08-05 19:20Z) Regenerated public schemas and added deterministic backend and frontend tests, including strict bundle fixtures.
- [x] (2026-08-05 19:40Z) Passed focused checks, `just smoke`, and complete `just ci`, including 197 unit tests, 108 frontend tests, 11 Docker tests, production build, and a five-case Icarus campaign.
- [x] (2026-08-05 19:21Z) Committed implementation milestones as `82b0dd1` and `a4e7fef` using Conventional Commits.
- [x] (2026-08-05 19:48Z) Completed parallel code, architecture, and documentation review, fixed all findings, passed focused recheck, fixed the control pass's waiver-ID/part invariant, and received a clean final control recheck.
- [x] (2026-08-05 19:45Z) Built local dashboard assets and exported fresh campaign `20260805T193924Z-fb89a80e0e85e398`; served it at `http://127.0.0.1:4173` and verified both HTML and data endpoints return HTTP 200.
- [x] (2026-08-05 19:55Z) Pushed `feat-waivers` and opened GitHub pull request `https://github.com/kleverhq/svtorture/pull/3` against `main`.

## Surprises & Discoveries

- Observation: The imported sidecars contain 1,900 waiver records over 8,217 unique anchors, while requirements cite 8,696 unique anchors. The two sets overlap on 112 anchors.
  Evidence: A local set comparison over `standards/waivers/*.json`, `standards/requirements/*.toml`, and `standards/ieee-1800-2023-anchors.json` produced `waiver-only=8105`, `overlap=112`, and `open=162`.

- Observation: All 162 anchors currently in neither set belong to chapters 1 and 2.
  Evidence: The same comparison grouped the open set as chapter 1: 129 and chapter 2: 33.

- Observation: The authoritative PDF bundled with the SystemVerilog skill exactly matches the annotator's reference hash, and complete regeneration matches the committed anchor index.
  Evidence: `sha256sum` returned `203fbcccbbae90cef401a3acd31835c8cd1507e8f12b2e069046d4f316e317c9`; `just annotate-check` reported 58/58 files, 16,963 globally unique anchors, and `verification: PASS`.

- Observation: Two existing waiver anchors are intentionally present in more than one waiver record, while no record repeats an anchor internally.
  Evidence: `[2023:5.2:P001:p073]` and `[2023:6.9.2:P001:p108]` each support two different waiver rationales. Runtime validation must reject duplicates within a record but permit cross-record reuse.

- Observation: Adding a required per-part `waived` operand changes all campaign and dashboard schemas that embed `CorpusMetrics`, but the existing projection code needs no special waiver path.
  Evidence: After adding the field to `CorpusPartMetric`, `just schemas` updated the campaign, manifest, catalog, summary, and trends schemas; bundle tests passed without changes to `src/svtorture/bundle.py`.

- Observation: The shared per-part public model can structurally carry `waived` for Cases even though the UI hides it.
  Evidence: Initial code and architecture reviewers independently identified that malformed external campaign data could set a nonzero Cases waiver. `CorpusMetrics` now rejects that contradictory state.

- Observation: The first control pass found that a syntactically valid waiver ID could encode a different part from its record.
  Evidence: `Waiver.valid_waiver()` now applies the same part-token consistency rule used by requirements, and focused metadata tests reject both record-part and ID-part contradictions.

- Observation: Campaigns freeze complete aggregate and per-part corpus metric operands at collection time, and dashboard bundles copy those operands rather than reading `standards/` in the browser.
  Evidence: `src/svtorture/campaign.py` constructs `corpus_metrics=catalog.corpus_metrics()`, and `src/svtorture/bundle.py` copies `campaign.corpus_metrics` into bundle models.

## Decision Log

- Decision: Define effective waived anchors as `waiver anchors - requirement-covered anchors`.
  Rationale: A complete source block can support an existing requirement while a waiver explains why it yields no additional independent requirement. Covered precedence avoids removing such an anchor from both numerator and denominator and makes the displayed waived count reconcile with the adjusted denominator.
  Date/Author: 2026-08-05 / pi

- Decision: Compute Requirements Coverage as `covered / (all - effective waived)` and leave Requirements Density unchanged.
  Rationale: Waivers identify anchors ineligible for an independent requirement; they do not create requirements. Density remains requirement-to-anchor links per covered anchor, preserving its existing meaning.
  Date/Author: 2026-08-05 / pi

- Decision: Expose only an integer waived count in each Requirements breakdown row.
  Rationale: This is the only new dashboard behavior requested. Publishing waiver IDs, anchors, reasons, aggregate cards, or trends would add contracts and UI without a current need.
  Date/Author: 2026-08-05 / pi

- Decision: New campaigns snapshot the new operands; old immutable campaigns are not rewritten.
  Rationale: Corpus numerators and denominators already move when requirements and cases change. Existing strict campaign verification deliberately rejects re-export against a changed catalog, while already-built bundles remain self-contained.
  Date/Author: 2026-08-05 / pi

- Decision: Add waivers for every currently open chapter 1 and chapter 2 anchor, not for anchors already cited by requirements.
  Rationale: The request is to complete waiver disposition for those parts. Waiving already covered anchors adds no effective exclusion and obscures the intended partition.
  Date/Author: 2026-08-05 / pi

## Outcomes & Retrospective

The plan is complete. Chapter 1 has seven grounded waiver records covering 129 anchors, chapter 2 has three covering 33 anchors, and the full inventory has zero open anchors. Runtime validation loads all 58 sidecars. New campaign metrics report adjusted Requirements Coverage of `8696 / 8696`, Requirements Density of `10771 / 8696`, and 8,267 effective waived anchors; Cases remain unchanged. The Requirements breakdown alone renders the Waived column. Focused checks, `just smoke`, and final `just ci` pass. Parallel review and both control passes completed with every finding fixed and a clean final result. Production dashboard data from fresh campaign `20260805T195208Z-241f22980e32aa45` is served at `http://127.0.0.1:4173`. Branch `feat-waivers` is pushed and pull request `https://github.com/kleverhq/svtorture/pull/3` is open against `main`.

## Context and Orientation

SVTORTURE treats an anchor as a stable identifier for one complete source block in IEEE Std 1800-2023. The committed anchor inventory is `standards/ieee-1800-2023-anchors.json`. Normative requirements in `standards/requirements/` cite anchors. JSON sidecars in `standards/waivers/` explain why source anchors did not become additional independent, portable requirements. A waiver is therefore catalog-authoring disposition, not a simulator-result exception.

`src/svtorture/catalog.py` loads the anchor index, requirements, waivers, cases, suites, and tools into a frozen `Catalog`. `Catalog.corpus_metrics()` computes Requirements Coverage as unique cited anchors divided by eligible anchors after waiver-only exclusions, and computes Requirements Density as unique requirement-to-anchor links divided by cited anchors. `src/svtorture/campaign.py` stores these metrics in every new schema-version-5 campaign. `src/svtorture/bundle.py` projects the frozen values into schema-version-6 dashboard resources. `dashboard/src/useDashboard.ts` loads those static resources, and `dashboard/src/CorpusCoverage.tsx` renders the aggregate and per-part breakdown. The browser never reads the repository's `standards/` directory.

The waiver source shape is a JSON object with `authority`, `part`, `schema_version`, and `waivers`. Each waiver has `id`, `part`, a nonempty list of complete `anchors`, and a nonempty project-owned `reason`. Existing files use authority `1800-2023`, schema version 2, filenames `chapter-NN.json` or `annex-X.json`, globally unique IDs beginning with `WV-2023-`, and anchors belonging to the declared part.

For any standard part, let `A` be all anchors in the committed index, `R` be anchors cited by requirements, and `W` be anchors named by waivers. The implementation must derive `covered = R`, `waived = W - R`, and `eligible = A - waived`. Requirements Coverage is `len(covered) / len(eligible)`. The existing density remains the number of unique requirement-anchor pairs divided by `len(covered)`. The displayed Waived count is `len(waived)`, not `len(W)`, so the row reconciles as `original total = adjusted denominator + waived`.

## Open Questions

There are no open product or implementation questions. The completed implementation places a required nonnegative `waived` integer on the existing per-part metric model, populates effective counts for Requirements, fixes Cases values at zero, and enforces that Cases invariant in `CorpusMetrics`.

## Plan of Work

The first milestone establishes authoritative source disposition for chapters 1 and 2. Run the repository annotator against the bundled IEEE 1800-2023 PDF whose SHA-256 matches the committed anchor index, then inspect `standards/ieee-1800-2023-annotate/generated/txt/01.txt` and `02.txt`. Read the corresponding surrounding clauses and any visually marked pages in the PDF. Compare those anchors with requirement citations and write `standards/waivers/chapter-01.json` and `chapter-02.json` for exactly the currently uncovered anchors. Group anchors only when one concise reason truthfully applies to every grouped block. Acceptance for this milestone is that every waiver anchor exists in its declared part and `A - R - W` is empty.

The second milestone makes waivers runtime catalog input. Add strict frozen input models or equally strict local parsing in `src/svtorture/models.py` and `src/svtorture/catalog.py`, reusing existing JSON and standard-part helpers. Loading must reject malformed schema versions, authorities, filenames, part mismatches, duplicate waiver IDs, duplicate anchors within one record, unknown anchors, and anchors belonging to another part. It must load exactly the sidecars maintained by the repository. The resulting catalog needs only the set of waived anchors required by metric computation; no dashboard waiver records are needed.

The third milestone changes the frozen metric projection. In `Catalog.corpus_metrics()`, calculate effective waived anchors per part, subtract their count from Requirements Coverage's denominator, preserve its numerator and both density operands, and attach the effective waived count to the requirement breakdown. Cases metrics remain unchanged and carry no meaningful waiver display. Update strict public models and generated schemas only as required by this small field. Add backend tests for waiver-only exclusion, covered-and-waived precedence, malformed sidecars, chapter/annex aggregates, and the current complete-corpus operands.

The fourth milestone changes the dashboard presentation. Update `dashboard/src/types.ts` and `dashboard/src/CorpusCoverage.tsx` so only the Requirements breakdown has a `Waived` column. Keep the collapsed summary unchanged. Update its formula copy to say that coverage divides referenced anchors by eligible anchors after waiver-only exclusions. Add component tests that check the new column, its effective count, and the absence of that column in Cases. Update the trend description and concise authoritative documentation in `docs/methodology.md`, `standards/README.md`, and `dashboard/README.md` without duplicating architecture details.

The fifth milestone validates and demonstrates the complete path. Regenerate schemas with `just schemas`, run focused Python and frontend tests, then run `just smoke`. Run `just ci` if Docker and network access are available; record any environmental failure without weakening a gate. Create or use a fresh local campaign compatible with the changed catalog, build `dashboard/dist/` and its static data through the root `justfile`, and serve it on localhost long enough to verify the Requirements breakdown visually. Keep generated `dashboard/dist/`, `.svtorture/`, PDFs, and annotated text ignored and out of commits.

The final milestone performs review and delivery. Commit coherent milestones with Conventional Commit messages. Launch parallel read-only code, architecture, and documentation reviewer lanes against `origin/main...HEAD`, address every substantive finding, rerun affected tests, and launch one fresh control review. Then push `feat-waivers`, open a pull request against `main`, and report the PR URL and local dashboard URL or exact serve command.

### Concrete Steps

Run all commands from `/home/esynr3z/orca/workspaces/sv-torture/feat-waivers`.

Commit this plan:

    git add docs/exec-plans/waiver-aware-coverage.md
    git commit -m "docs(plan): define waiver-aware coverage work"

Materialize and verify the local corpus using the bundled source-of-truth PDF:

    PDF=/home/esynr3z/.pi/agent/skills/systemverilog/references/IEEE-1800-2023.pdf
    sha256sum "$PDF"
    just annotate-check "$PDF"

The SHA-256 must be `203fbcccbbae90cef401a3acd31835c8cd1507e8f12b2e069046d4f316e317c9`, and `just annotate-check` must report no anchor-index difference. Inspect the generated chapter text and relevant PDF pages before authoring waiver reasons.

After source and code edits, prove complete disposition with a deterministic set comparison. Its final summary must be equivalent to:

    all=16963
    requirement-covered=8696
    effective-waived=8267
    open=0
    adjusted-requirements-coverage=8696/8696

The exact requirement-covered value may move if concurrent source changes are incorporated; the invariant that matters is `open=0` and `coverage denominator == covered + open`.

Regenerate and validate:

    just schemas
    uv run pytest -q tests/test_catalog_models.py tests/test_campaign_metric.py tests/test_bundle.py
    npm --prefix dashboard run typecheck
    npm --prefix dashboard test -- CorpusCoverage.test.tsx TrendsView.test.tsx
    just smoke
    just ci

Build local dashboard data from a fresh compatible campaign path:

    just dashboard-build .svtorture/campaigns/<fresh-campaign-id>/campaign.json
    just dashboard-serve 4173

Opening `http://127.0.0.1:4173` and expanding Requirements coverage must show the Waived column. The Cases breakdown must remain unchanged.

### Validation and Acceptance

Catalog validation must reject unknown waiver anchors, record/file part mismatches, duplicate IDs, duplicate anchors in one waiver, and unsupported source schema versions. It must accept all 58 chapter and annex sidecars after chapters 1 and 2 are added.

For the committed corpus, the union of requirement-covered and waiver anchors must equal all 16,963 committed anchors. Requirements Coverage must be 100% because every eligible anchor is requirement-covered; effective waived anchors are excluded rather than counted as covered. Requirements Density and all Cases operands must equal their values before this feature.

A newly collected campaign must serialize the adjusted aggregate and per-part operands plus effective waived counts. A bundle exported from that campaign must preserve the values. The dashboard Requirements breakdown must render one Waived value per chapter and annex, while the Cases breakdown must not display a Waived column. The collapsed coverage summary remains visually unchanged except for its adjusted percentage and updated explanatory text.

All deterministic checks in `just smoke` must pass. `just ci` must pass when Docker, licenses, and network-dependent upstream resolution are available. No licensed PDF, generated standard text, `.svtorture/` execution state, or `dashboard/dist/` output may appear in Git status.

### Idempotence and Recovery

Annotation commands delete and recreate only the ignored generated annotation directory and can be rerun safely. `just schemas` deterministically rewrites committed generated schemas and should be rerun after any model adjustment. Dashboard build commands rewrite ignored `dashboard/dist/` and can be repeated. If a test exposes a bad waiver grouping, edit only the affected sidecar record and rerun the deterministic set comparison and metadata tests. Do not modify the committed anchor index unless `just annotate-check` proves that the source annotator intentionally changed it; this feature does not require such a change.

Commits should remain small enough to revert independently. Do not amend or force-push after the pull request is opened unless explicitly requested.

### Artifacts and Notes

Baseline corpus evidence before implementation:

    all=16963 req=8696 waiver=8217 overlap=112
    waiver-only=8105 union=16801 open=162
    current=51.264517% eligible=98.171145%
    open by part: chapter 1=129, chapter 2=33

The expected current-corpus result after adding chapters 1 and 2 is 8,267 effective waived anchors and no open anchors. Because every remaining eligible anchor is cited, adjusted Requirements Coverage is expected to be `8,696 / 8,696 = 100%`.

### Interfaces and Dependencies

Use only the existing Python standard library, Pydantic models already used by `src/svtorture/models.py`, and existing React/TypeScript dependencies. Add no package.

The final Python catalog interface must retain `Catalog.corpus_metrics() -> CorpusMetrics`. It may add a frozen `waived_anchors: frozenset[str]` field to `Catalog`. `CorpusPartMetric` may gain `waived: int` with strict nonnegative validation, provided Cases metrics serialize zero and the dashboard only renders it for Requirements. Preserve the invariant `density.denominator == coverage.numerator`.

The waiver loader must consume the committed version-2 JSON sidecars and return a canonical immutable representation or a frozen anchor set. It must not require the IEEE PDF or generated annotated text during ordinary validation, campaign collection, replay, bundling, or dashboard serving.

Plan revision note: 2026-08-05 initial plan created after repository and data-flow analysis. It records the agreed KISS semantics, chapter 1–2 completion requirement, immutable campaign behavior, validation path, review process, and delivery steps.

Plan revision note: 2026-08-05 source milestone completed after deterministic annotation verification and direct inspection of IEEE Std 1800-2023 Clauses 1 and 2. The progress, discoveries, and interim outcome now record complete anchor disposition and the existing cross-record anchor reuse that runtime validation must preserve.

Plan revision note: 2026-08-05 runtime and dashboard milestones completed in commits `82b0dd1` and `a4e7fef`. Progress now records strict waiver loading, adjusted frozen metrics, schema/test updates, the requested UI column, and passing `just smoke`; remaining work is CI, review, local demonstration, and GitHub delivery.

Plan revision note: 2026-08-05 initial parallel review completed. The plan and architecture documentation now describe the implemented runtime path, and the public model enforces the reviewers' Cases-waiver invariant; focused recheck and a fresh control pass remain.

Plan revision note: 2026-08-05 validation and demonstration milestones completed. Full `just ci` passed and produced fresh campaign `20260805T193924Z-fb89a80e0e85e398`; its exported dashboard reports coverage `8696/8696`, density `10771/8696`, 8,267 effective waived anchors, zero Cases waivers, and is served locally on port 4173.

Plan revision note: 2026-08-05 first control review found one source-identity invariant: the part encoded in a waiver ID must match its record part. The model and strict rejection tests now enforce it, and `just smoke` passes after the fix.

Plan revision note: 2026-08-05 final control recheck returned no substantive findings. Review is complete; only commit delivery, push, and pull-request creation remain.

Plan revision note: 2026-08-05 delivery completed. Final `just ci` passed after all review fixes, the dashboard was rebuilt from campaign `20260805T195208Z-241f22980e32aa45`, branch `feat-waivers` was pushed, and pull request 3 was opened against `main`. No planned work remains.
