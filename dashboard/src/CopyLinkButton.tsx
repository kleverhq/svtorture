import { useEffect, useRef, useState } from "react";

type EntityLink =
  | {
      view: "matrix";
      parameter: "requirementId";
      id: string;
      campaignId?: string | undefined;
    }
  | {
      view: "evidence";
      parameter: "caseId";
      id: string;
      campaignId?: string | undefined;
    };

export function dashboardEntityUrl(target: EntityLink): string {
  const url = new URL(window.location.href);
  url.search = "";
  url.hash = "";
  url.searchParams.set("view", target.view);
  url.searchParams.set(target.parameter, target.id);
  if (target.campaignId) url.searchParams.set("campaign", target.campaignId);
  return url.toString();
}

async function copyText(value: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value);
      return;
    } catch {
      // The synchronous fallback can still work when Clipboard API permission is denied.
    }
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("clipboard unavailable");
}

export function CopyLinkButton({ target }: { target: EntityLink }) {
  const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle");
  const resetTimer = useRef<number | undefined>(undefined);
  const operation = useRef(0);
  const href = dashboardEntityUrl(target);
  const activeHref = useRef(href);
  activeHref.current = href;

  useEffect(() => {
    operation.current += 1;
    setStatus("idle");
    window.clearTimeout(resetTimer.current);
    return () => {
      operation.current += 1;
      window.clearTimeout(resetTimer.current);
    };
  }, [href]);

  const copy = async () => {
    window.clearTimeout(resetTimer.current);
    const currentOperation = ++operation.current;
    let nextStatus: "copied" | "failed";
    try {
      await copyText(href);
      nextStatus = "copied";
    } catch {
      nextStatus = "failed";
    }
    if (currentOperation !== operation.current || activeHref.current !== href) return;
    setStatus(nextStatus);
    resetTimer.current = window.setTimeout(() => setStatus("idle"), 1600);
  };

  return (
    <button
      type="button"
      className="button button--quiet copy-link-button"
      data-status={status}
      onClick={copy}
    >
      {status === "copied"
        ? "Link copied"
        : status === "failed"
          ? "Copy failed"
          : "Copy link"}
    </button>
  );
}
