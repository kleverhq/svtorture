# SVTORTURE

## What is SVTORTURE?

SystemVerilog tools do not always agree: one compiler accepts a construct,
another rejects it, and a third crashes or produces the wrong result. SVTORTURE
helps determine which behavior follows the language standard and preserves the
evidence needed to reproduce that judgment.

SVTORTURE is a standards-driven conformance framework. It connects each small,
tool-neutral test case to a specific IEEE 1800 requirement, runs the case at an
explicit phase such as parsing, elaboration, or simulation, and evaluates the
observation with a shared oracle. A timeout, crash, unrelated diagnostic, or
known tool issue never becomes a passing result.

The main data flow is:

```text
IEEE requirements
        ↓
SystemVerilog cases
        ↓
tool adapters and controlled Docker execution
        ↓
raw observations and generic conformance judgments
        ↓
reproducible campaigns
        ↓
static evidence dashboard
```

The committed corpus is intentionally small today. The goal is to expand it
chapter by chapter while keeping every result reviewable and reproducible, not
to claim complete SystemVerilog coverage prematurely.

## Another sv-tests?

SVTORTURE was inspired by
[CHIPS Alliance sv-tests](https://github.com/chipsalliance/sv-tests) and its
ability to run one SystemVerilog test collection across many tools. `sv-tests`
provides useful broad compatibility data and distinguishes several test modes,
but its feature/test-oriented results do not try to preserve SVTORTURE's
complete chain from a normative requirement through a phase-specific oracle and
observation to a reproducible conformance judgment.

SVTORTURE goes deeper rather than broader:

- IEEE requirements, not feature tags, are the unit of coverage and scoring;
- every oracle names an exact target phase while tool capability follows the
  cumulative preprocess → parse → elaborate → simulate pipeline;
- direct and cumulative evidence remain distinguishable, and an unrelated
  later-phase failure never satisfies an earlier negative oracle;
- negative tests require evidence tied to the intended construct;
- tool behavior never defines the expected result;
- campaigns retain exact tool revisions, container identities, portable
  commands, bounded output excerpts, and full-stream hashes; full logs remain
  transient local or CI artifacts;
- known failures remain failures instead of being converted into expected
  passes.

SVTORTURE is therefore not a fork or drop-in replacement for `sv-tests`. It is
an attempt to build stricter evidence for the part of the language covered by
its corpus.

## Requirements

Baseline development, metadata validation, and `just smoke` require:

- a POSIX-style environment with Bash and Git;
- Python 3.12 or newer;
- [uv](https://docs.astral.sh/uv/);
- Node.js 24 with npm, matching CI;
- [Just](https://just.systems/) 1.21 or newer;
- network access for the initial dependency installation.

Native Windows users need WSL or an equivalent POSIX environment. Running
open-source tools or the complete `just ci` gate additionally requires network
access for upstream source resolution and a Docker daemon capable of running
`linux/amd64` containers, either natively or through emulation.

Compiler and simulator binaries do not need to be installed on the host.
SVTORTURE resolves their source revisions and runs project-controlled Docker
images. Building a current upstream tool for the first time can take several
minutes.

An IEEE 1800-2023 PDF and Poppler are optional. They are needed only when
maintaining requirement annotations; ordinary validation, campaigns,
reproduction, and dashboard use do not require the PDF.

## Quick start

From the repository root, install the locked Python and frontend dependencies:

```bash
just setup
```

Run the fast deterministic checks:

```bash
just smoke
```

Resolve the current upstream Verilator revision, build its Docker image, and run
it against the complete current corpus:

```bash
just latest verilator
```

The command reports source resolution, image preparation, and each selected case.
The first image build can take several minutes. To also stream the Docker pull
and build output when an image must be built, run:

```bash
just latest-verbose verilator
```

For a shorter first run, select the smoke suite instead:

```bash
just latest verilator smoke
```

The command prints the generated campaign path, for example:

```text
campaign: .svtorture/campaigns/<campaign-id>/campaign.json
summary: conforming=… nonconforming=…
```

Ordinary conformance failures are recorded in that campaign rather than treated
as infrastructure failures. Build a local dashboard dataset from the printed
path:

```bash
just dashboard-build ".svtorture/campaigns/<campaign-id>/campaign.json"
```

Serve the static dashboard:

```bash
just dashboard-serve
```

Open <http://localhost:4173>. The dashboard provides a requirement matrix,
case-level evidence, campaign provenance, and history views. Generated
campaigns and dashboard data remain under ignored local directories.

To run all current public upstream tools instead of only Verilator, use:

```bash
just latest-all
```

## Documentation

- [Architecture and data flow](docs/architecture.md)
- [IEEE 1800-2023 annotation](docs/annotation.md)
- [Conformance methodology and metric](docs/methodology.md)
- [Adding a case](docs/adding-a-case.md)
- [Adding a tool](docs/adding-a-tool.md)
- [Campaign reproduction](docs/reproduction.md)
- [Dashboard design and local workflow](dashboard/README.md)

Maintainer rules and local constraints live in the nearest `AGENTS.md`.

## License

The project is licensed under [Apache-2.0](LICENSE).
