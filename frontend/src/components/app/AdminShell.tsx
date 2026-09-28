import { Link, Navigate, Outlet } from "react-router-dom";
import { useCurrentRecruiter } from "../../lib/auth";

/** Same session gate as AppShell, deliberately without Sidebar/Header — the
 * admin dashboard is a separate, hidden operator tool, not another item
 * inside the normal recruiter shell. Just a way back to it. */
export function AdminShell() {
  const {
    data: recruiter,
    isLoading,
    isError,
    refetch,
  } = useCurrentRecruiter();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas">
        <span
          className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent"
          aria-hidden="true"
        />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-canvas p-8 text-center">
        <h1 className="text-card font-semibold">Couldn't reach the API</h1>
        <p className="max-w-sm text-body text-muted">
          Confirm the backend is running, then try again.
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="rounded-control bg-primary px-5 py-3 text-body font-semibold text-white"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!recruiter) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="flex h-[72px] items-center justify-between border-b border-border bg-surface px-6">
        <span className="text-card font-extrabold">AutoHire Admin</span>
        <Link
          to="/dashboard"
          className="rounded-control border border-border bg-surface px-5 py-3 text-body font-semibold text-navy transition-colors hover:bg-primary-soft"
        >
          Back to Dashboard
        </Link>
      </header>
      <main className="p-8">
        <Outlet />
      </main>
    </div>
  );
}
