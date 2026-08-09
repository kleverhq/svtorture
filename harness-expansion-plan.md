# Expand the SVTORTURE harness through nine advanced cases

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current while implementation proceeds. The plan itself is a temporary working artifact and will be removed before final handoff, because the completed SVTORTURE tree must contain no migration notes or references to the source corpus from which the nine fixtures were adapted.

## Purpose / Big Picture

SVTORTURE currently executes small SystemVerilog-only cases with ordered source files, includes, defines, and runtime arguments. After this change, case authors can also express the smallest tool-neutral inputs needed to test SDF annotation, logical libraries and a configuration design root, functional covergroups, DPI C/C++ implementations, and VPI applications. Tool adapters, not case metadata, will own compiler flags, foreign compilation and linking, VPI loading, visibility, timing, and coverage activation.

The completed corpus will contain nine ordinary requirement-linked cases and an explicit advanced suite. A user can validate the complete metadata contract with `just schemas` and `just smoke`, and can run the advanced suite with `uv run svtorture run --tool <tool>@<ref> --suite advanced --exit-policy infra-only`. Every selected profile will either build a valid execution plan, return the existing structural `unsupported-capability` status, return an existing phase or revision disposition, or execute and produce normal conformance evidence. Foreign build failures will be infrastructure-owned rather than falsely scored as SystemVerilog nonconformance.

## Non-Goals

This work will not create a general build graph, arbitrary shell stages, per-tool options in cases, a generic capability-description language, requirement records, tags solely for the new mechanics, native C/C++ rejection oracles, assertion or waveform modes, private simulator APIs, an SDF parser, dashboard features, or a bulk migration loop. It will not retain a scanner, migration report, external repository path, copied harness metadata, or this plan in the final tree. It will not weaken a standards oracle to match current tool behavior.

## Progress

- [x] (2026-08-09 18:27Z) Rebased `feat/harness-expansion` onto `origin/main` at `b6d0733`.
- [x] (2026-08-09 18:27Z) Read the proposal, repository guidance, architecture, methodology, case/tool/reproduction workflows, current models, schemas, adapters, tests, suites, requirements, and the nine source fixtures.
- [x] (2026-08-09 18:27Z) Recorded user decisions: support every capable current adapter; use one generic `unsupported-capability` disposition; map the open-array and callback cases to the exact existing requirements; perform the final corpus scan only as temporary local work; remove all migration artifacts before handoff.
- [x] (2026-08-09 18:53Z) Completed focused probes for adapter commands, minimal fixture reductions, and the smallest contract delta; recorded capability and command evidence below.
- [x] (2026-08-09 18:31Z) Ran the baseline deterministic backend checks: Python formatting, lint, typing, catalog validation, 131 focused pytest tests, and 17 annotator tests passed; frontend typecheck stopped because `dashboard/node_modules` is not installed.
- [x] (2026-08-09 19:02Z) Installed locked frontend dependencies and reran the complete baseline smoke gate: all Python checks, 131 focused tests, 17 annotator tests, dashboard typecheck, and 108 dashboard tests passed.
- [x] (2026-08-09 19:10Z) Completed the plan checkpoint correctness/architecture review and mandatory ponytail KISS/YAGNI review; incorporated the substantive findings and recorded accepted/rejected simplifications below.
- [x] (2026-08-09 19:18Z) Resolved VCS VPI through the documented `-P` PLI-table path: use a standard case-local system task call, an adapter-generated table in `/work`, direct C/C++ linking, and `-debug_access+all`; do not use the compile-setup `-load` hook.
- [x] (2026-08-09 19:25Z) Ran fresh correctness and KISS control reviews; they found two execution-contract blockers and one overbroad validation rule, all resolved below.
- [x] (2026-08-09 19:31Z) Ran the final narrow correctness and mandatory KISS controls; added materialization collision checks and kept phase provenance non-null by excluding `foreign-build` stages by kind.
- [x] (2026-08-09 19:33Z) Committed the reviewed temporary execution plan as `d2145ce`.
- [x] (2026-08-09 19:43Z) Milestone 0 implementation complete pending review: ported both ordered multi-file cases with no metadata changes, generalized the existing source-order test across adapters, and removed the obsolete dead MVP-size audit.
- [x] (2026-08-09 19:43Z) Verified Milestone 0 on Verilator and Icarus; Slang returned the expected phase-limited structural result.
- [x] (2026-08-09 19:47Z) Restored the ignored local VCS runner configuration from the main worktree, fixed its worktree-path translation locally, and verified both new cases conform under VCS X-2025.06.
- [x] (2026-08-09 19:48Z) Completed Milestone 0 correctness, standards, and mandatory KISS/YAGNI reviews; corrected both primary requirement mappings and shrank/strengthened the ordered-source assertion.
- [x] (2026-08-09 19:54Z) Milestone 0 control reviewers reported no substantive findings and the mandatory KISS control returned `Lean already. Ship.`; `just smoke` passed with 134 focused Python tests and 108 dashboard tests.
- [x] (2026-08-09 19:55Z) Committed Milestone 0 as `d3a4d48`.
- [x] (2026-08-09 20:32Z) Milestone 1 implementation complete pending review: declared resources, strict input inventory/hashing, standard library maps, bounded generated work files, covergroup activation, structural capability disposition, replay support, three cases, advanced suite, schemas, docs, and focused tests.
- [x] (2026-08-09 20:32Z) Verified Milestone 1 end to end: all five advanced cases conform under VCS X-2025.06; Verilator conforms except its structural SDF limitation; Icarus conforms on SDF and reports structural configuration/covergroup limits; Slang remains phase-limited.
- [x] (2026-08-10 00:07Z) Completed Milestone 1 correctness, architecture, standards, and mandatory KISS reviews plus repeated controls. Fixed SDF race discrimination, exact covergroup/configuration primaries, bundle/replay library provenance, resource mutation detection, canonical path aliases, and all simplification findings; final controls were clean.
- [x] (2026-08-10 00:07Z) Milestone 1 validation passed: 213 non-Docker tests, `just smoke` with 143 focused Python and 108 dashboard tests, schemas, lint, typing, and the advanced multi-tool campaigns.
- [x] (2026-08-10 00:09Z) Committed Milestone 1 as `a65f018`.
- [x] (2026-08-09 21:20Z) Milestone 2 implementation complete pending review: one `foreign` enum, C/C++ resources, typed foreign-build stages, harness-owned native failures, Verilator generated-make flow, VCS analysis/build split, two DPI cases, schemas/docs, and focused evaluator/adapter/executor/replay tests.
- [x] (2026-08-09 21:20Z) Verified both DPI cases conform under current Verilator and VCS; Icarus reports structural `unsupported-capability` and Slang remains phase-limited.
- [x] (2026-08-10 01:18Z) Ran Milestone 2 correctness, architecture, standards, and mandatory KISS/YAGNI reviews. Fixed legacy v1 advanced-case reading, v6 dashboard loading, VCS mixed-link failure ownership, foreign-source duplication, public version documentation, and v3 foreign-evidence guards; focused checks and fresh Verilator/VCS advanced campaigns pass as expected.
- [x] (2026-08-10 01:38Z) Fresh Milestone 2 control reviews are clean: correctness reported `No substantive findings` and mandatory ponytail reported `Lean already. Ship.` Final `just smoke` passed with 161 focused Python, 17 annotator, and 110 dashboard tests; the final VCS advanced campaign kept both DPI cases conforming.
- [ ] Commit Milestone 2.
- [ ] Milestone 3: extend the foreign path only where VPI needs startup/loading and visibility mechanics; port both VPI cases for every capable adapter.
- [ ] Run focused correctness and architecture reviews plus the mandatory KISS/YAGNI ponytail review for Milestone 3, resolve findings, validate, and commit.
- [ ] Add the explicit advanced suite, concise durable authoring documentation, generated schemas, replay/bundle/publication compatibility, and end-to-end evidence available in this environment.
- [ ] Run the one-time deterministic corpus gap scan outside the committed tree, summarize its findings to the user, then remove the scanner, raw output, proposal, and this plan.
- [ ] Run `just smoke`, `just ci` when Docker and network are available, an advanced Verilator campaign, final multi-lane review, mandatory final ponytail review, and a clean-tree audit; resolve findings and commit the final cleanup.

