# SVTORTURE E2E MVP — implementation brief

You are a senior compiler-tooling and test-infrastructure engineer. Build a working end-to-end MVP of a public repository named **sv-torture**.

This is an implementation task, not an architecture exercise. Inspect the two reference repositories, implement the framework, run all checks available in the environment, and leave the target repository usable. Make reasonable engineering decisions autonomously. The product invariants and acceptance criteria below are binding; examples of commands, schemas, and layout are guidance rather than a mandate.

Do not weaken a standards oracle or rewrite a case merely to make a tool pass. Do not push to a remote unless explicitly authorized.

## 1. Inputs and naming

The user provides:

```text
$SV_TESTS_REPO
$VERILATOR_TORTURE_REPO
$SVTORTURE_REPO
```

Treat the first two directories as read-only references. Create or update files only under `$SVTORTURE_REPO`. If the target is nonempty, preserve compatible work.

Record the exact commit and dirty state of each reference checkout; when Git metadata is unavailable, record a deterministic content fingerprint. Inspect the parts relevant to runners/adapters, metadata, process control, result formats, reporting, history, CI, Docker, and commercial-tool integration. Reuse good ideas, but do not fork either architecture blindly.

Use these project names consistently:

- repository: `sv-torture`;
- product, Python package, CLI, internal directories, and lowercase identifiers: `svtorture`;
- uppercase markers and environment prefixes: `SVTORTURE`.

Examples: `src/svtorture/`, `.svtorture/`, `svtorture run`, `SVTORTURE_PASS`, and `SVTORTURE_TOOL_CONFIG`.

## 2. Product vision and MVP scope

SVTORTURE is a standards-driven SystemVerilog conformance framework intended to grow chapter by chapter and paragraph by paragraph through IEEE 1800. It should provide stronger evidence than a feature-tag matrix by preserving the distinction between a normative requirement, a test case, an execution phase, an observation, and a conformance judgment.

The MVP must include:

- a strict machine-readable inventory of the requirements exercised by the corpus;
- 10–12 deterministic cases from multiple chapters and using multiple oracle types;
- tool-neutral cases and a generic evaluator;
- adapters for Slang, Icarus (`iverilog`), and Verilator, plus an optional initial VCS adapter implemented through a generic commercial-tool path;
- parser, elaborator, and simulator profiles only; no synthesis;
- Docker-backed execution for all open-source tools, identical locally and in CI;
- selection of the latest upstream revision or any requested tag, branch, or commit;
- normalized campaign results with sufficient provenance for reproduction;
- a modern static dashboard published on GitHub Pages;
- lightweight PR CI and nightly runs of current open-source upstream revisions;
- a root `justfile` as the normal entry point for repository actions;
- committed pre-commit hooks with fast smoke checks.

The repository is public and Apache-2.0 licensed. Do not commit an IEEE PDF or substantial copied IEEE text. Store precise citations/anchors and concise original summaries.

## 3. Product invariants

Implement these in the data model and evaluator, not only in documentation.

1. **Expectation and observation are separate.** The standard defines the oracle. Tool behavior, another simulator, documentation, and `sv-tests` results may corroborate or prioritize, but never define correctness.
2. **The target phase is explicit.** Successful parsing is not successful elaboration; successful elaboration is not successful simulation. Do not silently substitute another phase.
3. **A negative result needs target evidence.** A nonzero status alone is insufficient. The diagnostic must be tied to the intended source construct or matched through a separately maintained adapter rule when locations are unavailable.
4. **Operational failures never satisfy a negative test.** Timeout, signal, crash, internal error, container failure, launch failure, and unrelated diagnostics are not conforming rejects.
5. **Runtime cases are self-checking.** Every wrong result must call `$fatal`; success emits exactly one `SVTORTURE_PASS:<case-id>` marker after all checks. Do not evaluate arbitrary simulator output as code.
6. **Cases are tool-neutral.** Tool flags, wrapper details, diagnostic normalization, and invocation workarounds belong to adapters. Do not keep per-tool expected behavior or rewritten sources in case metadata.
7. **Known defects remain failures.** A known-issue annotation may add context, but must not turn a nonconforming result green.
8. **Metadata is strict.** Reject unknown fields, bad references, invalid phase/oracle combinations, duplicate IDs, unsafe paths, and incomplete revision applicability.
9. **Cases are minimal and deterministic.** Each has one primary normative requirement; variants change one dimension at a time.
10. **Execution is controlled.** Use argv arrays rather than shell command strings, isolated work directories, bounded output, reliable timeout termination, and no network during case execution.
11. **Tool policy is data-driven.** Public/private, open-source/commercial, CI eligibility, and publication eligibility are declared in tool metadata. Core code must not infer policy from a specific tool name.

