import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EvidenceView } from "./EvidenceView";
import { makeTestDataset } from "./testDataset";

const originalScrollIntoView = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "scrollIntoView",
);

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  if (originalScrollIntoView) {
    Object.defineProperty(
      HTMLElement.prototype,
      "scrollIntoView",
      originalScrollIntoView,
    );
  } else {
    Reflect.deleteProperty(HTMLElement.prototype, "scrollIntoView");
  }
});

describe("EvidenceView", () => {
  it("reveals the selected case initially and when selection changes", async () => {
    const dataset = makeTestDataset();
    const first = dataset.cases[0];
    if (!first) throw new Error("incomplete test dataset");
    const second = {
      ...first,
      id: "ch41-deep-linked-case",
      title: "Case selected from a deep link",
    };
    dataset.cases.push(second);
    const scrollIntoView = vi.fn();
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollIntoView,
    });

    const props = {
      cases: dataset.cases,
      requirements: dataset.requirements,
      campaign: dataset.campaigns[0],
      toolFilter: "",
      profileFilter: "",
      onSelectCase: () => undefined,
      onInspectRequirement: () => undefined,
    };
    const view = render(<EvidenceView {...props} selectedCaseId={second.id} />);

    await waitFor(() => {
      expect(scrollIntoView).toHaveBeenCalledWith({
        block: "nearest",
        inline: "nearest",
      });
    });
    expect(
      screen.getByRole("heading", { name: "Case selected from a deep link" }),
    ).toBeTruthy();

    scrollIntoView.mockReset();
    view.rerender(<EvidenceView {...props} selectedCaseId={first.id} />);
    await waitFor(() => expect(scrollIntoView).toHaveBeenCalledOnce());
  });

  it("copies the selected campaign in a case deep link", async () => {
    const dataset = makeTestDataset();
    const testCase = dataset.cases[0];
    const campaign = dataset.campaigns[0];
    if (!testCase || !campaign) throw new Error("incomplete test dataset");
    campaign.id = "20251201T000000Z-selected";
    const writeText = vi.fn().mockResolvedValue(undefined);
    const navigatorWithClipboard = Object.create(navigator) as Navigator;
    Object.defineProperty(navigatorWithClipboard, "clipboard", {
      value: { writeText },
    });
    vi.stubGlobal("navigator", navigatorWithClipboard);

    render(
      <EvidenceView
        cases={dataset.cases}
        requirements={dataset.requirements}
        campaign={campaign}
        toolFilter=""
        profileFilter=""
        selectedCaseId={testCase.id}
        onSelectCase={() => undefined}
        onInspectRequirement={() => undefined}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Copy link" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledOnce());
    expect(new URL(writeText.mock.calls[0]?.[0] as string).search).toBe(
      `?view=evidence&caseId=${testCase.id}&campaign=${campaign.id}`,
    );
  });

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
        profileFilter=""
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
        profileFilter=""
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
      "simulate",
    );

    fireEvent.click(
      screen.getByRole("button", { name: /SV-2023-13-OUTPUT-COPYOUT/ }),
    );
    expect(inspectRequirement).toHaveBeenCalledWith("SV-2023-13-OUTPUT-COPYOUT");
  });

  it("shows unsupported tool capability simply as Not applicable", () => {
    const dataset = makeTestDataset();
    const campaign = dataset.campaigns[0];
    const result = campaign?.results[0];
    const testCase = dataset.cases.find((item) => item.id === result?.case_id);
    if (!campaign || !result || !testCase) {
      throw new Error("incomplete test dataset");
    }
    result.status = "unsupported-capability";
    result.reason = "unsupported-phase";

    render(
      <EvidenceView
        cases={dataset.cases}
        requirements={dataset.requirements}
        campaign={campaign}
        toolFilter=""
        profileFilter=""
        selectedCaseId={testCase.id}
        onSelectCase={() => undefined}
        onInspectRequirement={() => undefined}
      />,
    );

    expect(screen.getByText("Not applicable")).toBeTruthy();
    expect(screen.queryByText("Not applicable · profile scope")).toBeNull();
    expect(screen.getByText("unsupported-phase")).toBeTruthy();
  });

  it("shows cumulative evidence through a later phase", () => {
    const dataset = makeTestDataset();
    const testCase = dataset.cases[0];
    const campaign = dataset.campaigns[0];
    const result = campaign?.results[0];
    const observation = result?.observations[0];
    if (!testCase || !campaign || !result || !observation) {
      throw new Error("incomplete test dataset");
    }
    testCase.target_phase = "parse";
    testCase.expectation = "reject";
    testCase.oracle = {
      kind: "diagnostic-at-anchor",
      anchor: `SVTORTURE_DIAG_ANCHOR:${testCase.id}`,
    };
    result.target_phase = "parse";
    result.evidence_mode = "cumulative";
    result.summary = "The tool rejected the anchored construct.";
    observation.kind = "compile";
    observation.attempted_through_phase = "elaborate";
    observation.exit_code = 1;
    observation.stdout.excerpt = "";
    observation.stdout.size_bytes = 0;
    observation.diagnostics = [
      {
        severity: "error",
        message: "target diagnostic",
        source: "$CASE/top.sv",
        line: 2,
        target_case_id: testCase.id,
      },
    ];

    render(
      <EvidenceView
        cases={dataset.cases}
        requirements={dataset.requirements}
        campaign={campaign}
        toolFilter=""
        profileFilter=""
        selectedCaseId={testCase.id}
        onSelectCase={() => undefined}
        onInspectRequirement={() => undefined}
      />,
    );

    expect(screen.getByText("Target phase").parentElement?.textContent).toContain(
      "parse",
    );
    expect(screen.getByText("Evidence mode").parentElement?.textContent).toContain(
      "cumulative",
    );
    expect(screen.getByText("Attempted through").parentElement?.textContent).toContain(
      "elaborate",
    );
    expect(screen.getByText("through elaborate")).toBeTruthy();
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
        profileFilter=""
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
