# Make tool phases cumulative and expose honest phase evidence

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Note that this document must be maintained in accordance with the `exec-plan` skill.

## Purpose / Big Picture

After this change, SVTORTURE users will see the phase pipeline as they naturally expect it: a simulator can assess simulation and every prerequisite phase, an elaborator can assess elaboration and its prerequisites, and a parser can assess parsing and preprocessing. Icarus and Verilator will therefore execute the Chapter 5 whitespace rejection case instead of reporting that parsing is unsupported. The evidence will remain honest: a result records whether the requested oracle was observed in a command that stopped at the requested phase (`direct`) or in a command that could continue through a later phase (`cumulative`).

The Overview tool rows will replace the opaque numerator/denominator score with three colored requirement counts, `PASS`, `FAIL`, and `UNCLEAR`, followed by text such as `92% of IEEE 1800-2012 applicable requirements`. A fresh local campaign and the Case evidence view will demonstrate that the Chapter 5 parse rejection passes for Slang, Icarus, and Verilator, while Icarus records that evidence cumulatively through its elaboration-capable compile command.

This is an intentional clean schema break. The project has not been deployed, so no compatibility parser, legacy aliases, migration shim, or old campaign fixture will remain. All ignored local campaigns and the generated dashboard dataset will be deleted before fresh version-2 evidence is collected.

## Non-Goals

This work does not add cases or weaken any standards oracle. It does not infer a runtime result from compilation, treat unrelated later-phase errors as earlier-phase failures, preserve old campaign JSON, or publish licensed VCS evidence. It does not add a browser automation dependency; Chrome DevTools Protocol scripts under `/tmp` may be used for visual validation only.

## Progress

- [x] (2026-07-21 20:11Z) Analyzed the current exact-membership phase model, adapters, evaluator, metrics, schemas, dashboard, and current campaign behavior.
- [x] (2026-07-21 20:11Z) Chose a clean version-2 cumulative capability and explicit evidence-attribution design with no backward compatibility.
- [x] (2026-07-21 20:13Z) Committed this active ExecPlan and removed all ignored version-1 campaigns, transient work, and generated dashboard evidence.
- [x] (2026-07-21 23:25Z) Implemented the version-2 tool, execution, observation, result, and campaign contracts and regenerated committed schemas.
- [x] (2026-07-21 23:31Z) Implemented cumulative phase execution and safe evaluator inference across open-source, commercial, and fake adapters.
- [x] (2026-07-21 23:35Z) Updated metric scope, requirement-level PASS/FAIL/UNCLEAR presentation, evidence provenance, documentation, and Python/frontend tests.
- [ ] Collect a fresh three-tool full campaign, build the dashboard, and validate desktop/mobile behavior and Chapter 5 evidence in Chrome.
- [ ] Run focused and independent control reviews, fix every substantive finding, run `just ci`, finalize this plan, and remove the completed plan from the repository.

## Surprises & Discoveries

- Observation: The current `profile.phases` field represents independently assessable command boundaries rather than prerequisite capability, but the UI calls missing membership an unsupported tool capability.
  Evidence: `tools/tools.toml` gives Icarus and Verilator simulator profiles only `elaborate` and `simulate`, while `src/svtorture/campaign.py::run_campaign()` synthesizes `unsupported-phase` before running a parse case.

- Observation: Both exact current Icarus and Verilator images reject `4' hA` with a diagnostic on the case anchor.
  Evidence: Direct local runs returned Icarus exit 2 and Verilator exit 1 with syntax errors at `top.sv:2`; therefore the Chapter 5 rejection oracle can be established cumulatively.

- Observation: A later successful command proves that its prerequisites succeeded, but a later failure does not identify the failing phase.
  Evidence: `ExecutionStage.phase` currently labels an integrated compile as elaboration even if it exits during tokenization. Diagnostic source anchoring identifies the tested construct but not a standalone parser mode.

- Observation: The current corpus has zero preprocess targets, one parse target, four elaborate targets, and seven simulate targets.
  Evidence: The cumulative headline denominators should become 5 for Slang elaborator and 12 each for Icarus and Verilator simulators.

- Observation: The pinned Icarus image needs an explicit stdout destination for bounded preprocessing.
  Evidence: `iverilog -g2012 -E` attempted to create read-only `a.out`; `iverilog -g2012 -E -o -` emitted the preprocessed source to stdout successfully. Verilator `-E` emitted source directly.

## Decision Log

