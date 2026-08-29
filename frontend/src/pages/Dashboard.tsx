import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  AnimatedNumber,
  Card,
  DonutChart,
  DonutLegend,
  EmptyState,
  FunnelBarChart,
} from "../components/ui";
import { buttonClassName } from "../components/ui/Button";
import {
  BriefcaseIcon,
  CalendarIcon,
  MailIcon,
  UsersIcon,
} from "../components/ui/icons";
import { useCurrentRecruiter } from "../lib/auth";
import {
  topEntries,
  useDashboardStats,
  type DashboardStats,
} from "../lib/dashboard";
import { DELIVERY_STATUS_LABELS, type DeliveryStatus } from "../lib/emails";
import { apiErrorMessage } from "../lib/http";
import { JOB_STATUS_LABELS, type JobStatus } from "../lib/jobs";
import { SLOT_STATUS_LABELS, type SlotStatus } from "../lib/scheduling";

const containerMotion = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};
const itemMotion = {
  hidden: { opacity: 0, y: 14 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: "easeOut" as const },
  },
};

function KpiCard({
  icon,
  label,
  value,
  tone,
  breakdown,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  tone: "primary" | "ai" | "cyan" | "success";
  breakdown: [string, number][];
}) {
  const toneClasses = {
    primary: "bg-primary-soft text-primary",
    ai: "bg-ai/10 text-ai",
    cyan: "bg-cyan/10 text-cyan",
    success: "bg-success/10 text-success",
  }[tone];

  return (
    <motion.div
      variants={itemMotion}
      className="flex flex-col gap-4 rounded-card border border-border bg-surface p-6 shadow-card"
    >
      <div className="flex items-center justify-between">
        <span
          className={`flex h-11 w-11 items-center justify-center rounded-full ${toneClasses}`}
          aria-hidden="true"
        >
          {icon}
        </span>
      </div>
      <div>
        <div className="text-page font-semibold text-ink">
          <AnimatedNumber value={value} />
        </div>
        <div className="text-body text-muted">{label}</div>
      </div>
      {breakdown.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {breakdown.map(([name, count]) => (
            <span
              key={name}
              className="rounded-full bg-canvas px-2.5 py-1 text-helper text-muted"
            >
              {count} {name}
            </span>
          ))}
        </div>
      )}
    </motion.div>
  );
}

const JOB_COLORS: Record<string, string> = {
  DRAFT: "var(--color-muted)",
  LIVE: "var(--color-success)",
  CLOSED: "var(--color-navy)",
  PROCESSED: "var(--color-primary)",
};

const CANDIDATE_FUNNEL_ORDER = [
  "SUBMITTED",
  "PARSED",
  "RANKED",
  "INVITED",
  "CONFIRMED",
] as const;
const CANDIDATE_FUNNEL_COLORS: Record<string, string> = {
  SUBMITTED: "var(--color-primary)",
  PARSED: "var(--color-cyan)",
  RANKED: "var(--color-ai)",
  INVITED: "var(--color-navy)",
  CONFIRMED: "var(--color-success)",
};
const CANDIDATE_FUNNEL_LABELS: Record<string, string> = {
  SUBMITTED: "Submitted",
  PARSED: "Parsed",
  RANKED: "Ranked",
  INVITED: "Invited",
  CONFIRMED: "Confirmed",
};
const CANDIDATE_OFF_PATH_LABELS: Record<string, string> = {
  REJECTED: "Rejected",
  DECLINED: "Declined",
  RESCHEDULED: "Rescheduled",
  PARSE_ERROR: "Parse error",
};

const INTERVIEW_COLORS: Record<string, string> = {
  PENDING: "var(--color-primary)",
  CONFIRMED: "var(--color-success)",
  DECLINED: "var(--color-warning)",
  RESCHEDULED: "var(--color-cyan)",
  CANCELLED: "var(--color-muted)",
};

const EMAIL_COLORS: Record<string, string> = {
  SENT: "var(--color-success)",
  FAILED: "var(--color-error)",
  PENDING: "var(--color-warning)",
};

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-8">
      <div className="h-8 w-64 animate-pulse rounded-sm bg-border" />
      <div className="grid grid-cols-4 gap-5">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-40 animate-pulse rounded-card bg-border/40"
          />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-6">
        <div className="h-72 animate-pulse rounded-card bg-border/40" />
        <div className="h-72 animate-pulse rounded-card bg-border/40" />
      </div>
    </div>
  );
}

function statsToDonut(
  counts: Record<string, number>,
  colors: Record<string, string>,
  labels: Record<string, string>,
) {
  return Object.entries(counts)
    .filter(([key]) => colors[key])
    .map(([key, value]) => ({
      label: labels[key] ?? key,
      value,
      color: colors[key],
    }));
}

