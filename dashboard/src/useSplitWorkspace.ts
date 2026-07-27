import { useEffect, useLayoutEffect, useRef, type RefObject } from "react";

export function useViewportWorkspaceHeight<T extends HTMLElement>() {
  const workspaceRef = useRef<T>(null);

  useLayoutEffect(() => {
    const workspace = workspaceRef.current;
    if (!workspace) return;
    let frame = 0;
    const updateHeight = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        const top = Math.max(0, workspace.getBoundingClientRect().top);
        workspace.style.setProperty(
          "--split-workspace-height",
          `${Math.max(0, window.innerHeight - top)}px`,
        );
      });
    };
    updateHeight();
    window.addEventListener("resize", updateHeight);
    window.addEventListener("scroll", updateHeight, { passive: true });
    const observer =
      typeof ResizeObserver === "undefined" ? undefined : new ResizeObserver(updateHeight);
    for (const selector of [
      ".campaign-overview",
      ".corpus-coverage",
      ".workspace-bar",
    ]) {
      const element = document.querySelector(selector);
      if (element) observer?.observe(element);
    }
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", updateHeight);
      window.removeEventListener("scroll", updateHeight);
      observer?.disconnect();
    };
  }, []);

  return workspaceRef;
}

export function useRevealSplitSelection<T extends HTMLElement>(
  selectedId: string | undefined,
  selectedIndex: number,
  itemRefs: RefObject<Map<string, T>>,
  detailRef: RefObject<HTMLElement | null>,
) {
  const revealed = useRef("");

  useEffect(() => {
    if (!selectedId || selectedIndex < 0) {
      revealed.current = "";
      return;
    }
    const revealKey = `${selectedId}:${selectedIndex}`;
    if (revealed.current === revealKey) return;
    detailRef.current?.scrollTo?.({ top: 0 });
    const frame = window.requestAnimationFrame(() => {
      itemRefs.current.get(selectedId)?.scrollIntoView?.({
        block: "nearest",
        inline: "nearest",
      });
      revealed.current = revealKey;
    });
    return () => window.cancelAnimationFrame(frame);
  }, [detailRef, itemRefs, selectedId, selectedIndex]);
}
