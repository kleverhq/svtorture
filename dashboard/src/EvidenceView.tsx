import { useMemo, useState } from "react";

import {
  resultsByKey,
  STATUS_GROUP_LABELS,
  STATUS_GROUP_SYMBOLS,
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

function SourceLinks({
  testCase,
  campaign,
}: {
  testCase: CaseDefinition;
  campaign?: Campaign | undefined;
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
        return link ? (
          <a key={source} href={link}>
            {source}
          </a>
        ) : (
          <code key={source}>{source}</code>
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
  const copy = async () => {
    if (!reproduce) return;
    await navigator.clipboard.writeText(reproduce);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };
  return (
    <div className="evidence-detail">
      <p>{result.summary}</p>
      {tool && (
        <dl className="fact-grid evidence-detail__identity">
          <div>
            <dt>Tool source</dt>
            <dd>
              <code title={tool.selection?.resolved_sha}>
                {tool.selection?.resolved_sha.slice(0, 12) ?? "local wrapper"}
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
                {tool.image?.digest?.slice(0, 24) ?? "private wrapper"}
              </code>
            </dd>
          </div>
        </dl>
      )}
      {result.known_issue && (
        <p className="known-fail">
          <strong>Known fail:</strong> {result.known_issue}
        </p>
      )}
      {result.observations.map((observation) => (
        <article className="observation" key={observation.stage_id}>
          <div className="observation__facts">
            <strong>{observation.stage_id}</strong>
            <span>{observation.phase}</span>
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
  selectedCaseId,
  onSelectCase,
}: {
  cases: CaseDefinition[];
  requirements: Requirement[];
  campaign?: Campaign | undefined;
  toolFilter: string;
  selectedCaseId: string;
  onSelectCase: (caseId: string) => void;
}) {
  const resultMap = useMemo(() => resultsByKey(campaign), [campaign]);
  const profiles =
    campaign?.tools.flatMap((tool) =>
      tool.profile_ids.map((profile) => ({
        key: `${tool.definition.id}/${profile}`,
        toolId: tool.definition.id,
        profileId: profile,
      })),
    ) ?? [];
  const visibleProfiles = profiles.filter(
    (profile) => !toolFilter || profile.key === toolFilter,
  );
  const requirementMap = new Map(requirements.map((item) => [item.id, item]));
  const selected = selectedCaseId
    ? cases.find((testCase) => testCase.id === selectedCaseId)
    : cases[0];
  const requirement = selected
    ? requirementMap.get(selected.primary_requirement)
    : undefined;

  return (
    <section className="panel evidence" aria-labelledby="evidence-title">
      <div className="panel__heading panel__heading--compact">
        <div>
          <h2 id="evidence-title">Case evidence</h2>
          <span>
            {cases.length} cases · {visibleProfiles.length} tool profiles
          </span>
        </div>
      </div>
      {selected ? (
        <div className="evidence-workspace">
          <nav className="case-list" aria-label="Cases">
            {cases.map((testCase) => {
              const itemRequirement = requirementMap.get(testCase.primary_requirement);
              return (
                <button
                  type="button"
                  className={testCase.id === selected.id ? "is-selected" : ""}
                  aria-current={testCase.id === selected.id ? "true" : undefined}
                  key={testCase.id}
                  onClick={() => onSelectCase(testCase.id)}
                >
                  <span className="case-list__clause">
                    {itemRequirement?.clause ?? "—"} · {testCase.target_phase}
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

          <article className="evidence-pane">
            <header className="evidence-pane__header">
              <div>
                <span className="section-label">
                  Clause {requirement?.clause} · {selected.target_phase} ·{" "}
                  {selected.expectation}
                </span>
                <h3>{selected.title}</h3>
                <code>{selected.id}</code>
              </div>
              <div className="tag-list">
                {selected.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
            </header>
            <p className="evidence-pane__description">{selected.description}</p>
            <dl className="fact-grid case-facts">
              <div>
                <dt>Requirement</dt>
                <dd>
                  <strong>{selected.primary_requirement}</strong>
                  <span>{requirement?.summary}</span>
                </dd>
              </div>
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
                  <SourceLinks testCase={selected} campaign={campaign} />
                </dd>
              </div>
            </dl>
            <div className="tool-judgments">
              {visibleProfiles.map((profile) => {
                const result = resultMap.get(
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
                        status={result?.status ?? "not-run"}
                        reason={result?.reason}
                        knownIssue={result?.known_issue}
                      />
                      <span>{result?.reason ?? "no observation"}</span>
                    </summary>
                    {result ? (
                      <ObservationDetail
                        key={`${result.case_id}:${profile.key}`}
                        result={result}
                        tool={tool}
                      />
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
