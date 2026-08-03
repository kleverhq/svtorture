import { describe, expect, it } from "vitest";

import {
  buildSectionTree,
  decodeSectionSelection,
  encodeSectionSelection,
  sectionContains,
  sectionSelectionState,
  toggleSectionSelection,
} from "./requirementHierarchy";

const tree = buildSectionTree([
  { clause: "7", title: "Aggregate data types" },
  { clause: "7.2", title: "Structures and unions" },
  { clause: "7.2.1", title: "Packed structures" },
  { clause: "7.20", title: "Unrelated decimal sibling" },
  { clause: "8", title: "Classes" },
]);

describe("requirement hierarchy", () => {
  it("builds dotted ancestry without treating 7.20 as a child of 7.2", () => {
    expect(tree.map((node) => node.clause)).toEqual(["7", "8"]);
    expect(tree[0]?.children.map((node) => node.clause)).toEqual(["7.2", "7.20"]);
    expect(sectionContains("7.2", "7.2.1")).toBe(true);
    expect(sectionContains("7.2", "7.20")).toBe(false);
  });

  it("checks, partially clears, and canonically restores subtrees", () => {
    let tokens = toggleSectionSelection([], "7", true, tree);
    expect(tokens).toEqual(["7"]);
    let selected = decodeSectionSelection(tokens, tree);
    expect(sectionSelectionState(tree[0]!, selected)).toEqual({
      checked: true,
      indeterminate: false,
    });

    tokens = toggleSectionSelection(tokens, "7.2.1", false, tree);
    expect(tokens).toEqual(["=7", "=7.2", "7.20"]);
    selected = decodeSectionSelection(tokens, tree);
    expect(sectionSelectionState(tree[0]!, selected)).toEqual({
      checked: false,
      indeterminate: true,
    });
    expect(selected.has("7.2.1")).toBe(false);
    expect(selected.has("7.20")).toBe(true);

    tokens = toggleSectionSelection(tokens, "7.2.1", true, tree);
    expect(tokens).toEqual(["7"]);
  });

  it("preserves unrelated selections and drops unknown URL tokens", () => {
    const selected = decodeSectionSelection(["7.2", "missing", "=8"], tree);
    expect(encodeSectionSelection(selected, tree)).toEqual(["7.2", "8"]);
  });
});
