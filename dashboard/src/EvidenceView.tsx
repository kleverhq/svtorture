import {
  memo,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { CopyLinkButton } from "./CopyLinkButton";
import {
  resultsByKey,
  standardLocationLabel,
} from "./model";
import {
  buildSectionTree,
  decodeSectionSelection,
  sectionContains,
} from "./requirementHierarchy";
import { StandardTree } from "./StandardTree";
import { StatusBadge } from "./StatusBadge";
import type {
  Campaign,
  CampaignTool,
  CaseDefinition,
  Requirement,
  Result,
  StandardSection,
} from "./types";

interface SourceContent {
  name: string;
  text: string;
}

type SourceTarget =
  | { kind: "embedded"; text: string }
  | { kind: "external"; href: string }
  | { kind: "unavailable" };

interface VisibleProfile {
  key: string;
  toolId: string;
  profileId: string;
}

function sourceTarget(link: string | undefined): SourceTarget {
  const prefix = "data:text/plain;charset=utf-8,";
  if (link?.startsWith(prefix)) {
    try {
      return { kind: "embedded", text: decodeURIComponent(link.slice(prefix.length)) };
    } catch {
      return { kind: "unavailable" };
    }
  }
  if (!link || link.startsWith("data:")) return { kind: "unavailable" };
  try {
    const url = new URL(link);
    return url.protocol === "https:" && url.hostname === "github.com"
      ? { kind: "external", href: url.toString() }
      : { kind: "unavailable" };
  } catch {
    return { kind: "unavailable" };
  }
}

function SourceLinks({
  testCase,
  campaign,
  openSourceName,
  viewerId,
  onToggleSource,
}: {
  testCase: CaseDefinition;
  campaign?: Campaign | undefined;
  openSourceName?: string | undefined;
  viewerId: string;
  onToggleSource: (source: SourceContent, trigger: HTMLButtonElement) => void;
}) {
  return (
    <div className="source-links">
      {testCase.sources.map((source) => {
        const repository = campaign?.trust.repository;
        const commit = campaign?.repository.commit;
        const link =
          repository && commit && commit !== "unborn"
            ? `https://github.com/${repository}/blob/${commit}/cases/${testCase.id}/${source
                .split("/")
                .map(encodeURIComponent)
                .join("/")}`
            : testCase.source_links?.[source];
        const target = sourceTarget(link);
        if (target.kind === "embedded") {
          const expanded = openSourceName === source;
          return (
            <button
              type="button"
              className="source-link"
              key={source}
              aria-expanded={expanded}
              aria-controls={viewerId}
              onClick={(event) =>
                onToggleSource(
                  { name: source, text: target.text },
                  event.currentTarget,
                )
              }
            >
              {source}
            </button>
          );
        }
        if (target.kind === "external") {
          return (
            <a key={source} href={target.href} target="_blank" rel="noreferrer">
              {source} ↗
            </a>
          );
        }
        return (
          <span
            className="source-unavailable"
            title="Source content unavailable"
            key={source}
          >
            {source} · unavailable
          </span>
        );
      })}
    </div>
  );
}

function ObservationDetail({
  result,
  tool,
}: {
  result: Result;
  tool?: CampaignTool | undefined;
}) {
  const [copied, setCopied] = useState(false);
  const reproduce = result.reproduction_command;
  const observedThrough = [
    ...new Set(result.observations.map((item) => item.attempted_through_phase)),
  ].join(", ");
  const copy = async () => {
    if (!reproduce) return;
    await navigator.clipboard.writeText(reproduce);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };
  return (
    <div className="evidence-detail">
      <p>{result.summary}</p>
      <dl className="fact-grid evidence-detail__identity">
        <div>
          <dt>Target phase</dt>
          <dd>{result.target_phase}</dd>
        </div>
        <div>
          <dt>Evidence mode</dt>
          <dd>{result.evidence_mode}</dd>
        </div>
        <div>
          <dt>Attempted through</dt>
          <dd>{observedThrough || "not observed"}</dd>
        </div>
        {tool && (
          <>
            <div>
              <dt>Tool source</dt>
              <dd>
                <code title={tool.selection?.resolved_sha}>
                  {tool.selection?.resolved_sha.slice(0, 12) ?? "local runner"}
                </code>
              </dd>
            </div>
            <div>
              <dt>Reported version</dt>
              <dd>{tool.reported_version ?? "unavailable"}</dd>
            </div>
            <div>
              <dt>Image digest</dt>
              <dd>
                <code title={tool.image?.digest ?? undefined}>
                  {tool.image?.digest?.slice(0, 24) ?? "local runner"}
                </code>
              </dd>
            </div>
          </>
        )}
      </dl>
      {result.known_issue && (
        <p className="known-fail">
          <strong>Known fail:</strong> {result.known_issue}
        </p>
      )}
      {result.observations.map((observation) => (
        <article className="observation" key={observation.stage_id}>
          <div className="observation__facts">
            <strong>{observation.stage_id}</strong>
            <span>through {observation.attempted_through_phase}</span>
            <span>{observation.outcome}</span>
            <span>
              {observation.exit_code == null
                ? `signal ${observation.signal ?? "—"}`
                : `exit ${observation.exit_code}`}
            </span>
            <span>{observation.duration_seconds.toFixed(3)} s</span>
          </div>
          <code className="command">{observation.portable_argv.join(" ")}</code>
          {observation.diagnostics.map((diagnostic, index) => (
            <p className="diagnostic" key={`${diagnostic.message}-${index}`}>
              <strong>{diagnostic.severity}</strong>{" "}
              {diagnostic.source ?? "no location"}
              {diagnostic.line ? `:${diagnostic.line}` : ""}: {diagnostic.message}
            </p>
          ))}
          {(["stdout", "stderr"] as const).map((streamName) => {
            const stream = observation[streamName];
            return (
              <details key={streamName}>
                <summary>
                  {streamName} · {stream.size_bytes} bytes · sha256:
                  {stream.sha256.slice(0, 12)}
                  {stream.truncated ? " · bounded excerpt" : ""}
                </summary>
                <pre>{stream.excerpt || "(empty)"}</pre>
              </details>
            );
          })}
        </article>
      ))}
      {reproduce && (
        <div className="reproduce">
          <code>{reproduce}</code>
          <button type="button" className="button button--quiet" onClick={copy}>
            {copied ? "Copied" : "Copy command"}
          </button>
        </div>
      )}
    </div>
  );
}

function LazyDetails({
  label,
  count,
  onOpen,
  onOpenChange,
  renderContent,
}: {
  label: string;
  count: number;
  onOpen?: (() => void) | undefined;
  onOpenChange?: ((open: boolean) => void) | undefined;
  renderContent: () => ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <details
      className="requirement-card__details"
      open={open}
      onToggle={(event) => {
        const nextOpen = event.currentTarget.open;
        setOpen(nextOpen);
        onOpenChange?.(nextOpen);
        if (nextOpen) onOpen?.();
      }}
    >
      <summary>
        {label} <span>{count}</span>
      </summary>
      {open && renderContent()}
    </details>
  );
}

function applicabilityLabel(status: string): string {
  return status
    .split("-")
    .map((part) => `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

interface CaseCardProps {
  testCase: CaseDefinition;
  requirement?: Requirement | undefined;
  relatedRequirements: Requirement[];
  campaign?: Campaign | undefined;
  profiles: VisibleProfile[];
  compactResults: ReadonlyMap<string, Result>;
  selectedTags: ReadonlySet<string>;
  onToggleTag: (tag: string) => void;
  onInspectRequirement: (requirementId: string) => void;
  loadCaseEvidence?: ((caseId: string) => Promise<Result[]>) | undefined;
}

const CaseCard = memo(function CaseCard({
  testCase,
  requirement,
  relatedRequirements,
  campaign,
  profiles,
  compactResults,
  selectedTags,
  onToggleTag,
  onInspectRequirement,
  loadCaseEvidence,
}: CaseCardProps) {
  const [openSource, setOpenSource] = useState<SourceContent | undefined>();
  const sourceTriggerRef = useRef<HTMLButtonElement | null>(null);
  const sourceViewerId = useId();
  const evidenceRequested = useRef(false);
  const evidenceRequestGeneration = useRef(0);
  const [toolEvidenceOpen, setToolEvidenceOpen] = useState(false);
  const [detail, setDetail] = useState<{
    results?: Result[];
    error?: string;
  }>();
  const campaignId = campaign?.id ?? "";

  const requestEvidence = useCallback(() => {
    if (!loadCaseEvidence || evidenceRequested.current) return;
    evidenceRequested.current = true;
    const generation = ++evidenceRequestGeneration.current;
    setDetail({});
    loadCaseEvidence(testCase.id)
      .then((results) => {
        if (generation === evidenceRequestGeneration.current) {
          setDetail({ results });
        }
      })
      .catch((error: unknown) => {
        if (generation !== evidenceRequestGeneration.current) return;
        evidenceRequested.current = false;
        setDetail({
          error: error instanceof Error ? error.message : String(error),
        });
      });
  }, [loadCaseEvidence, testCase.id]);

  useEffect(() => {
    setOpenSource(undefined);
    sourceTriggerRef.current = null;
    evidenceRequested.current = false;
    evidenceRequestGeneration.current += 1;
    setDetail(undefined);
    if (toolEvidenceOpen) requestEvidence();
  }, [campaignId]);

  const detailResults = useMemo(
    () =>
      loadCaseEvidence
        ? new Map(
            (detail?.results ?? []).map((result) => [
              `${result.case_id}:${result.tool_id}:${result.profile_id}`,
              result,
            ]),
          )
        : compactResults,
    [compactResults, detail?.results, loadCaseEvidence],
  );
  const linkedRequirements = requirement
    ? [requirement, ...relatedRequirements]
    : relatedRequirements;
  const closeSource = () => {
    sourceTriggerRef.current?.focus();
    setOpenSource(undefined);
  };

  return (
    <article className="requirement-card case-card" aria-label={`Case ${testCase.id}`}>
      <header className="requirement-card__header">
        <div>
          <span className="section-label">
            {requirement
              ? standardLocationLabel(requirement.clause)
              : "Unknown standard location"}
            {" · "}{testCase.target_phase} · {testCase.expectation}
          </span>
          <h3>{testCase.title}</h3>
          <code>{testCase.id}</code>
        </div>
        <CopyLinkButton
          target={{
            view: "evidence",
            parameter: "caseId",
            id: testCase.id,
            campaignId: campaign?.id,
          }}
        />
      </header>

      <p className="case-card__description">{testCase.description}</p>

      <section className="requirement-card__applicability">
        <h4>Revision applicability</h4>
        <div className="requirement-card__table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Revision</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(testCase.revision_applicability).map(
                ([revision, status]) => (
                  <tr key={revision}>
                    <th scope="row">{revision}</th>
                    <td>{applicabilityLabel(status)}</td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="requirement-card__tags" aria-label="Case tags">
        <h4>Tags</h4>
        <div>
          {testCase.tags.length ? (
            testCase.tags.map((tag) => (
              <button
                type="button"
                aria-pressed={selectedTags.has(tag)}
                key={tag}
                onClick={() => onToggleTag(tag)}
              >
                {tag}
              </button>
            ))
          ) : (
            <span className="requirement-card__empty">No tags</span>
          )}
        </div>
      </section>

      <LazyDetails
        label="Requirements"
        count={linkedRequirements.length}
        renderContent={() =>
          linkedRequirements.length ? (
            <div className="supporting-case-list case-card__requirements">
              {linkedRequirements.map((item, index) => (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => onInspectRequirement(item.id)}
                >
                  <span>{index === 0 && item.id === requirement?.id ? "Primary" : "Related"}</span>
                  <strong>{item.summary}</strong>
                  <code>{item.id}</code>
                </button>
              ))}
            </div>
          ) : (
            <p>The referenced requirement is unavailable.</p>
          )
        }
      />

      <LazyDetails
        label="Oracle and sources"
        count={testCase.sources.length}
        renderContent={() => (
          <div className="case-card__definition">
            <dl className="fact-grid case-facts">
              <div>
                <dt>Target phase</dt>
                <dd>{testCase.target_phase}</dd>
              </div>
              <div>
                <dt>Expectation</dt>
                <dd>{testCase.expectation}</dd>
              </div>
              <div>
                <dt>Evidence</dt>
                <dd>{testCase.evidence}</dd>
              </div>
              <div>
                <dt>Oracle</dt>
                <dd>
                  <strong>{testCase.oracle.kind}</strong>
                  <code>
                    {testCase.oracle.marker ??
                      testCase.oracle.anchor ??
                      "target phase exit"}
                  </code>
                </dd>
              </div>
              <div>
                <dt>Sources</dt>
                <dd>
                  <SourceLinks
                    testCase={testCase}
                    campaign={campaign}
                    openSourceName={openSource?.name}
                    viewerId={sourceViewerId}
                    onToggleSource={(source, trigger) => {
                      if (openSource?.name === source.name) {
                        closeSource();
                        return;
                      }
                      sourceTriggerRef.current = trigger;
                      setOpenSource(source);
                    }}
                  />
                </dd>
              </div>
            </dl>
            {openSource && (
              <section
                className="source-viewer"
                id={sourceViewerId}
                aria-label={`Source ${openSource.name}`}
              >
                <header>
                  <div>
                    <span>Case source</span>
                    <strong>{openSource.name}</strong>
                  </div>
                  <button
                    type="button"
                    className="icon-button"
                    aria-label="Close source"
                    onClick={closeSource}
                  >
                    ×
                  </button>
                </header>
                <pre>
                  <code>{openSource.text}</code>
                </pre>
              </section>
            )}
          </div>
        )}
      />

      <LazyDetails
        label="Tool evidence"
        count={profiles.length}
        onOpen={requestEvidence}
        onOpenChange={setToolEvidenceOpen}
        renderContent={() => (
          <div
            className="tool-judgments"
            aria-busy={Boolean(
              loadCaseEvidence &&
                evidenceRequested.current &&
                !detail?.results &&
                !detail?.error,
            )}
          >
            <p className="visually-hidden" role="status">
              {detail?.error
                ? `Detailed evidence unavailable: ${detail.error}`
                : detail?.results
                  ? "Detailed evidence loaded"
                  : loadCaseEvidence && evidenceRequested.current
                    ? "Loading detailed evidence"
                    : ""}
            </p>
            {detail?.error && (
              <p className="empty-state">
                Evidence unavailable: {detail.error}. Close and reopen this section to retry.
              </p>
            )}
            {profiles.length ? (
              profiles.map((profile) => {
                const key = `${testCase.id}:${profile.toolId}:${profile.profileId}`;
                const compactResult = compactResults.get(key);
                const result = detailResults.get(key);
                const tool = campaign?.tools.find(
                  (item) => item.definition.id === profile.toolId,
                );
                return (
                  <details key={profile.key}>
                    <summary>
                      <strong>{profile.key}</strong>
                      <StatusBadge
                        status={compactResult?.status ?? "not-run"}
                        reason={compactResult?.reason}
                        knownIssue={compactResult?.known_issue}
                      />
                      <span>{compactResult?.reason ?? "no observation"}</span>
                    </summary>
                    {result ? (
                      <ObservationDetail result={result} tool={tool} />
                    ) : detail?.error ? (
                      <p className="empty-state">Detailed evidence unavailable.</p>
                    ) : compactResult && loadCaseEvidence && !detail?.results ? (
                      <p className="empty-state">Loading detailed evidence…</p>
                    ) : (
                      <p className="empty-state">No detailed result was recorded.</p>
                    )}
                  </details>
                );
              })
            ) : (
              <p>No tool evidence matches the current filters.</p>
            )}
          </div>
        )}
      />
    </article>
  );
});

function fallbackSections(requirements: Requirement[]): StandardSection[] {
  const sections = new Map<string, StandardSection>();
  for (const requirement of requirements) {
    const parts = requirement.clause.split(".");
    for (let length = 1; length <= parts.length; length += 1) {
      const clause = parts.slice(0, length).join(".");
      if (!sections.has(clause)) sections.set(clause, { clause, title: clause });
    }
  }
  return [...sections.values()];
}

export function EvidenceView({
  cases,
  allCases,
  requirements,
  standardSections,
  selectedSections,
  onSelectedSectionsChange,
  selectedTags = [],
  onToggleTag = () => undefined,
  campaign,
  toolFilter,
  profileFilter,
  selectedCaseId,
  onSelectCase,
  onInspectRequirement,
  loadCaseEvidence,
}: {
  cases: CaseDefinition[];
  allCases?: CaseDefinition[] | undefined;
  requirements: Requirement[];
  standardSections?: StandardSection[] | undefined;
  selectedSections?: string[] | undefined;
  onSelectedSectionsChange?: ((sections: string[]) => void) | undefined;
  selectedTags?: string[] | undefined;
  onToggleTag?: ((tag: string) => void) | undefined;
  campaign?: Campaign | undefined;
  toolFilter: string;
  profileFilter: string;
  selectedCaseId: string;
  onSelectCase: (caseId: string) => void;
  onInspectRequirement: (requirementId: string) => void;
  loadCaseEvidence?: ((caseId: string) => Promise<Result[]>) | undefined;
}) {
  const completeCases = allCases ?? cases;
  const sectionSelection = selectedSections ?? [];
  const changeSections = onSelectedSectionsChange ?? (() => undefined);
  const cardRefs = useRef(new Map<string, HTMLElement>());
  const navigationScrollId = useRef("");
  const requirementMap = useMemo(
    () => new Map(requirements.map((item) => [item.id, item])),
    [requirements],
  );
  const sections = useMemo(
    () =>
      standardSections?.length ? standardSections : fallbackSections(requirements),
    [requirements, standardSections],
  );
  const tree = useMemo(() => buildSectionTree(sections), [sections]);
  const selected = useMemo(
    () => decodeSectionSelection(sectionSelection, tree),
    [sectionSelection, tree],
  );
  const resultMap = useMemo(() => resultsByKey(campaign), [campaign]);
  const profiles = useMemo(
    () =>
      campaign?.tools.flatMap((tool) =>
        tool.profile_ids.flatMap((profileId) =>
          (!toolFilter || tool.definition.id === toolFilter) &&
          (!profileFilter || profileId === profileFilter)
            ? [
                {
                  key: `${tool.definition.id}/${profileId}`,
                  toolId: tool.definition.id,
                  profileId,
                },
              ]
            : [],
        ),
      ) ?? [],
    [campaign, profileFilter, toolFilter],
  );
  const selectedTagSet = useMemo(() => new Set(selectedTags), [selectedTags]);
  const relatedRequirementsByCase = useMemo(
    () =>
      new Map(
        cases.map((testCase) => [
          testCase.id,
          testCase.related_requirements
            .map((id) => requirementMap.get(id))
            .filter((item): item is Requirement => Boolean(item)),
        ]),
      ),
    [cases, requirementMap],
  );
  const caseClause = (testCase: CaseDefinition) =>
    requirementMap.get(testCase.primary_requirement)?.clause;
  const visibleCases = useMemo(
    () =>
      selected.size === 0
        ? cases
        : cases.filter((testCase) => {
            const clause = requirementMap.get(testCase.primary_requirement)?.clause;
            return Boolean(clause && selected.has(clause));
          }),
    [cases, requirementMap, selected],
  );
  const selectedCase = useMemo(
    () => visibleCases.find((testCase) => testCase.id === selectedCaseId),
    [selectedCaseId, visibleCases],
  );
  const treeItems = useMemo(
    () =>
      cases.flatMap((testCase) => {
        const clause = requirementMap.get(testCase.primary_requirement)?.clause;
        return clause
          ? [
              {
                clause,
                statuses: toolFilter
                  ? profiles.map(
                      (profile) =>
                        resultMap.get(
                          `${testCase.id}:${profile.toolId}:${profile.profileId}`,
                        )?.status ?? "not-run",
                    )
                  : undefined,
              },
            ]
          : [];
      }),
    [cases, profiles, requirementMap, resultMap, toolFilter],
  );
  const totalClauses = useMemo(
    () =>
      completeCases.flatMap((testCase) => {
        const clause = requirementMap.get(testCase.primary_requirement)?.clause;
        return clause ? [clause] : [];
      }),
    [completeCases, requirementMap],
  );

  useEffect(() => {
    if (!selectedCase) return;
    if (navigationScrollId.current === selectedCase.id) {
      navigationScrollId.current = "";
      return;
    }
    window.requestAnimationFrame(() => {
      cardRefs.current.get(selectedCase.id)?.scrollIntoView?.({ block: "start" });
    });
  }, [selectedCase]);

  const navigateToSection = (clause: string) => {
    const testCase = visibleCases.find((item) => {
      const itemClause = caseClause(item);
      return Boolean(itemClause && sectionContains(clause, itemClause));
    });
    if (!testCase) return;
    navigationScrollId.current = testCase.id === selectedCaseId ? "" : testCase.id;
    onSelectCase(testCase.id);
    const reduceMotion =
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    const card = cardRefs.current.get(testCase.id);
    card?.scrollIntoView?.({
      block: "start",
      behavior: reduceMotion ? "auto" : "smooth",
    });
    const heading = card?.querySelector("h3");
    if (heading instanceof HTMLElement) {
      heading.tabIndex = -1;
      heading.focus({ preventScroll: true });
    }
  };

  return (
    <section className="panel evidence requirements" aria-label="Case evidence">
      <div className="requirements-workspace cases-workspace">
        <StandardTree
          sections={sections}
          totalClauses={totalClauses}
          visibleItems={treeItems}
          selectedSections={sectionSelection}
          onSelectedSectionsChange={changeSections}
          onNavigate={navigateToSection}
          itemNoun="case"
          matchingCount={cases.length}
          totalCount={completeCases.length}
          autoExpandClause={
            selectedCase
              ? requirementMap.get(selectedCase.primary_requirement)?.clause
              : undefined
          }
          showTones={Boolean(toolFilter)}
        />

        <div className="requirement-cards case-cards">
          <header className="requirement-cards__header">
            <div>
              <span className="section-label">Case evidence</span>
              <h2 aria-live="polite" aria-atomic="true">
                {visibleCases.length} case{visibleCases.length === 1 ? "" : "s"}
              </h2>
            </div>
            {selected.size > 0 && (
              <button type="button" onClick={() => changeSections([])}>
                Show all sections
              </button>
            )}
          </header>
          {visibleCases.length ? (
            visibleCases.map((testCase) => {
              const requirement = requirementMap.get(testCase.primary_requirement);
              const relatedRequirements =
                relatedRequirementsByCase.get(testCase.id) ?? [];
              return (
                <div
                  className="requirement-card-anchor"
                  key={testCase.id}
                  ref={(element) => {
                    if (element) cardRefs.current.set(testCase.id, element);
                    else cardRefs.current.delete(testCase.id);
                  }}
                >
                  <CaseCard
                    testCase={testCase}
                    requirement={requirement}
                    relatedRequirements={relatedRequirements}
                    campaign={campaign}
                    profiles={profiles}
                    compactResults={resultMap}
                    selectedTags={selectedTagSet}
                    onToggleTag={onToggleTag}
                    onInspectRequirement={onInspectRequirement}
                    loadCaseEvidence={loadCaseEvidence}
                  />
                </div>
              );
            })
          ) : (
            <div className="empty-state">
              {cases.length
                ? "No cases belong to the selected standard sections."
                : "No cases match the current filters."}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
