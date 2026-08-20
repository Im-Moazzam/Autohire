import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { EmptyState, Input, Select, StatusBadge } from "../components/ui";
import { buttonClassName } from "../components/ui/Button";
import { useToast } from "../components/ui/Toast";
import { apiErrorMessage } from "../lib/http";
import { JOB_STATUS_LABELS, useJobs, useTriggerProcess, type Job, type JobStatus } from "../lib/jobs";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  ...Object.entries(JOB_STATUS_LABELS).map(([value, label]) => ({ value, label })),
];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function daysLeftLabel(expiresAt: string): string {
  const diffMs = new Date(expiresAt).getTime() - Date.now();
  const days = Math.ceil(diffMs / 86_400_000);
  if (days < 0) return `Expired ${Math.abs(days)}d ago`;
  if (days === 0) return "Expires today";
  return `${days}d left`;
}

function JobCard({ job }: { job: Job }) {
  const { showToast } = useToast();
  const triggerProcess = useTriggerProcess();

  const canProcess = job.status === "LIVE" && job.submission_count > 0;

  function handleProcess() {
    triggerProcess.mutate(job.job_id, {
      onSuccess: () => showToast("Resume processing started.", "success"),
      onError: (err) => showToast(apiErrorMessage(err, "Couldn't start processing."), "error"),
    });
  }

  return (
    <div className="rounded-card border border-border bg-surface p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="text-card font-semibold">{job.job_title}</h3>
            <StatusBadge status={JOB_STATUS_LABELS[job.status]} />
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-table text-muted">
            <span>
              {job.submission_count} application{job.submission_count === 1 ? "" : "s"}
            </span>
            <span>{daysLeftLabel(job.expires_at)}</span>
            <span>Created {formatDate(job.created_at)}</span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-4">
          <Link to={`/jobs/${job.job_id}/edit`} className="text-body text-primary hover:underline">
            View / Edit
          </Link>
          <button
            type="button"
            onClick={handleProcess}
            disabled={!canProcess || triggerProcess.isPending}
            title={
              !canProcess
                ? job.status !== "LIVE"
                  ? "Only live jobs can be processed"
                  : "No applications to process yet"
                : undefined
            }
            className={buttonClassName({ className: "px-4 py-2 text-table disabled:opacity-40" })}
          >
            {triggerProcess.isPending ? "Starting…" : "AI process"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function Jobs() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<JobStatus | "">("");
  const [q, setQ] = useState("");
  const { data, isLoading, isError, error, refetch } = useJobs({
    status: status || undefined,
    q: q || undefined,
  });

  const jobs = data?.items ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-page font-semibold">Job listings</h1>
          <p className="text-body text-muted">Manage and monitor your recruitment drives.</p>
        </div>
        <Link to="/jobs/new" className={buttonClassName()}>
          + Post new job
        </Link>
      </div>

      <div className="flex gap-4">
        <Input
          label="Search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search titles..."
          className="w-64"
        />
        <Select
          label="Status"
          options={STATUS_OPTIONS}
          value={status}
          onChange={(e) => setStatus(e.target.value as JobStatus | "")}
          className="w-48"
        />
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-card border border-border bg-border/20" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          variant="error"
          title="Couldn't load your jobs"
          description={apiErrorMessage(error, "Something went wrong.")}
          actionLabel="Retry"
          onAction={refetch}
        />
      ) : jobs.length === 0 ? (
        <EmptyState
          title="No jobs yet"
          description="Launch your first job to start collecting applications."
          actionLabel="+ Post new job"
          onAction={() => navigate("/jobs/new")}
        />
      ) : (
        <div className="flex flex-col gap-4">
          {jobs.map((job) => (
            <JobCard key={job.job_id} job={job} />
          ))}
        </div>
      )}
    </div>
  );
}
