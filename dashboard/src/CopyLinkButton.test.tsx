import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CopyLinkButton, dashboardEntityUrl } from "./CopyLinkButton";

const originalClipboard = Object.getOwnPropertyDescriptor(navigator, "clipboard");
const originalExecCommand = Object.getOwnPropertyDescriptor(document, "execCommand");

function setClipboard(value: { writeText: (text: string) => Promise<void> } | undefined) {
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value,
  });
}

function setExecCommand(value: (command: string) => boolean) {
  Object.defineProperty(document, "execCommand", {
    configurable: true,
    value,
  });
}

afterEach(() => {
  cleanup();
  if (originalClipboard) {
    Object.defineProperty(navigator, "clipboard", originalClipboard);
  } else {
    Reflect.deleteProperty(navigator, "clipboard");
  }
  if (originalExecCommand) {
    Object.defineProperty(document, "execCommand", originalExecCommand);
  } else {
    Reflect.deleteProperty(document, "execCommand");
  }
  window.history.replaceState(null, "", "/");
});

describe("CopyLinkButton", () => {
  it("builds canonical path-aware links for cases and requirements", () => {
    window.history.replaceState(
      null,
      "",
      "/svtorture/?view=trends&tool=fake#selected",
    );

    const caseUrl = new URL(
      dashboardEntityUrl({
        view: "evidence",
        parameter: "caseId",
        id: "case with spaces",
      }),
    );
    expect(caseUrl.pathname).toBe("/svtorture/");
    expect(caseUrl.searchParams.get("view")).toBe("evidence");
    expect(caseUrl.searchParams.get("caseId")).toBe("case with spaces");
    expect([...caseUrl.searchParams]).toHaveLength(2);
    expect(caseUrl.hash).toBe("");

    const requirementUrl = new URL(
      dashboardEntityUrl({
        view: "matrix",
        parameter: "requirementId",
        id: "SV-2023-13-OUTPUT-COPYOUT",
      }),
    );
    expect(requirementUrl.search).toBe(
      "?view=matrix&requirementId=SV-2023-13-OUTPUT-COPYOUT",
    );
  });

  it("copies the canonical link and confirms success", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard({ writeText });
    window.history.replaceState(null, "", "/svtorture/?search=hidden");

    render(
      <CopyLinkButton
        target={{ view: "evidence", parameter: "caseId", id: "case-1" }}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Copy link" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledOnce());
    expect(writeText.mock.calls[0]?.[0]).toMatch(
      /\/svtorture\/\?view=evidence&caseId=case-1$/,
    );
    expect(screen.getByRole("button", { name: "Link copied" })).toBeTruthy();
  });

  it("falls back when the Clipboard API is unavailable", async () => {
    const execCommand = vi.fn().mockReturnValue(true);
    setClipboard(undefined);
    setExecCommand(execCommand);

    render(
      <CopyLinkButton
        target={{ view: "matrix", parameter: "requirementId", id: "requirement-1" }}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Copy link" }));

    await screen.findByRole("button", { name: "Link copied" });
    expect(execCommand).toHaveBeenCalledWith("copy");
    expect(document.querySelector("textarea")).toBeNull();
  });

  it("reports failure when both clipboard paths fail", async () => {
    const writeText = vi.fn().mockRejectedValue(new Error("denied"));
    const execCommand = vi.fn().mockReturnValue(false);
    setClipboard({ writeText });
    setExecCommand(execCommand);

    render(
      <CopyLinkButton
        target={{ view: "evidence", parameter: "caseId", id: "case-1" }}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Copy link" }));

    await screen.findByRole("button", { name: "Copy failed" });
    expect(writeText).toHaveBeenCalledOnce();
    expect(execCommand).toHaveBeenCalledWith("copy");
  });

  it("ignores a completed copy after the selected entity changes", async () => {
    let resolveCopy: (() => void) | undefined;
    const writeText = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveCopy = resolve;
        }),
    );
    setClipboard({ writeText });

    const view = render(
      <CopyLinkButton
        target={{ view: "evidence", parameter: "caseId", id: "case-1" }}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Copy link" }));
    view.rerender(
      <CopyLinkButton
        target={{ view: "evidence", parameter: "caseId", id: "case-2" }}
      />,
    );
    await act(async () => resolveCopy?.());

    expect(screen.getByRole("button", { name: "Copy link" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Link copied" })).toBeNull();
  });
});
