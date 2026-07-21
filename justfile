set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
set dotenv-load := true
set dotenv-filename := ".env.local"

annotator_dir := "standards/ieee-1800-2023-annotate"
annotation_output := annotator_dir / "generated"
annotation_python := annotator_dir / "annotate.py" + " " + annotator_dir / "verify.py" + " " + annotator_dir / "tests" + " " + annotator_dir / "utils"
ieee_pdf := env_var_or_default("IEEE_1800_2023_PDF", "")

default:
    @just --list

# Install exact Python/frontend locks and the local pre-commit hook.
setup:
    uv sync --all-groups --frozen
    npm --prefix dashboard ci --ignore-scripts
    uv run pre-commit install

# Lockfile-only install used by CI (does not change Git hooks).
setup-ci:
    uv sync --all-groups --frozen
    npm --prefix dashboard ci --ignore-scripts

# Locked Python-only install for matrix preparation and collection jobs.
setup-python:
    uv sync --all-groups --frozen

# Fast Python formatting, linting, and typing.
hook-python:
    uv run ruff format --check src tests scripts {{annotation_python}}
    uv run ruff check src tests scripts {{annotation_python}}
    uv run mypy src

# Strict metadata and committed-schema verification.
hook-metadata:
    uv run svtorture validate

# Focused deterministic framework tests; never invokes Docker or the network.
hook-tests:
    uv run pytest -q -m "not docker" tests/test_evaluator.py tests/test_catalog_models.py tests/test_adapters.py
    just annotator-tests

# Lightweight frontend type and unit checks.
hook-frontend:
    npm --prefix dashboard run typecheck
    npm --prefix dashboard test

# Fast, deterministic checks suitable for pre-commit.
smoke: hook-python hook-metadata hook-tests hook-frontend

format:
    uv run ruff format src tests scripts {{annotation_python}}

lint: hook-python

metadata: hook-metadata

unit:
    uv run pytest -m "not docker"
    just annotator-tests

frontend:
    npm --prefix dashboard run typecheck
    npm --prefix dashboard test
    npm --prefix dashboard run build

precommit:
    git ls-files -z --cached --others --exclude-standard | xargs -0 uv run pre-commit run --files

# Source-only tests for the annotator and its maintainer utilities.
annotator-tests:
    python3 -m unittest discover -s {{annotator_dir}}/tests -v
    python3 -m unittest discover -s {{annotator_dir}}/utils/compare_baseline -p 'test_*.py' -v
    python3 -m unittest discover -s {{annotator_dir}}/utils/scan_copied_text -p 'test_*.py' -v

# Materialize the complete ignored annotated corpus without changing committed metadata.
annotate pdf=ieee_pdf:
    test -n "{{pdf}}" || { echo "Set IEEE_1800_2023_PDF in .env.local or pass a PDF path." >&2; exit 1; }
    command -v pdftohtml >/dev/null || { echo "pdftohtml is required; install the poppler-utils package." >&2; exit 1; }
    rm -rf {{annotation_output}}
    python3 {{annotator_dir}}/annotate.py --all --pdf "{{pdf}}" --output-dir {{annotation_output}}/txt

_check-annotation-index:
    if ! cmp -s {{annotation_output}}/anchors.json standards/ieee-1800-2023-anchors.json; then echo "Generated anchors differ. Run 'just annotate-update-anchors', then commit standards/ieee-1800-2023-anchors.json." >&2; exit 1; fi

# Materialize and compare the generated anchor index with the committed runtime index.
annotate-check pdf=ieee_pdf:
    just annotate "{{pdf}}"
    python3 {{annotator_dir}}/verify.py {{annotation_output}}/txt --pdf "{{pdf}}"
    just _check-annotation-index

# Deliberately replace the committed runtime anchor index after successful annotation.
annotate-update-anchors pdf=ieee_pdf:
    just annotate "{{pdf}}"
    python3 {{annotator_dir}}/verify.py {{annotation_output}}/txt --pdf "{{pdf}}"
    cp {{annotation_output}}/anchors.json standards/ieee-1800-2023-anchors.json

