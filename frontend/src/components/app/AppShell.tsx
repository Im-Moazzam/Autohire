import { Navigate, Outlet } from "react-router-dom";
import { googleReconnectUrl, useCurrentRecruiter } from "../../lib/auth";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

/** Authenticated recruiter shell — sidebar, header, and the session gate every
 * screen under it relies on. A page never needs to re-check /auth/me itself. */
export function AppShell() {
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
    <div className="flex min-h-screen bg-canvas text-ink">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        {recruiter.account_state === "REAUTH_REQUIRED" && (
          <div className="flex items-center justify-center gap-3 bg-warning px-6 py-3 text-body text-white">
            <span>Your Google authorization has expired.</span>
            <a
              href={googleReconnectUrl}
              className="font-semibold underline underline-offset-2"
            >
              Reconnect Google
            </a>
          </div>
        )}
        <Header />
        <main className="flex-1 overflow-y-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
