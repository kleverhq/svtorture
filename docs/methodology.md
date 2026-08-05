# Conformance methodology

## Authority and revision

IEEE Std 1800-2023 is the active authority. Requirement authors run the
repository annotator against their local PDF. Each requirement record identifies
a numeric chapter or alphabetic annex in `part`, a matching location, and at
least one complete corpus anchor. The first anchor cites the declared location;
additional anchors support rules that span several source blocks. Catalog
loading checks every citation against
`standards/ieee-1800-2023-anchors.json`, so it does not need the PDF or generated
corpus.

Each case names one primary normative requirement and states its applicability
to 1800-2012, 1800-2017, and 1800-2023. The rule from the selected revision sets
the expected result. Tool behavior, documentation, `sv-tests`, and other
simulators can help prioritize or corroborate a case, but they do not set its
oracle.

## Judgment

The phase pipeline is cumulative. `simulate` includes `elaborate`, which
includes `parse`, which includes `preprocess`. A tool profile declares its
highest reachable `phase_ceiling` and the phases with independently bounded
`direct_phases`. Each case oracle still names one target phase.

Evidence is **direct** when the command stops at that target. It is
**cumulative** when a later command proves the target oracle. A successful later
command proves earlier acceptance. A nonzero later command proves an earlier
rejection or required diagnostic only when normalized evidence identifies the
unique case anchor. Without that anchor, the result is inconclusive because the
framework cannot tell which phase rejected the source.

- Static acceptance requires a zero exit from a command that reaches the target.
- Simulation acceptance requires a zero runtime exit and exactly one
  `SVTORTURE_PASS:<case-id>` after all self-checks; compilation never substitutes
  for runtime evidence.
- Rejection requires a nonzero exit plus normalized evidence at the unique
  diagnostic anchor, or a separately reviewed adapter fallback for a tool that
  omits locations.
- A required diagnostic may be a warning or error, but must be tied to the
  intended construct; a successful warning path also needs its runtime marker.

A negative oracle requires evidence tied to the intended construct, either by a
location anchor or a separately reviewed adapter fallback. Timeouts, signals,
crashes, internal errors, launch failures, container failures, missing artifacts,
unrelated diagnostics, and marker mistakes do not meet it. Tool
crashes and timeouts are inconclusive tool observations. Backend or container
launch failures are harness errors.

Known-issue annotations provide context. They do not change a failure into a
pass.

## Headline metric

**Verified support in the covered corpus** counts normative requirements, not
cases or tags:

```text
applicable requirements whose selected mandatory variants all conform
----------------------------------------------------------------------
applicable requirements with selected cases at or below the profile phase ceiling
```

Current case mappings determine requirement coverage; the requirement catalog
does not store it. Exploratory cases do not score. A requirement is counted once
even when it has several variants. Nonconforming and inconclusive requirements
stay in the denominator but not the numerator. The dashboard presents
inconclusive evidence as Unclear rather than Pass or Fail. Unsupported, absent,
and not-applicable requirements are not verified. Any harness error invalidates
the profile metric.

Every displayed point includes numerator, denominator, revision, profile,
corpus manifest, completeness, exact tool commit/tags/version, image digest,
timestamp, and campaign ID. Corpus changes are visibly marked in Trends.

Each campaign stores four operands used for corpus trends. Requirements Coverage
is the number of unique cited standard anchors divided by eligible anchors. An
eligible anchor is any committed anchor except one that is waived and not cited
by a requirement. A cited anchor therefore remains covered even when it also
appears in a waiver. Requirements Density is the number of unique
requirement-to-anchor pairs divided by cited anchors. Cases Coverage is the
number of requirements linked as primary or related divided by all requirements.
Cases Density is the number of unique case-to-requirement pairs divided by linked
requirements.

The campaign stores the same operands for every chapter and annex, including
parts with zero values. Requirement breakdowns also store the number of
waiver-only anchors excluded in each part. When several parts are selected, the
dashboard sums their operands before applying the formula. The values describe
the full catalog and do not depend on tool, profile, suite, or result filters.
