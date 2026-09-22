import { useState } from "react";
import { Navigate } from "react-router-dom";
import {
  ACCOUNT_STATE_LABELS,
  ADMIN_PAGE_SIZE,
  TASK_STATUS_LABELS,
  useAdminRecruiters,
  useAdminTasks,
  useReactivateRecruiter,
  useSuspendRecruiter,
  type AdminRecruiter,
  type TaskStatus,
  type TaskType,
} from "../lib/admin";
import {
  Button,
  DataTable,
  Modal,
  Pagination,
  Select,
  StatusBadge,
  type DataTableColumn,
} from "../components/ui";
import { useToast } from "../components/ui/Toast";
import { ApiError, apiErrorMessage } from "../lib/http";

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

const TASK_STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  ...Object.entries(TASK_STATUS_LABELS).map(([value, label]) => ({
    value,
    label,
  })),
];

const TASK_TYPE_OPTIONS = [
  { value: "", label: "All types" },
  { value: "RESUME_PARSE", label: "Resume parse" },
  { value: "BATCH_RANKING", label: "Batch ranking" },
  { value: "EMAIL_DISPATCH", label: "Email dispatch" },
  { value: "CALENDAR_SYNC", label: "Calendar sync" },
  { value: "JD_EMBEDDING", label: "JD embedding" },
];

function RecruitersSection() {
  const [page, setPage] = useState(1);
  const recruiters = useAdminRecruiters(page);
  const suspend = useSuspendRecruiter();
  const reactivate = useReactivateRecruiter();
  const { showToast } = useToast();
  const [pendingSuspend, setPendingSuspend] = useState<AdminRecruiter | null>(
    null,
  );
  const [suspendError, setSuspendError] = useState<string>();

  function handleSuspend() {
    if (!pendingSuspend) return;
    setSuspendError(undefined);
    suspend.mutate(pendingSuspend.id, {
      onSuccess: () => {
        showToast(`${pendingSuspend.name} suspended.`, "success");
        setPendingSuspend(null);
      },
      onError: (err) =>
        setSuspendError(apiErrorMessage(err, "Couldn't suspend this account.")),
    });
  }

  const columns: DataTableColumn<AdminRecruiter>[] = [
    { key: "name", header: "Name" },
    { key: "email", header: "Email" },
    {
      key: "account_state",
      header: "Status",
      render: (row) => (
        <StatusBadge status={ACCOUNT_STATE_LABELS[row.account_state]} />
      ),
    },
    { key: "total_jobs", header: "Jobs" },
    { key: "total_candidates", header: "Candidates" },
    { key: "total_interviews", header: "Interviews" },
    { key: "total_emails", header: "Emails" },
    {
      key: "created_at",
      header: "Joined",
      render: (row) => formatDateTime(row.created_at),
    },
    {
      key: "last_login_at",
      header: "Last login",
      render: (row) => formatDateTime(row.last_login_at),
    },
    {
      key: "actions",
      header: "Actions",
      render: (row) =>
        row.account_state === "SUSPENDED" ? (
          <Button
            variant="secondary"
            onClick={() => reactivate.mutate(row.id)}
            isLoading={reactivate.isPending}
          >
            Reactivate
          </Button>
        ) : (
          <Button variant="destructive" onClick={() => setPendingSuspend(row)}>
            Suspend
          </Button>
        ),
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-section font-semibold">Recruiters</h2>
      <DataTable
        columns={columns}
        rows={recruiters.data?.items ?? []}
        rowKey={(row) => row.id}
        isLoading={recruiters.isLoading}
        errorText={
          recruiters.isError
            ? apiErrorMessage(recruiters.error, "Couldn't load recruiters.")
            : undefined
        }
        onRetry={recruiters.refetch}
        emptyTitle="No recruiters yet"
      />
      {recruiters.data && (
        <Pagination
          page={page}
          size={ADMIN_PAGE_SIZE}
          total={recruiters.data.total}
          onPageChange={setPage}
        />
      )}

      <Modal
        open={pendingSuspend !== null}
        title={`Suspend ${pendingSuspend?.name}?`}
        onClose={() => {
          setPendingSuspend(null);
          setSuspendError(undefined);
        }}
        primaryLabel="Suspend"
        onPrimary={handleSuspend}
        isLoading={suspend.isPending}
        errorText={suspendError}
      >
        <p className="text-body text-muted">
          They won't be able to sign in or use the platform until reactivated.
          Nothing they've already created is deleted.
        </p>
      </Modal>
    </div>
  );
}

function TasksSection() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<TaskStatus | "">("");
  const [taskType, setTaskType] = useState<TaskType | "">("");
  const tasks = useAdminTasks({
    status: status || undefined,
    task_type: taskType || undefined,
    page,
  });

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-section font-semibold">Background tasks</h2>
      <div className="flex gap-4">
        <Select
          label="Status"
          options={TASK_STATUS_OPTIONS}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as TaskStatus | "");
            setPage(1);
          }}
          className="w-52"
        />
        <Select
          label="Type"
          options={TASK_TYPE_OPTIONS}
          value={taskType}
          onChange={(e) => {
            setTaskType(e.target.value as TaskType | "");
            setPage(1);
          }}
          className="w-56"
        />
      </div>
      <DataTable
        columns={[
          { key: "recruiter_email", header: "Recruiter" },
          { key: "task_type", header: "Type" },
          {
            key: "status",
            header: "Status",
            render: (row) => (
              <StatusBadge status={TASK_STATUS_LABELS[row.status]} />
            ),
          },
          {
            key: "started_at",
            header: "Started",
            render: (row) => formatDateTime(row.started_at),
          },
          {
            key: "error_message",
            header: "Error",
            render: (row) => row.error_message ?? "—",
          },
        ]}
        rows={tasks.data?.items ?? []}
        rowKey={(row) => row.task_id}
        isLoading={tasks.isLoading}
        errorText={
          tasks.isError
            ? apiErrorMessage(tasks.error, "Couldn't load tasks.")
            : undefined
        }
        onRetry={tasks.refetch}
        emptyTitle="No background tasks yet"
      />
      {tasks.data && (
        <Pagination
          page={page}
          size={ADMIN_PAGE_SIZE}
          total={tasks.data.total}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}

export function Admin() {
  // Same query key/page as RecruitersSection's initial render, so this
  // doesn't duplicate the network request — just gives the page a place to
  // redirect on 403 before rendering an admin-only screen to a non-admin.
  const gate = useAdminRecruiters(1);

  if (
    gate.isError &&
    gate.error instanceof ApiError &&
    gate.error.status === 403
  ) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-page font-semibold">Admin</h1>
        <p className="text-body text-muted">
          Cross-recruiter usage, account health, and background task monitoring.
        </p>
      </div>
      <RecruitersSection />
      <TasksSection />
    </div>
  );
}
