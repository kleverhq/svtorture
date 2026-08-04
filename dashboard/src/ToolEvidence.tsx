import type { ReactNode } from "react";

import { StatusBadge } from "./StatusBadge";
import type { Status } from "./types";

export function ToolEvidenceRow({
  profileKey,
  status,
  reason,
  knownIssue,
  children,
}: {
  profileKey: string;
  status: Status;
  reason?: string | undefined;
  knownIssue?: string | undefined;
  children: ReactNode;
}) {
  return (
    <details>
      <summary>
        <strong>{profileKey}</strong>
        <StatusBadge status={status} reason={reason} knownIssue={knownIssue} />
        <span>{reason ?? "no observation"}</span>
      </summary>
      {children}
    </details>
  );
}
