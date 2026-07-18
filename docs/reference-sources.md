# Reference checkout audit

Both user-supplied references were inspected read-only on 2026-07-18.

| Reference | Exact Git commit | Dirty state | Relevant material inspected |
|---|---|---:|---|
| `sv-tests` | `5932688f54a00d8dac4265aacaeca9e043da3e05` (`v0.0-10816-g5932688f`) | clean | runner base/classes, Slang/Icarus/Verilator runners, report/history assets, metadata and runner configuration |
| `verilator-torture` | `8caf56f527527ae931e5efef5fed311aef625bc1` | clean | strict case metadata, process control, campaign/result provenance, methodology/revision docs, dashboards, build runner, VCS helper paths, chapter cases |

Ideas retained include small clause-indexed cases, explicit runner capabilities,
bounded process execution, exact source identity, immutable result manifests, and
history-aware reporting. SVTORTURE does not fork either architecture: it adds a
requirement coverage unit, generic cross-tool evaluation, strict target evidence,
revision-aware profiles, Docker-only public execution, name-independent
commercial/public policy, and a versioned campaign/dashboard contract.

Seven seed cases preserve an independently reviewed hypothesis from
`verilator-torture` while using rewritten tool-neutral source and explicit
attribution. That checkout contained no license file; every affected case records
this fact and is independently rewritten rather than copied. `sv-tests` guided
tool invocation and prioritization only and defines no oracle.

The standards claims were checked against locally installed copies of IEEE
1800-2012, IEEE 1800-2017, and IEEE 1800-2023. The repository contains only
clause citations and project-owned summaries. VCS invocation flags were checked
against the locally installed S-2021.09-1 documentation. Slang command behavior
was checked against its official command-line reference.
