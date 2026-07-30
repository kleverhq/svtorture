import campaignToDashboard from "../../docs/about/assets/campaign-to-dashboard.drawio.png";
import executableCases from "../../docs/about/assets/executable-cases.drawio.png";
import standardsToEvidence from "../../docs/about/assets/standards-to-evidence.drawio.png";
import toolApplicability from "../../docs/about/assets/tool-applicability.drawio.png";
import traceableRequirements from "../../docs/about/assets/traceable-requirements.drawio.png";

const CONTENTS = [
  ["overview", "Overview"],
  ["requirements", "Requirements"],
  ["cases", "Cases"],
  ["tools", "Tools"],
  ["campaigns", "Campaigns"],
  ["dashboard", "Dashboard"],
] as const;

const REPOSITORY_DOCS =
  "https://github.com/kleverhq/svtorture/tree/main/docs";

function GuideFigure({
  id,
  src,
  alt,
  width,
  height,
  caption,
  description,
}: {
  id: string;
  src: string;
  alt: string;
  width: number;
  height: number;
  caption: string;
  description: string;
}) {
  const descriptionId = `${id}-description`;
  return (
    <figure className="about-figure">
      <div
        className="about-figure__viewport"
        role="region"
        aria-label={`Scrollable diagram: ${alt}`}
        tabIndex={0}
      >
        <img
          src={src}
          alt={alt}
          width={width}
          height={height}
          aria-describedby={descriptionId}
          loading="lazy"
          decoding="async"
        />
      </div>
      <figcaption id={descriptionId}>
        <b>{caption}</b>
        <span>{description}</span>
      </figcaption>
    </figure>
  );
}

