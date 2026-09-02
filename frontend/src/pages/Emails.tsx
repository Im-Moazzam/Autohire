import { useMemo, useState } from "react";
import { DataTable, Pagination, Select, StatusBadge } from "../components/ui";
import { MailIcon } from "../components/ui/icons";
import { apiErrorMessage } from "../lib/http";
import { useJobs } from "../lib/jobs";
import {
  DELIVERY_STATUS_LABELS,
  EMAIL_TYPE_LABELS,
  EMAILS_PAGE_SIZE,
  useEmails,
  type EmailLog,
  type EmailType,
} from "../lib/emails";

const TYPE_OPTIONS = [
  { value: "", label: "All types" },
  ...Object.entries(EMAIL_TYPE_LABELS).map(([value, label]) => ({
    value,
    label,
  })),
];

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function Emails() {
  const [jobFilter, setJobFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState<EmailType | "">("");
  const [page, setPage] = useState(1);

  const jobs = useJobs({});
  const emails = useEmails({
    job_id: jobFilter || undefined,
    email_type: typeFilter || undefined,
    page,
  });

  const jobOptions = useMemo(
    () => [
      { value: "", label: "All jobs" },
      ...(jobs.data?.items ?? []).map((j) => ({
        value: j.job_id,
        label: j.job_title,
      })),
    ],
    [jobs.data],
  );

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-page font-semibold">Emails</h1>
        <p className="text-body text-muted">
          Delivery log for automated candidate emails.
        </p>
      </div>

      <div className="flex gap-4">
        <Select
          label="Job"
          options={jobOptions}
          value={jobFilter}
          onChange={(e) => {
            setJobFilter(e.target.value);
            setPage(1);
          }}
          className="w-64"
        />
        <Select
          label="Type"
          options={TYPE_OPTIONS}
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value as EmailType | "");
            setPage(1);
          }}
          className="w-56"
        />
      </div>

      <DataTable<EmailLog>
        columns={[
          { key: "candidate_name", header: "Candidate" },
          {
            key: "email_type",
            header: "Type",
            render: (row) => EMAIL_TYPE_LABELS[row.email_type],
          },
          { key: "subject", header: "Subject" },
          {
            key: "sent_at",
            header: "Sent",
            render: (row) => formatDateTime(row.sent_at),
          },
          {
            key: "delivery_status",
            header: "Status",
            render: (row) => (
              <StatusBadge
                status={DELIVERY_STATUS_LABELS[row.delivery_status]}
              />
            ),
          },
        ]}
        rows={emails.data?.items ?? []}
        rowKey={(row) => row.email_id}
        isLoading={emails.isLoading}
        errorText={
          emails.isError
            ? apiErrorMessage(emails.error, "Couldn't load emails.")
            : undefined
        }
        onRetry={emails.refetch}
        emptyTitle="No emails sent yet"
        emptyDescription="Automated emails (like interview invitations) will show up here once they're sent."
        emptyIcon={<MailIcon />}
      />

      {emails.data && (
        <Pagination
          page={page}
          size={EMAILS_PAGE_SIZE}
          total={emails.data.total}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