## 4. Standards, requirements, and cases

Use **IEEE Std 1800-2023** as the active authority. Every requirement and case records applicability to 1800-2012, 1800-2017, and 1800-2023. Distinguish at least:

```text
applicable
same-rule-different-clause
changed-expectation
not-applicable
not-assessed
```

A requirement is the unit of coverage and scoring. Give it a stable ID and enough metadata to support chapter-by-chapter work: revision, chapter, clause, paragraph/project anchor, concise summary, normativity, testability, coverage state, related clauses, and revision applicability. Free-form tags are useful for search but are not scoring units.

A case should use strict TOML or an equivalently reviewable format and include, at minimum:

- stable ID, title, and concise description;
- primary and related requirement IDs;
- standard revision and revision applicability;
- target phase: `preprocess`, `parse`, `elaborate`, or `simulate`;
- expectation: `accept`, `reject`, or `diagnostic`;
- ordered sources plus top, defines, include directories, runtime arguments, and limits when applicable;
- a machine-readable oracle;
- mandatory versus exploratory evidence;
- provenance: original, adapted, or inspired, including source commit/fingerprint and license notes.

For negative and diagnostic cases, place one unique source marker such as:

```systemverilog
// SVTORTURE_DIAG_ANCHOR:<case-id>
```

Prefer diagnostic source location matching. When a tool omits locations, keep any message/code matcher in the adapter, not in the case.

Icarus must run in an explicit IEEE 1800-2012/SystemVerilog mode. A 2023-authored case may run there only when its metadata says the source and oracle apply unchanged to 2012. Otherwise return `unsupported-revision`, not a normal pass or fail.

Verify standards claims against locally available authoritative material. When that is unavailable, base new variants on already reviewed hypotheses in `verilator-torture`, retain provenance, and do not invent normative wording.

Provide a clearly linked `docs/adding-a-case.md` (or equivalent) and a small template. Cover placement and metadata, requirement mapping, revision/phase/oracle selection, source design, provenance, suite membership, and the `just` validation commands. Quality criteria: one primary requirement, a precise anchor, minimal deterministic stimulus, self-checking runtime behavior, target-specific negative evidence, tool-neutral metadata, and strict validation. A case need not pass every tool; it must produce trustworthy evidence.

## 5. Core architecture

Preserve this conceptual pipeline:

```text
Requirement
  → Case
  → Tool/profile adapter
  → Execution plan
  → Raw observations
  → Generic evaluation
  → Immutable campaign
  → Dashboard dataset
```

Adapters describe capabilities, resolve tool identity, construct typed execution stages, and normalize diagnostics. They do not decide conformance. The generic evaluator compares observations with the case oracle.

Support profiles that make capability boundaries explicit, for example:

- Slang: parse and elaborate; headline profile is elaborate;
- Icarus: elaborate and simulate; headline profile is simulate;
- Verilator: elaborate and simulate; headline profile is simulate;
- the initial VCS adapter: elaborate and simulate through a private local wrapper; it is only one instance of the generic commercial-tool policy.

