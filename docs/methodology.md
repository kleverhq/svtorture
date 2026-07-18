# Conformance methodology

## Authority and revision

IEEE Std 1800-2023 is the active authority. Requirement records identify a
clause and a short project-owned paragraph anchor; cases identify one primary
normative requirement. Applicability to 1800-2012, 1800-2017, and 1800-2023 is
explicit and complete.

The expected result comes from the selected revision's rule. Tool behavior,
documentation, `sv-tests`, and other simulators may corroborate or prioritize a
case but never define its oracle.

## Judgment

The target phase is exact. Parse success does not stand in for elaboration, and
elaboration does not stand in for simulation.

- Static acceptance requires a zero exit at the declared target phase.
- Simulation acceptance requires a zero runtime exit and exactly one
  `SVTORTURE_PASS:<case-id>` after all self-checks.
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
applicable covered requirements whose every mandatory variant conforms
-----------------------------------------------------------------------
all applicable covered normative requirements in the profile phase scope
```

Exploratory cases do not score. A requirement is counted once even with several
variants. Nonconforming, inconclusive, unsupported, absent, crashed, or timed-out
evidence does not enter the numerator. Not-applicable and non-testable/deferred
requirements are excluded. Any harness error invalidates the profile metric.

Every displayed point includes numerator, denominator, revision, profile,
corpus manifest, completeness, exact tool commit/tags/version, image digest,
timestamp, and campaign ID. Corpus changes are visibly marked in history.
