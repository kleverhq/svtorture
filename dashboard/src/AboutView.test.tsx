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

    expect(screen.getByRole("heading", { name: "Overview" })).toBeTruthy();
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
        "Diagram of the IEEE standard, requirements, cases, tool profiles, campaign, and dashboard",
      ),
    ).toBeTruthy();
    expect(
      screen.getByAltText(
        "Diagram linking standard anchors to a requirement and corpus metrics",
      ),
    ).toBeTruthy();
    expect(
      screen.getByAltText(
        "Diagram linking case source and oracle to accepted and rejected outcomes",
      ),
    ).toBeTruthy();
    expect(
      screen.getByAltText(
        "Diagram of cumulative tool phases and case applicability checks",
      ),
    ).toBeTruthy();
    expect(
      screen.getByAltText(
        "Diagram of campaign contents and dashboard uses",
      ),
    ).toBeTruthy();
  });
});
