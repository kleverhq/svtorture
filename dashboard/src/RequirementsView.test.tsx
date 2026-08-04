import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RequirementsView, requirementTreeTone } from "./RequirementsView";
import { makeTestDataset } from "./testDataset";
import type { Requirement } from "./types";

const originalScrollIntoView = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "scrollIntoView",
);
const originalMatchMedia = Object.getOwnPropertyDescriptor(window, "matchMedia");

afterEach(() => {
  cleanup();
  if (originalScrollIntoView) {
    Object.defineProperty(
      HTMLElement.prototype,
      "scrollIntoView",
      originalScrollIntoView,
    );
  } else {
    Reflect.deleteProperty(HTMLElement.prototype, "scrollIntoView");
  }
  if (originalMatchMedia) {
    Object.defineProperty(window, "matchMedia", originalMatchMedia);
  } else {
    Reflect.deleteProperty(window, "matchMedia");
  }
});

function SelectionHarness({ requirements }: { requirements: Requirement[] }) {
  const dataset = makeTestDataset();
  const [sections, setSections] = useState<string[]>([]);
  return (
    <RequirementsView
      requirements={requirements}
      allRequirements={requirements}
      standardSections={[
        { clause: "13", title: "Tasks and functions" },
        { clause: "13.5", title: "Subroutine arguments" },
        { clause: "13.5.1", title: "Arguments by value" },
        { clause: "13.5.2", title: "Arguments by reference" },
        { clause: "14", title: "Clocking blocks" },
      ]}
      selectedSections={sections}
      onSelectedSectionsChange={setSections}
      cases={dataset.cases}
      campaign={dataset.campaigns[0]}
      toolFilter=""
      profileFilter=""
      selectedRequirementId=""
      onSelectRequirement={() => undefined}
      onInspectCase={() => undefined}
      onInspectEvidence={() => undefined}
    />
  );
}

