# Integrate the IEEE 1800-2023 annotator

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the `exec-plan` skill.

## Purpose / Big Picture

After this change, the repository owns the source code that turns a user-supplied IEEE 1800-2023 PDF into an annotated text corpus and stable anchor index. Normal framework use continues to depend only on the committed `standards/ieee-1800-2023-anchors.json`; no PDF, generated text, private URL, or external repository is required. A requirement author can put a stable local PDF path in ignored `.env.local`, run a root `just` target to materialize the corpus, and use a separate target to update the committed anchor index. CI regenerates and byte-compares that index only when the `IEEE_1800_2023_PDF_URL` secret is configured, otherwise it emits an explicit warning and passes.

The result is visible by running `just annotate`, inspecting the ignored `standards/ieee-1800-2023-annotate/generated/txt/` corpus, and running `just annotate-check`. The check must either succeed or explain that `just annotate-update-anchors` should be run and its result committed.

## Non-Goals

This change does not commit an IEEE PDF or generated annotated TXT files. It does not make annotation part of normal catalog loading, simulation, replay, dashboard publication, or deterministic tests that lack a PDF. It does not add requirement-schema-version-1 compatibility. It does not redesign anchor syntax, requirement semantics, or the existing committed requirement citations.

## Progress

- [x] (2026-07-21 07:13Z) Updated the existing submodule from `e63112d2a9dfb4586d0e33769721238c8c619ece` to latest `master` commit `67747e5a11a1772b9006288a88fc1786868422d6` and inspected every tracked source category.
- [x] (2026-07-21 07:13Z) Confirmed the local reference PDF at `/home/esynr3z/.pi/agent/skills/systemverilog/references/IEEE-1800-2023.pdf` has the expected SHA-256 `203fbcccbbae90cef401a3acd31835c8cd1507e8f12b2e069046d4f316e317c9`, and confirmed local Poppler `pdftohtml` is version 24.02.0.
- [x] (2026-07-21 07:13Z) Resolved product decisions: Poppler is a documented system dependency and an apt dependency in CI; anchor updates use a separate `just` target; legacy terminology becomes annotation terminology throughout.
- [x] (2026-07-21 07:18Z) Imported the latest annotator source into `standards/ieee-1800-2023-annotate/`, removed the submodule and `.gitmodules`, and renamed terminology and code consistently.
- [x] (2026-07-21 07:21Z) Added ignored local environment configuration, root `just` targets, integrated tests, and conditional CI anchor verification.
- [x] (2026-07-21 07:22Z) Replaced annotator development documentation with `docs/annotation.md`, simplified its local README, and updated adjacent architecture and workflow documents.
- [x] (2026-07-21 07:45Z) Materialized from the reference PDF, proved byte identity, passed strict verification and `just ci`, completed two focused reviews plus a fresh control review, fixed every finding, re-reviewed the fixes cleanly, and committed the integration.

## Surprises & Discoveries

- Observation: The latest annotator source intentionally tracks neither the PDF nor generated TXT and anchor outputs.
  Evidence: commit `67747e5` has root `.gitignore` entries for `/generated/`, `/pdf/`, `/txt/`, `/anchors.json`, and `*.pdf`; the tracked tree contains only Python source, structural data, tests, and maintenance utilities.
- Observation: The source uses only the Python standard library; Poppler is the only runtime dependency for annotation.
  Evidence: `annotate.py`'s predecessor invokes `pdftohtml`, while all tests use `unittest` and there is no Python requirements file.
- Observation: The expected PDF and Poppler versions are available locally and exactly match the annotator's development references.
  Evidence: SHA-256 is `203fb...e317c9`, PDF size is 9,448,927 bytes with 1,354 physical pages, and `pdftohtml -v` reports 24.02.0.
- Observation: Generated TXT metadata records the selected PDF path, but generated `anchors.json` records only the source SHA-256 and stable relative TXT paths.
  Evidence: `render()` writes `source=<path>` to each part, while `render_anchors_index()` emits `source_sha256` plus entries such as `txt/04.txt`; therefore byte comparison of the committed index is independent of local PDF path.
