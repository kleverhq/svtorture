import {
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
  sectionSelectionState,
  toggleSectionSelection,
  type RequirementSectionNode,
} from "./requirementHierarchy";
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
}

interface ProfileEvidence {
  key: string;
  status: Status;
  statuses: Status[];
  reason: string;
}

type TreeTone = "red" | "yellow" | "green" | "gray";

const TREE_TONE_LABELS: Record<TreeTone, string> = {
  red: "Failing or infrastructure error",
  yellow: "Unclear",
  green: "Passing",
  gray: "Not evaluated or not applicable",
};

const TREE_TONE_SYMBOLS: Record<TreeTone, string> = {
  red: "✕",
  yellow: "!",
  green: "✓",
  gray: "–",
};

const TREE_TONE_PRIORITY: Record<TreeTone, number> = {
  gray: 0,
  green: 1,
  yellow: 2,
  red: 3,
};

function mergeTreeTone(left: TreeTone | undefined, right: TreeTone): TreeTone {
  if (!left || TREE_TONE_PRIORITY[right] > TREE_TONE_PRIORITY[left]) return right;
  return left;
}

export function requirementTreeTone(statuses: Status[]): TreeTone {
  let tone: TreeTone = "gray";
  for (const status of statuses) {
    const group = statusGroup(status);
    if (group === "fail" || group === "infra") return "red";
    if (group === "unclear") tone = mergeTreeTone(tone, "yellow");
    else if (group === "pass") tone = mergeTreeTone(tone, "green");
  }
  return tone;
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

function countsBySection(
  requirements: Requirement[],
  sections: ReadonlySet<string>,
): Map<string, number> {
  const counts = new Map<string, number>();
  for (const requirement of requirements) {
    const parts = requirement.clause.split(".");
    for (let length = 1; length <= parts.length; length += 1) {
      const clause = parts.slice(0, length).join(".");
      if (sections.has(clause)) counts.set(clause, (counts.get(clause) ?? 0) + 1);
    }
  }
  return counts;
}

function applicabilityLabel(status: string): string {
  return status
    .split("-")
    .map((part) => `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

interface SectionTreeItemProps {
  node: RequirementSectionNode;
  expanded: ReadonlySet<string>;
  selected: ReadonlySet<string>;
  totalCounts: ReadonlyMap<string, number>;
  visibleCounts: ReadonlyMap<string, number>;
  tones: ReadonlyMap<string, TreeTone>;
  onToggleExpanded: (clause: string) => void;
  onToggleSelected: (clause: string, checked: boolean) => void;
  onNavigate: (clause: string) => void;
}

function SectionTreeItem({
  node,
  expanded,
  selected,
  totalCounts,
  visibleCounts,
  tones,
  onToggleExpanded,
  onToggleSelected,
  onNavigate,
}: SectionTreeItemProps) {
  const hasChildren = node.children.length > 0;
  const isExpanded = expanded.has(node.clause);
  const state = sectionSelectionState(node, selected);
  const visible = visibleCounts.get(node.clause) ?? 0;
  const total = totalCounts.get(node.clause) ?? 0;
  const tone = tones.get(node.clause);
  return (
    <li
      role="treeitem"
      aria-expanded={hasChildren ? isExpanded : undefined}
      className="requirement-toc__item"
    >
      <div
        className={`requirement-toc__row${tone ? ` requirement-toc__row--${tone}` : ""}${visible === 0 ? " is-empty" : ""}`}
      >
        {hasChildren ? (
          <button
            type="button"
            className="requirement-toc__toggle"
            aria-label={`${isExpanded ? "Collapse" : "Expand"} ${node.clause} ${node.title}`}
            onClick={() => onToggleExpanded(node.clause)}
          >
            {isExpanded ? "▾" : "▸"}
          </button>
        ) : (
          <span className="requirement-toc__toggle" aria-hidden="true" />
        )}
        <input
          type="checkbox"
          aria-label={`Select ${node.clause} ${node.title}`}
          checked={state.checked}
          ref={(element) => {
            if (element) element.indeterminate = state.indeterminate;
          }}
          onChange={(event) => onToggleSelected(node.clause, event.target.checked)}
        />
        <button
          type="button"
          className="requirement-toc__link"
          onClick={() => onNavigate(node.clause)}
          disabled={visible === 0}
        >
          <code>{node.clause}</code>
          <span>{node.title}</span>
        </button>
        {tone ? (
          <span
            className="requirement-toc__status"
            aria-label={`Section result: ${TREE_TONE_LABELS[tone]}`}
            title={TREE_TONE_LABELS[tone]}
          >
            {TREE_TONE_SYMBOLS[tone]}
          </span>
        ) : (
          <span className="requirement-toc__status" aria-hidden="true" />
        )}
        <span
          className="requirement-toc__count"
          aria-label={`${visible} of ${total} requirements`}
        >
          {visible}/{total}
        </span>
      </div>
      {hasChildren && isExpanded && (
        <ul role="group">
          {node.children.map((child) => (
            <SectionTreeItem
              key={child.clause}
              node={child}
              expanded={expanded}
              selected={selected}
              totalCounts={totalCounts}
              visibleCounts={visibleCounts}
              tones={tones}
              onToggleExpanded={onToggleExpanded}
              onToggleSelected={onToggleSelected}
              onNavigate={onNavigate}
            />
          ))}
        </ul>
      )}
    </li>
  );
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
  onInspectCase: (caseId: string) => void;
  onInspectEvidence: (
    toolId: string,
    profileId: string,
    requirementId: string,
  ) => void;
}

function RequirementCard({
  requirement,
  evidence,
  supporting,
  campaign,
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
            requirement.tags.map((tag) => <span key={tag}>{tag}</span>)
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
}

export function RequirementsView({
  requirements,
  allRequirements,
  standardSections,
  selectedSections,
  onSelectedSectionsChange,
  cases,
  evidenceCasesByProfile,
  campaign,
  toolFilter,
  profileFilter,
  selectedRequirementId,
  onSelectRequirement,
  onInspectCase,
  onInspectEvidence,
}: RequirementsProps) {
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const cardRefs = useRef(new Map<string, HTMLElement>());
  const sections = useMemo(
    () =>
      standardSections.length
        ? standardSections
        : fallbackSections(allRequirements),
    [allRequirements, standardSections],
  );
  const sectionClauses = useMemo(
    () => new Set(sections.map((section) => section.clause)),
    [sections],
  );
  const tree = useMemo(() => buildSectionTree(sections), [sections]);
  const selected = useMemo(
    () => decodeSectionSelection(selectedSections, tree),
    [selectedSections, tree],
  );
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
  const totalCounts = useMemo(
    () => countsBySection(allRequirements, sectionClauses),
    [allRequirements, sectionClauses],
  );
  const visibleCounts = useMemo(
    () => countsBySection(requirements, sectionClauses),
    [requirements, sectionClauses],
  );
  const tones = useMemo(() => {
    const values = new Map<string, TreeTone>();
    if (!toolFilter) return values;
    for (const requirement of requirements) {
      const tone = requirementTreeTone(
        (evidenceByRequirement.get(requirement.id) ?? []).flatMap(
          (item) => item.statuses,
        ),
      );
      const parts = requirement.clause.split(".");
      for (let length = 1; length <= parts.length; length += 1) {
        const clause = parts.slice(0, length).join(".");
        if (sectionClauses.has(clause)) {
          values.set(clause, mergeTreeTone(values.get(clause), tone));
        }
      }
    }
    return values;
  }, [evidenceByRequirement, requirements, sectionClauses, toolFilter]);
  const visibleRequirements = useMemo(
    () =>
      selected.size === 0
        ? requirements
        : requirements.filter((requirement) => selected.has(requirement.clause)),
    [requirements, selected],
  );

  useEffect(() => {
    if (!selectedRequirementId) return;
    const requirement = visibleRequirements.find(
      (item) => item.id === selectedRequirementId,
    );
    if (!requirement) return;
    const ancestors = requirement.clause.split(".");
    setExpanded((current) => {
      const next = new Set(current);
      for (let length = 1; length < ancestors.length; length += 1) {
        next.add(ancestors.slice(0, length).join("."));
      }
      return next;
    });
    window.requestAnimationFrame(() => {
      cardRefs.current.get(requirement.id)?.scrollIntoView?.({ block: "start" });
    });
  }, [selectedRequirementId, visibleRequirements]);

  const navigateToSection = (clause: string) => {
    const requirement = visibleRequirements.find((item) =>
      sectionContains(clause, item.clause),
    );
    if (!requirement) return;
    onSelectRequirement(requirement.id);
    cardRefs.current.get(requirement.id)?.scrollIntoView?.({
      block: "start",
      behavior: "smooth",
    });
  };
  const toggleExpanded = (clause: string) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(clause)) next.delete(clause);
      else next.add(clause);
      return next;
    });
  };
  const toggleSelected = (clause: string, checked: boolean) => {
    onSelectedSectionsChange(
      toggleSectionSelection(selectedSections, clause, checked, tree),
    );
  };

  return (
    <section className="panel requirements" aria-label="Requirement evidence">
      <div className="requirements-workspace">
        <nav className="requirement-toc" aria-label="Standard table of contents">
          <header className="requirement-toc__header">
            <div>
              <span className="section-label">IEEE Std 1800-2023</span>
              <h3>Table of contents</h3>
            </div>
            <span>{requirements.length} matching</span>
          </header>
          <label className="requirement-toc__all">
            <input
              type="checkbox"
              checked={selected.size === 0}
              onChange={() => onSelectedSectionsChange([])}
            />
            <strong>All</strong>
            <span>
              {requirements.length}/{allRequirements.length}
            </span>
          </label>
          <ul role="tree" aria-label="Standard sections">
            {tree.map((node) => (
              <SectionTreeItem
                key={node.clause}
                node={node}
                expanded={expanded}
                selected={selected}
                totalCounts={totalCounts}
                visibleCounts={visibleCounts}
                tones={tones}
                onToggleExpanded={toggleExpanded}
                onToggleSelected={toggleSelected}
                onNavigate={navigateToSection}
              />
            ))}
          </ul>
        </nav>

        <div className="requirement-cards" aria-live="polite">
          <header className="requirement-cards__header">
            <div>
              <span className="section-label">Requirement evidence</span>
              <h2>
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
                key={requirement.id}
                ref={(element) => {
                  if (element) cardRefs.current.set(requirement.id, element);
                  else cardRefs.current.delete(requirement.id);
                }}
              >
                <RequirementCard
                  requirement={requirement}
                  evidence={evidenceByRequirement.get(requirement.id) ?? []}
                  supporting={casesByRequirement.get(requirement.id) ?? []}
                  campaign={campaign}
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