## Surprises & Discoveries

- Observation: Current Docker and local-wrapper execution exposes the entire read-only case directory, while case identity hashes only ordered HDL sources and recursively declared include directories.
  Evidence: `src/svtorture/executor.py` mounts the case directory as `$CASE`; `src/svtorture/catalog.py::_case_hash` hashes `sources` and `include_dirs`. A consumed SDF, C/C++, map, or header could therefore escape the identity unless it becomes an explicitly validated input.

- Observation: `unsupported-capability` already exists in result schemas and dashboard rendering, but its only permitted reason is `unsupported-phase` and adapters have no pre-plan capability decision.
  Evidence: `src/svtorture/models.py::ResultStatus`, `ReasonCode`, and `NormalizedResult.coherent_judgment`; `src/svtorture/campaign.py::_run_campaign_case` handles only phase/revision before adapter plan construction.

- Observation: Ordered source semantics already exist and all production adapters issue one HDL invocation per case; Slang explicitly requests a single compilation unit.
  Evidence: `CaseDefinition.sources`, `adapters.base.ToolAdapter.source_argv`, and the adapter implementations in `src/svtorture/adapters/`.

- Observation: The current `ExecutionStage` contract distinguishes only `compile` and `run`. A native compiler/linker failure would otherwise look like an HDL rejection before the target phase.
  Evidence: `src/svtorture/models.py::StageKind`, `ExecutionStage`, and `src/svtorture/evaluator.py::evaluate`.

- Observation: Exact-image probes found different real capability boundaries. Icarus executes the SDF case with `-gspecify` but lacks configurations, covergroups, and DPI; Verilator executes configurations, covergroups, DPI, and VPI but does not implement the tested specify/SDF behavior; Slang can parse/elaborate several constructs but has no simulator; VCS supports SDF, configurations, covergroups, and DPI, while a neutral runtime VPI startup plan was not proven.
  Evidence: Verilator and Icarus image probes plus Slang command probes; VCS S-2021.09-1 help/examples and local X-2025.06 plan evidence. Exact commands are summarized under `Artifacts and Notes`.