Tool registration declares capabilities/profiles, distribution model, execution backend, CI eligibility, and publication eligibility. The evaluator, publisher, dashboard, and workflows must not special-case `vcs`; future Xcelium, Questa, Verissimo, and other adapters use the same extension mechanism.

Raw outcomes must distinguish normal exit, signal, timeout, launch failure, and container failure. Normalized results must distinguish at least:

```text
conforming
nonconforming
inconclusive
unsupported-capability
unsupported-revision
not-applicable
skipped-unavailable
harness-error
```

Keep structured reason codes for cases such as unexpected accept/reject, missing or off-target diagnostic, missing pass marker, wrong runtime result, timeout, crash, internal error, missing artifact, and invalid execution plan. Do not collapse the internal model to a boolean.

Classify failures by ownership:

- a compiler/simulator timeout, crash, or internal error is a tool result and is never conforming;
- Docker daemon failure, invalid mounts, corrupt framework output, or inability to launch the configured image is a harness error;
- a reject without evidence at the intended construct is inconclusive or nonconforming, never conforming.

## 6. Toolchains, containers, and reproducibility

All open-source tools must run inside project-controlled Docker images. Local commands and GitHub Actions must call the same repository implementation; workflow YAML must not duplicate resolution or execution logic. Host binaries are not a normal fallback.

Support selections equivalent to:

```text
slang@latest
slang@<tag-or-branch-or-sha>
icarus@latest
icarus@<tag-or-branch-or-sha>
verilator@latest
verilator@<tag-or-branch-or-sha>
```

`latest` means the configured upstream default-branch head at resolution time. Resolve every selection to one full commit SHA before building or running. Reject ambiguous refs. Record the requested ref, resolved SHA, exact tags, nearest tag when useful, tool-reported version, build recipe identity including base-image identity, platform, and final image digest.

Prefer compact images, use non-root execution where practical, and isolate case execution. Network may be used for source resolution and image construction, but not while running a case. Record portable argv and stable path placeholders rather than leaking local absolute paths.

Publish open-source nightly images to GHCR and record immutable digests. Reproduction should first use the recorded digest and be able to rebuild from the exact tool SHA and recipe when necessary.

Commercial tools use the same adapter/result contracts but run through generic user-supplied local wrappers into licensed Docker environments. VCS may be the first example, but no core policy, configuration, test, publisher rule, or UI behavior may depend on its name. Declare policy in tool metadata, for example `distribution = commercial`, `execution = local-wrapper`, `ci = false`, and `publish = false`. Use a generic gitignored private configuration referenced by `SVTORTURE_TOOL_CONFIG` or equivalent. Missing wrapper/license yields `skipped-unavailable`. Commercial images and results never enter GitHub Actions, `gh-pages`, or any public export; enforce this in the exporter.

Provide a clearly linked `docs/adding-a-tool.md` (or equivalent). Cover registration, profiles/capabilities, adapter responsibilities, image or wrapper integration, ref/version/provenance capture, diagnostic normalization, policy, and tests. Explain the distinct open-source and commercial paths. Require tests for command construction, capabilities, failure classification, and diagnostic normalization.

## 7. Campaign data

A campaign is an immutable measurement over one SVTORTURE corpus snapshot, exact toolchain snapshots, a declared selection, and a versioned result schema. Local campaigns may record a dirty checkout; public campaigns may not.

Record enough information to reconstruct it:

- campaign ID and UTC timestamps;
- repository/corpus commit and clean/dirty state;
- requirement, case, and selection manifest hashes;
- case IDs and content hashes;
- exact tool source and image identities;
- profiles, effective language modes, execution policy, platform, and portable commands;
- per-stage outcomes and normalized diagnostics;
- bounded sanitized stdout/stderr excerpts plus full-stream size and hash;
- completeness and metric inputs.

Keep local runs and transient work under gitignored `.svtorture/`. Full logs and generated work products remain local or are uploaded by CI as compressed artifacts with roughly 30 days of retention. Do not store full logs, generated C++, binaries, Docker layers, or work directories on GitHub Pages.

