# Standards catalog

`ieee-1800-2023-anchors.json` is the vendored runtime index used to validate
requirement citations. `index.toml` lists maintained chapters, `requirements/`
stores one requirement document per chapter, and `tags.toml` defines the shared
vocabulary used by requirements and cases. Normal setup, validation, execution,
and publication do not require the annotated-standard submodule.

When adding or revising a requirement, initialize the authoring corpus with:

```text
git submodule update --init standards/ieee-1800-2023-annotated
```

Read the matching `txt/NN.txt` blocks and inspect the pinned PDF for any
visual-review marker. Requirement `anchors` must be complete values from the
vendored index. When the submodule is initialized, pre-commit verifies that its
`anchors.json` is byte-for-byte identical to the vendored copy. Do not edit
submodule contents from this repository.