describe("RequirementsView", () => {
  it("uses the accepted worst-status hierarchy", () => {
    expect(requirementTreeTone(["conforming", "not-run"])).toBe("green");
    expect(requirementTreeTone(["conforming", "unsupported-capability"])).toBe(
      "green",
    );
    expect(requirementTreeTone(["not-applicable", "not-run"])).toBe("gray");
    expect(requirementTreeTone(["conforming", "inconclusive"])).toBe("yellow");
    expect(requirementTreeTone(["conforming", "nonconforming"])).toBe("red");
    expect(requirementTreeTone(["harness-error"])).toBe("red");
  });

  it("renders every compact card with applicability and expandable evidence", async () => {
    const dataset = makeTestDataset();
    const first = dataset.requirements[0];
    const testCase = dataset.cases[0];
    const campaign = dataset.campaigns[0];
    if (!first || !testCase || !campaign) {
      throw new Error("incomplete test dataset");
    }
    const second = {
      ...first,
      id: "SV-2023-14-SECOND",
      clause: "14",
      part: "14",
      summary: "Second visible requirement card",
      tags: ["clocking", "scheduling"],
    };
    const requirements = [first, second];
    const scrollIntoView = vi.fn();
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollIntoView,
    });
    const inspectCase = vi.fn();
    const inspectEvidence = vi.fn();
    const toggleTag = vi.fn();

    render(
      <RequirementsView
        requirements={requirements}
        allRequirements={requirements}
        standardSections={dataset.standard_sections}
        selectedSections={[]}
        onSelectedSectionsChange={() => undefined}
        selectedTags={["scheduling"]}
        onToggleTag={toggleTag}
        cases={dataset.cases}
        campaign={campaign}
        toolFilter=""
        profileFilter=""
        selectedRequirementId={second.id}
        onSelectRequirement={() => undefined}
        onInspectCase={inspectCase}
        onInspectEvidence={inspectEvidence}
      />,
    );

    expect(screen.getAllByRole("article")).toHaveLength(2);
    const card = screen.getByRole("article", { name: `Requirement ${second.id}` });
    expect(
      within(card).getByRole("heading", { name: second.summary }),
    ).toBeTruthy();
    const applicability = within(card).getByRole("table");
    expect(within(applicability).getByText("1800-2012")).toBeTruthy();
    expect(within(applicability).getByText("1800-2017")).toBeTruthy();
    expect(within(applicability).getByText("1800-2023")).toBeTruthy();
    const clockingTag = within(card).getByRole("button", { name: "clocking" });
    const schedulingTag = within(card).getByRole("button", {
      name: "scheduling",
    });
    expect(schedulingTag.getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(clockingTag);
    expect(toggleTag).toHaveBeenCalledWith("clocking");
    expect(within(card).getByRole("button", { name: "Copy link" })).toBeTruthy();

    const details = card.querySelectorAll("details");
    expect(details).toHaveLength(3);
    expect([...details].every((item) => !item.open)).toBe(true);
    fireEvent.click(within(card).getByText(/Tool evidence/));
    const profile = await within(card).findByText("fake/simulator");
    expect(profile.closest(".tool-judgments > details")).toBeTruthy();
    fireEvent.click(profile);
    const evidence = await within(card).findByRole("button", {
      name: new RegExp(`^View cases for ${second.id} with fake/simulator`),
    });
    fireEvent.click(evidence);
    expect(inspectEvidence).toHaveBeenCalledWith("fake", "simulator", second.id);

    const firstCard = screen.getByRole("article", {
      name: `Requirement ${first.id}`,
    });
    fireEvent.click(within(firstCard).getByText(/Supporting cases/));
    fireEvent.click(await within(firstCard).findByText(testCase.title));
    expect(inspectCase).toHaveBeenCalledWith(testCase.id);
    await waitFor(() =>
      expect(scrollIntoView).toHaveBeenCalledWith({ block: "start" }),
    );
  });

  it("filters by checked subtrees and exposes parent indeterminate state", () => {
    const dataset = makeTestDataset();
    const first = dataset.requirements[0];
    if (!first) throw new Error("incomplete test dataset");
    const byValue = { ...first, clause: "13.5.1", id: "SV-2023-13-BY-VALUE" };
    const byReference = {
      ...first,
      clause: "13.5.2",
      id: "SV-2023-13-BY-REFERENCE",
    };
    const clocking = {
      ...first,
      clause: "14",
      part: "14",
      id: "SV-2023-14-CLOCKING",
    };
    render(
      <SelectionHarness requirements={[byValue, byReference, clocking]} />,
    );

    expect(
      (screen.getByRole("radio", { name: /^All/ }) as HTMLInputElement).checked,
    ).toBe(true);
    fireEvent.click(
      screen.getByRole("button", {
        name: "Expand 13 Tasks and functions",
      }),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: "Expand 13.5 Subroutine arguments",
      }),
    );
    fireEvent.click(screen.getByLabelText("Select 13 Tasks and functions"));
    expect(screen.getAllByRole("article")).toHaveLength(2);
    expect(
      (screen.getByLabelText("Select 13.5.1 Arguments by value") as HTMLInputElement)
        .checked,
    ).toBe(true);

    fireEvent.click(
      screen.getByLabelText("Select 13.5.1 Arguments by value"),
    );
    const chapter = screen.getByLabelText(
      "Select 13 Tasks and functions",
    ) as HTMLInputElement;
    expect(chapter.checked).toBe(false);
    expect(chapter.indeterminate).toBe(true);
    expect(screen.getAllByRole("article")).toHaveLength(1);
    expect(
      screen.getByRole("article", { name: `Requirement ${byReference.id}` }),
    ).toBeTruthy();

    fireEvent.click(screen.getByRole("radio", { name: /^All/ }));
    expect(screen.getAllByRole("article")).toHaveLength(3);
  });

  it("navigates by section title and colors only a selected tool", () => {
    const dataset = makeTestDataset();
    const first = dataset.requirements[0];
    const campaign = dataset.campaigns[0];
    if (!first || !campaign) throw new Error("incomplete test dataset");
    const clocking = {
      ...first,
      clause: "14",
      part: "14",
      id: "SV-2023-14-CLOCKING",
      summary: "Clocking requirement",
    };
    const grayCase = {
      ...dataset.cases[0]!,
      id: "ch13-gray-evidence",
      primary_requirement: first.id,
    };
    const campaignWithGray = {
      ...campaign,
      case_ids: [...campaign.case_ids, grayCase.id],
      results: [
        ...campaign.results,
        {
          ...campaign.results[0]!,
          case_id: grayCase.id,
          status: "unsupported-capability" as const,
          reason: "unsupported-by-profile",
        },
      ],
    };
    const scrollIntoView = vi.fn();
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollIntoView,
    });
    const onSelectRequirement = vi.fn();
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: vi.fn(() => ({ matches: true })),
    });

    const view = render(
      <RequirementsView
        requirements={[first, clocking]}
        allRequirements={[first, clocking]}
        standardSections={dataset.standard_sections}
        selectedSections={[]}
        onSelectedSectionsChange={() => undefined}
        cases={[...dataset.cases, grayCase]}
        campaign={campaignWithGray}
        toolFilter=""
        profileFilter=""
        selectedRequirementId=""
        onSelectRequirement={onSelectRequirement}
        onInspectCase={() => undefined}
        onInspectEvidence={() => undefined}
      />,
    );

    const chapter13 = screen
      .getByText("Tasks and functions (subroutines)")
      .closest("button");
    if (!chapter13) throw new Error("chapter navigation is missing");
    expect(chapter13.closest(".requirement-toc__row")?.className).not.toMatch(
      /--(?:red|yellow|green|gray)/,
    );
    fireEvent.click(chapter13);
    expect(onSelectRequirement).toHaveBeenCalledWith(first.id);
    expect(scrollIntoView).toHaveBeenCalledWith({
      block: "start",
      behavior: "auto",
    });

    view.rerender(
      <RequirementsView
        requirements={[first, clocking]}
        allRequirements={[first, clocking]}
        standardSections={dataset.standard_sections}
        selectedSections={[]}
        onSelectedSectionsChange={() => undefined}
        cases={[...dataset.cases, grayCase]}
        campaign={campaignWithGray}
        toolFilter="fake"
        profileFilter=""
        selectedRequirementId=""
        onSelectRequirement={onSelectRequirement}
        onInspectCase={() => undefined}
        onInspectEvidence={() => undefined}
      />,
    );
    expect(
      screen
        .getByText("Tasks and functions (subroutines)")
        .closest(".requirement-toc__row")?.classList.contains(
          "requirement-toc__row--green",
        ),
    ).toBe(true);
    expect(screen.getByLabelText("Section result: Passing").textContent).toBe("✓");
    expect(
      screen
        .getByText("Clocking blocks")
        .closest(".requirement-toc__row")?.classList.contains(
          "requirement-toc__row--gray",
        ),
    ).toBe(true);
  });

  it("ignores unknown section tokens instead of hiding requirements", () => {
    const dataset = makeTestDataset();
    render(
      <RequirementsView
        requirements={dataset.requirements}
        allRequirements={dataset.requirements}
        standardSections={dataset.standard_sections}
        selectedSections={["missing", "=also-missing"]}
        onSelectedSectionsChange={() => undefined}
        cases={dataset.cases}
        campaign={dataset.campaigns[0]}
        toolFilter=""
        profileFilter=""
        selectedRequirementId=""
        onSelectRequirement={() => undefined}
        onInspectCase={() => undefined}
        onInspectEvidence={() => undefined}
      />,
    );

    expect(screen.getAllByRole("article")).toHaveLength(1);
    expect(
      (screen.getByRole("radio", { name: /^All/ }) as HTMLInputElement).checked,
    ).toBe(true);
  });

  it("keeps the complete tree when quick filters match no requirements", () => {
    const dataset = makeTestDataset();
    render(
      <RequirementsView
        requirements={[]}
        allRequirements={dataset.requirements}
        standardSections={dataset.standard_sections}
        selectedSections={[]}
        onSelectedSectionsChange={() => undefined}
        cases={dataset.cases}
        campaign={dataset.campaigns[0]}
        toolFilter=""
        profileFilter=""
        selectedRequirementId=""
        onSelectRequirement={() => undefined}
        onInspectCase={() => undefined}
        onInspectEvidence={() => undefined}
      />,
    );

    expect(screen.getByRole("list", { name: "Standard sections" })).toBeTruthy();
    expect(screen.getByText("No requirements match the current quick filters.")).toBeTruthy();
  });
});
