import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Button, Card, Input, Select, Textarea, type SelectOption } from "../components/ui";
import { buttonClassName } from "../components/ui/Button";
import { useToast } from "../components/ui/Toast";
import { apiErrorCode, apiErrorMessage } from "../lib/http";
import {
  FIELD_TYPES_WITH_OPTIONS,
  FIELD_TYPE_LABELS,
  useCreateTemplate,
  useReplaceTemplate,
  useTemplate,
  type FieldType,
  type TemplateFieldInput,
} from "../lib/templates";

interface DraftField {
  /** Stable client-side identity for list rendering — new fields have no
   * field_id yet, so React needs something else to key on. */
  key: string;
  field_id?: string;
  field_label: string;
  field_type: FieldType;
  is_required: boolean;
  optionsText: string;
}

const FIELD_TYPE_OPTIONS: SelectOption[] = Object.entries(FIELD_TYPE_LABELS).map(
  ([value, label]) => ({ value, label }),
);

function newField(): DraftField {
  return {
    key: crypto.randomUUID(),
    field_label: "",
    field_type: "SHORT_TEXT",
    is_required: false,
    optionsText: "",
  };
}

function hasIdentityFields(fields: DraftField[]): { email: boolean; name: boolean } {
  let email = false;
  let name = false;
  for (const field of fields) {
    const norm = field.field_label.toLowerCase().replace(/[^a-z0-9]/g, "");
    if (!email && norm.includes("email")) email = true;
    if (!name && !norm.includes("email") && norm.includes("name")) name = true;
  }
  return { email, name };
}

