# Execute campaign combinations through one bounded worker pool

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the repository's `exec-plan` skill.

## Purpose / Big Picture

A user running `svtorture run`, `just public`, `just commercial`, or `just all` should be able to execute independent tool/profile/case combinations concurrently. Omitting the worker count should use all CPUs available to the SVTORTURE process, while `--jobs N` or the corresponding Just argument should impose one global limit. The observable proof is that two combinations overlap in a deterministic unit test, the campaign still contains the complete grid in stable order, and a Docker smoke campaign succeeds with more than one worker.

A combination is one selected tool profile applied to one selected case. Stages inside a combination remain sequential because later stages consume artifacts from earlier stages. Tool preparation, including image resolution and image building, also remains sequential; this plan concerns campaign execution after preparation.

## Non-Goals

This change does not introduce per-tool queues, resource classes, license-seat discovery, CPU affinity assignment, Docker CPU quotas, a persistent scheduler, multiprocessing, or asynchronous I/O. It does not parallelize image builds. It does not change campaign schemas or serialize the local worker count as evidence.

## Progress

- [x] (2026-07-30 11:24Z) Traced CLI preparation, campaign orchestration, plan execution, process management, Just recipes, and existing tests.
- [x] (2026-07-30 11:24Z) Chose one standard-library thread pool over the flattened campaign grid and documented cancellation and ordering requirements.
- [x] (2026-07-30 11:30Z) Added failing tests for global overlap, stable result ordering, CLI exposure, worker-count resolution, and process cancellation; failures show `jobs`, `_worker_count`, and `ProcessCancelled` do not yet exist.
- [x] (2026-07-30 11:36Z) Implemented the bounded global thread pool, stable result restoration, affinity-aware automatic worker count, and prompt process-group cancellation without changing evaluation semantics.
- [x] (2026-07-30 11:38Z) Exposed `--jobs/-j` through the CLI and all campaign Just recipes, and documented global pooling and resource constraints.
- [x] (2026-07-30 11:40Z) Passed 162 non-Docker tests and the parallel fake Docker campaign test; verified Just argument forwarding and CLI help.
- [x] (2026-07-30 11:43Z) Resolved all code, architecture/performance, and documentation review findings; each impacted reviewer reported no substantive findings on recheck.
- [x] (2026-07-30 11:44Z) Passed `just smoke` and the first `just ci`: 162 non-Docker, 11 Docker, and 67 dashboard tests passed.
- [x] (2026-07-30 11:45Z) Ran `just all smoke 4`; one four-worker pool completed 20 combinations across Slang, Icarus, Verilator, and VCS and persisted a complete, stable campaign.
- [x] (2026-07-30 11:48Z) Resolved the final control-review finding by cleaning surviving descendants when the process-group leader exits before cancellation; the reviewer recheck found no substantive findings.
- [x] (2026-07-30 11:50Z) Re-ran final `just ci`: 163 non-Docker, 11 Docker, and 67 dashboard tests passed; audited stable campaign ordering, ignored local VCS files, private paths, and diff whitespace.
- [x] (2026-07-30 11:51Z) Committed the completed work as `feat(execution): parallelize campaign jobs` and verified the resulting commit.

## Surprises & Discoveries

- Observation: `run_campaign()` currently performs the complete grid through nested tool-major loops, while `execute_plan()` already gives every combination a unique work directory.
  Evidence: `src/svtorture/campaign.py` loops over prepared tools and then selected cases; `src/svtorture/executor.py` receives `.svtorture/work/<campaign>/<tool>/<profile>/<case>`.

- Observation: process output is already drained by threads, and the expensive work runs in Docker or a local wrapper subprocess rather than in Python.
  Evidence: `src/svtorture/process.py` creates two drain threads around `subprocess.Popen`; therefore Python's global interpreter lock is not a reason to use multiple Python processes.

- Observation: a plain `ThreadPoolExecutor` context waits for active work after `Ctrl-C`, while workers do not receive the main thread's `KeyboardInterrupt`.
  Evidence: active subprocesses need a shared cancellation event so they can terminate their process groups and let executor shutdown complete promptly.

- Observation: waiting only for the process-group leader after `SIGTERM` can leave an ignoring descendant alive with inherited output pipes.
  Evidence: review identified the leader/descendant race; the cancellation test now launches a child that ignores `SIGTERM`, and group-wide TERM-to-KILL cleanup completes in under four seconds.

- Observation: the real combined smoke campaign visibly completed in non-submission order while persisted result reporting remained tool-major.
  Evidence: `just all smoke 4` printed interleaved `done [1/20]` through `done [20/20]` lines for all four tools, then reported stable grouped results and campaign `20260730T114129Z-379b1499791f641b`.

## Decision Log

