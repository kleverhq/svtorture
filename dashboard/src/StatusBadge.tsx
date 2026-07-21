import {
  STATUS_GROUP_LABELS,
  STATUS_GROUP_SYMBOLS,
  STATUS_LABELS,
  STATUS_SYMBOLS,
  statusGroup,
} from "./model";
import type { Status } from "./types";

export function StatusBadge({
  status,
  reason,
  knownIssue,
  grouped = false,
}: {
  status: Status;
  reason?: string | undefined;
  knownIssue?: string | null | undefined;
  grouped?: boolean | undefined;
}) {
  const group = statusGroup(status);
  const exactLabel =
    knownIssue && status === "nonconforming" ? "Known fail" : STATUS_LABELS[status];
  const label = grouped ? STATUS_GROUP_LABELS[group] : exactLabel;
  const symbol = grouped ? STATUS_GROUP_SYMBOLS[group] : STATUS_SYMBOLS[status];
  const title = [exactLabel, reason, knownIssue].filter(Boolean).join(" · ");
  return (
    <span
      className={`status status--${group}`}
      data-status={status}
      title={title || label}
    >
      <span aria-hidden="true">{symbol}</span>
      <span>{label}</span>
    </span>
  );
}
