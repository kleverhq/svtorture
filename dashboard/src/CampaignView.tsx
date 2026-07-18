import type { Campaign } from "./types";

function Hash({ value }: { value: string | null | undefined }) {
  return <code title={value ?? "not recorded"}>{value?.slice(0, 18) ?? "—"}</code>;
}

export function CampaignView({ campaigns }: { campaigns: Campaign[] }) {
  const ordered = [...campaigns].sort((left, right) =>
    right.finished_at.localeCompare(left.finished_at),
  );
  return (
    <section className="panel campaigns" aria-labelledby="campaign-title">
      <div className="panel__heading">
        <div>
          <span className="eyebrow">Campaign provenance</span>
          <h2 id="campaign-title">Immutable measurements</h2>
        </div>
        <p>Corpus, tool source, image recipe, trust, and completeness are kept together.</p>
      </div>
      <div className="campaigns__list">
        {ordered.map((campaign) => (
          <article className="campaign-card" key={campaign.id}>
            <header>
              <div>
                <span className="eyebrow">
                  {new Date(campaign.finished_at).toLocaleString()}
                </span>
                <h3>{campaign.id}</h3>
              </div>
              <span className={`completeness ${campaign.complete ? "complete" : "incomplete"}`}>
                {campaign.complete ? "Complete" : "Incomplete"}
              </span>
            </header>
            <dl className="campaign-card__facts">
              <div>
                <dt>Corpus commit</dt>
                <dd>
                  <Hash value={campaign.repository.commit} />
                  {campaign.repository.dirty ? " · dirty" : " · clean"}
                </dd>
              </div>
              <div>
                <dt>Case manifest</dt>
                <dd>
                  <Hash value={campaign.hashes.cases} />
                </dd>
              </div>
              <div>
                <dt>Requirement manifest</dt>
                <dd>
                  <Hash value={campaign.hashes.requirements} />
                </dd>
              </div>
              <div>
                <dt>Selection manifest</dt>
                <dd>
                  <Hash value={campaign.hashes.selection} />
                </dd>
              </div>
              <div>
                <dt>Trust</dt>
                <dd>
                  {campaign.trust.source}
                  {campaign.trust.workflow_run_id
                    ? ` · run ${campaign.trust.workflow_run_id}`
                    : ""}
                </dd>
              </div>
              <div>
                <dt>Platform</dt>
                <dd>{campaign.platform}</dd>
              </div>
              <div>
                <dt>Selection</dt>
                <dd>
                  {campaign.selection_name} · {campaign.case_ids.length} cases
                </dd>
              </div>
              <div>
                <dt>Missing tools</dt>
                <dd>{campaign.missing_tool_ids.join(", ") || "none"}</dd>
              </div>
            </dl>
            <div className="campaign-card__tools">
              {campaign.tools.map((tool) => (
                <details key={tool.definition.id}>
                  <summary>
                    <strong>{tool.definition.display_name}</strong>
                    <span>{tool.profile_ids.join(", ")}</span>
                    <Hash value={tool.selection?.resolved_sha} />
                  </summary>
                  <dl className="compact-dl">
                    <div>
                      <dt>Preparation</dt>
                      <dd>{tool.preparation_error ?? "ready"}</dd>
                    </div>
                    <div>
                      <dt>Requested ref</dt>
                      <dd>{tool.selection?.requested_ref ?? "local"}</dd>
                    </div>
                    <div>
                      <dt>Exact / nearest tags</dt>
                      <dd>
                        {tool.selection?.exact_tags.join(", ") ||
                          tool.selection?.nearest_tag ||
                          "none"}
                      </dd>
                    </div>
                    <div>
                      <dt>Reported version</dt>
                      <dd>{tool.reported_version ?? "unavailable"}</dd>
                    </div>
                    <div>
                      <dt>Image digest</dt>
                      <dd>
                        <Hash value={tool.image?.digest} />
                      </dd>
                    </div>
                    <div>
                      <dt>Recipe</dt>
                      <dd>
                        <Hash value={tool.image?.recipe_sha256} />
                      </dd>
                    </div>
                    <div>
                      <dt>Base image</dt>
                      <dd>
                        <Hash value={tool.image?.base_image_digest} />
                      </dd>
                    </div>
                    <div>
                      <dt>Effective language</dt>
                      <dd>
                        {tool.definition.profiles
                          .filter((profile) => tool.profile_ids.includes(profile.id))
                          .map((profile) => profile.effective_language)
                          .join("; ")}
                      </dd>
                    </div>
                    <div>
                      <dt>Policy</dt>
                      <dd>
                        {tool.definition.distribution} · {tool.definition.execution} ·
                        publish {String(tool.definition.publish)}
                      </dd>
                    </div>
                  </dl>
                </details>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