- Decision: use one `concurrent.futures.ThreadPoolExecutor` for all tool/profile/case combinations.
  Rationale: it is a standard-library bounded pool suited to external subprocess work and avoids a custom scheduler or dependency.
  Date/Author: 2026-07-30 / Pi

- Decision: submit work case-major across prepared tools, consume futures as they complete, but restore the existing tool-major result order before campaign construction.
  Rationale: case-major submission mixes tools in the first worker wave, completion-order consumption exposes failures promptly, and indexed restoration preserves deterministic campaign JSON and existing behavior.
  Date/Author: 2026-07-30 / Pi

- Decision: invoke progress callbacks serially on the orchestration thread as combinations complete.
  Rationale: callbacks remain safe for ordinary mutable state and receive monotonic counts without blocking workers or falsely claiming deterministic start order.
  Date/Author: 2026-07-30 / Pi

- Decision: expose `--jobs/-j`, where zero means automatic and positive values are exact maximum concurrent combinations.
  Rationale: zero is easy for Just recipes to pass, while “jobs” accurately describes external executions rather than claiming CPU enforcement.
  Date/Author: 2026-07-30 / Pi

- Decision: automatic mode uses Linux CPU affinity when available, otherwise `os.cpu_count()`, and never creates more workers than combinations.
  Rationale: affinity reflects CPUs available to the process; the fallback is portable on Python 3.12.
  Date/Author: 2026-07-30 / Pi

- Decision: preserve sequential defaults for direct `run_campaign()` callers while the user-facing CLI defaults to automatic parallelism.
  Rationale: direct API tests and internal callers retain deterministic conservative behavior; all supported command-line campaign paths gain the requested default.
  Date/Author: 2026-07-30 / Pi

- Decision: use one shared `threading.Event` only for cancellation, threaded through campaign, executor, and process functions.
  Rationale: this is the smallest way to stop active process groups promptly; it does not schedule or prioritize work.
  Date/Author: 2026-07-30 / Pi

## Outcomes & Retrospective

The native global pool, deterministic persisted evidence, configurable concurrency, and prompt cancellation are implemented without a scheduler abstraction or dependency. Unit, Docker, dashboard, and real four-tool smoke evidence pass. Focused and independent control reviews have no unresolved findings. The completed work is committed as `feat(execution): parallelize campaign jobs`.

## Context and Orientation

`src/svtorture/cli.py` defines the Typer `run` command. It prepares each requested tool sequentially and calls `run_campaign()`.

`src/svtorture/campaign.py` owns the campaign grid, evaluation, result persistence, and progress callbacks. Its `PreparedTool` values identify one resolved tool profile and backend. Its `run_campaign()` function currently loops over every prepared tool and then every selected case.

`src/svtorture/executor.py` executes the stages of one `ExecutionPlan` in order. A stage is one compile, elaborate, or run subprocess. Each combination has a disjoint work directory, so combinations do not share generated artifacts.

`src/svtorture/process.py` launches a subprocess in a new process group, captures bounded output, and terminates the process group on timeout. A cancellation event must reuse that same termination path.

The root `justfile` is the stable command interface. Its `public`, `commercial`, and `all` recipes already construct one CLI invocation containing every selected tool, so they need only forward a worker count.

`tests/test_campaign_metric.py` tests campaign orchestration without requiring Docker. `tests/test_process.py` tests subprocess timeout and capture behavior. `tests/test_cli.py` checks the user-facing command. `tests/test_fake_docker.py` is the deterministic Docker integration suite.

## Open Questions

There are no unresolved design questions. Operators remain responsible for selecting a lower positive job count when memory or commercial license seats are scarcer than CPUs.

## Plan of Work

First add tests before production support. In `tests/test_campaign_metric.py`, create two copied fake tool definitions and monkeypatch `execute_plan()` with a two-party barrier. Run a two-tool campaign with `jobs=2`; require that the first overlapping pair contains both tool IDs and that persisted results still use the prior tool-major order. Add a separate assertion that `jobs=1` never overlaps. Avoid Docker and network access.

In `tests/test_process.py`, start a sleeping Python subprocess, set a cancellation event shortly afterward, require the internal cancellation exception, and require completion well before the normal timeout. In `tests/test_cli.py`, require `run --help` to expose `--jobs` and `-j`. Test the automatic worker helper with monkeypatched affinity and CPU-count values.

Then extract the current per-combination body of `run_campaign()` in `src/svtorture/campaign.py` into one private function returning exactly one `NormalizedResult`. Build work items in case-major submission order and give each item its existing tool-major result index. Submit them to `ThreadPoolExecutor`, consume them with `as_completed()`, and sort indexed results before attaching reproduction commands and building the campaign. Invoke progress callbacks from that completion loop. On any escaping exception, set the shared cancellation event and cancel queued futures so an unexpected failure does not consume the remaining campaign. Keep all existing synthetic status and evaluation behavior unchanged.