- Observation: Renaming the text-review marker and all annotation terminology does not change the anchor inventory.
  Evidence: `just annotate-check` generated 58 parts, verified 16,963 anchors and all object/marker counts, and byte-compared the generated index equal to the committed `standards/ieee-1800-2023-anchors.json`.
- Observation: A secret-backed job in a pull-request workflow must not execute pull-request-controlled annotation code.
  Evidence: code review identified the exposure; the annotation job is now restricted to trusted pushes to `main` and a branch-restricted GitHub environment.
- Observation: Quoting a `just` parameter with literal shell double quotes does not prevent command substitution in an adversarial path.
  Evidence: review identified the interpolation boundary. All PDF parameters now use Just's `quote()` function, and a path containing `$(touch ...)` was passed literally without creating the marker file.
- Observation: Even a trusted-branch secret job should not run floating setup actions or retain the secret while executing repository code.
  Evidence: the final control review identified the supply-chain boundary. The job now pins checkout, setup-just, and Just 1.21.0, scopes the URL to the curl-only step, and runs annotation in a later secret-free step.
- Observation: Source-only tests in normal repository gates must use the Python environment installed by `just setup`.
  Evidence: the final control review found direct host `python3` calls; `annotator-tests` now uses `uv run python`, and focused re-review reported no substantive findings.

## Decision Log

- Decision: Import the exact tracked contents of submodule commit `67747e5` under `standards/ieee-1800-2023-annotate/`, then delete `.gitmodules` and the gitlink.
  Rationale: This preserves the reviewed refactor as the integration baseline while removing network and repository-boundary coupling.
  Date/Author: 2026-07-21 / coding agent.
- Decision: Use `.env.local` as the ignored root configuration and track `.env.local.example` with `IEEE_1800_2023_PDF=/absolute/path/to/IEEE-1800-2023.pdf`.
  Rationale: `just` 1.21 supports `dotenv-load` with a custom filename, giving requirement authors a stable machine-local PDF path without committing it.
  Date/Author: 2026-07-21 / coding agent.
- Decision: Materialize generated files under `standards/ieee-1800-2023-annotate/generated/`.
  Rationale: The imported annotator already ignores this path, and colocating ephemeral output makes its ownership obvious without polluting framework runtime state.
  Date/Author: 2026-07-21 / coding agent.
- Decision: Provide `annotate`, `annotate-check`, `annotate-update-anchors`, `annotate-verify`, and `annotator-tests` recipes.
  Rationale: Generation, strict verification, CI comparison, deliberate committed-index update, and source-only tests are distinct actions. In particular, ordinary generation must not silently modify a committed file.
  Date/Author: 2026-07-21 / coding agent.
- Decision: Rename all legacy terminology in the integrated annotator, including the script and test names, internal identifiers and messages, documentation, generated preamble, and text-annotation review marker.
  Rationale: The repository presents a complete annotation pipeline. Poppler's executable name `pdftohtml` remains unchanged because it is an external program.
  Date/Author: 2026-07-21 / coding agent.
- Decision: Keep Poppler out of `pyproject.toml`; document package installation locally and install Ubuntu's `poppler-utils` only in the conditional CI annotation job.
  Rationale: Poppler is an operating-system program, not a Python package. Normal CI and users who do not annotate must not pay for or require it.
  Date/Author: 2026-07-21 / coding agent.
- Decision: CI will run annotation only on trusted pushes to `main` in the branch-restricted `ieee-1800-2023-annotation` environment. It downloads the PDF to ignored `.svtorture/` only when the environment secret `IEEE_1800_2023_PDF_URL` is nonempty, runs `just annotate-check <path>` in a separate secret-free step, and otherwise emits a warning. Setup actions and Just are pinned.
  Rationale: Pull-request-controlled code and floating setup dependencies never receive the licensed URL, while configured trusted CI proves deterministic byte identity and an unconfigured environment remains explicit.
  Date/Author: 2026-07-21 / coding agent.

## Outcomes & Retrospective

