# Adding a case

Start from [`templates/case/`](../templates/case/) and place the finished case in
`cases/<stable-kebab-id>/`. `suites/all.toml` selects it automatically through
`["*"]`; add it to `suites/smoke.toml` only when it adds a fast, distinct smoke
path.

## 1. Map the requirement

Add or reuse an entry in `standards/requirements/chapter-NN.toml` or
`standards/requirements/annex-X.toml`. Numeric chapters use a string `part`, such
as `"4"`. Annexes use a letter such as `"A"`, with requirement IDs such as
`SV-2023-A-FORMAL-SYNTAX`.

When adding or revising a requirement, configure the PDF path as described in
`annotation.md` and run `just annotate`. Derive the rule from the matching
`txt/<PART>.txt` blocks, such as `txt/04.txt` or `txt/A.txt`. The entry needs a
stable ID, its 2023 part and location, at least one anchor, any related locations,
controlled tags, and a rule for every supported revision. Copy complete anchor
values from `standards/ieee-1800-2023-anchors.json`. Put the main anchor for the
declared location first, followed by supporting blocks. If an anchor has a
visual-review marker, inspect that PDF page before writing the oracle.

When creating a requirement document for a new chapter or annex, add its
standard part to `standards/index.toml`. All requirements in the inventory must
be normative and testable in principle. Case mappings, not the requirement
records, determine coverage.

The case names exactly one primary requirement. Related requirements are context,
not scoring units. Reuse tags from `standards/tags.toml`; add a concise registry
entry when a genuinely new semantic category is needed.

## 2. Select revision, phase, and oracle

Declare applicability for 2012, 2017, and 2023. Use `not-assessed` when the rule
has not been checked for a revision. Choose the earliest phase that measures the
required behavior: `preprocess`, `parse`, `elaborate`, or `simulate`.

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

A case does not need to pass every tool, but it must produce trustworthy
evidence. Reviewers reject ambiguous anchors, non-minimal stimulus, per-tool
expectations, unsafe paths, incomplete revision maps, runtime tests without
self-checks, and oracles weakened to accommodate a current defect.
