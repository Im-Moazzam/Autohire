import { useRef, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Button,
  Card,
  EmptyState,
  FileInput,
  Input,
  Select,
  Textarea,
} from "../components/ui";
import { apiErrorCode, apiErrorMessage, ApiError } from "../lib/http";
import { resolveIdentityFields } from "../lib/identityFields";
import { FIELD_TYPES_WITH_OPTIONS } from "../lib/templates";
import {
  usePublicJob,
  useSubmitApplication,
  type TemplateField,
} from "../lib/apply";

const _RESUME_ERROR_CODES = new Set([
  "FILE_TOO_LARGE",
  "UNSUPPORTED_FILE_TYPE",
  "EMPTY_FILE",
]);
const _EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function sortedFields(fields: TemplateField[]): TemplateField[] {
  return [...fields].sort((a, b) => a.field_order - b.field_order);
}

function JobDescription({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = text.length > 320;

  return (
    <div>
      <p
        className={`mt-2 whitespace-pre-wrap text-body text-muted ${
          !expanded && isLong ? "line-clamp-4" : ""
        }`}
      >
        {text}
      </p>
      {isLong && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-1 text-body text-primary hover:underline"
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}

function Field({
  field,
  isEmail,
  value,
  errorText,
  onChange,
  onBlur,
  inputRef,
}: {
  field: TemplateField;
  isEmail: boolean;
  value: string;
  errorText?: string;
  onChange: (value: string) => void;
  onBlur: () => void;
  inputRef: (
    el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null,
  ) => void;
}) {
  const label = field.is_required
    ? `${field.field_label} *`
    : field.field_label;

  if (field.field_type === "PARAGRAPH") {
    return (
      <Textarea
        ref={inputRef as (el: HTMLTextAreaElement | null) => void}
        label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        errorText={errorText}
        rows={4}
      />
    );
  }

  if (FIELD_TYPES_WITH_OPTIONS.includes(field.field_type)) {
    return (
      <Select
        ref={inputRef as unknown as (el: HTMLSelectElement | null) => void}
        label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        errorText={errorText}
        placeholder="Choose one"
        options={(field.options ?? []).map((o) => ({ value: o, label: o }))}
      />
    );
  }

  const type = isEmail
    ? "email"
    : field.field_type === "DATE"
      ? "date"
      : field.field_type === "NUMBER"
        ? "number"
        : "text";
  return (
    <Input
      ref={inputRef as (el: HTMLInputElement | null) => void}
      label={label}
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
      errorText={errorText}
    />
  );
}

export function Apply() {
  const { slug } = useParams<{ slug: string }>();
  const job = usePublicJob(slug);
  const submit = useSubmitApplication(slug ?? "");

  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [resume, setResume] = useState<File | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [resumeError, setResumeError] = useState<string>();
  const [formError, setFormError] = useState<string>();

  const fieldRefs = useRef(
    new Map<
      string,
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >(),
  );
  const resumeInputRef = useRef<HTMLInputElement>(null);

  if (job.isLoading) {
    return <Card isLoading />;
  }

  if (job.isError) {
    const code = apiErrorCode(job.error);
    const closedTitle =
      code === "JOB_CLOSED"
        ? ((job.error as ApiError).body as { details?: { job_title?: string } })
            ?.details?.job_title
        : undefined;
    return (
      <EmptyState
        variant="error"
        title={
          closedTitle
            ? `"${closedTitle}" is no longer accepting applications`
            : "This link doesn't work"
        }
        description={apiErrorMessage(
          job.error,
          "The application link is invalid or the posting has been removed.",
        )}
      />
    );
  }

  if (!job.data) {
    return <Card isLoading />;
  }

  if (submit.isSuccess) {
    return (
      <EmptyState
        title="Application received"
        description={`Thanks for applying to ${job.data.job_title}. ${submit.data.message}`}
      />
    );
  }

  const fields = sortedFields(job.data.fields).filter(
    (f) => f.field_type !== "FILE_UPLOAD",
  );
  const hasRequiredField = fields.some((f) => f.is_required);
  const { emailIndex } = resolveIdentityFields(
    fields.map((f) => f.field_label),
  );
  const emailFieldId =
    emailIndex !== null ? fields[emailIndex].field_id : undefined;

  function setAnswer(fieldId: string, value: string) {
    setAnswers((prev) => ({ ...prev, [fieldId]: value }));
  }

  /** Required-empty and email-format checks, both inline on blur and again
   * at submit — ux.md: "Forms validate inline on blur, not only on submit." */
  function validateField(field: TemplateField): string | undefined {
    const value = (answers[field.field_id] ?? "").trim();
    if (field.is_required && !value) return "This field is required.";
    if (
      field.field_id === emailFieldId &&
      value &&
      !_EMAIL_PATTERN.test(value)
    ) {
      return "Enter a valid email address.";
    }
    return undefined;
  }

  function handleFieldBlur(field: TemplateField) {
    const error = validateField(field);
    setFieldErrors((prev) => {
      if (!error) {
        if (!(field.field_id in prev)) return prev;
        const next = { ...prev };
        delete next[field.field_id];
        return next;
      }
      return { ...prev, [field.field_id]: error };
    });
  }

  function validate(): boolean {
    const errors: Record<string, string> = {};
    let firstInvalid: string | undefined;
    for (const field of fields) {
      const error = validateField(field);
      if (error) {
        errors[field.field_id] = error;
        firstInvalid ??= field.field_id;
      }
    }
    setFieldErrors(errors);

    let resumeOk = true;
    if (!resume) {
      setResumeError("Attach your resume (PDF, DOC, or DOCX).");
      resumeOk = false;
      firstInvalid ??= "resume";
    } else {
      setResumeError(undefined);
    }

    if (firstInvalid) {
      if (firstInvalid === "resume") {
        resumeInputRef.current?.focus();
      } else {
        fieldRefs.current.get(firstInvalid)?.focus();
      }
    }

    return Object.keys(errors).length === 0 && resumeOk;
  }

  /** Maps a structured backend 422/409 back onto the specific field(s) it
   * complains about, so the recruiter's original ask — "highlight the wrong
   * fields, don't just say invalid" — holds for server-side rejections too,
   * not only the client-side checks in validate(). Returns false when the
   * error isn't field-shaped (e.g. a storage failure), so the caller can
   * fall back to a page-level message. */
  function applyServerFieldErrors(err: unknown): boolean {
    if (!(err instanceof ApiError)) return false;
    const code = apiErrorCode(err);
    const details = (err.body as { details?: Record<string, unknown> } | null)
      ?.details;
    const next: Record<string, string> = {};

    if (code === "MISSING_REQUIRED_FIELD" && Array.isArray(details?.missing)) {
      for (const fieldId of details.missing as string[]) {
        next[fieldId] = "This field is required.";
      }
    } else if (
      code === "UNKNOWN_FIELD" &&
      typeof details?.field_id === "string"
    ) {
      next[details.field_id] =
        "This field couldn't be submitted — try reloading the page.";
    } else if (code === "VALIDATION_ERROR" && Array.isArray(details?.fields)) {
      for (const fieldId of details.fields as string[]) {
        next[fieldId] = "This response is too long.";
      }
    } else if (code === "VALIDATION_ERROR" && Array.isArray(details?.errors)) {
      for (const e of details.errors as { loc?: unknown[] }[]) {
        const loc = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : undefined;
        if (loc === "email" && emailFieldId)
          next[emailFieldId] = "Enter a valid email address.";
        if (loc === "full_name") {
          const { nameIndex } = resolveIdentityFields(
            fields.map((f) => f.field_label),
          );
          if (nameIndex !== null)
            next[fields[nameIndex].field_id] = "Enter your full name.";
        }
      }
    } else if (code === "DUPLICATE_SUBMISSION" && emailFieldId) {
      next[emailFieldId] = apiErrorMessage(err);
    }

    if (Object.keys(next).length === 0) return false;
    setFieldErrors((prev) => ({ ...prev, ...next }));
    fieldRefs.current.get(Object.keys(next)[0])?.focus();
    return true;
  }

  function handleSubmit() {
    setFormError(undefined);
    if (!validate() || !resume) return;

    const formData = new FormData();
    for (const field of fields) {
      formData.append(field.field_id, answers[field.field_id] ?? "");
    }
    formData.append("resume", resume);

    submit.mutate(formData, {
      onError: (err) => {
        const code = apiErrorCode(err);
        if (_RESUME_ERROR_CODES.has(code ?? "")) {
          setResumeError(apiErrorMessage(err));
          return;
        }
        if (applyServerFieldErrors(err)) return;
        setFormError(apiErrorMessage(err));
      },
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-page font-semibold">{job.data.job_title}</h1>
        <JobDescription text={job.data.job_description} />
      </div>

      <div className="flex flex-col gap-4">
        {fields.map((field) => (
          <Field
            key={field.field_id}
            field={field}
            isEmail={field.field_id === emailFieldId}
            value={answers[field.field_id] ?? ""}
            errorText={fieldErrors[field.field_id]}
            onChange={(value) => setAnswer(field.field_id, value)}
            onBlur={() => handleFieldBlur(field)}
            inputRef={(el) => {
              if (el) fieldRefs.current.set(field.field_id, el);
              else fieldRefs.current.delete(field.field_id);
            }}
          />
        ))}

        <FileInput
          ref={resumeInputRef}
          label="Resume *"
          helperText="PDF, DOC, or DOCX, up to 5MB."
          errorText={resumeError}
          accept=".pdf,.doc,.docx"
          onChange={(e) => setResume(e.target.files?.[0] ?? null)}
        />
      </div>

      {hasRequiredField && (
        <p className="text-helper text-muted">* fields are required</p>
      )}

      {formError && (
        <p role="alert" className="text-body text-error">
          {formError}
        </p>
      )}

      <Button onClick={handleSubmit} isLoading={submit.isPending}>
        Submit application
      </Button>
    </div>
  );
}
