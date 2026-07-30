# About SVTORTURE

SVTORTURE is a standards-driven SystemVerilog conformance framework. It turns
normative language into traceable requirements, executable cases, normalized
tool observations, and reproducible campaign evidence.

This is a visual orientation, not a second specification of framework behavior.
See [architecture](../architecture.md), [methodology](../methodology.md), and
[reproduction](../reproduction.md) for the authoritative details.

## Overview

Broad compatibility suites are valuable. Inspired by `sv-tests`, SVTORTURE goes
deeper by preserving the chain from one normative rule to one conformance
judgment. It is neither a fork nor a replacement: its focus is exact phases,
shared oracles, and reproducible evidence.

![Flow from the IEEE standard through requirements and cases to campaign evidence](assets/standards-to-evidence.drawio.png)

The standard supplies the expectation; tools supply observations. IEEE
1800-2023 is the authoritative corpus. Annotation assigns stable anchors to
source blocks before requirements or cases are written.

## Requirements

A requirement is a concise, falsifiable statement distilled from one or more
anchored paragraphs, list items, tables, figures, or other source blocks. It
keeps its clause, tags, anchor links, related-clause references, and
applicability to IEEE 1800-2012, 1800-2017, and 1800-2023.

![Traceable requirements linked to standard anchors and corpus metrics](assets/traceable-requirements.drawio.png)

- **Requirements Coverage** is unique referenced anchors divided by all
  standard anchors.
- **Requirements Density** is unique requirement–anchor links divided by
  covered anchors.

See [annotation](../annotation.md) for anchor construction and
[methodology](../methodology.md) for metric semantics.

## Cases

A case materializes one primary requirement as minimal, tool-neutral source and
an exact oracle for one target phase. It can require successful preprocessing,
parsing, elaboration, or simulation; a simulation PASS marker; or nonzero
rejection with a matching diagnostic at the exact case anchor. A diagnostic
oracle separately requires a matching diagnostic at that exact anchor without
requiring rejection. Related requirements preserve context without changing the
primary scoring unit.

![Executable cases pairing source code with phase-specific oracles](assets/executable-cases.drawio.png)

- **Cases Coverage** is unique requirements linked from cases divided by all
  catalog requirements.
- **Cases Density** is unique case–requirement links divided by covered
  requirements.

Cases provide observations. The headline pass rate counts requirements whose
selected mandatory variants all conform; it is not a raw passed-case ratio. See
[adding a case](../adding-a-case.md) for the complete metadata and source
workflow.

## Tools

Preprocessing, parsing, elaboration, and simulation form a cumulative pipeline.
A tool profile declares its deepest phase and which phases it observes directly.
SVTORTURE uses the deepest suitable command and records evidence as direct,
cumulative, or not observed. A case runs only when its target phase is within
the profile ceiling and its selected language revision applies.

![Cumulative tool phases and the checks that decide case applicability](assets/tool-applicability.drawio.png)

Open-source integrations resolve a moving upstream reference to an immutable
revision before the project-controlled Docker build and can contribute to public
evidence. Commercial integrations use ignored machine-local runner configuration
and remain local. See [adding a tool](../adding-a-tool.md) for the portable/private
boundary.

## Campaigns

A campaign is the immutable evidence bundle for one selected grid of tools,
profiles, and cases. The launcher resolves tool identities and runs independent
combinations while keeping stages within one combination sequential.

![Campaign evidence flowing into dashboard investigation and reproduction](assets/campaign-to-dashboard.drawio.png)

For runnable observations, the bundle retains versions and source revisions,
exact Docker image identity or the external compatible-runner path, commands and
phases, diagnostics, bounded output excerpts, full-stream hashes, normalized
judgments, and reproduction data. Synthetic statuses such as unsupported,
inapplicable, unavailable, or preparation failure remain explicit but may not be
replayable. Commercial runner contents and commands are never embedded. Full
transient logs stay local.

## Dashboard

The dashboard is a static evidence browser, not a live database and not a
scoreboard detached from its corpus. It connects pass rate and completeness to
requirements, anchors, cases, source, diagnostics, outputs, campaign provenance,
and historical trends. A compact reproduction command helps turn an observed
difference into a focused bug report.

Periodic public campaigns can track resolved upstream mainline revisions. Local
exports may include commercial evidence, but the public export policy excludes
it. The useful unit is not a green cell: it is an expectation, an observation,
and the traceable evidence connecting them.

The `*.drawio.png` illustrations embed their Draw.io models and can be opened
for editing directly in Draw.io Desktop.
