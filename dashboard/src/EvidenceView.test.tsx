import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EvidenceView } from "./EvidenceView";
import { makeTestDataset } from "./testDataset";

afterEach(cleanup);

describe("EvidenceView", () => {
  it("opens embedded source and navigates back to its requirement", () => {
    const dataset = makeTestDataset();
    const testCase = dataset.cases[0];
    const campaign = dataset.campaigns[0];
    if (!testCase || !campaign) throw new Error("incomplete test dataset");
    testCase.source_links = {
      "top.sv":
        "data:text/plain;charset=utf-8,module%20top%3B%0A%20%20initial%20%24finish%3B%0Aendmodule%0A",
    };
    const inspectRequirement = vi.fn();

    const view = render(
      <EvidenceView
        cases={dataset.cases}
        requirements={dataset.requirements}
        campaign={campaign}
        toolFilter=""
        selectedCaseId={testCase.id}
        onSelectCase={() => undefined}
        onInspectRequirement={inspectRequirement}
      />,
    );

    const source = screen.getByRole("button", { name: "top.sv" });
    expect(source.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(source);
    const viewer = screen.getByLabelText("Source top.sv");
    expect(source.getAttribute("aria-expanded")).toBe("true");
    expect(source.getAttribute("aria-controls")).toBe(viewer.id);
    expect(viewer.textContent).toContain("module top;");

    fireEvent.click(screen.getByRole("button", { name: "Close source" }));
    expect(document.activeElement).toBe(source);
    expect(screen.queryByLabelText("Source top.sv")).toBeNull();

    fireEvent.click(source);
    view.rerender(
      <EvidenceView
        cases={dataset.cases}
        requirements={dataset.requirements}
        campaign={{ ...campaign, id: "20260102T000000Z-next" }}
        toolFilter=""
        selectedCaseId={testCase.id}
        onSelectCase={() => undefined}
        onInspectRequirement={inspectRequirement}
      />,
    );
    expect(screen.queryByLabelText("Source top.sv")).toBeNull();

    expect(screen.getByText("Target phase").parentElement?.textContent).toContain(
      "simulate",
    );
    expect(screen.getByText("Evidence mode").parentElement?.textContent).toContain(
      "direct",
    );
    expect(screen.getByText("Attempted through").parentElement?.textContent).toContain(
      "not observed",
    );

    fireEvent.click(
      screen.getByRole("button", { name: /SV-2023-13-OUTPUT-COPYOUT/ }),
    );
    expect(inspectRequirement).toHaveBeenCalledWith("SV-2023-13-OUTPUT-COPYOUT");
  });

  it("does not navigate to malformed or untrusted source links", () => {
    const dataset = makeTestDataset();
    const testCase = dataset.cases[0];
    const campaign = dataset.campaigns[0];
    if (!testCase || !campaign) throw new Error("incomplete test dataset");
    testCase.source_links = {
      "top.sv": "data:text/plain;charset=utf-8,%ZZ",
    };

    render(
      <EvidenceView
        cases={dataset.cases}
        requirements={dataset.requirements}
        campaign={campaign}
        toolFilter=""
        selectedCaseId={testCase.id}
        onSelectCase={() => undefined}
        onInspectRequirement={() => undefined}
      />,
    );

    expect(screen.queryByRole("button", { name: "top.sv" })).toBeNull();
    expect(screen.queryByRole("link", { name: /top\.sv/ })).toBeNull();
    expect(screen.getByText("top.sv · unavailable")).toBeTruthy();
  });
});
