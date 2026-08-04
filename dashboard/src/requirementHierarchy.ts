import type { Requirement, StandardSection } from "./types";

export interface RequirementSectionNode extends StandardSection {
  children: RequirementSectionNode[];
}

export function fallbackSections(requirements: Requirement[]): StandardSection[] {
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

function parentClause(clause: string): string | undefined {
  const separator = clause.lastIndexOf(".");
  return separator === -1 ? undefined : clause.slice(0, separator);
}

export function sectionContains(section: string, clause: string): boolean {
  return clause === section || clause.startsWith(`${section}.`);
}

export function buildSectionTree(
  sections: StandardSection[],
): RequirementSectionNode[] {
  const nodes = new Map<string, RequirementSectionNode>();
  for (const section of sections) {
    nodes.set(section.clause, { ...section, children: [] });
  }

  const roots: RequirementSectionNode[] = [];
  for (const section of sections) {
    const node = nodes.get(section.clause);
    if (!node) continue;
    const parent = nodes.get(parentClause(section.clause) ?? "");
    if (parent) parent.children.push(node);
    else roots.push(node);
  }
  return roots;
}

function visitSubtree(
  node: RequirementSectionNode,
  visit: (clause: string) => void,
): void {
  visit(node.clause);
  for (const child of node.children) visitSubtree(child, visit);
}

function nodesByClause(
  roots: RequirementSectionNode[],
): Map<string, RequirementSectionNode> {
  const nodes = new Map<string, RequirementSectionNode>();
  const add = (node: RequirementSectionNode) => {
    nodes.set(node.clause, node);
    for (const child of node.children) add(child);
  };
  for (const root of roots) add(root);
  return nodes;
}

export function decodeSectionSelection(
  tokens: string[],
  roots: RequirementSectionNode[],
): Set<string> {
  const nodes = nodesByClause(roots);
  const selected = new Set<string>();
  for (const token of tokens) {
    const exact = token.startsWith("=");
    const clause = exact ? token.slice(1) : token;
    const node = nodes.get(clause);
    if (!node) continue;
    if (exact) selected.add(clause);
    else visitSubtree(node, (value) => selected.add(value));
  }
  return selected;
}

interface EncodedSelection {
  all: boolean;
  any: boolean;
  tokens: string[];
}

function encodeNode(
  node: RequirementSectionNode,
  selected: ReadonlySet<string>,
): EncodedSelection {
  const children = node.children.map((child) => encodeNode(child, selected));
  const own = selected.has(node.clause);
  const all = own && children.every((child) => child.all);
  if (all) return { all: true, any: true, tokens: [node.clause] };

  const tokens = [
    ...(own ? [`=${node.clause}`] : []),
    ...children.flatMap((child) => child.tokens),
  ];
  return {
    all: false,
    any: own || children.some((child) => child.any),
    tokens,
  };
}

export function encodeSectionSelection(
  selected: ReadonlySet<string>,
  roots: RequirementSectionNode[],
): string[] {
  return roots.flatMap((root) => encodeNode(root, selected).tokens);
}

export function sectionSelectionState(
  node: RequirementSectionNode,
  selected: ReadonlySet<string>,
): { checked: boolean; indeterminate: boolean } {
  let selectedCount = 0;
  let total = 0;
  visitSubtree(node, (clause) => {
    total += 1;
    if (selected.has(clause)) selectedCount += 1;
  });
  return {
    checked: total > 0 && selectedCount === total,
    indeterminate: selectedCount > 0 && selectedCount < total,
  };
}

export function toggleSectionSelection(
  tokens: string[],
  clause: string,
  checked: boolean,
  roots: RequirementSectionNode[],
): string[] {
  const selected = decodeSectionSelection(tokens, roots);
  const nodes = nodesByClause(roots);
  const node = nodes.get(clause);
  if (!node) return encodeSectionSelection(selected, roots);
  visitSubtree(node, (value) => {
    if (checked) selected.add(value);
    else selected.delete(value);
  });
  return encodeSectionSelection(selected, roots);
}