Provide a reproduction command that can replay a selected campaign/tool/case from the recorded repository commit and exact public image digest, clearly reporting environmental differences. Any public dashboard result must remain reproducible after cloning the repository at its recorded SHA even after CI log artifacts expire.

A public campaign is publishable only when it comes from trusted GitHub Actions for this repository, the checkout is clean and matches the recorded SHA, every included tool is explicitly publication-eligible, the data validates, and no private paths, host identity, credentials, wrapper configuration, or license variables are present.

## 8. Headline metric

Expose one broad metric with a precise label such as **Verified support in the covered corpus**. Do not call it unconditional SystemVerilog support.

For each tool headline profile and active revision:

```text
applicable covered normative requirements whose mandatory evidence conforms
-------------------------------------------------------------------------
all applicable covered normative requirements in that profile's scope
```

Rules:

- count requirements, not cases or tags;
- count a requirement once even when it has multiple variants;
- all mandatory cases for that requirement/profile must conform;
- exploratory cases do not affect the score until promoted;
- nonconforming, inconclusive, unsupported revision, missing execution, timeout, crash, and internal error are not verified;
- not-applicable and genuinely non-testable/deferred requirements are excluded;
- a harness error invalidates the campaign/profile metric rather than silently changing it;
- always show numerator, denominator, revision, profile scope, corpus SHA, and completeness.

Show the detailed breakdown behind an expandable control: corpus coverage, execution coverage, conforming, nonconforming, inconclusive, unsupported, and infrastructure state. Make it clear that Slang's score covers elaboration while simulator scores include simulation.

## 9. Dashboard

Build a modern, backend-free React/TypeScript dashboard suitable for local use and GitHub Pages.

Required views:

1. a virtualized requirements matrix as the primary view, with tool/profile columns and expandable supporting cases;
2. a case-level evidence view;
3. history per tool/profile and a comparison view where meaningful;
4. campaign/provenance detail.

Provide useful filters for revision, chapter/clause, phase, expectation, requirement state, tags, tool/profile, result/reason, changed results, disagreement, date/campaign, and full-text search. Preserve filter state in the URL.

Do not communicate status by color alone. Use explicit labels for pass, fail, inconclusive, known fail, unsupported, not run, and harness error.

Every historical point must expose timestamp, exact tool SHA, exact/nearest tags, reported version, image digest, corpus SHA, numerator/denominator, completeness, and campaign ID. Visually mark corpus or denominator changes so they are not mistaken for pure tool regressions.

A result detail should show the requirement reference and summary, exact case source link, oracle, normalized observations, portable command, bounded excerpts/hashes, tool identity, annotations, and a copyable reproduction command.

The public dashboard contains only trusted CI data from publication-eligible open-source tools. The same application may show any commercial or otherwise private campaign when opened against local data.

## 10. GitHub Pages, CI, and nightly collection

Use the `gh-pages` branch for both the built static site and compact append-only public campaign history. Preserve existing campaign data when publishing, deduplicate by stable campaign identity, regenerate indices, and avoid destructive force-push workflows.

The root `justfile` is the repository task interface. README, contributor docs, and GitHub workflows must use `just` rather than duplicate raw `uv`, npm, or Docker command sequences. At minimum provide discoverable `just setup`, `just smoke`, and `just ci` recipes; recipes may delegate to the `svtorture` CLI or focused scripts.

Commit `.pre-commit-config.yaml` and install/prepare it through `just setup`. Hooks run fast deterministic smoke checks—format/lint, strict metadata/schema validation, focused unit tests, and lightweight frontend checks where practical—without network, Docker builds, or full E2E campaigns. Avoid recursive wiring: hooks may call `just smoke` or a dedicated recipe; `just ci` runs the full-tree hook set plus broader checks.

PR CI must be reproducible through `just ci` and include:

