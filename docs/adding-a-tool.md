# Adding a tool

Every tool has a `tools/<name>/tool.toml` manifest listed by the thin
`tools/tools.toml` index and implements the adapter contract in
`src/svtorture/adapters/`. Adapters construct typed stages and normalize
diagnostics; they never decide conformance. Manifest paths such as `Dockerfile`,
recipe files, and local runner configuration are relative to that tool directory.

## Registration and profiles

Declare:

- stable ID/display name and adapter implementation;
- parser, elaborator, and/or simulator profiles with a cumulative
  `phase_ceiling` and ordered `direct_phases`;
- headline profile and effective language/revision mode;
- `distribution`, `execution`, `ci`, and `publish` policy;
- public upstream/default branch, Dockerfile, repository, and additional
  `recipe_files` where applicable.

No synthesis profile belongs in this project. A parser ceiling is `parse`, an
elaborator ceiling is `elaborate`, and a simulator ceiling is `simulate`; every
profile supports prerequisite phases cumulatively. List a phase as direct only
when the adapter has a command bounded at that phase. If no direct command exists,
the adapter uses the nearest later command and records that later boundary rather
than relabeling it.

## Open-source path

Open-source tools use `execution = "docker"`. Their adapter must use the case's
ordered sources, top, includes, defines, and arguments while preserving a
portable `$CASE`/`$WORK` argv. Images build only after `latest`, tag, branch, or
full SHA resolves to one exact commit.

The build captures source SHA, exact/nearest tags when available, reported
version, recipe hash, pinned base-image digest, platform, image ID, and pushed
repository digest. Runtime execution cannot use a host binary or network.
Nightly publication also probes the digest without registry credentials; the
GHCR package must permit anonymous manifest access so historical results remain
reproducible after CI credentials and artifacts expire.

## Commercial path

Commercial tools use `distribution = "commercial"`,
`execution = "local-wrapper"`, `ci = false`, and `publish = false`. Their
committed manifest names `runner_config = "runner.toml"`. Copy the adjacent
example with `just runner-config <tool>` and set its command plus an explicit
environment allowlist. The resulting `runner.toml` remains ignored by Git.

The local runner command accepts `--request <json>` and owns licensed-container
setup. Each name in `environment_allowlist` is both the only host variable
forwarded and a required readiness input, so an absent license endpoint is
`skipped-unavailable`.

A version-2 version request contains `kind = "version"`, `tool`, and the
adapter's `argv`. Execute that argv in the licensed environment and forward the
tool's stdout, stderr, and exit status unchanged; the first nonempty output line
becomes the reported version.

A normal execution request contains `tool`, `case`, `profile`, one `stage`, a
`mounts` object, and `execution_policy`. The stage provides its ID, target and
attempted-through phases, argv, portable argv, and timeout. `mounts.case` and
`mounts.work` are host paths corresponding to the `/case` read-only and `/work`
writable aliases used in stage argv. The runner must make those paths available,
translate the aliases when its environment uses host paths, run from the work
directory without network access, and forward stdout, stderr, and exit status.
Generated artifacts remain under the supplied work path for framework
inspection. SVTORTURE enforces the timeout around the runner process, but the
runner remains responsible for terminating its licensed child processes.

A runner that discovers an unreachable license service after launch returns the
protocol's reserved exit status 69 (`EX_UNAVAILABLE`), which is normalized to
`skipped-unavailable`. Runner configuration, license variables, commercial
images, and commercial results cannot pass the public export policy. VCS is only
the initial adapter; policy code must work unchanged for any differently named
commercial simulator.

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
