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
                Broad compatibility suites are valuable. SVTORTURE goes deeper:
                it preserves the chain from a normative rule to the evidence used
                for one conformance judgment.
              </p>
              <p>
                Inspired by <code>sv-tests</code>, it is neither a fork nor a
                replacement. The corpus is built around exact phases, shared
                oracles, and reproducible observations rather than tool behavior.
              </p>
            </div>
          </div>
          <GuideFigure
            id="standards-flow"
            src={standardsToEvidence}
            alt="Flow from the IEEE standard through requirements and cases to campaign evidence"
            width={1342}
            height={578}
            caption="The standard supplies the expectation; tools supply observations."
            description="The IEEE source is annotated into stable anchors and falsifiable requirements. Cases and applicable tool profiles enter the runner; its normalized campaign evidence is then inspected in the dashboard."
          />
        </section>

        <section className="about-section" id="requirements">
          <div className="about-section__copy">
            <span className="about-section__number">02</span>
            <div>
              <h2>Requirements</h2>
              <p className="about-section__lead">
                Annotation gives every paragraph, list item, table, figure, and
                other source block a stable anchor. One or more anchors support a
                concise, falsifiable requirement.
              </p>
              <p>
                IEEE 1800-2023 is the authority. Each requirement also records
                whether its rule applies to 1800-2012 and 1800-2017, so older tool
                modes are assessed instead of guessed.
              </p>
            </div>
          </div>
          <GuideFigure
            id="requirements-flow"
            src={traceableRequirements}
            alt="Traceable requirements linked to standard anchors and corpus metrics"
            width={1222}
            height={633}
            caption="Traceability keeps every distilled rule connected to its normative basis."
            description="Paragraph, list-item, table, and figure anchors support a central requirement. Related-clause references preserve context, while coverage and density measure anchor reach and link depth."
          />
          <dl className="about-formulas">
            <div>
              <dt>Coverage</dt>
              <dd>How much of the anchor inventory is referenced?</dd>
            </div>
            <div>
              <dt>Density</dt>
              <dd>How many requirement–anchor links support each referenced anchor?</dd>
            </div>
          </dl>
        </section>

        <section className="about-section" id="cases">
          <div className="about-section__copy">
            <span className="about-section__number">03</span>
            <div>
              <h2>Cases</h2>
              <p className="about-section__lead">
                A case materializes one primary requirement as minimal,
                tool-neutral source and a phase-specific oracle.
              </p>
              <p>
                Source may need to preprocess, parse, elaborate, simulate, or be
                rejected with a matching diagnostic at the exact case anchor. A
                separate diagnostic oracle requires a matching message at that
                exact anchor without requiring rejection. Related requirements retain context
                without changing the primary scoring unit.
              </p>
            </div>
          </div>
          <GuideFigure
            id="cases-flow"
            src={executableCases}
            alt="Executable cases pairing source code with phase-specific oracles"
            width={1222}
            height={638}
            caption="A negative test passes only when evidence identifies the intended rejection."
            description="Primary and related requirements lead to minimal source and one exact oracle. The oracle distinguishes static acceptance, simulation with a PASS marker, a diagnostic at the exact case anchor, and nonzero rejection with an anchored diagnostic."
          />
          <dl className="about-formulas">
            <div>
              <dt>Cases Coverage</dt>
              <dd>Requirements linked from cases ÷ all catalog requirements.</dd>
            </div>
            <div>
              <dt>Cases Density</dt>
              <dd>Case–requirement links ÷ linked requirements.</dd>
            </div>
          </dl>
          <p className="about-note">
            Cases supply observations. The headline pass rate then counts
            requirements whose selected mandatory variants all conform—not raw
            case totals.
          </p>
        </section>

        <section className="about-section" id="tools">
          <div className="about-section__copy">
            <span className="about-section__number">04</span>
            <div>
              <h2>Tools</h2>
              <p className="about-section__lead">
                Preprocessing, parsing, elaboration, and simulation form one
                cumulative pipeline. A profile declares the deepest phase it can
                reach and the phases it can observe directly.
              </p>
              <p>
                SVTORTURE uses the deepest suitable command and records whether
                the resulting evidence is direct, cumulative, or not observed. A
                case runs only when its phase and standard revision apply.
              </p>
            </div>
          </div>
          <GuideFigure
            id="tools-flow"
            src={toolApplicability}
            alt="Cumulative tool phases and the checks that decide case applicability"
            width={1222}
            height={652}
            caption="Later phases include the earlier language-processing phases."
            description="Preprocessing sits inside parsing, which sits inside elaboration and simulation. The case phase, selected standard revision, and integration availability decide whether a profile can run it."
          />
          <div className="about-split-facts">
            <div>
              <b>Open source</b>
              <p>A moving upstream reference is resolved to an immutable revision before the project-controlled Docker build; eligible public evidence.</p>
            </div>
            <div>
              <b>Commercial</b>
              <p>Ignored machine-local runner configuration; local evidence only.</p>
            </div>
          </div>
        </section>

        <section className="about-section" id="campaigns">
          <div className="about-section__copy">
            <span className="about-section__number">05</span>
            <div>
              <h2>Campaigns</h2>
              <p className="about-section__lead">
                One campaign is the immutable evidence bundle for a selected grid
                of tools, profiles, and cases.
              </p>
              <p>
                The launcher runs independent jobs, keeps stages within each job
                sequential, and records normalized results. Runnable observations
                retain versions, hashes, commands, diagnostics, bounded output,
                and reproduction data; synthetic or incomplete statuses remain
                explicit even when they cannot be replayed.
              </p>
            </div>
          </div>
          <GuideFigure
            id="campaign-flow"
            src={campaignToDashboard}
            alt="Campaign evidence flowing into dashboard investigation and reproduction"
            width={1302}
            height={643}
            caption="Transient full logs stay local; compact evidence and full-stream hashes survive."
            description="The run grid feeds one immutable campaign containing normalized evidence and explicit synthetic statuses. The static dashboard connects runnable observations to inspection, compact reproduction, and focused reporting."
          />
        </section>

        <section className="about-section about-section--last" id="dashboard">
          <div className="about-section__copy">
            <span className="about-section__number">06</span>
            <div>
              <h2>Dashboard</h2>
              <p className="about-section__lead">
                The dashboard is a static evidence browser—not a live database
                and not a scoreboard detached from its corpus.
              </p>
              <p>
                Periodic public campaigns can track resolved upstream mainline
                revisions. Local exports may also include commercial evidence,
                but public export policy excludes it.
              </p>
            </div>
          </div>
          <div className="about-actions" aria-label="Dashboard uses">
            <div><span>01</span><b>Compare</b><p>Read pass rate, completeness, and trends with exact provenance.</p></div>
            <div><span>02</span><b>Investigate</b><p>Move from a requirement to cases, source, diagnostics, and output.</p></div>
            <div><span>03</span><b>Reproduce</b><p>Copy a compact command for one exact result and share it in a bug report.</p></div>
          </div>
          <p className="about-closing">
            The useful unit is not a green cell. It is an expectation, an
            observation, and the traceable evidence connecting them.
          </p>
        </section>
      </article>
    </div>
  );
}
