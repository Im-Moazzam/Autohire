import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  DataTable,
  EmptyState,
  Input,
  MatchScore,
  Modal,
  Select,
  StatusBadge,
} from "../components/ui";
import { buttonClassName } from "../components/ui/Button";
import { useToast } from "../components/ui/Toast";
import { LockIcon, UsersIcon } from "../components/ui/icons";
import { apiErrorMessage } from "../lib/http";
import { JOB_STATUS_LABELS, useJob, useTriggerRank } from "../lib/jobs";
import { useTask } from "../lib/tasks";
import {
  nextStatusOptions,
  statusActionLabel,
  resumeHref,
  SUBMISSION_STATUS_LABELS,
  useCandidate,
  useCandidates,
  useRankedCandidates,
  useUpdateCandidateStatus,
  type Candidate,
  type RankedCandidate,
  type SubmissionStatus,
} from "../lib/candidates";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  ...Object.entries(SUBMISSION_STATUS_LABELS).map(([value, label]) => ({
    value,
    label,
  })),
];

function SparkleIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8" />
    </svg>
  );
}

function ArrowLeftIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M19 12H5M12 19l-7-7 7-7" />
    </svg>
  );
}

function FileIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path d="M14 2v6h6" />
    </svg>
  );
}

function CheckIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

function XIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase();
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function ResumeLink({ url }: { url: string | null | undefined }) {
  const href = resumeHref(url);
  if (!href) return <span className="text-muted">—</span>;
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-1 text-primary hover:underline"
    >
      <FileIcon className="h-4 w-4" />
      Resume
    </a>
  );
}

function StatusActions({
  candidateId,
  current,
  jobId,
  onDone,
  onError,
}: {
  candidateId: string;
  current: SubmissionStatus;
  jobId: string | undefined;
  onDone?: () => void;
  /** Defaults to a toast. Pass this when rendering inside an open <dialog> —
   * it renders in the browser's top layer, above everything else including
   * a toast, so an error toast triggered from inside one is invisible
   * (dimmed behind the modal's own backdrop). */
  onError?: (message: string) => void;
}) {
  const { showToast } = useToast();
  const updateStatus = useUpdateCandidateStatus(jobId);
  const options = nextStatusOptions(current);

  if (options.length === 0) return null;

  function act(status: SubmissionStatus) {
    updateStatus.mutate(
      { candidateId, status },
      {
        onSuccess: () => {
          showToast(
            current === "REJECTED" && status === "PARSED"
              ? "Rejection undone."
              : `Marked as ${SUBMISSION_STATUS_LABELS[status]}.`,
            "success",
          );
          onDone?.();
        },
        onError: (err) => {
          const message = apiErrorMessage(err, "Couldn't update status.");
          if (onError) onError(message);
          else showToast(message, "error");
        },
      },
    );
  }

  return (
    <div className="flex gap-3">
      {options.map((status) => (
        <button
          key={status}
          type="button"
          disabled={updateStatus.isPending}
          onClick={() => act(status)}
          className={buttonClassName({
            variant: status === "REJECTED" ? "destructive" : "primary",
            className:
              "flex-1 h-11 gap-2 disabled:opacity-40 hover:-translate-y-px hover:shadow-card transition-transform",
          })}
        >
          {status === "REJECTED" ? (
            <XIcon className="h-4 w-4" />
          ) : (
            <CheckIcon className="h-4 w-4" />
          )}
          {statusActionLabel(status, current)}
        </button>
      ))}
    </div>
  );
}