- Observation: Icarus itself provides `iverilog-vpi`, but the project image omits a C++ compiler. A callback plugin worked when built outside the image; the packed-structure query then crashed, which is execution evidence rather than structural lack of VPI.
  Evidence: `tools/icarus/Dockerfile` and focused `iverilog-vpi`/`vvp` probes.

- Observation: Milestone 1 emitted non-foreign advanced fields under case schema version 1, so rejecting those combinations when adding version 2 would break replay and dashboard reading of the immediately preceding contract.
  Evidence: commit `a65f018` and focused compatibility tests. Readers therefore retain v1 non-foreign advanced cases, while newly authored advanced cases use v2 and the new foreign interface requires it.

- Observation: The main-branch CLI intentionally stopped enforcing the 10–12-case MVP seed, but the now-dead `mvp_audit` function and its direct unit test still rejected the expanded corpus.
  Evidence: commit `b6d0733` removed the only product caller; after adding cases, `test_seed_catalog_meets_mvp` failed at 14 cases. Deleting the dead function/test completes the main-branch intent instead of inventing a filtered seed subset.

- Observation: Exact current-image campaign evidence confirms the existing ordered-source contract is sufficient for the two new cases.
  Evidence: campaign `20260809T193930Z-f3e65ee43f08d16e` reported both new cases conforming under Verilator `645b8cdf240c` and Icarus `72998c54151e`; Slang stopped structurally at `unsupported-phase` before plan construction. Campaign `20260809T194658Z-c1de6eef2204f6f5` reported both conforming under VCS X-2025.06.

- Observation: Ignored runner configuration is worktree-local, and the main worktree's VCS runner translated aliases with unrestricted string replacement. Replacing `/work` after `/case` corrupted absolute paths containing `/workspaces/`.
  Evidence: the first VCS campaign rejected every case with an unopenable source path. A local ignored runner copy now translates only an argument equal to or below the exact `/case` or `/work` prefix; the rerun produced 13 conforming results and one unrelated existing nonconformance.

- Observation: VCS accepted the covergroup syntax but returned zero instance coverage until the standard `option.per_instance = 1` was set in the covergroup definition; neither `-cm line` nor `-lca` enabled the queried instance result.
  Evidence: controlled X-2025.06 probes and the first advanced campaign failed with `coverage=0.000000`; the standard option enabled instance reporting without a VCS-specific adapter flag. Review then strengthened the oracle to two same-time-step events with different values. Both VCS X-2025.06 and Verilator 5.051 record only the final value and return 50%, producing legitimate nonconformance against `SV-2023-19-CLOCKING-EVENT-IMMEDIATE-SAMPLING` rather than a weakened pass.

- Observation: A single standard library-map authority works across adapter strategies. Verilator consumes it directly with `--libmap`; VCS uses the strictly parsed declarations to generate its private setup and per-library `vlogan` stages.
  Evidence: campaigns `20260809T203114Z-42787f77db72f127` and `20260809T203120Z-f696b9e1c7bfa7bb` produced conforming configuration evidence on VCS and Verilator respectively.

## Decision Log

- Decision: Probe the two compilation-unit cases through the existing ordered `sources` contract before adding metadata.
  Rationale: Every adapter already preserves source order in one invocation, so a topology abstraction is unjustified unless a real case disproves that behavior.
  Date/Author: 2026-08-09 / user and coding agent.

- Decision: Implement advanced functionality in every current adapter whose tool/profile can execute it; use normal `unsupported-phase` for profiles below the target phase and one generic `unsupported-capability` result when the phase exists but the tool cannot provide the required feature.
  Rationale: This reports structural limitations without tool nonconformance and avoids a speculative public capability taxonomy.
  Date/Author: 2026-08-09 / user.

- Decision: Keep capability ownership in adapter code and infer the needed operation from narrow case fields rather than adding feature lists to tool manifests.
  Rationale: Tool manifests currently describe stable profile and execution policy. Focused probes confirmed that support depends on adapter mechanics and profile phase, so a generic feature registry would duplicate adapter knowledge and violate the explicit non-goal.
  Date/Author: 2026-08-09 / coding agent.

- Decision: Preserve version-1 metadata for existing cases, suites, tools, tags, and runner configuration; author new advanced cases as case metadata version 2 and require version 2 for the new foreign field, while retaining v1 non-foreign advanced cases for Milestone 1 compatibility. Emit execution/result version 3, campaign version 6, and dashboard-resource version 7 while accepting their immediately preceding versions.
  Rationale: Foreign stage semantics require a machine-readable boundary, but rejecting already-emitted v1 resource/map/covergroup cases would break replay. Narrow version types avoid accidentally widening unrelated metadata contracts.
  Date/Author: 2026-08-10 / coding agent after compatibility testing.