The private submodule and `.gitmodules` are gone; the repository owns the annotator source under the requested `standards/ieee-1800-2023-annotate/` path. The licensed PDF, `.env.local`, generated 58-part corpus, and generated index remain ignored. The committed runtime index did not change: generated and committed files share SHA-256 `34030dd64ab2d867124f0c449fe3e8146805df365dd7dd244ee2f38d4e71c9dc`.

`just annotate-check` reports 16,963 anchors and complete object/marker inventories, while `just annotate-verify` reports 58/58 deterministic regenerations and `verification: PASS`. `just annotate-update-anchors` leaves no diff for the reference PDF, and a forced byte mismatch prints the required update-and-commit instruction. Ninety-three framework tests, fifteen annotator and utility tests, five dashboard tests, eleven Docker integration tests, lint, typing, metadata validation, frontend build, pre-commit, smoke without dotenv, source-hygiene scanning, and the full `just ci` gate pass. The real Icarus smoke campaign completed without an infrastructure failure. No PDF or generated TXT is tracked.

Code/workflow and documentation reviewers found four substantive boundaries: pull-request secret exposure, unsafe shell interpolation, imprecise verification wording/stale plan state, and floating setup dependencies plus host-Python test execution. All were fixed. Focused re-reviews and a fresh control-finding re-review reported no substantive findings. The implementation is complete.

## Context and Orientation

The root repository is `/home/esynr3z/projects/sv-torture`. `standards/ieee-1800-2023-anchors.json` is a committed machine-readable inventory used by `src/svtorture/catalog.py` to validate every requirement citation. Catalog loading continues to use only that file. Before this plan, an optional submodule lived at `standards/ieee-1800-2023-annotated`; commit `8773fd9` replaced it and `.gitmodules` with owned annotator source.

At commit `67747e5`, the annotator consists of a legacy-named primary script, `verify.py`, `data/recipes.json`, `data/objects.csv`, its primary test, and two maintenance utilities under `utils/`. The primary script's `--all --pdf PDF --output-dir generated/txt` mode invokes Poppler `pdftohtml` for all 41 clauses and 17 annexes, writes 58 annotated TXT files, and produces `generated/anchors.json`. `verify.py generated/txt --pdf PDF` validates corpus structure and deterministic anchor-index generation; `--check-generated` regenerates each part and compares bytes. `data/recipes.json` carries only structural anchor and review-marker corrections, not copied standard prose. `data/objects.csv` inventories numbered tables, figures, and Syntax objects.

The new owned directory is exactly `standards/ieee-1800-2023-annotate/`. Its primary command becomes `annotate.py`; its main test becomes `tests/test_annotate.py`. `DEVELOPMENT.md` is removed. The local `README.md` becomes a short purpose and navigation document pointing to root `docs/annotation.md`, which owns prerequisites, environment setup, pipeline, outputs, anchor and marker conventions, recipe maintenance, verification, utilities, and CI behavior.

The root `justfile` is the stable command interface. Before this integration it did not load dotenv files. It now uses `set dotenv-load := true` and `set dotenv-filename := ".env.local"` to make the ignored local configuration available to recipes without affecting environments where the file does not exist. `.env.local.example` documents the only initial setting. The actual ignored `.env.local` on this workstation will use `/home/esynr3z/.pi/agent/skills/systemverilog/references/IEEE-1800-2023.pdf`.

## Open Questions

There are no unresolved product questions. Target behavior, terminology scope, Poppler installation, local PDF configuration, CI secret semantics, and documentation ownership were confirmed by the user.

## Plan of Work

First archive the tracked files from submodule commit `67747e5` into the new owned directory, excluding submodule Git metadata. Remove the old gitlink and `.gitmodules`. Delete imported `DEVELOPMENT.md`. Rename the primary script and test to `annotate.py` and `tests/test_annotate.py`. Update imports, symbols, messages, generated metadata, markers, tests, data recipes, utility source, and utility documentation so the integrated directory has no legacy terminology. Preserve genuine external names such as `pdftohtml`.

