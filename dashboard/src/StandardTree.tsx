import { useEffect, useMemo, useState } from "react";

import {
  buildSectionTree,
  decodeSectionSelection,
  sectionSelectionState,
  toggleSectionSelection,
  type RequirementSectionNode,
} from "./requirementHierarchy";
import { statusGroup } from "./model";
import type { StandardSection, Status } from "./types";

export type StandardTreeTone = "red" | "yellow" | "green" | "gray";

const TONE_LABELS: Record<StandardTreeTone, string> = {
  red: "Failing or infrastructure error",
  yellow: "Unclear",
  green: "Passing",
  gray: "Not evaluated or not applicable",
};

const TONE_SYMBOLS: Record<StandardTreeTone, string> = {
  red: "✕",
  yellow: "!",
  green: "✓",
  gray: "–",
};

const TONE_PRIORITY: Record<StandardTreeTone, number> = {
  gray: 0,
  green: 1,
  yellow: 2,
  red: 3,
};

function mergeTone(
  left: StandardTreeTone | undefined,
  right: StandardTreeTone,
): StandardTreeTone {
  if (!left || TONE_PRIORITY[right] > TONE_PRIORITY[left]) return right;
  return left;
}

export function standardTreeTone(statuses: Status[]): StandardTreeTone {
  let tone: StandardTreeTone = "gray";
  for (const status of statuses) {
    const group = statusGroup(status);
    if (group === "fail" || group === "infra") return "red";
    if (group === "unclear") tone = mergeTone(tone, "yellow");
    else if (group === "pass") tone = mergeTone(tone, "green");
  }
  return tone;
}

function countsBySection(
  clauses: string[],
  sections: ReadonlySet<string>,
): Map<string, number> {
  const counts = new Map<string, number>();
  for (const itemClause of clauses) {
    const parts = itemClause.split(".");
    for (let length = 1; length <= parts.length; length += 1) {
      const clause = parts.slice(0, length).join(".");
      if (sections.has(clause)) counts.set(clause, (counts.get(clause) ?? 0) + 1);
    }
  }
  return counts;
}

interface TreeItemProps {
  node: RequirementSectionNode;
  expanded: ReadonlySet<string>;
  selected: ReadonlySet<string>;
  totalCounts: ReadonlyMap<string, number>;
  visibleCounts: ReadonlyMap<string, number>;
  tones: ReadonlyMap<string, StandardTreeTone>;
  itemNoun: string;
  onToggleExpanded: (clause: string) => void;
  onToggleSelected: (clause: string, checked: boolean) => void;
  onNavigate: (clause: string) => void;
}