- Decision: Represent only four proven case concepts: exact `resources`, one exact standard `library_map` path, a boolean functional-covergroup request, and `foreign = "dpi" | "vpi"`. Reuse existing `top` as the configuration root and infer C/C++ compilation inputs from resource suffixes.
  Rationale: The standard map file already owns source-to-logical-library membership, so duplicating that mapping in TOML creates two authorities. Every remaining field is consumed by one of the nine cases. Separate language, compiler, flags, outputs, startup symbols, capability lists, and build-graph fields would duplicate information or expose adapter policy.
  Date/Author: 2026-08-09 / coding agent after KISS and correctness review.

- Decision: Preserve the existing whole-case read-only mount and make the catalog reject every case-directory file that is not `case.toml`, an ordered HDL source, inside a declared include tree, an exact resource, or the exact library map.
  Rationale: This makes the mounted tree identical to the declared immutable input inventory and closes the identity hole without adding a staging/copy layer. Every visible file is validated and hashed; generated files remain under `/work`.
  Date/Author: 2026-08-09 / coding agent after reconciling correctness and KISS reviews.

- Decision: Use one small adapter `check_case` operation that raises a typed structural-unsupported exception, and invoke it both before preparation dispositions and inside plan construction.
  Rationale: A plain `build_plan` exception is shorter but cannot deterministically establish precedence in preparation-failure campaigns and verification without fake image/wrapper values. One concrete check avoids a capability registry while keeping producers, verifier, bundle, and replay consistent.
  Date/Author: 2026-08-09 / coding agent after KISS review.

- Decision: Add one explicit `foreign-build` stage role and carry it unchanged through plans, observations, wrapper requests, schemas, evaluation, verification, bundles, and replay. Keep the existing non-null `attempted_through_phase`, set it to the HDL phase reached by that build flow, and exclude foreign stages from evidence by kind. Any timeout, signal, internal error, truncation, nonzero exit, unavailable executable, or missing artifact in that role is infrastructure-owned before generic conformance evaluation.
  Rationale: Stage IDs or argv inspection are brittle, and every failure shape must be prevented from becoming false standards evidence. The stage kind is sufficient; making phase nullable would cause an unnecessary public-schema/dashboard cascade.
  Date/Author: 2026-08-09 / coding agent after correctness and KISS reviews.

- Decision: Apply structural disposition precedence in this order: phase ceiling, revision applicability, adapter feature check, then tool preparation/runner availability.
  Rationale: Structural language/tool limitations are deterministic properties of a case/profile and should agree across normal campaigns, preparation-failure campaigns, verification, bundles, and replay.
  Date/Author: 2026-08-09 / coding agent after correctness review.

- Decision: Make each VPI fixture invoke one standard user-defined system task. Verilator and Icarus register that task through the application's `vlog_startup_routines`; VCS generates a `/work` PLI table mapping the same task to the same calltf routine and links the application directly with `-debug_access+all`.
  Rationale: VCS S-2021.09-1 documents and ships the `-P` system-task mapping path, but does not document automatic `vlog_startup_routines` execution and invokes `-load` registration too early. The system task runs at time zero, then schedules `cbAfterDelay` or queries the packed object, preserving the scored requirements without source rewrites or private APIs.
  Date/Author: 2026-08-09 / coding agent from bundled VCS documentation.

- Decision: Add a minimal `work_files` tuple to `ExecutionPlan`; each entry is a validated safe relative path and bounded UTF-8 text written by the executor before the first stage. Use it only for adapter-generated control files such as VCS `synopsys_sim.setup` and PLI tables.
  Rationale: Adapters construct side-effect-free argv plans and currently have no work-directory path. Generated control text is required, while arbitrary generators, binary payloads, stage-local files, environment maps, and shell commands are not.
  Date/Author: 2026-08-09 / coding agent after control review.

- Decision: Expose ordinary declared resources at their preserved relative paths in `/work` as executor-prepared read-only copies, while keeping the authoritative case inputs read-only under `/case`. Foreign compilers consume the same integrity-checked `/work` copies; library maps continue to use explicit `/case` paths.
  Rationale: Standard source calls such as `$sdf_annotate("test.sdf")` must remain tool-neutral and all stages run from `/work`. One generic copy path is smaller than per-stage cwd or bind-mount contracts, works for Docker and local runners, and prevents foreign tools from bypassing post-copy integrity checks.
  Date/Author: 2026-08-09 / coding agent after control review.

- Decision: For VCS DPI, run `vlogan` first as the SystemVerilog compile observation, then one adapter-generated make target that compiles the shared library and invokes `vcs` for mixed elaboration/linking as the `foreign-build` stage, then run `simv`. Treat every failure in that mixed stage as harness-owned.
  Rationale: The preceding HDL analysis preserves syntax rejection evidence; native compilation and VCS integration are inseparable harness prerequisites for execution and must not become tool nonconformance. The existing runner environment exposes the documented DPI include root without new protocol fields.
  Date/Author: 2026-08-09 / coding agent after control review.

