import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EvidenceView } from "./EvidenceView";
import { makeTestDataset } from "./testDataset";
import type { Result } from "./types";

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
  if (originalScrollTo) {
    Object.defineProperty(HTMLElement.prototype, "scrollTo", originalScrollTo);
  } else {
    Reflect.deleteProperty(HTMLElement.prototype, "scrollTo");
  }
});

describe("EvidenceView", () => {
  it("labels annex locations consistently in the list and detail", () => {
    const dataset = makeTestDataset();
    const testCase = dataset.cases[0];
    const requirement = dataset.requirements[0];
    if (!testCase || !requirement) throw new Error("incomplete test dataset");
    requirement.part = "A";
    requirement.clause = "A.1";

    render(
      <EvidenceView
        cases={dataset.cases}
        requirements={dataset.requirements}
        campaign={dataset.campaigns[0]}
        toolFilter=""
        profileFilter=""
        selectedCaseId={testCase.id}
        onSelectCase={() => undefined}
        onInspectRequirement={() => undefined}
      />,
    );

    expect(screen.getByText(/Annex A\.1/)).toBeTruthy();
  });

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

    await waitFor(() =>
      expect(scrollIntoView).toHaveBeenCalledWith({ block: "start" }),
    );
    expect(
      screen.getByRole("heading", { name: "Case selected from a deep link" }),
    ).toBeTruthy();

    scrollIntoView.mockReset();
    view.rerender(<EvidenceView {...props} selectedCaseId={first.id} />);
    await waitFor(() =>
      expect(scrollIntoView).toHaveBeenCalledWith({ block: "start" }),
    );
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

  it("loads detailed evidence only after its disclosure opens", async () => {
    const dataset = makeTestDataset();
    const testCase = dataset.cases[0];
    const campaign = dataset.campaigns[0];
    if (!testCase || !campaign) throw new Error("incomplete test dataset");
    const loadCaseEvidence = vi.fn().mockResolvedValue(campaign.results);

    render(
      <EvidenceView
        cases={dataset.cases}
        requirements={dataset.requirements}
        campaign={campaign}
        toolFilter=""
        profileFilter=""
        selectedCaseId=""
        onSelectCase={() => undefined}
        onInspectRequirement={() => undefined}
        loadCaseEvidence={loadCaseEvidence}
      />,
    );

    expect(loadCaseEvidence).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText(/Tool evidence/));
    await waitFor(() =>
      expect(loadCaseEvidence).toHaveBeenCalledWith(testCase.id),
    );
    expect(await screen.findByText("fake/simulator")).toBeTruthy();
  });

  it("connects case cards to hierarchy and tag actions", () => {
    const dataset = makeTestDataset();
    const firstCase = dataset.cases[0];
    const firstRequirement = dataset.requirements[0];
    if (!firstCase || !firstRequirement) {
      throw new Error("incomplete test dataset");
    }
    const secondRequirement = {
      ...firstRequirement,
      id: "SV-2023-14-SECOND-CASE",
      part: "14",
      clause: "14.2",
      summary: "A second case requirement",
    };
    const secondCase = {
      ...firstCase,
      id: "ch14-second-case",
      title: "A second case card",
      primary_requirement: secondRequirement.id,
      tags: ["second"],
    };
    const changeSections = vi.fn();
    const toggleTag = vi.fn();

    render(
      <EvidenceView
        cases={[firstCase, secondCase]}
        allCases={[firstCase, secondCase]}
        requirements={[firstRequirement, secondRequirement]}
        standardSections={[
          { clause: "13", title: "Tasks and functions" },
          { clause: "13.5", title: "Arguments" },
          { clause: "14", title: "Clocking blocks" },
          { clause: "14.2", title: "Clocking declarations" },
        ]}
        selectedSections={[]}
        onSelectedSectionsChange={changeSections}
        selectedTags={["copy-out"]}
        onToggleTag={toggleTag}
        campaign={dataset.campaigns[0]}
        toolFilter=""
        profileFilter=""
        selectedCaseId=""
        onSelectCase={() => undefined}
        onInspectRequirement={() => undefined}
      />,
    );

    expect(screen.getAllByRole("article", { name: /^Case / })).toHaveLength(2);
    const firstCard = screen.getByRole("article", { name: `Case ${firstCase.id}` });
    const copyOut = within(firstCard).getByRole("button", { name: "copy-out" });
    expect(copyOut.getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(copyOut);
    expect(toggleTag).toHaveBeenCalledWith("copy-out");
    fireEvent.click(screen.getByLabelText(/Select 13 Tasks and functions/));
    expect(changeSections).toHaveBeenCalledWith(["13"]);
    fireEvent.click(
      screen.getByRole("button", { name: "13 Tasks and functions" }),
    );
    expect(document.activeElement).toBe(
      within(firstCard).getByRole("heading", { name: firstCase.title }),
    );
  });

  it("retries a failed detailed evidence request", async () => {
    const dataset = makeTestDataset();
    const testCase = dataset.cases[0];
    const campaign = dataset.campaigns[0];
    if (!testCase || !campaign) throw new Error("incomplete test dataset");
    const loadCaseEvidence = vi
      .fn()
      .mockRejectedValueOnce(new Error("temporary outage"))
      .mockResolvedValueOnce(campaign.results);

    render(
      <EvidenceView
        cases={dataset.cases}
        requirements={dataset.requirements}
        campaign={campaign}
        toolFilter=""
        profileFilter=""
        selectedCaseId=""
        onSelectCase={() => undefined}
        onInspectRequirement={() => undefined}
        loadCaseEvidence={loadCaseEvidence}
      />,
    );

    const summary = screen.getByText(/Tool evidence/);
    fireEvent.click(summary);
    expect(await screen.findAllByText(/temporary outage/)).toHaveLength(2);
    const failureMessage = document.querySelector(".tool-evidence-message");
    expect(failureMessage?.textContent).toContain("temporary outage");
    expect(failureMessage?.classList.contains("empty-state")).toBe(false);
    fireEvent.click(summary);
    await waitFor(() => expect(summary.closest("details")?.open).toBe(false));
    fireEvent.click(summary);
    await waitFor(() => expect(loadCaseEvidence).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("Detailed evidence loaded")).toBeTruthy();
  });

  it("ignores an in-flight detail response after campaign changes", async () => {
    const dataset = makeTestDataset();
    const testCase = dataset.cases[0];
    const campaign = dataset.campaigns[0];
    const result = campaign?.results[0];
    if (!testCase || !campaign || !result) {
      throw new Error("incomplete test dataset");
    }
    let resolveOld: ((results: Result[]) => void) | undefined;
    const loadCaseEvidence = vi.fn(
      () =>
        new Promise<Result[]>((resolve) => {
          resolveOld = resolve;
        }),
    );
    const props = {
      cases: dataset.cases,
      requirements: dataset.requirements,
      toolFilter: "",
      profileFilter: "",
      selectedCaseId: "",
      onSelectCase: () => undefined,
      onInspectRequirement: () => undefined,
      loadCaseEvidence,
    };
    const view = render(<EvidenceView {...props} campaign={campaign} />);

    fireEvent.click(screen.getByText(/Tool evidence/));
    await waitFor(() => expect(loadCaseEvidence).toHaveBeenCalledOnce());
    const resolveFirstRequest = resolveOld;
    view.rerender(
      <EvidenceView
        {...props}
        campaign={{ ...campaign, id: "20251201T000000Z-new-campaign" }}
      />,
    );
    await waitFor(() => expect(loadCaseEvidence).toHaveBeenCalledTimes(2));
    await act(async () => {
      resolveFirstRequest?.([{ ...result, summary: "stale campaign evidence" }]);
      await Promise.resolve();
    });
    expect(screen.queryByText("Detailed evidence loaded")).toBeNull();
    expect(
      screen.getByText("Loading detailed evidence").closest("div")?.getAttribute(
        "aria-busy",
      ),
    ).toBe("true");
  });

  it("opens embedded source and navigates back to its requirement", async () => {
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

    fireEvent.click(screen.getByText(/Oracle and sources/));
    const source = await screen.findByRole("button", { name: "top.sv" });
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
    fireEvent.click(screen.getByText(/Oracle and sources/));
    await waitFor(() =>
      expect(screen.queryByLabelText("Source top.sv")).toBeNull(),
    );
    fireEvent.click(screen.getByText(/Oracle and sources/));
    expect(screen.queryByLabelText("Source top.sv")).toBeNull();
    fireEvent.click(await screen.findByRole("button", { name: "top.sv" }));
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

    fireEvent.click(screen.getByText(/Tool evidence/));
    fireEvent.click(await screen.findByText("fake/simulator"));
    expect(
      screen.getAllByText("Target phase").at(-1)?.parentElement?.textContent,
    ).toContain("simulate");
    expect(screen.getByText("Evidence mode").parentElement?.textContent).toContain(
      "direct",
    );
    expect(screen.getByText("Attempted through").parentElement?.textContent).toContain(
      "simulate",
    );

    fireEvent.click(screen.getByText(/Requirements/));
    fireEvent.click(
      await screen.findByRole("button", { name: /SV-2023-13-OUTPUT-COPYOUT/ }),
    );
    expect(inspectRequirement).toHaveBeenCalledWith("SV-2023-13-OUTPUT-COPYOUT");
  });

  it("shows unsupported tool capability simply as Not applicable", async () => {
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

    fireEvent.click(screen.getByText(/Tool evidence/));
    expect(await screen.findByText("Not applicable")).toBeTruthy();
    expect(screen.queryByText("Not applicable · profile scope")).toBeNull();
    expect(screen.getByText("unsupported-phase")).toBeTruthy();
  });

  it("shows cumulative evidence through a later phase", async () => {
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

    fireEvent.click(screen.getByText(/Tool evidence/));
    fireEvent.click(await screen.findByText("fake/simulator"));
    expect(
      (await screen.findByText("Target phase")).parentElement?.textContent,
    ).toContain(
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

  it("does not navigate to malformed or untrusted source links", async () => {
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

    fireEvent.click(screen.getByText(/Oracle and sources/));
    expect(await screen.findByText("top.sv · unavailable")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "top.sv" })).toBeNull();
    expect(screen.queryByRole("link", { name: /top\.sv/ })).toBeNull();
  });
});