Add root `.env.local` to `.gitignore`, create `.env.local.example`, and create the actual ignored local file with the known reference PDF path. Configure `just` to load `.env.local`. Add recipes that check the PDF argument and `pdftohtml`, generate to the ignored annotator `generated/` directory, verify generated output, compare generated and committed anchor indexes, update the committed index only on the explicit update target, and run all three authored unit-test suites. The comparison failure must print the exact remediation: run `just annotate-update-anchors` and commit `standards/ieee-1800-2023-anchors.json`.

Integrate source-only annotator checks into `just smoke`, `just unit`, formatting/linting where practical, and pre-commit file selection. Remove `scripts/check_annotated_anchors.py` and its old optional-submodule hook because the submodule no longer exists. Keep normal catalog and replay behavior using the committed runtime index.

Add a separate GitHub Actions annotation job or equivalent isolated steps. Detect whether `IEEE_1800_2023_PDF_URL` is configured without printing it. If absent, emit `::warning::` and succeed. If present, install `poppler-utils`, download the PDF into `.svtorture/`, run the root comparison target, and fail with the target's update-and-commit message when bytes differ. Normal CI remains independent of Poppler and the secret.

Write `docs/annotation.md` and simplify the nested README. Update `README.md`, `docs/README.md`, `docs/architecture.md`, `docs/methodology.md`, `docs/adding-a-case.md`, applicable `AGENTS.md` breadcrumbs, and durable reproduction wording so they distinguish the committed runtime index from optional annotation materialization and explain how the index is produced.

Finally run source-only checks, full annotation with the exact local reference PDF, structural and strict deterministic verification, byte comparison, all deterministic repository checks, dashboard build, and pre-commit. Confirm tracked files contain no PDF or generated TXT and that `.env.local` is ignored. Request focused code/workflow and documentation reviews, apply findings, rerun affected checks, run a fresh control review, and create Conventional Commits. Keep the ExecPlan updated after each milestone.

### Concrete Steps

Run all commands from `/home/esynr3z/projects/sv-torture`.

The import begins from the already updated submodule commit:

    git -C standards/ieee-1800-2023-annotated rev-parse HEAD

Expected output:

    67747e5a11a1772b9006288a88fc1786868422d6

Archive its tracked tree into the owned destination before removing the submodule:

    mkdir -p standards/ieee-1800-2023-annotate
    git -C standards/ieee-1800-2023-annotated archive HEAD |
      tar -x -C standards/ieee-1800-2023-annotate

Then deinitialize and remove the old gitlink and `.gitmodules`, rename and edit imported files, and add root integration.

The local ignored configuration is:

    IEEE_1800_2023_PDF=/home/esynr3z/.pi/agent/skills/systemverilog/references/IEEE-1800-2023.pdf

After implementation, materialize and compare:

    just annotate
    just annotate-check
    just annotate-verify

To deliberately refresh the committed index:

    just annotate-update-anchors
    git add standards/ieee-1800-2023-anchors.json

Run deterministic repository acceptance:

    just smoke
    just unit
    just frontend
    just precommit
    git diff --check

Audit terminology and tracked artifacts:

    # Search the integrated source and docs for the retired pre-annotation terminology.
    git ls-files '*.pdf' 'standards/ieee-1800-2023-annotate/generated/**' 'standards/ieee-1800-2023-annotate/txt/**'
    git check-ignore -v .env.local standards/ieee-1800-2023-annotate/generated/anchors.json

The terminology search should be empty. The tracked-artifact search should be empty. The ignore check should identify root and annotator ignore rules.

### Validation and Acceptance

A fresh normal checkout without `.env.local`, the PDF, Poppler, or `IEEE_1800_2023_PDF_URL` must pass all framework checks that do not request annotation. Catalog loading must continue to read only `standards/ieee-1800-2023-anchors.json`.

With the local reference PDF configured, `just annotate` must create exactly 58 TXT files and `generated/anchors.json` without touching the committed index. `just annotate-check` must pass against the committed index. Temporarily changing one byte in a generated index must make the comparison fail with a message that names `just annotate-update-anchors` and tells the contributor to commit the result. `just annotate-update-anchors` must be the only normal recipe that overwrites the committed index.