export function Dashboard() {
  const { data: recruiter } = useCurrentRecruiter();
  const stats = useDashboardStats();

  if (stats.isLoading) return <DashboardSkeleton />;

  if (stats.isError) {
    return (
      <EmptyState
        variant="error"
        title="Couldn't load your dashboard"
        description={apiErrorMessage(stats.error, "Something went wrong.")}
        actionLabel="Retry"
        onAction={() => stats.refetch()}
      />
    );
  }

  const data = stats.data as DashboardStats;

  if (data.total_jobs === 0) {
    return (
      <div className="flex flex-col items-center gap-3 text-center py-12 px-6">
        <div className="h-12 w-12 rounded-full flex items-center justify-center bg-primary-soft text-primary [&>svg]:h-6 [&>svg]:w-6">
          <BriefcaseIcon />
        </div>
        <h3 className="text-card font-semibold text-ink">
          Welcome to AutoHire
        </h3>
        <p className="text-body text-muted max-w-sm">
          Post your first job to start seeing live stats here — applications, AI
          rankings, interviews, and email delivery, all in one place.
        </p>
        <Link to="/jobs/new" className={buttonClassName({ className: "mt-2" })}>
          + Post new job
        </Link>
      </div>
    );
  }

  const jobsDonut = statsToDonut(
    data.jobs_by_status,
    JOB_COLORS,
    JOB_STATUS_LABELS,
  );
  const interviewsDonut = statsToDonut(
    data.interviews_by_status,
    INTERVIEW_COLORS,
    SLOT_STATUS_LABELS,
  );
  const emailsDonut = statsToDonut(
    data.emails_by_status,
    EMAIL_COLORS,
    DELIVERY_STATUS_LABELS,
  );
  const funnelData = CANDIDATE_FUNNEL_ORDER.map((key) => ({
    label: CANDIDATE_FUNNEL_LABELS[key],
    value:
      data.candidates_by_status[
        key as keyof typeof data.candidates_by_status
      ] ?? 0,
    color: CANDIDATE_FUNNEL_COLORS[key],
  }));
  const offPath = Object.entries(CANDIDATE_OFF_PATH_LABELS)
    .map(
      ([key, label]) =>
        [
          label,
          data.candidates_by_status[
            key as keyof typeof data.candidates_by_status
          ] ?? 0,
        ] as [string, number],
    )
    .filter(([, count]) => count > 0);

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-page font-semibold">
            Welcome back, {recruiter?.name}
          </h1>
          <p className="text-body text-muted">
            Here's what's happening across your jobs right now.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-full bg-success/10 px-3 py-1.5 text-helper font-semibold text-success">
          <span
            className="h-2 w-2 animate-pulse rounded-full bg-current"
            aria-hidden="true"
          />
          Live — updates every 30s
        </div>
      </div>

      <motion.div
        variants={containerMotion}
        initial="hidden"
        animate="show"
        className="grid grid-cols-4 gap-5"
      >
        <KpiCard
          icon={<BriefcaseIcon className="h-5 w-5" />}
          label="Jobs"
          value={data.total_jobs}
          tone="primary"
          breakdown={topEntries(data.jobs_by_status).map(([k, v]) => [
            JOB_STATUS_LABELS[k as JobStatus],
            v,
          ])}
        />
        <KpiCard
          icon={<UsersIcon className="h-5 w-5" />}
          label="Candidates"
          value={data.total_candidates}
          tone="ai"
          breakdown={topEntries(data.candidates_by_status).map(([k, v]) => [
            CANDIDATE_FUNNEL_LABELS[k] ?? CANDIDATE_OFF_PATH_LABELS[k] ?? k,
            v,
          ])}
        />
        <KpiCard
          icon={<CalendarIcon className="h-5 w-5" />}
          label="Interviews"
          value={data.total_interviews}
          tone="cyan"
          breakdown={topEntries(data.interviews_by_status).map(([k, v]) => [
            SLOT_STATUS_LABELS[k as SlotStatus],
            v,
          ])}
        />
        <KpiCard
          icon={<MailIcon className="h-5 w-5" />}
          label="Emails sent"
          value={data.total_emails}
          tone="success"
          breakdown={topEntries(data.emails_by_status).map(([k, v]) => [
            DELIVERY_STATUS_LABELS[k as DeliveryStatus],
            v,
          ])}
        />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.15 }}
      >
        <Card title="Candidate pipeline">
          <FunnelBarChart data={funnelData} />
          {offPath.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2 border-t border-border pt-4">
              {offPath.map(([label, count]) => (
                <span
                  key={label}
                  className="rounded-full bg-canvas px-2.5 py-1 text-helper text-muted"
                >
                  {count} {label}
                </span>
              ))}
            </div>
          )}
        </Card>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.25 }}
        className="grid grid-cols-3 gap-6"
      >
        <Card title="Jobs by status">
          <DonutChart data={jobsDonut} total={data.total_jobs} />
          <div className="mt-4">
            <DonutLegend data={jobsDonut} />
          </div>
        </Card>
        <Card title="Interviews">
          <DonutChart data={interviewsDonut} total={data.total_interviews} />
          <div className="mt-4">
            <DonutLegend data={interviewsDonut} />
          </div>
        </Card>
        <Card title="Email delivery">
          <DonutChart data={emailsDonut} total={data.total_emails} />
          <div className="mt-4">
            <DonutLegend data={emailsDonut} />
          </div>
        </Card>
      </motion.div>
    </div>
  );
}
