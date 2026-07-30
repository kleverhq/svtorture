# About SVTORTURE

SVTORTURE tests SystemVerilog tools against requirements derived from the
standard. A campaign records the cases that ran, the tool observations, and the
information needed to inspect or replay a result.

This page is a short visual guide. The detailed rules live in
[architecture](../architecture.md), [methodology](../methodology.md), and
[reproduction](../reproduction.md).

## Overview

Compatibility suites such as `sv-tests` cover many language features and tools.
SVTORTURE focuses on the evidence behind each result. It is not a fork or
replacement. Each case has an explicit target phase and oracle, and every result
can be traced back to a requirement.

![Diagram of the IEEE standard, requirements, cases, tool profiles, campaign, and dashboard](assets/standards-to-evidence.drawio.png)

The standard defines expected behavior; tools provide observations. IEEE
1800-2023 supplies the normative text. The annotator assigns stable anchors to
source blocks before requirements or cases are written.

## Requirements

A requirement is a testable statement supported by one or more anchored source
blocks, such as paragraphs, list items, tables, or figures. Its metadata includes
the clause, tags, anchor links, related clauses, and applicability to IEEE
1800-2012, 1800-2017, and 1800-2023.

![Diagram linking standard anchors to a requirement and corpus metrics](assets/traceable-requirements.drawio.png)

Requirements Coverage is the number of unique cited anchors divided by all
standard anchors. Requirements Density is the number of unique
requirement-to-anchor links divided by cited anchors.

See [annotation](../annotation.md) for anchor construction and
[methodology](../methodology.md) for the metric definitions.

## Cases

A case turns one primary requirement into minimal, tool-neutral source and an
oracle for a specific phase. The source may need to preprocess, parse, elaborate,
simulate, or fail with a matching diagnostic at the exact case anchor. A
diagnostic oracle can require that message without requiring a nonzero exit.
Related requirements record additional context but do not change which
requirement is scored.

![Diagram linking case source and oracle to accepted and rejected outcomes](assets/executable-cases.drawio.png)

Cases Coverage is the number of unique requirements linked from cases divided by
all catalog requirements. Cases Density is the number of unique
case-to-requirement links divided by linked requirements.

The dashboard does not calculate the headline pass rate from raw case totals. It
counts a requirement only when all selected mandatory variants conform. See
[adding a case](../adding-a-case.md) for the metadata and source workflow.

## Tools

Tool phases are cumulative: parsing includes preprocessing, elaboration includes
parsing, and simulation includes elaboration. A profile states its maximum phase
and which phases it observes directly. The runner uses the deepest suitable
command and marks the evidence as direct, cumulative, or not observed. It skips
a case when the target phase or selected language revision does not apply.

![Diagram of cumulative tool phases and case applicability checks](assets/tool-applicability.drawio.png)

For an open-source integration, SVTORTURE resolves the upstream reference to an
immutable revision and builds the project Docker image. These results can be
published. An ignored machine-local configuration invokes a commercial runner,
and those results stay local. See [adding a tool](../adding-a-tool.md) for the
boundary between committed and local configuration.

## Campaigns

A campaign contains the results for a selected set of tools, profiles, and cases.
Once written, the campaign record does not change. The runner schedules
combinations independently but executes the stages of each combination in order.

![Diagram of campaign contents and dashboard uses](assets/campaign-to-dashboard.drawio.png)

Runnable results retain the source revision, reported version, exact Docker image
identity or external runner path, commands, diagnostics, bounded output excerpts,
full-stream hashes, and replay data. Synthetic statuses such as unsupported,
inapplicable, unavailable, or preparation failure remain visible even when they
cannot be replayed. Commercial runner contents and commands are not embedded.
Full logs stay local.

## Dashboard

The dashboard reads static campaign exports. It has no application server or
live database, and every score stays linked to its requirements and cases. Users
can inspect pass rate, completeness, source, diagnostics, output, campaign
provenance, and historical trends. Runnable results include a replay command
that can be attached to a bug report.

Public campaigns can periodically test resolved upstream mainline revisions.
Local exports may include commercial results, but the public export policy
removes them.

The `*.drawio.png` illustrations embed their Draw.io models and can be opened in
Draw.io Desktop for editing.
