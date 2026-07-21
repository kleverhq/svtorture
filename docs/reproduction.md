# Reproduction

A campaign records the corpus commit/dirty state, requirement/case/selection
manifest hashes, exact case content hashes, tool source selection, reported
version, image and base-image digests, profiles and their phase ceilings, target phases, direct/cumulative evidence
modes, attempted-through phases, portable commands, normalized diagnostics,
bounded excerpts, and full-stream hashes.

Replay one result:

```text
just reproduce ".svtorture/campaigns/<id>/campaign.json" verilator simulator ch11-addition-context-width
```

The first argument may also be the credential-free HTTPS URL copied from a
public result. SVTORTURE bounds the download, validates the campaign schema and
manifests, then rechecks the recorded judgment from its observations before
replay. Public result cards use the immutable campaign document on the
`gh-pages` branch, for example:

```text
just reproduce "https://raw.githubusercontent.com/<owner>/<repo>/gh-pages/history/campaigns/<id>.json" verilator simulator ch11-addition-context-width
```

Replay first verifies the campaign and current corpus. If the recorded corpus
commit differs, it creates a detached git worktree. Requirement anchors in that
worktree are checked against the current checkout's committed anchor index, so
replay never needs the PDF or materialized annotated text. It then uses the recorded immutable
public image reference, attempts to pull it, and only then rebuilds
from the exact tool SHA, matching recipe hash, and recorded base-image digest.
The normalized status/reason is compared and platform differences are reported.

Private tools require the same local wrapper that their campaign used; no private
configuration is embedded in the campaign.

Full stage logs and generated artifacts are transient under `.svtorture/work`.
Public reproduction does not depend on them: the case, exact image/rebuild
identity, commands, bounded evidence, and judgment survive in the campaign.
