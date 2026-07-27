# Standards catalog

`ieee-1800-2023-anchors.json` is the committed runtime index used to validate
requirement citations. `index.toml` lists maintained standard parts, `requirements/`
stores `chapter-NN.toml` and `annex-X.toml` requirement documents, and `tags.toml`
defines the shared
vocabulary used by requirements and cases. Normal setup, validation, execution,
and publication need neither a PDF nor generated standard text.

`ieee-1800-2023-annotate/` contains the repository-owned annotator. When adding
or revising a requirement, configure `.env.local` and run `just annotate` to
materialize the ignored corpus. Read the matching generated `txt/NN.txt` blocks
and inspect the PDF for any visual-review marker. Use complete anchors from the
committed index. If an intentional annotator change modifies the index, run
`just annotate-update-anchors` and commit the result.

See `../docs/annotation.md` for prerequisites, targets, verification, and CI
behavior.
