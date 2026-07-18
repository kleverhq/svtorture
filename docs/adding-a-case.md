# Adding a case

Start from [`templates/case/`](../templates/case/) and place the finished case in
`cases/<stable-kebab-id>/`. Add its ID to `suites/all.toml` and to
`suites/smoke.toml` only when it adds a fast, distinct smoke path.

## 1. Map the requirement

Add or reuse one entry in `standards/requirements.toml`. It needs one stable ID,
the 2023 chapter/clause and concise anchor, normativity, testability, coverage
state, related clauses, tags, and a rule for every supported revision. Do not
copy substantial IEEE text.

The case names exactly one primary requirement. Related requirements are context,
not scoring units.

## 2. Select revision, phase, and oracle

Declare applicability for 2012, 2017, and 2023. Use `not-assessed` rather than
guessing. Choose the earliest exact phase whose required behavior is measured:
`preprocess`, `parse`, `elaborate`, or `simulate`.

- legal static source: `accept` + `phase-exit`;
- self-checking runtime source: `accept` + `runtime-pass-marker`;
- illegal source: `reject` + `diagnostic-at-anchor`;
- required warning/error: `diagnostic` + `diagnostic-at-anchor`.

A negative/diagnostic source contains exactly one
`SVTORTURE_DIAG_ANCHOR:<case-id>`. A simulation pass path emits exactly one
`SVTORTURE_PASS:<case-id>` after all checks, calls `$fatal` for every wrong value,
and terminates explicitly.

## 3. Design minimal source

Change one semantic dimension at a time. Keep ordered sources short,
deterministic, tool-neutral, and independent of wall-clock time or randomness.
Record `top`, include directories, defines, arguments, and resource limits in
metadata. Tool flags and diagnostic wording do not belong here.

Multi-file cases put package/compilation-unit order directly in `sources`.
Negative evidence should locate the intended token or construct, not a later
cascade.

## 4. Record provenance

Use `original`, `adapted`, or `inspired`. Adapted/inspired cases require the
source URL or stable reference label, full source commit/fingerprint, path,
license note, and a clear account of the rewrite. Existing results are not an
oracle.

## 5. Validate

```text
just schemas
just fixture
just smoke
just ci
```

A case need not pass every tool. It must produce trustworthy evidence. Review
rejects ambiguous anchors, non-minimal stimulus, per-tool expectations, unsafe
paths, incomplete revision maps, non-self-checking runtime tests, and any oracle
weakened to accommodate a current defect.
