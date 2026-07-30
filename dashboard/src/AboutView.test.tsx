import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { AboutView } from "./AboutView";

const SECTIONS = [
  ["overview", "Overview"],
  ["requirements", "Requirements"],
  ["cases", "Cases"],
  ["tools", "Tools"],
  ["campaigns", "Campaigns"],
  ["dashboard", "Dashboard"],
] as const;

afterEach(cleanup);

describe("AboutView", () => {
  it("links its table of contents to every guide section", () => {
    render(<AboutView />);

    const contents = screen.getByRole("navigation", { name: "About contents" });
    for (const [id, label] of SECTIONS) {
      expect(within(contents).getByRole("link", { name: label }).getAttribute("href"))
        .toBe(`#${id}`);
      expect(document.getElementById(id)).toBeTruthy();
      expect(screen.getByRole("heading", { name: label })).toBeTruthy();
    }
  });

  it("presents the framework as a concise illustrated evidence flow", () => {
    render(<AboutView />);

    expect(
      screen.getByRole("heading", {
        name: "From standard text to reproducible evidence",
      }),
    ).toBeTruthy();
    const images = screen.getAllByRole("img");
    expect(images).toHaveLength(5);
    expect(
      screen.getAllByRole("region", { name: /Scrollable diagram:/ }),
    ).toHaveLength(5);
    for (const image of images) {
      const descriptionId = image.getAttribute("aria-describedby");
      expect(descriptionId).toBeTruthy();
      expect(document.getElementById(descriptionId ?? "")?.textContent?.length).toBeGreaterThan(80);
    }
    expect(
      screen.getByAltText(
        "Flow from the IEEE standard through requirements and cases to campaign evidence",
      ),
    ).toBeTruthy();
    expect(
      screen.getByAltText(
        "Traceable requirements linked to standard anchors and corpus metrics",
      ),
    ).toBeTruthy();
    expect(
      screen.getByAltText(
        "Executable cases pairing source code with phase-specific oracles",
      ),
    ).toBeTruthy();
    expect(
      screen.getByAltText(
        "Cumulative tool phases and the checks that decide case applicability",
      ),
    ).toBeTruthy();
    expect(
      screen.getByAltText(
        "Campaign evidence flowing into dashboard investigation and reproduction",
      ),
    ).toBeTruthy();
  });
});