- Decision: Replace `ToolProfile.phases` with `phase_ceiling` and `direct_phases` rather than retaining two competing representations.
  Rationale: `phase_ceiling` derives cumulative support unambiguously, while `direct_phases` preserves whether an adapter has an independently bounded command. Removing `phases` satisfies the explicit no-compatibility requirement and prevents contradictory metadata.
  Date/Author: 2026-07-21 / coding agent

- Decision: Replace `ExecutionStage.phase` and `StageObservation.phase` with `attempted_through_phase`, add `ExecutionPlan.target_phase`, and add `NormalizedResult.target_phase` plus `evidence_mode` (`direct`, `cumulative`, or `not-observed`).
  Rationale: A unified compile command can attempt elaboration while establishing a parse oracle. The model must record both facts without relabeling the command as parser-only.
  Date/Author: 2026-07-21 / coding agent

- Decision: A successful later-phase command proves earlier acceptance; a targeted anchored rejection or diagnostic may prove an earlier negative oracle; an unrelated later failure is `inconclusive/target-phase-unproven`.
  Rationale: This makes capability cumulative without converting ambiguous failures into false tool nonconformance. Simulation markers remain simulation-only.
  Date/Author: 2026-07-21 / coding agent

- Decision: Break only the affected contracts to version 2: tool registry, execution plan/wrapper request, normalized result, and campaign. Keep case, suite, tag, standards, private-config, and diagnostic-rule versions unchanged where their structures do not change.
  Rationale: There is no backward compatibility, but unrelated metadata should not churn merely because the old code shared one version type.
  Date/Author: 2026-07-21 / coding agent

- Decision: The Overview triple uses requirement-level `MetricBreakdown.conforming`, `nonconforming`, and `inconclusive`, not raw case-result counts.
  Rationale: The headline metric weights each normative requirement once and requires every mandatory variant to conform. The visual labels must describe that same denominator.
  Date/Author: 2026-07-21 / coding agent

## Outcomes & Retrospective

Implementation has not started. At completion this section must record the new schema versions, fresh campaign IDs and exact metrics, visual validation, review results, and any deviation from the planned inference rules.

## Context and Orientation

A case under `cases/<case-id>/case.toml` declares `target_phase`, `expectation`, and an oracle. The four ordered phases are `preprocess`, `parse`, `elaborate`, and `simulate`. A tool profile in `tools/tools.toml` currently lists phases independently. `src/svtorture/campaign.py` checks exact membership and otherwise creates a synthetic Unsupported result. An adapter under `src/svtorture/adapters/` constructs an `ExecutionPlan`; `src/svtorture/executor.py` executes its stages and copies each stage phase into a `StageObservation`; `src/svtorture/evaluator.py` searches for an observation whose phase exactly equals the case target and applies the case oracle.

The new term `phase ceiling` means the latest pipeline boundary a profile can attempt. Every earlier phase is cumulatively supported. `Direct evidence` means the command is bounded at the case target, such as `slang --parse-only`. `Cumulative evidence` means a later-capable command establishes the earlier oracle, such as Icarus compilation rejecting an anchored lexical error while attempting elaboration. `Not observed` applies to synthetic results such as unavailable tools or inapplicable revisions.

`src/svtorture/metric.py` groups mandatory cases by requirement. A requirement contributes to the numerator only when every mandatory case is conforming. Nonconforming and inconclusive requirements remain in the denominator. `dashboard/src/HeadlineMetrics.tsx` renders these metric points. The frontend dataset is generated by `src/svtorture/publish.py`; TypeScript mirrors of public JSON live in `dashboard/src/types.ts`.

Public JSON schemas are generated by `just schemas` through `src/svtorture/catalog.py::write_json_schema`. Tests use model constructors in `tests/helpers.py`, so a clean schema break requires updating fixtures rather than accepting old field names. Ignored evidence lives in `.svtorture/campaigns/` and `dashboard/dist/data/dataset.json` and may be deleted because the user explicitly rejected compatibility and the repository has never been deployed.

## Open Questions

There are no user decisions outstanding. During implementation, verify the exact Icarus and Verilator preprocessing argv before declaring preprocessing direct. If either command does not provide a stable bounded preprocessing result in the pinned image, omit that phase from `direct_phases`; cumulative support still follows from the ceiling. VCS remains test-only through its private-wrapper plan because licensed execution is unavailable.

## Plan of Work

### Milestone 1: Establish the clean version-2 contracts

Split the shared schema-version aliases in `src/svtorture/models.py` so unchanged case and repository metadata remain on their current versions while `ToolRegistry`, `ExecutionPlan`, `NormalizedResult`, and `Campaign` require version 2. Add a central ordered phase helper and `ToolProfile.supports(phase)`. Replace the old profile phase list with a required ceiling and direct phase list, validating profile-name ceilings, canonical direct-phase ordering, uniqueness, and containment at or below the ceiling.