`just annotate-verify` must report 58/58 files, one valid anchor index, complete table/figure/Syntax inventories, expected marker totals, 58/58 deterministic regenerations, and `verification: PASS`. Annotator tests and utility tests must pass without a PDF. No tracked source under the integrated annotator may use retired pre-annotation terminology.

On a trusted `main` push, the branch-restricted annotation environment must emit a visible warning and succeed without installing Poppler when its URL secret is absent. With the environment secret present, it must install Poppler, download without logging the URL, generate the full corpus, and compare the generated index byte-for-byte to the committed file. Pull-request jobs must never receive or consume the secret.

### Idempotence and Recovery

The import uses `git archive`, so rerunning it into an empty destination reproduces exactly the tracked upstream tree without copying `.git` or ignored artifacts. Annotation targets remove or replace only the ignored `generated/` directory. The update target copies a deterministic generated JSON file over one committed file; rerunning it with the same PDF is byte-stable and any change is reviewable in Git.

Never copy or commit the PDF. Keep it at the external path in `.env.local`. CI downloads only to ignored `.svtorture/`. If annotation is interrupted, remove `standards/ieee-1800-2023-annotate/generated/` and rerun. If submodule removal is interrupted, preserve the archived destination, inspect `git status`, and use normal Git staging rather than deleting unrelated `.git/modules` state manually.

### Artifacts and Notes

The upstream integration baseline is:

    67747e5a11a1772b9006288a88fc1786868422d6

The reference input is:

    path: /home/esynr3z/.pi/agent/skills/systemverilog/references/IEEE-1800-2023.pdf
    sha256: 203fbcccbbae90cef401a3acd31835c8cd1507e8f12b2e069046d4f316e317c9
    Poppler pdftohtml: 24.02.0

The existing committed runtime index contains 16,963 anchors and was generated from that SHA-256. Its byte identity after the terminology refactor is an explicit acceptance condition; annotation marker renaming changes TXT content and verifier policy but not the list of anchors stored in this JSON index.

### Interfaces and Dependencies

No Python dependency is added. The new external dependency is Poppler's `pdftohtml`, supplied by the `poppler-utils` operating-system package. `standards/ieee-1800-2023-annotate/annotate.py` remains a Python 3.10+ standard-library CLI accepting `--pdf`, `--all`, `--output-dir`, `--anchors-from`, `--anchors-output`, and single-part positional mode. It resolves PDF input from `--pdf` first and `IEEE_1800_2023_PDF` second.

`standards/ieee-1800-2023-annotate/verify.py` remains the structural verifier, importing annotation primitives from `annotate.py`. Root recipes are the supported repository interface; direct script commands are documented as implementation-level equivalents only in `docs/annotation.md`.

The committed runtime contract remains `standards/ieee-1800-2023-anchors.json`. `src/svtorture/catalog.py` does not import annotator code and does not read generated TXT. GitHub Actions receives only `IEEE_1800_2023_PDF_URL`; the local ignored file receives only `IEEE_1800_2023_PDF`.

Revision note (2026-07-21 07:13Z): Initial self-contained plan written after updating and inspecting upstream, confirming the local PDF and Poppler versions, and resolving all user decisions.

Revision note (2026-07-21 07:23Z): Recorded source integration, terminology migration, root workflow and CI wiring, documentation migration, successful 58-part materialization, structural verification, and anchor-index byte identity.

Revision note (2026-07-21 07:31Z): Recorded strict regeneration, complete gates, focused review findings, trusted-branch secret isolation, shell-safe PDF arguments, and documentation corrections.

Revision note (2026-07-21 07:40Z): Closed the plan after control review, action/version pinning, URL-step isolation, uv-backed source tests, clean re-review, and the final evidence audit.

Revision note (2026-07-21 07:45Z): Added the successful full `just ci` result, including Docker integration and real-tool smoke evidence, and recorded the completed commits.
