import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  DataTable,
  Input,
  Select,
  StatusBadge,
} from "../components/ui";
import { CalendarIcon, VideoIcon } from "../components/ui/icons";
import { useToast } from "../components/ui/Toast";
import { apiErrorMessage } from "../lib/http";
import { useJobs } from "../lib/jobs";
import {
  SLOT_STATUS_LABELS,
  WEEKDAY_LABELS,
  WEEKDAY_ORDER,
  useInterviews,
  useSchedulingPreferences,
  useUpdateSchedulingPreferences,
  type InterviewSlot,
  type SlotStatus,
  type Weekday,
} from "../lib/scheduling";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  ...Object.entries(SLOT_STATUS_LABELS).map(([value, label]) => ({
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

/** "09:00:00" (backend TIME) <-> "09:00" (<input type="time">). */
function toInputTime(value: string): string {
  return value.slice(0, 5);
}
function toBackendTime(value: string): string {
  return `${value}:00`;
}

function AvailabilityForm() {
  const prefs = useSchedulingPreferences();
  const updatePrefs = useUpdateSchedulingPreferences();
  const { showToast } = useToast();

  const [days, setDays] = useState<Weekday[]>([]);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("17:00");
  const [duration, setDuration] = useState(30);
  const [formError, setFormError] = useState<string>();

  useEffect(() => {
    if (!prefs.data) return;
    setDays(prefs.data.available_days);
    setStartTime(toInputTime(prefs.data.available_start_time));
    setEndTime(toInputTime(prefs.data.available_end_time));
    setDuration(prefs.data.slot_duration_minutes);
  }, [prefs.data]);

  function toggleDay(day: Weekday) {
    setDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day],
    );
  }

  function handleSave() {
    setFormError(undefined);
    if (days.length === 0) {
      setFormError("Select at least one available day.");
      return;
    }
    if (startTime >= endTime) {
      setFormError("Start time must be before end time.");
      return;
    }
    updatePrefs.mutate(
      {
        available_days: days,
        available_start_time: toBackendTime(startTime),
        available_end_time: toBackendTime(endTime),
        slot_duration_minutes: duration,
      },
      {
        onSuccess: () => showToast("Availability saved.", "success"),
        onError: (err) =>
          setFormError(apiErrorMessage(err, "Couldn't save availability.")),
      },
    );
  }

  if (prefs.isLoading) {
    return <Card isLoading />;
  }

  if (prefs.isError) {
    return (
      <Card
        errorText={apiErrorMessage(
          prefs.error,
          "Couldn't load your availability.",
        )}
      >
        <Button
          variant="secondary"
          onClick={() => prefs.refetch()}
          className="mt-3"
        >
          Retry
        </Button>
      </Card>
    );
  }

  return (
    <Card title="Interview availability">
      {prefs.data?.preference_id === null && (
        <p className="mb-4 text-helper text-muted">
          Showing default availability — save to customize it.
        </p>
      )}

      <div className="flex flex-col gap-5">
        <div>
          <span className="mb-2 block text-body font-medium text-ink">
            Available days
          </span>
          <div className="flex flex-wrap gap-2">
            {WEEKDAY_ORDER.map((day) => (
              <button
                key={day}
                type="button"
                onClick={() => toggleDay(day)}
                aria-pressed={days.includes(day)}
                className={[
                  "rounded-control px-3 py-2 text-body font-medium transition-colors",
                  days.includes(day)
                    ? "bg-primary text-white"
                    : "bg-canvas text-muted hover:bg-primary-soft",
                ].join(" ")}
              >
                {WEEKDAY_LABELS[day]}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap gap-4">
          <Input
            label="Start time"
            type="time"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            className="w-40"
          />
          <Input
            label="End time"
            type="time"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
            className="w-40"
          />
          <Input
            label="Slot duration (minutes)"
            type="number"
            min={15}
            max={120}
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            className="w-48"
          />
        </div>

        {formError && (
          <p role="alert" className="text-body text-error">
            {formError}
          </p>
        )}

        <Button
          onClick={handleSave}
          isLoading={updatePrefs.isPending}
          className="w-fit"
        >
          Save availability
        </Button>
      </div>
    </Card>
  );
}

export function Scheduling() {
  const [jobFilter, setJobFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<SlotStatus | "">("");

  const jobs = useJobs({});
  const interviews = useInterviews({
    job_id: jobFilter || undefined,
    status: statusFilter || undefined,
  });

  const jobTitleById = useMemo(
    () =>
      Object.fromEntries(
        (jobs.data?.items ?? []).map((j) => [j.job_id, j.job_title]),
      ),
    [jobs.data],
  );

  const jobOptions = [
    { value: "", label: "All jobs" },
    ...(jobs.data?.items ?? []).map((j) => ({
      value: j.job_id,
      label: j.job_title,
    })),
  ];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-page font-semibold">Scheduling</h1>
        <p className="text-body text-muted">
          Set your interview availability and review scheduled interviews.
        </p>
      </div>

      <AvailabilityForm />

      <div className="flex flex-col gap-4">
        <h2 className="text-section font-semibold">Interviews</h2>

        <div className="flex gap-4">
          <Select
            label="Job"
            options={jobOptions}
            value={jobFilter}
            onChange={(e) => setJobFilter(e.target.value)}
            className="w-64"
          />
          <Select
            label="Status"
            options={STATUS_OPTIONS}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as SlotStatus | "")}
            className="w-52"
          />
        </div>

        <DataTable<InterviewSlot>
          columns={[
            { key: "candidate_name", header: "Candidate" },
            {
              key: "job_id",
              header: "Job",
              render: (row) => jobTitleById[row.job_id] ?? "—",
            },
            {
              key: "scheduled_at",
              header: "When",
              render: (row) => formatDateTime(row.scheduled_at),
            },
            {
              key: "duration_minutes",
              header: "Duration",
              render: (row) => `${row.duration_minutes} min`,
            },
            {
              key: "status",
              header: "Status",
              render: (row) => (
                <StatusBadge status={SLOT_STATUS_LABELS[row.status]} />
              ),
            },
            {
              key: "google_meet_link",
              header: "Meet link",
              render: (row) =>
                row.google_meet_link ? (
                  <a
                    href={row.google_meet_link}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-primary hover:underline"
                  >
                    <VideoIcon className="h-4 w-4" />
                    Join
                  </a>
                ) : (
                  <span className="text-muted">—</span>
                ),
            },
          ]}
          rows={interviews.data?.items ?? []}
          rowKey={(row) => row.slot_id}
          isLoading={interviews.isLoading}
          errorText={
            interviews.isError
              ? apiErrorMessage(interviews.error, "Couldn't load interviews.")
              : undefined
          }
          onRetry={interviews.refetch}
          emptyTitle="No interviews scheduled yet"
          emptyDescription="Schedule interviews for ranked candidates from a job's Candidates screen."
          emptyIcon={<CalendarIcon />}
        />
      </div>
    </div>
  );
}
