# Adding a tool

Each tool has a `tools/<name>/tool.toml` manifest listed in
`tools/tools.toml` and an adapter under `src/svtorture/adapters/`. The adapter
constructs typed stages and normalizes diagnostics. The evaluator, not the
adapter, decides conformance. Manifest paths for Dockerfiles, recipe files, and
local runner configuration are relative to the tool directory.

## Registration and profiles

Declare:

- stable ID/display name and adapter implementation;
- parser, elaborator, and/or simulator profiles with a cumulative
  `phase_ceiling` and ordered `direct_phases`;
- headline profile and effective language/revision mode;
- `distribution`, `execution`, `ci`, and `publish` policy;
- public upstream/default branch, Dockerfile, repository, and additional
  `recipe_files` where applicable.

Synthesis profiles do not belong in this project. A parser ceiling is `parse`,
an elaborator ceiling is `elaborate`, and a simulator ceiling is `simulate`.
Every profile supports prerequisite phases cumulatively. Mark a phase as direct
only when the adapter has a command bounded at that phase. Otherwise, use the
nearest later command and record its actual boundary.

## Open-source path

Open-source tools use `execution = "docker"`. The adapter reads the case's
ordered sources, top, include directories, defines, and arguments while keeping
`$CASE` and `$WORK` paths portable. Before building an image, SVTORTURE resolves
`latest`, a tag, a branch, or a full SHA to one commit.

The build records the source SHA, exact tags and the nearest tag when available,
reported version, recipe hash, pinned base-image digest, platform, image ID, and
pushed repository digest. Runtime execution cannot use a host binary or network. The
nightly workflow probes the digest without registry credentials. GHCR must allow
anonymous manifest access so old results remain reproducible after CI
credentials and artifacts expire.

## Commercial path

Commercial tools use `distribution = "commercial"`,
`execution = "local-wrapper"`, `ci = false`, and `publish = false`. Their
committed manifest names `runner_config = "runner.toml"`. Copy the adjacent
example with `just runner-config <tool>` and set its command plus an explicit
environment allowlist. The resulting `runner.toml` remains ignored by Git.

The local runner command accepts `--request <json>` and sets up the licensed
container or environment. `environment_allowlist` names the only host variables
that may be forwarded. Each listed variable is also a readiness requirement, so
a missing license endpoint produces `skipped-unavailable`.

A version-2 version request contains `kind = "version"`, `tool`, and the
adapter's `argv`. Execute that argv in the licensed environment and forward the
tool's stdout, stderr, and exit status unchanged; the first nonempty output line
becomes the reported version.

A normal execution request contains `tool`, `case`, `profile`, one `stage`, a
`mounts` object, and `execution_policy`. The stage includes its ID, target phase,
attempted-through phase, argv, portable argv, and timeout. `mounts.case` and
`mounts.work` are host paths for the read-only `/case` and writable `/work`
aliases used in stage argv.

The runner must expose those paths, translate aliases when the licensed
environment uses host paths, run from the work directory without network access,
and forward stdout, stderr, and exit status. Generated artifacts stay under the
supplied work path for framework inspection. SVTORTURE enforces a timeout around
the runner process. The runner must still terminate its licensed child
processes.

If the runner discovers after launch that the license service is unreachable,
it returns the reserved status 69 (`EX_UNAVAILABLE`). SVTORTURE normalizes it to
`skipped-unavailable`. Public export rejects runner configuration, license
variables, commercial images, and commercial results. VCS is the first
commercial adapter, but the policy code must work unchanged for every commercial
simulator regardless of name.

## Diagnostics and tests

Prefer source/line normalization. A locationless message/code rule belongs in
the owning `tool.toml` as `[[diagnostic_rules]]`, is scoped to one case by that
manifest, and receives separate review.

Add tests for:

- command construction, portable paths, target phase, and attempted-through
  phase;
- direct and cumulative evidence boundaries, including an unrelated later
  failure that must remain inconclusive;
- profile/capability boundaries and language mode;
- normal exit, timeout, signal/internal error, and backend failure ownership;
- diagnostic parsing, source mapping, and fallback behavior;
- image/ref/version provenance or wrapper request construction;
- metadata-driven CI/public exclusion.

Run `just smoke` and `just ci`.
