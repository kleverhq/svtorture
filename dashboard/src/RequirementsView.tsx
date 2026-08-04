import {
  memo,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { CopyLinkButton } from "./CopyLinkButton";
import {
  aggregateStatus,
  profileKeys,
  resultsByKey,
  STATUS_GROUP_LABELS,
  standardLocationLabel,
  statusGroup,
} from "./model";
import {
  buildSectionTree,
  decodeSectionSelection,
  sectionContains,
} from "./requirementHierarchy";
import { StandardTree, standardTreeTone } from "./StandardTree";
import { StatusBadge } from "./StatusBadge";
import type {
  Campaign,
  CaseDefinition,
  Requirement,
  Result,
  StandardSection,
  Status,
} from "./types";

interface RequirementsProps {
  requirements: Requirement[];
  allRequirements: Requirement[];
  standardSections: StandardSection[];
  selectedSections: string[];
  onSelectedSectionsChange: (sections: string[]) => void;
  selectedTags?: string[] | undefined;
  onToggleTag?: ((tag: string) => void) | undefined;
  cases: CaseDefinition[];
  evidenceCasesByProfile?: ReadonlyMap<string, CaseDefinition[]> | undefined;
  campaign?: Campaign | undefined;
  toolFilter: string;
  profileFilter: string;
  selectedRequirementId: string;
  onSelectRequirement: (requirementId: string) => void;
  onInspectCase: (caseId: string) => void;
  onInspectEvidence: (
    toolId: string,
    profileId: string,
    requirementId: string,
  ) => void;
  focusRequirementId?: string | undefined;
  onFocusedRequirement?: (() => void) | undefined;
}

interface ProfileEvidence {
  key: string;
  status: Status;
  statuses: Status[];
  reason: string;
}

const EMPTY_CASES: CaseDefinition[] = [];
const EMPTY_EVIDENCE: ProfileEvidence[] = [];
const NOOP = () => undefined;

export function requirementTreeTone(statuses: Status[]) {
  return standardTreeTone(statuses);
}

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

function applicabilityLabel(status: string): string {
  return status
    .split("-")
    .map((part) => `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

function LazyDetails({
  label,
  count,
  renderContent,
}: {
  label: string;
  count: number;
  renderContent: () => ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <details
      className="requirement-card__details"
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>
        {label} <span>{count}</span>
      </summary>
      {open && renderContent()}
    </details>
  );
}

interface RequirementCardProps {
  requirement: Requirement;
  evidence: ProfileEvidence[];
  supporting: CaseDefinition[];
  campaign?: Campaign | undefined;
  selectedTags: ReadonlySet<string>;
  onToggleTag: (tag: string) => void;
  onInspectCase: (caseId: string) => void;
  onInspectEvidence: (
    toolId: string,
    profileId: string,
    requirementId: string,
  ) => void;
}

const RequirementCard = memo(function RequirementCard({
  requirement,
  evidence,
  supporting,
  campaign,
  selectedTags,
  onToggleTag,
  onInspectCase,
  onInspectEvidence,
}: RequirementCardProps) {
  return (
    <article
      className="requirement-card"
      aria-label={`Requirement ${requirement.id}`}
    >
      <header className="requirement-card__header">
        <div>
          <span className="section-label">
            {standardLocationLabel(requirement.clause)}
          </span>
          <h3>{requirement.summary}</h3>
          <code>{requirement.id}</code>
        </div>
        <CopyLinkButton
          target={{
            view: "matrix",
            parameter: "requirementId",
            id: requirement.id,
            campaignId: campaign?.id,
          }}
        />
      </header>

      <section className="requirement-card__applicability">
        <h4>Revision applicability</h4>
        <div className="requirement-card__table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Revision</th>
                <th scope="col">Status</th>
                <th scope="col">Clause</th>
                <th scope="col">Note</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(requirement.revision_applicability).map(
                ([revision, rule]) => (
                  <tr key={revision}>
                    <th scope="row">{revision}</th>
                    <td>{applicabilityLabel(rule.status)}</td>
                    <td>{rule.clause ?? "—"}</td>
                    <td>{rule.note ?? "—"}</td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="requirement-card__tags" aria-label="Requirement tags">
        <h4>Tags</h4>
        <div>
          {requirement.tags.length ? (
            requirement.tags.map((tag) => (
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
        label="Standard anchors"
        count={requirement.anchors.length}
        renderContent={() => (
          <ul className="anchor-list">
            {requirement.anchors.map((anchor) => (
              <li key={anchor}>
                <code>{anchor}</code>
              </li>
            ))}
          </ul>
        )}
      />

      <LazyDetails
        label="Tool evidence"
        count={evidence.length}
        renderContent={() =>
          evidence.length ? (
            <div className="requirement-profile-list">
              {evidence.map((item) => {
                const [toolId = "", profileId = ""] = item.key.split("/");
                return (
                  <button
                    type="button"
                    className="requirement-profile"
                    key={item.key}
                    aria-label={`View cases for ${requirement.id} with ${item.key} — ${STATUS_GROUP_LABELS[statusGroup(item.status)]}${item.reason ? `: ${item.reason}` : ""}`}
                    onClick={() =>
                      onInspectEvidence(toolId, profileId, requirement.id)
                    }
                  >
                    <code>{item.key}</code>
                    <StatusBadge
                      status={item.status}
                      reason={item.reason}
                      grouped
                    />
                    {item.reason && <small>{item.reason}</small>}
                  </button>
                );
              })}
            </div>
          ) : (
            <p>No tool evidence matches the current filters.</p>
          )
        }
      />

      <LazyDetails
        label="Supporting cases"
        count={supporting.length}
        renderContent={() => (
          <div className="supporting-case-list">
            {supporting.length ? (
              supporting.map((testCase) => (
                <button
                  type="button"
                  key={testCase.id}
                  onClick={() => onInspectCase(testCase.id)}
                >
                  <span>
                    {testCase.target_phase} · {testCase.expectation}
                  </span>
                  <strong>{testCase.title}</strong>
                  <code>{testCase.id}</code>
                </button>
              ))
            ) : (
              <p>No case currently maps to this requirement.</p>
            )}
          </div>
        )}
      />
    </article>
  );
});

export function RequirementsView({
  requirements,
  allRequirements,
  standardSections,
  selectedSections,
  onSelectedSectionsChange,
  selectedTags = [],
  onToggleTag = NOOP,
  cases,
  evidenceCasesByProfile,
  campaign,
  toolFilter,
  profileFilter,
  selectedRequirementId,
  onSelectRequirement,
  onInspectCase,
  onInspectEvidence,
  focusRequirementId = "",
  onFocusedRequirement = NOOP,
}: RequirementsProps) {
  const cardRefs = useRef(new Map<string, HTMLElement>());
  const navigationScrollId = useRef("");
  const focusedRequirementId = useRef("");
  const suppressNextFocusClearScroll = useRef(false);
  const sections = useMemo(
    () =>
      standardSections.length
        ? standardSections
        : fallbackSections(allRequirements),
    [allRequirements, standardSections],
  );
  const tree = useMemo(() => buildSectionTree(sections), [sections]);
  const selected = useMemo(
    () => decodeSectionSelection(selectedSections, tree),
    [selectedSections, tree],
  );
  const selectedTagSet = useMemo(() => new Set(selectedTags), [selectedTags]);
  const profiles = useMemo(
    () =>
      profileKeys(campaign).filter((key) => {
        const [toolId, profileId] = key.split("/");
        return (
          (!toolFilter || toolId === toolFilter) &&
          (!profileFilter || profileId === profileFilter)
        );
      }),
    [campaign, profileFilter, toolFilter],
  );
  const resultMap = useMemo(() => resultsByKey(campaign), [campaign]);
  const casesByRequirement = useMemo(() => {
    const result = new Map<string, CaseDefinition[]>();
    for (const testCase of cases) {
      const linked = new Set([
        testCase.primary_requirement,
        ...testCase.related_requirements,
      ]);
      for (const requirementId of linked) {
        const values = result.get(requirementId) ?? [];
        values.push(testCase);
        result.set(requirementId, values);
      }
    }
    return result;
  }, [cases]);
  const evidenceCasesByRequirement = useMemo(() => {
    const result = new Map<string, Map<string, CaseDefinition[]>>();
    for (const profileKey of profiles) {
      const linkedCases = new Map<string, CaseDefinition[]>();
      for (const testCase of evidenceCasesByProfile?.get(profileKey) ?? cases) {
        for (const requirementId of new Set([
          testCase.primary_requirement,
          ...testCase.related_requirements,
        ])) {
          const values = linkedCases.get(requirementId) ?? [];
          values.push(testCase);
          linkedCases.set(requirementId, values);
        }
      }
      result.set(profileKey, linkedCases);
    }
    return result;
  }, [cases, evidenceCasesByProfile, profiles]);
  const evidenceByRequirement = useMemo(() => {
    const evidence = new Map<string, ProfileEvidence[]>();
    for (const requirement of requirements) {
      evidence.set(
        requirement.id,
        profiles.map((profileKey) => {
          const [toolId = "", profileId = ""] = profileKey.split("/");
          const supporting =
            evidenceCasesByRequirement.get(profileKey)?.get(requirement.id) ?? [];
          const results = supporting.map((testCase) =>
            resultMap.get(`${testCase.id}:${toolId}:${profileId}`),
          );
          const reasons = results
            .filter((result): result is Result => Boolean(result))
            .map((result) => result.reason);
          const statuses = results
            .filter((result): result is Result => Boolean(result))
            .map((result) => result.status);
          return {
            key: profileKey,
            status: aggregateStatus(results),
            statuses: statuses.length ? statuses : ["not-run"],
            reason: [...new Set(reasons)].join(", "),
          };
        }),
      );
    }
    return evidence;
  }, [evidenceCasesByRequirement, profiles, requirements, resultMap]);
  const treeItems = useMemo(
    () =>
      requirements.map((requirement) => ({
        clause: requirement.clause,
        statuses: toolFilter
          ? (evidenceByRequirement.get(requirement.id) ?? []).flatMap(
              (item) => item.statuses,
            )
          : undefined,
      })),
    [evidenceByRequirement, requirements, toolFilter],
  );
  const totalClauses = useMemo(
    () => allRequirements.map((requirement) => requirement.clause),
    [allRequirements],
  );
  const visibleRequirements = useMemo(
    () =>
      selected.size === 0
        ? requirements
        : requirements.filter((requirement) => selected.has(requirement.clause)),
    [requirements, selected],
  );

  const selectedRequirement = useMemo(
    () =>
      visibleRequirements.find((item) => item.id === selectedRequirementId),
    [selectedRequirementId, visibleRequirements],
  );

  useEffect(() => {
    if (!selectedRequirement) return;
    const navigatedInView = navigationScrollId.current === selectedRequirement.id;
    if (navigatedInView) navigationScrollId.current = "";
    const suppressScroll =
      !focusRequirementId && suppressNextFocusClearScroll.current;
    if (suppressScroll) suppressNextFocusClearScroll.current = false;
    window.requestAnimationFrame(() => {
      const card = cardRefs.current.get(selectedRequirement.id);
      if (!navigatedInView && !suppressScroll) {
        card?.scrollIntoView?.({ block: "start" });
      }
      if (
        focusRequirementId === selectedRequirement.id &&
        focusedRequirementId.current !== selectedRequirement.id
      ) {
        const heading = card?.querySelector("h3");
        if (heading instanceof HTMLElement) {
          heading.tabIndex = -1;
          heading.focus({ preventScroll: true });
          focusedRequirementId.current = selectedRequirement.id;
          suppressNextFocusClearScroll.current = true;
          onFocusedRequirement();
        }
      }
    });
  }, [focusRequirementId, onFocusedRequirement, selectedRequirement]);

  const navigateToSection = (clause: string) => {
    const requirement = visibleRequirements.find((item) =>
      sectionContains(clause, item.clause),
    );
    if (!requirement) return;
    navigationScrollId.current =
      requirement.id === selectedRequirementId ? "" : requirement.id;
    onSelectRequirement(requirement.id);
    const reduceMotion =
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    const card = cardRefs.current.get(requirement.id);
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
    <section className="panel requirements" aria-label="Requirement evidence">
      <div className="requirements-workspace">
        <StandardTree
          sections={sections}
          totalClauses={totalClauses}
          visibleItems={treeItems}
          selectedSections={selectedSections}
          onSelectedSectionsChange={onSelectedSectionsChange}
          onNavigate={navigateToSection}
          itemNoun="requirement"
          autoExpandClause={selectedRequirement?.clause}
          showTones={Boolean(toolFilter)}
        />

        <div className="requirement-cards">
          <header className="requirement-cards__header">
            <div>
              <span className="section-label">Requirement evidence</span>
              <h2 aria-live="polite" aria-atomic="true">
                {visibleRequirements.length} requirement
                {visibleRequirements.length === 1 ? "" : "s"}
              </h2>
            </div>
            {selected.size > 0 && (
              <button type="button" onClick={() => onSelectedSectionsChange([])}>
                Show all sections
              </button>
            )}
          </header>
          {visibleRequirements.length ? (
            visibleRequirements.map((requirement) => (
              <div
                className="requirement-card-anchor"
                key={requirement.id}
                ref={(element) => {
                  if (element) cardRefs.current.set(requirement.id, element);
                  else cardRefs.current.delete(requirement.id);
                }}
              >
                <RequirementCard
                  requirement={requirement}
                  evidence={
                    evidenceByRequirement.get(requirement.id) ?? EMPTY_EVIDENCE
                  }
                  supporting={
                    casesByRequirement.get(requirement.id) ?? EMPTY_CASES
                  }
                  campaign={campaign}
                  selectedTags={selectedTagSet}
                  onToggleTag={onToggleTag}
                  onInspectCase={onInspectCase}
                  onInspectEvidence={onInspectEvidence}
                />
              </div>
            ))
          ) : (
            <div className="empty-state">
              {requirements.length
                ? "No requirements belong to the selected standard sections."
                : "No requirements match the current quick filters."}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