- Python formatting/linting, type checking, and tests;
- strict metadata/schema validation;
- deterministic fake-tool integration tests;
- dashboard type checking/tests/build using fixture campaign data;
- a miniature real open-source Docker E2E run through the same path used locally and nightly.

Ordinary conformance failures must not make PR or nightly CI red. Invalid metadata, broken framework logic, corrupt results, harness failures, and infrastructure failures must. Use an `infra-only` default exit policy and optionally provide strict and always-zero policies for interactive or aggregation use.

Do not execute untrusted PR code with repository secrets and do not use `pull_request_target` for test execution.

For the MVP, do not add custom CI caches, `actions/cache`, remote BuildKit cache import/export, or cache-key machinery. Prefer clean deterministic builds and immutable artifacts. Keep build/provenance boundaries ready for later caching without changing campaign identity or result semantics.

Create scheduled and manually dispatchable nightly jobs for latest Slang, Icarus, and Verilator. Use a non-fail-fast matrix. Each job resolves an exact upstream SHA, builds its image from the recorded recipe, records/pushes the immutable digest, runs the corpus, and emits normalized results even when it encounters infrastructure failure. An aggregation job combines available results, marks incomplete campaigns honestly, updates the dashboard, appends compact data to `gh-pages`, and uploads full evidence as expiring CI artifacts.

All commercial adapters are excluded from GitHub workflows by declared policy, not by checking for a specific tool name.

## 11. Seed corpus

Create 10–12 real, short, deterministic, standards-grounded cases across at least eight IEEE chapters.

Use a mixed origin:

- a material subset adapted from `verilator-torture` and made tool-neutral;
- a material subset of original or independently re-authored boundary variants;
- target a roughly balanced mix unless the inspected corpus gives a strong reason to differ;
- `sv-tests` may guide prioritization, especially where broad green results hide weak semantics, but it is not the oracle.

The corpus must exercise:

- at least four self-checking simulation acceptance cases;
- at least two parse/elaboration acceptance cases;
- at least two targeted rejection cases;
- at least one diagnostic case where warning or error is allowed;
- multi-file or compilation-unit behavior;
- preprocessing through include or define;
- explicit top, hierarchy, or generate behavior;
- four-state semantics;
- at least one subtle semantic area such as sizing, signedness, context, scheduling, or copy-in/copy-out.

A genuine mixture of green, red, and disagreement is desirable. Do not manufacture failures and do not add expected-failure shortcuts.

Provide small suites such as `smoke` and `all` or equivalent; the smoke suite should cover positive, negative, runtime, and multi-file paths.

## 12. Validation and false-pass tests

Create a deterministic fake adapter or fake-tool container to exercise the real executor and evaluator. At minimum, tests must prove that none of these become false passes:

- negative case plus timeout, signal/crash, container launch failure, unrelated error, or wrong diagnostic location;
- simulation success status without the pass marker;
- pass marker with nonzero runtime status;
- wrong runtime value ending in `$fatal`;
- unsupported phase or revision;
- missing optional commercial-tool wrapper;
- unknown metadata, path traversal, duplicate IDs, or manifest/hash mismatch;
- public publication containing commercial/private data, including a synthetic commercial tool whose name is not VCS;
- multiple variants incorrectly increasing requirement weight;
- a harness error producing a valid headline score.

Also test command construction and diagnostic normalization for every real adapter. Automated tests must not require any commercial license.

Before finishing, run `just ci` and any additional environment-supported validation through `just` recipes. Coverage must include lockfile installs, pre-commit over the full tree, lint/format/type checks, tests, metadata validation, dashboard install/typecheck/test/build, fake-tool Docker E2E, at least one real open-source smoke run, a local dashboard export, public-export rejection of private data, and one campaign reproduction. Prefer running the complete seed suite on all available open-source images.

When Docker or network access is unavailable, complete the unblocked implementation and distinguish unexecuted checks from passing checks. Never fabricate results.

## 13. Recommended implementation direction

The user has approved this stack:

