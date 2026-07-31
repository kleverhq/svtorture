import { useEffect, useId, useMemo, useRef, useState } from "react";

import { CopyLinkButton } from "./CopyLinkButton";
import {
  resultsByKey,
  STATUS_GROUP_LABELS,
  STATUS_GROUP_SYMBOLS,
  standardLocationLabel,
  statusGroup,
} from "./model";
import { StatusBadge } from "./StatusBadge";
import type {
  Campaign,
  CampaignTool,
  CaseDefinition,
  Requirement,
  Result,
} from "./types";
import {
  useRevealSplitSelection,
  useViewportWorkspaceHeight,
} from "./useSplitWorkspace";

interface SourceContent {
  name: string;
  text: string;
}

interface OpenSource extends SourceContent {
  caseId: string;
  campaignId: string;
}

type SourceTarget =
  | { kind: "embedded"; text: string }
  | { kind: "external"; href: string }
  | { kind: "unavailable" };

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
            <a
              key={source}
              href={target.href}
              target="_blank"
              rel="noreferrer"
            >
              {source} ↗
            </a>
          );
        }
        return (
          <span className="source-unavailable" title="Source content unavailable" key={source}>
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

export function EvidenceView({
  cases,
  requirements,
  campaign,
  toolFilter,
  profileFilter,
  selectedCaseId,
  onSelectCase,
  onInspectRequirement,
  loadCaseEvidence,
}: {
  cases: CaseDefinition[];
  requirements: Requirement[];
  campaign?: Campaign | undefined;
  toolFilter: string;
  profileFilter: string;
  selectedCaseId: string;
  onSelectCase: (caseId: string) => void;
  onInspectRequirement: (requirementId: string) => void;
  loadCaseEvidence?: ((caseId: string) => Promise<Result[]>) | undefined;
}) {
  const [openSource, setOpenSource] = useState<OpenSource | undefined>();
  const sourceTriggerRef = useRef<HTMLButtonElement | null>(null);
  const workspaceRef = useViewportWorkspaceHeight<HTMLDivElement>();
  const evidencePaneRef = useRef<HTMLElement | null>(null);
  const caseButtonRefs = useRef(new Map<string, HTMLButtonElement>());
  const sourceViewerId = useId();
  const resultMap = useMemo(() => resultsByKey(campaign), [campaign]);
  const [detail, setDetail] = useState<{
    caseId: string;
    results?: Result[];
    error?: string;
  }>();
  const profiles =
    campaign?.tools.flatMap((tool) =>
      tool.profile_ids.map((profile) => ({
        key: `${tool.definition.id}/${profile}`,
        toolId: tool.definition.id,
        profileId: profile,
      })),
    ) ?? [];
  const visibleProfiles = profiles.filter(
    (profile) =>
      (!toolFilter || profile.toolId === toolFilter) &&
      (!profileFilter || profile.profileId === profileFilter),
  );
  const requirementMap = new Map(requirements.map((item) => [item.id, item]));
  const selected = selectedCaseId
    ? cases.find((testCase) => testCase.id === selectedCaseId)
    : cases[0];
  const selectedCaseIndex = selected
    ? cases.findIndex((testCase) => testCase.id === selected.id)
    : -1;
  const requirement = selected
    ? requirementMap.get(selected.primary_requirement)
    : undefined;
  const campaignId = campaign?.id ?? "";
  const visibleSource =
    openSource &&
    openSource.caseId === selected?.id &&
    openSource.campaignId === campaignId
      ? openSource
      : undefined;
  const closeSource = () => {
    sourceTriggerRef.current?.focus();
    setOpenSource(undefined);
  };
  useRevealSplitSelection(
    selected?.id,
    selectedCaseIndex,
    caseButtonRefs,
    evidencePaneRef,
  );
  useEffect(() => {
    setOpenSource(undefined);
    sourceTriggerRef.current = null;
  }, [campaignId, selected?.id]);
  useEffect(() => {
    if (!selected || !loadCaseEvidence) {
      setDetail(undefined);
      return;
    }
    let active = true;
    setDetail({ caseId: selected.id });
    loadCaseEvidence(selected.id)
      .then((results) => {
        if (active) setDetail({ caseId: selected.id, results });
      })
      .catch((error: unknown) => {
        if (active) {
          setDetail({
            caseId: selected.id,
            error: error instanceof Error ? error.message : String(error),
          });
        }
      });
    return () => {
      active = false;
    };
  }, [loadCaseEvidence, selected]);
  const detailResults = useMemo(
    () =>
      loadCaseEvidence
        ? new Map(
            (detail?.caseId === selected?.id ? detail?.results ?? [] : []).map(
              (result) => [
                `${result.case_id}:${result.tool_id}:${result.profile_id}`,
                result,
              ],
            ),
          )
        : resultMap,
    [detail, loadCaseEvidence, resultMap, selected?.id],
  );

  return (
    <section className="panel evidence" aria-label="Case evidence">
      {selected ? (
        <div className="evidence-workspace" ref={workspaceRef}>
          <nav className="case-list" aria-label="Cases">
            {cases.map((testCase) => {
              const itemRequirement = requirementMap.get(testCase.primary_requirement);
              return (
                <button
                  type="button"
                  className={testCase.id === selected.id ? "is-selected" : ""}
                  aria-current={testCase.id === selected.id ? "true" : undefined}
                  key={testCase.id}
                  ref={(node) => {
                    if (node) caseButtonRefs.current.set(testCase.id, node);
                    else caseButtonRefs.current.delete(testCase.id);
                  }}
                  onClick={() => onSelectCase(testCase.id)}
                >
                  <span className="case-list__clause">
                    {itemRequirement
                      ? standardLocationLabel(itemRequirement.clause)
                      : "—"} · {testCase.target_phase}
                  </span>
                  <strong>{testCase.title}</strong>
                  <code>{testCase.id}</code>
                  <span className="case-list__verdicts">
                    {visibleProfiles.map((profile) => {
                      const result = resultMap.get(
                        `${testCase.id}:${profile.toolId}:${profile.profileId}`,
                      );
                      const group = statusGroup(result?.status ?? "not-run");
                      return (
                        <span
                          className={`verdict-dot status--${group}`}
                          title={`${profile.key}: ${
                            result?.reason ?? STATUS_GROUP_LABELS[group]
                          }`}
                          aria-label={`${profile.key}: ${STATUS_GROUP_LABELS[group]}`}
                          key={profile.key}
                        >
                          {STATUS_GROUP_SYMBOLS[group]}
                        </span>
                      );
                    })}
                  </span>
                </button>
              );
            })}
          </nav>

          <article className="evidence-pane" ref={evidencePaneRef}>
            <header className="evidence-pane__header">
              <div>
                <span className="section-label">
                  {requirement ? standardLocationLabel(requirement.clause) : "Unknown part"} ·{" "}
                  {selected.target_phase} ·{" "}
                  {selected.expectation}
                </span>
                <h3>{selected.title}</h3>
                <code>{selected.id}</code>
              </div>
              <div className="evidence-pane__meta">
                <CopyLinkButton
                  target={{
                    view: "evidence",
                    parameter: "caseId",
                    id: selected.id,
                    campaignId: campaign?.id,
                  }}
                />
                <div className="tag-list">
                  {selected.tags.map((tag) => (
                    <span key={tag}>{tag}</span>
                  ))}
                </div>
              </div>
            </header>
            <p className="evidence-pane__description">{selected.description}</p>
            <dl className="fact-grid case-facts">
              <div>
                <dt>Requirement</dt>
                <dd>
                  <button
                    type="button"
                    className="relationship-link"
                    onClick={() => onInspectRequirement(selected.primary_requirement)}
                  >
                    <strong>{selected.primary_requirement}</strong>
                    <span>{requirement?.summary}</span>
                  </button>
                </dd>
              </div>
              {selected.related_requirements.length > 0 && (
                <div>
                  <dt>Related requirements</dt>
                  <dd className="relationship-list">
                    {selected.related_requirements.map((requirementId) => {
                      const related = requirementMap.get(requirementId);
                      return (
                        <button
                          type="button"
                          className="relationship-link"
                          key={requirementId}
                          onClick={() => onInspectRequirement(requirementId)}
                        >
                          <strong>{requirementId}</strong>
                          <span>{related?.summary}</span>
                        </button>
                      );
                    })}
                  </dd>
                </div>
              )}
              <div>
                <dt>Oracle</dt>
                <dd>
                  <strong>{selected.oracle.kind}</strong>
                  <code>
                    {selected.oracle.marker ??
                      selected.oracle.anchor ??
                      "target phase exit"}
                  </code>
                </dd>
              </div>
              <div>
                <dt>Sources</dt>
                <dd>
                  <SourceLinks
                    testCase={selected}
                    campaign={campaign}
                    openSourceName={visibleSource?.name}
                    viewerId={sourceViewerId}
                    onToggleSource={(source, trigger) => {
                      if (visibleSource?.name === source.name) {
                        closeSource();
                        return;
                      }
                      sourceTriggerRef.current = trigger;
                      setOpenSource({
                        ...source,
                        caseId: selected.id,
                        campaignId,
                      });
                    }}
                  />
                </dd>
              </div>
            </dl>
            {visibleSource && (
              <section
                className="source-viewer"
                id={sourceViewerId}
                aria-label={`Source ${visibleSource.name}`}
              >
                <header>
                  <div>
                    <span>Case source</span>
                    <strong>{visibleSource.name}</strong>
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
                  <code>{visibleSource.text}</code>
                </pre>
              </section>
            )}
            <div className="tool-judgments">
              {visibleProfiles.map((profile) => {
                const compactResult = resultMap.get(
                  `${selected.id}:${profile.toolId}:${profile.profileId}`,
                );
                const result = detailResults.get(
                  `${selected.id}:${profile.toolId}:${profile.profileId}`,
                );
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
                    {detail?.caseId === selected.id && detail.error ? (
                      <p className="empty-state">Evidence unavailable: {detail.error}</p>
                    ) : result ? (
                      <ObservationDetail
                        key={`${result.case_id}:${profile.key}`}
                        result={result}
                        tool={tool}
                      />
                    ) : compactResult ? (
                      <p className="empty-state">Loading detailed evidence…</p>
                    ) : (
                      <p className="empty-state">No result was recorded.</p>
                    )}
                  </details>
                );
              })}
            </div>
          </article>
        </div>
      ) : selectedCaseId && cases.length ? (
        <div className="empty-state">
          <p>
            Selected case <code>{selectedCaseId}</code> is unavailable under the current
            filters.
          </p>
          <button
            type="button"
            className="button button--quiet"
            onClick={() => {
              const first = cases[0];
              if (first) onSelectCase(first.id);
            }}
          >
            Open first visible case
          </button>
        </div>
      ) : (
        <div className="empty-state">No cases match the current filters.</div>
      )}
    </section>
  );
}