- Decision: Keep the top-level foreign failure status as `harness-error`; distinguish a compiler/linker nonzero exit from SystemVerilog evidence so it cannot become `nonconforming`.
  Rationale: A broken adapter command, missing ABI header, or failed native link is infrastructure evidence until the target simulator phase runs. Existing aggregate logic already invalidates a profile containing a harness error.
  Date/Author: 2026-08-09 / user and coding agent.

- Decision: Use `SV-2023-35-OPEN-ARRAY-CALL-SITE-RANGES` as the open-array primary requirement with `SV-2023-35-DPI-INOUT-COPY-IN-OUT` related, and `SV-2023-38-VPI-CB-AFTER-DELAY` as the callback primary requirement with `SV-2023-36-CALLBACK-SIMULATION-TIME` related.
  Rationale: Each primary names the exact observed behavior; the secondary behavior remains explicit without scoring one case twice.
  Date/Author: 2026-08-09 / user.

- Decision: Use the external fixture checkout only as temporary read-only authoring input. Do not commit provenance, scan tooling, scan output, external paths, archived stdout regexes, public-target metadata, raw tool flags, or migration documents.
  Rationale: The final result is an independently maintained expansion of the SVTORTURE corpus, not an integration with another repository.
  Date/Author: 2026-08-09 / user.

- Decision: At every key milestone, block the commit on focused correctness/architecture review and a separate read-only KISS/YAGNI reviewer explicitly following the ponytail-review skill. Run a fresh control review after fixes.
  Rationale: The user explicitly requires correctness review and repeated challenge against unnecessary abstractions.
  Date/Author: 2026-08-09 / user.

## Outcomes & Retrospective

Milestones 0 and 1 are committed as `d3a4d48` and `a65f018` respectively. Milestone 2 is implemented, reviewed, and end-to-end proven, pending a clean control pass and commit. The catalog fingerprints and validates every declared case input, rejects undeclared files and noncanonical path aliases, and detects any resource-copy mutation before accepting evidence. Standard library maps remain the sole logical-library authority; their validated derivation survives bundles and replay. Bounded generated setup text, covergroup activation, and one generic structural unsupported reason cover the three new cases without raw tool options. SDF and configuration results match the capability matrix. The strengthened immediate-sampling oracle intentionally records current Verilator/VCS nonconformance instead of weakening the requirement.

## Context and Orientation

SVTORTURE connects each case to one existing IEEE 1800 requirement and evaluates observations independently of tool-specific behavior. `src/svtorture/models.py` defines frozen strict public models. `src/svtorture/catalog.py` loads cases, validates safe paths and markers, and calculates content identity. `src/svtorture/adapters/base.py`, `open_source.py`, and `commercial.py` turn a case into an ordered `ExecutionPlan`. A plan is a list of argv-only stages; no shell evaluates case data. `src/svtorture/executor.py` runs those stages with a read-only case input and writable isolated work directory. `src/svtorture/evaluator.py` alone converts observations into conforming, nonconforming, inconclusive, unsupported, unavailable, or harness-owned results.

A case lives under `cases/<case-id>/`. Its `case.toml` currently declares ordered SystemVerilog `sources`, `top`, include directories, defines, runtime arguments, resource limits, one primary requirement, optional related requirements, phase, expectation, and oracle. Runtime cases must print exactly one complete `SVTORTURE_PASS:<case-id>` line after all self-checks and terminate explicitly. Negative cases use one diagnostic anchor, but all nine additions are ordinary positive cases.

A tool profile declares its highest language phase: preprocess, parse, elaborate, or simulate. A profile below a case target returns `unsupported-phase` without execution. A capability limitation differs: the profile reaches the target phase but cannot perform SDF, configurations, coverage, DPI, or VPI. This plan adds one generic capability disposition without creating a registry of named capabilities.

Current production tools are Verilator, Icarus Verilog, Slang, and VCS. Open-source tools execute in project-owned Docker images. VCS uses a user-configured local wrapper and cannot be exercised without its licensed environment, but its plan construction and portable wrapper request can be tested deterministically. Slang has no simulation profile, so runtime advanced cases normally stop at `unsupported-phase`. The fake tool exists only for deterministic framework integration tests.

Case identity must cover every consumed immutable input. The implementation must therefore validate and hash exact resource, foreign-source, header, map, and HDL paths. Adapters may create symlinks or generated files in the writable work directory, but they must never modify declared inputs. Replay reconstructs plans from the recorded repository commit; bundle/catalog projections and source links must preserve enough case identity to reject mismatches without embedding local files.

The nine cases are: prior compilation-unit type visibility across files; macro visibility across files; SDF IOPATH rise annotation; logical-library configuration selection; automatic covergroup sampling; basic DPI C import; DPI open unpacked array bounds and writable inout; VPI callback after delay; and VPI packed-structure size lookup. They will form `suites/advanced.toml`. `suites/all.toml` remains `cases = ["*"]`, and advanced cases will not be added wholesale to the fast smoke suite.

## Open Questions