function TreeItem({
  node,
  expanded,
  selected,
  totalCounts,
  visibleCounts,
  tones,
  itemNoun,
  onToggleExpanded,
  onToggleSelected,
  onNavigate,
}: TreeItemProps) {
  const hasChildren = node.children.length > 0;
  const isExpanded = expanded.has(node.clause);
  const state = sectionSelectionState(node, selected);
  const visible = visibleCounts.get(node.clause) ?? 0;
  const total = totalCounts.get(node.clause) ?? 0;
  const tone = tones.get(node.clause);
  return (
    <li className="requirement-toc__item">
      <div
        className={`requirement-toc__row${tone ? ` requirement-toc__row--${tone}` : ""}${visible === 0 ? " is-empty" : ""}`}
      >
        {hasChildren ? (
          <button
            type="button"
            className="requirement-toc__toggle"
            aria-label={`${isExpanded ? "Collapse" : "Expand"} ${node.clause} ${node.title}`}
            aria-expanded={isExpanded}
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
          aria-label={`${node.clause} ${node.title}`}
          onClick={() => onNavigate(node.clause)}
          disabled={visible === 0}
        >
          <code>{node.clause}</code>
          <span>{node.title}</span>
        </button>
        {tone ? (
          <span
            className="requirement-toc__status"
            role="img"
            aria-label={`Section result: ${TONE_LABELS[tone]}`}
            title={TONE_LABELS[tone]}
          >
            {TONE_SYMBOLS[tone]}
          </span>
        ) : (
          <span className="requirement-toc__status" aria-hidden="true" />
        )}
        <span
          className="requirement-toc__count"
          aria-label={`${visible} of ${total} ${itemNoun}${total === 1 ? "" : "s"}`}
        >
          {visible}/{total}
        </span>
      </div>
      {hasChildren && isExpanded && (
        <ul>
          {node.children.map((child) => (
            <TreeItem
              key={child.clause}
              node={child}
              expanded={expanded}
              selected={selected}
              totalCounts={totalCounts}
              visibleCounts={visibleCounts}
              tones={tones}
              itemNoun={itemNoun}
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

export interface StandardTreeItem {
  clause: string;
  statuses?: Status[] | undefined;
}

interface StandardTreeProps {
  sections: StandardSection[];
  totalClauses: string[];
  visibleItems: StandardTreeItem[];
  selectedSections: string[];
  onSelectedSectionsChange: (sections: string[]) => void;
  onNavigate: (clause: string) => void;
  itemNoun: string;
  matchingCount?: number | undefined;
  totalCount?: number | undefined;
  autoExpandClause?: string | undefined;
  showTones?: boolean | undefined;
}

export function StandardTree({
  sections,
  totalClauses,
  visibleItems,
  selectedSections,
  onSelectedSectionsChange,
  onNavigate,
  itemNoun,
  matchingCount = visibleItems.length,
  totalCount = totalClauses.length,
  autoExpandClause,
  showTones = false,
}: StandardTreeProps) {
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const sectionClauses = useMemo(
    () => new Set(sections.map((section) => section.clause)),
    [sections],
  );
  const tree = useMemo(() => buildSectionTree(sections), [sections]);
  const selected = useMemo(
    () => decodeSectionSelection(selectedSections, tree),
    [selectedSections, tree],
  );
  const visibleClauses = useMemo(
    () => visibleItems.map((item) => item.clause),
    [visibleItems],
  );
  const totalCounts = useMemo(
    () => countsBySection(totalClauses, sectionClauses),
    [sectionClauses, totalClauses],
  );
  const visibleCounts = useMemo(
    () => countsBySection(visibleClauses, sectionClauses),
    [sectionClauses, visibleClauses],
  );
  const tones = useMemo(() => {
    const values = new Map<string, StandardTreeTone>();
    if (!showTones) return values;
    for (const item of visibleItems) {
      const tone = standardTreeTone(item.statuses ?? ["not-run"]);
      const parts = item.clause.split(".");
      for (let length = 1; length <= parts.length; length += 1) {
        const clause = parts.slice(0, length).join(".");
        if (sectionClauses.has(clause)) {
          values.set(clause, mergeTone(values.get(clause), tone));
        }
      }
    }
    return values;
  }, [sectionClauses, showTones, visibleItems]);

  useEffect(() => {
    if (!autoExpandClause) return;
    const ancestors = autoExpandClause.split(".");
    setExpanded((current) => {
      let changed = false;
      const next = new Set(current);
      for (let length = 1; length < ancestors.length; length += 1) {
        const ancestor = ancestors.slice(0, length).join(".");
        if (!next.has(ancestor)) {
          next.add(ancestor);
          changed = true;
        }
      }
      return changed ? next : current;
    });
  }, [autoExpandClause]);

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
    <nav className="requirement-toc" aria-label="Standard table of contents">
      <header className="requirement-toc__header">
        <div>
          <span className="section-label">IEEE Std 1800-2023</span>
          <h3>Table of contents</h3>
        </div>
        <span>{matchingCount} matching</span>
      </header>
      <label className="requirement-toc__all">
        <input
          type="checkbox"
          checked={selected.size === 0}
          onChange={() => onSelectedSectionsChange([])}
        />
        <strong>All</strong>
        <span>
          {matchingCount}/{totalCount}
        </span>
      </label>
      <ul aria-label="Standard sections">
        {tree.map((node) => (
          <TreeItem
            key={node.clause}
            node={node}
            expanded={expanded}
            selected={selected}
            totalCounts={totalCounts}
            visibleCounts={visibleCounts}
            tones={tones}
            itemNoun={itemNoun}
            onToggleExpanded={toggleExpanded}
            onToggleSelected={toggleSelected}
            onNavigate={onNavigate}
          />
        ))}
      </ul>
    </nav>
  );
}
