import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RequirementsView } from "./RequirementsView";
import { makeTestDataset } from "./testDataset";

const originalScrollIntoView = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "scrollIntoView",
);
const originalScrollTo = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "scrollTo",
);

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
  if (originalScrollTo) {
    Object.defineProperty(HTMLElement.prototype, "scrollTo", originalScrollTo);
  } else {
    Reflect.deleteProperty(HTMLElement.prototype, "scrollTo");
  }
});

describe("RequirementsView", () => {
  it("renders a scalable list and details for primary and related evidence", async () => {
    const dataset = makeTestDataset();
    const first = dataset.requirements[0];
    const testCase = dataset.cases[0];
    const campaign = dataset.campaigns[0];
    const tool = campaign?.tools[0];
    if (!first || !testCase || !campaign || !tool) {
      throw new Error("incomplete test dataset");
    }
    const selected = {
      ...first,
      id: "SV-2023-41-DEEP-LINK",
      clause: "41.9",
      summary: "Requirement selected from a deep link",
    };
    dataset.requirements.push(selected);
    testCase.related_requirements = [selected.id];
    tool.profile_ids = [
      "simulator",
      "profile-2",
      "profile-3",
      "profile-4",
      "profile-5",
      "profile-6",
    ];
    const scrollIntoView = vi.fn();
    const scrollTo = vi.fn();
    Object.defineProperties(HTMLElement.prototype, {
      scrollIntoView: { configurable: true, value: scrollIntoView },
      scrollTo: { configurable: true, value: scrollTo },
    });
    const selectRequirement = vi.fn();
    const inspectCase = vi.fn();

    render(
      <RequirementsView
        requirements={dataset.requirements}
        cases={dataset.cases}
        campaign={campaign}
        toolFilter=""
        profileFilter=""
        selectedRequirementId={selected.id}
        onSelectRequirement={selectRequirement}
        onInspectCase={inspectCase}
      />,
    );

    await waitFor(() => {
      expect(scrollIntoView).toHaveBeenCalledWith({
        block: "nearest",
        inline: "nearest",
      });
    });
    expect(scrollTo).toHaveBeenCalledWith({ top: 0 });
    expect(screen.queryByRole("table")).toBeNull();

    const list = screen.getByRole("listbox", { name: "Requirements" });
    const options = within(list).getAllByRole("option");
    expect(options).toHaveLength(2);
    expect(options[0]?.getAttribute("tabindex")).toBe("-1");
    expect(options[1]?.getAttribute("tabindex")).toBe("0");
    expect(
      within(list).getAllByLabelText(/^fake\//, { selector: ".verdict-dot" }),
    ).toHaveLength(12);

    const detail = screen.getByRole("article");
    expect(
      within(detail).getByRole("heading", {
        name: "Requirement selected from a deep link",
      }),
    ).toBeTruthy();
    expect(detail.querySelectorAll(".requirement-profile")).toHaveLength(6);
    expect(within(detail).getByText(testCase.title)).toBeTruthy();
    expect(within(detail).getByRole("button", { name: "Copy link" })).toBeTruthy();

    fireEvent.click(within(detail).getByText(testCase.title));
    expect(inspectCase).toHaveBeenCalledWith(testCase.id);
    fireEvent.keyDown(options[1] as HTMLElement, { key: "ArrowUp" });
    expect(selectRequirement).toHaveBeenCalledWith(first.id);
  });

  it("measures the split workspace when filters reveal requirements", async () => {
    const dataset = makeTestDataset();
    const requirement = dataset.requirements[0];
    if (!requirement) throw new Error("incomplete test dataset");
    const props = {
      cases: dataset.cases,
      campaign: dataset.campaigns[0],
      toolFilter: "",
      profileFilter: "",
      selectedRequirementId: "",
      onSelectRequirement: () => undefined,
      onInspectCase: () => undefined,
    };
    const view = render(<RequirementsView {...props} requirements={[]} />);
    expect(screen.getByText("No requirements match the current filters.")).toBeTruthy();

    view.rerender(
      <RequirementsView {...props} requirements={[requirement]} />,
    );
    await waitFor(() => {
      expect(
        document
          .querySelector<HTMLElement>(".requirements-workspace")
          ?.style.getPropertyValue("--split-workspace-height"),
      ).not.toBe("");
    });
  });
});
