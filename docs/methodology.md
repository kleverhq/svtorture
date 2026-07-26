# Conformance methodology

## Authority and revision

IEEE Std 1800-2023 is the active authority. Requirement authors use the
repository-owned annotator to materialize a local corpus from their PDF.
Requirement records identify a clause and a nonempty list of complete corpus
anchors; the first anchor cites the declared clause and later anchors support
rules that span blocks. Catalog loading verifies every citation against the
committed `standards/ieee-1800-2023-anchors.json` without requiring the PDF or
generated corpus.
Cases identify one primary normative requirement. Applicability to 1800-2012,
1800-2017, and 1800-2023 is explicit and complete.

The expected result comes from the selected revision's rule. Tool behavior,
documentation, `sv-tests`, and other simulators may corroborate or prioritize a
case but never define its oracle.

## Judgment

The pipeline is cumulative: `simulate` reaches `elaborate`, which reaches
`parse`, which reaches `preprocess`. A tool profile declares its latest reachable
`phase_ceiling` and the phases for which its adapter has independently bounded
`direct_phases`. The case oracle still names one exact target.

Evidence is **direct** when the command stops at that target and **cumulative**
when a later-capable command proves the target oracle. A successful later command
proves earlier acceptance. A nonzero later command proves an earlier rejection or
required diagnostic only when normalized evidence identifies the unique case
anchor. An unrelated later failure is inconclusive because it does not establish
which phase rejected the source.

- Static acceptance requires a zero exit from a command that reaches the target.
- Simulation acceptance requires a zero runtime exit and exactly one
  `SVTORTURE_PASS:<case-id>` after all self-checks; compilation never substitutes
  for runtime evidence.
- Rejection requires a nonzero exit plus normalized evidence at the unique
  diagnostic anchor, or a separately reviewed adapter fallback for a tool that
  omits locations.
- A required diagnostic may be a warning or error, but must be tied to the
  intended construct; a successful warning path also needs its runtime marker.

Timeouts, signals, crashes, internal errors, launch failures, container failures,
missing artifacts, unrelated diagnostics, and marker mistakes never satisfy a
negative oracle. Tool crashes/timeouts are inconclusive tool observations;
backend/container launch failures are harness errors.

Known-issue annotations add context only. They do not change a failure into a
pass.

## Headline metric

**Verified support in the covered corpus** counts normative requirements, not
cases or tags:

```text
applicable requirements whose selected mandatory variants all conform
----------------------------------------------------------------------
applicable requirements with selected cases at or below the profile phase ceiling
```

Requirement coverage is computed from current case mappings; it is not stored in
the requirement catalog. Exploratory cases do not score. A requirement is
counted once even with several variants. Nonconforming and inconclusive
requirements remain in the denominator but do not enter the numerator;
inconclusive evidence is neither Pass nor Fail and is presented as Unclear.
Unsupported, absent, and not-applicable requirements do not become verified.
Any harness error invalidates the profile metric.

Every displayed point includes numerator, denominator, revision, profile,
corpus manifest, completeness, exact tool commit/tags/version, image digest,
timestamp, and campaign ID. Corpus changes are visibly marked in Trends.

Each campaign also freezes four corpus-wide trend operands. Requirements
Coverage is the number of unique referenced standard anchors divided by every
anchor in the committed index; Requirements Density is unique
requirement–anchor pairs divided by referenced anchors. Cases Coverage is the
number of requirements linked as primary or related divided by all requirements;
Cases Density is unique case–requirement pairs divided by linked requirements.
Campaigns preserve the same operands for every chapter and annex, including
zero rows. Selecting several standard parts sums their operands before applying
the formula. These values describe the complete catalog and are independent of
tool, profile, suite selection, and result filters.