Add the new execution and provenance names to the strict models. Add `EvidenceMode` and `ReasonCode.TARGET_PHASE_UNPROVEN`, and strengthen result coherence so executable judgments carry observations and direct or cumulative attribution while synthetic judgments are `not-observed`. Update `tools/tools.toml`, `tools/private.example.toml` only if its public tool contract requires it, test helpers, model tests, and schema generation. Delete the old ignored campaigns and dashboard dataset rather than teaching any loader to accept version 1.

This milestone is accepted when `load_catalog()` accepts only the new tool registry, the old `phases` key is rejected, constructors use version 2 for affected models, `just schemas` produces no legacy profile phase field, and focused model/schema tests pass.

### Milestone 2: Execute cumulative targets and judge them safely

Update `_stage()` and all adapters so a stage records the furthest phase its command can attempt. Slang and Fake continue to provide exact direct stages. Icarus and Verilator should use a verified preprocessing-only command for preprocess targets, their existing static compile/lint command through elaboration for parse and elaborate targets, and compile plus run for simulation. VCS should record integrated compilation through elaboration for earlier static targets and runtime separately.

Update `ExecutionPlan` validation to require a stage that can cover its target. Update wrapper request JSON to version 2 and use the new names. In `src/svtorture/evaluator.py`, select the nearest observation whose attempted-through phase reaches the target. Preserve all operational-failure and bounded-output protections. Apply direct semantics unchanged. For cumulative semantics, accept a successful later command for an earlier acceptance oracle, accept a targeted anchored rejection or diagnostic, reject a later success for a required rejection, and classify unrelated later failures as `inconclusive/target-phase-unproven`. Never use compile evidence for a simulation oracle.

Change both campaign phase gates and `compute_metric()` to use `profile.supports()`. Update preparation-failure generation, campaign verification, selection hashing as needed, reproduction, aggregation, and tests. This milestone is accepted when deterministic unit tests prove each inference rule and Docker execution shows the Chapter 5 case as conforming for exact current Icarus and Verilator images with `evidence_mode=cumulative` and `attempted_through_phase=elaborate`.

### Milestone 3: Present requirement outcomes and provenance clearly

Update `dashboard/src/types.ts` for version-2 profiles, results, and observations. In `EvidenceView.tsx`, show target phase, attempted-through phase, and evidence mode in plain language. Keep exact statuses and diagnostic output unchanged.

Replace the current numerator/denominator block in `HeadlineMetrics.tsx` with three adjacent requirement counts. The conforming value is green with label `PASS`, nonconforming is red with label `FAIL`, and inconclusive is yellow with label `UNCLEAR`. The adjacent coverage sentence must read, for example, `92% of IEEE 1800-2012 applicable requirements`. Invalid metrics remain explicitly unavailable rather than green. Keep every tool as one full-width row and preserve readable wrapping on mobile.

Update dashboard fixtures and tests to assert the values, labels, semantic color classes, wording, and cumulative evidence details. Update `docs/methodology.md`, `docs/architecture.md`, `docs/adding-a-tool.md`, `docs/reproduction.md`, and dashboard documentation so they define ceiling, direct evidence, cumulative evidence, safe inference, metric treatment of inconclusive requirements, and the clean version-2 contract without mentioning a supported legacy format.

This milestone is accepted when TypeScript checks and frontend tests pass and Chrome screenshots at wide, 621 px, and 390 px widths show the requested count layout without page overflow.

### Milestone 4: Collect evidence, audit, and hand off

Run a fresh `just latest-all all` after the implementation commit so its campaign records a clean repository commit and only version-2 evidence. Build the local dashboard from that campaign. Inspect the campaign JSON to prove that all three tools conform for `ch05-base-format-whitespace-rejected`, that Slang is direct while Icarus and Verilator are cumulative, and that headline denominators are 5, 12, and 12. Confirm the Overview shows expected PASS/FAIL/UNCLEAR counts and applicable-requirement percentages.

Run focused parallel reviews for model/evaluator correctness, schemas and replay integrity, dashboard semantics/accessibility, and documentation. Fix all findings, then run a fresh independent control review. Run `just ci`, ensure `git diff --check` and a clean status, finalize this plan’s progress and retrospective, commit the completion record, and remove this completed plan in a final cleanup commit as required by repository policy.

### Concrete Steps

Run all commands from `/home/esynr3z/projects/sv-torture`.

First preserve the plan and remove ignored legacy evidence:

    git add PHASE_MODEL_EXECPLAN.md
    git commit -m "docs(plan): adopt cumulative phase model"
    rm -rf .svtorture/campaigns .svtorture/work
    rm -f dashboard/dist/data/dataset.json