export function AboutView() {
  return (
    <div className="about-view">
      <nav className="about-toc" aria-label="About contents">
        <span className="section-label">On this page</span>
        <ol>
          {CONTENTS.map(([id, label], index) => (
            <li key={id}>
              <a href={`#${id}`}>
                <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
                {label}
              </a>
            </li>
          ))}
        </ol>
        <a
          className="about-toc__docs"
          href={REPOSITORY_DOCS}
          target="_blank"
          rel="noreferrer"
        >
          Maintainer docs ↗
        </a>
      </nav>

      <article className="about-story" aria-label="About SVTORTURE">
        <section className="about-section" id="overview">
          <div className="about-section__copy">
            <span className="about-section__number">01</span>
            <div>
              <h2>Overview</h2>
              <p className="about-section__lead">
                Compatibility suites such as <code>sv-tests</code> cover many
                language features and tools. SVTORTURE focuses on the evidence
                behind each result.
              </p>
              <p>
                It is not a fork or replacement. Each case has an explicit target
                phase and oracle, and every result can be traced back to a
                requirement.
              </p>
            </div>
          </div>
          <GuideFigure
            id="standards-flow"
            src={standardsToEvidence}
            alt="Diagram of the IEEE standard, requirements, cases, tool profiles, campaign, and dashboard"
            width={1342}
            height={578}
            caption="The standard defines expected behavior. Tools provide observations."
            description="Annotation assigns stable anchors to IEEE source blocks, and requirements cite those anchors. Cases and compatible tool profiles go to the runner. It records campaign results for the dashboard."
          />
        </section>

        <section className="about-section" id="requirements">
          <div className="about-section__copy">
            <span className="about-section__number">02</span>
            <div>
              <h2>Requirements</h2>
              <p className="about-section__lead">
                The annotator assigns a stable anchor to each source block,
                including paragraphs, list items, tables, and figures. A
                requirement cites one or more of these anchors.
              </p>
              <p>
                IEEE 1800-2023 supplies the normative text. Each requirement also
                records whether the rule applies to 1800-2012 and 1800-2017 tool
                modes.
              </p>
            </div>
          </div>
          <GuideFigure
            id="requirements-flow"
            src={traceableRequirements}
            alt="Diagram linking standard anchors to a requirement and corpus metrics"
            width={1222}
            height={633}
            caption="Each requirement retains links to the standard text it came from."
            description="Paragraph, list item, table, and figure anchors can support a requirement. Related clause references record its context. Coverage measures how many anchors are cited; density measures the number of links to cited anchors."
          />
          <dl className="about-formulas">
            <div>
              <dt>Coverage</dt>
              <dd>How much of the anchor inventory is referenced?</dd>
            </div>
            <div>
              <dt>Density</dt>
              <dd>How many requirement-to-anchor links support each referenced anchor?</dd>
            </div>
          </dl>
        </section>

        <section className="about-section" id="cases">
          <div className="about-section__copy">
            <span className="about-section__number">03</span>
            <div>
              <h2>Cases</h2>
              <p className="about-section__lead">
                A case turns one primary requirement into minimal, tool-neutral
                source and an oracle for a specific phase.
              </p>
              <p>
                The source may need to preprocess, parse, elaborate, simulate, or
                fail with a matching diagnostic at the exact case anchor. A
                diagnostic oracle can require that message without requiring a
                nonzero exit. Related requirements record additional context but
                do not change which requirement is scored.
              </p>
            </div>
          </div>
          <GuideFigure
            id="cases-flow"
            src={executableCases}
            alt="Diagram linking case source and oracle to accepted and rejected outcomes"
            width={1222}
            height={638}
            caption="A negative case passes only when the tool rejects the intended construct."
            description="The case combines its primary requirement, related context, source files, and one oracle. The oracle can require static acceptance, a simulation PASS marker, a diagnostic at the exact case anchor, or a nonzero exit with that diagnostic."
          />
          <dl className="about-formulas">
            <div>
              <dt>Cases Coverage</dt>
              <dd>Requirements linked from cases ÷ all catalog requirements.</dd>
            </div>
            <div>
              <dt>Cases Density</dt>
              <dd>Case-to-requirement links ÷ linked requirements.</dd>
            </div>
          </dl>
          <p className="about-note">
            The dashboard does not calculate the headline pass rate from raw case
            totals. It counts a requirement only when all selected mandatory
            variants conform.
          </p>
        </section>

        <section className="about-section" id="tools">
          <div className="about-section__copy">
            <span className="about-section__number">04</span>
            <div>
              <h2>Tools</h2>
              <p className="about-section__lead">
                Tool phases are cumulative: parsing includes preprocessing,
                elaboration includes parsing, and simulation includes elaboration.
                A profile states its maximum phase and which phases it observes
                directly.
              </p>
              <p>
                The runner uses the deepest suitable command and marks the
                evidence as direct, cumulative, or not observed. It skips a case
                when the target phase or standard revision does not apply.
              </p>
            </div>
          </div>
          <GuideFigure
            id="tools-flow"
            src={toolApplicability}
            alt="Diagram of cumulative tool phases and case applicability checks"
            width={1222}
            height={652}
            caption="A later phase includes all earlier language-processing phases."
            description="The nested boxes show the phase order. Before running a case, SVTORTURE checks the profile phase, selected standard revision, and whether the tool integration is available."
          />
          <div className="about-split-facts">
            <div>
              <b>Open source</b>
              <p>
                SVTORTURE resolves the upstream reference to an immutable
                revision, then builds the project Docker image. These results can
                be published.
              </p>
            </div>
            <div>
              <b>Commercial</b>
              <p>
                An ignored machine-local configuration invokes the commercial
                runner. These results stay local.
              </p>
            </div>
          </div>
        </section>

        <section className="about-section" id="campaigns">
          <div className="about-section__copy">
            <span className="about-section__number">05</span>
            <div>
              <h2>Campaigns</h2>
              <p className="about-section__lead">
                A campaign contains the results for a selected set of tools,
                profiles, and cases. Once written, the campaign record does not
                change.
              </p>
              <p>
                The runner schedules combinations independently but executes the
                stages of each combination in order. Runnable results retain the
                version, hashes, command, diagnostics, bounded output, and replay
                data. Synthetic and incomplete results remain visible even when
                they cannot be replayed.
              </p>
            </div>
          </div>
          <GuideFigure
            id="campaign-flow"
            src={campaignToDashboard}
            alt="Diagram of campaign contents and dashboard uses"
            width={1302}
            height={643}
            caption="Campaigns store excerpts and full-stream hashes. Full logs stay local."
            description="Each tool, profile, and case combination produces a normalized result or an explicit synthetic status. The dashboard reads the campaign record and links runnable results to their replay commands."
          />
        </section>

        <section className="about-section about-section--last" id="dashboard">
          <div className="about-section__copy">
            <span className="about-section__number">06</span>
            <div>
              <h2>Dashboard</h2>
              <p className="about-section__lead">
                The dashboard reads static campaign exports. It has no application
                server or live database, and every score stays linked to its
                requirements and cases.
              </p>
              <p>
                Public campaigns can periodically test resolved upstream mainline
                revisions. Local exports may include commercial results, but the
                public export policy removes them.
              </p>
            </div>
          </div>
          <div className="about-actions" aria-label="Dashboard uses">
            <div>
              <span>01</span>
              <b>Compare</b>
              <p>Compare pass rate, completeness, and trends for the selected corpus.</p>
            </div>
            <div>
              <span>02</span>
              <b>Investigate</b>
              <p>
                Open a requirement, then inspect its cases, source, diagnostics,
                and output.
              </p>
            </div>
            <div>
              <span>03</span>
              <b>Reproduce</b>
              <p>
                Copy the replay command for a result and include the evidence in
                a bug report.
              </p>
            </div>
          </div>
        </section>
      </article>
    </div>
  );
}
