# Reproduction

A campaign records the corpus commit and dirty state, manifest hashes for
requirements, cases, and selections, and aggregate and per-part Coverage and
Density operands. It also records case content hashes, tool source selection,
reported version, image and base-image digests, profiles, phase ceilings, target
and attempted-through phases, portable commands, normalized diagnostics,
bounded excerpts, and full-stream hashes. Evidence mode is `direct`,
`cumulative`, or `not-observed`. Synthetic unsupported, unavailable, and
inapplicable results use `not-observed` and have no attempted-through
observation.

Replay one result:

```text
just reproduce ".svtorture/campaigns/<id>/campaign.json" verilator simulator ch11-addition-context-width
```

The first argument may instead be a local portable campaign ZIP, an unpacked
bundle or `manifest.json`, or a credential-free HTTPS manifest URL. Public
results use the immutable campaign ZIP attached to their GitHub Release:

```text
just reproduce "https://github.com/<owner>/<repo>/releases/download/campaign-<id>/svtorture-campaign-<id>.zip" verilator simulator ch11-addition-context-width
```

SVTORTURE bounds remote downloads and archive members, rejects unsafe ZIP paths,
and verifies the manifest plus the selected catalog, verdict, and evidence
resources before replay. It reads only the evidence shard containing the
requested result and recalculates the recorded judgment from its observations.

Replay then verifies the selected bundle identities against the current corpus.
If the recorded corpus commit differs from the checkout, SVTORTURE creates a
detached Git worktree. It checks requirement anchors from that worktree against
the committed anchor index in the current checkout; replay does not need the PDF
or generated annotation text.

SVTORTURE first checks for the recorded immutable public image locally. If it is
absent, the framework tries to pull it. If the pull fails, it rebuilds from the
recorded tool SHA, matching recipe hash, and base-image digest. It compares the
normalized status and reason and reports platform differences.

Commercial tools require a compatible local runner command configured by the
current checkout's ignored per-tool `runner.toml`; no runner configuration is
embedded in the campaign.

The stage logs and generated artifacts from the recorded campaign stay under
`.svtorture/work` and are not replay inputs. Replay writes its own logs and
artifacts under `.svtorture/reproduce-work`. The campaign retains the repository
commit, case identity and content hash, image or rebuild identity, commands,
bounded evidence, and judgment. Replay obtains the source from the recorded
repository checkout.