No design question remains for VCS runtime VPI. Bundled VCS S-2021.09-1 documentation and shipped examples establish direct C/C++ linking, `-P` PLI-table system-task mapping, and `-debug_access+all` packed-object visibility. The fixtures therefore call one standard VPI-defined system task at time zero; the callback calltf schedules `cbAfterDelay`, while the object calltf performs `vpi_handle_by_name` and `vpiSize`. Icarus VPI support requires adding the native compiler already expected by `iverilog-vpi` to its controlled image, then executing both VPI cases and recording any crash as ordinary runtime evidence rather than structural unsupported. No source retains a Verilator-only visibility pragma.

The probe and reviews fixed the minimal metadata shape: exact opaque `resources`; one optional exact `library_map` path whose standard contents are the sole logical-library authority; `covergroups = true`; and `foreign = "dpi" | "vpi"`. Existing `top` names either the normal design top or, when `library_map` is present, the configuration root. C/C++ compilation inputs are the `.c`, `.cc`, `.cpp`, and `.cxx` resources; other resource suffixes remain opaque, and headers are resources. No field carries compiler flags, include paths, link libraries, output names, startup symbols, or capabilities.

## Plan of Work

Milestone 0 ports the two multi-file fixtures directly into normal case directories. The sources will be reduced to the declarations and observation needed by the existing requirements. No new metadata is allowed in this milestone. The existing ordered-source adapter test will be parameterized rather than duplicated. Acceptance requires real compile/run evidence for Verilator and Icarus, Slang parse/elaboration evidence with its documented `--single-unit`, and a statically validated VCS one-invocation plan plus licensed execution when the configured runner is available. A focused review and ponytail review will challenge any topology field or special flag before the milestone commit.

Milestone 1 first closes the identity hole with a narrow declaration of case-local non-HDL resources. `CaseDefinition` and `LoadedCase` will expose exact validated paths; `catalog.py` will reject missing, unsafe, duplicate, symlinked, directory-valued, cross-role, and undeclared case-directory files and hash every declared byte. Existing whole-case mounting remains read-only because validation makes that tree exactly the declared inventory. The executor copies declared resources into `/work` at the same relative paths with read-only permissions for standard relative file access. The same milestone adds one exact standard library-map path, reuses `top` as the configuration root, adds one functional-covergroup request, and lets plans carry only bounded generated control text under safe `/work` paths. Adapters translate neutral semantics into argv or generated VCS setup files. Before preparation and plan construction, a small adapter check either accepts the case/profile or raises the one generic structural capability disposition. Campaign collection, preparation-failure campaigns, result verification, replay, and bundles must agree on that decision. The SDF case must observe an annotated delay; the configuration case must prove the selected design at runtime; the coverage case must call standard covergroup methods and prove automatic sampling.

Milestone 2 adds exact C/C++ and header resources plus one foreign interface mode sufficient for DPI. It reuses the same validation and hashing path as resources. Adapter plans own compiler choice, generated headers, standard ABI headers, link inputs, and output artifacts. Verilator separates translation from its generated make build; VCS first analyzes HDL with `vlogan`, then treats its documented mixed elaboration/native-link driver as the foreign-build stage; unsupported Icarus stops structurally. Every foreign-build outcome is classified before standards evaluation. The basic C case proves import/call/link operation; the C++ open-array case proves actual bounds and a writable inout element through `svOpenArrayHandle`. No case may include a generated model header or command fragment.

Milestone 3 reuses Milestone 2 and adds only VPI-specific registration/loading and visibility behavior. Each case calls one standard user-defined system task at time zero. The callback task schedules and proves a timed `cbAfterDelay`; the packed-structure task proves name lookup and `vpiSize` without a private source pragma. Verilator and Icarus use the application's startup array to register the task. VCS uses an adapter-generated `/work` PLI table mapping the same task to its calltf routine and enables documented debug/VPI visibility. Capable simulators execute equivalent plans; genuinely incapable profiles return structural unsupported results.

The final milestone adds `suites/advanced.toml`, updates concise durable authoring guidance in `docs/adding-a-case.md` and tool guidance only where necessary, regenerates schemas with `just schemas`, and verifies campaign, replay, bundle, publication, and dashboard compatibility. A temporary local scan will count remaining external-corpus patterns and representative paths for the requested categories. Its summary will be delivered to the user, but its code/output and all migration artifacts will be deleted before the final commit.

### Concrete Steps

Work from `/home/esynr3z/orca/workspaces/sv-torture/feat-harness-expansion`.

After each model or schema change, run:

    uv run pytest -q tests/test_catalog_models.py tests/test_adapters.py tests/test_campaign_metric.py tests/test_evaluator.py tests/test_reproduce.py tests/test_bundle.py
    just schemas
    uv run svtorture validate

After each case milestone, run:

    uv run svtorture validate
    uv run pytest -q -m "not docker" tests/test_catalog_models.py tests/test_adapters.py tests/test_campaign_metric.py tests/test_evaluator.py

Before every key commit, inspect:

    git status --short
    git diff --check
    git diff --stat

Then launch read-only focused correctness/architecture reviewers and a separate read-only KISS/YAGNI reviewer using the ponytail-review format. Resolve substantive findings, rerun focused tests, and run one fresh control pass. Commit with a Conventional Commit message describing the behavior delivered.

