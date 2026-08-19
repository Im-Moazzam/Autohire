import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Button, Card, EmptyState, Input, Select, Textarea } from "../components/ui";
import { buttonClassName } from "../components/ui/Button";
import { useToast } from "../components/ui/Toast";
import { apiErrorCode, apiErrorMessage } from "../lib/http";
import { useCreateJob, useJob, useUpdateJob } from "../lib/jobs";
import { useTemplates } from "../lib/templates";

/** Applications close at the end of the chosen day (23:59:59 local), so a
 * recruiter picking "today" doesn't accidentally close the job immediately. */
function dateToExpiresAt(date: string): string {
  return new Date(`${date}T23:59:59`).toISOString();
}

function expiresAtToDateInput(iso: string): string {
  return iso.slice(0, 10);
}

export function JobBuilder() {
  const { jobId } = useParams<{ jobId: string }>();
  const isEditing = !!jobId;
  const navigate = useNavigate();
  const { showToast } = useToast();

  const existing = useJob(jobId);
  const templates = useTemplates();
  const createJob = useCreateJob();
  const updateJob = useUpdateJob(jobId ?? "");

  const [jobTitle, setJobTitle] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [templateId, setTemplateId] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [titleError, setTitleError] = useState<string>();
  const [formError, setFormError] = useState<string>();
  const [retryJobId, setRetryJobId] = useState<string>();

  const titleInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (existing.data) {
      setJobTitle(existing.data.job_title);
      setJobDescription(existing.data.job_description);
      setTemplateId(existing.data.template_id);
      setExpiresAt(expiresAtToDateInput(existing.data.expires_at));
    }
  }, [existing.data]);

  if (isEditing && existing.isLoading) {
    return (
      <div className="max-w-2xl">
        <Card isLoading />
      </div>
    );
  }

  if (isEditing && existing.isError) {
    return (
      <div className="max-w-2xl">
        <Card errorText={apiErrorMessage(existing.error, "Couldn't load this job.")} />
        <Link to="/jobs" className="mt-4 inline-block text-body text-primary hover:underline">
          Back to jobs
        </Link>
      </div>
    );
  }

  if (!isEditing && templates.isLoading) {
    return (
      <div className="max-w-2xl">
        <Card isLoading />
      </div>
    );
  }

  if (!isEditing && (templates.data?.items.length ?? 0) === 0) {
    return (
      <div className="max-w-2xl">
        <EmptyState
          title="You need a template first"
          description="A job's application form comes from a template. Create one, then come back to launch this job."
          actionLabel="+ Create template"
          onAction={() => navigate("/templates/new")}
        />
      </div>
    );
  }

  const mutation = isEditing ? updateJob : createJob;
  const canClose = isEditing && existing.data?.status === "LIVE";

  function validateTitle(): boolean {
    if (!jobTitle.trim()) {
      setTitleError("Job title is required.");
      return false;
    }
    setTitleError(undefined);
    return true;
  }

  function handleSubmit() {
    setFormError(undefined);
    setRetryJobId(undefined);

    if (!validateTitle()) {
      titleInputRef.current?.focus();
      return;
    }
    if (!isEditing && !templateId) {
      setFormError("Choose a template.");
      return;
    }
    if (!expiresAt) {
      setFormError("Set an application deadline.");
      return;
    }
    const expiresAtIso = dateToExpiresAt(expiresAt);
    if (new Date(expiresAtIso) <= new Date()) {
      setFormError("The deadline must be in the future.");
      return;
    }

    const onError = (err: unknown) => {
      if (apiErrorCode(err) === "RESUME_FOLDER_FAILED") {
        const details = (err as { body?: { details?: { job_id?: string } } })?.body?.details;
        setFormError(
          "The job was saved, but its storage folder couldn't be created. Try launching it again.",
        );
        setRetryJobId(details?.job_id ?? jobId);
        return;
      }
      setFormError(apiErrorMessage(err));
    };

    if (isEditing) {
      updateJob.mutate(
        {
          job_title: jobTitle.trim(),
          job_description: jobDescription.trim(),
          expires_at: expiresAtIso,
        },
        {
          onSuccess: () => {
            showToast("Job saved.", "success");
            navigate("/jobs");
          },
          onError,
        },
      );
    } else {
      createJob.mutate(
        {
          job_title: jobTitle.trim(),
          job_description: jobDescription.trim(),
          template_id: templateId,
          expires_at: expiresAtIso,
        },
        {
          onSuccess: () => {
            showToast("Job launched.", "success");
            navigate("/jobs");
          },
          onError,
        },
      );
    }
  }

  function handleClose() {
    updateJob.mutate(
      { status: "CLOSED" },
      {
        onSuccess: () => {
          showToast("Job closed.", "success");
          navigate("/jobs");
        },
        onError: (err) => showToast(apiErrorMessage(err, "Couldn't close this job."), "error"),
      },
    );
  }

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-page font-semibold">{isEditing ? "Edit job" : "Create new job"}</h1>
        <Link to="/jobs" className="text-body text-muted hover:text-ink">
          Cancel
        </Link>
      </div>

      <Input
        ref={titleInputRef}
        label="Job title"
        value={jobTitle}
        onChange={(e) => setJobTitle(e.target.value)}
        onBlur={validateTitle}
        errorText={titleError}
        placeholder="e.g. Senior Frontend Engineer"
      />

      <Textarea
        label="Job description"
        value={jobDescription}
        onChange={(e) => setJobDescription(e.target.value)}
        placeholder="We are looking for..."
        rows={8}
      />

      {isEditing ? (
        <div className="flex flex-col gap-2">
          <span className="text-body font-medium text-ink">Template</span>
          <p className="text-body text-muted">
            {templates.data?.items.find((t) => t.template_id === templateId)?.template_name ??
              "—"}{" "}
            <span className="text-helper">(can't be changed after launch)</span>
          </p>
        </div>
      ) : (
        <Select
          label="Template"
          options={(templates.data?.items ?? []).map((t) => ({
            value: t.template_id,
            label: t.template_name,
          }))}
          value={templateId}
          onChange={(e) => setTemplateId(e.target.value)}
          placeholder="Choose a template"
        />
      )}

      <Input
        label="Application deadline"
        type="date"
        value={expiresAt}
        onChange={(e) => setExpiresAt(e.target.value)}
        helperText="Applications close at the end of this day."
        min={new Date().toISOString().slice(0, 10)}
      />

      {formError && (
        <div role="alert" className="flex flex-col gap-2 text-body text-error">
          <p>{formError}</p>
          {retryJobId && (
            <Link to={`/jobs/${retryJobId}/edit`} className="text-primary hover:underline">
              Go to the job and retry
            </Link>
          )}
        </div>
      )}

      <div className="flex items-center justify-between">
        {canClose ? (
          <button
            type="button"
            onClick={handleClose}
            disabled={updateJob.isPending}
            className="text-body text-error hover:underline disabled:opacity-50"
          >
            Close job
          </button>
        ) : (
          <span />
        )}
        <div className="flex gap-3">
          <Link to="/jobs" className={buttonClassName({ variant: "secondary" })}>
            Cancel
          </Link>
          <Button onClick={handleSubmit} isLoading={mutation.isPending}>
            {isEditing ? "Save changes" : "Launch job"}
          </Button>
        </div>
      </div>
    </div>
  );
}
