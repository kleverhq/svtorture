import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import aboutMarkdown from "../../docs/about/README.md?raw";
import { AboutView, resolveLink, sectionsFromMarkdown } from "./AboutView";

const SECTIONS = sectionsFromMarkdown(aboutMarkdown);

afterEach(cleanup);

describe("AboutView", () => {
  it("builds its sections and contents from the canonical Markdown", () => {
    render(<AboutView />);

    const contents = screen.getByRole("navigation", { name: "About contents" });
    for (const { id, title } of SECTIONS) {
      expect(within(contents).getByRole("link", { name: title }).getAttribute("href"))
        .toBe(`#${id}`);
      expect(document.getElementById(id)).toBeTruthy();
      expect(screen.getByRole("heading", { name: title })).toBeTruthy();
    }
  });

  it("recognizes Markdown headings without treating fenced text as a section", () => {
    const sections = sectionsFromMarkdown(`
# Preamble

## First section ##

\`\`\`
## Not a section
\`\`\`

## First section

Body.
`);

    expect(sections.map(({ id, title }) => [id, title])).toEqual([
      ["first-section", "First section"],
      ["first-section-2", "First section"],
    ]);
    expect(sections[0]?.markdown).toContain("## Not a section");
  });

  it("resolves relative documentation links without dropping suffixes", () => {
    expect(resolveLink("../methodology.md?plain=1#metrics")).toBe(
      "https://github.com/kleverhq/svtorture/blob/main/docs/methodology.md?plain=1#metrics",
    );
    expect(resolveLink("#campaigns")).toBe("#campaigns");
    expect(resolveLink("https://example.com/guide")).toBe("https://example.com/guide");
  });

  it("presents each Markdown illustration as an accessible diagram", () => {
    render(<AboutView />);

    const images = screen.getAllByRole("img");
    const regions = screen.getAllByRole("region", { name: /Scrollable diagram:/ });
    expect(images.length).toBeGreaterThan(0);
    expect(regions).toHaveLength(images.length);
    for (const image of images) {
      expect(image.getAttribute("alt")).toBeTruthy();
      expect(image.getAttribute("width")).toBeTruthy();
      expect(image.getAttribute("height")).toBeTruthy();
      const descriptionId = image.getAttribute("aria-describedby");
      expect(descriptionId).toBeTruthy();
      expect(document.getElementById(descriptionId ?? "")?.textContent?.length)
        .toBeGreaterThan(80);
    }
  });
});