At final validation, run:

    just smoke
    just ci
    uv run svtorture run --tool verilator@latest --tool icarus@latest --tool slang@latest --suite advanced --exit-policy infra-only
    uv run svtorture doctor
    uv run svtorture run --tool vcs@local --suite advanced --exit-policy infra-only

The VCS command is conditional on `doctor` reporting its ignored local runner ready. `just ci` and current-upstream open-source campaigns require Docker and network access. If an environmental prerequisite is unavailable, record the exact command and failure, run all deterministic checks and available-tool campaigns, and do not claim unavailable evidence.

Before handoff, remove temporary files and verify that no external corpus path or migration artifact remains:

    rm -f harnses-proposal.md harness-expansion-plan.md
    git status --short

Inspect the final tracked diff and search for migration-only identifiers while preserving legitimate references to the supported Verilator tool. The expected final tree contains harness implementation, nine ordinary cases, the advanced suite, focused tests, generated schemas, and concise authoring documentation only.

### Validation and Acceptance

Metadata acceptance is demonstrated when `uv run svtorture validate` reports the enlarged case count and no schema mismatch. Ordinary legacy cases must continue loading without any new fields. Mutating one byte in a declared SDF, map, C, C++, or header input in a test fixture must change the case content hash; unsafe and missing inputs must fail catalog loading.

Structural acceptance is demonstrated when every applicable, revision-compatible, prepared profile that reaches the target phase either builds a typed plan containing only argv arrays and declared inputs or returns `unsupported-capability` with no observations. Phase-limited profiles continue returning `unsupported-phase`; revision, applicability, preparation, and runner-unavailable states retain their existing dispositions. Replay and campaign verification must recompute the same precedence.

Behavioral acceptance for the advanced suite is demonstrated by valid plans for all nine cases and end-to-end Verilator, Icarus, and Slang campaign evidence, plus VCS when its licensed runner is configured, with no invalid plan, missing input, accidental host dependency, or unclassified foreign build failure. Conforming, nonconforming, inconclusive, phase-limited, and genuinely unsupported tool judgments are legitimate; infrastructure ambiguity is not.

Regression acceptance is demonstrated by `just smoke`, schema generation with no manual JSON edits, deterministic unit tests, bundle/reproduction compatibility, and `just ci` when its environmental prerequisites are available.

### Idempotence and Recovery

Schema generation, validation, unit tests, and suite runs are repeatable. Case inputs are never edited during execution. Generated artifacts stay under ignored `.svtorture/` work directories and can be deleted safely between runs. If an adapter probe fails, record the evidence in `Surprises & Discoveries`, leave the tool structurally unsupported for that exact feature only when the tool truly lacks it, and continue without weakening the case.

Each milestone ends in a reviewed commit. If a later milestone fails, reset only the uncommitted work to the last milestone commit; do not rewrite reviewed commits unless a review fix logically belongs there. Never remove or reset the external fixture checkout or licensed runner infrastructure.

### Artifacts and Notes

The branch was rebased successfully:

    Successfully rebased and updated refs/heads/feat/harness-expansion.
    b6d0733 (HEAD, origin/main, main) fix(cli): allow catalogs beyond MVP seed

Baseline deterministic evidence before implementation:

    validated cases=12
    131 passed in 86.97s
    annotator suites: 10 passed, 6 passed, 1 passed
    frontend typecheck: tsc not found because locked npm dependencies were not installed

Focused adapter evidence selected for implementation:

    multi-file: one ordered invocation on Verilator, Icarus, Slang, and VCS
    SDF: Icarus -gspecify and VCS supported; Verilator unsupported
    config: Verilator --libmap, Slang --libmap, VCS logical-library flow; Icarus unsupported
    covergroup: Verilator --coverage-user and VCS supported; Icarus unsupported
    DPI: Verilator and VCS supported; Icarus unsupported
    VPI: Verilator --vpi; Icarus iverilog-vpi after image toolchain fix; VCS -P table and -debug_access+all

The current identity gap is the central contract issue:

    mounted input: complete cases/<id> directory
    hashed input: case.toml + sources + recursive include_dirs
    required state: every adapter-consumed file is declared, validated, immutable, and hashed

### Interfaces and Dependencies

Use only Python 3.12 standard-library facilities and the repository's existing Pydantic models. Add no dependency. Public case fields remain optional with empty defaults so every existing HDL-only case remains byte-for-byte valid.

The final interface must include one adapter-owned preflight operation that receives a loaded case and profile and either permits plan construction or produces the existing generic unsupported disposition. It must not expose a configurable capability registry.

In `src/svtorture/models.py`, add one `ForeignInterface` enum with `dpi` and `vpi`, and optional fields on `CaseDefinition` equivalent to `resources: tuple[str, ...] = ()`, `library_map: str | None = None`, `covergroups: bool = False`, and `foreign: ForeignInterface | None = None`. Existing `top` is the configuration root whenever `library_map` is present.

