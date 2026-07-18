import { STATUS_LABELS, STATUS_SYMBOLS } from "./model";
import type { Status } from "./types";

export function StatusBadge({
  status,
  reason,
  knownIssue,
}: {
  status: Status;
  reason?: string | undefined;
  knownIssue?: string | null | undefined;
}) {
  const label = knownIssue && status === "nonconforming" ? "Known fail" : STATUS_LABELS[status];
  return (
    <span
      className={`status status--${status}`}
      title={reason ? `${label}: ${reason}` : label}
    >
      <span aria-hidden="true">{STATUS_SYMBOLS[status]}</span>
      <span>{label}</span>
    </span>
  );
}