In `src/svtorture/process.py`, add a private process-group termination helper and a `ProcessCancelled` exception. Extend `run_process()` with an optional cancellation event. Poll process completion against both the existing deadline and that event; on cancellation, terminate the process group, drain and close output, then raise `ProcessCancelled`. Thread the optional event through `src/svtorture/executor.py`.

In `src/svtorture/cli.py`, add `--jobs/-j` with default zero and reject negative values. Resolve zero to available CPUs, cap the value to at least one, and pass it to `run_campaign()`. In the root `justfile`, add a final `jobs="0"` parameter to campaign recipes and pass `--jobs`. Update `README.md` and the execution description in `docs/architecture.md` with concise current behavior and the warning that commercial licenses and aggregate memory may require a smaller explicit value.

### Concrete Steps

Run all commands from the repository root.

Before production edits, run the new focused tests and expect failures proving the requested behavior is absent:

    uv run pytest -q tests/test_campaign_metric.py tests/test_process.py tests/test_cli.py

After implementation, repeat that command and expect all selected tests to pass. Then run:

    just smoke
    uv run pytest -q tests/test_fake_docker.py::test_fake_container_exercises_executor_campaign_and_reproduction
    just ci

The focused Docker test builds the fake image and calls `run_campaign(..., jobs=2)` against the smoke suite. It is the deterministic end-to-end proof because the internal fake tool intentionally has no public upstream ref and therefore cannot be selected through `tool@ref` CLI syntax.

### Validation and Acceptance

The implementation is accepted when a deterministic unit test proves two different tool/case combinations are active simultaneously under `jobs=2`, while `jobs=1` proves no overlap. Campaign results must remain ordered by prepared tool and selected case regardless of completion order. `svtorture run --help` must show `--jobs` and `-j`; negative values must fail with a parameter error; omitted or zero values must resolve to available CPUs. Cancellation must terminate a sleeping process promptly. Existing synthetic outcomes, evaluation, campaign validation, and reproduction data must remain unchanged.

`just smoke` and `just ci` must pass. A Docker-backed campaign with at least two workers must produce one complete result per selected combination without work-directory conflicts. Commercial VCS execution is optional for validation because license capacity is machine-specific; if run, choose a conservative explicit job count.

### Idempotence and Recovery

Tests and campaign commands are safe to repeat. Campaign and work output stays under ignored `.svtorture/`. If an interrupted run leaves work output, rerunning creates a new campaign ID. Do not delete or alter local commercial runner configuration. If parallel Docker execution exposes a resource shortage, rerun with `--jobs 1` to distinguish resource capacity from correctness.

### Artifacts and Notes

The essential implementation shape is:

    work = [(result_index, prepared_tool, loaded_case), ...]
    futures = [pool.submit(run_one, item) for item in work]
    indexed_results = [future.result() for future in as_completed(futures)]
    results = [result for _, result in sorted(indexed_results)]

No queue class, scheduler object, resource broker, or new dependency should appear in the final diff.

### Interfaces and Dependencies

Use only Python 3.12 standard library modules `concurrent.futures`, `threading`, and `os`.

`src/svtorture/campaign.py` must expose:

    def run_campaign(..., jobs: int = 1, ...) -> Campaign

`src/svtorture/process.py` must expose an internal cancellation exception and extend:

    def run_process(..., cancel_event: threading.Event | None = None) -> ProcessResult

`src/svtorture/executor.py` must extend:

    def execute_plan(..., cancel_event: threading.Event | None = None) -> tuple[StageObservation, ...]

The Typer command must expose `--jobs/-j` as a nonnegative integer where zero means automatic. No public Pydantic model or JSON Schema changes are required.

Revision note (2026-07-30): Initial plan created after tracing the current execution path and selecting the smallest standard-library global-pool design.

Revision note (2026-07-30): Recorded the TDD implementation, documentation, and focused unit/Docker evidence; replaced an invalid fake-tool CLI example with the actual deterministic Docker test.

Revision note (2026-07-30): Incorporated review findings by making unexpected failures fail fast, keeping progress callbacks serialized on the orchestration thread, and strengthening process-group termination for descendants that ignore `SIGTERM`.

Revision note (2026-07-30): Recorded complete CI, resolved review lanes, and the real four-tool parallel smoke campaign; only control review and commit remain.

Revision note (2026-07-30): Recorded the final leader-exit cancellation fix, clean reviewer recheck, second complete CI run, and audit evidence before commit.

Revision note (2026-07-30): Marked the plan complete after creating and verifying the requested Conventional Commit.