The input contract must validate exact safe relative regular files, reject symlinks, cross-role duplicates, and any undeclared case-directory file, accept opaque resource suffixes, infer foreign compilation inputs only from the bounded C/C++ suffix set, and require at least one such resource when `foreign` is set. Only `foreign` requires a positive simulation oracle because intentional native rejection is out of scope; `covergroups` requires a simulation runtime oracle; resources and library maps receive no speculative phase restriction. The standard library map is validated as an exact input and as bounded library declarations needed by adapters; library identifiers must use the existing identifier grammar before interpolation into generated setup files. Functional coverage is a boolean request, not a mode list.

In `src/svtorture/models.py`, add one tiny generated work-file model containing a safe relative path and bounded nonempty text, and `ExecutionPlan.work_files` with an empty default. `validate_plan_for_profile` must reject duplicate, exact, and ancestor/descendant collisions among copied resource paths, generated work files, and every stage `expected_artifact` before materialization. `executor.py` writes the generated files and read-only resource copies before running stages, without invoking a shell. The wrapper request needs no new payload because the host work mount already contains the materialized files.

The execution contract must distinguish a foreign compiler/linker failure from standards evidence. Add the smallest explicit stage role and reason necessary, retain the existing non-null phase field, exclude foreign stages from evidence by kind, and classify every foreign-stage outcome before generic operational and standards evaluation. Preserve the rule that only target-reaching SystemVerilog observations establish conformance.

No external libraries, network services, or host compilers may become runtime dependencies for open-source adapters; required toolchains belong in their controlled images. VCS continues through the existing local-wrapper request contract.

Plan revision note (2026-08-09): Created after rebasing onto `origin/main`. Incorporated repository research, the full proposal, and all user decisions through the clarification that the external corpus scan is one-time work and leaves no committed artifact.

Plan revision note (2026-08-09 18:53Z): Added completed adapter/fixture/contract probe evidence, baseline validation results, the four-field minimal case contract, established schema-version policy, and the observed per-tool support matrix. These discoveries replace pre-probe alternatives and make Milestone 1 implementable without external context.

Plan revision note (2026-08-09 19:10Z): Incorporated the first correctness/architecture and mandatory ponytail reviews. Replaced duplicated source-library metadata with one standard map authority, removed separate foreign-source declarations, retained the native whole-case mount while closing it through strict undeclared-file rejection, specified full foreign-stage provenance/failure ownership and disposition precedence, strengthened real multi-tool validation, and made VCS VPI a blocking research item rather than an unsupported shortcut.

Plan revision note (2026-08-09 19:18Z): Resolved that blocker from bundled VCS S-2021.09-1 documentation. The plan now uses a portable case-local VPI system task, startup-array registration on Verilator/Icarus, an adapter-generated VCS `-P` table, direct VCS linking, and documented debug visibility; the unsuitable compile-setup `-load` path is explicitly excluded.

Plan revision note (2026-08-09 19:25Z): Incorporated the fresh control reviews. Added the missing minimal generated-work-file contract, defined generic read-only resource materialization for relative runtime access, separated VCS HDL analysis from its harness-owned mixed foreign build, and narrowed validation from all advanced mechanics to only the selected foreign and covergroup requirements.

Plan revision note (2026-08-09 19:31Z): Incorporated the final narrow controls. Added exact/prefix collision validation across all materialized work paths and kept phase provenance non-null, using `foreign-build` kind—not nullable phase—to exclude native prerequisites from conformance evidence.

Plan revision note (2026-08-09 19:43Z): Recorded Milestone 0 implementation, exact open-source campaign evidence, the initially unavailable VCS runner, and removal of the dead MVP-size audit exposed by expanding beyond the former seed corpus.

Plan revision note (2026-08-09 19:48Z): Recorded the restored ignored VCS runner, its local exact-prefix translation fix, successful X-2025.06 campaign, and Milestone 0 review fixes: exact primary mappings plus a shorter complete actual/portable source-order assertion.

Plan revision note (2026-08-09 19:54Z): Recorded clean Milestone 0 correctness, standards, and mandatory KISS control passes plus the post-fix smoke evidence.

Plan revision note (2026-08-09 20:32Z): Recorded the Milestone 1 contract/case implementation, generated schema and focused test evidence, VCS covergroup discovery, cross-adapter library-map strategy, and initial advanced campaign outcomes.

Plan revision note (2026-08-10 00:07Z): Recorded all Milestone 1 review/control findings and fixes, final validation counts, bundle/replay provenance checks, immutable-resource verification, canonical path hardening, and the deliberate Verilator/VCS nonconformance exposed by the strengthened same-time-step covergroup oracle.

Plan revision note (2026-08-09 21:20Z): Recorded Milestone 2 implementation and campaigns. Verilator now translates HDL and generates a main before a separate make-based foreign build; VCS analyzes HDL before its mixed elaboration/native build. Both DPI cases conform on both capable simulators, while structural limitations remain observation-free.

Plan revision note (2026-08-10 01:38Z): Recorded Milestone 2 compatibility and control-review fixes. V1 non-foreign advanced evidence remains readable, dashboard readers accept v6/v7, foreign evidence requires v3, and one VCS foreign-build recipe owns native compilation plus VCS linking. Final correctness and KISS controls are clean.
