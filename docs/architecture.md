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
                                      ▼
                          static dashboard dataset
```

`models.py` defines strict, frozen, unknown-field-rejecting public models.
`catalog.py` validates requirement citations against the committed anchor index,
then validates cross-references, safe paths, diagnostic anchors, marker
uniqueness, source hashes, and the seed-corpus composition. The source under
`standards/ieee-1800-2023-annotate/` materializes that index from a user-supplied
PDF, but neither the annotator nor its generated text is in this runtime data
flow. Tool profiles declare a cumulative phase ceiling plus the command boundaries the
adapter can assess directly. Adapters only declare commands, the furthest phase
each command attempts, and diagnostic normalization. `executor.py` runs argv
arrays in isolated work directories and records bounded excerpts plus full-stream
hashes. `evaluator.py` alone compares observations to the exact case oracle and
records whether the evidence is direct or cumulative.

If either bounded excerpt is truncated, the evaluator records an inconclusive
`output-truncated` result; retained output can therefore never hide a second
pass marker or an internal-error diagnostic and create a false pass.

Open-source execution is always Docker-backed. Runtime containers have no
network, a read-only root filesystem, dropped capabilities, PID/memory bounds,
read-only case input, and a per-case writable work mount. Full logs and generated
artifacts remain under `.svtorture/work`; campaigns contain only sanitized,
bounded evidence.

Commercial execution uses the same version-2 `ExecutionPlan`,
`StageObservation`, and `NormalizedResult` contracts. A plan records its target
phase; each stage and observation records `attempted_through_phase`; and the
result records `direct`, `cumulative`, or `not-observed` evidence. An ignored
per-tool `runner.toml` selects a local command that receives the versioned JSON
wrapper request. Distribution, CI, and publication policy comes from the
committed per-tool manifest, so
publishers and workflows never infer it from an adapter name.

Campaigns include a full result grid for every selected case and profile plus
the exact aggregate and per-chapter/annex requirement/case Coverage and Density
operands computed from the full catalog at collection time. Loading rejects duplicate/missing results,
mismatched case or selection manifests, and corpus metrics that no longer match
the catalog. Aggregation records expected and missing tools rather than quietly
changing completeness. If nightly collection fails before an immutable source
and image identity exists, its private artifact still contains a per-case grid
with explicit `tool-preparation-failure` harness results (while preserving
structural unsupported/not-applicable judgments). Aggregation removes that
unpublishable placeholder identity and exposes the tool as missing, so no
preparation failure can be mistaken for measured conformance.

Public export additionally re-evaluates every recorded observation, requires a
clean matching checkout inside the same GitHub Actions repository/run/SHA,
checks tool definitions against the committed registry, requires pullable GHCR
digests, and scans the complete compact dataset for private paths and common
credential forms.
