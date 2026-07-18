import { useMemo, useState } from "react";

import { resultsByKey } from "./model";
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
        <dl className="compact-dl evidence-detail__identity">
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
            <span>{observation.stage_id}</span>
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
            {copied ? "Copied" : "Copy reproduction command"}
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
}: {
  cases: CaseDefinition[];
  requirements: Requirement[];
  campaign?: Campaign | undefined;
  toolFilter: string;
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
  return (
    <section className="panel evidence" aria-labelledby="evidence-title">
      <div className="panel__heading">
        <div>
          <span className="eyebrow">Case-level evidence</span>
          <h2 id="evidence-title">Oracle and observations</h2>
        </div>
        <p>Expand a tool judgment to inspect normalized evidence, hashes, and replay.</p>
      </div>
      <div className="evidence__list">
        {cases.map((testCase) => {
          const requirement = requirementMap.get(testCase.primary_requirement);
          return (
            <article className="case-card" key={testCase.id}>
              <header>
                <div>
                  <span className="eyebrow">
                    Clause {requirement?.clause} · {testCase.target_phase} ·{" "}
                    {testCase.expectation}
                  </span>
                  <h3>{testCase.title}</h3>
                  <code>{testCase.id}</code>
                </div>
                <div className="tag-list">
                  {testCase.tags.map((tag) => (
                    <span key={tag}>{tag}</span>
                  ))}
                </div>
              </header>
              <p>{testCase.description}</p>
              <div className="case-card__meta">
                <div>
                  <strong>{testCase.primary_requirement}</strong>
                  <span>{requirement?.summary}</span>
                </div>
                <div>
                  <strong>Oracle · {testCase.oracle.kind}</strong>
                  <code>
                    {testCase.oracle.marker ?? testCase.oracle.anchor ?? "target phase exit"}
                  </code>
                </div>
                <div>
                  <strong>Sources</strong>
                  <SourceLinks testCase={testCase} campaign={campaign} />
                </div>
              </div>
              <div className="case-card__results">
                {visibleProfiles.map((profile) => {
                  const result = resultMap.get(
                    `${testCase.id}:${profile.toolId}:${profile.profileId}`,
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
                        <ObservationDetail result={result} tool={tool} />
                      ) : (
                        <p>No result was recorded for this tool/profile.</p>
                      )}
                    </details>
                  );
                })}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
