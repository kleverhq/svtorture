set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

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
    uv run ruff format --check src tests scripts
    uv run ruff check src tests scripts
    uv run mypy src

# Strict metadata and committed-schema verification.
hook-metadata:
    uv run svtorture validate
    uv run python scripts/generate_dashboard_fixture.py --check

# Focused deterministic framework tests; never invokes Docker or the network.
hook-tests:
    uv run pytest -q -m "not docker" tests/test_evaluator.py tests/test_catalog_models.py tests/test_adapters.py

# Lightweight frontend type and unit checks.
hook-frontend:
    npm --prefix dashboard run typecheck
    npm --prefix dashboard test

# Fast, deterministic checks suitable for pre-commit.
smoke: hook-python hook-metadata hook-tests hook-frontend

format:
    uv run ruff format src tests scripts

lint: hook-python

metadata: hook-metadata

unit:
    uv run pytest -m "not docker"

frontend:
    npm --prefix dashboard run typecheck
    npm --prefix dashboard test
    npm --prefix dashboard run build

precommit:
    git ls-files -z --cached --others --exclude-standard | xargs -0 uv run pre-commit run --files

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
    test -e toolchains/private.toml || cp toolchains/private.example.toml toolchains/private.toml

# Regenerate deterministic frontend fixture data.
fixture:
    uv run python scripts/generate_dashboard_fixture.py

# Build the fixture-backed dashboard.
dashboard-fixture:
    npm --prefix dashboard run build

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
