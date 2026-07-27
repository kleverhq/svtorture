import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MatrixView } from "./MatrixView";
import { makeTestDataset } from "./testDataset";

const virtualizerMock = vi.hoisted(() => ({
  scrollToIndex: vi.fn(),
}));

vi.mock("@tanstack/react-virtual", () => ({
  useWindowVirtualizer: ({ count, scrollMargin }: { count: number; scrollMargin: number }) => ({
    getTotalSize: () => count * 54,
    getVirtualItems: () =>
      Array.from({ length: count }, (_, index) => ({
        index,
        key: index,
        start: index * 54,
        size: 54,
      })),
    options: { scrollMargin },
    scrollToIndex: virtualizerMock.scrollToIndex,
  }),
}));

afterEach(() => {
  cleanup();
  virtualizerMock.scrollToIndex.mockReset();
});

describe("MatrixView", () => {
  it("reveals a non-first selected requirement through the virtualizer", async () => {
    const dataset = makeTestDataset();
    const first = dataset.requirements[0];
    if (!first) throw new Error("incomplete test dataset");
    const selected = {
      ...first,
      id: "SV-2023-41-DEEP-LINK",
      clause: "41.9",
      summary: "Requirement selected from a deep link",
    };
    dataset.requirements.push(selected);

    render(
      <MatrixView
        requirements={dataset.requirements}
        cases={dataset.cases}
        campaign={dataset.campaigns[0]}
        toolFilter=""
        profileFilter=""
        selectedRequirementId={selected.id}
        onSelectRequirement={() => undefined}
        onInspectCase={() => undefined}
      />,
    );

    await waitFor(() => {
      expect(virtualizerMock.scrollToIndex).toHaveBeenCalledWith(1, {
        align: "center",
      });
    });
    expect(screen.getByRole("complementary", { name: selected.id })).toBeTruthy();
  });
});