During contract and runtime work, use focused tests repeatedly:

    uv run pytest tests/test_catalog_models.py tests/test_adapters.py tests/test_evaluator.py tests/test_campaign_metric.py tests/test_publish.py tests/test_reproduce.py
    just schemas
    just metadata

During frontend work:

    npm --prefix dashboard run typecheck
    npm --prefix dashboard test
    npm --prefix dashboard run build

After an implementation commit and a clean status, collect fresh evidence:

    just latest-all all
    find .svtorture/campaigns -name campaign.json -print
    just dashboard-build ".svtorture/campaigns/<new-id>/campaign.json"
    just dashboard-serve

Final validation:

    just ci
    git diff --check
    git status --short --branch

Expected evidence includes a version-2 result conceptually equivalent to:

    case_id: ch05-base-format-whitespace-rejected
    tool_id: icarus
    target_phase: parse
    evidence_mode: cumulative
    observation.attempted_through_phase: elaborate
    status: conforming

### Validation and Acceptance

The clean schema break is proven when old tool TOML containing `phases` and old campaign JSON with schema version 1 are rejected by strict model tests, while no compatibility branch or alias remains in production code. Generated schema snapshots must expose only `phase_ceiling`, `direct_phases`, `attempted_through_phase`, `target_phase`, and `evidence_mode` where applicable.

Cumulative evaluation is proven by tests for successful later-phase acceptance, targeted cumulative rejection, unrelated later failure, direct evidence, and simulation isolation. Real Docker evidence must show the Chapter 5 case passing for Slang, Icarus, and Verilator. The metric must keep inconclusive requirements in the denominator but outside PASS and FAIL, exposing them as UNCLEAR.

The UI is accepted when each tool row shows three normal-size colored counts with labels below and the coverage sentence uses `applicable requirements`; no graphical progress bar or old ratio remains. Evidence details must state whether evidence is direct or cumulative. Desktop and mobile views must have no page-level horizontal overflow or runtime/network errors.

### Idempotence and Recovery

Schema generation, tests, frontend builds, and campaign collection are safe to rerun. Removing `.svtorture/campaigns`, `.svtorture/work`, and the generated dashboard dataset is intentionally destructive and authorized by the user; these paths are ignored and contain only reproducible local evidence. Docker images may remain cached. If a campaign run fails, delete only the newly generated ignored campaign directory and rerun after fixing the code. Never edit campaign JSON manually.

### Artifacts and Notes

The old campaign that motivated this change recorded no observations for Icarus or Verilator because the exact-membership gate ran first. Direct manual proof showed:

    Icarus: /case/top.sv:2: syntax error, exit 2
    Verilator: %Error ... /case/top.sv:2:26: syntax error, exit 1

The expected new Overview values for the current corpus are approximately:

    slang/elaborator: PASS 5, FAIL 0, UNCLEAR 0, 100%
    icarus/simulator: PASS 11, FAIL 1, UNCLEAR 0, 92%
    verilator/simulator: PASS 12, FAIL 0, UNCLEAR 0, 100%

These are expectations to verify, not hard-coded product data.

### Interfaces and Dependencies

Use existing Pydantic strict models, Python standard library, React, TypeScript, and CSS. Add no dependency.

In `src/svtorture/models.py`, provide a single phase-order function used by profile support, plan validation, evaluator selection, and metric scope. `ToolProfile.supports(target: Phase) -> bool` must derive support from `phase_ceiling`. `ExecutionPlan` must carry `target_phase`. `ExecutionStage` and `StageObservation` must carry `attempted_through_phase`. `NormalizedResult` must carry `target_phase` and `evidence_mode`.

In `src/svtorture/evaluator.py`, keep `evaluate(case, tool_id, profile_id, observations)` as the public entry point so campaign, publication verification, and reproduction continue to share one policy. The returned result must preserve all observations and encode direct/cumulative attribution explicitly.

In the dashboard, consume `MetricPoint.conforming`, `nonconforming`, and `inconclusive` directly. Do not recompute requirement counts from raw results in the component.

Plan revision note (2026-07-21 20:11Z): Created the initial self-contained implementation plan after repository and runtime analysis. It records the user-authorized clean schema break, safe cumulative inference rules, required visual redesign, destructive evidence cleanup, and final review workflow.

Plan revision note (2026-07-21 23:35Z): Recorded completion of the clean contract, runtime, evaluator, metric, dashboard, documentation, and focused test milestones. Added the verified Icarus and Verilator preprocessing command behavior that determined direct-phase metadata.