function CandidateDetailModal({
  candidateId,
  jobId,
  onClose,
}: {
  candidateId: string | null;
  jobId: string | undefined;
  onClose: () => void;
}) {
  const { data, isLoading, isError, error } = useCandidate(
    candidateId ?? undefined,
  );
  const [statusError, setStatusError] = useState<string>();

  useEffect(() => {
    setStatusError(undefined);
  }, [candidateId]);

  return (
    <Modal
      open={!!candidateId}
      title="Candidate profile"
      onClose={onClose}
      size="lg"
      errorText={statusError}
      footer={
        data && nextStatusOptions(data.submission_status).length > 0 ? (
          <StatusActions
            candidateId={data.candidate_id}
            current={data.submission_status}
            jobId={jobId}
            onDone={onClose}
            onError={setStatusError}
          />
        ) : undefined
      }
    >
      {isLoading ? (
        <div className="flex flex-col gap-3">
          <div className="h-12 w-12 rounded-full bg-border animate-pulse" />
          <div className="h-4 w-2/3 rounded-sm bg-border animate-pulse" />
          <div className="h-4 w-full rounded-sm bg-border animate-pulse" />
          <div className="h-4 w-full rounded-sm bg-border animate-pulse" />
        </div>
      ) : isError ? (
        <p className="text-body text-error">
          {apiErrorMessage(error, "Couldn't load this candidate.")}
        </p>
      ) : data ? (
        <div className="flex flex-col gap-5 animate-fade-in">
          <div className="flex items-center gap-4">
            <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary-soft text-section font-semibold text-primary">
              {initials(data.full_name)}
            </span>
            <div className="flex flex-col gap-1">
              <h3 className="text-card font-semibold text-ink">
                {data.full_name}
              </h3>
              <div className="text-body text-muted">
                {data.email}
                {data.phone_number ? ` · ${data.phone_number}` : ""}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <StatusBadge
              status={SUBMISSION_STATUS_LABELS[data.submission_status]}
            />
            <ResumeLink url={data.resume_url} />
          </div>

          {data.parse_error && (
            <p className="rounded-md bg-error/10 px-3 py-2 text-helper text-error">
              Parse error: {data.parse_error}
            </p>
          )}

          {data.form_responses.length > 0 && (
            <div className="flex max-h-72 flex-col gap-4 overflow-y-auto rounded-md border border-border bg-canvas p-5">
              {data.form_responses.map((r) => (
                <div key={r.field_id}>
                  <div className="text-helper font-semibold uppercase tracking-wide text-muted">
                    {r.field_label}
                  </div>
                  <div className="text-body text-ink">
                    {r.response_value || "—"}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </Modal>
  );
}

function RankedCard({
  candidate,
  jobId,
  onOpen,
}: {
  candidate: RankedCandidate;
  jobId: string | undefined;
  onOpen: (candidateId: string) => void;
}) {
  return (
    <div
      onClick={() => onOpen(candidate.candidate_id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen(candidate.candidate_id);
        }
      }}
      className="flex cursor-pointer flex-col gap-3 rounded-card border border-border bg-surface p-5 animate-slide-up transition-shadow hover:shadow-card"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ai/10 text-helper font-semibold text-ai">
            #{candidate.rank_position}
          </span>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-card font-semibold">{candidate.full_name}</h3>
              <StatusBadge
                status={SUBMISSION_STATUS_LABELS[candidate.submission_status]}
              />
            </div>
            <div className="text-helper text-muted">{candidate.email}</div>
          </div>
        </div>
        <span onClick={(e) => e.stopPropagation()}>
          <ResumeLink url={candidate.resume_url} />
        </span>
      </div>

      <MatchScore score={candidate.semantic_score} />

      {candidate.ai_feedback_summary && (
        <p className="text-body text-muted">{candidate.ai_feedback_summary}</p>
      )}

      {(candidate.matched_skills.length > 0 ||
        candidate.missing_skills.length > 0) && (
        <div className="flex flex-wrap gap-1.5">
          {candidate.matched_skills.map((s) => (
            <span
              key={s}
              className="rounded-full bg-success/10 px-2.5 py-1 text-helper text-success"
            >
              {s}
            </span>
          ))}
          {candidate.missing_skills.map((s) => (
            <span
              key={s}
              className="rounded-full bg-border/50 px-2.5 py-1 text-helper text-muted line-through"
            >
              {s}
            </span>
          ))}
        </div>
      )}

      <div onClick={(e) => e.stopPropagation()}>
        <StatusActions
          candidateId={candidate.candidate_id}
          current={candidate.submission_status}
          jobId={jobId}
        />
      </div>
    </div>
  );
}

export function Candidates() {
  const { jobId } = useParams<{ jobId: string }>();
  const { showToast, dismissToast } = useToast();
  const [tab, setTab] = useState<"all" | "ranked">("all");
  const [status, setStatus] = useState<SubmissionStatus | "">("");
  const [q, setQ] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [rankTaskId, setRankTaskId] = useState<string | undefined>();
  // "loading" toasts never auto-dismiss (Toast.tsx) — this one has to be
  // explicitly cleared once the task reaches a terminal status.
  const rankToastId = useRef<number | null>(null);

  const job = useJob(jobId);
  const candidates = useCandidates(jobId, {
    submission_status: status || undefined,
    q: q || undefined,
  });
  const ranked = useRankedCandidates(tab === "ranked" ? jobId : undefined);
  const triggerRank = useTriggerRank();
  const rankTask = useTask(rankTaskId);

  const isRanking = rankTask.data
    ? !["SUCCESS", "FAILED", "RETRIED"].includes(rankTask.data.status)
    : false;

  useEffect(() => {
    if (!rankTaskId || !rankTask.data) return;
    if (rankTask.data.status === "SUCCESS") {
      setRankTaskId(undefined);
      if (rankToastId.current !== null) dismissToast(rankToastId.current);
      ranked.refetch();
      job.refetch();
      showToast("AI ranking complete.", "success");
    } else if (rankTask.data.status === "FAILED") {
      setRankTaskId(undefined);
      if (rankToastId.current !== null) dismissToast(rankToastId.current);
      showToast(rankTask.data.error_message ?? "AI ranking failed.", "error");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rankTask.data?.status]);

  function handleRank() {
    if (!jobId) return;
    triggerRank.mutate(jobId, {
      onSuccess: (task) => {
        setRankTaskId(task.task_id);
        rankToastId.current = showToast("AI ranking started.", "loading");
      },
      onError: (err) =>
        showToast(apiErrorMessage(err, "Couldn't start ranking."), "error"),
    });
  }

  const canRank =
    job.data?.status === "CLOSED" || job.data?.status === "PROCESSED";

  return (
    <div className="flex flex-col gap-6">
      <Link
        to="/jobs"
        className="inline-flex items-center gap-1 text-body text-muted hover:text-ink w-fit"
      >
        <ArrowLeftIcon className="h-4 w-4" />
        Back to jobs
      </Link>

      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-page font-semibold">
              {job.isLoading
                ? "Loading…"
                : (job.data?.job_title ?? "Candidates")}
            </h1>
            {job.data && (
              <StatusBadge status={JOB_STATUS_LABELS[job.data.status]} />
            )}
          </div>
          <p className="text-body text-muted">
            Review submissions and AI-ranked candidates for this job.
          </p>
        </div>
        {canRank ? (
          <button
            type="button"
            onClick={handleRank}
            disabled={triggerRank.isPending || isRanking}
            className={buttonClassName({
              variant: "primary",
              className: "gap-2 disabled:opacity-40",
            })}
          >
            {isRanking || triggerRank.isPending ? (
              <span
                className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
                aria-hidden="true"
              />
            ) : (
              <SparkleIcon className="h-4 w-4" />
            )}
            {isRanking || triggerRank.isPending ? "Ranking…" : "Run AI ranking"}
          </button>
        ) : (
          <button
            type="button"
            disabled
            title="Close the job before ranking candidates"
            className="flex cursor-not-allowed items-center gap-2 rounded-control bg-warning/10 px-5 py-3 text-body font-semibold text-warning"
          >
            <LockIcon className="h-4 w-4" />
            Can't rank until job is closed
          </button>
        )}
      </div>

      <div className="flex gap-1 rounded-control bg-border/30 p-1 w-fit">
        {(["all", "ranked"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={[
              "rounded-md px-4 py-2 text-body font-medium transition-colors",
              tab === t
                ? "bg-surface text-ink shadow-card"
                : "text-muted hover:text-ink",
            ].join(" ")}
          >
            {t === "all" ? "All submissions" : "AI ranked"}
          </button>
        ))}
      </div>

      {tab === "all" ? (
        <>
          <div className="flex gap-4">
            <Input
              label="Search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search name or email..."
              className="w-64"
            />
            <Select
              label="Status"
              options={STATUS_OPTIONS}
              value={status}
              onChange={(e) =>
                setStatus(e.target.value as SubmissionStatus | "")
              }
              className="w-52"
            />
          </div>

          <DataTable<Candidate>
            columns={[
              {
                key: "full_name",
                header: "Applicant",
                render: (c) => (
                  <button
                    type="button"
                    onClick={() => setSelectedId(c.candidate_id)}
                    className="text-left hover:underline"
                  >
                    <div className="font-medium text-ink">{c.full_name}</div>
                    <div className="text-helper text-muted">{c.email}</div>
                  </button>
                ),
              },
              {
                key: "submission_status",
                header: "Status",
                render: (c) => (
                  <StatusBadge
                    status={SUBMISSION_STATUS_LABELS[c.submission_status]}
                  />
                ),
              },
              {
                key: "submitted_at",
                header: "Submitted",
                render: (c) => formatDateTime(c.submitted_at),
              },
              {
                key: "resume",
                header: "Resume",
                render: (c) => <ResumeLink url={c.resume_url} />,
              },
            ]}
            rows={candidates.data?.items ?? []}
            rowKey={(c) => c.candidate_id}
            isLoading={candidates.isLoading}
            errorText={
              candidates.isError
                ? apiErrorMessage(candidates.error, "Couldn't load candidates.")
                : undefined
            }
            onRetry={candidates.refetch}
            emptyTitle="No submissions yet"
            emptyDescription="Applications will show up here once candidates apply."
            emptyIcon={<UsersIcon />}
          />
        </>
      ) : ranked.isLoading ? (
        <div className="flex flex-col gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-40 animate-pulse rounded-card border border-border bg-border/20"
            />
          ))}
        </div>
      ) : ranked.isError ? (
        <EmptyState
          variant="error"
          title="Couldn't load rankings"
          description={apiErrorMessage(ranked.error, "Something went wrong.")}
          actionLabel="Retry"
          onAction={ranked.refetch}
        />
      ) : (ranked.data?.items.length ?? 0) === 0 ? (
        <EmptyState
          title="No ranked candidates yet"
          description={
            canRank
              ? "Run AI ranking above to score and rank submissions."
              : "Close this job, then run AI ranking to score submissions."
          }
          icon={<SparkleIcon />}
        />
      ) : (
        <div className="flex flex-col gap-4">
          {ranked.data!.items.map((c) => (
            <RankedCard
              key={c.candidate_id}
              candidate={c}
              jobId={jobId}
              onOpen={setSelectedId}
            />
          ))}
        </div>
      )}

      <CandidateDetailModal
        candidateId={selectedId}
        jobId={jobId}
        onClose={() => setSelectedId(null)}
      />
    </div>
  );
}
