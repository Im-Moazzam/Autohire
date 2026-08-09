import { useState } from "react";
import {
  Button,
  Input,
  Select,
  Textarea,
  FileInput,
  DataTable,
  Modal,
  StatusBadge,
  MatchScore,
  Card,
  EmptyState,
  useToast,
  type Status,
} from "../components/ui";

const statuses: Status[] = [
  "Active",
  "Expired",
  "Draft",
  "Processing",
  "Scheduled",
  "Interview Invited",
  "Confirmed",
  "Reschedule Requested",
  "Rejected",
  "Failed",
  "Connected",
  "Disconnected",
  "Syncing",
  "Quota Warning",
];

type Candidate = { id: string; name: string; email: string };
const rows: Candidate[] = [
  { id: "1", name: "Aisha Khan", email: "aisha@example.com" },
  { id: "2", name: "Bilal Ahmed", email: "bilal@example.com" },
];

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-4 py-8 border-b border-border">
      <h2 className="text-section font-semibold text-ink">{title}</h2>
      <div className="flex flex-wrap gap-4 items-start">{children}</div>
    </section>
  );
}

export function KitchenSink() {
  const [modalOpen, setModalOpen] = useState(false);
  const { showToast } = useToast();

  return (
    <div className="p-8 max-w-5xl mx-auto flex flex-col">
      <h1 className="text-page font-semibold text-ink mb-2">Kitchen sink</h1>
      <p className="text-body text-muted mb-4">
        Every UI primitive, every state. Dev only.
      </p>

      <Section title="Button">
        <Button>Save changes</Button>
        <Button variant="secondary">Cancel</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="destructive">Delete job</Button>
        <Button isLoading>Saving…</Button>
        <Button disabled>Disabled</Button>
        <Button hasError>Retry</Button>
      </Section>

      <Section title="Input">
        <Input
          label="Full name"
          placeholder="Jane Doe"
          helperText="As it appears on the resume"
        />
        <Input label="Email" disabled defaultValue="disabled@example.com" />
        <Input
          label="Email"
          errorText="Enter a valid email address"
          defaultValue="not-an-email"
        />
        <Input label="Slug" isValidating defaultValue="checking-availability" />
      </Section>

      <Section title="Select">
        <Select
          label="Notice period"
          options={[
            { value: "2w", label: "2 weeks" },
            { value: "1m", label: "1 month" },
          ]}
          placeholder="Choose one"
        />
        <Select label="Notice period" options={[]} isLoading />
        <Select label="Notice period" options={[]} disabled />
        <Select label="Notice period" options={[]} errorText="Required" />
      </Section>

      <Section title="Textarea">
        <Textarea label="Job description" placeholder="Describe the role…" />
        <Textarea label="Job description" disabled defaultValue="Locked" />
        <Textarea label="Job description" errorText="Description is required" />
      </Section>

      <Section title="FileInput">
        <FileInput label="Resume" helperText="PDF or DOCX, under 5MB" />
        <FileInput label="Resume" uploadProgress={60} />
        <FileInput label="Resume" disabled />
        <FileInput
          label="Resume"
          errorText="Resume must be PDF or DOCX under 5MB"
        />
      </Section>

      <Section title="StatusBadge">
        {statuses.map((s) => (
          <StatusBadge key={s} status={s} />
        ))}
      </Section>

      <Section title="MatchScore">
        <MatchScore score={0.92} />
        <MatchScore score={0.68} />
        <MatchScore score={0.45} />
        <MatchScore score={0.2} />
        <MatchScore isLoading />
        <MatchScore errorText="Parse failed" />
      </Section>

      <Section title="Card">
        <Card title="Open jobs" className="w-64">
          12 active postings
        </Card>
        <Card isLoading className="w-64" />
        <Card errorText="Couldn't load this card" className="w-64" />
        <Card title="Archived" disabled className="w-64">
          Read only
        </Card>
      </Section>

      <Section title="EmptyState">
        <div className="w-96 border border-border rounded-card">
          <EmptyState
            title="No jobs yet"
            description="Launch your first job to start ranking candidates."
            actionLabel="Create job"
            onAction={() => {}}
          />
        </div>
        <div className="w-96 border border-border rounded-card">
          <EmptyState
            variant="error"
            title="Couldn't load jobs"
            description="Check your connection and try again."
            actionLabel="Retry"
            onAction={() => {}}
          />
        </div>
      </Section>

      <Section title="DataTable">
        <div className="w-full flex flex-col gap-6">
          <DataTable
            columns={[
              { key: "name", header: "Name" },
              { key: "email", header: "Email" },
            ]}
            rows={rows}
            rowKey={(r) => r.id}
          />
          <DataTable
            columns={[{ key: "name", header: "Name" }]}
            rows={[]}
            rowKey={(r: Candidate) => r.id}
            isLoading
          />
          <DataTable
            columns={[{ key: "name", header: "Name" }]}
            rows={[]}
            rowKey={(r: Candidate) => r.id}
            emptyTitle="No candidates yet"
          />
          <DataTable
            columns={[{ key: "name", header: "Name" }]}
            rows={[]}
            rowKey={(r: Candidate) => r.id}
            errorText="Request timed out"
            onRetry={() => {}}
          />
          <DataTable
            columns={[
              { key: "name", header: "Name" },
              { key: "email", header: "Email" },
            ]}
            rows={rows}
            rowKey={(r) => r.id}
            rowError={(r) =>
              r.id === "2" ? "Resume failed to parse" : undefined
            }
          />
        </div>
      </Section>

      <Section title="Modal">
        <Button onClick={() => setModalOpen(true)}>Open modal</Button>
        <Modal
          open={modalOpen}
          title="Launch job"
          onClose={() => setModalOpen(false)}
          primaryLabel="Launch job"
          onPrimary={() => setModalOpen(false)}
        >
          <p className="text-body text-muted">
            This will notify all connected recruiters.
          </p>
        </Modal>
      </Section>

      <Section title="Toast">
        <Button onClick={() => showToast("Job launched", "success")}>
          Trigger success
        </Button>
        <Button onClick={() => showToast("Failed to launch job", "error")}>
          Trigger error
        </Button>
        <Button onClick={() => showToast("Quota running low", "warning")}>
          Trigger warning
        </Button>
        <Button onClick={() => showToast("Processing resumes…", "loading")}>
          Trigger loading
        </Button>
      </Section>
    </div>
  );
}
