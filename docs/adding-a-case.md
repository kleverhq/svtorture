# Adding a case

Start from [`templates/case/`](../templates/case/) and place the finished case in
`cases/<stable-kebab-id>/`. `suites/all.toml` selects it automatically through
`["*"]`; add it to `suites/smoke.toml` only when it adds a fast, distinct smoke
path.

## 1. Map the requirement

Add or reuse one entry in `standards/requirements/chapter-NN.toml` or
`standards/requirements/annex-X.toml`. Numeric chapters use a string `part` such
as `"4"`; annexes use a letter such as `"A"` and requirement IDs such as
`SV-2023-A-FORMAL-SYNTAX`. When adding or revising that requirement,
configure the PDF path as described in `annotation.md`, run `just annotate`, and
derive the expected rule from the matching generated `txt/<PART>.txt` blocks,
such as `txt/04.txt` or `txt/A.txt`. The entry needs one stable ID, its 2023
`part` and matching location, a nonempty `anchors` list, related locations,
controlled tags, and a rule for every supported revision. Use complete values
from `standards/ieee-1800-2023-anchors.json`, with the declared location's main
anchor first and any supporting blocks after it. If a cited block has a
visual-review marker, inspect its PDF page before defining the oracle. When
creating a new requirement document, add its standard part to
`standards/index.toml`.
Requirements in this inventory are normative and testable in principle by
definition. Coverage is derived from case mappings rather than stored.

The case names exactly one primary requirement. Related requirements are context,
not scoring units. Reuse tags from `standards/tags.toml`; add a concise registry
entry when a genuinely new semantic category is needed.

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

## 4. Validate

```text
just schemas
just smoke
just ci
```

A case need not pass every tool. It must produce trustworthy evidence. Review
rejects ambiguous anchors, non-minimal stimulus, per-tool expectations, unsafe
paths, incomplete revision maps, non-self-checking runtime tests, and any oracle
weakened to accommodate a current defect.