export function TemplateBuilder() {
  const { templateId } = useParams<{ templateId: string }>();
  const isEditing = !!templateId;
  const navigate = useNavigate();
  const { showToast } = useToast();

  const existing = useTemplate(templateId);
  const createTemplate = useCreateTemplate();
  const replaceTemplate = useReplaceTemplate(templateId ?? "");

  const [templateName, setTemplateName] = useState("");
  const [fields, setFields] = useState<DraftField[]>([newField()]);
  const [nameError, setNameError] = useState<string>();
  const [formError, setFormError] = useState<string>();

  const nameInputRef = useRef<HTMLInputElement>(null);
  const fieldLabelRefs = useRef(new Map<string, HTMLInputElement>());
  const [focusFieldKey, setFocusFieldKey] = useState<string | null>(null);

  useEffect(() => {
    if (!focusFieldKey) return;
    fieldLabelRefs.current.get(focusFieldKey)?.focus();
    setFocusFieldKey(null);
  }, [focusFieldKey]);

  useEffect(() => {
    if (existing.data) {
      setTemplateName(existing.data.template_name);
      setFields(
        existing.data.fields.map((f) => ({
          key: f.field_id,
          field_id: f.field_id,
          field_label: f.field_label,
          field_type: f.field_type,
          is_required: f.is_required,
          optionsText: (f.options ?? []).join("\n"),
        })),
      );
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
        <Card errorText={apiErrorMessage(existing.error, "Couldn't load this template.")} />
        <Link to="/templates" className="mt-4 inline-block text-body text-primary hover:underline">
          Back to templates
        </Link>
      </div>
    );
  }

  const identity = hasIdentityFields(fields);
  const mutation = isEditing ? replaceTemplate : createTemplate;

  function updateField(key: string, patch: Partial<DraftField>) {
    setFields((prev) => prev.map((f) => (f.key === key ? { ...f, ...patch } : f)));
  }

  function removeField(key: string) {
    setFields((prev) => prev.filter((f) => f.key !== key));
  }

  function addField() {
    const field = newField();
    setFields((prev) => [...prev, field]);
    setFocusFieldKey(field.key);
  }

  function moveField(index: number, direction: -1 | 1) {
    setFields((prev) => {
      const next = [...prev];
      const target = index + direction;
      if (target < 0 || target >= next.length) return prev;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function validateName(): boolean {
    if (!templateName.trim()) {
      setNameError("Template name is required.");
      return false;
    }
    setNameError(undefined);
    return true;
  }

  function handleSubmit() {
    setFormError(undefined);

    if (!validateName()) {
      nameInputRef.current?.focus();
      return;
    }
    if (fields.length === 0) {
      setFormError("Add at least one field.");
      return;
    }
    for (const field of fields) {
      if (!field.field_label.trim()) {
        setFormError("Every field needs a label.");
        fieldLabelRefs.current.get(field.key)?.focus();
        return;
      }
      if (FIELD_TYPES_WITH_OPTIONS.includes(field.field_type) && !field.optionsText.trim()) {
        setFormError(`"${field.field_label}" needs at least one option.`);
        fieldLabelRefs.current.get(field.key)?.focus();
        return;
      }
    }
    if (!identity.email || !identity.name) {
      setFormError(
        "Include a field labeled with \"email\" and one with \"name\" (e.g. \"Full Name\", \"Email Address\") — candidates can't be matched to submissions without both.",
      );
      return;
    }

    const payload = {
      template_name: templateName.trim(),
      fields: fields.map<TemplateFieldInput>((field, index) => ({
        field_id: field.field_id,
        field_label: field.field_label.trim(),
        field_type: field.field_type,
        is_required: field.is_required,
        field_order: index,
        options: FIELD_TYPES_WITH_OPTIONS.includes(field.field_type)
          ? field.optionsText.split("\n").map((o) => o.trim()).filter(Boolean)
          : null,
      })),
    };

    mutation.mutate(payload, {
      onSuccess: () => {
        showToast(isEditing ? "Template saved." : "Template created.", "success");
        navigate("/templates");
      },
      onError: (err) => {
        if (apiErrorCode(err) === "DUPLICATE_TEMPLATE_NAME") {
          setNameError(apiErrorMessage(err));
          return;
        }
        setFormError(apiErrorMessage(err));
      },
    });
  }

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-page font-semibold">
          {isEditing ? "Edit template" : "Create template"}
        </h1>
        <Link to="/templates" className="text-body text-muted hover:text-ink">
          Cancel
        </Link>
      </div>

      <Input
        ref={nameInputRef}
        label="Template name"
        value={templateName}
        onChange={(e) => setTemplateName(e.target.value)}
        onBlur={validateName}
        errorText={nameError}
        placeholder="e.g. Software Engineer - Senior"
      />

      <div className="flex flex-col gap-4">
        <h2 className="text-card font-semibold">Fields</h2>

        {fields.length === 0 ? (
          <div className="rounded-card border border-dashed border-border p-8 text-center">
            <p className="text-body text-muted">No fields yet.</p>
            <button
              type="button"
              onClick={addField}
              className="mt-2 text-body text-primary hover:underline"
            >
              Add your first field
            </button>
          </div>
        ) : (
          fields.map((field, index) => (
            <div key={field.key} className="rounded-card border border-border bg-surface p-4">
              <div className="flex items-start gap-3">
                <div className="flex flex-1 flex-col gap-3">
                  <Input
                    ref={(el) => {
                      if (el) fieldLabelRefs.current.set(field.key, el);
                      else fieldLabelRefs.current.delete(field.key);
                    }}
                    label="Field label"
                    value={field.field_label}
                    onChange={(e) => updateField(field.key, { field_label: e.target.value })}
                    placeholder="e.g. Full Name"
                  />
                  <Select
                    label="Field type"
                    options={FIELD_TYPE_OPTIONS}
                    value={field.field_type}
                    onChange={(e) =>
                      updateField(field.key, { field_type: e.target.value as FieldType })
                    }
                  />
                  {FIELD_TYPES_WITH_OPTIONS.includes(field.field_type) && (
                    <Textarea
                      label="Options"
                      helperText="One option per line."
                      value={field.optionsText}
                      onChange={(e) => updateField(field.key, { optionsText: e.target.value })}
                    />
                  )}
                  <label className="flex items-center gap-2 text-body">
                    <input
                      type="checkbox"
                      checked={field.is_required}
                      onChange={(e) => updateField(field.key, { is_required: e.target.checked })}
                    />
                    Required
                  </label>
                </div>
                <div className="flex flex-col items-center gap-1">
                  <button
                    type="button"
                    onClick={() => moveField(index, -1)}
                    disabled={index === 0}
                    aria-label="Move field up"
                    className="text-muted hover:text-ink disabled:opacity-30"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    onClick={() => moveField(index, 1)}
                    disabled={index === fields.length - 1}
                    aria-label="Move field down"
                    className="text-muted hover:text-ink disabled:opacity-30"
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    onClick={() => removeField(field.key)}
                    aria-label="Remove field"
                    className="mt-2 text-error hover:underline"
                  >
                    Remove
                  </button>
                </div>
              </div>
            </div>
          ))
        )}

        {fields.length > 0 && (
          <button
            type="button"
            onClick={addField}
            className="self-start rounded-control border border-dashed border-border px-4 py-2 text-body text-primary hover:bg-primary-soft"
          >
            + Add field
          </button>
        )}
      </div>

      {formError && (
        <p role="alert" className="text-body text-error">
          {formError}
        </p>
      )}

      <div className="flex justify-end gap-3">
        <Link to="/templates" className={buttonClassName({ variant: "secondary" })}>
          Cancel
        </Link>
        <Button onClick={handleSubmit} isLoading={mutation.isPending}>
          Save template
        </Button>
      </div>
    </div>
  );
}
