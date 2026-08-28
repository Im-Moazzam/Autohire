export type Status =
  | "Active"
  | "Expired"
  | "Draft"
  | "Live"
  | "Closed"
  | "Processed"
  | "Processing"
  | "Scheduled"
  | "Submitted"
  | "Parsed"
  | "Ranked"
  | "Interview Invited"
  | "Confirmed"
  | "Declined"
  | "Reschedule Requested"
  | "Rejected"
  | "Failed"
  | "Parse Error"
  | "Connected"
  | "Disconnected"
  | "Syncing"
  | "Quota Warning";

type Tone = "success" | "warning" | "error" | "primary" | "ai" | "muted";

const statusTone: Record<Status, Tone> = {
  Active: "success",
  Expired: "muted",
  Draft: "muted",
  Live: "success",
  Closed: "muted",
  Processed: "primary",
  Processing: "ai",
  Scheduled: "primary",
  Submitted: "primary",
  Parsed: "muted",
  Ranked: "ai",
  "Interview Invited": "primary",
  Confirmed: "success",
  Declined: "warning",
  "Reschedule Requested": "warning",
  Rejected: "error",
  Failed: "error",
  "Parse Error": "error",
  Connected: "success",
  Disconnected: "muted",
  Syncing: "ai",
  "Quota Warning": "warning",
};

const toneClasses: Record<Tone, string> = {
  success: "bg-success/10 text-success",
  warning: "bg-warning/10 text-warning",
  error: "bg-error/10 text-error",
  primary: "bg-primary/10 text-primary",
  ai: "bg-ai/10 text-ai",
  muted: "bg-border/40 text-muted",
};

const LOADING_STATUSES: Status[] = ["Processing", "Syncing"];

export interface StatusBadgeProps {
  status: Status;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const tone = statusTone[status];
  const isLoading = LOADING_STATUSES.includes(status);

  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 rounded-xl px-3 py-1 text-helper font-semibold",
        toneClasses[tone],
      ].join(" ")}
    >
      {isLoading ? (
        <span
          className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-current border-t-transparent"
          aria-hidden="true"
        />
      ) : (
        <span className="h-2 w-2 rounded-full bg-current" aria-hidden="true" />
      )}
      {status}
    </span>
  );
}
