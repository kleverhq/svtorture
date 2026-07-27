import { useEffect, useMemo, useRef, type KeyboardEvent } from "react";

import { CopyLinkButton } from "./CopyLinkButton";
import {
  aggregateStatus,
  profileKeys,
  resultsByKey,
  STATUS_GROUP_LABELS,
  STATUS_GROUP_SYMBOLS,
  standardLocationLabel,
  statusGroup,
} from "./model";
import { StatusBadge } from "./StatusBadge";
import type {
  Campaign,
  CaseDefinition,
  Requirement,
  Result,
  Status,
} from "./types";
import {
  useRevealSplitSelection,
  useViewportWorkspaceHeight,
} from "./useSplitWorkspace";

interface RequirementsProps {
  requirements: Requirement[];
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
  reason: string;
}

export function RequirementsView({
  requirements,
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
  const workspaceRef = useViewportWorkspaceHeight<HTMLDivElement>();
  const requirementPaneRef = useRef<HTMLElement | null>(null);
  const requirementButtonRefs = useRef(new Map<string, HTMLButtonElement>());
  const resultMap = useMemo(() => resultsByKey(campaign), [campaign]);
  const profiles = profileKeys(campaign).filter((key) => {
    const [toolId, profileId] = key.split("/");
    return (
      (!toolFilter || toolId === toolFilter) &&
      (!profileFilter || profileId === profileFilter)
    );
  });
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
          return {
            key: profileKey,
            status: aggregateStatus(results),
            reason: [...new Set(reasons)].join(", "),
          };
        }),
      );
    }
    return evidence;
  }, [evidenceCasesByRequirement, profiles, requirements, resultMap]);
  const selected =
    requirements.find((requirement) => requirement.id === selectedRequirementId) ??
    requirements[0];
  useEffect(() => {
    if (
      selectedRequirementId &&
      selected &&
      selected.id !== selectedRequirementId
    ) {
      onSelectRequirement(selected.id);
    }
  }, [onSelectRequirement, selected, selectedRequirementId]);
  const selectedIndex = selected
    ? requirements.findIndex((requirement) => requirement.id === selected.id)
    : -1;
  useRevealSplitSelection(
    selected?.id,
    selectedIndex,
    requirementButtonRefs,
    requirementPaneRef,
  );
  const supporting = selected ? (casesByRequirement.get(selected.id) ?? []) : [];
  const selectedEvidence = selected
    ? (evidenceByRequirement.get(selected.id) ?? [])
    : [];
  const moveSelection = (
    event: KeyboardEvent<HTMLButtonElement>,
    currentIndex: number,
  ) => {
    let nextIndex: number | undefined;
    if (event.key === "ArrowDown" || event.key === "ArrowRight") {
      nextIndex = Math.min(requirements.length - 1, currentIndex + 1);
    } else if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
      nextIndex = Math.max(0, currentIndex - 1);
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = requirements.length - 1;
    }
    if (nextIndex === undefined) return;
    event.preventDefault();
    if (nextIndex === currentIndex) return;
    const requirement = requirements[nextIndex];
    if (!requirement) return;
    onSelectRequirement(requirement.id);
    window.requestAnimationFrame(() =>
      requirementButtonRefs.current.get(requirement.id)?.focus(),
    );
  };

  return (
    <section className="panel requirements" aria-label="Requirement evidence">
      {selected ? (
        <div className="requirements-workspace" ref={workspaceRef}>
          <nav
            className="requirement-list"
            aria-label="Requirements"
            role="listbox"
          >
            {requirements.map((requirement, index) => {
              const evidence = evidenceByRequirement.get(requirement.id) ?? [];
              return (
                <button
                  type="button"
                  className={requirement.id === selected.id ? "is-selected" : ""}
                  role="option"
                  aria-selected={requirement.id === selected.id}
                  aria-current={requirement.id === selected.id ? "true" : undefined}
                  tabIndex={requirement.id === selected.id ? 0 : -1}
                  key={requirement.id}
                  ref={(node) => {
                    if (node) requirementButtonRefs.current.set(requirement.id, node);
                    else requirementButtonRefs.current.delete(requirement.id);
                  }}
                  onClick={() => onSelectRequirement(requirement.id)}
                  onKeyDown={(event) => moveSelection(event, index)}
                >
                  <span className="requirement-list__clause">
                    {standardLocationLabel(requirement.clause)}
                  </span>
                  <strong>{requirement.summary}</strong>
                  <code>{requirement.id}</code>
                  <span className="requirement-list__verdicts">
                    {evidence.map((item) => {
                      const group = statusGroup(item.status);
                      return (
                        <span
                          className={`verdict-dot status--${group}`}
                          title={`${item.key}: ${STATUS_GROUP_LABELS[group]}${
                            item.reason ? ` — ${item.reason}` : ""
                          }`}
                          aria-label={`${item.key}: ${STATUS_GROUP_LABELS[group]}`}
                          key={item.key}
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

          <article
            className="requirement-pane"
            ref={requirementPaneRef}
            aria-label={`Requirement ${selected.id}`}
          >
            <header className="requirement-pane__header">
              <div>
                <span className="section-label">
                  {standardLocationLabel(selected.clause)}
                </span>
                <h3>{selected.summary}</h3>
                <code>{selected.id}</code>
              </div>
              <CopyLinkButton
                target={{
                  view: "matrix",
                  parameter: "requirementId",
                  id: selected.id,
                  campaignId: campaign?.id,
                }}
              />
            </header>

            <section className="requirement-pane__section">
              <h4>Standard anchors</h4>
              <ul className="anchor-list">
                {selected.anchors.map((anchor) => (
                  <li key={anchor}>
                    <code>{anchor}</code>
                  </li>
                ))}
              </ul>
            </section>

            <section className="requirement-pane__section">
              <h4>Tool evidence</h4>
              {selectedEvidence.length ? (
                <div className="requirement-profile-list">
                  {selectedEvidence.map((item) => {
                    const [toolId = "", profileId = ""] = item.key.split("/");
                    return (
                      <button
                        type="button"
                        className="requirement-profile"
                        key={item.key}
                        aria-label={`View cases for ${selected.id} with ${item.key} — ${STATUS_GROUP_LABELS[statusGroup(item.status)]}${item.reason ? `: ${item.reason}` : ""}`}
                        onClick={() =>
                          onInspectEvidence(toolId, profileId, selected.id)
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
              )}
            </section>

            <section className="requirement-pane__section">
              <h4>Supporting cases</h4>
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
            </section>
          </article>
        </div>
      ) : (
        <div className="empty-state">No requirements match the current filters.</div>
      )}
    </section>
  );
}
