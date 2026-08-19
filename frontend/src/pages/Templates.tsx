import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { DataTable, Modal, type DataTableColumn } from "../components/ui";
import { buttonClassName } from "../components/ui/Button";
import { useToast } from "../components/ui/Toast";
import { apiErrorMessage } from "../lib/http";
import { useDeleteTemplate, useTemplates, type Template } from "../lib/templates";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function Templates() {
  const { data, isLoading, isError, error, refetch } = useTemplates();
  const deleteTemplate = useDeleteTemplate();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [pendingDelete, setPendingDelete] = useState<Template | null>(null);

  const templates = data?.items ?? [];

  function handleDelete() {
    if (!pendingDelete) return;
    deleteTemplate.mutate(pendingDelete.template_id, {
      onSuccess: () => {
        showToast(`"${pendingDelete.template_name}" deleted.`, "success");
        setPendingDelete(null);
      },
      onError: (err) => {
        // Most likely TEMPLATE_IN_USE (409) — a job posting still references
        // this template. Surface it and keep the modal open so the recruiter
        // sees why the delete didn't go through, rather than it silently closing.
        showToast(apiErrorMessage(err, "Couldn't delete this template."), "error");
      },
    });
  }

  const columns: DataTableColumn<Template>[] = [
    { key: "template_name", header: "Template name" },
    {
      key: "fields",
      header: "Fields",
      render: (row) => `${row.fields.length} field${row.fields.length === 1 ? "" : "s"}`,
    },
    {
      key: "updated_at",
      header: "Last updated",
      render: (row) => formatDate(row.updated_at),
    },
    {
      key: "actions",
      header: "Actions",
      render: (row) => (
        <div className="flex justify-end gap-4">
          <Link to={`/templates/${row.template_id}/edit`} className="text-body text-primary hover:underline">
            Edit
          </Link>
          <button
            type="button"
            onClick={() => setPendingDelete(row)}
            className="text-body text-error hover:underline"
          >
            Delete
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-page font-semibold">Application templates</h1>
          <p className="text-body text-muted">
            Manage and reuse application forms across different job postings.
          </p>
        </div>
        <Link to="/templates/new" className={buttonClassName()}>
          + Create template
        </Link>
      </div>

      <DataTable
        columns={columns}
        rows={templates}
        rowKey={(row) => row.template_id}
        isLoading={isLoading}
        errorText={isError ? apiErrorMessage(error, "Couldn't load your templates.") : undefined}
        onRetry={refetch}
        emptyTitle="No templates yet"
        emptyDescription="Create a reusable application form to start launching jobs."
        emptyActionLabel="+ Create template"
        onEmptyAction={() => navigate("/templates/new")}
      />

      <Modal
        open={pendingDelete !== null}
        title={`Delete "${pendingDelete?.template_name}"?`}
        onClose={() => setPendingDelete(null)}
        primaryLabel="Delete"
        onPrimary={handleDelete}
        isLoading={deleteTemplate.isPending}
      >
        <p className="text-body text-muted">
          This can't be undone. Jobs already using this template keep working, but
          you won't be able to pick it for a new one.
        </p>
      </Modal>
    </div>
  );
}
