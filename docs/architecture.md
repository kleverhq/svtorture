# Architecture

SVTORTURE keeps the units of evidence distinct:

```text
licensed IEEE PDF (local path or CI secret URL)
          │ optional authoring path
          ▼
standards/ieee-1800-2023-annotate/annotate.py
          │ materializes ignored TXT + anchors.json
          ▼ explicit annotate-update-anchors
standards/ieee-1800-2023-anchors.json
          │ validates citations at runtime
          ▼
standards/index.toml + requirements/{chapter-NN,annex-X}.toml
          │
          ▼
cases/<id>/case.toml + ordered sources
          │
          ▼
tools/tools.toml ──► tools/*/tool.toml ──► adapter ──► typed ExecutionPlan
                                      │
                                      ▼
                              StageObservation[]
                                      │
                                      ▼
                              generic evaluator
                                      │
                                      ▼
                         immutable Campaign JSON
                                      │
                                      ▼ derived projection
                    version-6 portable campaign bundle
                                      │
                                      ▼ lazy static resources
                           React evidence dashboard
```

`models.py` defines strict, frozen public models that reject unknown fields.
`catalog.py` checks requirement citations against the committed anchor index. It
also checks cross-references, safe paths, diagnostic anchors, marker uniqueness,
source hashes, and the seed corpus. The annotator under
`standards/ieee-1800-2023-annotate/` builds the anchor index from a user-supplied
PDF. Neither the annotator nor its generated text is part of runtime execution.

A tool profile declares a cumulative phase ceiling and the command boundaries
that its adapter can assess directly. Adapters declare commands, the furthest
phase attempted by each command, and diagnostic normalization. `executor.py`
runs argv arrays in isolated work directories and records bounded excerpts with
full-stream hashes. Only `evaluator.py` compares those observations with the
case oracle and labels the evidence as direct or cumulative.

When either excerpt is truncated, the evaluator returns the inconclusive reason
`output-truncated`. It does not evaluate partial text that might omit a second
pass marker or an internal-error diagnostic.

Open-source tools always run in Docker. Runtime containers have no network,
use a read-only root filesystem, drop capabilities, and enforce PID and memory
bounds. Case input is read-only, while each case receives a writable work mount.
Full logs and generated artifacts stay under `.svtorture/work`; campaigns keep
only sanitized, bounded evidence.

Commercial execution uses the same version-2 `ExecutionPlan`,
`StageObservation`, and `NormalizedResult` contracts. A plan records its target
phase. Each stage and observation records `attempted_through_phase`, and the
result records `direct`, `cumulative`, or `not-observed` evidence. An ignored
per-tool `runner.toml` selects the local command that receives the versioned JSON
request. The committed tool manifest defines distribution, CI, and publication
policy; publishers and workflows do not infer policy from an adapter name.

Tools are prepared sequentially. Campaign execution then sends every selected
tool/profile/case combination to one bounded thread pool. The threads wait for
Docker or local-runner processes; they do not perform CPU-bound Python work.
Combinations can run concurrently, but stages within one combination run in
order and share its isolated work directory. One worker count limits the whole
campaign. Automatic mode uses the CPUs available to the process. Operators can
lower the count when memory or license seats impose a tighter limit.

A campaign contains one result for every selected case and profile. It also
stores the aggregate and per-part operands for Requirements Coverage,
Requirements Density, Cases Coverage, and Cases Density. These operands come
from the full catalog at collection time. Loading rejects duplicate or missing
results, mismatched case or selection manifests, and corpus metrics that do not
match the catalog.

Aggregation records both expected and missing tools. If nightly preparation
fails before an immutable source and image identity exists, the private artifact
still contains a per-case grid with `tool-preparation-failure` harness
results. Structural `unsupported` and `not-applicable` judgments are preserved.
Aggregation removes the placeholder identity from public data and reports the
tool as missing, so preparation failures are not presented as conformance
measurements.

Before public export, the publisher re-evaluates every recorded observation. It
requires a clean matching checkout from the same GitHub Actions
repository/run/SHA, checks tool definitions against the committed registry,
requires pullable GHCR digests, and scans the compact bundle projection for
private paths and common credential forms.

The canonical schema-version-5 `Campaign` remains the complete local evidence
record. `bundle.py` derives strict schema-version-6 manifest, catalog, compact
verdict, and case-centric evidence resources without changing evaluator or
metric semantics. Local assembly writes `index.json` and `trends.json` for any
number of validated bundle directories or ZIPs. The browser loads those small
entry resources first, then one selected manifest/catalog/verdict set, and only
loads an evidence shard when a case detail is opened.