# Regenerate every part a second time and require complete byte-for-byte stability.
annotate-verify pdf=ieee_pdf:
    just annotate "{{pdf}}"
    python3 {{annotator_dir}}/verify.py {{annotation_output}}/txt --pdf "{{pdf}}" --check-generated

# Real executor/evaluator integration with the deterministic container.
docker-fake:
    SVTORTURE_REQUIRE_DOCKER=1 uv run pytest -m docker

# Miniature current-upstream Docker E2E; ordinary conformance failures exit zero.
real-smoke tool_ref="icarus@latest":
    uv run svtorture run --tool "{{tool_ref}}" --suite smoke --exit-policy infra-only

# Full local equivalent of pull-request CI.
ci: setup-ci
    just precommit
    just lint
    just metadata
    just unit
    just frontend
    just docker-fake
    just real-smoke

# Resolve, build, and run one current upstream over the complete corpus.
latest tool suite="all":
    uv run svtorture run --tool "{{tool}}@latest" --suite "{{suite}}" --exit-policy infra-only

# Resolve an explicit tag, branch, or full SHA before building and running.
pinned tool ref suite="all":
    uv run svtorture run --tool "{{tool}}@{{ref}}" --suite "{{suite}}" --exit-policy infra-only

# Run all current public upstreams through the same Docker path.
latest-all suite="all":
    uv run svtorture run --tool slang@latest --tool icarus@latest --tool verilator@latest --suite "{{suite}}" --exit-policy infra-only

# Optional user-owned licensed wrapper; unavailable wrappers are recorded as skipped.
commercial suite="all":
    uv run svtorture run --tool vcs@local --suite "{{suite}}" --exit-policy infra-only

# Create the gitignored private-wrapper configuration once.
private-config:
    test -e tools/private.toml || cp tools/private.example.toml tools/private.toml

# Build a local dashboard dataset from one or more campaign paths.
dashboard-build campaigns visibility="local":
    npm --prefix dashboard run build
    uv run svtorture dashboard export {{campaigns}} --visibility "{{visibility}}" --output dashboard/dist/data/dataset.json

# Serve an already built local dashboard.
dashboard-serve port="4173":
    uv run svtorture dashboard serve --directory dashboard/dist --port "{{port}}"

# Replay one exact tool/profile/case judgment.
reproduce campaign tool profile case_id:
    uv run svtorture reproduce "{{campaign}}" --tool "{{tool}}" --profile "{{profile}}" --case "{{case_id}}"

# Publication-eligible tools as a GitHub matrix, selected only from metadata policy.
ci-matrix:
    uv run svtorture ci-matrix

# Nightly exact resolution, immutable GHCR push, and full-corpus collection.
nightly tool repository="":
    repository="{{repository}}"; if test -z "$repository"; then repository="ghcr.io/${GITHUB_REPOSITORY,,}-{{tool}}"; fi; mkdir -p .svtorture/campaigns; before="$(find .svtorture/campaigns -name campaign.json | wc -l)"; status=0; uv run svtorture run --tool "{{tool}}@latest" --suite all --push --repository "$repository" --exit-policy infra-only || status=$?; after="$(find .svtorture/campaigns -name campaign.json | wc -l)"; if test "$status" -ne 0 && test "$before" = "$after"; then uv run svtorture record-missing --tool "{{tool}}" --suite all; fi; exit "$status"

# Aggregate whatever nightly campaign artifacts arrived and mark missing tools.
aggregate-artifacts artifacts:
    uv run python scripts/aggregate_artifacts.py "{{artifacts}}"

# Append a trusted aggregate to gh-pages without force-pushing.
pages-publish campaign:
    npm --prefix dashboard run build
    uv run python scripts/publish_pages.py "{{campaign}}"

schemas:
    uv run svtorture schemas --write
