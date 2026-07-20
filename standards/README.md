# Standards catalog

`ieee-1800-2023-annotated/` is the pinned annotated-standard submodule used for
all 1800-2023 interpretation and citations. `index.toml` lists maintained
chapters, `requirements/` stores one requirement document per chapter, and
`tags.toml` defines the shared vocabulary used by requirements and cases.

Initialize the source after cloning with:

```text
git submodule update --init --recursive
```

Requirement `anchors` must be complete values from the submodule's
`anchors.json`; catalog validation rejects missing citations. Read the matching
`txt/NN.txt` blocks and inspect the pinned PDF for any visual-review marker. Do
not edit submodule contents from this repository.
