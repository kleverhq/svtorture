# Standards catalog

`ieee-1800-2023-anchors.json` is the committed runtime index used to validate
requirement citations. `index.toml` lists maintained standard parts, `requirements/`
stores `chapter-NN.toml` and `annex-X.toml` requirement documents, and `tags.toml`
defines the shared vocabulary used by requirements and cases.

The requirement-loop publication also supplies three JSON sidecar collections:
`waivers/` records why source anchors were not materialized as independent
requirements, `materialization-hints/` records guidance for future cases, and
`historical-evidence/` records IEEE 1800-2012 and IEEE 1800-2017 refinement
evidence. These sidecars cover chapters 3–41 and annexes A–Q. They are retained
for review and case authoring but are not loaded into the runtime catalog and do
not affect coverage, scoring, bundles, or the dashboard. Extraction session
manifests are intentionally not retained.

The consolidated publication contains 6,719 requirements and 1,900 waivers. Its
files were copied without semantic modification from the final requirement-loop
runs; the 12 earlier case-facing requirements were deduplicated by remapping
those cases to the corresponding consolidated records.

Normal setup, validation, execution, and publication need neither a PDF nor
generated standard text.

`ieee-1800-2023-annotate/` contains the repository-owned annotator. When adding
or revising a requirement, configure `.env.local` and run `just annotate` to
materialize the ignored corpus. Read the matching generated `txt/NN.txt` blocks
and inspect the PDF for any visual-review marker. Use complete anchors from the
committed index. If an intentional annotator change modifies the index, run
`just annotate-update-anchors` and commit the result.

See `../docs/annotation.md` for prerequisites, targets, verification, and CI
behavior.
