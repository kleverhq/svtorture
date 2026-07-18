# Adding a tool

Every tool is registered in `tools/tools.toml` and implements the adapter
contract in `src/svtorture/adapters/`. Adapters construct typed stages and
normalize diagnostics; they never decide conformance.

## Registration and profiles

Declare:

- stable ID/display name and adapter implementation;
- parser, elaborator, and/or simulator profiles with exact phase capabilities;
- headline profile and effective language/revision mode;
- `distribution`, `execution`, `ci`, and `publish` policy;
- public upstream/default branch, Dockerfile, repository, and additional
  `recipe_files` where applicable.

No synthesis profile belongs in this project.

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
`execution = "local-wrapper"`, `ci = false`, and `publish = false`. Copy the
gitignored example with `just private-config`, point
`SVTORTURE_TOOL_CONFIG` at another private file if desired, and provide an argv
wrapper plus an explicit environment allowlist.

The wrapper accepts `--request <json>` and owns licensed-container setup. Each
name in `environment_allowlist` is both the only host variable forwarded and a
required readiness input, so an absent license endpoint is
`skipped-unavailable`. The same request protocol uses `kind = "version"` with
the adapter's version argv to capture the private tool version. A wrapper that
discovers an unreachable license service after launch returns the protocol's
reserved exit status 69 (`EX_UNAVAILABLE`), which is normalized to the same
`skipped-unavailable` result. Wrapper configuration, license variables,
commercial images, and private results cannot pass the public export policy.
VCS is only the initial adapter; policy code must work unchanged for any
differently named commercial simulator.

## Diagnostics and tests

Prefer source/line normalization. A locationless message/code rule belongs in
`tools/diagnostic-rules.toml`, is scoped to adapter and case, and receives
separate review.

Add tests for:

- command construction and portable paths;
- profile/capability boundaries and language mode;
- normal exit, timeout, signal/internal error, and backend failure ownership;
- diagnostic parsing, source mapping, and fallback behavior;
- image/ref/version provenance or wrapper request construction;
- metadata-driven CI/public exclusion.

Run `just smoke` and `just ci`.