- Python 3.12, `uv`, Pydantic v2, Typer, pytest, Ruff, and practical static typing;
- React, TypeScript, Vite, TanStack Table/Virtual, and Apache ECharts;
- committed Python and npm lockfiles;
- `just` as the root task runner and pre-commit for fast commit-time checks.

A reasonable repository shape is:

```text
src/svtorture/        core models, adapters, execution, evaluation, campaigns, publishing
standards/            versioned requirement inventory
cases/                one directory per case
schemas/              externally consumable schemas generated or checked against models
toolchains/           upstream registry and public/private tool policy
containers/           open-source and fake-tool images
dashboard/            static application
fixtures/, tests/     unit, integration, and E2E coverage
docs/                 concise architecture, methodology, case/tool authoring, and reproduction docs
.github/workflows/     CI, nightly collection, and Pages publication
```

Exact module boundaries are yours to choose. The CLI must cover validation/doctoring, listing, tool-ref resolution and image preparation, single runs, campaigns, aggregation, reproduction, and dashboard export/serve/publish. Use `svtorture` as the executable name, but make root `just` recipes the documented and CI-facing task interface.

Keep documentation concise and generated where possible. Do not maintain corpus counts manually in several files.

## 14. Explicit non-goals

Do not implement synthesis, complete migration of `verilator-torture`, all 41 chapters, fuzzing, a backend/database, permanent full-log storage, commercial-tool CI, automated upstream issue filing, a full findings workflow, broad DPI/VPI/PLI coverage, macOS/Windows, or non-x86-64 execution.

Design the core so these can be added later without replacing the evaluator or result model.

## 15. Acceptance criteria

The MVP is complete when:

1. `$SVTORTURE_REPO` contains a coherent working implementation, not a design-only skeleton.
2. Strict versioned models exist for requirements, cases, results, and campaigns.
3. The 10–12 case corpus spans at least eight chapters and exercises every required oracle path.
4. Slang, Icarus, Verilator, and the optional initial commercial adapter implement one adapter contract while conformance and commercial/public policy remain generic and name-independent.
5. Open-source execution is Docker-only and identical locally and in CI.
6. Latest and pinned tool refs resolve to exact SHAs with immutable image/build provenance.
7. Revision applicability, especially Icarus 2012 versus the 2023 authority, is explicit.
8. Timeout, crash, unrelated rejection, and missing runtime evidence cannot become conforming results.
9. A normalized campaign builds the local/static dashboard and supports selected-case reproduction.
10. The dashboard provides the requirements matrix, case evidence, filters, headline metric with breakdown, and time/SHA/tag/corpus-aware history.
11. A root `justfile` is the action entry point, `just ci` reproduces PR CI locally, and committed pre-commit hooks run fast smoke checks.
12. PR CI validates the framework without requiring tools to be conforming; nightly workflows collect latest public tools, publish images, append compact history to `gh-pages`, and retain full logs only as expiring artifacts.
13. Public export rejects every commercial/private tool by metadata policy and leaks no host-specific or secret information.
14. The repository contains no IEEE PDF, generated binaries, bulk logs, credentials, or local absolute paths.
15. The repository clearly documents how to add a case and how to add either an open-source or commercial tool, including enforceable quality criteria.
16. MVP CI uses straightforward clean builds without custom cache machinery, while the architecture leaves room for later caching.
17. Critical paths contain no unresolved placeholders.

## 16. Final report

At completion, report:

- the architecture actually implemented and any deliberate deviation from this brief;
- the selected requirements/cases, chapters, and provenance;
- `just` commands for latest runs, pinned runs, optional commercial tools, dashboard use, reproduction, smoke checks, and full local CI-equivalent validation;
- exact public tool revisions/images used in executed checks;
- observed conforming, nonconforming, and inconclusive results without treating tool consensus as the oracle;
- checks that passed and checks blocked by the environment;
- main files created or changed;
- remaining work outside the MVP.

